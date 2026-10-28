import discord
from discord.ext import commands

from config import OWNER_ID
from database.database import db


# =========================
# CREATOR CHECK
# =========================

def creator_only():
    async def predicate(ctx: commands.Context) -> bool:
        if ctx.author.id != OWNER_ID:
            raise commands.CheckFailure(
                "Only the KYŌKA creator can use this command."
            )

        return True

    return commands.check(predicate)


# =========================
# ADMIN CHECK
# =========================

def admin_only():
    async def predicate(ctx: commands.Context) -> bool:
        if not isinstance(ctx.author, discord.Member):
            return False

        if not ctx.author.guild_permissions.administrator:
            raise commands.CheckFailure(
                "You need Administrator permission to use this command."
            )

        return True

    return commands.check(predicate)


# =========================
# MODERATOR CHECK
# =========================

def moderator_only():
    async def predicate(ctx: commands.Context) -> bool:
        if not isinstance(ctx.author, discord.Member):
            return False

        permissions = ctx.author.guild_permissions

        if not any([
            permissions.administrator,
            permissions.manage_guild,
            permissions.manage_messages,
            permissions.kick_members,
            permissions.ban_members,
            permissions.moderate_members,
        ]):
            raise commands.CheckFailure(
                "You need moderator permissions to use this command."
            )

        return True

    return commands.check(predicate)


# =========================
# PREMIUM CHECK
# =========================

def premium_only():
    async def predicate(ctx: commands.Context) -> bool:
        if ctx.guild is None:
            raise commands.CheckFailure(
                "This command can only be used inside a server."
            )

        premium = await db.fetchone(
            """
            SELECT enabled, expires_at
            FROM premium
            WHERE guild_id = ?
            """,
            (ctx.guild.id,)
        )

        if not premium or not premium["enabled"]:
            raise commands.CheckFailure(
                "This is a KYŌKA Premium command."
            )

        return True

    return commands.check(predicate)


# =========================
# GUILD ONLY
# =========================

def guild_only():
    async def predicate(ctx: commands.Context) -> bool:
        if ctx.guild is None:
            raise commands.CheckFailure(
                "This command can only be used inside a server."
            )

        return True

    return commands.check(predicate)


# =========================
# BOT PERMISSION CHECK
# =========================

def bot_has_permissions(**permissions):
    async def predicate(ctx: commands.Context) -> bool:
        if ctx.guild is None:
            return False

        me = ctx.guild.me

        if me is None:
            return False

        missing = []

        for permission, required in permissions.items():
            if required and not getattr(
                me.guild_permissions,
                permission,
                False
            ):
                missing.append(permission)

        if missing:
            formatted = ", ".join(
                permission.replace("_", " ")
                for permission in missing
            )

            raise commands.CheckFailure(
                f"I am missing these permissions: {formatted}"
            )

        return True

    return commands.check(predicate)


# =========================
# USER PERMISSION CHECK
# =========================

def user_has_permissions(**permissions):
    async def predicate(ctx: commands.Context) -> bool:
        if ctx.guild is None:
            return False

        if not isinstance(ctx.author, discord.Member):
            return False

        missing = []

        for permission, required in permissions.items():
            if required and not getattr(
                ctx.author.guild_permissions,
                permission,
                False
            ):
                missing.append(permission)

        if missing:
            formatted = ", ".join(
                permission.replace("_", " ")
                for permission in missing
            )

            raise commands.CheckFailure(
                f"You are missing these permissions: {formatted}"
            )

        return True

    return commands.check(predicate)


# =========================
# PREMIUM OR CREATOR
# =========================

def premium_or_creator():
    async def predicate(ctx: commands.Context) -> bool:
        if ctx.author.id == OWNER_ID:
            return True

        if ctx.guild is None:
            return False

        premium = await db.fetchone(
            """
            SELECT enabled
            FROM premium
            WHERE guild_id = ?
            """,
            (ctx.guild.id,)
        )

        if premium and premium["enabled"]:
            return True

        raise commands.CheckFailure(
            "This feature requires KYŌKA Premium."
        )

    return commands.check(predicate)
