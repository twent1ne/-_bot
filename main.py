from dotenv import load_dotenv

load_dotenv()

import os
import asyncio
import aiosqlite
from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

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