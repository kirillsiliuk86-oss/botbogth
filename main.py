import asyncio
import logging
import os
import random
import time
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from aiogram.filters import Command
from sqlalchemy import create_engine, Column, Integer, String, BigInteger
from sqlalchemy.orm import declarative_base, sessionmaker
import uvicorn

# ================= НАСТРОЙКИ =================
BOT_TOKEN = "8849457070:AAHfu38xNcnfFsPdqVqE-rMZAW2qLxtmDqg" # <--- ВСТАВЬ СВОЙ ТОКЕН
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
    last_work = Column(Integer, default=0)

Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

# --- БОТ ---
@dp.message(Command("start"))
async def start(message: Message):
    await message.answer("Привет! Нажми на кнопку 'Играть' слева от поля ввода, чтобы начать.")

# --- САЙТ (API ДЛЯ MINI APP) ---
app = FastAPI()

# Ищем файл index.html в той же папке, где лежит main.py
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=BASE_DIR)

@app.get("/", response_class=HTMLResponse)
async def read_index(request: Request):
    # Исправленный вызов, который не выдает ошибку TypeError
    return templates.TemplateResponse(request=request, name="index.html")

@app.get("/api/profile/{user_id}")
async def get_profile(user_id: int):
    session = Session()
    u = session.query(User).filter_by(id=user_id).first()
    if not u:
        u = User(id=user_id)
        session.add(u)
        session.commit()
    
    data = {"nickname": u.nickname, "balance": u.balance, "energy": u.energy}
    session.close()
    return data

@app.get("/api/work/{user_id}")
async def do_work(user_id: int):
    session = Session()
    u = session.query(User).filter_by(id=user_id).first()
    if not u:
        session.close()
        return {"error": "Нет игрока"}
    
    now = int(time.time())
    if now - u.last_work < 60:
        session.close()
        return {"error": "Подожди минуту!"}
    
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

# --- ЗАПУСК БОТА ВНУТРИ FASTAPI ---
@app.on_event("startup")
async def on_startup():
    asyncio.create_task(dp.start_polling(bot))

# Для Railway
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
