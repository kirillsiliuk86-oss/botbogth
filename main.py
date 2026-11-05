import asyncio
import logging
import os
import random
import time
import threading
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from sqlalchemy import create_engine, Column, Integer, String, BigInteger
from sqlalchemy.orm import declarative_base, sessionmaker

# ================= НАСТРОЙКИ =================
BOT_TOKEN = "8849457070:AAHfu38xNcnfFsPdqVqE-rMZAW2qLxtmDqg" # <--- ВСТАВЬ ТОКЕН ОТ BOTFATHER
# ============================================

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- БАЗА ДАННЫХ ---
engine = create_engine('sqlite:///bandit_web.db', connect_args={"check_same_thread": False})
Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(BigInteger, primary_key=True)
    nickname = Column(String, default="Игрок")
    balance = Column(Integer, default=5000)
    energy = Column(Integer, default=100)
    level = Column(Integer, default=1)
    last_work = Column(Integer, default=0)
    job = Column(String, default="Безработный")

Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

def get_db(): return Session()

# --- БОТ ---
@dp.message(Command("start"))
async def start(message: Message):
    session = get_db()
    u = session.query(User).filter_by(id=message.from_user.id).first()
    if not u:
        u = User(id=message.from_user.id, nickname=message.from_user.first_name)
        session.add(u)
        session.commit()
    
    # Получаем URL сайта (Railway сам подставит его)
    domain = os.environ.get("captivating-motivation-production-ee2d.up.railway.app", "localhost:8080")
    app_url = f"https://{domain}"
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎮 Открыть игру", web_app=WebAppInfo(url=app_url))]
    ])
    await message.answer(f"Привет, {u.nickname}!\nНажми кнопку ниже, чтобы открыть игру прямо в Telegram:", reply_markup=kb)
    session.close()

# --- САЙТ (API ДЛЯ MINI APP) ---
app = FastAPI()
templates = Jinja2Templates(directory=".")

@app.get("/", response_class=HTMLResponse)
async def read_index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/profile/{user_id}")
async def get_profile(user_id: int):
    session = get_db()
    u = session.query(User).filter_by(id=user_id).first()
    if not u:
        session.close()
        return {"error": "User not found"}
    
    data = {
        "nickname": u.nickname,
        "balance": u.balance,
        "energy": u.energy,
        "level": u.level,
        "job": u.job
    }
    session.close()
    return data

@app.get("/api/work/{user_id}")
async def do_work(user_id: int):
    session = get_db()
    u = session.query(User).filter_by(id=user_id).first()
    if not u:
        session.close()
        return {"error": "User not found"}
    
    now = int(time.time())
    if now - u.last_work < 60:
        session.close()
        return {"error": "Кулдаун! Подожди минуту."}
    
    if u.energy < 10:
        session.close()
        return {"error": "Мало энергии!"}
        
    earned = random.randint(100, 500)
    u.balance += earned
    u.energy -= 10
    u.last_work = now
    session.commit()
    
    res = {"success": True, "earned": earned, "new_balance": u.balance, "new_energy": u.energy}
    session.close()
    return res

# --- ЗАПУСК ---
def run_web():
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)), log_level="warning")

async def main():
    threading.Thread(target=run_web, daemon=True).start()
    print("Сайт запущен в фоне...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
