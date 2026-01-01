import time
import sys
import platform

from hydrogram import Client, filters, enums
from hydrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils import temp
from info import IS_PREMIUM

# ======================================================
# 🆔 ID COMMAND (Optimized)
# ======================================================

@Client.on_message(filters.command("id"))
async def get_id(client, message):
    reply = message.reply_to_message
    
    # 1. Target User Identify
    user = reply.from_user if reply and reply.from_user else message.from_user
    
    # 2. Admin Badge (Only in Groups) - Async Check
    badge = "👤 Member"
    if message.chat.type in (enums.ChatType.GROUP, enums.ChatType.SUPERGROUP):
        try:
            # Fast Member Lookup
            member = await message.chat.get_member(user.id)
            if member.status == enums.ChatMemberStatus.OWNER:
                badge = "👑 Owner"
            elif member.status in (enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.ADMIN):
                badge = "🛡 Admin"
        except:
            pass

    # 3. Build Text (Fast String Formatting)
    text = (
        "🆔 <b>ID INFORMATION</b>\n\n"
        f"👤 <b>Name:</b> {user.first_name or ''} {user.last_name or ''}\n"
        f"🦹 <b>User ID:</b> <code>{user.id}</code>\n"
        f"🏷 <b>Username:</b> @{user.username if user.username else 'N/A'}\n"
        f"🌐 <b>DC ID:</b> <code>{user.dc_id or 'Unknown'}</code>\n"
        f"🤖 <b>Bot:</b> {'Yes' if user.is_bot else 'No'}\n"
        f"{badge}\n"
        f"🔗 <b>Profile:</b> <a href='tg://user?id={user.id}'>Open</a>\n"
    )

    # 4. Chat Info
    text += (
        "\n💬 <b>CHAT & MESSAGE</b>\n"
        f"🆔 <b>Chat ID:</b> <code>{message.chat.id}</code>\n"
        f"📩 <b>Msg ID:</b> <code>{message.id}</code>\n"
    )

    # 5. Group Specific Info
    if message.chat.type in (enums.ChatType.GROUP, enums.ChatType.SUPERGROUP):
        text += (
            f"📛 <b>Title:</b> {message.chat.title}\n"
            f"🔗 <b>Link:</b> @{message.chat.username if message.chat.username else 'Private'}\n"
        )

    # 6. Sticker Info (If replied to sticker)
    if reply and reply.sticker:
        st = reply.sticker
        text += (
            "\n🎭 <b>STICKER DETAILS</b>\n"
            f"🆔 <b>File ID:</b> <code>{st.file_id}</code>\n"
            f"📦 <b>Set:</b> <code>{st.set_name or 'N/A'}</code>\n"
            f"🔖 <b>Emoji:</b> {st.emoji or 'N/A'}\n"
            f"🎞 <b>Anim:</b> {'Yes' if st.is_animated else 'No'} | <b>Vid:</b> {'Yes' if st.is_video else 'No'}\n"
        )

    await message.reply_text(
        text,
        parse_mode=enums.ParseMode.HTML,
        disable_web_page_preview=True
    )


# ======================================================
# 🚨 REPORT SYSTEM (New Feature)
# ======================================================

