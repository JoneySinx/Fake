import os
import asyncio
import random
from time import monotonic, time as time_now
from hydrogram import Client, filters, enums
from hydrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from database.ia_filterdb import (
    db_count_documents,
    second_db_count_documents,
    get_file_details,
    delete_files
)
from database.users_chats_db import db
from info import (
    ADMINS, BIN_CHANNEL, URL,
    INDEX_CHANNELS, DELETE_TIME,
    PM_FILE_DELETE_TIME
)
from utils import (
    get_settings,
    get_size,
    is_check_admin,
    temp,
    get_readable_time
)

# ─────────────────────────────────────
# START (ADMIN ONLY)
# ─────────────────────────────────────
@Client.on_message(filters.command("start"))
async def start(client, message):
    if message.from_user.id not in ADMINS:
        return await message.reply("❌ This bot is admin-only.")

    await message.reply(
        f"👋 Hello {message.from_user.mention}\n\n"
        f"⚙️ Admin-only file manager bot"
    )

# ─────────────────────────────────────
# SEND SINGLE FILE
# ─────────────────────────────────────
@Client.on_message(filters.private & filters.command("file"))
async def send_file(client, message):
    if message.from_user.id not in ADMINS:
        return

    try:
        _, grp_id, file_id = message.command
    except:
        return await message.reply("Invalid request.")

    file = await get_file_details(file_id)
    if not file:
        return await message.reply("File not found.")

    caption = f"{file['file_name']} ({get_size(file['file_size'])})"

    msg = await client.send_cached_media(
        chat_id=message.chat.id,
        file_id=file_id,
        caption=caption
    )

    await asyncio.sleep(PM_FILE_DELETE_TIME)
    await msg.delete()

# ─────────────────────────────────────
# DELETE FILES
# ─────────────────────────────────────
@Client.on_message(filters.command("delete") & filters.user(ADMINS))
async def delete_query(bot, message):
    try:
        query = message.text.split(" ", 1)[1]
    except:
        return await message.reply("Usage: /delete query")

    btn = [[
        InlineKeyboardButton("YES", callback_data=f"delete_{query}"),
        InlineKeyboardButton("NO", callback_data="close")
    ]]
    await message.reply(
        f"Delete all files matching:\n<code>{query}</code> ?",
        reply_markup=InlineKeyboardMarkup(btn)
    )

# ─────────────────────────────────────
# STATS (ADMIN)
# ─────────────────────────────────────
@Client.on_message(filters.command("stats") & filters.user(ADMINS))
async def stats(bot, message):
    files = db_count_documents()
    users = await db.total_users_count()
    chats = await db.total_chat_count()
    uptime = get_readable_time(time_now() - temp.START_TIME)

    await message.reply(
        f"📊 Bot Stats\n\n"
        f"Users: {users}\n"
        f"Chats: {chats}\n"
        f"Files: {files}\n"
        f"Uptime: {uptime}"
    )

# ─────────────────────────────────────
# PING
# ─────────────────────────────────────
@Client.on_message(filters.command("ping"))
async def ping(client, message):
    start = monotonic()
    msg = await message.reply("⏱️")
    end = monotonic()
    await msg.edit(f"{round((end - start) * 1000)} ms")

# ─────────────────────────────────────
# CALLBACK DELETE
# ─────────────────────────────────────
@Client.on_callback_query(filters.regex("^delete_"))
async def cb_delete(_, query):
    q = query.data.split("_", 1)[1]
    deleted = await delete_files(q)
    await query.message.edit(f"Deleted {deleted} files.")

@Client.on_callback_query(filters.regex("^close$"))
async def close(_, query):
    await query.message.delete()
