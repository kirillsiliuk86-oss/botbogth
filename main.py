import asyncio
import logging
import os
import random
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import create_engine, Column, Integer, String, BigInteger
from sqlalchemy.orm import declarative_base, sessionmaker
import uvicorn

# ================= НАСТРОЙКИ =================
BOT_TOKEN = "8849457070:AAHfu38xNcnfFsPdqVqE-rMZAW2qLxtmDqg" # <--- ВСТАВЬ
# ============================================

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- БАЗА ДАННЫХ ---
engine = create_engine('sqlite:///bandit_sets.db', connect_args={"check_same_thread": False})
Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(BigInteger, primary_key=True)
    nickname = Column(String, default="Игрок")
    city = Column(String, default="Москва")
    balance = Column(Integer, default=10000)
    energy = Column(Integer, default=100)
    status = Column(String, default="Бомж") # Бомж, Пацанчик, Бизнесмен, Мафиози
    weapon = Column(String, default="Кулаки")
    car = Column(String, default="Пешком")

Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

# --- БОТ ---
@dp.message(Command("start"))
async def start(message: Message):
    session = Session()
    u = session.query(User).filter_by(id=message.from_user.id).first()
    if not u:
        u = User(id=message.from_user.id, nickname=message.from_user.first_name)
        session.add(u)
        session.commit()
    session.close()
    await message.answer(f"Привет, {u.nickname}! Жми 'Играть 🎮' внизу.")

# --- САЙТ ---
app = FastAPI()
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=BASE_DIR)

@app.get("/", response_class=HTMLResponse)
async def read_index(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

@app.get("/api/profile/{user_id}")
async def get_profile(user_id: int):
    session = Session()
    u = session.query(User).filter_by(id=user_id).first()
    if not u:
        session.close()
        return {"error": "Not found"}
    data = {
        "nickname": u.nickname, "balance": u.balance, "energy": u.energy,
        "city": u.city, "status": u.status, "weapon": u.weapon, "car": u.car
    }
    session.close()
    return data

@app.post("/api/buy_set/{user_id}")
async def buy_set(user_id: int, request: Request):
    data = await request.json()
    set_name = data.get("set_name")
    
    session = Session()
    u = session.query(User).filter_by(id=user_id).first()
    if u:
        u.status = set_name
        # Тут можно списывать реальные деньги или звезды. 
        # Пока просто меняем статус (для теста).
        session.commit()
    session.close()
    return {"success": True}

@app.on_event("startup")
async def on_startup():
    asyncio.create_task(dp.start_polling(bot))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
