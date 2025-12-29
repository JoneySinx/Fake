from pymongo import MongoClient

from info import (
    BOT_ID,
    DATABASE_URL,
    DATABASE_NAME,
    FILE_CAPTION,
    WELCOME,
    WELCOME_TEXT,
    SPELL_CHECK,
    PROTECT_CONTENT,
    AUTO_DELETE
)

# ─────────────────────────────────────────────
# 🔌 SINGLE DATABASE CONNECTION (FINAL)
# ─────────────────────────────────────────────
client = MongoClient(
    DATABASE_URL,
    maxPoolSize=50,
    minPoolSize=10,
    maxIdleTimeMS=45000
)
_db = client[DATABASE_NAME]


# ─────────────────────────────────────────────
# 🧠 DATABASE CLASS
# ─────────────────────────────────────────────
class Database:

    # Minimal & required group settings only
    default_setgs = {
        "file_secure": PROTECT_CONTENT,
        "spell_check": SPELL_CHECK,
        "auto_delete": AUTO_DELETE,
        "welcome": WELCOME,
        "welcome_text": WELCOME_TEXT,
        "caption": FILE_CAPTION
    }

    default_prm = {
        "expire": "",
        "trial": False,
        "plan": "",
        "premium": False
    }

    def __init__(self):
        self.users = _db.Users
        self.groups = _db.Groups
        self.premium = _db.Premiums
        self.connections = _db.Connections
        self.settings = _db.Settings

    # ───────── USERS ─────────
    def new_user(self, user_id, name):
        return {
            "id": int(user_id),
            "name": name,
            "ban_status": {
                "is_banned": False,
                "ban_reason": ""
            }
        }

    async def add_user(self, user_id, name):
        self.users.insert_one(self.new_user(user_id, name))

    async def is_user_exist(self, user_id):
        return bool(self.users.find_one({"id": int(user_id)}))

    async def total_users_count(self):
        return self.users.count_documents({})

    async def delete_user(self, user_id):
        self.users.delete_many({"id": int(user_id)})

    async def ban_user(self, user_id, reason="No Reason"):
        self.users.update_one(
            {"id": int(user_id)},
            {"$set": {"ban_status": {"is_banned": True, "ban_reason": reason}}}
        )

    async def unban_user(self, user_id):
        self.users.update_one(
            {"id": int(user_id)},
            {"$set": {"ban_status": {"is_banned": False, "ban_reason": ""}}}
        )

    async def get_ban_status(self, user_id):
        user = self.users.find_one({"id": int(user_id)})
        return user.get("ban_status") if user else {
            "is_banned": False,
            "ban_reason": ""
        }

    # ───────── GROUPS ─────────
    def new_group(self, group_id, title):
        return {
            "id": int(group_id),
            "title": title,
            "chat_status": {
                "is_disabled": False,
                "reason": ""
            },
            "settings": self.default_setgs
        }

    async def add_chat(self, group_id, title):
        self.groups.insert_one(self.new_group(group_id, title))

    async def delete_chat(self, group_id):
        self.groups.delete_many({"id": int(group_id)})

    async def get_chat(self, group_id):
        grp = self.groups.find_one({"id": int(group_id)})
        return grp.get("chat_status") if grp else False

    async def disable_chat(self, group_id, reason="No Reason"):
        self.groups.update_one(
            {"id": int(group_id)},
            {"$set": {"chat_status": {"is_disabled": True, "reason": reason}}}
        )

    async def re_enable_chat(self, group_id):
        self.groups.update_one(
            {"id": int(group_id)},
            {"$set": {"chat_status": {"is_disabled": False, "reason": ""}}}
        )

    async def total_chat_count(self):
        return self.groups.count_documents({})

    async def get_all_chats(self):
        return self.groups.find({})

    # ───────── GROUP SETTINGS ─────────
    async def update_settings(self, group_id, settings):
        self.groups.update_one(
            {"id": int(group_id)},
            {"$set": {"settings": settings}}
        )

    async def get_settings(self, group_id):
        grp = self.groups.find_one({"id": int(group_id)})
        return grp.get("settings", self.default_setgs) if grp else self.default_setgs

    # ───────── PREMIUM ─────────
    def get_plan(self, user_id):
        st = self.premium.find_one({"id": int(user_id)})
        return st["status"] if st else self.default_prm

    def update_plan(self, user_id, data):
        if not self.premium.find_one({"id": int(user_id)}):
            self.premium.insert_one({"id": int(user_id), "status": data})
        else:
            self.premium.update_one(
                {"id": int(user_id)},
                {"$set": {"status": data}}
            )

    def get_premium_count(self):
        return self.premium.count_documents({"status.premium": True})

    def get_premium_users(self):
        return self.premium.find({})

    # ───────── CONNECTIONS ─────────
    def add_connect(self, group_id, user_id):
        user = self.connections.find_one({"_id": int(user_id)})
        if user:
            if group_id not in user["group_ids"]:
                self.connections.update_one(
                    {"_id": int(user_id)},
                    {"$push": {"group_ids": group_id}}
                )
        else:
            self.connections.insert_one(
                {"_id": int(user_id), "group_ids": [group_id]}
            )

    def get_connections(self, user_id):
        user = self.connections.find_one({"_id": int(user_id)})
        return user["group_ids"] if user else []

    # ───────── BOT SETTINGS ─────────
    def update_bot_sttgs(self, var, val):
        if not self.settings.find_one({"id": BOT_ID}):
            self.settings.insert_one({"id": BOT_ID, var: val})
        else:
            self.settings.update_one(
                {"id": BOT_ID},
                {"$set": {var: val}}
            )

    def get_bot_sttgs(self):
        return self.settings.find_one({"id": BOT_ID}) or {}

    # ───────── STARTUP SUPPORT ─────────
    async def get_banned(self):
        """
        Used at bot startup
        """
        banned_users = []
        banned_chats = []

        try:
            for u in self.users.find({"ban_status.is_banned": True}):
                banned_users.append(u["id"])
        except Exception:
            pass

        try:
            for g in self.groups.find({"chat_status.is_disabled": True}):
                banned_chats.append(g["id"])
        except Exception:
            pass

        return banned_users, banned_chats


# ─────────────────────────────────────────────
# 🔚 INSTANCE
# ─────────────────────────────────────────────
db = Database()
