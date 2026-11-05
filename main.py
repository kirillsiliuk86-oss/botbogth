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

# --- СОСТОЯНИЯ (FSM) ---
class UserStates(StatesGroup):
    waiting_for_nickname = State()
    waiting_for_city = State()
    waiting_for_new_nick = State()
    waiting_for_pay_amount = State()
    waiting_for_bank_amount = State()

# ================= СТАРТ И РЕГИСТРАЦИЯ =================
@dp.message(Command("start"))
async def start(message: Message, state: FSMContext):
    u = get_user(message.from_user.id)
    if u.is_registered == 0:
        await message.answer("👋 Добро пожаловать в **CITY LIFE RPG**!\nДавай создадим твоего персонажа. Введи свой **игровой ник**:", parse_mode="Markdown")
        await state.set_state(UserStates.waiting_for_nickname)
    else:
        await message.answer(f"С возвращением, **{u.nickname}**!", reply_markup=main_menu(), parse_mode="Markdown")

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
    
    # Проверка на платный город
    if CITIES[city]["price"] > u.balance:
        await call.answer(f"❌ Для переезда в {city} нужно {CITIES[city]['price']}$", show_alert=True)
        return

    u.balance -= CITIES[city]["price"]
    u.city = city
    u.is_registered = 1
    session.commit()
    session.close()
    
    await call.message.edit_text(f"✅ Регистрация завершена!\nТвой ник: **{u.nickname}**\nГород: **{city}**\nБонус: {CITIES[city]['bonus']}", parse_mode="Markdown")
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
    
    jail = "🚔 **В ТЮРЬМЕ!**\n" if u.jail_time > int(time.time()) else ""
    wanted = f"🚨 **В РОЗЫСКЕ**\n" if u.wanted > 0 else ""
    vip = "👑 VIP\n" if u.vip > int(time.time()) else ""

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
    await call.message.edit_text(text, reply_markup=back_kb(), parse_mode="Markdown")
    session.close()

# ================= НАСТРОЙКИ =================
@dp.callback_query(F.data == "settings")
async def settings(call: CallbackQuery):
    await call.message.edit_text("⚙️ **Настройки**", reply_markup=settings_menu(), parse_mode="Markdown")

@dp.callback_query(F.data == "change_nick")
async def change_nick(call: CallbackQuery, state: FSMContext):
    await call.message.edit_text("Введи новый ник:")
    await state.set_state(UserStates.waiting_for_new_nick)

@dp.message(UserStates.waiting_for_new_nick)
async def set_new_nick(message: Message, state: FSMContext):
    session = get_db()
    u = session.query(User).filter_by(id=message.from_user.id).first()
    u.nickname = message.text
    session.commit()
    session.close()
    await message.answer(f"✅ Ник изменен на **{message.text}**!", parse_mode="Markdown")
    await state.clear()
    await message.answer("🌆 Главное меню:", reply_markup=main_menu())

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
        
    if sender.balance < amount:
        session.close()
        return await message.answer("❌ Недостаточно денег.")
        
    if amount <= 0:
        session.close()
        return await message.answer("❌ Сумма должна быть больше нуля.")

    # Комиссия банка 2%
    commission = int(amount * 0.02)
    total_deduction = amount + commission

    if sender.balance < total_deduction:
        session.close()
        return await message.answer(f"❌ Не хватает денег с учетом комиссии 2% ({commission}$).")

    sender.balance -= total_deduction
    receiver.balance += amount
    session.commit()
    session.close()
    
    await message.answer(f"💸 Перевод успешен!\nТы отправил **{amount}$** игроку {receiver.nickname}.\nКомиссия банка: {commission}$", parse_mode="Markdown")

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
        await call.answer(f"💼 Отработал ({job_name}) и получил {pay} $!", show_alert=True)
    else:
        await call.answer("❌ Не хватает энергии!", show_alert=True)
    session.close()

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
        await call.answer(f"✅ Куплен {biz_name}!", show_alert=True)
    else:
        await call.answer("❌ Не хватает денег!", show_alert=True)
    session.close()

# ================= МАГАЗИН =================
@dp.callback_query(F.data == "shop_menu")
async def shop_menu_cb(call: CallbackQuery):
    await call.message.edit_text("🛒 **Магазин**", reply_markup=shop_menu(), parse_mode="Markdown")

