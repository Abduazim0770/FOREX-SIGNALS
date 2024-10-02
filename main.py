import sqlite3
from datetime import datetime, timedelta
import asyncio

from aiogram import Bot, Dispatcher
from aiogram import types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor
from aiogram.utils.exceptions import BotBlocked

# Bot tokeni va admin ID si
API_TOKEN = '7746093294:AAH1WH6rLnyKgPUyz2Z-5wAsmj8VYNZJoNo'
ADMIN_ID = 5699779185

# Bot va Dispatcher yaratish
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
dp.middleware.setup(LoggingMiddleware())

# Bazaga ulanish
conn = sqlite3.connect('forex_signals.db')
cursor = conn.cursor()

# VIP foydalanuvchilar ro'yxatini yaratish
cursor.execute("""CREATE TABLE IF NOT EXISTS vip_users (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER UNIQUE,
                    subscription_date DATE,
                    duration INTEGER
                )""")
conn.commit()

# Admin menyusi tugmalari
admin_keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
admin_keyboard.add(KeyboardButton("📊 SIGNAL BERISH"), KeyboardButton("➕ ODAM QO‘SHISH"))
admin_keyboard.add(KeyboardButton("📋 MALUMOTLAR"))

# Foydalanuvchi menyusi tugmasi
user_keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
user_keyboard.add(KeyboardButton("💎 VIP OBUNA SOTIB OLISH"))

# VIP obuna sotib olish uchun inline tugmalar
vip_buttons = InlineKeyboardMarkup(row_width=3)
vip_buttons.add(
    InlineKeyboardButton("1 - OY", callback_data='1_oy'),
    InlineKeyboardButton("2 - OY", callback_data='2_oy'),
    InlineKeyboardButton("3 - OY", callback_data='3_oy')
)

# VIP narxlar
prices = {
    "1_oy": 15000,
    "2_oy": 25000,
    "3_oy": 40000
}


# Holatlar uchun state
class SignalState(StatesGroup):
    signal = State()


class AddUserState(StatesGroup):
    user_id = State()


# Start kommandasi
@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer("Siz adminsiz! 👨‍💼", reply_markup=admin_keyboard)
    else:
        await message.answer("Salom FOREX - SIGNALS botiga xush kelibsiz! 🤗", reply_markup=user_keyboard)


