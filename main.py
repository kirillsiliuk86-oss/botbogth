import asyncio
import logging
import random
import time
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# Импортируем наши модули
from config import *
from database import get_db, get_user, User, Session
from keyboards import *

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

class UserStates(StatesGroup):
    waiting_for_nickname = State()
    waiting_for_city = State()
    waiting_for_new_nick = State()
    waiting_for_bank_amount = State()

# ================= СТАРТ И РЕГИСТРАЦИЯ =================
@dp.message(Command("start"))
async def start(message: Message, state: FSMContext):
    session = get_db()
    u = session.query(User).filter_by(id=message.from_user.id).first()
    
    if not u:
        u = User(id=message.from_user.id)
        session.add(u)
        session.commit()
        
    if u.is_registered == 0:
        await message.answer("👋 Добро пожаловать в **CITY LIFE RPG**!\nДавай создадим твоего персонажа. Введи свой **игровой ник**:", parse_mode="Markdown")
        await state.set_state(UserStates.waiting_for_nickname)
    else:
        await message.answer(f"С возвращением, **{u.nickname}**!", reply_markup=main_menu(), parse_mode="Markdown")
    session.close()

@dp.message(UserStates.waiting_for_nickname)
async def process_nick(message: Message, state: FSMContext):
    session = get_db()
    u = session.query(User).filter_by(id=message.from_user.id).first()
    u.nickname = message.text
    session.commit()
    session.close()
    
    kb = [
        [InlineKeyboardButton(text="Москва", callback_data="city_Москва")],
        [InlineKeyboardButton(text="Санкт-Петербург", callback_data="city_Санкт-Петербург")],
        [InlineKeyboardButton(text="Дубай (50к)", callback_data="city_Дубай")],
        [InlineKeyboardButton(text="Токио (150к)", callback_data="city_Токио")]
    ]
    await message.answer("Отлично! Теперь выбери свой город (у каждого свои бонусы):", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await state.set_state(UserStates.waiting_for_city)

@dp.callback_query(UserStates.waiting_for_city, F.data.startswith("city_"))
async def process_city(call: CallbackQuery, state: FSMContext):
    city = call.data.split("_")[1]
    session = get_db()
    u = session.query(User).filter_by(id=call.from_user.id).first()
    
    if CITIES[city]["price"] > u.balance:
        await call.answer(f"❌ Для переезда в {city} нужно {CITIES[city]['price']}$", show_alert=True)
        session.close()
        return

    u.balance -= CITIES[city]["price"]
    u.city = city
    u.is_registered = 1
    session.commit()
    
    nickname = u.nickname # Сохраняем в переменную до закрытия базы
    session.close()
    
    await call.message.edit_text(f"✅ Регистрация завершена!\nТвой ник: **{nickname}**\nГород: **{city}**\nБонус: {CITIES[city]['bonus']}", parse_mode="Markdown")
    await state.clear()
    await call.message.answer("🌆 Главное меню:", reply_markup=main_menu())

@dp.callback_query(F.data == "back")
async def back(call: CallbackQuery):
    await call.message.edit_text("🌆 **Главное меню**", reply_markup=main_menu(), parse_mode="Markdown")

# ================= ПРОФИЛЬ =================
@dp.callback_query(F.data == "profile")
async def profile(call: CallbackQuery):
    session = get_db()
    u = session.query(User).filter_by(id=call.from_user.id).first()
    
    if not u:
        session.close()
        return await call.answer("Сначала напиши /start")

    jail = "🚔 **В ТЮРЬМЕ!**\n" if u.jail_time > int(time.time()) else ""
    wanted = f"🚨 **В РОЗЫСКЕ**\n" if u.wanted > 0 else ""
    vip = "👑 VIP\n" if u.vip > int(time.time()) else ""

    # Сохраняем все данные в переменные ДО закрытия базы
    text = (f"👤 **Досье: {u.nickname}**\n{jail}{wanted}{vip}"
            f"🏙 Город: {u.city}\n"
            f"💰 Баланс: {u.balance} $\n"
            f"🏦 В банке: {u.bank_deposit} $\n"
            f"💎 Кристаллы: {u.donate_bal}\n"
            f"🎖 Статус: {u.role}\n"
            f"🏛 Должность: {u.gov_rank}\n"
            f"💼 Работа: {u.job}\n"
            f"🏢 Бизнес: {u.business}\n"
            f"🔫 Оружие: {u.weapon}\n"
            f"🚗 Машина: {u.car}\n"
            f"🏠 Жилье: {u.estate}\n"
            f"⚡ Энергия: {u.energy}/100")
    
    session.close() # Закрываем ТОЛЬКО после того, как собрали текст
    await call.message.edit_text(text, reply_markup=back_kb(), parse_mode="Markdown")

# ================= РАБОТЫ =================
@dp.callback_query(F.data == "jobs_menu")
async def jobs_menu(call: CallbackQuery):
    await call.message.edit_text("💼 **Биржа труда**", reply_markup=job_categories(), parse_mode="Markdown")

@dp.callback_query(F.data.startswith("jobcat_"))
async def jobs_list_cb(call: CallbackQuery):
    cat = call.data.split("_")[1]
    await call.message.edit_text("Выбери работу:", reply_markup=jobs_list(cat))

@dp.callback_query(F.data.startswith("work_"))
async def do_job(call: CallbackQuery):
    job_name = call.data.split("_")[1]
    en_cost, pay = JOBS[job_name]
    
    session = get_db()
    u = session.query(User).filter_by(id=call.from_user.id).first()
    
    if u.jail_time > int(time.time()): 
        session.close()
        return await call.answer("❌ Ты в тюрьме!", show_alert=True)
    
    if u.city == "Санкт-Петербург": en_cost = int(en_cost * 0.9)
    if u.city == "Москва": pay = int(pay * 1.2)

    if u.energy >= en_cost:
        u.energy -= en_cost
        u.balance += pay
        u.job = job_name
        session.commit()
        session.close()
        await call.answer(f"💼 Отработал ({job_name}) и получил {pay} $!", show_alert=True)
    else:
        session.close()
        await call.answer("❌ Не хватает энергии!", show_alert=True)

# ================= БИЗНЕСЫ =================
@dp.callback_query(F.data == "biz_menu")
async def biz_menu(call: CallbackQuery):
    await call.message.edit_text("🏢 **Бизнес-центр**", reply_markup=biz_categories(), parse_mode="Markdown")

@dp.callback_query(F.data.startswith("bizcat_"))
async def biz_list_cb(call: CallbackQuery):
    cat = call.data.split("_")[1]
    await call.message.edit_text("Выбери бизнес:", reply_markup=biz_list(cat))

@dp.callback_query(F.data.startswith("biz_buy_"))
async def buy_biz(call: CallbackQuery):
    biz_name = call.data.split("_")[2]
    price, income = BUSINESSES[biz_name]
    
    session = get_db()
    u = session.query(User).filter_by(id=call.from_user.id).first()
    
    if u.business != "Нет": 
        session.close()
        return await call.answer("❌ У тебя уже есть бизнес!", show_alert=True)
        
    if u.balance >= price:
        u.balance -= price
        u.business = biz_name
        session.commit()
        session.close()
        await call.answer(f"✅ Куплен {biz_name}!", show_alert=True)
    else:
        session.close()
        await call.answer("❌ Не хватает денег!", show_alert=True)

# ================= ПЕРЕВОД ДЕНЕГ =================
@dp.message(Command("pay"))
async def pay_command(message: Message):
    if not message.reply_to_message:
        return await message.answer("❌ Ответь на сообщение игрока, которому хочешь перевести деньги.")
    
    try:
        amount = int(message.text.split()[1])
    except:
        return await message.answer("❌ Напиши сумму: `/pay 1000`", parse_mode="Markdown")
        
    session = get_db()
    sender = session.query(User).filter_by(id=message.from_user.id).first()
    receiver = session.query(User).filter_by(id=message.reply_to_message.from_user.id).first()
    
    if not receiver:
        session.close()
        return await message.answer("❌ Этот игрок еще не зарегистрирован.")
        
    if sender.balance < amount or amount <= 0:
        session.close()
        return await message.answer("❌ Недостаточно денег или неверная сумма.")

    commission = int(amount * 0.02)
    total_deduction = amount + commission

    if sender.balance < total_deduction:
        session.close()
        return await message.answer(f"❌ Не хватает денег с учетом комиссии 2% ({commission}$).")

    sender.balance -= total_deduction
    receiver.balance += amount
    
    rec_name = receiver.nickname
    
    session.commit()
    session.close()
    
    await message.answer(f"💸 Перевод успешен!\nТы отправил **{amount}$** игроку {rec_name}.\nКомиссия банка: {commission}$", parse_mode="Markdown")

# ================= ФОНОВАЯ ЗАДАЧА =================
async def background_loop():
    while True:
        await asyncio.sleep(60)
        session = get_db()
        users = session.query(User).all()
        for u in users:
            if u.energy < 100:
                regen = 10 + REAL_ESTATE.get(u.estate, (0, 0))[1]
                u.energy += regen
                if u.energy > 100: u.energy = 100
            
            if u.gov_rank != "Нет":
                salary = GOV_RANKS.get(u.gov_rank, (0, 0))[1]
                u.balance += salary
            
            if u.business != "Нет":
                base_inc = BUSINESSES.get(u.business, (0, 0))[1]
                if u.city == "Дубай": base_inc = int(base_inc * 1.3)
                u.balance += base_inc
        session.commit()
        session.close()

async def main():
    asyncio.create_task(background_loop())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
