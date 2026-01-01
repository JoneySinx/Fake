from hydrogram import Client, filters, enums
from database.users_chats_db import db

# =========================
# CONFIG
# =========================

REPORT_COOLDOWN = 300  # seconds (5 min)

# =========================
# HELPERS
# =========================

async def is_admin(client, chat_id, user_id):
    try:
        m = await client.get_chat_member(chat_id, user_id)
        return m.status in (
            enums.ChatMemberStatus.ADMINISTRATOR,
            enums.ChatMemberStatus.OWNER
        )
    except:
        return False

async def get_admins(client, chat_id):
    admins = []
    async for m in client.get_chat_members(chat_id, filter=enums.ChatMembersFilter.ADMINISTRATORS):
        if not m.user.is_bot:
            admins.append(m.user.id)
    return admins

# =========================
# /report COMMAND
# =========================

@Client.on_message(filters.group & filters.command("report"))
async def report_cmd(client, message):
    if not message.from_user:
        return

    chat_id = message.chat.id
    user_id = message.from_user.id

    # ❌ Admins don't need report
    if await is_admin(client, chat_id, user_id):
        return await message.reply("ℹ️ Admins don't need to report")

    # ❌ Must be reply
    if not message.reply_to_message or not message.reply_to_message.from_user:
        return await message.reply("❌ Reply to a message to report")

    # ⏱️ Cooldown check
    key = f"report_{user_id}_{chat_id}"
    last = await db.get_temp(key)
    if last:
        return await message.reply("⏳ Please wait before reporting again")

    await db.set_temp(key, True, REPORT_COOLDOWN)

    reported = message.reply_to_message.from_user
    reason = " ".join(message.command[1:]) if len(message.command) > 1 else "No reason"

    admins = await get_admins(client, chat_id)
    if not admins:
        return await message.reply("❌ No admins found")

    # 🔗 Message link
    msg_link = f"https://t.me/c/{str(chat_id)[4:]}/{message.reply_to_message.id}"

    text = (
        "🚨 **New Report**\n"
        "━━━━━━━━━━━━━━\n\n"
        f"👤 **Reported User:** {reported.mention}\n"
        f"🧾 **Reported By:** {message.from_user.mention}\n"
        f"📌 **Reason:** {reason}\n"
        f"🔗 [Go to Message]({msg_link})\n\n"
        f"🏷️ **Group:** {message.chat.title}"
    )

    for admin_id in admins:
        try:
            await client.send_message(admin_id, text, disable_web_page_preview=True)
        except:
            pass

    await message.reply("✅ Report sent to admins")

# =========================
# /rhelp (optional help)
# =========================

@Client.on_message(filters.group & filters.command("rhelp"))
async def report_help(client, message):
    await message.reply(
        "🚨 **Report Help**\n"
        "━━━━━━━━━━━━━━\n\n"
        "• Reply to a message and use:\n"
        "`/report spam`\n\n"
        "• Cooldown: 5 minutes\n"
        "• Reports go directly to admins\n"
        "• Abuse may lead to action"
    )
