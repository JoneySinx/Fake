import asyncio
from google import genai
from hydrogram import Client, filters, enums
from info import GEMINI_API_KEY

# ==========================================
# 🧠 AI CONFIGURATION (New Google GenAI SDK)
# ==========================================

if GEMINI_API_KEY:
    # Initialize the new Client
    ai_client = genai.Client(api_key=GEMINI_API_KEY)
else:
    ai_client = None

# ==========================================
# 🗣️ AI CHAT COMMAND
# ==========================================

@Client.on_message(filters.command(["ask", "ai"]))
async def ask_ai(client, message):
    # 1. Check API Key
    if not ai_client:
        return await message.reply("❌ **AI Error:** API Key missing in Config.")

    # 2. Check Input
    if len(message.command) < 2 and not message.reply_to_message:
        return await message.reply(
            "🤖 **Gemini AI (Updated)**\n\n"
            "Usage:\n"
            "• `/ask Who is Iron Man?`\n"
            "• Reply to a text with `/ask`"
        )

    # 3. Get Question
    if len(message.command) > 1:
        question = message.text.split(None, 1)[1]
    elif message.reply_to_message and message.reply_to_message.text:
        question = message.reply_to_message.text
    else:
        return await message.reply("❌ कृपया कुछ लिखें या टेक्स्ट को रिप्लाई करें।")

    # 4. Process (Show Typing)
    status = await message.reply("🧠 Thinking...")
    await client.send_chat_action(message.chat.id, enums.ChatAction.TYPING)

    try:
        # 5. Call Google API (Non-Blocking)
        # Using the new 'gemini-1.5-flash' model which is faster and free
        loop = asyncio.get_event_loop()
        
        response = await loop.run_in_executor(
            None, 
            lambda: ai_client.models.generate_content(
                model='gemini-1.5-flash', 
                contents=question
            )
        )
        
        if not response.text:
            return await status.edit("❌ **Error:** AI sent an empty response.")

        answer = response.text

        # 6. Send Response (Split if too long)
        if len(answer) > 4000:
            for i in range(0, len(answer), 4000):
                await message.reply(answer[i:i+4000], parse_mode=enums.ParseMode.MARKDOWN)
            await status.delete()
        else:
            await status.edit(answer, parse_mode=enums.ParseMode.MARKDOWN)

    except Exception as e:
        await status.edit(f"❌ **Error:** `{str(e)}`")

