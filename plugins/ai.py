import asyncio
from google import genai
from hydrogram import Client, filters, enums
from info import GEMINI_API_KEY

# ==========================================
# 🧠 AI CONFIGURATION (Stable Version)
# ==========================================

if GEMINI_API_KEY:
    # Google GenAI Client
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

    # 1. SMART PROMPT EXTRACTOR
    prompt = ""
    
    # Method A: Command ke saath (/ask Hello)
    if len(message.command) > 1:
        prompt = message.text.split(None, 1)[1]
    
    # Method B: Reply ke saath (Text ya Caption)
    elif message.reply_to_message:
        prompt = message.reply_to_message.text or message.reply_to_message.caption or ""

    # 2. VALIDATION
    if not prompt.strip():
        return await message.reply(
            "🤖 **Gemini AI**\n\n"
            "**Error:** अरे कहना क्या चाहते हो? (Empty Message)\n\n"
            "**Usage:**\n"
            "• `/ask India ka capital kya hai?`\n"
            "• Kisi msg ko reply karke `/ask` likho."
        )

    # 3. PROCESSING
    status = await message.reply("🧠 Thinking...")
    await client.send_chat_action(message.chat.id, enums.ChatAction.TYPING)

    try:
        loop = asyncio.get_event_loop()
        
        # 🔥 FIX: Using Specific Version Name 'gemini-1.5-flash-001'
        # This solves the 404 Not Found error
        response = await loop.run_in_executor(
            None, 
            lambda: ai_client.models.generate_content(
                model='gemini-1.5-flash-001', 
                contents=prompt
            )
        )
        
        if not response.text:
            return await status.edit("❌ **Error:** Empty Response from AI.")

        answer = response.text

        # 4. SENDING (Split if long)
        if len(answer) > 4000:
            for i in range(0, len(answer), 4000):
                await message.reply(answer[i:i+4000], parse_mode=enums.ParseMode.MARKDOWN)
            await status.delete()
        else:
            await status.edit(answer, parse_mode=enums.ParseMode.MARKDOWN)

    except Exception as e:
        # Fallback Error Handling
        err_msg = str(e)
        if "404" in err_msg:
            await status.edit("❌ **Error:** Model not found. Try updating 'gemini-1.5-flash-001' to 'gemini-pro' in code.")
        elif "429" in err_msg:
            await status.edit("❌ **Quota Exceeded:** API Limit full. Wait for some time.")
        else:
            await status.edit(f"❌ **Error:** `{err_msg}`")

