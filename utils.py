import asyncio
import re
import requests
from datetime import datetime, timedelta
from hydrogram.errors import FloodWait
from hydrogram import enums
from hydrogram.types import InlineKeyboardButton

from info import ADMINS, IS_PREMIUM, TIME_ZONE, LOG_CHANNEL
from database.users_chats_db import db


# ─────────────────────────────────────────────
# 🧠 TEMP RUNTIME STORAGE
# ─────────────────────────────────────────────
class temp(object):
    START_TIME = 0
    BANNED_USERS = []
    BANNED_CHATS = []
    ME = None
    CANCEL = False
    U_NAME = None
    B_NAME = None
    SETTINGS = {}
    FILES = {}
    USERS_CANCEL = False
    GROUPS_CANCEL = False
    BOT = None
    PREMIUM = {}
    PM_FILES = {}


# ─────────────────────────────────────────────
# 👮 ADMIN CHECK
# ─────────────────────────────────────────────
async def is_check_admin(bot, chat_id, user_id):
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        return member.status in (
            enums.ChatMemberStatus.ADMINISTRATOR,
            enums.ChatMemberStatus.OWNER
        )
    except Exception:
        return False


# ─────────────────────────────────────────────
# 💎 PREMIUM SYSTEM (Synced with Premium.py)
# ─────────────────────────────────────────────
async def is_premium(user_id, bot):
    """Check if user has active premium subscription"""
    if not IS_PREMIUM:
        return True
    if user_id in ADMINS:
        return True

    mp = db.get_plan(user_id)
    if mp.get("premium"):
        if mp.get("expire") and mp["expire"] < datetime.now():
            try:
                await bot.send_message(
                    user_id,
                    f"❌ Your premium {mp.get('plan')} plan has expired.\n\nUse /plan to renew your subscription."
                )
            except Exception:
                pass

            mp.update({
                "expire": "",
                "plan": "",
                "premium": False
            })
            db.update_plan(user_id, mp)
            return False
        return True
    return False


async def check_premium(bot):
    """
    Background task that runs every 20 minutes to:
    1. Check expired premium users
    2. Send expiry reminders (24h, 6h, 1h before expiry)
    
    ⚠️ NOTE: This function is now replaced by check_premium_expired() in Premium.py
    This is kept for backward compatibility only.
    """
    while True:
        try:
            current_time = datetime.now()
            
            for p in db.get_premium_users():
                user_id = p.get("id")
                mp = p.get("status", {})
                
                if mp.get("premium") and mp.get("expire"):
                    expire_time = mp["expire"]
                    time_left = expire_time - current_time
                    
                    # Check if expired
                    if time_left.total_seconds() <= 0:
                        try:
                            await bot.send_message(
                                user_id,
                                f"❌ Your premium {mp.get('plan')} plan has expired.\n\n"
                                f"Expired on: {expire_time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                                f"Use /plan to renew your subscription."
                            )
                        except Exception as e:
                            print(f"Failed to notify user {user_id}: {e}")

                        mp.update({
                            "expire": "",
                            "plan": "",
                            "premium": False
                        })
                        db.update_plan(user_id, mp)
                        
                        # Log to admin channel
                        try:
                            await bot.send_message(
                                LOG_CHANNEL,
                                f"#PremiumExpired\n\n"
                                f"User ID: {user_id}\n"
                                f"Plan: {mp.get('plan', 'Unknown')}\n"
                                f"Expired: {expire_time.strftime('%Y-%m-%d %H:%M:%S')}"
                            )
                        except:
                            pass
                    
                    # Send reminders
                    else:
                        hours_left = time_left.total_seconds() / 3600
                        
                        # 24 hour reminder
                        if 23.5 <= hours_left <= 24.5 and not mp.get("reminded_24h"):
                            try:
                                await bot.send_message(
                                    user_id,
                                    f"⏰ <b>Premium Expiry Reminder</b>\n\n"
                                    f"Your premium {mp.get('plan')} plan will expire in 24 hours.\n"
                                    f"Expiry time: {expire_time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                                    f"Use /plan to renew your subscription.",
                                    parse_mode=enums.ParseMode.HTML
                                )
                                mp["reminded_24h"] = True
                                db.update_plan(user_id, mp)
                            except Exception as e:
                                print(f"Failed to send 24h reminder to {user_id}: {e}")
                        
                        # 6 hour reminder
                        elif 5.5 <= hours_left <= 6.5 and not mp.get("reminded_6h"):
                            try:
                                await bot.send_message(
                                    user_id,
                                    f"⚠️ <b>Premium Expiry Alert</b>\n\n"
                                    f"Your premium {mp.get('plan')} plan will expire in 6 hours.\n"
                                    f"Expiry time: {expire_time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                                    f"Use /plan to renew now!",
                                    parse_mode=enums.ParseMode.HTML
                                )
                                mp["reminded_6h"] = True
                                db.update_plan(user_id, mp)
                            except Exception as e:
                                print(f"Failed to send 6h reminder to {user_id}: {e}")
                        
                        # 1 hour reminder
                        elif 0.5 <= hours_left <= 1.5 and not mp.get("reminded_1h"):
                            try:
                                await bot.send_message(
                                    user_id,
                                    f"🚨 <b>URGENT: Premium Expiring Soon</b>\n\n"
                                    f"Your premium {mp.get('plan')} plan will expire in 1 hour!\n"
                                    f"Expiry time: {expire_time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                                    f"Renew immediately to avoid service interruption: /plan",
                                    parse_mode=enums.ParseMode.HTML
                                )
                                mp["reminded_1h"] = True
                                db.update_plan(user_id, mp)
                            except Exception as e:
                                print(f"Failed to send 1h reminder to {user_id}: {e}")
            
            # Check every 20 minutes (1200 seconds)
            await asyncio.sleep(1200)
            
        except Exception as e:
            print(f"Error in check_premium: {e}")
            await asyncio.sleep(1200)


