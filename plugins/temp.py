import aiohttp
import asyncio
from hydrogram import Client, filters
from hydrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# ─────────────────────────────────────────────
# 🛠️ 1SECMAIL API CONFIGURATION
# ─────────────────────────────────────────────
API_URL = "https://www.1secmail.com/api/v1/"

async def generate_email():
    """Generate a random email address"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{API_URL}?action=genRandomMailbox&count=1") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data[0]
    except Exception as e:
        print(f"Gen Error: {e}")
    return None

async def get_messages(email):
    """Check inbox for new messages"""
    login, domain = email.split("@")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{API_URL}?action=getMessages&login={login}&domain={domain}") as resp:
                if resp.status == 200:
                    return await resp.json()
    except Exception as e:
        print(f"Check Error: {e}")
    return []

async def read_message(email, msg_id):
    """Read specific message content"""
    login, domain = email.split("@")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{API_URL}?action=readMessage&login={login}&domain={domain}&id={msg_id}") as resp:
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
    msg = await message.reply("🔄 **Generating Temporary Email...**")
    
    email = await generate_email()
    
    if not email:
        return await msg.edit("❌ **Error!** API Down or IP Blocked. Try again later.")
    
    text = (
        f"📧 **Your Temp Mail:**\n\n"
        f"`{email}`\n\n"
        f"__Click to copy. Inbox checks automatically.__\n"
        f"⚡ Powered by 1secmail"
    )
    
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("📩 Check Inbox", callback_data=f"sec_chk#{email}")],
        [InlineKeyboardButton("❌ Close", callback_data="close_data")]
    ])
    
    await msg.edit(text, reply_markup=buttons)

# ─────────────────────────────────────────────
# 📩 CHECK INBOX (CALLBACK)
# ─────────────────────────────────────────────
@Client.on_callback_query(filters.regex(r"^sec_chk#"))
async def check_inbox(client, query):
    _, email = query.data.split("#")
    
    messages = await get_messages(email)
    
    if not messages:
        return await query.answer("📭 Inbox Empty! Refresh in a few seconds.", show_alert=True)
    
    buttons = []
    for msg in messages[:5]: # Show last 5 emails
        subject = msg.get('subject', 'No Subject')
        if len(subject) > 20:
            subject = subject[:20] + "..."
            
        buttons.append([
            InlineKeyboardButton(
                f"📨 {subject}", 
                callback_data=f"sec_read#{msg['id']}#{email}"
            )
        ])
    
    buttons.append([InlineKeyboardButton("🔄 Refresh", callback_data=f"sec_chk#{email}")])
    buttons.append([InlineKeyboardButton("🔙 Back", callback_data=f"sec_back#{email}")])
    
    await query.message.edit(
        f"📬 **Inbox for:** `{email}`\n\n👇 Click to read:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# ─────────────────────────────────────────────
# 📖 READ MESSAGE
# ─────────────────────────────────────────────
@Client.on_callback_query(filters.regex(r"^sec_read#"))
async def read_content(client, query):
    _, msg_id, email = query.data.split("#")
    
    await query.answer("🔄 Fetching email content...")
    
    data = await read_message(email, msg_id)
    if not data:
        return await query.answer("❌ Error opening email.", show_alert=True)
    
    # 1secmail returns HTML and Text body. We prefer textBody.
    body = data.get('textBody', data.get('body', 'No Content'))
    
    text = (
        f"📨 **From:** `{data['from']}`\n"
        f"📌 **Subject:** `{data['subject']}`\n"
        f"🕒 **Date:** `{data['date']}`\n\n"
        f"📜 **Message:**\n{body[:3500]}"
    )
    
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back", callback_data=f"sec_chk#{email}")],
        [InlineKeyboardButton("❌ Close", callback_data="close_data")]
    ])
    
    await query.message.edit(text, reply_markup=buttons)

# ─────────────────────────────────────────────
# 🔙 BACK LOGIC
# ─────────────────────────────────────────────
@Client.on_callback_query(filters.regex(r"^sec_back#"))
async def back_home(client, query):
    _, email = query.data.split("#")
    
    text = (
        f"📧 **Your Email:**\n\n"
        f"`{email}`"
    )
    
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("📩 Check Inbox", callback_data=f"sec_chk#{email}")],
        [InlineKeyboardButton("❌ Close", callback_data="close_data")]
    ])
    
    await query.message.edit(text, reply_markup=buttons)
