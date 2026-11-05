import asyncio
import logging
import os  # <--- ОБЯЗАТЕЛЬНО ДОБАВИТЬ ЭТУ СТРОКУ
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from aiogram import Bot, Dispatcher
from aiogram.types import Message, WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
import uvicorn

BOT_TOKEN = "8849457070:AAHfu38xNcnfFsPdqVqE-rMZAW2qLxtmDqg"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Создаем веб-приложение
app = FastAPI()
templates = Jinja2Templates(directory=".")

# --- ОБРАБОТКА БОТА ---
@dp.message(Command("start"))
async def start(message: Message):
    # Кнопка, которая открывает Mini App (сайт)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Играть", web_app=WebAppInfo(url="captivating-motivation-production-ee2d.up.railway.app"))]
    ])
    await message.answer("Добро пожаловать в BANDIT WEB APP! Нажми кнопку ниже, чтобы открыть игру:", reply_markup=kb)

# --- ОБРАБОТКА САЙТА ---
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# --- ЗАПУСК ВСЕГО ВМЕСТЕ ---
async def start_bot():
    await dp.start_polling(bot)

async def start_web():
    config = uvicorn.Config(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
    server = uvicorn.Server(config)
    await server.serve()

async def main():
    # Запускаем бота и сайт параллельно с помощью asyncio.create_task
    # Это предотвращает конфликты
    asyncio.create_task(start_web())
    await start_bot() # Бот блокирует основной поток

if __name__ == "__main__":
    asyncio.run(main())

