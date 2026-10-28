import re
import time
from collections import defaultdict, deque
from datetime import timedelta

import discord
from discord.ext import commands

from database.database import db
from utils.checks import guild_only
from utils.embeds import success, error, info


class AutoMod(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        # guild_id -> user_id -> message timestamps
        self.spam_tracker = defaultdict(
            lambda: defaultdict(deque)
        )

        # guild_id -> user_id -> strike count
        self.strikes = defaultdict(
            lambda: defaultdict(int)
        )

        # Default configuration.
        self.defaults = {
            "anti_spam": 1,
            "anti_invite": 1,
            "link_filter": 0,
            "bad_words": 0,
            "mention_spam": 1,
            "anti_raid": 1,
        }

        self.bad_words = {
            "badword",
            "examplebadword",
        }

    # =========================================================
    # DATABASE
    # =========================================================

    async def get_settings(self, guild_id: int):
        row = await db.fetchone(
            """
            SELECT *
            FROM automod_settings
            WHERE guild_id = ?
            """,
            (guild_id,)
        )

        if row:
            return row

        await db.execute(
            """
            INSERT OR IGNORE INTO automod_settings
            (
                guild_id,
                anti_spam,
                anti_invite,
                link_filter,
                bad_words,
                mention_spam,
                anti_raid
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                guild_id,
                self.defaults["anti_spam"],
                self.defaults["anti_invite"],
                self.defaults["link_filter"],
                self.defaults["bad_words"],
                self.defaults["mention_spam"],
                self.defaults["anti_raid"],
            ),
            commit=True
        )

        return await db.fetchone(
            """
            SELECT *
            FROM automod_settings
            WHERE guild_id = ?
            """,
            (guild_id,)
        )

    # =========================================================
    # HELPERS
    # =========================================================

    def is_invite(self, content: str):
        patterns = [
            r"discord\.gg/",
            r"discord\.com/invite/",
            r"discordapp\.com/invite/",
        ]

        return any(
            re.search(
                pattern,
                content,
                re.IGNORECASE
            )
            for pattern in patterns
        )

    def contains_link(self, content: str):
        return bool(
            re.search(
                r"https?://\S+|www\.\S+",
                content,
                re.IGNORECASE
            )
        )

    def contains_bad_word(self, content: str):
        lowered = content.lower()

        return any(
            word.lower() in lowered
            for word in self.bad_words
        )

    async def add_strike(
        self,
        guild: discord.Guild,
        member: discord.Member,
        reason: str
    ):
        guild_id = guild.id
        user_id = member.id

        self.strikes[guild_id][user_id] += 1

        strikes = self.strikes[
            guild_id
        ][user_id]

        if strikes < 3:
            return

        self.strikes[
            guild_id
        ][user_id] = 0

        try:
            await member.timeout(
                timedelta(minutes=5),
                reason=f"KYŌKA AutoMod: {reason}"
            )
        except discord.HTTPException:
            pass

    async def delete_message(
        self,
        message: discord.Message,
        reason: str
    ):
        try:
            await message.delete()
        except discord.HTTPException:
            return False

        try:
            warning = await message.channel.send(
                f"🛡️ {message.author.mention}, "
                f"your message was removed: **{reason}**.",
                delete_after=5
            )

            return warning

        except discord.HTTPException:
            return True

    # =========================================================
    # AUTOMOD GROUP
    # =========================================================

    @commands.hybrid_group(
        name="automod",
        description="Configure KYŌKA AutoMod."
    )
    @commands.has_permissions(manage_guild=True)
    @guild_only()
    async def automod(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send(
                embed=info(
                    "🛡️ AutoMod",
                    (
                        "`k!automod enable <setting>`\n"
                        "`k!automod disable <setting>`\n"
                        "`k!automod status`\n"
                        "`k!automod setting <setting> <on/off>`\n\n"
                        "**Settings:**\n"
                        "`anti_spam`\n"
                        "`anti_invite`\n"
                        "`link_filter`\n"
                        "`bad_words`\n"
                        "`mention_spam`\n"
                        "`anti_raid`"
                    )
                )
            )

    # =========================================================
    # ENABLE
    # =========================================================

    @automod.command(
        name="enable",
        description="Enable an AutoMod protection."
    )
    async def automod_enable(
        self,
        ctx,
        setting: str
    ):
        setting = setting.lower()

        if setting not in self.defaults:
            await ctx.send(
                embed=error(
                    "Unknown AutoMod setting."
                )
            )
            return

        await self.get_settings(
            ctx.guild.id
        )

        await db.execute(
            f"""
            UPDATE automod_settings
            SET {setting} = 1
            WHERE guild_id = ?
            """,
            (ctx.guild.id,),
            commit=True
        )

        await ctx.send(
            embed=success(
                f"🛡️ `{setting}` is now **enabled**."
            )
        )

    # =========================================================
    # DISABLE
    # =========================================================

    @automod.command(
        name="disable",
        description="Disable an AutoMod protection."
    )
    async def automod_disable(
        self,
        ctx,
        setting: str
    ):
        setting = setting.lower()

        if setting not in self.defaults:
            await ctx.send(
                embed=error(
                    "Unknown AutoMod setting."
                )
            )
            return

        await self.get_settings(
            ctx.guild.id
        )

        await db.execute(
            f"""
            UPDATE automod_settings
            SET {setting} = 0
            WHERE guild_id = ?
            """,
            (ctx.guild.id,),
            commit=True
        )

        await ctx.send(
            embed=success(
                f"🛡️ `{setting}` is now **disabled**."
            )
        )

    # =========================================================
    # SETTING
    # =========================================================

    @automod.command(
        name="setting",
        description="Enable or disable an AutoMod setting."
    )
    async def automod_setting(
        self,
        ctx,
        setting: str,
        state: str
    ):
        setting = setting.lower()
        state = state.lower()

        if setting not in self.defaults:
            await ctx.send(
                embed=error(
                    "Unknown AutoMod setting."
                )
            )
            return

        enabled_values = {
            "on",
            "enable",
            "enabled",
            "true",
            "1"
        }

        disabled_values = {
            "off",
            "disable",
            "disabled",
            "false",
            "0"
        }

        if state in enabled_values:
            value = 1
        elif state in disabled_values:
            value = 0
        else:
            await ctx.send(
                embed=error(
                    "State must be `on` or `off`."
                )
            )
            return

        await self.get_settings(
            ctx.guild.id
        )

        await db.execute(
            f"""
            UPDATE automod_settings
            SET {setting} = ?
            WHERE guild_id = ?
            """,
            (
                value,
                ctx.guild.id
            ),
            commit=True
        )

        status = (
            "enabled"
            if value
            else "disabled"
        )

        await ctx.send(
            embed=success(
                f"🛡️ `{setting}` is now **{status}**."
            )
        )

    # =========================================================
    # STATUS
    # =========================================================

    @automod.command(
        name="status",
        description="Show AutoMod configuration."
    )
    async def automod_status(self, ctx):
        settings = await self.get_settings(
            ctx.guild.id
        )

        names = {
            "anti_spam": "Anti-Spam",
            "anti_invite": "Anti-Invite",
            "link_filter": "Link Filter",
            "bad_words": "Bad Words",
            "mention_spam": "Mention Spam",
            "anti_raid": "Anti-Raid",
        }

        lines = []

        for key, name in names.items():
            enabled = bool(
                settings[key]
            )

            lines.append(
                f"{'🟢' if enabled else '🔴'} "
                f"**{name}**"
            )

        await ctx.send(
            embed=info(
                "🛡️ AutoMod Status",
                "\n".join(lines)
            )
        )

    # =========================================================
    # MESSAGE MODERATION
    # =========================================================

    @commands.Cog.listener()
    async def on_message(
        self,
        message: discord.Message
    ):
        if message.author.bot:
            return

        if not message.guild:
            return

        if not message.content:
            return

        if not isinstance(
            message.author,
            discord.Member
        ):
            return

        settings = await self.get_settings(
            message.guild.id
        )

        content = message.content

        # -----------------------------------------------------
        # ANTI-SPAM
        # -----------------------------------------------------

        if settings["anti_spam"]:
            guild_id = message.guild.id
            user_id = message.author.id

            timestamps = self.spam_tracker[
                guild_id
            ][user_id]

            now = time.monotonic()

            timestamps.append(now)

            while timestamps and (
                now - timestamps[0] > 8
            ):
                timestamps.popleft()

            if len(timestamps) >= 6:
                timestamps.clear()

                deleted = await self.delete_message(
                    message,
                    "spam"
                )

                if deleted:
                    await self.add_strike(
                        message.guild,
                        message.author,
                        "spam"
                    )

                return

        # -----------------------------------------------------
        # MENTION SPAM
        # -----------------------------------------------------

        if settings["mention_spam"]:
            mention_count = (
                len(message.mentions)
                + len(message.role_mentions)
            )

            if (
                mention_count >= 5
                or message.mention_everyone
            ):
                deleted = await self.delete_message(
                    message,
                    "mention spam"
                )

                if deleted:
                    await self.add_strike(
                        message.guild,
                        message.author,
                        "mention spam"
                    )

                return

        # -----------------------------------------------------
        # ANTI INVITE
        # -----------------------------------------------------

        if (
            settings["anti_invite"]
            and self.is_invite(content)
        ):
            deleted = await self.delete_message(
                message,
                "Discord invite links are not allowed"
            )

            if deleted:
                await self.add_strike(
                    message.guild,
                    message.author,
                    "Discord invite"
                )

            return

        # -----------------------------------------------------
        # LINK FILTER
        # -----------------------------------------------------

        if (
            settings["link_filter"]
            and self.contains_link(content)
        ):
            deleted = await self.delete_message(
                message,
                "links are not allowed"
            )

            if deleted:
                await self.add_strike(
                    message.guild,
                    message.author,
                    "blocked link"
                )

            return

        # -----------------------------------------------------
        # BAD WORDS
        # -----------------------------------------------------

        if (
            settings["bad_words"]
            and self.contains_bad_word(content)
        ):
            deleted = await self.delete_message(
                message,
                "inappropriate language"
            )

            if deleted:
                await self.add_strike(
                    message.guild,
                    message.author,
                    "bad language"
                )

            return

    # =========================================================
    # ANTI RAID
    # =========================================================

    @commands.Cog.listener()
    async def on_member_join(
        self,
        member: discord.Member
    ):
        if member.bot:
            return

        settings = await self.get_settings(
            member.guild.id
        )

        if not settings["anti_raid"]:
            return

        account_age = (
            discord.utils.utcnow()
            - member.created_at
        )

        # Accounts younger than 24 hours
        # are flagged for staff attention.
        if account_age.total_seconds() < 86400:
            channel = member.guild.system_channel

            if not channel:
                return

            try:
                await channel.send(
                    f"🛡️ **AutoMod Alert:** "
                    f"{member.mention} joined with an account "
                    f"younger than **24 hours**.",
                    allowed_mentions=discord.AllowedMentions(
                        users=True,
                        roles=False,
                        everyone=False
                    ),
                    delete_after=15
                )
            except discord.HTTPException:
                pass


async def setup(bot):
    await bot.add_cog(
        AutoMod(bot)
    )