def get_premium_button():
    """Get standard premium button"""
    return InlineKeyboardButton('💎 Buy Premium', url=f"https://t.me/{temp.U_NAME}?start=premium")


def premium_required(func):
    """Decorator to check if user has premium access"""
    async def wrapper(client, message):
        if not await is_premium(message.from_user.id, client):
            from hydrogram.types import InlineKeyboardMarkup
            btn = [[get_premium_button()]]
            return await message.reply(
                '🔒 <b>Premium Feature</b>\n\n'
                'This feature is only available for premium users!\n\n'
                'Use /plan to activate premium subscription.',
                reply_markup=InlineKeyboardMarkup(btn),
                parse_mode=enums.ParseMode.HTML
            )
        return await func(client, message)
    return wrapper


# ─────────────────────────────────────────────
# 📢 BROADCAST
# ─────────────────────────────────────────────
async def broadcast_messages(user_id, message, pin=False):
    try:
        msg = await message.copy(chat_id=user_id)
        if pin:
            await msg.pin(both_sides=True)
        return "Success"
    except FloodWait as e:
        await asyncio.sleep(e.value)
        return await broadcast_messages(user_id, message, pin)
    except Exception:
        await db.delete_user(int(user_id))
        return "Error"


async def groups_broadcast_messages(chat_id, message, pin=False):
    try:
        msg = await message.copy(chat_id=chat_id)
        if pin:
            try:
                await msg.pin()
            except Exception:
                pass
        return "Success"
    except FloodWait as e:
        await asyncio.sleep(e.value)
        return await groups_broadcast_messages(chat_id, message, pin)
    except Exception:
        await db.delete_chat(chat_id)
        return "Error"


# ─────────────────────────────────────────────
# ⚙️ GROUP SETTINGS (CACHE)
# ─────────────────────────────────────────────
async def get_settings(group_id):
    settings = temp.SETTINGS.get(group_id)
    if not settings:
        settings = await db.get_settings(group_id)
        temp.SETTINGS[group_id] = settings
    return settings


async def save_group_settings(group_id, key, value):
    current = await get_settings(group_id)
    current[key] = value
    temp.SETTINGS[group_id] = current
    await db.update_settings(group_id, current)


# ─────────────────────────────────────────────
# 🚫 FORCE SUB REMOVED (DUMMY)
# ─────────────────────────────────────────────
async def is_subscribed(bot, query):
    """
    Force subscribe system removed.
    Dummy function for compatibility.
    """
    return []


# ─────────────────────────────────────────────
# 🖼 IMAGE UPLOAD (img_2_link)
# ─────────────────────────────────────────────
def upload_image(file_path: str):
    try:
        with open(file_path, "rb") as f:
            response = requests.post(
                "https://uguu.se/upload",
                files={"files[]": f},
                timeout=30
            )
        if response.status_code == 200:
            data = response.json()
            return data["files"][0]["url"].replace("\\/", "/")
    except Exception:
        pass
    return None


# ─────────────────────────────────────────────
# 📦 UTILS
# ─────────────────────────────────────────────
def get_size(size):
    units = ["Bytes", "KB", "MB", "GB", "TB"]
    size = float(size)
    i = 0
    while size >= 1024 and i < len(units) - 1:
        size /= 1024
        i += 1
    return f"{size:.2f} {units[i]}"


def get_readable_time(seconds):
    periods = [('d', 86400), ('h', 3600), ('m', 60), ('s', 1)]
    result = ''
    for name, sec in periods:
        if seconds >= sec:
            val, seconds = divmod(seconds, sec)
            result += f"{int(val)}{name}"
    return result or "0s"


def get_wish():
    hour = datetime.now().hour
    if hour < 12:
        return "ɢᴏᴏᴅ ᴍᴏʀɴɪɴɢ 🌞"
    elif hour < 18:
        return "ɢᴏᴏᴅ ᴀꜰᴛᴇʀɴᴏᴏɴ 🌗"
    return "ɢᴏᴏᴅ ᴇᴠᴇɴɪɴɢ 🌘"


async def get_seconds(time_string):
    match = re.match(r"(\d+)(s|min|hour|day|month|year)", time_string)
    if not match:
        return 0

    value, unit = int(match.group(1)), match.group(2)
    return {
        "s": value,
        "min": value * 60,
        "hour": value * 3600,
        "day": value * 86400,
        "month": value * 86400 * 30,
        "year": value * 86400 * 365
    }.get(unit, 0)
