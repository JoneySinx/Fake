import logging
import asyncio
import os
import time
from typing import Union, Optional, AsyncGenerator
from datetime import datetime
import pytz

# ==========================================================
# 🔥 UVLOOP (High Performance Event Loop)
# ==========================================================
try:
    import uvloop
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
except ImportError:
    pass

# ==========================================================
# LOGGING SETUP
# ==========================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logging.getLogger('hydrogram').setLevel(logging.ERROR)
# ✅ Suppress noisy logs from aiohttp & uptime probes
logging.getLogger('aiohttp.access').setLevel(logging.WARNING)
logging.getLogger('aiohttp.server').setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# ==========================================================
# IMPORTS
# ==========================================================
from aiohttp import web
from hydrogram import Client, types
from web import web_app
from info import (
    API_ID, API_HASH, BOT_TOKEN, PORT, ADMINS, 
    LOG_CHANNEL, DATABASE_URL, DATABASE_NAME
)
from utils import temp
from database.users_chats_db import db

# ⚡ IMPORTANT: Import Database Indexer
from Database.ia_filterdb import ensure_indexes

# -------------------- IMPORT PREMIUM MODULE --------------------
from plugins.premium import check_premium_expired

# ==========================================================
# BOT CLASS
# ==========================================================
class Bot(Client):
    def __init__(self):
        super().__init__(
            name="Auto_Filter_Bot",
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=BOT_TOKEN,
            plugins={"root": "plugins"}
        )

    async def start(self):
        # 1. Start Client
        await super().start()
        temp.START_TIME = time.time()

        # 2. Initialize Database Indexes (Background Task)
        # यह सर्च को सुपर फास्ट बनाने के लिए जरूरी है
        await ensure_indexes()
        logger.info("✅ Database Indexes Checked/Created")

        # 3. Load banned users & chats (Async)
        try:
            b_users, b_chats = await db.get_banned()
            temp.BANNED_USERS = b_users
            temp.BANNED_CHATS = b_chats
        except Exception as e:
            logger.error(f"Error loading banned list: {e}")

        # 4. Restart Handler (If restart was triggered)
        if os.path.exists("restart.txt"):
            try:
                with open("restart.txt") as f:
                    chat_id, msg_id = map(int, f.read().split())
                await self.edit_message_text(
                    chat_id=chat_id,
                    message_id=msg_id,
                    text="✅ Restarted Successfully!"
                )
            except Exception as e:
                logger.error(f"Restart message error: {e}")
            finally:
                os.remove("restart.txt")

        # 5. Set Bot Identity
        temp.BOT = self
        me = await self.get_me()
        temp.ME = me.id
        temp.U_NAME = me.username
        temp.B_NAME = me.first_name

        # 6. Start Web Server
        runner = web.AppRunner(web_app, access_log=None)
        await runner.setup()
        await web.TCPSite(runner, "0.0.0.0", PORT).start()
        logger.info(f"✅ Web Server Started on Port {PORT}")

        # 7. Start Premium Checker Task
        asyncio.create_task(check_premium_expired(self))

        # 8. Send Startup Logs
        ist = pytz.timezone("Asia/Kolkata")
        now = datetime.now(ist)
        date_str = now.strftime("%d %B %Y")
        time_str = now.strftime("%I:%M:%S %p")

        startup_msg = (
            f"🤖 <b>Bot Started Successfully!</b>\n\n"
            f"📅 <b>Date:</b> {date_str}\n"
            f"🕐 <b>Time:</b> {time_str}\n"
            f"🌏 <b>Timezone:</b> IST (Asia/Kolkata)\n"
            f"🚀 <b>Speed:</b> Optimized (Async/Motor)\n"
            f"✅ <b>Status:</b> Online"
        )

        # Admin Notify
        for admin_id in ADMINS:
            try:
                await self.send_message(admin_id, startup_msg)
            except Exception:
                pass # Ignore if admin blocked bot

        # Log Channel Notify
        if LOG_CHANNEL:
            try:
                await self.send_message(
                    LOG_CHANNEL,
                    f"<b>{me.mention} restarted successfully 🤖</b>"
                )
            except Exception as e:
                logger.warning(f"Failed to send log to LOG_CHANNEL: {e}")

        logger.info(f"@{me.username} is Online & Ready!")

    async def stop(self, *args):
        await super().stop()
        logger.info("Bot stopped. Bye 👋")

    # Custom iterator (Keeping your logic)
    async def iter_messages(
        self: Client,
        chat_id: Union[int, str],
        limit: int,
        offset: int = 0
    ) -> Optional[AsyncGenerator["types.Message", None]]:
        current = offset
        while current < limit:
            diff = min(200, limit - current)
            try:
                messages = await self.get_messages(
                    chat_id,
                    list(range(current, current + diff))
                )
                for message in messages:
                    yield message
                current += diff
            except Exception as e:
                logger.error(f"Error fetching messages: {e}")
                return

# ==========================================================
# MAIN EXECUTION
# ==========================================================
async def main():
    bot = Bot()
    await bot.start()
    # Idle wait
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())

