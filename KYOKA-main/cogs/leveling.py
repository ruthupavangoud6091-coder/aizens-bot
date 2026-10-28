import random
import time

import discord
from discord.ext import commands

from database.database import db
from utils.checks import guild_only
from utils.embeds import success, error, info


class Leveling(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        # Per-user message cooldown.
        self.xp_cooldowns = {}

    # =========================================================
    # DATABASE
    # =========================================================

    async def get_settings(self, guild_id: int):
        row = await db.fetchone(
            """
            SELECT *
            FROM leveling_settings
            WHERE guild_id = ?
            """,
            (guild_id,)
        )

        if row:
            return row

        await db.execute(
            """
            INSERT OR IGNORE INTO leveling_settings
            (
                guild_id,
                enabled,
                xp_min,
                xp_max,
                cooldown,
                levelup_channel_id,
                levelup_message
            )
            VALUES (?, 1, 10, 20, 60, NULL, ?)
            """,
            (
                guild_id,
                "🎉 {user} reached **Level {level}**!"
            ),
            commit=True
        )

        return await db.fetchone(
            """
            SELECT *
            FROM leveling_settings
            WHERE guild_id = ?
            """,
            (guild_id,)
        )

    async def get_user(self, guild_id: int, user_id: int):
        return await db.ensure_user(
            guild_id,
            user_id
        )

    # =========================================================
    # XP CALCULATION
    # =========================================================

    def xp_required(self, level: int):
        """
        XP required to reach the next level.

        Example:
        Level 1 -> 100 XP
        Level 2 -> 150 XP
        Level 3 -> 200 XP
        """
        return 100 + ((level - 1) * 50)

    def total_xp_for_level(self, level: int):
        total = 0

        for current in range(1, level):
            total += self.xp_required(
                current
            )

        return total

    def level_from_xp(self, xp: int):
        level = 1

        while xp >= self.total_xp_for_level(
            level + 1
        ):
            level += 1

            if level >= 1000:
                break

        return level

    def progress_for_level(self, xp: int):
        level = self.level_from_xp(xp)

        current_level_xp = self.total_xp_for_level(
            level
        )

        next_level_xp = self.total_xp_for_level(
            level + 1
        )

        current = max(
            0,
            xp - current_level_xp
        )

        required = (
            next_level_xp
            - current_level_xp
        )

        return (
            level,
            current,
            required
        )

    # =========================================================
    # VARIABLES
    # =========================================================

    def replace_variables(
        self,
        message: str,
        member: discord.Member,
        level: int
    ):
        replacements = {
            "{user}": member.mention,
            "{username}": member.name,
            "{displayname}": member.display_name,
            "{level}": str(level),
            "{server}": member.guild.name,
            "{membercount}": str(
                member.guild.member_count or 0
            )
        }

        for key, value in replacements.items():
            message = message.replace(
                key,
                value
            )

        return message

    # =========================================================
    # MESSAGE XP
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

        settings = await self.get_settings(
            message.guild.id
        )

        if not settings["enabled"]:
            return

        user_id = message.author.id
        guild_id = message.guild.id

        cooldown_key = (
            guild_id,
            user_id
        )

        now = time.time()

        last_xp = self.xp_cooldowns.get(
            cooldown_key,
            0
        )

        cooldown = max(
            1,
            int(settings["cooldown"])
        )

        if now - last_xp < cooldown:
            return

        self.xp_cooldowns[
            cooldown_key
        ] = now

        xp_min = max(
            1,
            int(settings["xp_min"])
        )

        xp_max = max(
            xp_min,
            int(settings["xp_max"])
        )

        gained = random.randint(
            xp_min,
            xp_max
        )

        user = await self.get_user(
            guild_id,
            user_id
        )

        old_xp = int(
            user["xp"] or 0
        )

        old_level = self.level_from_xp(
            old_xp
        )

        new_xp = old_xp + gained

        new_level = self.level_from_xp(
            new_xp
        )

        await db.execute(
            """
            UPDATE users
            SET xp = ?,
                level = ?
            WHERE guild_id = ?
            AND user_id = ?
            """,
            (
                new_xp,
                new_level,
                guild_id,
                user_id
            ),
            commit=True
        )

        # -----------------------------------------------------
        # LEVEL UP
        # -----------------------------------------------------

        if new_level <= old_level:
            return

        channel_id = settings[
            "levelup_channel_id"
        ]

        channel = (
            message.guild.get_channel(
                int(channel_id)
            )
            if channel_id
            else message.channel
        )

        if not channel:
            return

        level_message = (
            settings["levelup_message"]
            or "🎉 {user} reached **Level {level}**!"
        )

        level_message = self.replace_variables(
            level_message,
            message.author,
            new_level
        )

        embed = discord.Embed(
            title="🎉 Level Up!",
            description=level_message,
            color=discord.Color.gold()
        )

        embed.set_thumbnail(
            url=message.author.display_avatar.url
        )

        try:
            await channel.send(
                embed=embed,
                allowed_mentions=discord.AllowedMentions(
                    users=True,
                    roles=False,
                    everyone=False
                )
            )
        except discord.HTTPException:
            pass

        # -----------------------------------------------------
        # LEVEL ROLE REWARDS
        # -----------------------------------------------------

        await self.apply_level_roles(
            message.author,
            new_level
        )

    # =========================================================
    # LEVEL ROLE REWARDS
    # =========================================================

    async def apply_level_roles(
        self,
        member: discord.Member,
        level: int
    ):
        rows = await db.fetchall(
            """
            SELECT *
            FROM level_roles
            WHERE guild_id = ?
            AND level <= ?
            ORDER BY level DESC
            """,
            (
                member.guild.id,
                level
            )
        )

        if not rows:
            return

        selected_role = None

        for row in rows:
            role = member.guild.get_role(
                int(row["role_id"])
            )

            if role:
                selected_role = role
                break

        if not selected_role:
            return

        if selected_role in member.roles:
            return

        try:
            await member.add_roles(
                selected_role,
                reason=f"KYŌKA level {level} reward"
            )
        except discord.HTTPException:
            pass

    # =========================================================
    # LEVEL GROUP
    # =========================================================

    @commands.hybrid_group(
        name="level",
        description="View and manage the leveling system."
    )
    @guild_only()
    async def level(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send(
                embed=info(
                    "⭐ Leveling",
                    (
                        "`k!level rank`\n"
                        "`k!level level`\n"
                        "`k!level leaderboard`\n"
                        "`k!level settings`\n"
                        "`k!level enable`\n"
                        "`k!level disable`"
                    )
                )
            )

    # =========================================================
    # RANK
    # =========================================================

    @level.command(
        name="rank",
        description="Show your or another member's rank."
    )
    async def level_rank(
        self,
        ctx,
        member: discord.Member = None
    ):
        member = member or ctx.author

        user = await self.get_user(
            ctx.guild.id,
            member.id
        )

        xp = int(
            user["xp"] or 0
        )

        level, current, required = (
            self.progress_for_level(xp)
        )

        rows = await db.fetchall(
            """
            SELECT user_id, xp
            FROM users
            WHERE guild_id = ?
            ORDER BY xp DESC
            """,
            (ctx.guild.id,)
        )

        rank = 1

        for index, row in enumerate(rows, 1):
            if int(row["user_id"]) == member.id:
                rank = index
                break

        progress_percent = (
            current / required * 100
            if required
            else 0
        )

        bars = 10
        filled = int(
            progress_percent / 100 * bars
        )

        progress_bar = (
            "█" * filled
            + "░" * (bars - filled)
        )

        embed = discord.Embed(
            title=f"⭐ {member.display_name}'s Rank",
            color=discord.Color.blurple()
        )

        embed.set_thumbnail(
            url=member.display_avatar.url
        )

        embed.add_field(
            name="🏆 Level",
            value=f"`{level}`",
            inline=True
        )

        embed.add_field(
            name="📊 Server Rank",
            value=f"`#{rank}`",
            inline=True
        )

        embed.add_field(
            name="✨ XP",
            value=f"`{xp}`",
            inline=True
        )

        embed.add_field(
            name="Progress",
            value=(
                f"`{progress_bar}` "
                f"`{current}/{required}` "
                f"({progress_percent:.1f}%)"
            ),
            inline=False
        )

        await ctx.send(
            embed=embed
        )

    # =========================================================
    # LEVEL
    # =========================================================

    @level.command(
        name="level",
        description="Show a member's level."
    )
    async def level_level(
        self,
        ctx,
        member: discord.Member = None
    ):
        member = member or ctx.author

        user = await self.get_user(
            ctx.guild.id,
            member.id
        )

        xp = int(
            user["xp"] or 0
        )

        level = self.level_from_xp(
            xp
        )

        await ctx.send(
            embed=info(
                "⭐ Level",
                f"{member.mention} is **Level {level}**."
            )
        )

    # =========================================================
    # LEADERBOARD
    # =========================================================

    @level.command(
        name="leaderboard",
        aliases=["lb", "top"],
        description="Show the server XP leaderboard."
    )
    async def level_leaderboard(
        self,
        ctx
    ):
        rows = await db.fetchall(
            """
            SELECT user_id, xp, level
            FROM users
            WHERE guild_id = ?
            ORDER BY xp DESC
            LIMIT 10
            """,
            (ctx.guild.id,)
        )

        if not rows:
            await ctx.send(
                embed=info(
                    "🏆 Leaderboard",
                    "No XP data exists yet."
                )
            )
            return

        lines = []

        medals = [
            "🥇",
            "🥈",
            "🥉"
        ]

        for index, row in enumerate(
            rows,
            1
        ):
            member = ctx.guild.get_member(
                int(row["user_id"])
            )

            if member:
                name = member.display_name
            else:
                name = f"User {row['user_id']}"

            prefix = (
                medals[index - 1]
                if index <= 3
                else f"`#{index}`"
            )

            lines.append(
                f"{prefix} **{name}** — "
                f"Level `{row['level']}` • "
                f"`{row['xp']} XP`"
            )

        await ctx.send(
            embed=info(
                "🏆 XP Leaderboard",
                "\n".join(lines)
            )
        )

    # =========================================================
    # SETTINGS
    # =========================================================

    @level.command(
        name="settings",
        description="Show leveling settings."
    )
    @commands.has_permissions(manage_guild=True)
    async def level_settings(
        self,
        ctx
    ):
        settings = await self.get_settings(
            ctx.guild.id
        )

        channel = (
            f"<#{settings['levelup_channel_id']}>"
            if settings["levelup_channel_id"]
            else "Current channel"
        )

        embed = discord.Embed(
            title="⚙️ Leveling Settings",
            color=discord.Color.blurple()
        )

        embed.add_field(
            name="Enabled",
            value=(
                "Yes"
                if settings["enabled"]
                else "No"
            ),
            inline=True
        )

        embed.add_field(
            name="XP Range",
            value=(
                f"{settings['xp_min']}-"
                f"{settings['xp_max']}"
            ),
            inline=True
        )

        embed.add_field(
            name="Cooldown",
            value=f"{settings['cooldown']}s",
            inline=True
        )

        embed.add_field(
            name="Level-up Channel",
            value=channel,
            inline=False
        )

        await ctx.send(
            embed=embed
        )

    # =========================================================
    # ENABLE
    # =========================================================

    @level.command(
        name="enable",
        description="Enable leveling."
    )
    @commands.has_permissions(manage_guild=True)
    async def level_enable(
        self,
        ctx
    ):
        await self.get_settings(
            ctx.guild.id
        )

        await db.execute(
            """
            UPDATE leveling_settings
            SET enabled = 1
            WHERE guild_id = ?
            """,
            (ctx.guild.id,),
            commit=True
        )

        await ctx.send(
            embed=success(
                "⭐ Leveling is now **enabled**."
            )
        )

    # =========================================================
    # DISABLE
    # =========================================================

    @level.command(
        name="disable",
        description="Disable leveling."
    )
    @commands.has_permissions(manage_guild=True)
    async def level_disable(
        self,
        ctx
    ):
        await self.get_settings(
            ctx.guild.id
        )

        await db.execute(
            """
            UPDATE leveling_settings
            SET enabled = 0
            WHERE guild_id = ?
            """,
            (ctx.guild.id,),
            commit=True
        )

        await ctx.send(
            embed=success(
                "⭐ Leveling is now **disabled**."
            )
        )

    # =========================================================
    # XP ADMIN GROUP
    # =========================================================

    @commands.hybrid_group(
        name="xp",
        description="Manage member XP."
    )
    @commands.has_permissions(manage_guild=True)
    @guild_only()
    async def xp(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send(
                embed=info(
                    "✨ XP Management",
                    (
                        "`k!xp add @user 100`\n"
                        "`k!xp remove @user 100`\n"
                        "`k!xp set @user 1000`"
                    )
                )
            )

    # =========================================================
    # ADD XP
    # =========================================================

    @xp.command(
        name="add",
        description="Add XP to a member."
    )
    async def xp_add(
        self,
        ctx,
        member: discord.Member,
        amount: int
    ):
        if amount <= 0:
            await ctx.send(
                embed=error(
                    "XP amount must be greater than 0."
                )
            )
            return

        if amount > 1_000_000:
            await ctx.send(
                embed=error(
                    "Maximum XP change is 1,000,000."
                )
            )
            return

        user = await self.get_user(
            ctx.guild.id,
            member.id
        )

        old_xp = int(
            user["xp"] or 0
        )

        new_xp = old_xp + amount

        old_level = self.level_from_xp(
            old_xp
        )

        new_level = self.level_from_xp(
            new_xp
        )

        await db.execute(
            """
            UPDATE users
            SET xp = ?,
                level = ?
            WHERE guild_id = ?
            AND user_id = ?
            """,
            (
                new_xp,
                new_level,
                ctx.guild.id,
                member.id
            ),
            commit=True
        )

        await ctx.send(
            embed=success(
                f"✨ Added **{amount} XP** to "
                f"{member.mention}."
            )
        )

        if new_level > old_level:
            await self.apply_level_roles(
                member,
                new_level
            )

    # =========================================================
    # REMOVE XP
    # =========================================================

    @xp.command(
        name="remove",
        description="Remove XP from a member."
    )
    async def xp_remove(
        self,
        ctx,
        member: discord.Member,
        amount: int
    ):
        if amount <= 0:
            await ctx.send(
                embed=error(
                    "XP amount must be greater than 0."
                )
            )
            return

        user = await self.get_user(
            ctx.guild.id,
            member.id
        )

        old_xp = int(
            user["xp"] or 0
        )

        new_xp = max(
            0,
            old_xp - amount
        )

        new_level = self.level_from_xp(
            new_xp
        )

        await db.execute(
            """
            UPDATE users
            SET xp = ?,
                level = ?
            WHERE guild_id = ?
            AND user_id = ?
            """,
            (
                new_xp,
                new_level,
                ctx.guild.id,
                member.id
            ),
            commit=True
        )

        await ctx.send(
            embed=success(
                f"✨ Removed **{amount} XP** from "
                f"{member.mention}."
            )
        )

    # =========================================================
    # SET XP
    # =========================================================

    @xp.command(
        name="set",
        description="Set a member's XP."
    )
    async def xp_set(
        self,
        ctx,
        member: discord.Member,
        amount: int
    ):
        if amount < 0:
            await ctx.send(
                embed=error(
                    "XP cannot be negative."
                )
            )
            return

        if amount > 100_000_000:
            await ctx.send(
                embed=error(
                    "Maximum XP is 100,000,000."
                )
            )
            return

        new_level = self.level_from_xp(
            amount
        )

        await self.get_user(
            ctx.guild.id,
            member.id
        )

        await db.execute(
            """
            UPDATE users
            SET xp = ?,
                level = ?
            WHERE guild_id = ?
            AND user_id = ?
            """,
            (
                amount,
                new_level,
                ctx.guild.id,
                member.id
            ),
            commit=True
        )

        await ctx.send(
            embed=success(
                f"✨ Set {member.mention}'s XP to "
                f"**{amount}**.\n"
                f"Level: **{new_level}**"
            )
        )

        await self.apply_level_roles(
            member,
            new_level
        )


async def setup(bot):
    await bot.add_cog(
        Leveling(bot)
    )
