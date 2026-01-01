import time
import asyncio
from hydrogram import Client, filters, enums
from database.users_chats_db import db

# =========================
# 🚀 SMART CACHE SYSTEM
# =========================
NOTES_CACHE = {}
CACHE_TTL = 300  # 5 मिनट तक RAM में रहेगा

async def get_notes_data(chat_id):
    current_time = time.time()
    if chat_id in NOTES_CACHE:
        data, timestamp = NOTES_CACHE[chat_id]
        if current_time - timestamp < CACHE_TTL:
            return data

    # DB से नोट्स लाओ (Assuming db structure supports this)
    # अगर आपके DB में notes का function नहीं है, तो नीचे मैं add करने का तरीका बता दूंगा
    data = await db.get_all_notes(chat_id) or {}
    NOTES_CACHE[chat_id] = (data, current_time)
    return data

async def save_note_local(chat_id, name, note_data):
    # Cache और DB दोनों अपडेट करो
    data = await get_notes_data(chat_id)
    data[name] = note_data
    NOTES_CACHE[chat_id] = (data, time.time())
    await db.save_note(chat_id, name, note_data)

async def delete_note_local(chat_id, name):
    data = await get_notes_data(chat_id)
    if name in data:
        del data[name]
        NOTES_CACHE[chat_id] = (data, time.time())
        await db.delete_note(chat_id, name)
        return True
    return False

async def is_admin(c, chat_id, user_id):
    try:
        m = await c.get_chat_member(chat_id, user_id)
        return m.status in (enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER)
    except:
        return False

# =========================
# 📝 SAVE & DELETE COMMANDS
# =========================

@Client.on_message(filters.group & filters.command(["save", "addnote"]))
async def save_note_handler(c, m):
    if not await is_admin(c, m.chat.id, m.from_user.id): return
    
    # नाम निकालो
    if len(m.command) < 2:
        return await m.reply("❗ Use: `/save <name>` (Reply to message)")
    
    name = m.command[1].lower()
    
    # रिप्लाई चेक करो (Text or Media)
    if not m.reply_to_message:
        return await m.reply("❗ Please reply to a text or media to save it.")
    
    reply = m.reply_to_message
    note_type = "text"
    file_id = None
    caption = reply.caption or ""
    text = reply.text or ""

    # मीडिया डिटेक्ट करो
    if reply.photo:
        note_type = "photo"
        file_id = reply.photo.file_id
    elif reply.video:
        note_type = "video"
        file_id = reply.video.file_id
    elif reply.document:
        note_type = "document"
        file_id = reply.document.file_id
    elif reply.sticker:
        note_type = "sticker"
        file_id = reply.sticker.file_id
    elif reply.animation:
        note_type = "animation"
        file_id = reply.animation.file_id
    
    note_data = {
        "type": note_type,
        "file_id": file_id,
        "caption": caption,
        "text": text
    }

    await save_note_local(m.chat.id, name, note_data)
    await m.reply(f"✅ Note **#{name}** saved!")

@Client.on_message(filters.group & filters.command(["clear", "rmnote"]))
async def delete_note_handler(c, m):
    if not await is_admin(c, m.chat.id, m.from_user.id): return
    
    if len(m.command) < 2:
        return await m.reply("❗ Use: `/clear <name>`")
    
    name = m.command[1].lower()
    if await delete_note_local(m.chat.id, name):
        await m.reply(f"🗑️ Note **#{name}** deleted.")
    else:
        await m.reply(f"❌ Note **#{name}** not found.")

@Client.on_message(filters.group & filters.command("notes"))
async def list_notes(c, m):
    data = await get_notes_data(m.chat.id)
    if not data:
        return await m.reply("📭 No notes saved.")
    
    note_list = "\n".join(f"• `#{name}`" for name in data.keys())
    await m.reply(f"📝 **Saved Notes:**\n{note_list}")

# =========================
# 🔎 NOTE FETCHER (Smart Filter)
# =========================

@Client.on_message(filters.group & filters.regex(r"^#[\w]+"), group=11)
async def get_note_handler(c, m):
    # यह सिर्फ तब चलेगा जब मैसेज # से शुरू होगा (No Lag)
    name = m.text.split()[0][1:].lower() # #remove karke name nikalo
    
    data = await get_notes_data(m.chat.id)
    if name not in data: return

    note = data[name]
    type = note.get("type")
    
    # मीडिया भेजो
    if type == "text":
        await m.reply(note["text"])
    elif type == "photo":
        await m.reply_photo(note["file_id"], caption=note["caption"])
    elif type == "video":
        await m.reply_video(note["file_id"], caption=note["caption"])
    elif type == "document":
        await m.reply_document(note["file_id"], caption=note["caption"])
    elif type == "sticker":
        await m.reply_sticker(note["file_id"])
    elif type == "animation":
        await m.reply_animation(note["file_id"], caption=note["caption"])
