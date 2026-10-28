import discord
from discord.ext import commands
from discord import app_commands
import platform
import time

from config import PREFIX, BOT_NAME, VERSION


class Core(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.start_time = time.time()

    # ---------------- READY ----------------

    @commands.Cog.listener()
    async def on_ready(self):
        if getattr(self.bot, "_kyoka_ready", False):
            return

        self.bot._kyoka_ready = True

        print("=" * 50)
        print(f"{BOT_NAME} is online!")
        print(f"Version: {VERSION}")
        print(f"Discord.py: {discord.__version__}")
        print(f"Python: {platform.python_version()}")
        print(f"Servers: {len(self.bot.guilds)}")
        print("=" * 50)

    # ---------------- PING ----------------

    @commands.hybrid_command(
        name="ping",
        description="Check KYŌKA's latency."
    )
    async def ping(self, ctx):
        latency = round(self.bot.latency * 1000)

        embed = discord.Embed(
            title="🏓 KYŌKA Pong!",
            color=discord.Color.green()
        )

        embed.add_field(
            name="Latency",
            value=f"`{latency}ms`",
            inline=True
        )

        embed.add_field(
            name="Status",
            value="🟢 Online",
            inline=True
        )

        await ctx.send(embed=embed)

    # ---------------- BOT INFO ----------------

    @commands.hybrid_command(
        name="botinfo",
        description="View information about KYŌKA."
    )
    async def botinfo(self, ctx):
        uptime = int(time.time() - self.start_time)

        days, remainder = divmod(uptime, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)

        uptime_text = (
            f"{days}d {hours}h {minutes}m {seconds}s"
        )

        users = sum(
            guild.member_count or 0
            for guild in self.bot.guilds
        )

        embed = discord.Embed(
            title=f"✨ {BOT_NAME}",
            description="All-in-one Discord community bot.",
            color=discord.Color.blurple()
        )

        if self.bot.user:
            embed.set_thumbnail(
                url=self.bot.user.display_avatar.url
            )

        embed.add_field(
            name="Version",
            value=f"`{VERSION}`",
            inline=True
        )

        embed.add_field(
            name="Servers",
            value=f"`{len(self.bot.guilds)}`",
            inline=True
        )

        embed.add_field(
            name="Users",
            value=f"`{users:,}`",
            inline=True
        )

        embed.add_field(
            name="Latency",
            value=f"`{round(self.bot.latency * 1000)}ms`",
            inline=True
        )

        embed.add_field(
            name="Uptime",
            value=f"`{uptime_text}`",
            inline=True
        )

        embed.add_field(
            name="Prefix",
            value=f"`{PREFIX}`",
            inline=True
        )

        embed.set_footer(
            text="KYŌKA • Built for Discord communities"
        )

        await ctx.send(embed=embed)

    # ---------------- SERVER COUNT ----------------

    @commands.hybrid_command(
        name="servers",
        description="Show how many servers KYŌKA is in."
    )
    async def servers(self, ctx):
        users = sum(
            guild.member_count or 0
            for guild in self.bot.guilds
        )

        embed = discord.Embed(
            title="🌐 KYŌKA Network",
            color=discord.Color.blurple()
        )

        embed.add_field(
            name="Servers",
            value=f"`{len(self.bot.guilds):,}`",
            inline=True
        )

        embed.add_field(
            name="Users",
            value=f"`{users:,}`",
            inline=True
        )

        await ctx.send(embed=embed)

    # ---------------- UPTIME ----------------

    @commands.hybrid_command(
        name="uptime",
        description="Show how long KYŌKA has been online."
    )
    async def uptime(self, ctx):
        seconds = int(time.time() - self.start_time)

        days, remainder = divmod(seconds, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)

        embed = discord.Embed(
            title="⏱️ KYŌKA Uptime",
            description=(
                f"`{days}d {hours}h "
                f"{minutes}m {seconds}s`"
            ),
            color=discord.Color.green()
        )

        await ctx.send(embed=embed)

    # ---------------- INVITE ----------------

    @commands.hybrid_command(
        name="invite",
        description="Get KYŌKA's invite link."
    )
    async def invite(self, ctx):
        if not self.bot.user:
            await ctx.send("❌ Bot information isn't ready yet.")
            return

        permissions = discord.Permissions.all()

        invite_url = discord.utils.oauth_url(
            self.bot.user.id,
            permissions=permissions,
            scopes=("bot", "applications.commands")
        )

        embed = discord.Embed(
            title="🔗 Invite KYŌKA",
            description=(
                f"[Click here to invite {BOT_NAME}]"
                f"({invite_url})"
            ),
            color=discord.Color.blurple()
        )

        await ctx.send(embed=embed)

    # ---------------- HELP ----------------

    @commands.hybrid_command(
        name="help",
        description="Show KYŌKA's command categories."
    )
    async def help(self, ctx):
        embed = discord.Embed(
            title="📚 KYŌKA Help",
            description=(
                f"Use `{PREFIX}<command>` or `/command`.\n\n"
                "Choose a category below or use the commands directly."
            ),
            color=discord.Color.blurple()
        )

        categories = {
            "🛡️ Moderation": "`ban`, `kick`, `timeout`, `warn`, `purge`",
            "🤖 AutoMod": "`automod`",
            "🎫 Tickets": "`ticketpanel`, `ticketsetup`",
            "💰 Economy": "`balance`, `daily`, `work`, `pay`",
            "🎮 Games": "`flip`, `mine`, `dice`, `rps`, `slots`",
            "📈 Leveling": "`rank`, `level`, `leaderboard`",
            "😴 AFK": "`afk`",
            "🎁 Giveaways": "`giveaway`",
            "⚙️ Utility": "`userinfo`, `serverinfo`, `avatar`",
            "✨ Custom Commands": "`customadd`, `customlist`",
            "🤖 AI": "`ai`, `ask`",
            "🎵 Music": "`play`, `pause`, `skip`, `queue`",
        }

        for name, value in categories.items():
            embed.add_field(
                name=name,
                value=value,
                inline=False
            )

        embed.set_footer(
            text=f"KYŌKA • Prefix: {PREFIX}"
        )

        await ctx.send(embed=embed)

    # ---------------- COMMAND ERROR ----------------

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandNotFound):
            return

        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(
                f"❌ Missing argument: `{error.param.name}`."
            )
            return

        if isinstance(error, commands.MissingPermissions):
            await ctx.send(
                "❌ You don't have permission to use this command."
            )
            return

        if isinstance(error, commands.BotMissingPermissions):
            await ctx.send(
                "❌ I don't have the required permissions "
                "to perform that action."
            )
            return

        if isinstance(error, commands.NoPrivateMessage):
            await ctx.send(
                "❌ This command can only be used inside a server."
            )
            return

        print(
            f"[COMMAND ERROR] "
            f"{getattr(ctx.command, 'qualified_name', 'unknown')}: "
            f"{error}"
        )

    # ---------------- GUILD JOIN ----------------

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        print(
            f"[GUILD JOIN] {guild.name} "
            f"({guild.id})"
        )

        owner = guild.owner

        if owner:
            try:
                await owner.send(
                    f"👋 Thanks for adding **{BOT_NAME}** "
                    f"to **{guild.name}**!\n\n"
                    f"Use `{PREFIX}help` to get started."
                )
            except discord.Forbidden:
                pass

    # ---------------- GUILD REMOVE ----------------

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        print(
            f"[GUILD LEFT] {guild.name} "
            f"({guild.id})"
        )


async def setup(bot):
    await bot.add_cog(Core(bot))
