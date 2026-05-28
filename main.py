from dotenv import load_dotenv

load_dotenv()

import os
import asyncio
import aiosqlite
from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

import asyncio
import feedparser
from datetime import datetime

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
CHANNEL_ID = os.getenv("CHANNEL_ID")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
app = FastAPI()


# ---------- DB ----------
async def init_db():
    async with aiosqlite.connect("posts.db") as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT,
            status TEXT
        )
        """)
        await db.commit()


# ---------- Keyboard ----------
def kb(post_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Publish", callback_data=f"pub_{post_id}"),
            InlineKeyboardButton(text="❌ Reject", callback_data=f"rej_{post_id}")
        ]
    ])


# ---------- Incoming message ----------
@app.post("/webhook")
async def webhook(req: Request):
    data = await req.json()

    update = types.Update(**data)
    await dp.feed_update(bot, update)

    return {"ok": True}


# ---------- Handle user messages ----------
@dp.message()
async def handle_message(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return

    async with aiosqlite.connect("posts.db") as db:
        await db.execute(
            "INSERT INTO posts (text, status) VALUES (?, ?)",
            (message.text, "pending")
        )
        await db.commit()

        cur = await db.execute("SELECT last_insert_rowid()")
        row = await cur.fetchone()
        post_id = row[0]

    await bot.send_message(
        ADMIN_ID,
        f"📄 Новый пост:\n\n{message.text}",
        reply_markup=kb(post_id)
    )


# ---------- Callbacks ----------
@dp.callback_query()
async def callback_handler(callback: types.CallbackQuery):
    action, post_id = callback.data.split("_")
    post_id = int(post_id)

    async with aiosqlite.connect("posts.db") as db:
        cur = await db.execute("SELECT text FROM posts WHERE id=?", (post_id,))
        row = await cur.fetchone()
        text = row[0]

        if action == "pub":
            await bot.send_message(CHANNEL_ID, text)
            await db.execute("UPDATE posts SET status='published' WHERE id=?", (post_id,))
            await callback.message.edit_text("✅ Published")

        elif action == "rej":
            await db.execute("UPDATE posts SET status='rejected' WHERE id=?", (post_id,))
            await callback.message.edit_text("❌ Rejected")

        await db.commit()


# ---------- startup ----------
@app.on_event("startup")
async def startup():
    await init_db()

from dotenv import load_dotenv
load_dotenv()

RSS_URL = "https://news.google.com/rss/search?q=Russia+when:1d&hl=en-US&gl=US&ceid=US:en"

KEYWORDS = [
    "russia",
    "kremlin",
    "moscow",
    "ukraine",
    "sanctions",
    "putin",
    "nato"
]

def fetch_news():
    feed = feedparser.parse(RSS_URL)
    items = []

    for entry in feed.entries:
        title = entry.title
        link = entry.link

        text = (title + " " + link).lower()

        if any(word in text for word in KEYWORDS):
            items.append({
                "title": title,
                "link": link
            })

    return items[:5]

async def news_loop():
    while True:
        try:
            news_list = fetch_news()

            for news in news_list:
                text = format_post(news)
"""

                await bot.send_message(
                    ADMIN_ID,
                    text
                )

            await asyncio.sleep(7200)  # каждые 2 часа

        except Exception as e:
            print("RSS error:", e)
            await asyncio.sleep(60)

@app.on_event("startup")
async def startup():
    asyncio.create_task(news_loop())

def format_post(news):
    title = news["title"]
    link = news["link"]

    post = f"""📰 {title}

📌 Факт:
Новость появилась в международных источниках и касается текущей политической/экономической повестки.

🌍 Почему это важно:
Это может влиять на международные отношения и восприятие текущей ситуации вокруг России.

💬 Мнение:
Мне кажется, здесь интереснее не сама новость, а реакция на неё и возможные последствия.

❓ Вопрос:
Это реальный сигнал изменений или просто очередной информационный шум?

🔗 Источник:
{link}
"""

    return post