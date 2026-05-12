import asyncio
import aiosqlite
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
import os
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")


# --- НАСТРОЙКИ ---
TOKEN = "8646909728:AAFC5NF4hdus5QmTBF4knqiqvvTMQpm6z-w"
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

class Form(StatesGroup):
    waiting_for_task = State()

# --- КЛАВИАТУРА ---
def get_main_kb():
    builder = ReplyKeyboardBuilder()
    builder.add(types.KeyboardButton(text="Мой список"))
    builder.add(types.KeyboardButton(text="Очистить все"))
    builder.add(types.KeyboardButton(text="Добавить задачу"))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

# --- БЛОК БАЗЫ ДАННЫХ ---
async def init_db():
    async with aiosqlite.connect("todo.db") as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                task_text TEXT
            )
        ''')
        await db.commit()

async def add_task(user_id, text):
    async with aiosqlite.connect("todo.db") as db:
        await db.execute("INSERT INTO tasks (user_id, task_text) VALUES (?, ?)", (user_id, text))
        await db.commit()

async def delete_task_by_index(user_id, index):
    async with aiosqlite.connect("todo.db") as db:
        async with db.execute("SELECT id FROM tasks WHERE user_id = ?", (user_id,)) as cursor:
            rows = await cursor.fetchall()
            if 0 <= index < len(rows):
                task_id = rows[index][0]
                await db.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
                await db.commit()
                return True
            return False

# --- ОБРАБОТКА СООБЩЕНИЙ ---
@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    await message.answer(
        f"Привет, {message.from_user.full_name}! Я помогу со списком дел.",
        reply_markup=get_main_kb()
    )

@dp.message(F.text == "Добавить задачу")
async def add_task_start(message: types.Message, state: FSMContext):
    cancel_kb = types.ReplyKeyboardMarkup(
        keyboard=[[types.KeyboardButton(text="Отмена")]],
        resize_keyboard=True
    )
    await message.answer("Напиши название задачи:", reply_markup=cancel_kb)
    await state.set_state(Form.waiting_for_task)

@dp.message(Form.waiting_for_task, F.text == "Отмена")
async def cancel_handler(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Добавление отменено.", reply_markup=get_main_kb())

@dp.message(Form.waiting_for_task)
async def save_task_to_db(message: types.Message, state: FSMContext):
    await add_task(message.from_user.id, message.text)
    await message.answer(f"Задача '{message.text}' добавлена!", reply_markup=get_main_kb())
    await state.clear()

@dp.message(F.text.startswith("Удалить "))
async def delete_item(message: types.Message):
    try:
        task_num = int(message.text.replace("Удалить ", ""))
        deleted = await delete_task_by_index(message.from_user.id, task_num - 1)
        if deleted:
            await message.answer(f"Задача №{task_num} удалена!")
        else:
            await message.answer("Задачи с таким номером нет.")
    except ValueError:
        await message.answer("Напиши номер, например: Удалить 2")

@dp.message()
async def handle_all(message: types.Message):
    if message.text == "Мой список":
        async with aiosqlite.connect("todo.db") as db:
            async with db.execute("SELECT task_text FROM tasks WHERE user_id = ?", (message.from_user.id,)) as cursor:
                rows = await cursor.fetchall()
        if not rows:
            await message.answer("Твой список пуст!")
        else:
            res = "\n".join([f"{i+1}. {row[0]}" for i, row in enumerate(rows)])
            await message.answer(f"**Твой список дел:**\n\n{res}", parse_mode="Markdown")

    elif message.text == "Очистить все":
        async with aiosqlite.connect("todo.db") as db:
            await db.execute("DELETE FROM tasks WHERE user_id = ?", (message.from_user.id,))
            await db.commit()
        await message.answer("Список очищен!", reply_markup=get_main_kb())

# --- ЗАПУСК ---
async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
