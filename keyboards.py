from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import CITIES, JOBS, BUSINESSES, WEAPONS, CARS, REAL_ESTATE, GOV_RANKS

# --- ГЛАВНОЕ МЕНЮ ---
def main_menu():
    kb = [
        [InlineKeyboardButton(text="👤 Профиль", callback_data="profile"), InlineKeyboardButton(text="💼 Работа", callback_data="jobs_menu")],
        [InlineKeyboardButton(text="🏢 Бизнесы", callback_data="biz_menu"), InlineKeyboardButton(text="🏛 Государство", callback_data="gov_menu")],
        [InlineKeyboardButton(text="🚔 Полиция", callback_data="police_menu"), InlineKeyboardButton(text="💀 Криминал", callback_data="crime_menu")],
        [InlineKeyboardButton(text="🛒 Магазин", callback_data="shop_menu"), InlineKeyboardButton(text="💎 Донат", callback_data="donate_menu")],
        [InlineKeyboardButton(text="🏦 Банк", callback_data="bank_menu"), InlineKeyboardButton(text="🚗 Автопарк", callback_data="garage_menu")],
        [InlineKeyboardButton(text="🏠 Недвижимость", callback_data="estate_menu"), InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings")],
        [InlineKeyboardButton(text="🏆 Топы", callback_data="top_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def back_kb():
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="back")]])

# --- НАСТРОЙКИ ---
def settings_menu():
    kb = [
        [InlineKeyboardButton(text="✏️ Сменить ник", callback_data="change_nick")],
        [InlineKeyboardButton(text="📊 Моя статистика", callback_data="stats")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

# --- РАБОТА ---
def job_categories():
    kb = [
        [InlineKeyboardButton(text="🧹 Низкие (до 1.2к)", callback_data="jobcat_1")],
        [InlineKeyboardButton(text="🔧 Средние (до 4к)", callback_data="jobcat_2")],
        [InlineKeyboardButton(text="🎓 Высокие (до 12к)", callback_data="jobcat_3")],
        [InlineKeyboardButton(text="👑 Элитные (до 100к)", callback_data="jobcat_4")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def jobs_list(cat):
    jobs = list(JOBS.items())
    start = (int(cat)-1)*5
    kb = []
    for name, (en, pay) in jobs[start:start+5]:
        kb.append([InlineKeyboardButton(text=f"{name} ({pay}$ | {en}⚡)", callback_data=f"work_{name}")])
    kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data="jobs_menu")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

# --- БИЗНЕСЫ ---
def biz_categories():
    kb = [
        [InlineKeyboardButton(text="🥙 Малый (до 25к)", callback_data="bizcat_1")],
        [InlineKeyboardButton(text="🏪 Средний (до 300к)", callback_data="bizcat_2")],
        [InlineKeyboardButton(text="🏭 Крупный (до 5млн)", callback_data="bizcat_3")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def biz_list(cat):
    biz = list(BUSINESSES.items())
    start = (int(cat)-1)*5
    kb = []
    for name, (price, inc) in biz[start:start+5]:
        kb.append([InlineKeyboardButton(text=f"{name} ({price}$)", callback_data=f"biz_buy_{name}")])
    kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data="biz_menu")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

# --- МАГАЗИН (ОРУЖИЕ И ДРУГОЕ) ---
def shop_menu():
    kb = [
        [InlineKeyboardButton(text="🔫 Оружейный магазин", callback_data="weapon_shop")],
        [InlineKeyboardButton(text="🚗 Автосалон", callback_data="garage_menu")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def weapon_shop():
    kb = []
    for name, (price, bonus) in WEAPONS.items():
        if name != "Кулаки":
            if price >= 500: # Донат-оружие
                kb.append([InlineKeyboardButton(text=f"{name} (💎{price})", callback_data=f"wep_buy_{name}")])
            else:
                kb.append([InlineKeyboardButton(text=f"{name} ({price}$ | +{bonus})", callback_data=f"wep_buy_{name}")])
    kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data="shop_menu")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

# --- АВТОСАЛОН ---
def garage_menu():
    kb = []
    for name, (price, bonus) in CARS.items():
        if name != "Пешком":
            kb.append([InlineKeyboardButton(text=f"{name} ({price}$ | Побег +{bonus})", callback_data=f"car_buy_{name}")])
    kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data="shop_menu")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

# --- НЕДВИЖИМОСТЬ ---
def estate_menu():
    kb = []
    for name, (price, bonus) in REAL_ESTATE.items():
        if name != "Общежитие":
            kb.append([InlineKeyboardButton(text=f"{name} ({price}$ | ⚡+{bonus})", callback_data=f"estate_buy_{name}")])
    kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

# --- БАНК ---
def bank_menu():
    kb = [
        [InlineKeyboardButton(text="💵 Положить в банк", callback_data="bank_deposit")],
        [InlineKeyboardButton(text="🏧 Снять деньги", callback_data="bank_withdraw")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

# --- ГОСУДАРСТВО ---
def gov_menu(current_rank):
    kb = []
    keys = list(GOV_RANKS.keys())
    if current_rank == "Нет":
        kb.append([InlineKeyboardButton(text="Стать Клерком (10 000$)", callback_data="gov_up")])
    elif current_rank != "Президент":
        next_rank = keys[keys.index(current_rank) + 1]
        price, salary = GOV_RANKS[next_rank]
        kb.append([InlineKeyboardButton(text=f"Повыситься до {next_rank} ({price}$)", callback_data="gov_up")])
    
    kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

# --- ДОНАТ ---
def donate_menu():
    kb = [
        [InlineKeyboardButton(text="💎 Купить 100 кристаллов", callback_data="donate_100")],
        [InlineKeyboardButton(text="💎 Купить 500 кристаллов", callback_data="donate_500")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

# --- ТОПЫ ---
def top_menu():
    kb = [
        [InlineKeyboardButton(text="💰 По деньгам", callback_data="top_money")],
        [InlineKeyboardButton(text="⭐ По должности", callback_data="top_gov")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)
