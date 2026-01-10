# plugins/draw.py

import asyncio
import aiohttp
import io
from hydrogram import Client, filters, enums
from hydrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from info import HF_TOKEN

# ===============================
# 🎨 AI Image Generator Config
# ===============================

HF_API_BASE = "https://router.huggingface.co/models"
TIMEOUT = aiohttp.ClientTimeout(total=60)

MODELS = [
    "stabilityai/stable-diffusion-xl-base-1.0",
    "prompthero/openjourney",
    "runwayml/stable-diffusion-v1-5",
    "CompVis/stable-diffusion-v1-4"
]

HEADERS = {
    "Authorization": f"Bearer {HF_TOKEN}"
}

# ===============================
# 🔧 Helper Functions
# ===============================

def extract_prompt(message):
    if len(message.command) > 1:
        return message.text.split(None, 1)[1]

    if message.reply_to_message and message.reply_to_message.text:
        return message.reply_to_message.text

    return None


def enhance_prompt(prompt: str) -> str:
    if "quality" not in prompt.lower():
        return f"{prompt}, cinematic lighting, 8k, ultra detailed, realistic, masterpiece"
    return prompt


async def generate_image(prompt: str):
    async with aiohttp.ClientSession(headers=HEADERS, timeout=TIMEOUT) as session:
        for model in MODELS:
            url = f"{HF_API_BASE}/{model}"
            try:
                async with session.post(url, json={"inputs": prompt}) as resp:
                    if resp.status == 200:
                        return await resp.read(), model

                    if resp.status == 503:
                        await asyncio.sleep(3)

            except Exception as e:
                print(f"[HF ERROR] {model}: {e}")

    return None, None


# ===============================
# 🎨 Command Handler
# ===============================

@Client.on_message(filters.command(["draw", "imagine", "img"]))
async def draw_image(client, message):

    if not HF_TOKEN:
        return await message.reply("❌ **HF_TOKEN missing**")

    prompt = extract_prompt(message)
    if not prompt:
        return await message.reply(
            "🎨 **AI Image Generator**\n\n"
            "`/draw <prompt>`\n"
            "Example: `/draw a dragon flying over city, 4k`"
        )

    if message.reply_to_message and message.reply_to_message.photo:
        await message.reply(
            "⚠️ मैं पुरानी फोटो edit नहीं कर सकता,\n"
            "आपके prompt से नई image बना रहा हूँ।",
            quote=True
        )

    prompt = enhance_prompt(prompt)

    status = await message.reply(f"🎨 **Generating...**\n`{prompt}`")
    await client.send_chat_action(message.chat.id, enums.ChatAction.UPLOAD_PHOTO)

    image_bytes, model_used = await generate_image(prompt)

    if not image_bytes:
        return await status.edit("❌ Server busy या models unavailable")

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
