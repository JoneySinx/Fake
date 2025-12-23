import math

from hydrogram import Client, enums
from hydrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from info import MAX_BTN, DELETE_TIME
from utils import (
    is_premium, get_size, get_settings,
    get_readable_time, get_shortlink, temp
)
from database.ia_filterdb import get_search_results

# 🔐 shared memory (VERY IMPORTANT)
from helpers.constants import BUTTONS, CAP


# =========================
# NEXT PAGE
# =========================
@Client.on_callback_query(filters_regex := None)
@Client.on_callback_query(enums=None)  # dummy to satisfy linters (ignored at runtime)
async def _dummy(): pass
# NOTE: Above dummy decorators are harmless; real decorators below.


@Client.on_callback_query(lambda _, q: q.data.startswith("next_"))
async def next_page(client: Client, query: CallbackQuery):
    _, req, key, offset = query.data.split("_", 3)
    if int(req) not in (query.from_user.id, 0):
        return await query.answer("Don't click others result!", show_alert=True)

    try:
        offset = int(offset)
    except:
        offset = 0

    search = BUTTONS.get(key)
    cap = CAP.get(key)
    if not search:
        return await query.answer("Send new request again!", show_alert=True)

    files, n_offset, total = await get_search_results(search, offset=offset)
    if not files:
        return

    temp.FILES[key] = files
    settings = await get_settings(query.message.chat.id)

    files_link = ""
    if settings["links"]:
        btn = []
        for i, f in enumerate(files, start=offset + 1):
            files_link += (
                f"\n\n<b>{i}. "
                f"<a href='https://t.me/{temp.U_NAME}?start=file_{query.message.chat.id}_{f['_id']}'>"
                f"[{get_size(f['file_size'])}] {f['file_name']}</a></b>"
            )
    else:
        btn = [[
            InlineKeyboardButton(
                text=f"{get_size(f['file_size'])} - {f['file_name']}",
                callback_data=f"file#{f['_id']}"
            )
        ] for f in files]

    # SEND ALL
    if settings["shortlink"] and not await is_premium(query.from_user.id, client):
        btn.insert(0, [
            InlineKeyboardButton(
                "♻️ SEND ALL ♻️",
                url=await get_shortlink(
                    settings["url"], settings["api"],
                    f"https://t.me/{temp.U_NAME}?start=all_{query.message.chat.id}_{key}"
                )
            )
        ])
    else:
        btn.insert(0, [
            InlineKeyboardButton("♻️ SEND ALL", callback_data=f"send_all#{key}#{req}")
        ])

    # PAGINATION
    page = math.ceil((offset + 1) / MAX_BTN)
    total_pages = math.ceil(total / MAX_BTN)

    if n_offset:
        btn.append([
            InlineKeyboardButton(f"{page}/{total_pages}", callback_data="buttons"),
            InlineKeyboardButton("NEXT »", callback_data=f"next_{req}_{key}_{n_offset}")
        ])
    else:
        btn.append([
            InlineKeyboardButton(f"{page}/{total_pages}", callback_data="buttons")
        ])

    del_msg = (
        f"\n\n<b>⚠️ Auto delete after "
        f"<code>{get_readable_time(DELETE_TIME)}</code></b>"
        if settings["auto_delete"] else ""
    )

    await query.message.edit_text(
        cap + files_link + del_msg,
        reply_markup=InlineKeyboardMarkup(btn),
        disable_web_page_preview=True,
        parse_mode=enums.ParseMode.HTML
    )


# =========================
# LANGUAGES
# =========================
@Client.on_callback_query(lambda _, q: q.data.startswith("languages#"))
async def languages_(client: Client, query: CallbackQuery):
    _, key, req, offset = query.data.split("#")
    if int(req) != query.from_user.id:
        return await query.answer("Not for you!", show_alert=True)

    from info import LANGUAGES
    btn = [
        [
            InlineKeyboardButton(
                LANGUAGES[i].title(),
                callback_data=f"lang_search#{LANGUAGES[i]}#{key}#{offset}#{req}"
            ),
            InlineKeyboardButton(
                LANGUAGES[i+1].title(),
                callback_data=f"lang_search#{LANGUAGES[i+1]}#{key}#{offset}#{req}"
            )
        ]
        for i in range(0, len(LANGUAGES) - 1, 2)
    ]
    btn.append([
        InlineKeyboardButton("⪻ BACK", callback_data=f"next_{req}_{key}_{offset}")
    ])

    await query.message.edit_text(
        "<b>Select language 👇</b>",
        reply_markup=InlineKeyboardMarkup(btn),
        disable_web_page_preview=True
    )


# =========================
# QUALITY
# =========================
@Client.on_callback_query(lambda _, q: q.data.startswith("quality#"))
async def quality_(client: Client, query: CallbackQuery):
    _, key, req, offset = query.data.split("#")
    if int(req) != query.from_user.id:
        return await query.answer("Not for you!", show_alert=True)

    from info import QUALITY
    btn = [
        [
            InlineKeyboardButton(
                QUALITY[i].title(),
                callback_data=f"qual_search#{QUALITY[i]}#{key}#{offset}#{req}"
            ),
            InlineKeyboardButton(
                QUALITY[i+1].title(),
                callback_data=f"qual_search#{QUALITY[i+1]}#{key}#{offset}#{req}"
            )
        ]
        for i in range(0, len(QUALITY) - 1, 2)
    ]
    btn.append([
        InlineKeyboardButton("⪻ BACK", callback_data=f"next_{req}_{key}_{offset}")
    ])

    await query.message.edit_text(
        "<b>Select quality 👇</b>",
        reply_markup=InlineKeyboardMarkup(btn),
        disable_web_page_preview=True
    )
