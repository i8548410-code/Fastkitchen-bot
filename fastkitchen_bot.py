import asyncio
import logging
import aiosqlite
from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message, ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
)
from aiogram.filters import CommandStart
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

TOKEN = "TOKEN"
ADMIN_ID =Admin id # Admin ID yozing

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ================= DATABASE =================

async def init_db():
    async with aiosqlite.connect("bot.db") as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS products(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            price TEXT
        )
        """)
        await db.commit()

# ================= STATES =================

class Register(StatesGroup):
    name = State()
    surname = State()
    age = State()
    phone = State()

class AddProduct(StatesGroup):
    name = State()
    price = State()

class OrderState(StatesGroup):
    quantity = State()

# ================= ADMIN MENU =================

def admin_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Mahsulot qo'shish")],
            [KeyboardButton(text="📦 Mahsulotlarni ko'rish")],
            [KeyboardButton(text="❌ Mahsulot o'chirish")]
        ],
        resize_keyboard=True
    )

# ================= START =================

@dp.message(CommandStart())
async def start(message: Message, state: FSMContext):
    if message.from_user.id == ADMIN_ID:
        await message.answer("Siz adminsiz 👨‍💼", reply_markup=admin_keyboard())
    else:
        await message.answer("Ismingizni kiriting:")
        await state.set_state(Register.name)

# ================= REGISTRATION =================

@dp.message(Register.name)
async def get_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Familiyangizni kiriting:")
    await state.set_state(Register.surname)

@dp.message(Register.surname)
async def get_surname(message: Message, state: FSMContext):
    await state.update_data(surname=message.text)
    await message.answer("Yoshingizni kiriting:")
    await state.set_state(Register.age)

@dp.message(Register.age)
async def get_age(message: Message, state: FSMContext):
    await state.update_data(age=message.text)
    button = KeyboardButton(text="📞 Kontaktni yuborish", request_contact=True)
    keyboard = ReplyKeyboardMarkup(keyboard=[[button]], resize_keyboard=True)
    await message.answer("Telefon raqamingizni yuboring:", reply_markup=keyboard)
    await state.set_state(Register.phone)

@dp.message(Register.phone)
async def get_phone(message: Message, state: FSMContext):
    await state.update_data(phone=message.contact.phone_number)
    await message.answer("Ro'yxatdan o'tdingiz ✅", reply_markup=ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🛒 Buyurtma berish")]],
        resize_keyboard=True
    ))
    await state.clear()

# ================= ADMIN FUNCTIONS =================

@dp.message(F.text == "➕ Mahsulot qo'shish")
async def add_product_start(message: Message, state: FSMContext):
    await message.answer("Mahsulot nomini kiriting:")
    await state.set_state(AddProduct.name)

@dp.message(AddProduct.name)
async def add_product_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Narxini kiriting:")
    await state.set_state(AddProduct.price)

@dp.message(AddProduct.price)
async def add_product_price(message: Message, state: FSMContext):
    data = await state.get_data()
    async with aiosqlite.connect("bot.db") as db:
        await db.execute(
            "INSERT INTO products (name, price) VALUES (?, ?)",
            (data["name"], message.text)
        )
        await db.commit()
    await message.answer("Mahsulot qo'shildi ✅", reply_markup=admin_keyboard())
    await state.clear()

@dp.message(F.text == "📦 Mahsulotlarni ko'rish")
async def view_products(message: Message):
    async with aiosqlite.connect("bot.db") as db:
        async with db.execute("SELECT id, name, price FROM products") as cursor:
            products = await cursor.fetchall()

    if not products:
        await message.answer("Mahsulot yo'q.")
        return

    text = ""
    for p in products:
        text += f"{p[0]}. {p[1]} - {p[2]} so'm\n"

    await message.answer(text)

@dp.message(F.text == "❌ Mahsulot o'chirish")
async def delete_products(message: Message):
    async with aiosqlite.connect("bot.db") as db:
        async with db.execute("SELECT id, name FROM products") as cursor:
            products = await cursor.fetchall()

    if not products:
        await message.answer("O'chirish uchun mahsulot yo'q.")
        return

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=p[1], callback_data=f"del_{p[0]}")]
            for p in products
        ]
    )

    await message.answer("O'chirish uchun tanlang:", reply_markup=keyboard)

@dp.callback_query(F.data.startswith("del_"))
async def delete_product(callback: CallbackQuery):
    product_id = int(callback.data.split("_")[1])
    async with aiosqlite.connect("bot.db") as db:
        await db.execute("DELETE FROM products WHERE id = ?", (product_id,))
        await db.commit()
    await callback.message.edit_text("Mahsulot o'chirildi ✅")

# ================= ORDER =================

@dp.message(F.text == "🛒 Buyurtma berish")
async def show_products(message: Message):
    async with aiosqlite.connect("bot.db") as db:
        async with db.execute("SELECT id, name, price FROM products") as cursor:
            products = await cursor.fetchall()

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"{p[1]} - {p[2]} so'm", callback_data=f"order_{p[0]}")]
            for p in products
        ]
    )

    await message.answer("Mahsulotni tanlang:", reply_markup=keyboard)

@dp.callback_query(F.data.startswith("order_"))
async def order_product(callback: CallbackQuery, state: FSMContext):
    product_id = int(callback.data.split("_")[1])
    await state.update_data(product_id=product_id)
    await callback.message.answer("Necha dona yoki kg yozing:")
    await state.set_state(OrderState.quantity)

@dp.message(OrderState.quantity)
async def get_quantity(message: Message, state: FSMContext):
    data = await state.get_data()
    quantity = message.text

    async with aiosqlite.connect("bot.db") as db:
        async with db.execute("SELECT name FROM products WHERE id = ?", (data["product_id"],)) as cursor:
            product = await cursor.fetchone()

    order_text = f"""
🆕 Yangi buyurtma!

📦 Mahsulot: {product[0]}
🔢 Miqdor: {quantity}

👤 Buyurtmachi:
Ism: {message.from_user.first_name}
Username: @{message.from_user.username}
ID: {message.from_user.id}
"""

    await bot.send_message(ADMIN_ID, order_text)
    await message.answer("Buyurtma yuborildi ✅")
    await state.clear()

# ================= RUN =================

async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":

    asyncio.run(main())
