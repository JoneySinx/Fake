import asyncio
from datetime import datetime, timedelta
from hydrogram import Client, filters, enums
from hydrogram.types import ChatPermissions
from database.users_chats_db import db
import pytz

# =========================
# CONFIG
# =========================
MAX_WARNS = 3
AUTO_MUTE_TIME = 600  # 10 minutes
IST = pytz.timezone('Asia/Kolkata')

# =========================
# HELPERS
# =========================

async def is_admin(client, chat_id, user_id):
    try:
        member = await client.get_chat_member(chat_id, user_id)
        return member.status in (
            enums.ChatMemberStatus.ADMINISTRATOR,
            enums.ChatMemberStatus.OWNER
        )
    except:
        return False

async def warn_user(user_id, chat_id):
    data = await db.get_warn(user_id, chat_id) or {"count": 0}
    data["count"] += 1
    await db.set_warn(user_id, chat_id, data)
    return data["count"]

async def reset_warn(user_id, chat_id):
    await db.clear_warn(user_id, chat_id)

def get_ist_time():
    """Get current time in IST"""
    return datetime.now(IST).strftime('%d-%m-%Y %I:%M:%S %p')

# =========================
# REPORT SYSTEM
# =========================

@Client.on_message(filters.group & filters.reply & filters.command(["report", "Report"]))
async def report_message(client, message):
    """
    Report a message to all group admins via PM
    Usage: Reply to a message with /report or /Report
    """
    chat_id = message.chat.id
    reporter = message.from_user
    reported_msg = message.reply_to_message
    
    if not reported_msg:
        return await message.reply("❌ Please reply to a message to report it!")
    
    # Don't allow reporting own messages
    if reported_msg.from_user and reported_msg.from_user.id == reporter.id:
        return await message.reply("❌ You cannot report your own message!")
    
    # Get all admins (including those who reported - they can report too)
    admins = []
    admin_ids = []
    async for member in client.get_chat_members(chat_id, enums.ChatMembersFilter.ADMINISTRATORS):
        if not member.user.is_bot:
            admins.append(member.user)
            admin_ids.append(member.user.id)
    
    if not admins:
        return await message.reply("❌ No admins found!")
    
    # Get chat info
    try:
        chat = await client.get_chat(chat_id)
        chat_name = chat.title
        chat_username = f"@{chat.username}" if chat.username else "Private Group"
    except:
        chat_name = "Unknown Group"
        chat_username = "N/A"
    
    # Build reported user info
    reported_user = reported_msg.from_user
    if reported_user:
        reported_user_info = (
            f"**👤 Reported User:**\n"
            f"├ Name: {reported_user.first_name} {reported_user.last_name or ''}\n"
            f"├ ID: `{reported_user.id}`\n"
            f"└ Username: @{reported_user.username or 'None'}\n\n"
        )
        reported_mention = reported_user.mention
    else:
        reported_user_info = "**👤 Reported User:** Anonymous/Channel\n\n"
        reported_mention = "Anonymous User"
    
    # Get message content
    if reported_msg.text:
        msg_content = reported_msg.text[:200] + ("..." if len(reported_msg.text) > 200 else "")
    elif reported_msg.caption:
        msg_content = f"[Media] {reported_msg.caption[:150]}"
    elif reported_msg.photo:
        msg_content = "[Photo]"
    elif reported_msg.video:
        msg_content = "[Video]"
    elif reported_msg.document:
        msg_content = "[Document]"
    elif reported_msg.sticker:
        msg_content = "[Sticker]"
    elif reported_msg.voice:
        msg_content = "[Voice Message]"
    elif reported_msg.audio:
        msg_content = "[Audio]"
    else:
        msg_content = "[Unknown Media Type]"
    
    # Build report message for admin PMs
    report_text = (
        f"🚨 **NEW REPORT**\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"**📍 Group:** {chat_name}\n"
        f"**🔗 Username:** {chat_username}\n"
        f"**🆔 Group ID:** `{chat_id}`\n\n"
        f"**👮 Reporter:**\n"
        f"├ Name: {reporter.first_name} {reporter.last_name or ''}\n"
        f"├ ID: `{reporter.id}`\n"
        f"└ Username: @{reporter.username or 'None'}\n\n"
        f"{reported_user_info}"
        f"**💬 Reported Message:**\n"
        f"```\n{msg_content}\n```\n\n"
        f"**🔗 [Click here to view message]({reported_msg.link})**\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"⏰ **Time:** {get_ist_time()} IST"
    )
    
    # Send to all admins via PM
    success_count = 0
    failed_admins = []
    
    for admin in admins:
        try:
            await client.send_message(
                admin.id,
                report_text,
                parse_mode=enums.ParseMode.MARKDOWN,
                disable_web_page_preview=False
            )
            success_count += 1
            await asyncio.sleep(0.1)  # Small delay to avoid flood
        except Exception as e:
            failed_admins.append(admin.first_name)
    
    # Build confirmation message
    if success_count > 0:
        confirm_text = (
            f"✅ **Report Sent Successfully!**\n\n"
            f"📊 **Statistics:**\n"
            f"├ Total Admins: {len(admins)}\n"
            f"├ Reports Sent: {success_count}\n"
            f"└ Failed: {len(failed_admins)}\n\n"
            f"**Reported:** {reported_mention}\n"
            f"**Message:** {msg_content[:50]}...\n\n"
            f"⏰ {get_ist_time()} IST"
        )
        
        if failed_admins:
            confirm_text += f"\n\n⚠️ Some admins haven't started the bot: {', '.join(failed_admins[:3])}"
        
        reply = await message.reply(confirm_text, parse_mode=enums.ParseMode.MARKDOWN)
    else:
        reply = await message.reply(
            "⚠️ **Report Failed!**\n\n"
            "Could not send report to any admin.\n"
            "**Reason:** Admins must start the bot first to receive reports.\n\n"
            "**Solution:**\n"
            "1. Ask admins to start the bot in PM\n"
            "2. Try using `@admin` mention in group instead"
        )
    
    # Delete both messages after 10 seconds
    await asyncio.sleep(10)
    try:
        await message.delete()
        await reply.delete()
    except:
        pass


