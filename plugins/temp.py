import aiohttp
from hydrogram import Client, filters
from hydrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# ─────────────────────────────────────────────
# 🛠️ HELPER FUNCTIONS (API REQUESTS)
# ─────────────────────────────────────────────
async def get_email_address():
    """Generate a random email address"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://www.1secmail.com/api/v1/?action=genRandomMailbox&count=1") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data[0]
    except Exception as e:
        print(f"TempEmail Error: {e}")
    return None

async def get_messages(login, domain):
    """Check inbox for new messages"""
    try:
        async with aiohttp.ClientSession() as session:
            url = f"https://www.1secmail.com/api/v1/?action=getMessages&login={login}&domain={domain}"
            async with session.get(url) as resp:
                if resp.status == 200:
                    return await resp.json()
    except:
        pass
    return []

async def read_message(login, domain, msg_id):
    """Read specific message content"""
    try:
        async with aiohttp.ClientSession() as session:
            url = f"https://www.1secmail.com/api/v1/?action=readMessage&login={login}&domain={domain}&id={msg_id}"
            async with session.get(url) as resp:
                if resp.status == 200:
                    return await resp.json()
    except:
        pass
    return None

# ─────────────────────────────────────────────
# 📧 RANDOM EMAIL GENERATOR
# ─────────────────────────────────────────────
@Client.on_message(filters.command(["email", "temp", "gen", "fake"]))
async def gen_temp_email(client, message):
    msg = await message.reply("🔄 **Generating Temp Mail...**")
    
    email = await get_email_address()
    if not email:
        return await msg.edit("❌ Error generating email. Try again later.")
    
    # Split login and domain for callback data
    login, domain = email.split("@")
    
    text = (
        f"📧 **Your Temporary Email:**\n\n"
        f"`{email}`\n\n"
        f"__Click on the email to copy it.__\n\n"
        f"⚠️ **Note:**\n"
        f"• Messages are deleted after **2-3 hours**.\n"
        f"• Do not use for important accounts.\n"
        f"• Click 'Check Inbox' to refresh."
    )
    
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("📩 Check Inbox", callback_data=f"chk_mail#{login}#{domain}")],
        [InlineKeyboardButton("❌ Close", callback_data="close_data")]
    ])
    
    await msg.edit(text, reply_markup=buttons)

# ─────────────────────────────────────────────
# 🎨 CUSTOM EMAIL GENERATOR (/set_email name)
# ─────────────────────────────────────────────
@Client.on_message(filters.command(["set_email", "custom", "mymail"]))
async def custom_email(client, message):
    if len(message.command) < 2:
        return await message.reply("⚠️ Usage: `/set_email rahul`\n(Only letters and numbers allowed)")
    
    login = message.command[1].lower()
    
    # Validation: Only alphanumeric allowed
    if not login.isalnum():
        return await message.reply("❌ **Invalid Name!** Use only letters (a-z) and numbers (0-9).")
        
    domain = "1secmail.com" # Default reliable domain
    email = f"{login}@{domain}"
    
    text = (
        f"📧 **Your Custom Email:**\n\n"
        f"`{email}`\n\n"
        f"__Click on the email to copy it.__\n\n"
        f"⚠️ **Note:**\n"
        f"• Anyone can access this email if they guess the name.\n"
        f"• Use a unique name for privacy."
    )
    
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("📩 Check Inbox", callback_data=f"chk_mail#{login}#{domain}")],
        [InlineKeyboardButton("❌ Close", callback_data="close_data")]
    ])
    
    await message.reply(text, reply_markup=buttons)

# ─────────────────────────────────────────────
# 📩 CHECK INBOX (CALLBACK)
# ─────────────────────────────────────────────
@Client.on_callback_query(filters.regex(r"^chk_mail#"))
async def check_temp_inbox(client, query):
    _, login, domain = query.data.split("#")
    email = f"{login}@{domain}"
    
    # Check messages
    messages = await get_messages(login, domain)
    
    if not messages:
        return await query.answer("❌ Inbox is Empty! Refresh later.", show_alert=True)
    
    # Create buttons for messages
    buttons = []
    for msg in messages[:5]: # Show max 5 latest emails
        buttons.append([
            InlineKeyboardButton(
                f"📨 {msg['subject'][:20]}... | {msg['from'][:10]}...", 
                callback_data=f"read_mail#{msg['id']}#{login}#{domain}"
            )
        ])
    
    buttons.append([InlineKeyboardButton("🔄 Refresh Inbox", callback_data=f"chk_mail#{login}#{domain}")])
    buttons.append([InlineKeyboardButton("🔙 Back", callback_data=f"back_mail#{login}#{domain}")])
    
    await query.message.edit(
        f"📬 **Inbox for:** `{email}`\n\n👇 Click on a message to read it:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# ─────────────────────────────────────────────
# 📖 READ MESSAGE (CALLBACK)
# ─────────────────────────────────────────────
@Client.on_callback_query(filters.regex(r"^read_mail#"))
async def read_temp_message(client, query):
    _, msg_id, login, domain = query.data.split("#")
    
    await query.answer("🔄 Fetching email content...")
    
    email_data = await read_message(login, domain, msg_id)
    if not email_data:
        return await query.answer("❌ Error reading email!", show_alert=True)
    
    # content handling
    body = email_data.get('textBody') or email_data.get('body') or "No Text Content"
    
    text = (
        f"📨 **From:** `{email_data['from']}`\n"
        f"📌 **Subject:** `{email_data['subject']}`\n"
        f"📅 **Date:** `{email_data['date']}`\n\n"
        f"📜 **Message:**\n{body[:3500]}" # Limit text
    )
    
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back to Inbox", callback_data=f"chk_mail#{login}#{domain}")],
        [InlineKeyboardButton("❌ Close", callback_data="close_data")]
    ])
    
    await query.message.edit(text, reply_markup=buttons)

# ─────────────────────────────────────────────
# 🔙 BACK BUTTON LOGIC
# ─────────────────────────────────────────────
@Client.on_callback_query(filters.regex(r"^back_mail#"))
async def back_to_mail_home(client, query):
    _, login, domain = query.data.split("#")
    email = f"{login}@{domain}"
    
    text = (
        f"📧 **Your Email:**\n\n"
        f"`{email}`\n\n"
        f"__Click on the email to copy it.__"
    )
    
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("📩 Check Inbox", callback_data=f"chk_mail#{login}#{domain}")],
        [InlineKeyboardButton("❌ Close", callback_data="close_data")]
    ])
    
    await query.message.edit(text, reply_markup=buttons)
