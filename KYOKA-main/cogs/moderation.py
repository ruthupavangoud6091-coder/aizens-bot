import discord
from discord.ext import commands
from datetime import timedelta

from utils.embeds import success, error, warning, info
from utils.permissions import can_act_on


class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # =========================
    # BAN
    # =========================

    @commands.hybrid_command(
        name="ban",
        description="Ban a member from the server."
    )
    @commands.bot_has_permissions(ban_members=True)
    @commands.has_permissions(ban_members=True)
    async def ban(
        self,
        ctx: commands.Context,
        member: discord.Member,
        *,
        reason: str = "No reason provided."
    ):
        if not can_act_on(ctx.author, member):
            return await ctx.send(
                embed=error(
                    "Cannot Ban",
                    "You cannot ban this member."
                )
            )

        try:
            await member.ban(reason=reason)

            await ctx.send(
                embed=success(
                    "Member Banned",
                    f"**{member}** has been banned.\n"
                    f"**Reason:** {reason}"
                )
            )

        except discord.Forbidden:
            await ctx.send(
                embed=error(
                    "Permission Error",
                    "I cannot ban that member."
                )
            )

    # =========================
    # UNBAN
    # =========================

    @commands.hybrid_command(
        name="unban",
        description="Unban a user."
    )
    @commands.bot_has_permissions(ban_members=True)
    @commands.has_permissions(ban_members=True)
    async def unban(
        self,
        ctx: commands.Context,
        user_id: str
    ):
        try:
            user = await self.bot.fetch_user(int(user_id))
            await ctx.guild.unban(user)

            await ctx.send(
                embed=success(
                    "User Unbanned",
                    f"**{user}** has been unbanned."
                )
            )

        except ValueError:
            await ctx.send(
                embed=error(
                    "Invalid ID",
                    "Please provide a valid Discord user ID."
                )
            )

        except discord.NotFound:
            await ctx.send(
                embed=error(
                    "Not Found",
                    "That user is not currently banned."
                )
            )

        except discord.Forbidden:
            await ctx.send(
                embed=error(
                    "Permission Error",
                    "I cannot unban users in this server."
                )
            )

    # =========================
    # KICK
    # =========================

    @commands.hybrid_command(
        name="kick",
        description="Kick a member from the server."
    )
    @commands.bot_has_permissions(kick_members=True)
    @commands.has_permissions(kick_members=True)
    async def kick(
        self,
        ctx: commands.Context,
        member: discord.Member,
        *,
        reason: str = "No reason provided."
    ):
        if not can_act_on(ctx.author, member):
            return await ctx.send(
                embed=error(
                    "Cannot Kick",
                    "You cannot kick this member."
                )
            )

        try:
            await member.kick(reason=reason)

            await ctx.send(
                embed=success(
                    "Member Kicked",
                    f"**{member}** has been kicked.\n"
                    f"**Reason:** {reason}"
                )
            )

        except discord.Forbidden:
            await ctx.send(
                embed=error(
                    "Permission Error",
                    "I cannot kick that member."
                )
            )

    # =========================
    # TIMEOUT
    # =========================

    @commands.hybrid_command(
        name="timeout",
        description="Timeout a member."
    )
    @commands.bot_has_permissions(moderate_members=True)
    @commands.has_permissions(moderate_members=True)
    async def timeout(
        self,
        ctx: commands.Context,
        member: discord.Member,
        minutes: int,
        *,
        reason: str = "No reason provided."
    ):
        if minutes < 1:
            return await ctx.send(
                embed=error(
                    "Invalid Duration",
                    "Timeout duration must be at least 1 minute."
                )
            )

        if minutes > 40320:
            return await ctx.send(
                embed=error(
                    "Invalid Duration",
                    "Discord allows a maximum timeout of 28 days."
                )
            )

        if not can_act_on(ctx.author, member):
            return await ctx.send(
                embed=error(
                    "Cannot Timeout",
                    "You cannot timeout this member."
                )
            )

        try:
            await member.timeout(
                timedelta(minutes=minutes),
                reason=reason
            )

            await ctx.send(
                embed=success(
                    "Member Timed Out",
                    f"**{member}** has been timed out for "
                    f"**{minutes} minute(s)**.\n"
                    f"**Reason:** {reason}"
                )
            )

        except discord.Forbidden:
            await ctx.send(
                embed=error(
                    "Permission Error",
                    "I cannot timeout that member."
                )
            )

    # =========================
    # MUTE
    # =========================

    @commands.hybrid_command(
        name="mute",
        description="Mute a member using Discord timeout."
    )
    @commands.bot_has_permissions(moderate_members=True)
    @commands.has_permissions(moderate_members=True)
    async def mute(
        self,
        ctx: commands.Context,
        member: discord.Member,
        minutes: int = 10,
        *,
        reason: str = "No reason provided."
    ):
        if minutes < 1:
            return await ctx.send(
                embed=error(
                    "Invalid Duration",
                    "Duration must be at least 1 minute."
                )
            )

        if minutes > 40320:
            return await ctx.send(
                embed=error(
                    "Invalid Duration",
                    "Maximum timeout duration is 28 days."
                )
            )

        if not can_act_on(ctx.author, member):
            return await ctx.send(
                embed=error(
                    "Cannot Mute",
                    "You cannot mute this member."
                )
            )

        try:
            await member.timeout(
                timedelta(minutes=minutes),
                reason=reason
            )

            await ctx.send(
                embed=success(
                    "Member Muted",
                    f"**{member}** has been muted for "
                    f"**{minutes} minute(s)**."
                )
            )

        except discord.Forbidden:
            await ctx.send(
                embed=error(
                    "Permission Error",
                    "I cannot mute that member."
                )
            )

    # =========================
    # UNMUTE
    # =========================

    @commands.hybrid_command(
        name="unmute",
        description="Remove a member's timeout."
    )
    @commands.bot_has_permissions(moderate_members=True)
    @commands.has_permissions(moderate_members=True)
    async def unmute(
        self,
        ctx: commands.Context,
        member: discord.Member
    ):
        if not can_act_on(ctx.author, member):
            return await ctx.send(
                embed=error(
                    "Cannot Unmute",
                    "You cannot modify this member."
                )
            )

        try:
            await member.timeout(None)

            await ctx.send(
                embed=success(
                    "Member Unmuted",
                    f"**{member}** is no longer timed out."
                )
            )

        except discord.Forbidden:
            await ctx.send(
                embed=error(
                    "Permission Error",
                    "I cannot remove that timeout."
                )
            )

    # =========================
    # WARN
    # =========================

    @commands.hybrid_command(
        name="warn",
        description="Warn a member."
    )
    @commands.has_permissions(moderate_members=True)
    async def warn(
        self,
        ctx: commands.Context,
        member: discord.Member,
        *,
        reason: str = "No reason provided."
    ):
        from database.database import db

        if not can_act_on(ctx.author, member):
            return await ctx.send(
                embed=error(
                    "Cannot Warn",
                    "You cannot warn this member."
                )
            )

        await db.execute(
            """
            INSERT INTO warnings
            (guild_id, user_id, moderator_id, reason)
            VALUES (?, ?, ?, ?)
            """,
            (
                ctx.guild.id,
                member.id,
                ctx.author.id,
                reason
            )
        )

        count = await db.fetchone(
            """
            SELECT COUNT(*) AS count
            FROM warnings
            WHERE guild_id = ?
            AND user_id = ?
            """,
            (
                ctx.guild.id,
                member.id
            )
        )

        await ctx.send(
            embed=warning(
                "Member Warned",
                f"**{member}** has been warned.\n"
                f"**Reason:** {reason}\n"
                f"**Total warnings:** {count['count']}"
            )
        )

    # =========================
    # WARNINGS
    # =========================

    @commands.hybrid_command(
        name="warnings",
        description="View a member's warnings."
    )
    @commands.has_permissions(moderate_members=True)
    async def warnings(
        self,
        ctx: commands.Context,
        member: discord.Member
    ):
        from database.database import db

        rows = await db.fetchall(
            """
            SELECT moderator_id, reason, created_at
            FROM warnings
            WHERE guild_id = ?
            AND user_id = ?
            ORDER BY id DESC
            LIMIT 15
            """,
            (
                ctx.guild.id,
                member.id
            )
        )

        if not rows:
            return await ctx.send(
                embed=info(
                    "Warnings",
                    f"**{member}** has no warnings."
                )
            )

        description = []

        for index, row in enumerate(rows, start=1):
            description.append(
                f"**{index}.** {row['reason']}\n"
                f"Moderator: <@{row['moderator_id']}>\n"
                f"`{row['created_at']}`"
            )

        await ctx.send(
            embed=info(
                f"Warnings • {member}",
                "\n\n".join(description)
            )
        )

    # =========================
    # PURGE
    # =========================

    @commands.hybrid_command(
        name="purge",
        aliases=["clear"],
        description="Delete multiple messages."
    )
    @commands.bot_has_permissions(manage_messages=True)
    @commands.has_permissions(manage_messages=True)
    async def purge(
        self,
        ctx: commands.Context,
        amount: int
    ):
        if amount < 1:
            return await ctx.send(
                embed=error(
                    "Invalid Amount",
                    "Amount must be at least 1."
                )
            )

        if amount > 100:
            return await ctx.send(
                embed=error(
                    "Invalid Amount",
                    "You can delete a maximum of 100 messages at once."
                )
            )

        deleted = await ctx.channel.purge(
            limit=amount + 1
        )

        message = await ctx.send(
            embed=success(
                "Messages Cleared",
                f"Deleted **{len(deleted) - 1}** message(s)."
            )
        )

        await message.delete(delay=5)

    # =========================
    # LOCK
    # =========================

    @commands.hybrid_command(
        name="lock",
        description="Lock the current channel."
    )
    @commands.bot_has_permissions(manage_channels=True)
    @commands.has_permissions(manage_channels=True)
    async def lock(self, ctx: commands.Context):
        overwrite = ctx.channel.overwrites_for(
            ctx.guild.default_role
        )

        overwrite.send_messages = False

        await ctx.channel.set_permissions(
            ctx.guild.default_role,
            overwrite=overwrite
        )

        await ctx.send(
            embed=success(
                "Channel Locked",
                "This channel has been locked."
            )
        )

    # =========================
    # UNLOCK
    # =========================

    @commands.hybrid_command(
        name="unlock",
        description="Unlock the current channel."
    )
    @commands.bot_has_permissions(manage_channels=True)
    @commands.has_permissions(manage_channels=True)
    async def unlock(self, ctx: commands.Context):
        overwrite = ctx.channel.overwrites_for(
            ctx.guild.default_role
        )

        overwrite.send_messages = None

        await ctx.channel.set_permissions(
            ctx.guild.default_role,
            overwrite=overwrite
        )

        await ctx.send(
            embed=success(
                "Channel Unlocked",
                "This channel has been unlocked."
            )
        )

    # =========================
    # SLOWMODE
    # =========================

    @commands.hybrid_command(
        name="slowmode",
        description="Set channel slowmode."
    )
    @commands.bot_has_permissions(manage_channels=True)
    @commands.has_permissions(manage_channels=True)
    async def slowmode(
        self,
        ctx: commands.Context,
        seconds: int
    ):
        if seconds < 0 or seconds > 21600:
            return await ctx.send(
                embed=error(
                    "Invalid Duration",
                    "Slowmode must be between 0 and 21600 seconds."
                )
            )

        await ctx.channel.edit(
            slowmode_delay=seconds
        )

        await ctx.send(
            embed=success(
                "Slowmode Updated",
                f"Slowmode set to **{seconds} seconds**."
            )
        )


async def setup(bot):
    await bot.add_cog(Moderation(bot))
