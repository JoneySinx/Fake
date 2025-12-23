import asyncio
import re
import math

from hydrogram import Client, filters, enums
from hydrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from hydrogram.errors.exceptions.bad_request_400 import (
    MediaEmpty, PhotoInvalidDimensions, WebpageMediaEmpty
)

from Script import script
from info import (
    DELETE_TIME, MAX_BTN, FILMS_LINK, LOG_CHANNEL
)
from utils import (
    is_premium, get_size, get_settings,
    get_readable_time, get_poster, temp
)
from database.users_chats_db import db
from database.ia_filterdb import get_search_results

# 🔐 shared memory (VERY IMPORTANT)
from helpers.constants import BUTTONS, CAP


# =========================
# PM SEARCH
# =========================
@Client.on_message(filters.private & filters.text & filters.incoming)
async def pm_search(client, message):
    if message.text.startswith("/"):
        return

    stg = db.get_bot_sttgs()
    if not stg.get("PM_SEARCH"):
        return await message.reply_text("PM search was disabled!")

    if await is_premium(message.from_user.id, client):
        if not stg.get("AUTO_FILTER"):
            return await message.reply_text("Auto filter was disabled!")
        s = await message.reply(f"<b><i>⚠️ `{message.text}` searching...</i></b>")
        await auto_filter(client, message, s)
    else:
        files, _, total = await get_search_results(message.text)
        if total:
            btn = [[
                InlineKeyboardButton("🗂 CLICK HERE 🗂", url=FILMS_LINK)
            ], [
                InlineKeyboardButton("🤑 Buy Premium", url=f"https://t.me/{temp.U_NAME}?start=premium")
            ]]
            await message.reply_text(
                f"<b><i>Total <code>{total}</code> results found 👇</i></b>",
                reply_markup=InlineKeyboardMarkup(btn)
            )


# =========================
# GROUP SEARCH
# =========================
@Client.on_message(filters.group & filters.text & filters.incoming)
async def group_search(client, message):
    stg = db.get_bot_sttgs()
    if not stg.get("AUTO_FILTER"):
        return

    if message.text.startswith("/"):
        return

    s = await message.reply(f"<b><i>⚠️ `{message.text}` searching...</i></b>")
    await auto_filter(client, message, s)


# =========================
# AUTO FILTER (CORE ENGINE)
# =========================
async def auto_filter(client, msg, s, spoll=False):
    if not spoll:
        message = msg
        settings = await get_settings(message.chat.id)

        search = re.sub(
            r"\s+", " ",
            re.sub(r"[-:\"';!]", " ", message.text)
        ).strip()

        files, offset, total = await get_search_results(search)
        if not files:
            if settings["spell_check"]:
                await advantage_spell_chok(message, s)
            else:
                await s.edit(f"I can't find <b>{search}</b>")
            return
    else:
        settings = await get_settings(msg.message.chat.id)
        message = msg.message.reply_to_message
        search, files, offset, total = spoll

    req = message.from_user.id if message.from_user else 0
    key = f"{message.chat.id}-{message.id}"

    temp.FILES[key] = files
    BUTTONS[key] = search

    files_link = ""
    if settings["links"]:
        btn = []
        for i, file in enumerate(files, start=1):
            files_link += (
                f"\n\n<b>{i}. "
                f"<a href='https://t.me/{temp.U_NAME}?start=file_{message.chat.id}_{file['_id']}'>"
                f"[{get_size(file['file_size'])}] {file['file_name']}</a></b>"
            )
    else:
        btn = [[
            InlineKeyboardButton(
                text=f"{get_size(f['file_size'])} - {f['file_name']}",
                callback_data=f"file#{f['_id']}"
            )
        ] for f in files]

    if offset != "":
        btn.append([
            InlineKeyboardButton(
                text=f"1/{math.ceil(int(total) / MAX_BTN)}",
                callback_data="buttons"
            ),
            InlineKeyboardButton(
                text="NEXT »",
                callback_data=f"next_{req}_{key}_{offset}"
            )
        ])

    btn.append([
        InlineKeyboardButton("🤑 Buy Premium", url=f"https://t.me/{temp.U_NAME}?start=premium")
    ])

    imdb = await get_poster(search, file=files[0]["file_name"]) if settings["imdb"] else None
    if imdb:
        cap = settings["template"].format(**imdb, query=search)
    else:
        cap = f"<b>Results for <code>{search}</code></b>"

    CAP[key] = cap

    del_msg = (
        f"\n\n<b>⚠️ Auto delete after "
        f"<code>{get_readable_time(DELETE_TIME)}</code></b>"
        if settings["auto_delete"] else ""
    )

    try:
        await s.delete()
        await message.reply_text(
            cap + files_link + del_msg,
            reply_markup=InlineKeyboardMarkup(btn),
            disable_web_page_preview=True,
            parse_mode=enums.ParseMode.HTML
        )
    except Exception:
        pass


# =========================
# SPELL CHECK
# =========================
async def advantage_spell_chok(message, s):
    search = message.text
    btn = [[
        InlineKeyboardButton("🔎 Search Google", url=f"https://www.google.com/search?q={search.replace(' ', '+')}")
    ]]
    await s.edit(
        script.NOT_FILE_TXT.format(message.from_user.mention, search),
        reply_markup=InlineKeyboardMarkup(btn)
    )
    await asyncio.sleep(10)
    try:
        await s.delete()
        await message.delete()
    except:
        pass