@dp.callback_query(F.data == "weapon_shop")
async def weapon_shop_cb(call: CallbackQuery):
    await call.message.edit_text("🔫 **Оружейный магазин**\nБонус влияет на победу в PvP!", reply_markup=weapon_shop(), parse_mode="Markdown")

@dp.callback_query(F.data.startswith("wep_buy_"))
async def buy_weapon(call: CallbackQuery):
    wep_name = call.data.split("_")[2]
    price, bonus = WEAPONS[wep_name]
    
    session = get_db()
    u = session.query(User).filter_by(id=call.from_user.id).first()
    
    if wep_name == "Золотой АК" or wep_name == "Меч Самурая":
        if u.donate_bal >= price:
            u.donate_bal -= price
            u.weapon = wep_name
            session.commit()
            await call.answer(f"🔥 Куплен {wep_name}!", show_alert=True)
        else:
            await call.answer("❌ Нужны кристаллы!", show_alert=True)
    else:
        if u.balance >= price:
            u.balance -= price
            u.weapon = wep_name
            session.commit()
            await call.answer(f"🔫 Куплен {wep_name}!", show_alert=True)
        else:
            await call.answer("❌ Не хватает денег!", show_alert=True)
    session.close()

# ================= АВТОСАЛОН =================
@dp.callback_query(F.data == "garage_menu")
async def garage_cb(call: CallbackQuery):
    await call.message.edit_text("🚗 **Автосалон**\nМашины помогают сбегать от полиции.", reply_markup=garage_menu(), parse_mode="Markdown")

@dp.callback_query(F.data.startswith("car_buy_"))
async def buy_car(call: CallbackQuery):
    car_name = call.data.split("_")[2]
    price, bonus = CARS[car_name]
    
    session = get_db()
    u = session.query(User).filter_by(id=call.from_user.id).first()
    
    if u.balance >= price:
        u.balance -= price
        u.car = car_name
        session.commit()
        await call.answer(f"🚗 Куплена {car_name}!", show_alert=True)
    else:
        await call.answer("❌ Не хватает денег!", show_alert=True)
    session.close()

# ================= НЕДВИЖИМОСТЬ =================
@dp.callback_query(F.data == "estate_menu")
async def estate_cb(call: CallbackQuery):
    await call.message.edit_text("🏠 **Недвижимость**\nУлучшает восстановление энергии.", reply_markup=estate_menu(), parse_mode="Markdown")

@dp.callback_query(F.data.startswith("estate_buy_"))
async def buy_estate(call: CallbackQuery):
    est_name = call.data.split("_")[2]
    price, bonus = REAL_ESTATE[est_name]
    
    session = get_db()
    u = session.query(User).filter_by(id=call.from_user.id).first()
    
    if u.balance >= price:
        u.balance -= price
        u.estate = est_name
        session.commit()
        await call.answer(f"🏠 Куплено: {est_name}!", show_alert=True)
    else:
        await call.answer("❌ Не хватает денег!", show_alert=True)
    session.close()

# ================= БАНК =================
@dp.callback_query(F.data == "bank_menu")
async def bank_cb(call: CallbackQuery):
    await call.message.edit_text("🏦 **Банк**\nДепозит приносит 5% в час.", reply_markup=bank_menu(), parse_mode="Markdown")

@dp.callback_query(F.data == "bank_deposit")
async def bank_dep(call: CallbackQuery, state: FSMContext):
    await call.message.edit_text("Введи сумму для пополнения депозита:")
    await state.set_state(UserStates.waiting_for_bank_amount)

@dp.message(UserStates.waiting_for_bank_amount)
async def process_bank_dep(message: Message, state: FSMContext):
    try:
        amount = int(message.text)
        if amount <= 0: raise ValueError
    except:
        return await message.answer("❌ Введи число больше нуля.")
        
    session = get_db()
    u = session.query(User).filter_by(id=message.from_user.id).first()
    
    if u.balance >= amount:
        u.balance -= amount
        u.bank_deposit += amount
        session.commit()
        await message.answer(f"🏦 Ты положил {amount}$ на депозит.")
    else:
        await message.answer("❌ Не хватает денег.")
    session.commit()
    session.close()
    await state.clear()
    await message.answer("🌆 Главное меню:", reply_markup=main_menu())

