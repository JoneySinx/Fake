import asyncio
import re
import math
import random
from hydrogram import Client, filters, enums
from hydrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# ✅ Updated Imports (Ensure these exist)
from info import ADMINS, DELETE_TIME, MAX_BTN, IS_PREMIUM, PICS
from utils import is_premium, get_size, is_check_admin, temp, get_settings, save_group_settings
from database.ia_filterdb import get_search_results # डेटाबेस फाइल से सर्च फंक्शन

# ─────────────────────────────────────────────
# ⚡ GLOBAL CACHE (Auto-Cleaner)
# ─────────────────────────────────────────────
BUTTONS = {}

def check_cache_limit():
    """Koyeb RAM Saver: Clears cache if it gets too big"""
    if len(BUTTONS) > 500:  # 1000 थोड़ा ज्यादा हो सकता है, 500 सेफ है
        BUTTONS.clear()
        temp.FILES.clear()

# ─────────────────────────────────────────────
# 🛠️ VALIDATOR
# ─────────────────────────────────────────────
async def is_valid_search(message):
    """Checks if message is a valid search query"""
    if not message.text or message.text.startswith("/"):
        return False
    
    # Ignore Forwards & Media
    if message.forward_date or message.photo or message.video or message.document:
        return False
        
    # Ignore Links
    if message.entities:
        for entity in message.entities:
            if entity.type in [enums.MessageEntityType.URL, enums.MessageEntityType.TEXT_LINK]:
                return False
                
    # Ignore Symbols only
    if not any(c.isalnum() for c in message.text):
        return False
        
    return True

# ─────────────────────────────────────────────
# 🔍 PRIVATE SEARCH
# ─────────────────────────────────────────────
@Client.on_message(filters.private & filters.text & filters.incoming)
async def pm_search(client, message):
    if not await is_valid_search(message):
        return

    if IS_PREMIUM and not await is_premium(message.from_user.id, client):
        return await message.reply_photo(
            random.choice(PICS),
            caption="🔒 **Premium Required**\n\nOnly Premium users can use this bot in DM.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("💎 Buy Premium", callback_data="activate_plan"),
                InlineKeyboardButton("📊 My Plan", callback_data="myplan")
            ]])
        )

    await auto_filter(client, message, collection_type="all")

# ─────────────────────────────────────────────
# 🔍 GROUP SEARCH
# ─────────────────────────────────────────────
@Client.on_message(filters.group & filters.text & filters.incoming)
async def group_search(client, message):
    if not await is_valid_search(message):
        return

    chat_id = message.chat.id
    user_id = message.from_user.id

    # 1. Settings Check
    settings = await get_settings(chat_id)
    if not settings.get("search_enabled", True):
        return

    # 2. Premium Check
    if IS_PREMIUM and not await is_premium(user_id, client):
        return

    text_lower = message.text.lower()

    # 3. Admin Report Logic (Safe)
    if "@admin" in text_lower:
        if await is_check_admin(client, chat_id, user_id):
            return
        
        mentions = []
        async for m in client.get_chat_administrators(chat_id):
            if not m.user.is_bot:
                mentions.append(f"<a href='tg://user?id={m.user.id}'>\u2063</a>")
        
        await message.reply(f"✅ Report sent to admins!{''.join(mentions)}")
        return

    # 4. Link Blocking
    if "http" in text_lower or "t.me/" in text_lower:
        if re.search(r"(?:http|www\.|t\.me/)", text_lower):
            if not await is_check_admin(client, chat_id, user_id):
                try: await message.delete()
                except: pass
                msg = await message.reply("❌ Links not allowed!", quote=True)
                await asyncio.sleep(5)
                try: await msg.delete()
                except: pass
                return

    await auto_filter(client, message, collection_type="all")

# ─────────────────────────────────────────────
# ⚙️ ADMIN TOGGLE
# ─────────────────────────────────────────────
@Client.on_message(filters.command("search") & filters.group)
async def search_toggle(client, message):
    if not await is_check_admin(client, message.chat.id, message.from_user.id):
        return

    if len(message.command) < 2:
        return await message.reply("Usage: `/search on` or `/search off`")

    action = message.command[1].lower()
    state = True if action == "on" else False
    
    await save_group_settings(message.chat.id, "search_enabled", state)
    await message.reply(f"✅ Search is now **{'ENABLED' if state else 'DISABLED'}**")

