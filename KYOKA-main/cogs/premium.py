import discord
from discord.ext import commands
from datetime import datetime, timedelta, timezone

from config import OWNER_ID, PREMIUM_NAME
from database.database import db
from utils.embeds import success, error, info, premium


class Premium(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # =========================================================
    # HELPERS
    # =========================================================

    def is_owner(self, user_id: int) -> bool:
        return user_id == OWNER_ID

    async def user_has_premium(
        self,
        guild_id: int,
        user_id: int
    ) -> bool:

        row = await db.fetchone(
            """
            SELECT expires_at
            FROM premium_users
            WHERE guild_id = ?
            AND user_id = ?
            """,
            (guild_id, user_id)
        )

        if not row:
            return False

        expires_at = row["expires_at"]

        if not expires_at:
            return True

        try:
            expires = datetime.fromisoformat(
                expires_at
            )

            if expires.tzinfo is None:
                expires = expires.replace(
                    tzinfo=timezone.utc
                )

            if expires <= datetime.now(timezone.utc):
                await db.execute(
                    """
                    DELETE FROM premium_users
                    WHERE guild_id = ?
                    AND user_id = ?
                    """,
                    (guild_id, user_id)
                )

                return False

        except (ValueError, TypeError):
            return False

        return True

    async def log_owner_action(
        self,
        ctx,
        action: str,
        target_id=None,
        details=""
    ):
        await db.log_owner_action(
            owner_id=ctx.author.id,
            action=action,
            target_id=target_id,
            details=details
        )

    # =========================================================
    # NORMAL PREMIUM STATUS
    # =========================================================

    @commands.hybrid_command(
        name="premium",
        description="Check your KYŌKA Premium status."
    )
    @commands.guild_only()
    async def premium_status(
        self,
        ctx: commands.Context
    ):
        active = await self.user_has_premium(
            ctx.guild.id,
            ctx.author.id
        )

        if not active:
            await ctx.send(
                embed=info(
                    "💎 Premium",
                    (
                        f"You don't currently have "
                        f"**{PREMIUM_NAME}**.\n\n"
                        "Ask the server owner for Premium access."
                    )
                )
            )
            return

        row = await db.fetchone(
            """
            SELECT expires_at
            FROM premium_users
            WHERE guild_id = ?
            AND user_id = ?
            """,
            (
                ctx.guild.id,
                ctx.author.id
            )
        )

        expires_at = row["expires_at"]

        try:
            timestamp = int(
                datetime.fromisoformat(
                    expires_at
                ).timestamp()
            )

            expiry = f"<t:{timestamp}:R>"

        except Exception:
            expiry = "Unknown"

        await ctx.send(
            embed=premium(
                "💎 Premium Active",
                (
                    f"**Plan:** {PREMIUM_NAME}\n"
                    f"**Expires:** {expiry}"
                )
            )
        )

    # =========================================================
    # OWNER-ONLY PREMIUM ADD
    #
    # k!premiumadd @user 30
    # /premiumadd @user 30
    #
    # ONLY OWNER_ID CAN USE THIS.
    # =========================================================

    @commands.hybrid_command(
        name="premiumadd",
        description="OWNER ONLY — Give Premium to a user."
    )
    @commands.guild_only()
    async def premium_add(
        self,
        ctx: commands.Context,
        user: discord.User,
        days: int = 30
    ):
        if not self.is_owner(ctx.author.id):
            await ctx.send(
                embed=error(
                    "You don't have permission to use this command."
                )
            )
            return

        if days < 1:
            await ctx.send(
                embed=error(
                    "Premium duration must be at least 1 day."
                )
            )
            return

        if days > 3650:
            await ctx.send(
                embed=error(
                    "Premium duration cannot exceed 3650 days."
                )
            )
            return

        now = datetime.now(timezone.utc)

        existing = await db.fetchone(
            """
            SELECT expires_at
            FROM premium_users
            WHERE guild_id = ?
            AND user_id = ?
            """,
            (
                ctx.guild.id,
                user.id
            )
        )

        if existing and existing["expires_at"]:
            try:
                current_expiry = datetime.fromisoformat(
                    existing["expires_at"]
                )

                if current_expiry.tzinfo is None:
                    current_expiry = current_expiry.replace(
                        tzinfo=timezone.utc
                    )

                if current_expiry > now:
                    expires_at = (
                        current_expiry
                        + timedelta(days=days)
                    )
                else:
                    expires_at = (
                        now
                        + timedelta(days=days)
                    )

            except Exception:
                expires_at = (
                    now
                    + timedelta(days=days)
                )

        else:
            expires_at = (
                now
                + timedelta(days=days)
            )

        await db.execute(
            """
            INSERT INTO premium_users
            (
                guild_id,
                user_id,
                expires_at,
                granted_by,
                created_at
            )
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(guild_id, user_id)
            DO UPDATE SET
                expires_at = excluded.expires_at,
                granted_by = excluded.granted_by
            """,
            (
                ctx.guild.id,
                user.id,
                expires_at.isoformat(),
                ctx.author.id,
                now.isoformat()
            )
        )

        await self.log_owner_action(
            ctx,
            "premium_add",
            user.id,
            f"Granted {days} days Premium"
        )

        await ctx.send(
            embed=success(
                f"💎 Premium granted to {user.mention} "
                f"for **{days} days**."
            )
        )

    # =========================================================
    # OWNER-ONLY PREMIUM REMOVE
    #
    # k!premiumremove @user
    # =========================================================

    @commands.hybrid_command(
        name="premiumremove",
        description="OWNER ONLY — Remove Premium from a user."
    )
    @commands.guild_only()
    async def premium_remove(
        self,
        ctx: commands.Context,
        user: discord.User
    ):
        if not self.is_owner(ctx.author.id):
            await ctx.send(
                embed=error(
                    "You don't have permission to use this command."
                )
            )
            return

        await db.execute(
            """
            DELETE FROM premium_users
            WHERE guild_id = ?
            AND user_id = ?
            """,
            (
                ctx.guild.id,
                user.id
            )
        )

        await self.log_owner_action(
            ctx,
            "premium_remove",
            user.id,
            "Removed Premium"
        )

        await ctx.send(
            embed=success(
                f"💎 Premium removed from {user.mention}."
            )
        )

    # =========================================================
    # OWNER-ONLY PREMIUM INFO
    # =========================================================

    @commands.hybrid_command(
        name="premiuminfo",
        description="OWNER ONLY — Check a user's Premium."
    )
    @commands.guild_only()
    async def premium_info(
        self,
        ctx: commands.Context,
        user: discord.User
    ):
        if not self.is_owner(ctx.author.id):
            await ctx.send(
                embed=error(
                    "You don't have permission to use this command."
                )
            )
            return

        row = await db.fetchone(
            """
            SELECT *
            FROM premium_users
            WHERE guild_id = ?
            AND user_id = ?
            """,
            (
                ctx.guild.id,
                user.id
            )
        )

        if not row:
            await ctx.send(
                embed=info(
                    "💎 Premium Info",
                    f"{user.mention} does not have Premium."
                )
            )
            return

        await ctx.send(
            embed=info(
                "💎 Premium Info",
                (
                    f"**User:** {user.mention}\n"
                    f"**User ID:** `{user.id}`\n"
                    f"**Expires:** `{row['expires_at']}`\n"
                    f"**Granted By:** `{row['granted_by']}`"
                )
            )
        )

    # =========================================================
    # OWNER-ONLY PREMIUM LIST
    # =========================================================

    @commands.hybrid_command(
        name="premiumlist",
        description="OWNER ONLY — List Premium users."
    )
    @commands.guild_only()
    async def premium_list(
        self,
        ctx: commands.Context
    ):
        if not self.is_owner(ctx.author.id):
            await ctx.send(
                embed=error(
                    "You don't have permission to use this command."
                )
            )
            return

        rows = await db.fetchall(
            """
            SELECT user_id, expires_at
            FROM premium_users
            WHERE guild_id = ?
            ORDER BY expires_at DESC
            LIMIT 25
            """,
            (ctx.guild.id,)
        )

        if not rows:
            await ctx.send(
                embed=info(
                    "💎 Premium Users",
                    "No Premium users found."
                )
            )
            return

        lines = []

        for index, row in enumerate(rows, 1):
            member = ctx.guild.get_member(
                row["user_id"]
            )

            if member:
                name = member.mention
            else:
                name = f"`{row['user_id']}`"

            lines.append(
                f"**{index}.** {name}\n"
                f"└ Expires: `{row['expires_at']}`"
            )

        await ctx.send(
            embed=info(
                "💎 Premium Users",
                "\n".join(lines)
            )
        )

    # =========================================================
    # OWNER-ONLY SERVER PREMIUM
    #
    # k!premiumserver 30
    # =========================================================

    @commands.hybrid_command(
        name="premiumserver",
        description="OWNER ONLY — Give Premium to this server."
    )
    @commands.guild_only()
    async def premium_server(
        self,
        ctx: commands.Context,
        days: int = 30
    ):
        if not self.is_owner(ctx.author.id):
            await ctx.send(
                embed=error(
                    "You don't have permission to use this command."
                )
            )
            return

        if days < 1:
            await ctx.send(
                embed=error(
                    "Duration must be at least 1 day."
                )
            )
            return

        if days > 3650:
            await ctx.send(
                embed=error(
                    "Duration cannot exceed 3650 days."
                )
            )
            return

        now = datetime.now(timezone.utc)

        existing = await db.fetchone(
            """
            SELECT expires_at
            FROM premium
            WHERE guild_id = ?
            """,
            (ctx.guild.id,)
        )

        if existing and existing["expires_at"]:
            try:
                current_expiry = datetime.fromisoformat(
                    existing["expires_at"]
                )

                if current_expiry.tzinfo is None:
                    current_expiry = current_expiry.replace(
                        tzinfo=timezone.utc
                    )

                if current_expiry > now:
                    expires_at = (
                        current_expiry
                        + timedelta(days=days)
                    )
                else:
                    expires_at = (
                        now
                        + timedelta(days=days)
                    )

            except Exception:
                expires_at = (
                    now
                    + timedelta(days=days)
                )
        else:
            expires_at = (
                now
                + timedelta(days=days)
            )

        await db.execute(
            """
            INSERT INTO premium
            (
                guild_id,
                enabled,
                expires_at,
                plan,
                activated_by,
                activated_at
            )
            VALUES (?, 1, ?, ?, ?, ?)
            ON CONFLICT(guild_id)
            DO UPDATE SET
                enabled = 1,
                expires_at = excluded.expires_at,
                plan = excluded.plan,
                activated_by = excluded.activated_by,
                activated_at = excluded.activated_at
            """,
            (
                ctx.guild.id,
                expires_at.isoformat(),
                PREMIUM_NAME,
                ctx.author.id,
                now.isoformat()
            )
        )

        await self.log_owner_action(
            ctx,
            "premium_server",
            ctx.guild.id,
            f"Enabled server Premium for {days} days"
        )

        await ctx.send(
            embed=success(
                f"💎 Server Premium enabled for "
                f"**{days} days**."
            )
        )

    # =========================================================
    # OWNER-ONLY SERVER PREMIUM CHECK
    # =========================================================

    @commands.hybrid_command(
        name="premiumcheck",
        description="OWNER ONLY — Check server Premium."
    )
    @commands.guild_only()
    async def premium_check(
        self,
        ctx: commands.Context
    ):
        if not self.is_owner(ctx.author.id):
            await ctx.send(
                embed=error(
                    "You don't have permission to use this command."
                )
            )
            return

        row = await db.fetchone(
            """
            SELECT *
            FROM premium
            WHERE guild_id = ?
            """,
            (ctx.guild.id,)
        )

        if not row or not row["enabled"]:
            await ctx.send(
                embed=error(
                    "💎 Server Premium is **INACTIVE**."
                )
            )
            return

        expires_at = row["expires_at"]

        if expires_at:
            try:
                expires = datetime.fromisoformat(
                    expires_at
                )

                if expires.tzinfo is None:
                    expires = expires.replace(
                        tzinfo=timezone.utc
                    )

                if expires <= datetime.now(timezone.utc):
                    await db.execute(
                        """
                        UPDATE premium
                        SET enabled = 0
                        WHERE guild_id = ?
                        """,
                        (ctx.guild.id,)
                    )

                    await ctx.send(
                        embed=error(
                            "💎 Server Premium has expired."
                        )
                    )
                    return

            except Exception:
                pass

        await ctx.send(
            embed=success(
                f"💎 Server Premium is **ACTIVE**.\n"
                f"Expires: `{expires_at}`"
            )
        )


async def setup(bot):
    await bot.add_cog(
        Premium(bot)
    )
