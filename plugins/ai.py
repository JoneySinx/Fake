import asyncio
from google import genai
from hydrogram import Client, filters, enums
from info import GEMINI_API_KEY

# ==========================================
# 🧠 AI CONFIGURATION (Latest Flash ⚡)
# ==========================================

if GEMINI_API_KEY:
    # Using the latest experimental flash model which is the backend for "Gemini 3 Flash" preview
    ai_client = genai.Client(api_key=GEMINI_API_KEY)
else:
    ai_client = None

# ==========================================
# 🗣️ AI CHAT COMMAND
# ==========================================

@Client.on_message(filters.command(["ask", "ai"]))
async def ask_ai(client, message):
    if not ai_client:
        return await message.reply("❌ **AI Error:** API Key missing.")

    # 1. EXTRACT PROMPT (SMART)
    prompt = ""
    
    # Case A: Argument directly (/ask Hello)
    if len(message.command) > 1:
        prompt = message.text.split(None, 1)[1]
    
    # Case B: Reply to Message (Text OR Caption)
    elif message.reply_to_message:
        if message.reply_to_message.text:
            prompt = message.reply_to_message.text
        elif message.reply_to_message.caption:
            prompt = message.reply_to_message.caption

    # 2. VALIDATE PROMPT
    if not prompt or not prompt.strip():
        return await message.reply(
            "⚡ **Gemini Flash AI**\n\n"
            "**Error:** No text found!\n\n"
            "Usage:\n"
            "• `/ask Who is Batman?`\n"
            "• Reply to any text/caption with `/ask`"
        )

    # 3. PROCESSING
    status = await message.reply("⚡ Thinking...")
    await client.send_chat_action(message.chat.id, enums.ChatAction.TYPING)

    try:
        loop = asyncio.get_event_loop()
        
        # 🔥 Using 'gemini-2.0-flash-exp'
        # Note: API IDs often differ from Marketing names (3 Flash is currently 2.0-exp in API)
        response = await loop.run_in_executor(
            None, 
            lambda: ai_client.models.generate_content(
                model='gemini-2.0-flash-exp', 
                contents=prompt
            )
        )
        
        if not response.text:
            return await status.edit("❌ **Error:** Empty Response from AI.")

        answer = response.text

        # 4. SEND (Split Long Messages)
        if len(answer) > 4000:
            for i in range(0, len(answer), 4000):
                await message.reply(answer[i:i+4000], parse_mode=enums.ParseMode.MARKDOWN)
            await status.delete()
        else:
            await status.edit(answer, parse_mode=enums.ParseMode.MARKDOWN)

    except Exception as e:
        error_msg = str(e)
        if "404" in error_msg:
            await status.edit("❌ **Model Error:** Gemini 2.0/3.0 API is not active for your key yet.\nTry switching to `gemini-1.5-flash` in code.")
        else:
            await status.edit(f"❌ **Error:** `{error_msg}`")

