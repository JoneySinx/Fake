import asyncio
from google import genai
from hydrogram import Client, filters, enums
from info import GEMINI_API_KEY

# ==========================================
# 🧠 AI CONFIGURATION (AUTO-FALLBACK SYSTEM)
# ==========================================

if GEMINI_API_KEY:
    ai_client = genai.Client(api_key=GEMINI_API_KEY)
else:
    ai_client = None

# List of models to try (Priority wise)
# 1. 1.5 Flash (Fastest & Stable)
# 2. 1.5 Pro (Powerful backup)
# 3. Gemini Pro (Old reliable 1.0)
MODELS_TO_TRY = [
    'gemini-1.5-flash',
    'gemini-1.5-flash-001',
    'gemini-1.5-pro',
    'gemini-pro'
]

# ==========================================
# 🗣️ AI CHAT COMMAND
# ==========================================

@Client.on_message(filters.command(["ask", "ai"]))
async def ask_ai(client, message):
    if not ai_client:
        return await message.reply("❌ **AI Error:** API Key missing.")

    # 1. SMART PROMPT EXTRACTOR
    prompt = ""
    if len(message.command) > 1:
        prompt = message.text.split(None, 1)[1]
    elif message.reply_to_message:
        prompt = message.reply_to_message.text or message.reply_to_message.caption or ""

    if not prompt.strip():
        return await message.reply("🤖 **AI:** कृपया कुछ लिखें या रिप्लाई करें!")

    status = await message.reply("⚡ Thinking...")
    await client.send_chat_action(message.chat.id, enums.ChatAction.TYPING)

    # 2. FALLBACK LOOP (Try models one by one)
    final_answer = None
    last_error = ""

    loop = asyncio.get_event_loop()

    for model_name in MODELS_TO_TRY:
        try:
            response = await loop.run_in_executor(
                None, 
                lambda: ai_client.models.generate_content(
                    model=model_name, 
                    contents=prompt
                )
            )
            
            if response.text:
                final_answer = response.text
                break # Success! Exit loop
        except Exception as e:
            last_error = str(e)
            # If rate limit (429), try next immediately
            # If not found (404), try next immediately
            continue 

    # 3. SEND RESPONSE OR ERROR
    if final_answer:
        try:
            if len(final_answer) > 4000:
                for i in range(0, len(final_answer), 4000):
                    await message.reply(final_answer[i:i+4000], parse_mode=enums.ParseMode.MARKDOWN)
                await status.delete()
            else:
                await status.edit(final_answer, parse_mode=enums.ParseMode.MARKDOWN)
        except Exception as e:
            await status.edit(f"❌ **Formatting Error:** {e}")
    else:
        # If all models failed
        if "429" in last_error:
            await status.edit("❌ **Busy:** AI का कोटा अभी फुल है, कृपया 1 मिनट बाद ट्राई करें।")
        else:
            await status.edit(f"❌ **All Models Failed.**\nLast Error: `{last_error}`")