# ================= КРИМИНАЛ =================
@dp.callback_query(F.data == "crime_menu")
async def crime_menu_cb(call: CallbackQuery):
    await call.message.edit_text("💀 **Криминал**\n/rob - ограбить игрока (Reply)\n/become_criminal - стать бандитом\n/rob_bank - ограбить банк", reply_markup=back_kb(), parse_mode="Markdown")

@dp.message(Command("become_criminal"))
async def become_criminal(message: Message):
    session = get_db()
    u = session.query(User).filter_by(id=message.from_user.id).first()
    u.role = "Преступник"
    u.gov_rank = "Нет"
    session.commit()
    session.close()
    await message.answer("💀 Теперь ты преступник!")

@dp.message(Command("rob"))
async def rob_player(message: Message):
    if not message.reply_to_message: return await message.answer("❌ Ответь на сообщение!")
    session = get_db()
    robber = session.query(User).filter_by(id=message.from_user.id).first()
    victim = session.query(User).filter_by(id=message.reply_to_message.from_user.id).first()
    
    if robber.role != "Преступник" or robber.energy < 20: 
        session.close()
        return await message.answer("❌ Ты не бандит или нет энергии (20).")
    
    robber.energy -= 20
    # Бонус Токио
    chance = 0.5 + (0.2 if robber.city == "Токио" else 0)
    
    if random.random() < chance:
        loot = int(victim.balance * 0.2)
        if loot < 100: loot = 100
        victim.balance -= loot
        robber.balance += loot
        robber.wanted += 1
        await message.answer(f"💰 Ограбление удалось! Ты забрал {loot} $.")
    else:
        robber.wanted += 1
        await message.answer("🚨 Ограбление провалилось!")
    session.commit()
    session.close()

@dp.message(Command("rob_bank"))
async def rob_bank(message: Message):
    session = get_db()
    u = session.query(User).filter_by(id=message.from_user.id).first()
    if u.role != "Преступник": 
        session.close()
        return await message.answer("❌ Ты не преступник!")
    
    chance = 0.4 + (0.2 if u.city == "Токио" else 0)
    
    if random.random() < chance:
        loot = random.randint(10000, 50000)
        u.balance += loot
        u.wanted += 2
        await message.answer(f"💰 Ты ограбил банк и забрал {loot} $!")
    else:
        u.jail_time = int(time.time()) + 600
        await message.answer("🚔 Тебя поймали! 10 минут тюрьмы.")
    session.commit()
    session.close()

# ================= МВД =================
@dp.callback_query(F.data == "police_menu")
async def police_menu_cb(call: CallbackQuery):
    await call.message.edit_text("🚔 **Полиция**\n/arrest - арестовать (Reply)\n/pardon - снять розыск (5000$)", reply_markup=back_kb(), parse_mode="Markdown")

@dp.message(Command("arrest"))
async def arrest(message: Message):
    if not message.reply_to_message: return await message.answer("❌ Ответь на сообщение!")
    session = get_db()
    cop = session.query(User).filter_by(id=message.from_user.id).first()
    crim = session.query(User).filter_by(id=message.reply_to_message.from_user.id).first()
    
    if cop.gov_rank not in ["Министр МВД", "Премьер", "Президент"]:
        session.close()
        return await message.answer("❌ У тебя нет полномочий МВД!")
        
    crim.jail_time = int(time.time()) + 600
    crim.role = "Гражданин"
    crim.wanted = 0
    fine = crim.balance // 2
    crim.balance -= fine
    cop.balance += fine
    session.commit()
    session.close()
    await message.answer(f"🚔 Арестован! Штраф {fine} $ твой.")

@dp.message(Command("pardon"))
async def pardon(message: Message):
    if not message.reply_to_message: return await message.answer("❌ Ответь на сообщение!")
    session = get_db()
    u = session.query(User).filter_by(id=message.from_user.id).first()
    target = session.query(User).filter_by(id=message.reply_to_message.from_user.id).first()
    
    if u.gov_rank not in ["Министр МВД", "Премьер", "Президент"]:
        session.close()
        return await message.answer("❌ Только МВД может снимать розыск!")
    if u.balance < 5000:
        session.close()
        return await message.answer("❌ Нужно 5000$ для бумаг.")
        
    u.balance -= 5000
    target.wanted = 0
    session.commit()
    session.close()
    await message.answer(f"📄 Розыск снят!")

