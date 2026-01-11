import aiohttp
import asyncio
import random
import string
from hydrogram import Client, filters
from hydrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# ─────────────────────────────────────────────
# 🛠️ TEMPMAIL.PLUS CONFIGURATION (Bypass Block)
# ─────────────────────────────────────────────
# हम API से ईमेल नहीं मांगेंगे, खुद बनाएंगे ताकि IP Block न हो।
VALID_DOMAINS = [
    "fexpost.com", "fexbox.org", "mailbox.in.ua", 
    "rover.info", "inpwa.com", "intopwa.com", "tofeat.com"
]

def generate_local_email():
    """Generate email locally to bypass API rate limits"""
    username = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    domain = random.choice(VALID_DOMAINS)
    return f"{username}@{domain}"

async def get_plus_messages(email):
    """Check inbox on TempMail.plus"""
    try:
        async with aiohttp.ClientSession() as session:
            # API call only to check mail, not to create account
            url = f"https://tempmail.plus/api/mails?email={email}&limit=10"
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get('mail_list', [])
    except Exception as e:
        print(f"Check Error: {e}")
    return []

async def read_plus_message(email, msg_id):
    """Read specific message content"""
    try:
        async with aiohttp.ClientSession() as session:
            url = f"https://tempmail.plus/api/mails/{msg_id}?email={email}"
            async with session.get(url) as resp:
                if resp.status == 200:
                    return await resp.json()
    except Exception as e:
        print(f"Read Error: {e}")
    return None

# ─────────────────────────────────────────────
# 📧 GENERATE EMAIL COMMAND
# ─────────────────────────────────────────────
@Client.on_message(filters.command(["email", "temp", "gen"]))
async def gen_temp_email(client, message):
    msg = await message.reply("🔄 **Generating Magic Email...**")
    
    # Local Generation (100% Success Rate)
    email = generate_local_email()
    
    text = (
        f"📧 **Your Temp Mail:**\n\n"
        f"`{email}`\n\n"
        f"__This works flawlessly on Cloud Servers.__\n"
        f"⚡ Powered by TempMail.plus"
    )
    
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("📩 Check Inbox", callback_data=f"plus_chk#{email}")],
        [InlineKeyboardButton("❌ Close", callback_data="close_data")]
    ])
    
    await msg.edit(text, reply_markup=buttons)

# ─────────────────────────────────────────────
# 📩 CHECK INBOX (CALLBACK)
# ─────────────────────────────────────────────
@Client.on_callback_query(filters.regex(r"^plus_chk#"))
async def check_inbox(client, query):
    _, email = query.data.split("#")
    
    messages = await get_plus_messages(email)
    
    if not messages:
        return await query.answer("📭 Inbox Empty! Refresh in a few seconds.", show_alert=True)
    
    buttons = []
    for msg in messages[:5]: 
        subject = msg.get('subject', 'No Subject')
        if len(subject) > 20: subject = subject[:20] + "..."
        
        # TempMail.plus uses 'mail_id' or 'id'
        msg_id = msg.get('mail_id', msg.get('id'))
        
        buttons.append([
            InlineKeyboardButton(
                f"📨 {subject}", 
                callback_data=f"plus_read#{msg_id}#{email}"
            )
        ])
    
    buttons.append([InlineKeyboardButton("🔄 Refresh", callback_data=f"plus_chk#{email}")])
    buttons.append([InlineKeyboardButton("🔙 Back", callback_data=f"plus_back#{email}")])
    
    await query.message.edit(
        f"📬 **Inbox for:** `{email}`\n\n👇 Click to read:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# ─────────────────────────────────────────────
# 📖 READ MESSAGE
# ─────────────────────────────────────────────
@Client.on_callback_query(filters.regex(r"^plus_read#"))
async def read_content(client, query):
    _, msg_id, email = query.data.split("#")
    
    await query.answer("🔄 Fetching email content...")
    
    data = await read_plus_message(email, msg_id)
    if not data:
        return await query.answer("❌ Error opening email.", show_alert=True)
    
    # Content Handling
    text_content = data.get('text', data.get('html', 'No Content'))
    # Basic cleanup if needed, or send as is
    
    text = (
        f"📨 **From:** `{data.get('from_mail', 'Unknown')}`\n"
        f"📌 **Subject:** `{data.get('subject', 'No Subject')}`\n"
        f"🕒 **Date:** `{data.get('date', 'Unknown')}`\n\n"
        f"📜 **Message:**\n{text_content[:3500]}"
    )
    
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back", callback_data=f"plus_chk#{email}")],
        [InlineKeyboardButton("❌ Close", callback_data="close_data")]
    ])
    
    await query.message.edit(text, reply_markup=buttons)

# ─────────────────────────────────────────────
# 🔙 BACK LOGIC
# ─────────────────────────────────────────────
@Client.on_callback_query(filters.regex(r"^plus_back#"))
async def back_home(client, query):
    _, email = query.data.split("#")
    
    text = (
        f"📧 **Your Email:**\n\n"
        f"`{email}`"
    )
    
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("📩 Check Inbox", callback_data=f"plus_chk#{email}")],
        [InlineKeyboardButton("❌ Close", callback_data="close_data")]
    ])
    
    await query.message.edit(text, reply_markup=buttons)
