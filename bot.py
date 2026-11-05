import asyncio
import logging
import random
import time
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from sqlalchemy import create_engine, Column, Integer, String, BigInteger
from sqlalchemy.orm import declarative_base, sessionmaker

# ================= НАСТРОЙКИ =================
BOT_TOKEN = "8996438777:AAFSiI1XaFY5cEa9d9Lr0fb0m0MtRrBq2SA"
# ============================================

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- БАЗА ДАННЫХ ---
engine = create_engine('sqlite:///city_gov.db', connect_args={"check_same_thread": False})
Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(BigInteger, primary_key=True)
    balance = Column(Integer, default=5000)
    role = Column(String, default="Гражданин") # Гражданин, Преступник, Госслужащий
    gov_rank = Column(String, default="Нет")   
    job = Column(String, default="Безработный")
    business = Column(String, default="Нет")
    energy = Column(Integer, default=100)
    jail_time = Column(Integer, default=0)
    wanted = Column(Integer, default=0) # Уровень розыска (сколько раз грабил)

Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

def get_db(): return Session()

def get_user(user_id):
    session = get_db()
    user = session.query(User).filter_by(id=user_id).first()
    if not user:
        user = User(id=user_id)
        session.add(user)
        session.commit()
    session.close()
    return user

# --- ИЕРАРХИЯ ВЛАСТИ (Для госслужащих) ---
GOV_RANKS = {
    "Клерк Мэрии": (10000, 500), "Специалист Мэрии": (50000, 1500),
    "Начальник Отдела": (200000, 5000), "Вице-Мэр": (1000000, 15000),
    "Мэр Города": (5000000, 50000), "Министр Финансов": (10000000, 100000),
    "Министр Внутренних Дел": (15000000, 150000), "Премьер-Министр": (25000000, 250000),
    "Президент": (50000000, 500000)
}

# --- КЛАВИАТУРЫ ---
def main_menu():
    kb = [
        [InlineKeyboardButton(text="👤 Профиль", callback_data="profile"), InlineKeyboardButton(text="🏛 Гос. Служба", callback_data="gov_menu")],
        [InlineKeyboardButton(text="🚔 МВД (Полиция)", callback_data="police_menu"), InlineKeyboardButton(text="💀 Криминал", callback_data="crime_menu")],
        [InlineKeyboardButton(text="🏆 Топ богачей", callback_data="top")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def back_kb(): return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="back")]])

@dp.message(Command("start"))
async def start(message: Message):
    get_user(message.from_user.id)
    await message.answer("🌆 **Добро пожаловать в CITY PVP!** 🌆\nТеперь бандиты могут грабить игроков, а полиция их ловить!", reply_markup=main_menu(), parse_mode="Markdown")

@dp.callback_query(F.data == "back")
async def back(call: CallbackQuery):
    await call.message.edit_text("🌆 **Главное меню**", reply_markup=main_menu(), parse_mode="Markdown")

# --- ПРОФИЛЬ ---
@dp.callback_query(F.data == "profile")
async def profile(call: CallbackQuery):
    session = get_db()
    u = session.query(User).filter_by(id=call.from_user.id).first()
    
    jail_status = "🚔 **В ТЮРЬМЕ!**\n" if u.jail_time > int(time.time()) else ""
    wanted_status = f"🚨 **В РОЗЫСКЕ (Уровень {u.wanted})**\n" if u.wanted > 0 else ""
    gov_status = f"🏛 Должность: {u.gov_rank}\n" if u.gov_rank != "Нет" else ""

    text = (f"👤 **Досье**\n{jail_status}{wanted_status}"
            f"💰 Баланс: {u.balance} $\n"
            f"🎖 Статус: {u.role}\n"
            f"{gov_status}"
            f"⚡ Энергия: {u.energy}/100")
    await call.message.edit_text(text, reply_markup=back_kb(), parse_mode="Markdown")
    session.close()

# --- КРИМИНАЛ (Ограбление игроков) ---
@dp.callback_query(F.data == "crime_menu")
async def crime_menu(call: CallbackQuery):
    text = ("💀 **Криминальный мир**\n\n"
            "Стать преступником: `/become_criminal`\n"
            "Ограбить игрока: ответь на его сообщение и напиши `/rob` (нужно быть бандитом)\n"
            "Ограбить банк: `/rob_bank`")
    await call.message.edit_text(text, reply_markup=back_kb(), parse_mode="Markdown")