# Adminning SIGNAL BERISH tugmasini bosishi
@dp.message_handler(Text(equals='📊 SIGNAL BERISH'), state=None)
async def send_signal(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer("Signal yozing: ✍️")
        await SignalState.signal.set()


# Signalni qabul qilish va VIP foydalanuvchilarga yuborish
@dp.message_handler(state=SignalState.signal)
async def handle_signal(message: types.Message, state: FSMContext):
    if message.from_user.id == ADMIN_ID:
        signal_text = message.text
        cursor.execute("SELECT user_id FROM vip_users")
        vip_users = cursor.fetchall()

        for user in vip_users:
            try:
                await bot.send_message(user[0], f"Yangi signal: {signal_text} 📈")
            except BotBlocked:
                # Foydalanuvchi botni bloklagan bo'lsa, bazadan o'chirib tashlaymiz
                cursor.execute("DELETE FROM vip_users WHERE user_id = ?", (user[0],))
                conn.commit()

        await state.finish()
        await message.answer("Signal muvaffaqiyatli yuborildi! ✅")


# ODAM QO‘SHISH tugmasini bosganda
@dp.message_handler(Text(equals='➕ ODAM QO‘SHISH'), state=None)
async def add_user(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer("Qo‘shmoqchi bo‘lgan odamingizning ID raqamini yozing: 🔢")
        await AddUserState.user_id.set()


# Foydalanuvchini ID orqali qo‘shish va bazaga yozish
@dp.message_handler(state=AddUserState.user_id)
async def handle_user_add(message: types.Message, state: FSMContext):
    if message.from_user.id == ADMIN_ID:
        try:
            user_id = int(message.text)
            current_date = datetime.now().date()

            # Foydalanuvchi mavjudligini tekshirish
            cursor.execute("SELECT user_id FROM vip_users WHERE user_id = ?", (user_id,))
            if cursor.fetchone() is not None:
                await message.answer(f"Foydalanuvchi {user_id} allaqachon mavjud! 🚫")
            else:
                # Yangi foydalanuvchini qo'shish va obunani belgilang
                cursor.execute("INSERT INTO vip_users (user_id, subscription_date, duration) VALUES (?, ?, ?)",
                               (user_id, current_date, 3))  # 3 oylik qo'shish (bu misolda)

                conn.commit()

                await bot.send_message(user_id, "Siz botdan foydalanish huquqiga egasiz! 🆓")
                await message.answer(f"Foydalanuvchi {user_id} muvaffaqiyatli qo‘shildi! ✔️")
        except ValueError:
            await message.answer("Iltimos, faqat raqam kiriting. 🚫")
        await state.finish()


# Foydalanuvchi VIP OBUNA SOTIB OLISH tugmasini bosganda
@dp.message_handler(Text(equals='💎 VIP OBUNA SOTIB OLISH'))
async def vip_purchase(message: types.Message):
    await message.answer("Necha oylik VIP obuna olmoqchisiz? Tanlang:", reply_markup=vip_buttons)


# VIP obuna tanlash uchun inline tugmalari
@dp.callback_query_handler(lambda c: c.data in ['1_oy', '2_oy', '3_oy'])
async def process_callback_button(callback_query: types.CallbackQuery):
    plan = callback_query.data
    price = prices[plan]
    await bot.send_message(callback_query.from_user.id,
                           f"Siz {plan.replace('_', ' - ')} VIP obunani tanladingiz.\nNarxi: {price} so‘m\n\nSHU KARTA RAQAMIGA PUL TASHLANG: 'KARTA RAQAM'\n\nCHEK ADMINGA TASHLANG",
                           reply_markup=InlineKeyboardMarkup().add(
                               InlineKeyboardButton("ADMIN", url='https://t.me/a_rixsiyev')))


# Obuna muddati tugagan foydalanuvchilarni tekshirish va o'chirish
async def check_subscriptions():
    current_date = datetime.now().date()
    cursor.execute("SELECT user_id, subscription_date, duration FROM vip_users")
    vip_users = cursor.fetchall()

    for user_id, sub_date, duration in vip_users:
        sub_date = datetime.strptime(sub_date, '%Y-%m-%d').date()  # stringni date ga o'tkazish
        end_date = sub_date + timedelta(days=duration * 30)

        if current_date > end_date:
            cursor.execute("DELETE FROM vip_users WHERE user_id = ?", (user_id,))
            conn.commit()
            await bot.send_message(user_id,
                                   f"SIZ SOTIB OLGAN {duration} - OYLIK OBUNA VAQTI TUGADI. YANA TO‘LOV QILIB AKTIV QILSANGIZ BO‘LADI",
                                   reply_markup=InlineKeyboardMarkup().add(
                                       InlineKeyboardButton("ADMIN", url='https://t.me/a_rixsiyev')))


# Admin menyusidagi MALUMOTLAR tugmasi
# Admin menyusidagi MALUMOTLAR tugmasi
@dp.message_handler(Text(equals='📋 MALUMOTLAR'), state=None)
async def show_users(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        cursor.execute("SELECT user_id, subscription_date, duration FROM vip_users")
        vip_users = cursor.fetchall()

        if vip_users:
            response = "VIP foydalanuvchilar:\n"
            for user_id, sub_date, duration in vip_users:
                sub_date = datetime.strptime(sub_date, '%Y-%m-%d').date()  # stringni date ga o'tkazish
                end_date = sub_date + timedelta(days=duration * 30)

                # Username olish (agar mavjud bo'lsa)
                user = await bot.get_chat(user_id)
                username = user.username if user.username else "N/A"

                response += (
                    f"1. ID: {user_id}\n"
                    f"2. USERNAME: {username}\n"
                    f"3. NECHI OYLIK VIP OBUNA SOTIB OLGANLIGI: {duration}-OY\n"
                    f"4. OLgan sanasi: {sub_date}\n"
                    f"5. Tugash sanasi: {end_date}\n\n"
                )

            await message.answer(response)
        else:
            await message.answer("Hozirda VIP foydalanuvchilar yo'q. 🚫")


# Botni ishga tushirish
async def scheduler():
    while True:
        await check_subscriptions()
        await asyncio.sleep(3600)  # Har bir soatdan so'ng qaytadan tekshirish


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.create_task(scheduler())
    executor.start_polling(dp, skip_updates=True)