@Client.on_message(filters.group & filters.text & filters.regex(r"@admin|@admins"))
async def admin_mention_alert(client, message):
    """
    Alert admins when @admin or @admins is mentioned
    """
    chat_id = message.chat.id
    user_id = message.from_user.id if message.from_user else 0
    
    if not user_id:
        return
    
    # Skip if user is admin
    if await is_admin(client, chat_id, user_id):
        return
    
    # Get all admins
    admins = []
    async for member in client.get_chat_members(chat_id, enums.ChatMembersFilter.ADMINISTRATORS):
        if not member.user.is_bot:
            admins.append(member.user.id)
    
    # Send hidden mention to all admins
    hidden = "".join(f"[\u2064](tg://user?id={i})" for i in admins)
    await message.reply_text("⚠️ Report sent to admins!" + hidden)

# =========================
# ADMIN MODERATION (REPLY)
# =========================

@Client.on_message(filters.group & filters.reply & filters.command("mute"))
async def mute_user(client, message):
    if not await is_admin(client, message.chat.id, message.from_user.id):
        return
    user = message.reply_to_message.from_user
    until = datetime.utcnow() + timedelta(seconds=AUTO_MUTE_TIME)
    await client.restrict_chat_member(
        message.chat.id,
        user.id,
        ChatPermissions(),
        until_date=until
    )
    await message.reply(f"🔇 {user.mention} has been muted")

