import asyncio
import aiohttp
import io
from hydrogram import Client, filters, enums
from hydrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from info import HF_TOKEN

# ==================================================
# 🎨 AI IMAGE GENERATOR – FINAL STABLE VERSION
# ==================================================

HF_API_BASE = "https://api-inference.huggingface.co/models"
TIMEOUT = aiohttp.ClientTimeout(total=90)

MODELS = [
    "stabilityai/stable-diffusion-2-1",
    "runwayml/stable-diffusion-v1-5",
    "CompVis/stable-diffusion-v1-4"
]

HEADERS = {
    "Authorization": f"Bearer {HF_TOKEN}"
}

# ==================================================
# 🧠 Helper Functions
# ==================================================

def extract_prompt(message):
    if len(message.command) > 1:
        return message.text.split(None, 1)[1]

    if message.reply_to_message and message.reply_to_message.text:
        return message.reply_to_message.text

    return None


def enhance_prompt(prompt: str) -> str:
    if "quality" not in prompt.lower():
        return f"{prompt}, cinematic lighting, ultra detailed, realistic, masterpiece"
    return prompt


async def generate_image(prompt: str):
    async with aiohttp.ClientSession(headers=HEADERS, timeout=TIMEOUT) as session:
        for model in MODELS:
            url = f"{HF_API_BASE}/{model}"

            try:
                async with session.post(url, json={"inputs": prompt}) as resp:
                    content_type = resp.headers.get("content-type", "")

                    # ✅ Image response
                    if resp.status == 200 and "image" in content_type:
                        return await resp.read(), model

                    # ⏳ Model loading
                    if resp.status == 503:
                        await asyncio.sleep(6)
                        continue

                    # ❌ JSON error
                    try:
                        error = await resp.json()
                        print(f"[HF ERROR] {model}: {error}")
                    except:
                        pass

            except Exception as e:
                print(f"[HF EXCEPTION] {model}: {e}")

    return None, None


# ==================================================
# 🎨 Command Handler
# ==================================================

@Client.on_message(filters.command(["draw", "imagine", "img"]))
async def draw_image(client, message):

    if not HF_TOKEN:
        return await message.reply("❌ HuggingFace token missing")

    prompt = extract_prompt(message)
    if not prompt:
        return await message.reply(
            "🎨 **AI Image Generator**\n\n"
            "`/draw <prompt>`\n"
            "Example: `/draw flying dog in sky, 4k`"
        )

    # Warn if replied to photo
    if message.reply_to_message and message.reply_to_message.photo:
        await message.reply(
            "⚠️ Photo edit supported नहीं है.\n"
            "आपके prompt से नई image बना रहा हूँ।",
            quote=True
        )

    prompt = enhance_prompt(prompt)

    status = await message.reply(f"🎨 **Generating...**\n`{prompt}`")
    await client.send_chat_action(message.chat.id, enums.ChatAction.UPLOAD_PHOTO)

    image_bytes, model_used = await generate_image(prompt)

    if not image_bytes:
        return await status.edit("❌ Server busy या सभी models unavailable")

    image = io.BytesIO(image_bytes)
    image.name = "ai_art.jpg"

    await client.send_photo(
        chat_id=message.chat.id,
        photo=image,
        caption=(
            f"✨ **Prompt:** `{prompt}`\n"
            f"🎨 **Model:** `{model_used}`\n"
            f"🤖 @{client.me.username}"
        ),
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("🗑 Delete", callback_data="close_data")]]
        )
    )

    await status.delete()