# ================= ГОСУДАРСТВО =================
@dp.callback_query(F.data == "gov_menu")
async def gov_menu_cb(call: CallbackQuery):
    session = get_db()
    u = session.query(User).filter_by(id=call.from_user.id).first()
    text = f"🏛 **Гос-во**\nДолжность: **{u.gov_rank}**"
    await call.message.edit_text(text, reply_markup=gov_menu(u.gov_rank), parse_mode="Markdown")
    session.close()

@dp.callback_query(F.data == "gov_up")
async def gov_up(call: CallbackQuery):
    session = get_db()
    u = session.query(User).filter_by(id=call.from_user.id).first()
    keys = list(GOV_RANKS.keys())
    next_rank = keys[0] if u.gov_rank == "Нет" else keys[keys.index(u.gov_rank) + 1]
    price, salary = GOV_RANKS[next_rank]
    
    if u.balance >= price:
        u.balance -= price
        u.gov_rank = next_rank
        u.role = "Госслужащий"
        session.commit()
        await call.answer(f"🎉 Ты теперь {next_rank}!", show_alert=True)
    else:
        await call.answer("❌ Не хватает денег!", show_alert=True)
    session.close()

# ================= ДОНАТ =================
@dp.callback_query(F.data == "donate_menu")
async def donate_menu_cb(call: CallbackQuery):
    await call.message.edit_text("💎 **Донат-магазин**\nПокупка через админа (тест).", reply_markup=donate_menu(), parse_mode="Markdown")

@dp.callback_query(F.data.startswith("donate_"))
async def donate_buy(call: CallbackQuery):
    amount = int(call.data.split("_")[1])
    session = get_db()
    u = session.query(User).filter_by(id=call.from_user.id).first()
    u.donate_bal += amount
    session.commit()
    session.close()
    await call.answer(f"✅ Начислено {amount} кристаллов!", show_alert=True)

# ================= ТОПЫ =================
@dp.callback_query(F.data == "top_menu")
async def top_menu_cb(call: CallbackQuery):
    await call.message.edit_text("🏆 **Топы**", reply_markup=top_menu(), parse_mode="Markdown")

@dp.callback_query(F.data == "top_money")
async def top_money(call: CallbackQuery):
    session = get_db()
    top = session.query(User).order_by(User.balance.desc()).limit(10).all()
    text = "🏆 **Топ-10 богачей:**\n\n"
    for i, u in enumerate(top, 1):
        text += f"{i}. {u.nickname} - {u.balance} $\n"
    await call.message.edit_text(text, reply_markup=top_menu(), parse_mode="Markdown")
    session.close()

# ================= ФОНОВАЯ ЗАДАЧА =================
async def background_loop():
    while True:
        await asyncio.sleep(60)
        session = get_db()
        users = session.query(User).all()
        for u in users:
            # Энергия (с бонусом жилья)
            if u.energy < 100:
                regen = 10 + REAL_ESTATE.get(u.estate, (0, 0))[1]
                u.energy += regen
                if u.energy > 100: u.energy = 100
            
            # Зарплата
            if u.gov_rank != "Нет":
                salary = GOV_RANKS.get(u.gov_rank, (0, 0))[1]
                u.balance += salary
            
            # Бизнес
            if u.business != "Нет":
                base_inc = BUSINESSES.get(u.business, (0, 0))[1]
                if u.city == "Дубай": base_inc = int(base_inc * 1.3)
                u.balance += base_inc
                
            # Банковский процент (5% в час)
            if u.bank_deposit > 0:
                # Начисляем раз в 60 минут, значит 5% / 60 = ~0.08% в минуту
                # Упрощенно: начисляем 5% раз в 60 циклов
                if random.randint(1, 60) == 1:
                    interest = int(u.bank_deposit * 0.05)
                    u.bank_deposit += interest

        session.commit()
        session.close()

async def main():
    asyncio.create_task(background_loop())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