@Client.on_message(filters.group & filters.reply & filters.command("unmute"))
async def unmute_user(client, message):
    if not await is_admin(client, message.chat.id, message.from_user.id):
        return
    user = message.reply_to_message.from_user
    await client.restrict_chat_member(
        message.chat.id,
        user.id,
        ChatPermissions(can_send_messages=True)
    )
    await message.reply(f"🔊 {user.mention} has been unmuted")

@Client.on_message(filters.group & filters.reply & filters.command("ban"))
async def ban_user(client, message):
    if not await is_admin(client, message.chat.id, message.from_user.id):
        return
    user = message.reply_to_message.from_user
    await client.ban_chat_member(message.chat.id, user.id)
    await message.reply(f"🚫 {user.mention} has been banned")

@Client.on_message(filters.group & filters.reply & filters.command("warn"))
async def warn_cmd(client, message):
    if not await is_admin(client, message.chat.id, message.from_user.id):
        return
    user = message.reply_to_message.from_user
    warns = await warn_user(user.id, message.chat.id)
    await message.reply(f"⚠️ {user.mention} warned ({warns}/{MAX_WARNS})")

@Client.on_message(filters.group & filters.reply & filters.command("resetwarn"))
async def resetwarn_cmd(client, message):
    if not await is_admin(client, message.chat.id, message.from_user.id):
        return
    user = message.reply_to_message.from_user
    await reset_warn(user.id, message.chat.id)
    await message.reply(f"♻️ Warnings reset for {user.mention}")

# =========================
# BLACKLIST SYSTEM
# =========================

@Client.on_message(filters.group & filters.command("addblacklist"))
async def add_blacklist(client, message):
    if not await is_admin(client, message.chat.id, message.from_user.id):
        return
    if len(message.command) < 2:
        return

    word = message.text.split(None, 1)[1].lower()
    data = await db.get_settings(message.chat.id) or {}

    blacklist = data.get("blacklist", [])
    blacklist.append(word)

    data["blacklist"] = list(set(blacklist))
    data.setdefault("blacklist_warn", True)
    await db.update_settings(message.chat.id, data)

@Client.on_message(filters.group & filters.command("removeblacklist"))
async def remove_blacklist(client, message):
    if not await is_admin(client, message.chat.id, message.from_user.id):
        return
    if len(message.command) < 2:
        return

    word = message.text.split(None, 1)[1].lower()
    data = await db.get_settings(message.chat.id) or {}
    blacklist = data.get("blacklist", [])

    if word in blacklist:
        blacklist.remove(word)
        data["blacklist"] = blacklist
        await db.update_settings(message.chat.id, data)

@Client.on_message(filters.group & filters.command("blacklist"))
async def view_blacklist(client, message):
    if not await is_admin(client, message.chat.id, message.from_user.id):
        return

    data = await db.get_settings(message.chat.id) or {}
    blacklist = data.get("blacklist", [])

    if not blacklist:
        return await message.reply("📭 Blacklist is empty")

    await message.reply("\n".join(f"• `{w}`" for w in blacklist))

@Client.on_message(filters.group & filters.command("blacklistwarn"))
async def blacklistwarn(client, message):
    if not await is_admin(client, message.chat.id, message.from_user.id):
        return
    if len(message.command) < 2:
        return

    data = await db.get_settings(message.chat.id) or {}
    data["blacklist_warn"] = message.command[1] == "on"
    await db.update_settings(message.chat.id, data)

@Client.on_message(filters.group & filters.text)
async def blacklist_filter(client, message):
    if not message.from_user:
        return
    if await is_admin(client, message.chat.id, message.from_user.id):
        return

    data = await db.get_settings(message.chat.id) or {}
    blacklist = data.get("blacklist", [])
    warn_on = data.get("blacklist_warn", True)
    text = message.text.lower()

    for word in blacklist:
        if (word.endswith("*") and text.startswith(word[:-1])) or (word in text):
            await message.delete()
            if warn_on:
                await warn_user(message.from_user.id, message.chat.id)
            return

# =========================
# DLINK (DELAYED DELETE) - IMPROVED
# =========================