@dp.message(Command("become_criminal"))
async def become_criminal(message: Message):
    session = get_db()
    u = session.query(User).filter_by(id=message.from_user.id).first()
    u.role = "Преступник"
    u.gov_rank = "Нет"
    session.commit()
    session.close()
    await message.answer("💀 Ты стал преступником! Теперь можешь грабить игроков.")

@dp.message(Command("rob"))
async def rob_player(message: Message):
    if not message.reply_to_message:
        return await message.answer("❌ Ответь на сообщение того, кого хочешь ограбить!")
    
    session = get_db()
    robber = session.query(User).filter_by(id=message.from_user.id).first()
    victim = session.query(User).filter_by(id=message.reply_to_message.from_user.id).first()
    
    if not victim or victim.id == robber.id: return
    
    if robber.role != "Преступник":
        return await message.answer("❌ Ты не бандит! Стань преступником.")
    if robber.jail_time > int(time.time()):
        return await message.answer("❌ Ты в тюрьме, какой грабеж?")
    if robber.energy < 20:
        return await message.answer("❌ Мало энергии для ограбления (нужно 20).")

    robber.energy -= 20
    
    # Шанс успеха 50%
    if random.random() < 0.5:
        loot = int(victim.balance * 0.2) # Забираем 20%
        if loot < 100: loot = 100
        
        victim.balance -= loot
        robber.balance += loot
        robber.wanted += 1 # Повышаем розыск
        text = f"💰 **Ограбление удалось!**\nБандит {message.from_user.first_name} украл {loot} $ у {message.reply_to_message.from_user.first_name}!"
    else:
        text = f"🚨 **Ограбление провалилось!**\n{message.from_user.first_name} пытался ограбить {message.reply_to_message.from_user.first_name}, но его спугнули!"
        robber.wanted += 1 # Все равно в розыск
        
    session.commit()
    session.close()
    await message.answer(text)

@dp.message(Command("rob_bank"))
async def rob_bank(message: Message):
    session = get_db()
    u = session.query(User).filter_by(id=message.from_user.id).first()
    if u.role != "Преступник": return await message.answer("❌ Ты не преступник!")
    if random.random() < 0.4:
        loot = random.randint(10000, 50000)
        u.balance += loot
        u.wanted += 2 # За банк дают больше розыска
        await message.answer(f"💰 Ты ограбил банк и забрал {loot} $! Ты в розыске.")
    else:
        u.jail_time = int(time.time()) + 600
        await message.answer("🚔 Тебя поймали! 10 минут тюрьмы.")
    session.commit()
    session.close()

# --- МВД (Арест бандитов) ---
@dp.callback_query(F.data == "police_menu")
async def police_menu(call: CallbackQuery):
    text = ("🚔 **МВД - Полиция**\n\n"
            "Арестовать преступника: ответь на его сообщение командой `/arrest`\n"
            "(Работает для Министра Внутренних Дел и выше).\n\n"
            "Снять розыск с игрока: `/pardon` (стоит 5000$)")
    await call.message.edit_text(text, reply_markup=back_kb(), parse_mode="Markdown")

@dp.message(Command("arrest"))
async def arrest(message: Message):
    if not message.reply_to_message: return await message.answer("❌ Ответь на сообщение!")
    session = get_db()
    cop = session.query(User).filter_by(id=message.from_user.id).first()
    crim = session.query(User).filter_by(id=message.reply_to_message.from_user.id).first()
    
    if cop.gov_rank not in ["Министр Внутренних Дел", "Премьер-Министр", "Президент"]:
        return await message.answer("❌ У тебя нет полномочий МВД!")
    if crim.wanted == 0 and crim.role != "Преступник":
        return await message.answer("❌ За что его арестовывать? Он чист.")
        
    crim.jail_time = int(time.time()) + 600
    crim.role = "Гражданин"
    crim.wanted = 0 # Сбрасываем розыск
    fine = crim.balance // 2
    crim.balance -= fine
    cop.balance += fine
    session.commit()
    session.close()
    await message.answer(f"🚔 Бандит арестован! Штраф {fine} $ переведен офицеру.")

