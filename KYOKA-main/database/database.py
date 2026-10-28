import sqlite3
import os
import asyncio
from datetime import datetime


class Database:
    def __init__(self, path="database/kyoka.db"):
        self.path = path
        self._lock = asyncio.Lock()

        directory = os.path.dirname(self.path)

        if directory:
            os.makedirs(directory, exist_ok=True)

        self.conn = sqlite3.connect(
            self.path,
            check_same_thread=False
        )

        self.conn.row_factory = sqlite3.Row

    async def initialize(self):
        async with self._lock:
            self._initialize()

    def _initialize(self):
        cursor = self.conn.cursor()

        cursor.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            balance INTEGER DEFAULT 0,
            bank INTEGER DEFAULT 0,
            xp INTEGER DEFAULT 0,
            level INTEGER DEFAULT 1,
            afk INTEGER DEFAULT 0,
            afk_reason TEXT,
            afk_since TEXT,
            reputation INTEGER DEFAULT 0,
            last_daily TEXT,
            last_work TEXT,
            created_at TEXT
        );

        CREATE TABLE IF NOT EXISTS guilds (
            guild_id INTEGER PRIMARY KEY,
            prefix TEXT DEFAULT 'k!',
            welcome_channel INTEGER,
            goodbye_channel INTEGER,
            log_channel INTEGER,
            auto_role INTEGER,
            welcome_enabled INTEGER DEFAULT 0,
            goodbye_enabled INTEGER DEFAULT 0,
            welcome_message TEXT,
            goodbye_message TEXT,
            custom_currency TEXT DEFAULT 'Coins',
            currency_emoji TEXT DEFAULT '🪙',
            created_at TEXT
        );

        CREATE TABLE IF NOT EXISTS premium (
            guild_id INTEGER PRIMARY KEY,
            enabled INTEGER DEFAULT 0,
            expires_at TEXT,
            plan TEXT,
            activated_by INTEGER,
            activated_at TEXT
        );

        CREATE TABLE IF NOT EXISTS premium_users (
            guild_id INTEGER,
            user_id INTEGER,
            expires_at TEXT,
            granted_by INTEGER,
            created_at TEXT,
            PRIMARY KEY (guild_id, user_id)
        );

        CREATE TABLE IF NOT EXISTS inventory (
            user_id INTEGER,
            item_id TEXT,
            amount INTEGER DEFAULT 0,
            PRIMARY KEY (user_id, item_id)
        );

        CREATE TABLE IF NOT EXISTS warnings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER,
            user_id INTEGER,
            moderator_id INTEGER,
            reason TEXT,
            created_at TEXT
        );

        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            type TEXT,
            amount INTEGER,
            description TEXT,
            created_at TEXT
        );

        CREATE TABLE IF NOT EXISTS custom_commands (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER,
            name TEXT,
            response TEXT,
            creator_id INTEGER,
            created_at TEXT,
            UNIQUE(guild_id, name)
        );

        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER,
            channel_id INTEGER,
            user_id INTEGER,
            category TEXT,
            status TEXT DEFAULT 'open',
            claimed_by INTEGER,
            created_at TEXT,
            closed_at TEXT
        );

        CREATE TABLE IF NOT EXISTS giveaways (
            message_id INTEGER PRIMARY KEY,
            guild_id INTEGER,
            channel_id INTEGER,
            host_id INTEGER,
            prize TEXT,
            winners INTEGER DEFAULT 1,
            end_time TEXT,
            ended INTEGER DEFAULT 0,
            created_at TEXT,
            description TEXT,
            image_url TEXT
        );

        CREATE TABLE IF NOT EXISTS giveaway_entries (
            message_id INTEGER,
            user_id INTEGER,
            PRIMARY KEY (message_id, user_id)
        );

        CREATE TABLE IF NOT EXISTS level_roles (
            guild_id INTEGER,
            level INTEGER,
            role_id INTEGER,
            PRIMARY KEY (guild_id, level)
        );

        CREATE TABLE IF NOT EXISTS suggestions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER,
            user_id INTEGER,
            suggestion TEXT,
            status TEXT DEFAULT 'pending',
            moderator_id INTEGER,
            created_at TEXT
        );

        CREATE TABLE IF NOT EXISTS birthdays (
            guild_id INTEGER,
            user_id INTEGER,
            month INTEGER,
            day INTEGER,
            PRIMARY KEY (guild_id, user_id)
        );

        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            channel_id INTEGER,
            message TEXT,
            remind_at TEXT,
            completed INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS logging_settings (
            guild_id INTEGER PRIMARY KEY,
            log_channel_id INTEGER,
            message_logs INTEGER DEFAULT 1,
            member_logs INTEGER DEFAULT 1,
            moderation_logs INTEGER DEFAULT 1,
            server_logs INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS automod_settings (
            guild_id INTEGER PRIMARY KEY,
            enabled INTEGER DEFAULT 0,
            anti_spam INTEGER DEFAULT 0,
            anti_invite INTEGER DEFAULT 0,
            link_filter INTEGER DEFAULT 0,
            bad_words INTEGER DEFAULT 0,
            mention_spam INTEGER DEFAULT 0,
            anti_raid INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS ai_settings (
            guild_id INTEGER PRIMARY KEY,
            enabled INTEGER DEFAULT 0,
            personality TEXT,
            instructions TEXT,
            channel_id INTEGER
        );

        CREATE TABLE IF NOT EXISTS economy_settings (
            guild_id INTEGER PRIMARY KEY,
            enabled INTEGER DEFAULT 1,
            currency_name TEXT DEFAULT 'Coins',
            currency_emoji TEXT DEFAULT '🪙',
            daily_amount INTEGER DEFAULT 100,
            work_min INTEGER DEFAULT 50,
            work_max INTEGER DEFAULT 250
        );

        CREATE TABLE IF NOT EXISTS game_sessions (
            user_id INTEGER PRIMARY KEY,
            game TEXT,
            data TEXT,
            started_at TEXT
        );

        CREATE TABLE IF NOT EXISTS owner_actions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_id INTEGER,
            action TEXT,
            target_id INTEGER,
            details TEXT,
            created_at TEXT
        );

        CREATE TABLE IF NOT EXISTS analytics (
            guild_id INTEGER,
            event TEXT,
            value INTEGER DEFAULT 1,
            created_at TEXT
        );

        CREATE TABLE IF NOT EXISTS ticket_settings (
            guild_id INTEGER,
            category TEXT,
            staff_role_id INTEGER,
            category_id INTEGER,
            PRIMARY KEY (guild_id, category)
        );

        CREATE TABLE IF NOT EXISTS automation_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER,
            channel_id INTEGER,
            message TEXT,
            run_at TEXT,
            repeat_seconds INTEGER DEFAULT 0,
            enabled INTEGER DEFAULT 1,
            created_by INTEGER
        );

        CREATE TABLE IF NOT EXISTS automation_triggers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER,
            trigger TEXT,
            response TEXT,
            enabled INTEGER DEFAULT 1,
            created_by INTEGER
        );

        CREATE TABLE IF NOT EXISTS giveaway_requirements (
            message_id INTEGER PRIMARY KEY,
            required_role_id INTEGER,
            minimum_level INTEGER DEFAULT 0,
            minimum_account_age INTEGER DEFAULT 0,
            minimum_server_age INTEGER DEFAULT 0,
            required_server_tag TEXT,
            blacklist TEXT,
            max_entries INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS welcome_settings (
            guild_id INTEGER PRIMARY KEY,
            enabled INTEGER DEFAULT 0,
            channel_id INTEGER,
            message TEXT,
            goodbye_enabled INTEGER DEFAULT 0,
            goodbye_channel_id INTEGER,
            goodbye_message TEXT,
            auto_role_id INTEGER,
            background_url TEXT
        );

        CREATE TABLE IF NOT EXISTS leveling_settings (
            guild_id INTEGER PRIMARY KEY,
            enabled INTEGER DEFAULT 1,
            xp_min INTEGER DEFAULT 5,
            xp_max INTEGER DEFAULT 15,
            cooldown INTEGER DEFAULT 60,
            levelup_channel_id INTEGER,
            levelup_message TEXT
        );

        CREATE TABLE IF NOT EXISTS bot_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER,
            event TEXT,
            user_id INTEGER,
            target_id INTEGER,
            details TEXT,
            created_at TEXT
        );
        """)

        self.conn.commit()

    # ==================================================
    # CORE DATABASE METHODS
    # ==================================================

    async def execute(self, query, params=(), commit=True):
        async with self._lock:
            cursor = self.conn.cursor()

            cursor.execute(query, params)

            if commit:
                self.conn.commit()

            return cursor

    async def fetchone(self, query, params=()):
        async with self._lock:
            cursor = self.conn.cursor()

            cursor.execute(query, params)

            return cursor.fetchone()

    async def fetchall(self, query, params=()):
        async with self._lock:
            cursor = self.conn.cursor()

            cursor.execute(query, params)

            return cursor.fetchall()

    # ==================================================
    # USER SYSTEM
    # ==================================================

    async def ensure_user(self, user_id):
        row = await self.fetchone(
            "SELECT user_id FROM users WHERE user_id = ?",
            (user_id,)
        )

        if not row:
            await self.execute(
                """
                INSERT INTO users
                (user_id, created_at)
                VALUES (?, ?)
                """,
                (
                    user_id,
                    datetime.utcnow().isoformat()
                )
            )

    async def get_user(self, user_id):
        await self.ensure_user(user_id)

        return await self.fetchone(
            "SELECT * FROM users WHERE user_id = ?",
            (user_id,)
        )

    # ==================================================
    # BALANCE
    # ==================================================

    async def set_balance(self, user_id, amount):
        await self.ensure_user(user_id)

        await self.execute(
            """
            UPDATE users
            SET balance = ?
            WHERE user_id = ?
            """,
            (
                max(0, int(amount)),
                user_id
            )
        )

    async def add_balance(self, user_id, amount):
        await self.ensure_user(user_id)

        await self.execute(
            """
            UPDATE users
            SET balance = balance + ?
            WHERE user_id = ?
            """,
            (
                int(amount),
                user_id
            )
        )

    async def remove_balance(self, user_id, amount):
        await self.ensure_user(user_id)

        row = await self.get_user(user_id)

        current = row["balance"]

        if current < amount:
            return False

        await self.execute(
            """
            UPDATE users
            SET balance = balance - ?
            WHERE user_id = ?
            """,
            (
                int(amount),
                user_id
            )
        )

        return True

    # ==================================================
    # BANK
    # ==================================================

    async def set_bank(self, user_id, amount):
        await self.ensure_user(user_id)

        await self.execute(
            """
            UPDATE users
            SET bank = ?
            WHERE user_id = ?
            """,
            (
                max(0, int(amount)),
                user_id
            )
        )

    async def add_bank(self, user_id, amount):
        await self.ensure_user(user_id)

        await self.execute(
            """
            UPDATE users
            SET bank = bank + ?
            WHERE user_id = ?
            """,
            (
                int(amount),
                user_id
            )
        )

    async def remove_bank(self, user_id, amount):
        await self.ensure_user(user_id)

        row = await self.get_user(user_id)

        if row["bank"] < amount:
            return False

        await self.execute(
            """
            UPDATE users
            SET bank = bank - ?
            WHERE user_id = ?
            """,
            (
                int(amount),
                user_id
            )
        )

        return True

    # ==================================================
    # INVENTORY
    # ==================================================

    async def add_item(
        self,
        user_id,
        item_id,
        amount=1
    ):
        await self.ensure_user(user_id)

        existing = await self.fetchone(
            """
            SELECT amount
            FROM inventory
            WHERE user_id = ?
            AND item_id = ?
            """,
            (
                user_id,
                item_id
            )
        )

        if existing:
            await self.execute(
                """
                UPDATE inventory
                SET amount = amount + ?
                WHERE user_id = ?
                AND item_id = ?
                """,
                (
                    amount,
                    user_id,
                    item_id
                )
            )
        else:
            await self.execute(
                """
                INSERT INTO inventory
                (user_id, item_id, amount)
                VALUES (?, ?, ?)
                """,
                (
                    user_id,
                    item_id,
                    amount
                )
            )

    async def remove_item(
        self,
        user_id,
        item_id,
        amount=1
    ):
        existing = await self.fetchone(
            """
            SELECT amount
            FROM inventory
            WHERE user_id = ?
            AND item_id = ?
            """,
            (
                user_id,
                item_id
            )
        )

        if not existing or existing["amount"] < amount:
            return False

        new_amount = (
            existing["amount"] - amount
        )

        if new_amount <= 0:
            await self.execute(
                """
                DELETE FROM inventory
                WHERE user_id = ?
                AND item_id = ?
                """,
                (
                    user_id,
                    item_id
                )
            )
        else:
            await self.execute(
                """
                UPDATE inventory
                SET amount = ?
                WHERE user_id = ?
                AND item_id = ?
                """,
                (
                    new_amount,
                    user_id,
                    item_id
                )
            )

        return True

    async def get_inventory(self, user_id):
        return await self.fetchall(
            """
            SELECT *
            FROM inventory
            WHERE user_id = ?
            ORDER BY item_id
            """,
            (user_id,)
        )

    # ==================================================
    # TRANSACTIONS
    # ==================================================

    async def log_transaction(
        self,
        user_id,
        transaction_type,
        amount,
        description=""
    ):
        await self.execute(
            """
            INSERT INTO transactions
            (
                user_id,
                type,
                amount,
                description,
                created_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                user_id,
                transaction_type,
                amount,
                description,
                datetime.utcnow().isoformat()
            )
        )

    # ==================================================
    # OWNER LOGS
    # ==================================================

    async def log_owner_action(
        self,
        owner_id,
        action,
        target_id=None,
        details=""
    ):
        await self.execute(
            """
            INSERT INTO owner_actions
            (
                owner_id,
                action,
                target_id,
                details,
                created_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                owner_id,
                action,
                target_id,
                details,
                datetime.utcnow().isoformat()
            )
        )

    # ==================================================
    # CLOSE
    # ==================================================

    async def close(self):
        async with self._lock:
            self.conn.close()


# ==================================================
# SHARED DATABASE INSTANCE
# ==================================================

db = Database()