@Client.on_message(filters.group & filters.command("dlink"))
async def add_dlink(client, message):
    """
    Add delayed delete rule
    Usage: 
      /dlink <word> - Delete after 5 minutes (default)
      /dlink 10m <word> - Delete after 10 minutes
      /dlink 2h <word> - Delete after 2 hours
    """
    if not await is_admin(client, message.chat.id, message.from_user.id):
        return await message.reply("❌ Admin only command!")

    args = message.text.split()
    
    if len(args) < 2:
        return await message.reply(
            "❌ **Invalid Usage!**\n\n"
            "**Examples:**\n"
            "• `/dlink movie` - Delete after 5 min\n"
            "• `/dlink 10m movie` - Delete after 10 min\n"
            "• `/dlink 2h movie` - Delete after 2 hours"
        )
    
    delay = 300  # default 5 min
    index = 1

    # Parse time format: 10m, 2h, etc.
    if len(args) > 2 and args[1][-1] in ("m", "h") and args[1][:-1].isdigit():
        time_value = int(args[1][:-1])
        time_unit = args[1][-1]
        
        if time_unit == "m":
            delay = time_value * 60
        elif time_unit == "h":
            delay = time_value * 3600
        
        index = 2

    word = " ".join(args[index:]).lower()
    
    if not word:
        return await message.reply("❌ Please provide a word/phrase to track!")
    
    data = await db.get_settings(message.chat.id) or {}
    dlink = data.get("dlink", {})

    dlink[word] = delay
    data["dlink"] = dlink
    await db.update_settings(message.chat.id, data)
    
    # Format delay for display
    if delay < 3600:
        delay_str = f"{delay // 60} minute(s)"
    else:
        delay_str = f"{delay // 3600} hour(s)"
    
    await message.reply(
        f"✅ **Dlink Rule Added!**\n\n"
        f"**Word:** `{word}`\n"
        f"**Delete After:** {delay_str}\n\n"
        f"⏰ Added at: {get_ist_time()} IST"
    )

@Client.on_message(filters.group & filters.command("removedlink"))
async def remove_dlink(client, message):
    """Remove delayed delete rule"""
    if not await is_admin(client, message.chat.id, message.from_user.id):
        return await message.reply("❌ Admin only command!")

    if len(message.command) < 2:
        return await message.reply(
            "❌ **Invalid Usage!**\n\n"
            "**Example:** `/removedlink movie`"
        )

    word = message.text.split(None, 1)[1].lower()
    data = await db.get_settings(message.chat.id) or {}
    dlink = data.get("dlink", {})

    if word not in dlink:
        return await message.reply(
            f"❌ **Not Found!**\n\n"
            f"`{word}` is not in dlink list.\n\n"
            f"Use `/dlinklist` to view all rules."
        )

    dlink.pop(word, None)
    data["dlink"] = dlink
    await db.update_settings(message.chat.id, data)
    
    await message.reply(
        f"✅ **Dlink Rule Removed!**\n\n"
        f"**Word:** `{word}`\n"
        f"⏰ Removed at: {get_ist_time()} IST"
    )

@Client.on_message(filters.group & filters.command("dlinklist"))
async def dlink_list(client, message):
    """View all delayed delete rules"""
    if not await is_admin(client, message.chat.id, message.from_user.id):
        return await message.reply("❌ Admin only command!")

    data = await db.get_settings(message.chat.id) or {}
    dlink = data.get("dlink", {})

    if not dlink:
        return await message.reply(
            "📭 **Dlink List is Empty**\n\n"
            "No delayed delete rules set.\n\n"
            "**Add one with:** `/dlink <word>`"
        )

    # Format list
    dlink_text = "📋 **Delayed Delete Rules**\n" + "━" * 30 + "\n\n"
    
    for idx, (word, delay) in enumerate(dlink.items(), 1):
        if delay < 3600:
            delay_str = f"{delay // 60}m"
        else:
            delay_str = f"{delay // 3600}h"
        
        dlink_text += f"{idx}. `{word}` → ⏱️ {delay_str}\n"
    
    dlink_text += f"\n━" + "━" * 30
    dlink_text += f"\n**Total Rules:** {len(dlink)}"
    dlink_text += f"\n⏰ {get_ist_time()} IST"

    await message.reply(dlink_text)

