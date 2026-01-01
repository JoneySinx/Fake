from hydrogram import Client, filters, enums
from database.users_chats_db import db

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

async def get_data(chat_id):
    data = await db.get_settings(chat_id) or {}
    data.setdefault("auto_reply", {})
    data["auto_reply"].setdefault("__phrases__", {})
    return data

async def save_data(chat_id, data):
    await db.update_settings(chat_id, data)

# =========================
# /save <key>
# =========================

@Client.on_message(filters.group & filters.command("save"))
async def save_reply(client, message):
    if not await is_admin(client, message.chat.id, message.from_user.id):
        return

    if len(message.command) < 2:
        return await message.reply("❌ /save <key> (reply or text)")

    key = message.command[1].lower()
    item = {}

    if message.reply_to_message:
        r = message.reply_to_message
        if r.text:
            item = {"type": "text", "content": r.text}
        elif r.photo:
            item = {"type": "photo", "file_id": r.photo.file_id, "caption": r.caption}
        elif r.video:
            item = {"type": "video", "file_id": r.video.file_id, "caption": r.caption}
        elif r.document:
            item = {"type": "document", "file_id": r.document.file_id, "caption": r.caption}
        elif r.audio:
            item = {"type": "audio", "file_id": r.audio.file_id, "caption": r.caption}
        elif r.sticker:
            item = {"type": "sticker", "file_id": r.sticker.file_id}
        else:
            return await message.reply("❌ Unsupported media")

    elif len(message.command) > 2:
        item = {"type": "text", "content": message.text.split(None, 2)[2]}
    else:
        return await message.reply("❌ Reply to text/media or add text")

    data = await get_data(message.chat.id)
    data["auto_reply"][key] = item
    await save_data(message.chat.id, data)

    await message.reply(f"✅ Saved `{key}`")

# =========================
# /filter "phrase"
# =========================

@Client.on_message(filters.group & filters.command("filter"))
async def add_phrase_filter(client, message):
    if not await is_admin(client, message.chat.id, message.from_user.id):
        return

    text = message.text
    if '"' not in text:
        return await message.reply('❌ /filter "test drive" reply/text')

    try:
        phrase = text.split('"')[1].lower()
    except IndexError:
        return await message.reply("❌ Invalid quotes")

    item = {}

    if message.reply_to_message:
        r = message.reply_to_message
        if r.text:
            item = {"type": "text", "content": r.text}
        elif r.photo:
            item = {"type": "photo", "file_id": r.photo.file_id, "caption": r.caption}
        elif r.video:
            item = {"type": "video", "file_id": r.video.file_id, "caption": r.caption}
        elif r.document:
            item = {"type": "document", "file_id": r.document.file_id, "caption": r.caption}
        elif r.audio:
            item = {"type": "audio", "file_id": r.audio.file_id, "caption": r.caption}
        elif r.sticker:
            item = {"type": "sticker", "file_id": r.sticker.file_id}
        else:
            return await message.reply("❌ Unsupported media")
    else:
        parts = text.split('"', 2)
        if len(parts) < 3 or not parts[2].strip():
            return await message.reply("❌ Reply or add content")
        item = {"type": "text", "content": parts[2].strip()}

    data = await get_data(message.chat.id)
    data["auto_reply"]["__phrases__"][phrase] = item
    await save_data(message.chat.id, data)

    await message.reply(f"✅ Phrase filter saved: `{phrase}`")

# =========================
# /clear <key|phrase>
# =========================

@Client.on_message(filters.group & filters.command("clear"))
async def clear_reply(client, message):
    if not await is_admin(client, message.chat.id, message.from_user.id):
        return

    if len(message.command) < 2:
        return await message.reply("❌ /clear <key|phrase>")

    key = message.command[1].lower()
    data = await get_data(message.chat.id)

    if key in data["auto_reply"]:
        data["auto_reply"].pop(key)
    elif key in data["auto_reply"]["__phrases__"]:
        data["auto_reply"]["__phrases__"].pop(key)
    else:
        return await message.reply("📭 Not found")

    await save_data(message.chat.id, data)
    await message.reply(f"🗑️ Deleted `{key}`")

# =========================
# /notes
# =========================

@Client.on_message(filters.group & filters.command("notes"))
async def list_notes(client, message):
    if not await is_admin(client, message.chat.id, message.from_user.id):
        return

    data = await get_data(message.chat.id)
    keys = [k for k in data["auto_reply"] if k != "__phrases__"]

    if not keys:
        return await message.reply("📭 No notes / word filters")

    await message.reply(
        "📒 **Notes / Word Filters**\n\n" +
        "\n".join(f"• `{k}`" for k in keys)
    )

# =========================
# /filters
# =========================

@Client.on_message(filters.group & filters.command("filters"))
async def list_filters(client, message):
    if not await is_admin(client, message.chat.id, message.from_user.id):
        return

    data = await get_data(message.chat.id)
    phrases = data["auto_reply"]["__phrases__"]

    if not phrases:
        return await message.reply("📭 No phrase filters")

    await message.reply(
        "🔎 **Phrase Filters**\n\n" +
        "\n".join(f"• `{k}`" for k in phrases.keys())
    )

# =========================
# /help
# =========================

@Client.on_message(filters.group & filters.command("ihelp"))
async def help_cmd(client, message):
    if not await is_admin(client, message.chat.id, message.from_user.id):
        return

    await message.reply(
        "🛠️ **Auto Reply Help**\n"
        "━━━━━━━━━━━━━━\n\n"
        "🔐 **Admin Commands**\n"
        "• `/save <key>` → save note / word filter\n"
        "• `/filter \"phrase\"` → phrase filter\n"
        "• `/clear <key|phrase>` → delete\n"
        "• `/notes` → list notes\n"
        "• `/filters` → list phrase filters\n\n"
        "🌍 **Public Triggers**\n"
        "• `#key` → note\n"
        "• `key` → exact word\n"
        "• sentence contains phrase → phrase reply\n\n"
        "⚡ Fast • Media supported • Koyeb safe"
    )

# =========================
# AUTO REPLY HANDLER
# =========================

@Client.on_message(filters.group & filters.text)
async def auto_reply_handler(client, message):
    text = message.text.strip().lower()
    chat_id = message.chat.id

    data = await db.get_settings(chat_id)
    if not data or "auto_reply" not in data:
        return

    replies = data["auto_reply"]

    # 🔹 Hashtag / exact
    key = text[1:].split()[0] if text.startswith("#") else text
    item = replies.get(key)

    # 🔹 Phrase match
    if not item:
        for phrase, p_item in replies.get("__phrases__", {}).items():
            if phrase in text:
                item = p_item
                break

    if not item:
        return

    t = item["type"]
    if t == "text":
        await message.reply(item["content"])
    elif t == "photo":
        await message.reply_photo(item["file_id"], caption=item.get("caption"))
    elif t == "video":
        await message.reply_video(item["file_id"], caption=item.get("caption"))
    elif t == "document":
        await message.reply_document(item["file_id"], caption=item.get("caption"))
    elif t == "audio":
        await message.reply_audio(item["file_id"], caption=item.get("caption"))
    elif t == "sticker":
        await message.reply_sticker(item["file_id"])
