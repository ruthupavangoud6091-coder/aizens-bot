import io
from datetime import datetime, timezone

import discord
from discord.ext import commands

from database.database import db
from utils.banners import create_welcome_banner
from utils.checks import guild_only
from utils.embeds import success, error, info


class Welcome(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # =========================================================
    # DATABASE
    # =========================================================

    async def get_settings(self, guild_id: int):
        row = await db.fetchone(
            """
            SELECT *
            FROM welcome_settings
            WHERE guild_id = ?
            """,
            (guild_id,)
        )

        if row:
            return row

        await db.execute(
            """
            INSERT OR IGNORE INTO welcome_settings
            (
                guild_id,
                enabled,
                channel_id,
                message,
                goodbye_enabled,
                goodbye_channel_id,
                goodbye_message,
                auto_role_id,
                background_url
            )
            VALUES (?, 0, NULL, ?, 0, NULL, ?, NULL, NULL)
            """,
            (
                guild_id,
                "Welcome to {server}, {user}! 🎉",
                "Goodbye {user}! 👋"
            ),
            commit=True
        )

        return await db.fetchone(
            """
            SELECT *
            FROM welcome_settings
            WHERE guild_id = ?
            """,
            (guild_id,)
        )

    # =========================================================
    # VARIABLE REPLACEMENT
    # =========================================================

    def replace_variables(
        self,
        text: str,
        member: discord.Member
    ):
        if not text:
            return ""

        guild = member.guild

        replacements = {
            "{user}": member.mention,
            "{username}": member.name,
            "{displayname}": member.display_name,
            "{server}": guild.name,
            "{membercount}": str(
                guild.member_count or 0
            ),
            "{channel}": (
                member.guild.system_channel.mention
                if member.guild.system_channel
                else ""
            )
        }

        for key, value in replacements.items():
            text = text.replace(
                key,
                value
            )

        return text

    # =========================================================
    # WELCOME BANNER
    # =========================================================

    async def create_banner(
        self,
        member: discord.Member,
        background_url=None
    ):
        try:
            image = await create_welcome_banner(
                member,
                background_url=background_url
            )

            if image is None:
                return None

            if isinstance(image, bytes):
                return discord.File(
                    io.BytesIO(image),
                    filename="welcome.png"
                )

            if hasattr(image, "save"):
                buffer = io.BytesIO()
                image.save(
                    buffer,
                    format="PNG"
                )
                buffer.seek(0)

                return discord.File(
                    buffer,
                    filename="welcome.png"
                )

        except Exception as exc:
            print(
                f"[KYŌKA] Welcome banner error: "
                f"{type(exc).__name__}: {exc}"
            )

        return None

    # =========================================================
    # WELCOME
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

        # -----------------------------------------------------
        # AUTO ROLE
        # -----------------------------------------------------

        auto_role_id = settings["auto_role_id"]

        if auto_role_id:
            role = member.guild.get_role(
                int(auto_role_id)
            )

            if role:
                try:
                    await member.add_roles(
                        role,
                        reason="KYŌKA automatic welcome role"
                    )
                except discord.HTTPException:
                    pass

        # -----------------------------------------------------
        # WELCOME ENABLED?
        # -----------------------------------------------------

        if not settings["enabled"]:
            return

        channel_id = settings["channel_id"]

        if not channel_id:
            return

        channel = member.guild.get_channel(
            int(channel_id)
        )

        if not channel:
            return

        message = self.replace_variables(
            settings["message"],
            member
        )

        banner_file = await self.create_banner(
            member,
            settings["background_url"]
        )

        embed = discord.Embed(
            title=f"Welcome to {member.guild.name}! 🎉",
            description=message,
            color=discord.Color.blurple(),
            timestamp=datetime.now(timezone.utc)
        )

        embed.set_thumbnail(
            url=member.display_avatar.url
        )

        embed.set_footer(
            text=f"Member #{member.guild.member_count}"
        )

        try:
            if banner_file:
                await channel.send(
                    embed=embed,
                    file=banner_file,
                    allowed_mentions=discord.AllowedMentions(
                        users=True,
                        roles=False,
                        everyone=False
                    )
                )
            else:
                await channel.send(
                    embed=embed,
                    allowed_mentions=discord.AllowedMentions(
                        users=True,
                        roles=False,
                        everyone=False
                    )
                )

        except discord.HTTPException as exc:
            print(
                f"[KYŌKA] Welcome message failed: "
                f"{type(exc).__name__}: {exc}"
            )

    # =========================================================
    # GOODBYE
    # =========================================================

    @commands.Cog.listener()
    async def on_member_remove(
        self,
        member: discord.Member
    ):
        settings = await self.get_settings(
            member.guild.id
        )

        if not settings["goodbye_enabled"]:
            return

        channel_id = settings["goodbye_channel_id"]

        if not channel_id:
            return

        channel = member.guild.get_channel(
            int(channel_id)
        )

        if not channel:
            return

        message = self.replace_variables(
            settings["goodbye_message"],
            member
        )

        embed = discord.Embed(
            title=f"Goodbye {member.display_name} 👋",
            description=message,
            color=discord.Color.dark_gray(),
            timestamp=datetime.now(timezone.utc)
        )

        embed.set_thumbnail(
            url=member.display_avatar.url
        )

        embed.set_footer(
            text=f"{member.guild.name} • Member left"
        )

        try:
            await channel.send(
                embed=embed,
                allowed_mentions=discord.AllowedMentions(
                    users=False,
                    roles=False,
                    everyone=False
                )
            )
        except discord.HTTPException:
            pass

    # =========================================================
    # WELCOME GROUP
    # =========================================================

    @commands.hybrid_group(
        name="welcome",
        description="Configure the welcome system."
    )
    @commands.has_permissions(manage_guild=True)
    @guild_only()
    async def welcome(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send(
                embed=info(
                    "👋 Welcome System",
                    (
                        "`k!welcome enable`\n"
                        "`k!welcome disable`\n"
                        "`k!welcome channel #channel`\n"
                        "`k!welcome message <text>`\n"
                        "`k!welcome background <url>`\n"
                        "`k!welcome goodbye enable`\n"
                        "`k!welcome goodbye disable`\n"
                        "`k!welcome goodbyechannel #channel`\n"
                        "`k!welcome goodbyemessage <text>`\n"
                        "`k!welcome autorole @role`\n"
                        "`k!welcome preview`\n"
                        "`k!welcome status`"
                    )
                )
            )

    # =========================================================
    # ENABLE
    # =========================================================

    @welcome.command(
        name="enable",
        description="Enable welcome messages."
    )
    async def welcome_enable(self, ctx):
        await self.get_settings(
            ctx.guild.id
        )

        await db.execute(
            """
            UPDATE welcome_settings
            SET enabled = 1
            WHERE guild_id = ?
            """,
            (ctx.guild.id,),
            commit=True
        )

        await ctx.send(
            embed=success(
                "👋 Welcome messages are now **enabled**."
            )
        )

    # =========================================================
    # DISABLE
    # =========================================================

    @welcome.command(
        name="disable",
        description="Disable welcome messages."
    )
    async def welcome_disable(self, ctx):
        await self.get_settings(
            ctx.guild.id
        )

        await db.execute(
            """
            UPDATE welcome_settings
            SET enabled = 0
            WHERE guild_id = ?
            """,
            (ctx.guild.id,),
            commit=True
        )

        await ctx.send(
            embed=success(
                "👋 Welcome messages are now **disabled**."
            )
        )

    # =========================================================
    # CHANNEL
    # =========================================================

    @welcome.command(
        name="channel",
        description="Set the welcome channel."
    )
    async def welcome_channel(
        self,
        ctx,
        channel: discord.TextChannel
    ):
        await self.get_settings(
            ctx.guild.id
        )

        await db.execute(
            """
            UPDATE welcome_settings
            SET channel_id = ?
            WHERE guild_id = ?
            """,
            (
                channel.id,
                ctx.guild.id
            ),
            commit=True
        )

        await ctx.send(
            embed=success(
                f"👋 Welcome channel set to {channel.mention}."
            )
        )

    # =========================================================
    # MESSAGE
    # =========================================================

    @welcome.command(
        name="message",
        description="Set the welcome message."
    )
    async def welcome_message(
        self,
        ctx,
        *,
        message: str
    ):
        if len(message) > 1000:
            await ctx.send(
                embed=error(
                    "Welcome message must be 1000 characters or less."
                )
            )
            return

        await self.get_settings(
            ctx.guild.id
        )

        await db.execute(
            """
            UPDATE welcome_settings
            SET message = ?
            WHERE guild_id = ?
            """,
            (
                message,
                ctx.guild.id
            ),
            commit=True
        )

        await ctx.send(
            embed=success(
                "✏️ Welcome message updated."
            )
        )

    # =========================================================
    # BACKGROUND
    # =========================================================

    @welcome.command(
        name="background",
        description="Set the welcome banner background."
    )
    async def welcome_background(
        self,
        ctx,
        url: str
    ):
        if not (
            url.startswith("http://")
            or url.startswith("https://")
        ):
            await ctx.send(
                embed=error(
                    "Please provide a valid image URL."
                )
            )
            return

        await self.get_settings(
            ctx.guild.id
        )

        await db.execute(
            """
            UPDATE welcome_settings
            SET background_url = ?
            WHERE guild_id = ?
            """,
            (
                url,
                ctx.guild.id
            ),
            commit=True
        )

        await ctx.send(
            embed=success(
                "🖼️ Welcome background updated."
            )
        )

    # =========================================================
    # GOODBYE GROUP
    # =========================================================

    @welcome.group(
        name="goodbye",
        description="Configure goodbye messages."
    )
    async def goodbye(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send(
                embed=info(
                    "👋 Goodbye",
                    (
                        "`k!welcome goodbye enable`\n"
                        "`k!welcome goodbye disable`\n"
                        "`k!welcome goodbye message <text>`"
                    )
                )
            )

    @goodbye.command(
        name="enable",
        description="Enable goodbye messages."
    )
    async def goodbye_enable(self, ctx):
        await self.get_settings(
            ctx.guild.id
        )

        await db.execute(
            """
            UPDATE welcome_settings
            SET goodbye_enabled = 1
            WHERE guild_id = ?
            """,
            (ctx.guild.id,),
            commit=True
        )

        await ctx.send(
            embed=success(
                "👋 Goodbye messages are now **enabled**."
            )
        )

    @goodbye.command(
        name="disable",
        description="Disable goodbye messages."
    )
    async def goodbye_disable(self, ctx):
        await self.get_settings(
            ctx.guild.id
        )

        await db.execute(
            """
            UPDATE welcome_settings
            SET goodbye_enabled = 0
            WHERE guild_id = ?
            """,
            (ctx.guild.id,),
            commit=True
        )

        await ctx.send(
            embed=success(
                "👋 Goodbye messages are now **disabled**."
            )
        )

    @goodbye.command(
        name="message",
        description="Set the goodbye message."
    )
    async def goodbye_message(
        self,
        ctx,
        *,
        message: str
    ):
        if len(message) > 1000:
            await ctx.send(
                embed=error(
                    "Goodbye message must be 1000 characters or less."
                )
            )
            return

        await self.get_settings(
            ctx.guild.id
        )

        await db.execute(
            """
            UPDATE welcome_settings
            SET goodbye_message = ?
            WHERE guild_id = ?
            """,
            (
                message,
                ctx.guild.id
            ),
            commit=True
        )

        await ctx.send(
            embed=success(
                "✏️ Goodbye message updated."
            )
        )

    # =========================================================
    # GOODBYE CHANNEL
    # =========================================================

    @welcome.command(
        name="goodbyechannel",
        description="Set the goodbye channel."
    )
    async def goodbye_channel(
        self,
        ctx,
        channel: discord.TextChannel
    ):
        await self.get_settings(
            ctx.guild.id
        )

        await db.execute(
            """
            UPDATE welcome_settings
            SET goodbye_channel_id = ?
            WHERE guild_id = ?
            """,
            (
                channel.id,
                ctx.guild.id
            ),
            commit=True
        )

        await ctx.send(
            embed=success(
                f"👋 Goodbye channel set to {channel.mention}."
            )
        )

    # =========================================================
    # AUTO ROLE
    # =========================================================

    @welcome.command(
        name="autorole",
        description="Set the automatic member role."
    )
    async def welcome_autorole(
        self,
        ctx,
        role: discord.Role
    ):
        if role >= ctx.guild.me.top_role:
            await ctx.send(
                embed=error(
                    "I cannot assign a role that is equal to "
                    "or higher than my highest role."
                )
            )
            return

        await self.get_settings(
            ctx.guild.id
        )

        await db.execute(
            """
            UPDATE welcome_settings
            SET auto_role_id = ?
            WHERE guild_id = ?
            """,
            (
                role.id,
                ctx.guild.id
            ),
            commit=True
        )

        await ctx.send(
            embed=success(
                f"🤖 Auto-role set to {role.mention}."
            )
        )

    # =========================================================
    # PREVIEW
    # =========================================================

    @welcome.command(
        name="preview",
        description="Preview your welcome message."
    )
    async def welcome_preview(self, ctx):
        settings = await self.get_settings(
            ctx.guild.id
        )

        message = self.replace_variables(
            settings["message"],
            ctx.author
        )

        banner_file = await self.create_banner(
            ctx.author,
            settings["background_url"]
        )

        embed = discord.Embed(
            title=f"Welcome to {ctx.guild.name}! 🎉",
            description=message,
            color=discord.Color.blurple(),
            timestamp=datetime.now(timezone.utc)
        )

        embed.set_thumbnail(
            url=ctx.author.display_avatar.url
        )

        embed.set_footer(
            text=f"Member #{ctx.guild.member_count}"
        )

        if banner_file:
            await ctx.send(
                embed=embed,
                file=banner_file
            )
        else:
            await ctx.send(
                embed=embed
            )

    # =========================================================
    # STATUS
    # =========================================================

    @welcome.command(
        name="status",
        description="Show welcome configuration."
    )
    async def welcome_status(self, ctx):
        settings = await self.get_settings(
            ctx.guild.id
        )

        welcome_channel = (
            f"<#{settings['channel_id']}>"
            if settings["channel_id"]
            else "Not set"
        )

        goodbye_channel = (
            f"<#{settings['goodbye_channel_id']}>"
            if settings["goodbye_channel_id"]
            else "Not set"
        )

        auto_role = (
            f"<@&{settings['auto_role_id']}>"
            if settings["auto_role_id"]
            else "Not set"
        )

        embed = discord.Embed(
            title="👋 Welcome Configuration",
            color=discord.Color.blurple()
        )

        embed.add_field(
            name="Welcome",
            value=(
                f"Enabled: "
                f"`{'Yes' if settings['enabled'] else 'No'}`\n"
                f"Channel: {welcome_channel}"
            ),
            inline=False
        )

        embed.add_field(
            name="Goodbye",
            value=(
                f"Enabled: "
                f"`{'Yes' if settings['goodbye_enabled'] else 'No'}`\n"
                f"Channel: {goodbye_channel}"
            ),
            inline=False
        )

        embed.add_field(
            name="Auto Role",
            value=auto_role,
            inline=False
        )

        embed.add_field(
            name="Background",
            value=(
                "Configured"
                if settings["background_url"]
                else "Default"
            ),
            inline=False
        )

        await ctx.send(
            embed=embed
        )


async def setup(bot):
    await bot.add_cog(
        Welcome(bot)
    )