# ─────────────────────────────────────────────
# 🚀 AUTO FILTER CORE
# ─────────────────────────────────────────────
async def auto_filter(client, msg, collection_type="all"):
    check_cache_limit() 

    search = msg.text.strip()
    
    # ⚡ DB Call
    files, next_offset, total, actual_source = await get_search_results(
        search, max_results=MAX_BTN, offset=0, collection_type=collection_type
    )

    if not files:
        try:
            # Send and auto-delete "Not Found"
            m = await msg.reply(f"❌ No results for <b>{search}</b>", quote=True)
            await asyncio.sleep(5)
            await m.delete()
        except:
            pass
        return

    key = f"{msg.chat.id}-{msg.id}"
    temp.FILES[key] = files
    BUTTONS[key] = search

    # ⚡ Link Generation
    list_items = []
    for file in files:
        # यहाँ हम _id (Unique ID with access_hash) का उपयोग कर रहे हैं जो सुरक्षित है
        f_link = f"https://t.me/{temp.U_NAME}?start=file_{msg.chat.id}_{file['_id']}"
        
        # फाइल का नाम और साइज
        list_items.append(
            f"📁 <a href='{f_link}'>[{get_size(file['file_size'])}] {file['file_name']}</a>"
        )
    
    files_text = "\n\n".join(list_items)
    total_pages = math.ceil(total / MAX_BTN)
    
    cap = (
        f"<b>👑 Search: {search}\n"
        f"🎬 Total: {total}\n"
        f"📚 Source: {actual_source.upper()}\n"
        f"📄 Page: 1/{total_pages}</b>\n\n"
        f"{files_text}"
    )

    # Buttons
    btn = []
    nav = [InlineKeyboardButton(f"📄 1/{total_pages}", callback_data="pages")]
    if next_offset:
        # Note: 'pri' is short for primary to save callback bytes
        nav.append(InlineKeyboardButton("Next »", callback_data=f"nav_{msg.from_user.id}_{key}_{next_offset}_{actual_source}"))
    btn.append(nav)

    # Collection Buttons
    col_btn = []
    for c in ["primary", "cloud", "archive"]:
        tick = "✅" if c == actual_source else "📂"
        col_btn.append(InlineKeyboardButton(f"{tick} {c.title()}", callback_data=f"coll_{msg.from_user.id}_{key}_{c}"))
    btn.append(col_btn)

    btn.append([InlineKeyboardButton("❌ Close", callback_data="close_data")])

    try:
        m = await msg.reply(cap, reply_markup=InlineKeyboardMarkup(btn), disable_web_page_preview=True, quote=True)
        
        # Auto Delete Logic
        settings = await get_settings(msg.chat.id)
        if settings.get("auto_delete"):
            asyncio.create_task(auto_delete_msg(m, msg))
    except Exception as e:
        print(f"Error sending filter: {e}")

async def auto_delete_msg(bot_msg, user_msg):
    await asyncio.sleep(DELETE_TIME)
    try: await bot_msg.delete()
    except: pass
    try: await user_msg.delete()
    except: pass