@Client.on_message(filters.group & filters.text, group=10)
async def silent_dlink_handler(client, message):
    """
    Silently delete messages containing dlink words after delay
    Works for ALL users including admins (basic feature)
    Priority: group=10 (runs after other handlers)
    """
    # Skip if no text
    if not message.text:
        return
    
    data = await db.get_settings(message.chat.id) or {}
    dlink = data.get("dlink", {})
    
    if not dlink:
        return
    
    text = message.text.lower()

    for word, delay in dlink.items():
        # Match logic: exact match or wildcard
        matched = False
        
        if word.endswith("*"):
            # Wildcard: "movie*" matches "movie", "movies", etc.
            if text.startswith(word[:-1]):
                matched = True
        else:
            # Exact word match (as whole word or part of text)
            if word in text:
                matched = True
        
        if matched:
            # Schedule deletion
            await asyncio.sleep(delay)
            try:
                await message.delete()
            except Exception as e:
                # Message might be already deleted or bot lacks permission
                pass
            return  # Only delete once per message

# =========================
# ANTI BOT PROTECTION
# =========================

@Client.on_message(filters.new_chat_members)
async def anti_bot(client, message):
    for user in message.new_chat_members:
        if user.is_bot and not await is_admin(client, message.chat.id, message.from_user.id):
            await client.ban_chat_member(message.chat.id, user.id)

# =========================
# HELP COMMAND (GROUP ADMIN ONLY)
# =========================

@Client.on_message(filters.group & filters.command("help"))
async def help_command(client, message):
    if not await is_admin(client, message.chat.id, message.from_user.id):
        return

    help_text = (
        "🛠️ **Admin Help Menu**\n"
        "━━━━━━━━━━━━━━━━━━\n\n"

        "📢 **Report System:**\n"
        "🚨 `/report` or `/Report` – Report a message (reply to message)\n"
        "📣 `@admin` or `@admins` – Alert all admins\n\n"

        "👮 **Moderation (Reply Required):**\n"
        "🔇 `/mute` – Mute a user (10 minutes)\n"
        "🔊 `/unmute` – Unmute a user\n"
        "🚫 `/ban` – Ban a user from group\n"
        "⚠️ `/warn` – Give a warning\n"
        "♻️ `/resetwarn` – Reset user warnings\n\n"

        "🚫 **Blacklist System:**\n"
        "➕ `/addblacklist <word/link>` – Add to blacklist\n"
        "➖ `/removeblacklist <word/link>` – Remove from blacklist\n"
        "📃 `/blacklist` – View blacklist\n"
        "⚙️ `/blacklistwarn on | off` – Warn on blacklist match\n\n"

        "⏱️ **Delayed Delete (DLINK):**\n"
        "🕒 `/dlink <word>` – Delete after 5 minutes\n"
        "🕒 `/dlink 10m <word>` – Delete after 10 minutes\n"
        "🕒 `/dlink 1h <word>` – Delete after 1 hour\n"
        "🗑️ `/removedlink <word>` – Remove delayed delete rule\n"
        "📃 `/dlinklist` – View delayed delete list\n\n"

        "🤖 **Auto Protection:**\n"
        "• Anti-bot system is enabled\n"
        "• Only admins can add bots\n\n"

        "⚠️ **Notes:**\n"
        "• Admin commands work only in groups\n"
        "• Some commands must be used as a reply\n"
        "• `/help` is admin-only\n"
        "• Reports are sent to admin PMs\n"
    )

    await message.reply(help_text)
