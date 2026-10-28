import discord
from discord.ext import commands


class LoggingCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db

    # =========================
    # DATABASE
    # =========================

    async def get_settings(self, guild_id):
        row = await self.db.fetchone(
            """
            SELECT *
            FROM logging_settings
            WHERE guild_id = ?
            """,
            (guild_id,)
        )

        if not row:
            await self.db.execute(
                """
                INSERT OR IGNORE INTO logging_settings
                (
                    guild_id,
                    log_channel_id,
                    message_logs,
                    member_logs,
                    moderation_logs,
                    server_logs
                )
                VALUES (?, NULL, 1, 1, 1, 1)
                """,
                (guild_id,)
            )

            row = await self.db.fetchone(
                """
                SELECT *
                FROM logging_settings
                WHERE guild_id = ?
                """,
                (guild_id,)
            )

        return row

    async def is_enabled(self, guild_id, category):
        settings = await self.get_settings(guild_id)

        if not settings:
            return False

        return bool(settings[category])

    async def send_log(
        self,
        guild,
        title,
        description,
        color=discord.Color.blurple()
    ):
        if not guild:
            return

        settings = await self.get_settings(guild.id)

        if not settings:
            return

        channel_id = settings["log_channel_id"]

        if not channel_id:
            return

        channel = guild.get_channel(channel_id)

        if not channel:
            return

        embed = discord.Embed(
            title=title,
            description=description,
            color=color,
            timestamp=discord.utils.utcnow()
        )

        embed.set_footer(
            text=f"{guild.name} • KYŌKA Logs"
        )

        try:
            await channel.send(embed=embed)
        except (
            discord.Forbidden,
            discord.HTTPException
        ):
            pass

    # =========================
    # SET LOG CHANNEL
    # =========================

    @commands.hybrid_command(
        name="logging",
        description="Set the server logging channel."
    )
    @commands.has_guild_permissions(manage_guild=True)
    async def logging(
        self,
        ctx,
        channel: discord.TextChannel = None
    ):
        if channel is None:
            settings = await self.get_settings(
                ctx.guild.id
            )

            channel_id = settings["log_channel_id"]

            if channel_id:
                current = ctx.guild.get_channel(
                    channel_id
                )

                if current:
                    await ctx.send(
                        f"📋 Logging channel: {current.mention}"
                    )
                    return

            await ctx.send(
                "❌ No logging channel is configured."
            )
            return

        await self.db.execute(
            """
            INSERT OR IGNORE INTO logging_settings
            (
                guild_id,
                log_channel_id,
                message_logs,
                member_logs,
                moderation_logs,
                server_logs
            )
            VALUES (?, ?, 1, 1, 1, 1)
            """,
            (
                ctx.guild.id,
                channel.id
            )
        )

        await self.db.execute(
            """
            UPDATE logging_settings
            SET log_channel_id = ?
            WHERE guild_id = ?
            """,
            (
                channel.id,
                ctx.guild.id
            )
        )

        await ctx.send(
            f"✅ Logging channel set to {channel.mention}."
        )

    # =========================
    # SETTINGS
    # =========================

    @commands.hybrid_command(
        name="logsettings",
        description="View logging settings."
    )
    @commands.has_guild_permissions(manage_guild=True)
    async def logsettings(self, ctx):
        settings = await self.get_settings(
            ctx.guild.id
        )

        channel = None

        if settings["log_channel_id"]:
            channel = ctx.guild.get_channel(
                settings["log_channel_id"]
            )

        embed = discord.Embed(
            title="📋 KYŌKA Logging Settings",
            color=discord.Color.blurple()
        )

        embed.add_field(
            name="Log Channel",
            value=(
                channel.mention
                if channel
                else "Not configured"
            ),
            inline=False
        )

        embed.add_field(
            name="Messages",
            value=(
                "Enabled"
                if settings["message_logs"]
                else "Disabled"
            )
        )

        embed.add_field(
            name="Members",
            value=(
                "Enabled"
                if settings["member_logs"]
                else "Disabled"
            )
        )

        embed.add_field(
            name="Moderation",
            value=(
                "Enabled"
                if settings["moderation_logs"]
                else "Disabled"
            )
        )

        embed.add_field(
            name="Server",
            value=(
                "Enabled"
                if settings["server_logs"]
                else "Disabled"
            )
        )

        await ctx.send(embed=embed)

    # =========================
    # TOGGLE
    # =========================

    @commands.hybrid_command(
        name="logtoggle",
        description="Enable or disable a logging category."
    )
    @commands.has_guild_permissions(manage_guild=True)
    async def logtoggle(
        self,
        ctx,
        category: str,
        state: str
    ):
        categories = {
            "messages": "message_logs",
            "message": "message_logs",
            "members": "member_logs",
            "member": "member_logs",
            "moderation": "moderation_logs",
            "mod": "moderation_logs",
            "server": "server_logs"
        }

        category = category.lower()
        state = state.lower()

        if category not in categories:
            await ctx.send(
                "❌ Categories: "
                "`messages`, `members`, "
                "`moderation`, `server`."
            )
            return

        if state not in ("on", "off"):
            await ctx.send(
                "❌ State must be `on` or `off`."
            )
            return

        column = categories[category]
        value = 1 if state == "on" else 0

        # Make sure settings exist.
        await self.get_settings(ctx.guild.id)

        await self.db.execute(
            f"""
            UPDATE logging_settings
            SET {column} = ?
            WHERE guild_id = ?
            """,
            (
                value,
                ctx.guild.id
            )
        )

        await ctx.send(
            f"✅ **{category}** logging is now "
            f"**{state}**."
        )

    # =========================
    # MESSAGE DELETE
    # =========================

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if not message.guild:
            return

        if message.author.bot:
            return

        if not await self.is_enabled(
            message.guild.id,
            "message_logs"
        ):
            return

        content = (
            message.content
            or "*No text content*"
        )

        if len(content) > 1500:
            content = content[:1500] + "..."

        await self.send_log(
            message.guild,
            "🗑️ Message Deleted",
            (
                f"**Author:** {message.author.mention}\n"
                f"**Channel:** {message.channel.mention}\n\n"
                f"**Content:**\n{content}"
            ),
            discord.Color.red()
        )

    # =========================
    # MESSAGE EDIT
    # =========================

    @commands.Cog.listener()
    async def on_message_edit(
        self,
        before,
        after
    ):
        if not before.guild:
            return

        if before.author.bot:
            return

        if before.content == after.content:
            return

        if not await self.is_enabled(
            before.guild.id,
            "message_logs"
        ):
            return

        old = before.content or "*Empty*"
        new = after.content or "*Empty*"

        if len(old) > 1000:
            old = old[:1000] + "..."

        if len(new) > 1000:
            new = new[:1000] + "..."

        await self.send_log(
            before.guild,
            "✏️ Message Edited",
            (
                f"**Author:** {before.author.mention}\n"
                f"**Channel:** {before.channel.mention}\n\n"
                f"**Before:**\n{old}\n\n"
                f"**After:**\n{new}"
            ),
            discord.Color.orange()
        )

    # =========================
    # MEMBER JOIN
    # =========================

    @commands.Cog.listener()
    async def on_member_join(self, member):
        if not await self.is_enabled(
            member.guild.id,
            "member_logs"
        ):
            return

        await self.send_log(
            member.guild,
            "📥 Member Joined",
            (
                f"**Member:** {member.mention}\n"
                f"**Username:** `{member}`\n"
                f"**ID:** `{member.id}`\n"
                f"**Account Created:** "
                f"<t:{int(member.created_at.timestamp())}:R>"
            ),
            discord.Color.green()
        )

    # =========================
    # MEMBER LEAVE
    # =========================

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        if not await self.is_enabled(
            member.guild.id,
            "member_logs"
        ):
            return

        joined = (
            f"<t:{int(member.joined_at.timestamp())}:R>"
            if member.joined_at
            else "Unknown"
        )

        await self.send_log(
            member.guild,
            "📤 Member Left",
            (
                f"**Member:** `{member}`\n"
                f"**ID:** `{member.id}`\n"
                f"**Joined:** {joined}"
            ),
            discord.Color.red()
        )

    # =========================
    # BAN
    # =========================

    @commands.Cog.listener()
    async def on_member_ban(
        self,
        guild,
        user
    ):
        if not await self.is_enabled(
            guild.id,
            "moderation_logs"
        ):
            return

        await self.send_log(
            guild,
            "🔨 Member Banned",
            (
                f"**User:** `{user}`\n"
                f"**ID:** `{user.id}`"
            ),
            discord.Color.dark_red()
        )

    # =========================
    # UNBAN
    # =========================

    @commands.Cog.listener()
    async def on_member_unban(
        self,
        guild,
        user
    ):
        if not await self.is_enabled(
            guild.id,
            "moderation_logs"
        ):
            return

        await self.send_log(
            guild,
            "🔓 Member Unbanned",
            (
                f"**User:** `{user}`\n"
                f"**ID:** `{user.id}`"
            ),
            discord.Color.green()
        )

    # =========================
    # ROLE CREATE
    # =========================

    @commands.Cog.listener()
    async def on_guild_role_create(self, role):
        if not await self.is_enabled(
            role.guild.id,
            "server_logs"
        ):
            return

        await self.send_log(
            role.guild,
            "🎭 Role Created",
            (
                f"**Role:** {role.mention}\n"
                f"**Name:** `{role.name}`\n"
                f"**ID:** `{role.id}`"
            ),
            discord.Color.green()
        )

    # =========================
    # ROLE DELETE
    # =========================

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role):
        if not await self.is_enabled(
            role.guild.id,
            "server_logs"
        ):
            return

        await self.send_log(
            role.guild,
            "🗑️ Role Deleted",
            (
                f"**Role:** `{role.name}`\n"
                f"**ID:** `{role.id}`"
            ),
            discord.Color.red()
        )

    # =========================
    # CHANNEL CREATE
    # =========================

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        if not await self.is_enabled(
            channel.guild.id,
            "server_logs"
        ):
            return

        mention = (
            channel.mention
            if hasattr(channel, "mention")
            else f"`{channel.name}`"
        )

        await self.send_log(
            channel.guild,
            "📁 Channel Created",
            (
                f"**Channel:** {mention}\n"
                f"**Name:** `{channel.name}`\n"
                f"**ID:** `{channel.id}`"
            ),
            discord.Color.green()
        )

    # =========================
    # CHANNEL DELETE
    # =========================

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        if not await self.is_enabled(
            channel.guild.id,
            "server_logs"
        ):
            return

        await self.send_log(
            channel.guild,
            "🗑️ Channel Deleted",
            (
                f"**Name:** `{channel.name}`\n"
                f"**ID:** `{channel.id}`"
            ),
            discord.Color.red()
        )

    # =========================
    # SERVER UPDATE
    # =========================

    @commands.Cog.listener()
    async def on_guild_update(
        self,
        before,
        after
    ):
        if not await self.is_enabled(
            after.id,
            "server_logs"
        ):
            return

        changes = []

        if before.name != after.name:
            changes.append(
                f"**Name:** `{before.name}` → `{after.name}`"
            )

        if before.afk_channel != after.afk_channel:
            changes.append(
                "**AFK channel changed.**"
            )

        if before.afk_timeout != after.afk_timeout:
            changes.append(
                f"**AFK timeout:** "
                f"`{before.afk_timeout}` → "
                f"`{after.afk_timeout}`"
            )

        if not changes:
            return

        await self.send_log(
            after,
            "⚙️ Server Updated",
            "\n".join(changes),
            discord.Color.orange()
        )

    # =========================
    # MEMBER ROLE UPDATE
    # =========================

    @commands.Cog.listener()
    async def on_member_update(
        self,
        before,
        after
    ):
        if not await self.is_enabled(
            after.guild.id,
            "member_logs"
        ):
            return

        added = [
            role
            for role in after.roles
            if role not in before.roles
        ]

        removed = [
            role
            for role in before.roles
            if role not in after.roles
        ]

        for role in added:
            await self.send_log(
                after.guild,
                "🎭 Role Added",
                (
                    f"**Member:** {after.mention}\n"
                    f"**Role:** {role.mention}"
                ),
                discord.Color.green()
            )

        for role in removed:
            await self.send_log(
                after.guild,
                "🎭 Role Removed",
                (
                    f"**Member:** {after.mention}\n"
                    f"**Role:** {role.name}"
                ),
                discord.Color.orange()
            )


async def setup(bot):
    await bot.add_cog(LoggingCog(bot))
