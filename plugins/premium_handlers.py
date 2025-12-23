import os
import qrcode
from datetime import datetime, timedelta

from hydrogram import Client
from hydrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from hydrogram.errors import ListenerTimeout

from info import (
    IS_PREMIUM, PRE_DAY_AMOUNT,
    RECEIPT_SEND_USERNAME,
    UPI_ID, UPI_NAME
)
from utils import is_premium
from database.users_chats_db import db


@Client.on_callback_query()
async def premium_callback_handler(client, query):
    data = query.data

    # =========================
    # ACTIVATE TRIAL
    # =========================
    if data == "activate_trial":
        if not IS_PREMIUM:
            return await query.answer("Premium disabled!", show_alert=True)

        mp = db.get_plan(query.from_user.id)
        if mp.get("trial"):
            return await query.answer(
                "Trial already used! Use /plan",
                show_alert=True
            )

        ex = datetime.now() + timedelta(hours=1)
        mp.update({
            "expire": ex,
            "trial": True,
            "plan": "1 hour",
            "premium": True
        })
        db.update_plan(query.from_user.id, mp)

        await query.message.edit(
            f"✅ Trial activated for 1 hour\nExpire: {ex.strftime('%Y-%m-%d %H:%M:%S')}"
        )
        return

    # =========================
    # ACTIVATE PAID PLAN
    # =========================
    if data == "activate_plan":
        if not IS_PREMIUM:
            return await query.answer("Premium disabled!", show_alert=True)

        q = await query.message.edit(
            "How many days premium do you need?\nSend number only (example: 7)"
        )

        try:
            msg = await client.listen(
                chat_id=query.message.chat.id,
                user_id=query.from_user.id,
                timeout=120
            )
            days = int(msg.text)
        except (ValueError, ListenerTimeout):
            await q.delete()
            return await query.message.reply("Invalid input or timeout!")

        amount = days * PRE_DAY_AMOUNT
        note = f"{days} days premium for {query.from_user.id}"

        upi_uri = (
            f"upi://pay?pa={UPI_ID}&pn={UPI_NAME}"
            f"&am={amount}&cu=INR&tn={note}"
        )

        qr = qrcode.make(upi_uri)
        file = f"upi_{query.from_user.id}.png"
        qr.save(file)
        await q.delete()

        await query.message.reply_photo(
            file,
            caption=(
                f"💎 Premium Plan: {days} days\n"
                f"💰 Amount: {amount} INR\n\n"
                f"Scan QR & pay.\n"
                f"Send receipt photo here within 10 minutes.\n\n"
                f"Support: {RECEIPT_SEND_USERNAME}"
            )
        )
        os.remove(file)

        try:
            receipt = await client.listen(
                chat_id=query.message.chat.id,
                user_id=query.from_user.id,
                timeout=600
            )
        except ListenerTimeout:
            return await query.message.reply(
                f"Time over! Send receipt to {RECEIPT_SEND_USERNAME}"
            )

        if not receipt.photo:
            return await query.message.reply(
                f"Invalid receipt! Send manually to {RECEIPT_SEND_USERNAME}"
            )

        await client.send_photo(
            RECEIPT_SEND_USERNAME,
            receipt.photo.file_id,
            caption=note
        )
        await query.message.reply(
            "✅ Receipt sent to admin. Please wait for confirmation."
        )
        return
