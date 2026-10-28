import asyncio
import discord
from discord.ext import commands

from config import TOKEN, PREFIX, BOT_NAME, VERSION
from database.database import db


intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.presences = True


class Kyoka(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix=PREFIX,
            intents=intents,
            help_command=None
        )

        self.db = db
        self.maintenance_mode = False
        self._kyoka_ready = False

    async def setup_hook(self):
        # Initialize database
        await self.db.initialize()

        # Load all KYŌKA cogs
        cogs = [
            "cogs.core",
            "cogs.moderation",
            "cogs.afk",
            "cogs.economy",
            "cogs.games",
            "cogs.tickets",
            "cogs.welcome",
            "cogs.automod",
            "cogs.leveling",
            "cogs.giveaways",
            "cogs.utility",
            "cogs.custom_commands",
            "cogs.analytics",
            "cogs.automation",
            "cogs.premium",
            "cogs.music",
            "cogs.ai",
            "cogs.owner",
            "cogs.logging",
        ]

        failed = []

        for cog in cogs:
            try:
                await self.load_extension(cog)
                print(f"[KYŌKA] Loaded: {cog}")

            except Exception as e:
                failed.append((cog, e))
                print(
                    f"[KYŌKA] FAILED: {cog} "
                    f"-> {type(e).__name__}: {e}"
                )

        # Sync slash commands
        try:
            synced = await self.tree.sync()

            print(
                f"[KYŌKA] Synced "
                f"{len(synced)} slash commands"
            )

        except Exception as e:
            print(
                f"[KYŌKA] Slash sync failed: "
                f"{type(e).__name__}: {e}"
            )

        loaded = len(cogs) - len(failed)

        print(
            f"[KYŌKA] Extension check: "
            f"{loaded}/{len(cogs)} loaded"
        )

        if failed:
            print("[KYŌKA] Failed extensions:")

            for cog, error in failed:
                print(
                    f"  - {cog}: "
                    f"{type(error).__name__}: {error}"
                )


bot = Kyoka()


@bot.event
async def on_ready():
    bot._kyoka_ready = True

    try:
        await bot.change_presence(
            activity=discord.Game(
                name=f"{PREFIX}help • {BOT_NAME}"
            )
        )
    except Exception as e:
        print(
            f"[KYŌKA] Presence error: "
            f"{type(e).__name__}: {e}"
        )

    print("=" * 50)
    print(f" {BOT_NAME} {VERSION}")
    print(f" Logged in as: {bot.user}")
    print(f" User ID: {bot.user.id}")
    print(f" Servers: {len(bot.guilds)}")
    print(f" Prefix: {PREFIX}")
    print(
        f" Latency: "
        f"{round(bot.latency * 1000)}ms"
    )
    print("=" * 50)


@bot.event
async def on_command_error(ctx, error):

    # Ignore unknown prefix commands
    if isinstance(
        error,
        commands.CommandNotFound
    ):
        return

    # Missing permissions
    if isinstance(
        error,
        commands.MissingPermissions
    ):
        await ctx.send(
            "❌ You don't have permission "
            "to use this command."
        )
        return

    # Bot missing permissions
    if isinstance(
        error,
        commands.BotMissingPermissions
    ):
        await ctx.send(
            "❌ I don't have the required "
            "Discord permissions."
        )
        return

    # Missing argument
    if isinstance(
        error,
        commands.MissingRequiredArgument
    ):
        await ctx.send(
            f"❌ Missing argument: "
            f"`{error.param.name}`"
        )
        return

    # Invalid argument
    if isinstance(
        error,
        commands.BadArgument
    ):
        await ctx.send(
            "❌ Invalid argument."
        )
        return

    # Cooldown
    if isinstance(
        error,
        commands.CommandOnCooldown
    ):
        await ctx.send(
            f"⏳ Try again in "
            f"`{error.retry_after:.1f}s`."
        )
        return

    # Owner-only / custom check failures
    if isinstance(
        error,
        commands.CheckFailure
    ):
        await ctx.send(
            "❌ You don't have permission "
            "to use this command."
        )
        return

    # Command execution error
    if isinstance(
        error,
        commands.CommandInvokeError
    ):
        original = error.original

        print(
            f"[COMMAND ERROR] "
            f"{type(original).__name__}: "
            f"{original}"
        )

    else:
        print(
            f"[COMMAND ERROR] "
            f"{type(error).__name__}: "
            f"{error}"
        )

    try:
        await ctx.send(
            "❌ Something went wrong "
            "while running that command."
        )

    except discord.HTTPException:
        pass


async def main():
    if not TOKEN:
        raise RuntimeError(
            "DISCORD_TOKEN is missing "
            "from your .env file."
        )

    async with bot:
        await bot.start(TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