@dp.message(Command("pardon"))
async def pardon(message: Message):
    if not message.reply_to_message: return await message.answer("❌ Ответь на сообщение игрока!")
    session = get_db()
    u = session.query(User).filter_by(id=message.from_user.id).first()
    target = session.query(User).filter_by(id=message.reply_to_message.from_user.id).first()
    
    if u.gov_rank not in ["Министр Внутренних Дел", "Премьер-Министр", "Президент"]:
        return await message.answer("❌ Только МВД может снимать розыск!")
    if u.balance < 5000:
        return await message.answer("❌ Нужно 5000$ для оформления бумаг.")
        
    u.balance -= 5000
    target.wanted = 0
    session.commit()
    session.close()
    await message.answer(f"📄 Розыск с {message.reply_to_message.from_user.first_name} снят!")

# --- ГОСУДАРСТВО (Иерархия) ---
@dp.callback_query(F.data == "gov_menu")
async def gov_menu(call: CallbackQuery):
    session = get_db()
    u = session.query(User).filter_by(id=call.from_user.id).first()
    
    text = f"🏛 **Государственная Служба**\n\nДолжность: **{u.gov_rank}**\n\n"
    keys = list(GOV_RANKS.keys())
    
    if u.gov_rank == "Нет":
        text += "Начни карьеру с Клерка."
        kb = [[InlineKeyboardButton(text="Стать Клерком (10 000$)", callback_data="gov_rank_up")], [InlineKeyboardButton(text="🔙 Назад", callback_data="back")]]
    elif u.gov_rank == "Президент":
        text += "Ты на вершине власти! 👑"
        kb = [[InlineKeyboardButton(text="🔙 Назад", callback_data="back")]]
    else:
        curr_index = keys.index(u.gov_rank)
        next_rank = keys[curr_index + 1]
        price, salary = GOV_RANKS[next_rank]
        text += f"Следующая ступень: **{next_rank}**\nЦена: {price} $\nЗарплата: {salary} $/мин."
        kb = [[InlineKeyboardButton(text=f"Повыситься", callback_data="gov_rank_up")], [InlineKeyboardButton(text="🔙 Назад", callback_data="back")]]
        
    await call.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="Markdown")
    session.close()

@dp.callback_query(F.data == "gov_rank_up")
async def rank_up(call: CallbackQuery):
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
        await call.answer(f"🎉 Ты повышен до {next_rank}!", show_alert=True)
        await gov_menu(call)
    else:
        await call.answer(f"❌ Нужно {price} $!", show_alert=True)
    session.close()

# --- НАЛОГИ ---
@dp.message(Command("taxes"))
async def taxes(message: Message):
    session = get_db()
    u = session.query(User).filter_by(id=message.from_user.id).first()
    if u.gov_rank not in ["Министр Финансов", "Премьер-Министр", "Президент"]:
        return await message.answer("❌ Только Минфин собирает налоги!")
    
    all_users = session.query(User).all()
    total = 0
    for user in all_users:
        if user.id != u.id and user.balance > 0:
            tax = int(user.balance * 0.03)
            user.balance -= tax
            total += tax
    u.balance += total
    session.commit()
    session.close()
    await message.answer(f"🏛 Минфин собрал налоги! В казну поступило: {total} $.")

# --- ТОП ---
@dp.callback_query(F.data == "top")
async def top_menu(call: CallbackQuery):
    session = get_db()
    top_users = session.query(User).order_by(User.balance.desc()).limit(10).all()
    text = "🏆 **Топ-10 богачей:**\n\n"
    for i, u in enumerate(top_users, 1):
        role_text = f"({u.gov_rank})" if u.gov_rank != "Нет" else f"({u.role})"
        text += f"{i}. `{u.id}` - {u.balance} $ {role_text}\n"
    await call.message.edit_text(text, reply_markup=back_kb(), parse_mode="Markdown")
    session.close()

# --- ФОНОВАЯ ЗАДАЧА ---
async def background_loop():
    while True:
        await asyncio.sleep(60)
        session = get_db()
        users = session.query(User).all()
        for u in users:
            if u.energy < 100:
                u.energy += 10
                if u.energy > 100: u.energy = 100
            if u.gov_rank != "Нет":
                salary = GOV_RANKS.get(u.gov_rank, (0, 0))[1]
                u.balance += salary
        session.commit()
        session.close()

async def main():
    asyncio.create_task(background_loop())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