# ─────────────────────────────────────────────
# 🔁 NAVIGATION HANDLER
# ─────────────────────────────────────────────
@Client.on_callback_query(filters.regex(r"^nav_"))
async def nav_handler(client, query):
    try:
        _, req, key, offset, coll_type = query.data.split("_", 4)
        if int(req) != query.from_user.id:
            return await query.answer("❌ Not for you!", show_alert=True)
    except:
        return await query.answer("❌ Error!", show_alert=True)

    if IS_PREMIUM and not await is_premium(query.from_user.id, client):
        return await query.answer("❌ Premium Expired!", show_alert=True)

    search = BUTTONS.get(key)
    if not search:
        return await query.answer("❌ Search Expired! Search again.", show_alert=True)

    files, next_off, total, act_src = await get_search_results(
        search, max_results=MAX_BTN, offset=int(offset), collection_type=coll_type
    )
    if not files: return await query.answer("❌ No more pages!", show_alert=True)

    temp.FILES[key] = files

    list_items = []
    for file in files:
        f_link = f"https://t.me/{temp.U_NAME}?start=file_{query.message.chat.id}_{file['_id']}"
        list_items.append(f"📁 <a href='{f_link}'>[{get_size(file['file_size'])}] {file['file_name']}</a>")
    
    files_text = "\n\n".join(list_items)
    total_pages = math.ceil(total / MAX_BTN)
    curr_page = (int(offset) // MAX_BTN) + 1
    
    cap = (
        f"<b>👑 Search: {search}\n"
        f"🎬 Total: {total}\n"
        f"📚 Source: {act_src.upper()}\n"
        f"📄 Page: {curr_page}/{total_pages}</b>\n\n"
        f"{files_text}"
    )

    btn = []
    nav = []
    prev_off = int(offset) - MAX_BTN
    
    if prev_off >= 0:
        nav.append(InlineKeyboardButton("« Prev", callback_data=f"nav_{req}_{key}_{prev_off}_{act_src}"))
    
    nav.append(InlineKeyboardButton(f"📄 {curr_page}/{total_pages}", callback_data="pages"))
    
    if next_off:
        nav.append(InlineKeyboardButton("Next »", callback_data=f"nav_{req}_{key}_{next_off}_{act_src}"))
    btn.append(nav)

    col_btn = []
    for c in ["primary", "cloud", "archive"]:
        tick = "✅" if c == act_src else "📂"
        col_btn.append(InlineKeyboardButton(f"{tick} {c.title()}", callback_data=f"coll_{req}_{key}_{c}"))
    btn.append(col_btn)
    
    btn.append([InlineKeyboardButton("❌ Close", callback_data="close_data")])

    try:
        await query.message.edit_text(cap, reply_markup=InlineKeyboardMarkup(btn), disable_web_page_preview=True)
    except:
        pass
    await query.answer()

# ─────────────────────────────────────────────
# 🗂️ COLLECTION SWITCH
# ─────────────────────────────────────────────
@Client.on_callback_query(filters.regex(r"^coll_"))
async def coll_handler(client, query):
    try:
        _, req, key, coll_type = query.data.split("_", 3)
        if int(req) != query.from_user.id:
            return await query.answer("❌ Not for you!", show_alert=True)
    except:
        return

    if IS_PREMIUM and not await is_premium(query.from_user.id, client):
        return await query.answer("❌ Premium Expired!", show_alert=True)

    search = BUTTONS.get(key)
    if not search:
        return await query.answer("❌ Search Expired!", show_alert=True)

    files, next_off, total, act_src = await get_search_results(
        search, max_results=MAX_BTN, offset=0, collection_type=coll_type
    )
    if not files:
        return await query.answer(f"❌ No files in {coll_type.upper()}", show_alert=True)

    temp.FILES[key] = files

    list_items = []
    for file in files:
        f_link = f"https://t.me/{temp.U_NAME}?start=file_{query.message.chat.id}_{file['_id']}"
        list_items.append(f"📁 <a href='{f_link}'>[{get_size(file['file_size'])}] {file['file_name']}</a>")
    
    files_text = "\n\n".join(list_items)
    total_pages = math.ceil(total / MAX_BTN)
    
    cap = (
        f"<b>👑 Search: {search}\n"
        f"🎬 Total: {total}\n"
        f"📚 Source: {act_src.upper()}\n"
        f"📄 Page: 1/{total_pages}</b>\n\n"
        f"{files_text}"
    )

    btn = []
    nav = [InlineKeyboardButton(f"📄 1/{total_pages}", callback_data="pages")]
    if next_off:
        nav.append(InlineKeyboardButton("Next »", callback_data=f"nav_{req}_{key}_{next_off}_{act_src}"))
    btn.append(nav)

    col_btn = []
    for c in ["primary", "cloud", "archive"]:
        tick = "✅" if c == act_src else "📂"
        col_btn.append(InlineKeyboardButton(f"{tick} {c.title()}", callback_data=f"coll_{req}_{key}_{c}"))
    btn.append(col_btn)
    btn.append([InlineKeyboardButton("❌ Close", callback_data="close_data")])

    try:
        await query.message.edit_text(cap, reply_markup=InlineKeyboardMarkup(btn), disable_web_page_preview=True)
    except:
        pass
    await query.answer()

@Client.on_callback_query(filters.regex("^close_data$"))
async def close_cb(c, q):
    try:
        # Cache clean up for this specific key to save RAM
        # But we need key first, usually encoded in other buttons. 
        # For simplicity, just delete.
        await q.message.delete()
    except:
        pass

@Client.on_callback_query(filters.regex("^pages$"))
async def pages_cb(c, q):
    await q.answer()
