import discord
from discord.ext import commands
from datetime import datetime, timezone

from database.database import db
from utils.embeds import success, info


class AFK(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # =========================================================
    # AFK COMMAND
    # =========================================================

    @commands.hybrid_command(
        name="afk",
        description="Set or remove your AFK status."
    )
    async def afk(
        self,
        ctx: commands.Context,
        *,
        reason: str = "AFK"
    ):
        await db.ensure_user(ctx.author.id)

        user = await db.get_user(ctx.author.id)

        # -----------------------------------------------------
        # If already AFK, remove AFK
        # -----------------------------------------------------

        if user["afk"]:
            await db.execute(
                """
                UPDATE users
                SET afk = 0,
                    afk_reason = NULL,
                    afk_since = NULL
                WHERE user_id = ?
                """,
                (ctx.author.id,)
            )

            await ctx.send(
                embed=success(
                    "Welcome Back",
                    f"Welcome back, {ctx.author.mention}! "
                    "Your AFK status has been removed."
                )
            )

            return

        # -----------------------------------------------------
        # Set AFK
        # -----------------------------------------------------

        now = datetime.now(
            timezone.utc
        ).isoformat()

        await db.execute(
            """
            UPDATE users
            SET afk = 1,
                afk_reason = ?,
                afk_since = ?
            WHERE user_id = ?
            """,
            (
                reason[:500],
                now,
                ctx.author.id
            )
        )

        await ctx.send(
            embed=success(
                "AFK Enabled",
                f"{ctx.author.mention} is now AFK.\n"
                f"**Reason:** {reason[:500]}"
            )
        )

    # =========================================================
    # MESSAGE LISTENER
    # =========================================================

    @commands.Cog.listener()
    async def on_message(
        self,
        message: discord.Message
    ):
        if message.author.bot:
            return

        if message.guild is None:
            return

        # -----------------------------------------------------
        # Check if the author is currently AFK
        # -----------------------------------------------------

        author = await db.get_user(
            message.author.id
        )

        if author and author["afk"]:

            await db.execute(
                """
                UPDATE users
                SET afk = 0,
                    afk_reason = NULL,
                    afk_since = NULL
                WHERE user_id = ?
                """,
                (message.author.id,)
            )

            await message.channel.send(
                embed=success(
                    "Welcome Back",
                    f"Welcome back, {message.author.mention}! "
                    "Your AFK status has been removed."
                ),
                delete_after=8
            )

        # -----------------------------------------------------
        # Check mentioned users
        # -----------------------------------------------------

        if not message.mentions:
            return

        already_replied = set()

        for member in message.mentions:

            if member.id in already_replied:
                continue

            already_replied.add(
                member.id
            )

            user = await db.get_user(
                member.id
            )

            if not user:
                continue

            if not user["afk"]:
                continue

            reason = (
                user["afk_reason"]
                or "AFK"
            )

            duration_text = ""

            # -------------------------------------------------
            # Calculate AFK duration
            # -------------------------------------------------

            if user["afk_since"]:

                try:
                    started = datetime.fromisoformat(
                        user["afk_since"]
                    )

                    if started.tzinfo is None:
                        started = started.replace(
                            tzinfo=timezone.utc
                        )

                    elapsed = (
                        datetime.now(timezone.utc)
                        - started
                    )

                    total_seconds = int(
                        elapsed.total_seconds()
                    )

                    days, remainder = divmod(
                        total_seconds,
                        86400
                    )

                    hours, remainder = divmod(
                        remainder,
                        3600
                    )

                    minutes, _ = divmod(
                        remainder,
                        60
                    )

                    parts = []

                    if days:
                        parts.append(
                            f"{days}d"
                        )

                    if hours:
                        parts.append(
                            f"{hours}h"
                        )

                    if minutes:
                        parts.append(
                            f"{minutes}m"
                        )

                    if not parts:
                        parts.append(
                            "<1m"
                        )

                    duration_text = (
                        "\n**AFK for:** "
                        + " ".join(parts)
                    )

                except (
                    ValueError,
                    TypeError
                ):
                    duration_text = ""

            # -------------------------------------------------
            # Send AFK response
            # -------------------------------------------------

            await message.channel.send(
                embed=info(
                    f"{member.display_name} is AFK",
                    f"**Reason:** {reason}"
                    f"{duration_text}"
                ),
                delete_after=10
            )


async def setup(bot):
    await bot.add_cog(
        AFK(bot)
            )
