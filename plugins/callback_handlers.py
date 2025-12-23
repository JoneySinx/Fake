import random
from datetime import datetime, timedelta

from hydrogram import Client, enums
from hydrogram.types import (
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    InputMediaPhoto
)

from Script import script
from info import (
    ADMINS, PICS, URL, BIN_CHANNEL,
    DELETE_TIME, SHORTLINK_API, SHORTLINK_URL,
    TUTORIAL
)
from utils import (
    is_premium, is_subscribed, is_check_admin,
    get_settings, get_readable_time, temp,
    save_group_settings
)
from database.users_chats_db import db
from database.ia_filterdb import delete_files

# 🔐 shared memory
from helpers.constants import BUTTONS, CAP


@Client.on_callback_query()
async def cb_handler(client: Client, query: CallbackQuery):
    data = query.data

    # =========================
    # CLOSE
    # =========================
    if data == "close_data":
        try:
            uid = query.message.reply_to_message.from_user.id
        except:
            uid = query.from_user.id

        if uid not in (0, query.from_user.id):
            return await query.answer("This is not for you!", show_alert=True)

        await query.answer("Closed")
        await query.message.delete()
        try:
            await query.message.reply_to_message.delete()
        except:
            pass
        return

    # =========================
    # FILE BUTTON
    # =========================
    if data.startswith("file#"):
        _, file_id = data.split("#", 1)
        try:
            uid = query.message.reply_to_message.from_user.id
        except:
            uid = query.message.from_user.id

        if uid not in (0, query.from_user.id):
            return await query.answer("Don't click others result!", show_alert=True)

        await query.answer(
            url=f"https://t.me/{temp.U_NAME}?start=file_{query.message.chat.id}_{file_id}"
        )
        return

    # =========================
    # SEND ALL
    # =========================
    if data.startswith("send_all#"):
        _, key, req = data.split("#")
        if int(req) != query.from_user.id:
            return await query.answer("Not for you!", show_alert=True)

        await query.answer(
            url=f"https://t.me/{temp.U_NAME}?start=all_{query.message.chat.id}_{key}"
        )
        return

    # =========================
    # CHECK SUBSCRIBE
    # =========================
    if data.startswith("checksub#"):
        _, mc = data.split("#", 1)
        btn = await is_subscribed(client, query)
        if btn:
            btn.append([
                InlineKeyboardButton("🔁 Try Again", callback_data=f"checksub#{mc}")
            ])
            await query.answer(
                "Please join updates channel and try again.",
                show_alert=True
            )
            await query.edit_message_reply_markup(
                InlineKeyboardMarkup(btn)
            )
            return

        await query.answer(
            url=f"https://t.me/{temp.U_NAME}?start={mc}"
        )
        await query.message.delete()
        return

    # =========================
    # STREAM
    # =========================
    if data.startswith("stream#"):
        file_id = data.split("#", 1)[1]
        if not await is_premium(query.from_user.id, client):
            return await query.answer(
                "Only premium users can stream!",
                show_alert=True
            )

        msg = await client.send_cached_media(
            chat_id=BIN_CHANNEL,
            file_id=file_id
        )
        watch = f"{URL}watch/{msg.id}"
        download = f"{URL}download/{msg.id}"

        btn = [[
            InlineKeyboardButton("WATCH ONLINE", url=watch),
            InlineKeyboardButton("FAST DOWNLOAD", url=download)
        ], [
            InlineKeyboardButton("❌ CLOSE", callback_data="close_data")
        ]]

        await query.edit_message_reply_markup(
            reply_markup=InlineKeyboardMarkup(btn)
        )
        return

    # =========================
    # DELETE (ADMIN)
    # =========================
    if data.startswith("delete_"):
        if query.from_user.id not in ADMINS:
            return await query.answer("Admins only!", show_alert=True)

        _, q = data.split("_", 1)
        await query.message.edit("Deleting...")
        deleted = await delete_files(q)
        await query.message.edit(f"Deleted {deleted} files for query `{q}`")
        return

    # =========================
    # SETTINGS TOGGLE
    # =========================
    if data.startswith("bool_setgs"):
        _, set_type, status, grp_id = data.split("#")
        uid = query.from_user.id

        if not await is_check_admin(client, int(grp_id), uid):
            return await query.answer("You are not admin!", show_alert=True)

        await save_group_settings(
            int(grp_id),
            set_type,
            False if status == "True" else True
        )

        from plugins.commands import get_grp_stg
        btn = await get_grp_stg(int(grp_id))
        await query.message.edit_reply_markup(
            InlineKeyboardMarkup(btn)
        )
        return

    # =========================
    # BACK SETTINGS
    # =========================
    if data.startswith("back_setgs"):
        _, grp_id = data.split("#")
        uid = query.from_user.id

        if not await is_check_admin(client, int(grp_id), uid):
            return await query.answer("You are not admin!", show_alert=True)

        from plugins.commands import get_grp_stg
        btn = await get_grp_stg(int(grp_id))
        chat = await client.get_chat(int(grp_id))

        await query.message.edit(
            f"Change settings for <b>{chat.title}</b>",
            reply_markup=InlineKeyboardMarkup(btn)
        )
        return

    # =========================
    # START / ABOUT / HELP UI
    # =========================
    if data in ("start", "about", "help"):
        if data == "start":
            caption = script.START_TXT.format(
                query.from_user.mention, ""
            )
        elif data == "about":
            caption = script.MY_ABOUT_TXT
        else:
            caption = script.HELP_TXT.format(
                query.from_user.mention
            )

        await query.edit_message_media(
            InputMediaPhoto(
                random.choice(PICS),
                caption=caption
            )
        )
        return

    # =========================
    # STATS (CALLBACK)
    # =========================
    if data == "stats":
        if query.from_user.id not in ADMINS:
            return await query.answer("Admins only!", show_alert=True)

        users = await db.total_users_count()
        chats = await db.total_chat_count()
        uptime = get_readable_time(
            int(datetime.now().timestamp() - temp.START_TIME)
        )

        await query.edit_message_media(
            InputMediaPhoto(
                random.choice(PICS),
                caption=script.STATUS_TXT.format(
                    users, 0, chats, "-", "-", "-", "-", "-", uptime
                )
            )
        )
        return
