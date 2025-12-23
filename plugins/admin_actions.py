from datetime import datetime, timedelta

from hydrogram import Client, enums
from hydrogram.types import CallbackQuery

from utils import is_check_admin


@Client.on_callback_query()
async def admin_actions_handler(client: Client, query: CallbackQuery):
    data = query.data

    # =========================
    # UNMUTE ALL MEMBERS
    # =========================
    if data == "unmute_all_members":
        if not await is_check_admin(client, query.message.chat.id, query.from_user.id):
            return await query.answer("Admins only!", show_alert=True)

        users = []
        await query.message.edit("🔓 Unmuting all members...")

        try:
            async for member in client.get_chat_members(
                query.message.chat.id,
                filter=enums.ChatMembersFilter.RESTRICTED
            ):
                users.append(member.user.id)

            for uid in users:
                await client.unban_chat_member(query.message.chat.id, uid)

        except Exception as e:
            return await query.message.edit(f"Error:\n<code>{e}</code>")

        await query.message.edit(
            f"✅ Unmuted <code>{len(users)}</code> users."
            if users else "No muted users found."
        )
        return

    # =========================
    # UNBAN ALL MEMBERS
    # =========================
    if data == "unban_all_members":
        if not await is_check_admin(client, query.message.chat.id, query.from_user.id):
            return await query.answer("Admins only!", show_alert=True)

        users = []
        await query.message.edit("♻️ Unbanning all members...")

        try:
            async for member in client.get_chat_members(
                query.message.chat.id,
                filter=enums.ChatMembersFilter.BANNED
            ):
                users.append(member.user.id)

            for uid in users:
                await client.unban_chat_member(query.message.chat.id, uid)

        except Exception as e:
            return await query.message.edit(f"Error:\n<code>{e}</code>")

        await query.message.edit(
            f"✅ Unbanned <code>{len(users)}</code> users."
            if users else "No banned users found."
        )
        return

    # =========================
    # KICK MUTED MEMBERS
    # =========================
    if data == "kick_muted_members":
        if not await is_check_admin(client, query.message.chat.id, query.from_user.id):
            return await query.answer("Admins only!", show_alert=True)

        users = []
        await query.message.edit("🚫 Kicking muted members...")

        try:
            async for member in client.get_chat_members(
                query.message.chat.id,
                filter=enums.ChatMembersFilter.RESTRICTED
            ):
                users.append(member.user.id)

            for uid in users:
                await client.ban_chat_member(
                    query.message.chat.id,
                    uid,
                    datetime.now() + timedelta(seconds=30)
                )

        except Exception as e:
            return await query.message.edit(f"Error:\n<code>{e}</code>")

        await query.message.edit(
            f"✅ Kicked <code>{len(users)}</code> muted users."
            if users else "No muted users found."
        )
        return

    # =========================
    # KICK DELETED ACCOUNTS
    # =========================
    if data == "kick_deleted_accounts_members":
        if not await is_check_admin(client, query.message.chat.id, query.from_user.id):
            return await query.answer("Admins only!", show_alert=True)

        users = []
        await query.message.edit("🧹 Removing deleted accounts...")

        try:
            async for member in client.get_chat_members(query.message.chat.id):
                if member.user.is_deleted:
                    users.append(member.user.id)

            for uid in users:
                await client.ban_chat_member(
                    query.message.chat.id,
                    uid,
                    datetime.now() + timedelta(seconds=30)
                )

        except Exception as e:
            return await query.message.edit(f"Error:\n<code>{e}</code>")

        await query.message.edit(
            f"✅ Removed <code>{len(users)}</code> deleted accounts."
            if users else "No deleted accounts found."
        )
        return
