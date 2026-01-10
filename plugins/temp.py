import aiohttp
import asyncio
from hydrogram import Client, filters
from hydrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# ─────────────────────────────────────────────
# 🛠️ MAIL.TM API CONFIGURATION
# ─────────────────────────────────────────────
BASE_URL = "https://api.mail.tm"
HEADERS = {
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (TelegramBot)"
}
# सभी टेम्प मेल के लिए एक कॉमन पासवर्ड (स्टेटलेस रहने के लिए)
COMMON_PASSWORD = "TempPassword123!" 

async def get_domain():
    """Get available domain"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{BASE_URL}/domains", headers=HEADERS) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data['hydra:member'][0]['domain']
    except:
        pass
    return "kool.kz" # Fallback

async def create_account(username, domain):
    """Create account on Mail.tm"""
    email = f"{username}@{domain}"
    data = {"address": email, "password": COMMON_PASSWORD}
    
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{BASE_URL}/accounts", json=data, headers=HEADERS) as resp:
            if resp.status in [201, 422]: # 201=Created, 422=Already Exists (Good)
                return email
    return None

async def get_auth_token(email):
    """Login and get JWT Token"""
    data = {"address": email, "password": COMMON_PASSWORD}
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{BASE_URL}/token", json=data, headers=HEADERS) as resp:
            if resp.status == 200:
                return (await resp.json())['token']
    return None

async def get_tm_messages(email):
    """Get messages using Token"""
    token = await get_auth_token(email)
    if not token: return []
    
    auth_headers = {**HEADERS, "Authorization": f"Bearer {token}"}
    
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{BASE_URL}/messages", headers=auth_headers) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data['hydra:member']
    return []

async def read_tm_message(email, msg_id):
    """Read full message"""
    token = await get_auth_token(email)
    if not token: return None

    auth_headers = {**HEADERS, "Authorization": f"Bearer {token}"}
    
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{BASE_URL}/messages/{msg_id}", headers=auth_headers) as resp:
            if resp.status == 200:
                return await resp.json()
    return None

# ─────────────────────────────────────────────
# 📧 GENERATE EMAIL COMMAND
# ─────────────────────────────────────────────
@Client.on_message(filters.command(["email", "temp", "gen"]))
async def gen_temp_email(client, message):
    msg = await message.reply("🔄 **Connecting to Secure Mail Server...**")
    
    import random
    import string
    
    # Random Username
    username = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
    domain = await get_domain()
    
    email = await create_account(username, domain)
    
    if not email:
        return await msg.edit("❌ **Server Error!** Try again later.")
    
    text = (
        f"📧 **Your Premium Temp Mail:**\n\n"
        f"`{email}`\n\n"
        f"__Click to copy. This address is permanent until you delete it.__\n"
        f"⚡ Powered by Mail.tm"
    )
    
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("📩 Check Inbox", callback_data=f"tm_chk#{email}")],
        [InlineKeyboardButton("❌ Close", callback_data="close_data")]
    ])
    
    await msg.edit(text, reply_markup=buttons)

# ─────────────────────────────────────────────
# 📩 CHECK INBOX (CALLBACK)
# ─────────────────────────────────────────────
@Client.on_callback_query(filters.regex(r"^tm_chk#"))
async def check_tm_inbox(client, query):
    _, email = query.data.split("#")
    
    # Check messages
    messages = await get_tm_messages(email)
    
    if not messages:
        return await query.answer("📭 Inbox Empty! Refresh in a few seconds.", show_alert=True)
    
    buttons = []
    for msg in messages[:5]: 
        buttons.append([
            InlineKeyboardButton(
                f"📨 {msg['subject'][:20]}...", 
                callback_data=f"tm_read#{msg['id']}#{email}"
            )
        ])
    
    buttons.append([InlineKeyboardButton("🔄 Refresh", callback_data=f"tm_chk#{email}")])
    buttons.append([InlineKeyboardButton("🔙 Back", callback_data=f"tm_back#{email}")])
    
    await query.message.edit(
        f"📬 **Inbox for:** `{email}`\n\n👇 Click to read:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# ─────────────────────────────────────────────
# 📖 READ MESSAGE
# ─────────────────────────────────────────────
@Client.on_callback_query(filters.regex(r"^tm_read#"))
async def read_tm_content(client, query):
    _, msg_id, email = query.data.split("#")
    
    await query.answer("🔄 Downloading content...")
    
    data = await read_tm_message(email, msg_id)
    if not data:
        return await query.answer("❌ Error opening email.", show_alert=True)
    
    text = (
        f"📨 **From:** `{data['from']['address']}`\n"
        f"📌 **Subject:** `{data['subject']}`\n\n"
        f"📜 **Message:**\n{data.get('text', 'No Text Content')[:3500]}"
    )
    
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back", callback_data=f"tm_chk#{email}")],
        [InlineKeyboardButton("❌ Close", callback_data="close_data")]
    ])
    
    await query.message.edit(text, reply_markup=buttons)

# ─────────────────────────────────────────────
# 🔙 BACK LOGIC
# ─────────────────────────────────────────────
@Client.on_callback_query(filters.regex(r"^tm_back#"))
async def back_tm_home(client, query):
    _, email = query.data.split("#")
    
    text = (
        f"📧 **Your Email:**\n\n"
        f"`{email}`"
    )
    
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("📩 Check Inbox", callback_data=f"tm_chk#{email}")],
        [InlineKeyboardButton("❌ Close", callback_data="close_data")]
    ])
    
    await query.message.edit(text, reply_markup=buttons)
