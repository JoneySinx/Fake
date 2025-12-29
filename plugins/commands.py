import os
import random
import asyncio
from time import time as time_now, monotonic
from datetime import datetime, timedelta

from Script import script
from hydrogram import Client, filters, enums
from hydrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from database.ia_filterdb import (
    db_count_documents,
    get_file_details,
    delete_files
)

from database.users_chats_db import db

from info import (
    IS_PREMIUM,
    PRE_DAY_AMOUNT,
    RECEIPT_SEND_USERNAME,
    URL,
    BIN_CHANNEL,
    STICKERS,
    INDEX_CHANNELS,
    ADMINS,
    DELETE_TIME,
    LOG_CHANNEL,
    PICS,
    IS_STREAM,
    REACTIONS,
    PM_FILE_DELETE_TIME
)

from utils import (
    is_premium,
    upload_image,
    get_settings,
    get_size,
    is_check_admin,
    save_group_settings,
    temp,
    get_readable_time,
    get_wish
)

# ─────────────────────────────────────
# HELPERS
# ─────────────────────────────────────
async def del_stk(s):
    await asyncio.sleep(3)
    try:
        await s.delete()
    except:
        pass


# ─────────────────────────────────────
# /start
# ─────────────────────────────────────
@Client.on_message(filters.command("start") & filters.incoming)
async def start(client, message):

    # ───── GROUP START ─────
    if message.chat.type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        if not await db.get_chat(message.chat.id):
            total = await client.get_chat_members_count(message.chat.id)
            username = f'@{message.chat.username}' if message.chat.username else 'Private'
            await client.send_message(
                LOG_CHANNEL,
                script.NEW_GROUP_TXT.format(
                    message.chat.title,
                    message.chat.id,
                    username,
                    total
                )
            )
            await db.add_chat(message.chat.id, message.chat.title)

        await message.reply(
            f"<b>ʜᴇʏ {message.from_user.mention}, <i>{get_wish()}</i>\n"
            f"ʜᴏᴡ ᴄᴀɴ ɪ ʜᴇʟᴘ ʏᴏᴜ??</b>"
        )
        return

    # ───── PRIVATE START ─────

    # ✅ REACTION SAFE
    try:
        if REACTIONS:
            await message.react(emoji=random.choice(REACTIONS), big=True)
        else:
            await message.react("⚡️", big=True)
    except:
        pass

    # ✅ STICKER SAFE (FIXED)
    if STICKERS:
        try:
            stk = await client.send_sticker(
                message.chat.id,
                random.choice(STICKERS)
            )
            asyncio.create_task(del_stk(stk))
        except:
            pass
    # if STICKERS empty → silently skip

    # ───── USER DB ─────
    if not await db.is_user_exist(message.from_user.id):
        await db.add_user(message.from_user.id, message.from_user.first_name)
        await client.send_message(
            LOG_CHANNEL,
            script.NEW_USER_TXT.format(
                message.from_user.mention,
                message.from_user.id
            )
        )

    # ───── PREMIUM CHECK ─────
    if not await is_premium(message.from_user.id, client) and message.from_user.id not in ADMINS:
        return await message.reply_photo(
            random.choice(PICS),
            caption="❌ This bot is only for Premium users and Admins!",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(
                    "🤑 Buy Premium",
                    url=f"https://t.me/{temp.U_NAME}?start=premium"
                )
            ]])
        )

    # ───── NORMAL START UI ─────
    if len(message.command) == 1:
        await message.reply_photo(
            random.choice(PICS),
            caption=script.START_TXT.format(
                message.from_user.mention,
                get_wish()
            ),
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "+ ADD ME TO YOUR GROUP +",
                        url=f"https://t.me/{temp.U_NAME}?startgroup=start"
                    )
                ],
                [
                    InlineKeyboardButton("👨‍🚒 HELP", callback_data="help"),
                    InlineKeyboardButton("📚 ABOUT", callback_data="about")
                ]
            ])
        )
        return


# ─────────────────────────────────────
# STATS (SINGLE DB)
# ─────────────────────────────────────
@Client.on_message(filters.command("stats") & filters.user(ADMINS))
async def stats(_, message):
    files = db_count_documents()
    users = await db.total_users_count()
    chats = await db.total_chat_count()
    prm = db.get_premium_count()

    used_files_db_size = get_size(await db.get_files_db_size())
    used_data_db_size = get_size(await db.get_data_db_size())
    uptime = get_readable_time(time_now() - temp.START_TIME)

    await message.reply_text(
        script.STATUS_TXT.format(
            users,
            prm,
            chats,
            files,
            used_files_db_size,
            used_data_db_size,
            uptime
        )
    )


# ─────────────────────────────────────
# GROUP SETTINGS UI
# ─────────────────────────────────────
async def get_grp_stg(group_id):
    """
    Return inline buttons for group settings panel
    (Used by pm_filter.py)
    """
    settings = await get_settings(group_id)

    buttons = [
        [
            InlineKeyboardButton(
                "✏️ Edit File Caption",
                callback_data=f"caption_setgs#{group_id}"
            )
        ],
        [
            InlineKeyboardButton(
                f"🗑 Auto Delete {'✅' if settings.get('auto_delete') else '❌'}",
                callback_data=f"bool_setgs#auto_delete#{settings.get('auto_delete')}#{group_id}"
            )
        ],
        [
            InlineKeyboardButton(
                f"👋 Welcome {'✅' if settings.get('welcome') else '❌'}",
                callback_data=f"bool_setgs#welcome#{settings.get('welcome')}#{group_id}"
            )
        ],
        [
            InlineKeyboardButton(
                f"⏱ Delete Time: {get_readable_time(DELETE_TIME)}",
                callback_data="noop"
            )
        ]
    ]
    return buttons
