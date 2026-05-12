import asyncio
import sqlite3
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiogram import F
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

TOKEN = ("Your bot token")

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# --- БЛОК БАЗЫ ДАННЫХ ---
class Form(StatesGroup):
    waiting_for_task = State()

def get_main_kb():
    builder = ReplyKeyboardBuilder()
    builder.add(types.KeyboardButton(text="Мой список"))
    builder.add(types.KeyboardButton(text="Очистить все"))
    builder.add(types.KeyboardButton(text="Добавить задачу"))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)
    
def init_db():
    conn = sqlite3.connect("todo.db") #создаем файл в котором уже будем хранить список дел
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            task_text TEXT
        )
    """)
    conn.commit()
    conn.close()



def delete_task_by_index(user_id, index):
    conn = sqlite3.connect("todo.db")
    cursor = conn.cursor()
    # Получаем ID всех задач пользователя, чтобы найти нужную по счету
    cursor.execute("SELECT id FROM tasks WHERE user_id = ?", (user_id,))
    tasks = cursor.fetchall()
    
    if 0 <= index < len(tasks):
        task_id = tasks[index][0]
        cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        conn.commit()
        conn.close()
        return True
    conn.close()
    return False


    

def add_task(user_id, text):
    conn = sqlite3.connect("todo.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO tasks (user_id, task_text) VALUES (?, ?)", (user_id, text))
    conn.commit()
    conn.close()

# Запускаем создание базы сразу при старте скрипта
init_db()

# --- БЛОК ОБРАБОТКИ СООБЩЕНИЙ ---

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    await message.answer(
        f"Привет, {message.from_user.full_name}! Выбирай действие:",
        reply_markup=get_main_kb() # Используем ту же функцию
    )
    
@dp.message(F.text == "Добавить задачу")
async def add_task_start(message: types.Message, state: FSMContext):
    # Создаем временную кнопку отмены
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

# Этот хэндлер должен стоять СТРОГО ПЕРЕД handle_all
@dp.message(Form.waiting_for_task)
async def save_task_to_db(message: types.Message, state: FSMContext):
    # Сохраняем в базу (вызываем твою функцию)
    add_task(message.from_user.id, message.text) 
    await message.answer(f"Задача '{message.text}' успешно добавлена!", reply_markup=get_main_kb())
    await state.clear() # Выключаем режим ожидания


@dp.message(F.text.startswith("Удалить "))
async def delete_item(message: types.Message):
    try:
        # Получаем номер, который ввел пользователь
        task_num = int(message.text.replace("Удалить ", ""))
        
        conn = sqlite3.connect("todo.db")
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM tasks WHERE user_id = ?", (message.from_user.id,))
        rows = cursor.fetchall()
        
        if 1 <= task_num <= len(rows):
            task_id = rows[task_num-1][0]
            cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            conn.commit()
            await message.answer(f"Задача №{task_num} удалена!")
        else:
            await message.answer("Задачи с таким номером нет в списке.")
        conn.close()
    except:
        await message.answer("Напиши номер, например: Удалить 2")    


@dp.message()
async def handle_all(message: types.Message):
    if message.text == "Мой список":
        conn = sqlite3.connect("todo.db")
        cursor = conn.cursor()
        cursor.execute("SELECT task_text FROM tasks WHERE user_id = ?", (message.from_user.id,))
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            await message.answer("Твой список пуст!")
        else:
            # Извлекаем текст из кортежей (база возвращает данные в виде [(текст,), (текст,)])
            res = "\n".join([f"{i+1}. {row[0]}" for i, row in enumerate(rows)])
            await message.answer(f" **Твой список дел:**\n\n{res}", parse_mode="Markdown")
            
    elif message.text == "Очистить все":
        conn = sqlite3.connect("todo.db")
        cursor = conn.cursor()
        cursor.execute("DELETE FROM tasks WHERE user_id = ?", (message.from_user.id,))
        conn.commit()
        conn.close()
        await message.answer("Список очищен!", reply_markup=get_main_kb())


# --- ЗАПУСК ---

async def main():
    print("Бот запущен и готов к работе!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот выключен")
