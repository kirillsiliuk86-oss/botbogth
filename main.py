import asyncio
import logging
import os
import random
import time
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import create_engine, Column, Integer, String, BigInteger
from sqlalchemy.orm import declarative_base, sessionmaker
import uvicorn

# ================= НАСТРОЙКИ =================
BOT_TOKEN = "8849457070:AAHfu38xNcnfFsPdqVqE-rMZAW2qLxtmDqg" # <--- ВСТАВЬ ТОКЕН
# ============================================

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- БАЗА ДАННЫХ ---
engine = create_engine('sqlite:///bandit_full.db', connect_args={"check_same_thread": False})
Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(BigInteger, primary_key=True)
    nickname = Column(String, default="Игрок")
    city = Column(String, default="Москва")
    balance = Column(Integer, default=10000)
    business = Column(String, default="Нет")
    job = Column(String, default="Безработный")
    status = Column(String, default="Бомж")
    last_work = Column(Integer, default=0)
    weapon = Column(String, default="Кулаки")
    car = Column(String, default="Пешком")
    house = Column(String, default="Общежитие")

Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

def get_db(): return Session()

# --- КОНСТАНТЫ ИГРЫ ---
JOBS = {
    "Курьер": {"pay": 500, "time": 3},
    "Таксист": {"pay": 1500, "time": 5},
    "Строитель": {"pay": 3000, "time": 8},
    "Программист": {"pay": 8000, "time": 12},
    "Директор": {"pay": 25000, "time": 20}
}

BUSINESSES = {
    "Шаурма": {"price": 5000, "income": 100},
    "Кофейня": {"price": 15000, "income": 350},
    "Автомойка": {"price": 50000, "income": 1200},
    "Завод": {"price": 1000000, "income": 25000}
}

SETS = {
    "Пацанчик": {"bonus": 1.1, "avatar": "https://api.dicebear.com/7.x/avataaars/svg?seed=Gopnik&top=shortHair&clothing=hoodie"},
    "Бизнесмен": {"bonus": 1.3, "avatar": "https://api.dicebear.com/7.x/avataaars/svg?seed=Boss&top=hat&clothing=blazerAndShirt"},
    "Мафиози": {"bonus": 1.5, "avatar": "https://api.dicebear.com/7.x/avataaars/svg?seed=Mafia&top=hat&clothing=blazerAndShirt&accessories=sunglasses"}
}

# --- БОТ ---
class Reg(StatesGroup):
    waiting_for_nickname = State()

@dp.message(Command("start"))
async def start(message: Message, state: FSMContext):
    session = get_db()
    u = session.query(User).filter_by(id=message.from_user.id).first()
    if not u or u.nickname == "Игрок":
        await message.answer("Привет! Придумай свой игровой ник:")
        await state.set_state(Reg.waiting_for_nickname)
    else:
        await message.answer(f"С возвращением, {u.nickname}! Жми 'Играть 🎮'.")
    session.close()

@dp.message(Reg.waiting_for_nickname)
async def set_nick(message: Message, state: FSMContext):
    session = get_db()
    u = session.query(User).filter_by(id=message.from_user.id).first()
    if not u:
        u = User(id=message.from_user.id, nickname=message.text)
        session.add(u)
    else:
        u.nickname = message.text
    session.commit()
    session.close()
    await state.clear()
    await message.answer(f"✅ Твой ник: {message.text}")

# --- САЙТ ---
app = FastAPI()
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=BASE_DIR)

@app.get("/", response_class=HTMLResponse)
async def read_index(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

@app.get("/api/profile/{user_id}")
async def profile(user_id: int):
    session = get_db()
    u = session.query(User).filter_by(id=user_id).first()
    if not u:
        session.close()
        return {"error": "Not found"}
    
    avatar = "https://api.dicebear.com/7.x/avataaars/svg?seed=Felix"
    if u.status in SETS: avatar = SETS[u.status]["avatar"]
    
    data = {"nickname": u.nickname, "balance": u.balance, "status": u.status, "job": u.job, "business": u.business, "avatar": avatar}
    session.close()
    return data

@app.get("/api/jobs")
async def jobs_list(): return JOBS

@app.get("/api/biz")
async def biz_list(): return BUSINESSES

@app.post("/api/work/{user_id}")
async def work(user_id: int, request: Request):
    data = await request.json()
    job = data.get("job")
    session = get_db()
    u = session.query(User).filter_by(id=user_id).first()
    
    now = int(time.time())
    if now - u.last_work < JOBS[job]["time"]:
        session.close()
        return {"error": "Еще работаешь!"}
        
    pay = JOBS[job]["pay"]
    if u.status in SETS: pay = int(pay * SETS[u.status]["bonus"])
    
    u.balance += pay
    u.job = job
    u.last_work = now
    session.commit()
    res = {"success": True, "earned": pay, "new_balance": u.balance}
    session.close()
    return res

@app.post("/api/buy_biz/{user_id}")
async def buy_biz(user_id: int, request: Request):
    data = await request.json()
    biz_name = data.get("biz_name")
    session = get_db()
    u = session.query(User).filter_by(id=user_id).first()
    
    if u.balance >= BUSINESSES[biz_name]["price"]:
        u.balance -= BUSINESSES[biz_name]["price"]
        u.business = biz_name
        session.commit()
        session.close()
        return {"success": True}
    session.close()
    return {"error": "Мало денег!"}

@app.post("/api/buy_set/{user_id}")
async def buy_set(user_id: int, request: Request):
    data = await request.json()
    set_name = data.get("set_name")
    session = get_db()
    u = session.query(User).filter_by(id=user_id).first()
    if u:
        u.status = set_name
        session.commit()
    session.close()
    return {"success": True}

# Фоновая задача для бизнесов
async def income_loop():
    while True:
        await asyncio.sleep(60) # Раз в минуту
        session = get_db()
        users = session.query(User).all()
        for u in users:
            if u.business != "Нет":
                u.balance += BUSINESSES[u.business]["income"]
        session.commit()
        session.close()

@app.on_event("startup")
async def startup():
    asyncio.create_task(dp.start_polling(bot))
    asyncio.create_task(income_loop())

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
