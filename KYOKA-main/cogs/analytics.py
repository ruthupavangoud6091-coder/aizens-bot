import discord
from discord.ext import commands
from datetime import datetime, timezone

from database.database import db
from utils.checks import guild_only
from utils.embeds import info, error


class Analytics(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # =========================================================
    # ANALYTICS
    # =========================================================

    @commands.hybrid_group(
        name="analytics",
        description="View server analytics."
    )
    @guild_only()
    async def analytics(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send(
                embed=info(
                    "📊 Analytics",
                    "Use `k!analytics overview` to view your server analytics."
                )
            )

    # =========================================================
    # OVERVIEW
    # =========================================================

    @analytics.command(
        name="overview",
        description="View server overview."
    )
    async def overview(self, ctx):
        guild = ctx.guild

        total_members = guild.member_count or 0

        bots = sum(
            1 for member in guild.members
            if member.bot
        )

        humans = total_members - bots

        online = sum(
            1 for member in guild.members
            if member.status != discord.Status.offline
            and not member.bot
        )

        text_channels = len(guild.text_channels)
        voice_channels = len(guild.voice_channels)
        categories = len(guild.categories)
        roles = len(guild.roles)

        created = guild.created_at.strftime("%d %b %Y")

        embed = info(
            f"📊 {guild.name} Analytics",
            (
                f"👥 **Members:** `{total_members:,}`\n"
                f"👤 **Humans:** `{humans:,}`\n"
                f"🤖 **Bots:** `{bots:,}`\n"
                f"🟢 **Online:** `{online:,}`\n\n"
                f"💬 **Text Channels:** `{text_channels}`\n"
                f"🔊 **Voice Channels:** `{voice_channels}`\n"
                f"📁 **Categories:** `{categories}`\n"
                f"🎭 **Roles:** `{roles}`\n\n"
                f"📅 **Created:** `{created}`"
            )
        )

        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)

        await ctx.send(embed=embed)

    # =========================================================
    # MEMBERS
    # =========================================================

    @analytics.command(
        name="members",
        description="View member statistics."
    )
    async def members(self, ctx):
        guild = ctx.guild

        total = guild.member_count or 0

        humans = sum(
            1 for member in guild.members
            if not member.bot
        )

        bots = sum(
            1 for member in guild.members
            if member.bot
        )

        online = sum(
            1 for member in guild.members
            if member.status != discord.Status.offline
        )

        idle = sum(
            1 for member in guild.members
            if member.status == discord.Status.idle
        )

        dnd = sum(
            1 for member in guild.members
            if member.status == discord.Status.dnd
        )

        embed = info(
            "👥 Member Analytics",
            (
                f"**Total:** `{total:,}`\n"
                f"**Humans:** `{humans:,}`\n"
                f"**Bots:** `{bots:,}`\n\n"
                f"🟢 **Online:** `{online:,}`\n"
                f"🟡 **Idle:** `{idle:,}`\n"
                f"🔴 **DND:** `{dnd:,}`"
            )
        )

        await ctx.send(embed=embed)

    # =========================================================
    # CHANNELS
    # =========================================================

    @analytics.command(
        name="channels",
        description="View channel statistics."
    )
    async def channels(self, ctx):
        guild = ctx.guild

        text = len(guild.text_channels)
        voice = len(guild.voice_channels)
        categories = len(guild.categories)
        forums = len(guild.forums)

        await ctx.send(
            embed=info(
                "📺 Channel Analytics",
                (
                    f"💬 **Text:** `{text}`\n"
                    f"🔊 **Voice:** `{voice}`\n"
                    f"🗂️ **Categories:** `{categories}`\n"
                    f"📰 **Forums:** `{forums}`"
                )
            )
        )

    # =========================================================
    # ROLES
    # =========================================================

    @analytics.command(
        name="roles",
        description="View role statistics."
    )
    async def roles(self, ctx):
        guild = ctx.guild

        roles = [
            role for role in guild.roles
            if role != guild.default_role
        ]

        managed = sum(
            1 for role in roles
            if role.managed
        )

        normal = len(roles) - managed

        await ctx.send(
            embed=info(
                "🎭 Role Analytics",
                (
                    f"**Total roles:** `{len(roles):,}`\n"
                    f"**Custom roles:** `{normal:,}`\n"
                    f"**Managed roles:** `{managed:,}`"
                )
            )
        )

    # =========================================================
    # SERVER INFO
    # =========================================================

    @analytics.command(
        name="server",
        description="View detailed server analytics."
    )
    @commands.has_permissions(manage_guild=True)
    async def server(self, ctx):
        guild = ctx.guild

        owner = guild.owner.mention if guild.owner else "Unknown"

        embed = info(
            f"📊 {guild.name}",
            (
                f"**Server ID:** `{guild.id}`\n"
                f"**Owner:** {owner}\n"
                f"**Members:** `{guild.member_count:,}`\n"
                f"**Boost Level:** `{guild.premium_tier}`\n"
                f"**Boosts:** `{guild.premium_subscription_count}`\n"
                f"**Verification:** `{guild.verification_level.name}`\n"
                f"**Created:** `{guild.created_at.strftime('%d %b %Y')}`"
            )
        )

        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)

        await ctx.send(embed=embed)

    # =========================================================
    # GUILD ACTIVITY
    # =========================================================

    @analytics.command(
        name="activity",
        description="View recent bot activity."
    )
    @commands.has_permissions(manage_guild=True)
    async def activity(self, ctx):
        try:
            rows = await db.fetchall(
                """
                SELECT *
                FROM bot_logs
                WHERE guild_id = ?
                ORDER BY created_at DESC
                LIMIT 10
                """,
                (ctx.guild.id,)
            )
        except Exception:
            rows = []

        if not rows:
            await ctx.send(
                embed=info(
                    "📈 Activity",
                    "No tracked activity is available yet."
                )
            )
            return

        lines = []

        for row in rows:
            action = row["action"] if "action" in row.keys() else "Activity"
            lines.append(f"• `{action}`")

        await ctx.send(
            embed=info(
                "📈 Recent Activity",
                "\n".join(lines)
            )
        )

    # =========================================================
    # BOT STATS
    # =========================================================

    @commands.hybrid_command(
        name="statistics",
        description="View KYŌKA statistics."
    )
    @guild_only()
    async def statistics(self, ctx):
        guilds = len(self.bot.guilds)

        members = sum(
            guild.member_count or 0
            for guild in self.bot.guilds
        )

        latency = round(
            self.bot.latency * 1000
        )

        embed = info(
            "📊 KYŌKA Statistics",
            (
                f"🌐 **Servers:** `{guilds:,}`\n"
                f"👥 **Users:** `{members:,}`\n"
                f"📡 **Latency:** `{latency}ms`\n"
                f"🐍 **Python:** `{discord.__version__}`"
            )
        )

        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Analytics(bot))