@Client.on_message(filters.command(["report", "Report"]) & filters.group)
async def report_user(client, message):
    # 1. Check if replied
    if not message.reply_to_message:
        return await message.reply("⚠️ **Invalid Usage!**\n\nकिसी यूजर के मैसेज को Reply करके `/report` लिखें।")

    reply = message.reply_to_message
    reporter = message.from_user
    reported = reply.from_user

    # 2. Basic Checks
    if not reported:
        return await message.reply("❌ इस यूजर को रिपोर्ट नहीं किया जा सकता।")
    
    if reported.is_bot:
        return await message.reply("❌ बॉट्स को रिपोर्ट नहीं कर सकते।")
    
    if reported.id == client.me.id:
        return await message.reply("❌ मुझे रिपोर्ट क्यों कर रहे हो? 🥺")

    # 3. Message Preview
    msg_preview = "Media/File"
    if reply.text:
        msg_preview = reply.text[:100] + ("..." if len(reply.text) > 100 else "")
    elif reply.caption:
        msg_preview = reply.caption[:100] + ("..." if len(reply.caption) > 100 else "")

    # 4. Notify Admins
    text = (
        f"🚨 **NEW REPORT**\n\n"
        f"📂 **Group:** {message.chat.title} (`{message.chat.id}`)\n"
        f"🔗 **Link:** [Click Here]({message.link})\n\n"
        f"👤 **Reporter:** {reporter.mention} (`{reporter.id}`)\n"
        f"💀 **Reported User:** {reported.mention} (`{reported.id}`)\n\n"
        f"📝 **Message:** `{msg_preview}`"
    )

    btn = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔗 View Message", url=reply.link)],
        [InlineKeyboardButton("🗑 Delete Message", callback_data=f"del_msg_{message.chat.id}_{reply.id}")]
    ])

    sent_count = 0
    admins = []
    
    # Get Admins
    async for member in message.chat.get_members(filter=enums.ChatMembersFilter.ADMINISTRATORS):
        if not member.user.is_bot:
            admins.append(member.user.id)

    # Send to PM
    for admin_id in admins:
        try:
            await client.send_message(
                chat_id=admin_id,
                text=text,
                reply_markup=btn,
                disable_web_page_preview=True
            )
            sent_count += 1
        except Exception:
            pass # Admin blocked bot or hasn't started it

    await message.reply(f"✅ **Report Sent!**\n\nAlert sent to {sent_count} admins.")


# ======================================================
# 🗑 DELETE CALLBACK (For Admins in PM)
# ======================================================
@Client.on_callback_query(filters.regex(r"^del_msg_"))
async def delete_reported_msg(client, query):
    try:
        data = query.data.split("_")
        chat_id = int(data[2])
        msg_id = int(data[3])

        # Check if user is admin in that group
        member = await client.get_chat_member(chat_id, query.from_user.id)
        if member.status not in (enums.ChatMemberStatus.OWNER, enums.ChatMemberStatus.ADMINISTRATOR):
            return await query.answer("❌ You are not an admin in that group anymore!", show_alert=True)

        await client.delete_messages(chat_id, msg_id)
        await query.answer("✅ Message Deleted!", show_alert=True)
        await query.message.edit_text(query.message.text + "\n\n✅ **ACTION TAKEN: Deleted**")
    
    except Exception as e:
        await query.answer(f"❌ Error: {e}", show_alert=True)


# ======================================================
# 🏓 PING (Simple & Fast)
# ======================================================

@Client.on_message(filters.command("ping"))
async def ping_cmd(client, message):
    start = time.time()
    msg = await message.reply_text("🏓 Pinging...")
    end = time.time()
    
    latency = int((end - start) * 1000)
    
    await msg.edit_text(
        f"🏓 <b>Pong!</b>\n\n⚡ Latency: <code>{latency} ms</code>",
        parse_mode=enums.ParseMode.HTML
    )


# ======================================================
# 🤖 BOT INFO (Lightweight)
# ======================================================

@Client.on_message(filters.command("botinfo"))
async def bot_info(client, message):
    uptime = int(time.time() - temp.START_TIME)
    h = uptime // 3600
    m = (uptime % 3600) // 60
    
    py_ver = sys.version.split()[0]
    os_sys = platform.system()

    text = (
        f"🤖 <b>BOT STATUS</b>\n\n"
        f"⏱️ <b>Uptime:</b> <code>{h}h {m}m</code>\n"
        f"🐍 <b>Python:</b> <code>{py_ver}</code>\n"
        f"⚙️ <b>OS:</b> <code>{os_sys}</code>\n"
        f"📦 <b>Lib:</b> <code>Hydrogram</code>\n"
        f"💎 <b>Premium:</b> <code>{'Enabled' if IS_PREMIUM else 'Disabled'}</code>\n"
    )

    await message.reply_text(text, parse_mode=enums.ParseMode.HTML)

