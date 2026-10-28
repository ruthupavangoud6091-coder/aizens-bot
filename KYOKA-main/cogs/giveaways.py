import random
import re
from datetime import datetime, timezone

import discord
from discord.ext import commands, tasks

from database.database import db
from utils.checks import guild_only
from utils.embeds import success, error, info


# =========================================================
# GIVEAWAY VIEW
# =========================================================

class GiveawayView(discord.ui.View):
    def __init__(self, cog, message_id: int):
        super().__init__(timeout=None)
        self.cog = cog
        self.message_id = message_id

    @discord.ui.button(
        label="🎉 Enter",
        style=discord.ButtonStyle.success,
        custom_id="kyoka_giveaway_enter",
    )
    async def enter(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        await self.cog.enter_giveaway(
            interaction,
            self.message_id,
        )

    @discord.ui.button(
        label="🚪 Leave",
        style=discord.ButtonStyle.danger,
        custom_id="kyoka_giveaway_leave",
    )
    async def leave(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        await self.cog.leave_giveaway(
            interaction,
            self.message_id,
        )


# =========================================================
# GIVEAWAYS
# =========================================================

class Giveaways(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.giveaway_loop.start()

    def cog_unload(self):
        self.giveaway_loop.cancel()

    # =====================================================
    # DATABASE
    # =====================================================

    async def get_giveaway(self, message_id: int):
        return await db.fetchone(
            """
            SELECT *
            FROM giveaways
            WHERE message_id = ?
            """,
            (message_id,),
        )

    async def get_entries(self, message_id: int):
        rows = await db.fetchall(
            """
            SELECT user_id
            FROM giveaway_entries
            WHERE message_id = ?
            """,
            (message_id,),
        )

        return [int(row["user_id"]) for row in rows]

    # =====================================================
    # DURATION
    # =====================================================

    def parse_duration(self, duration: str):

        pattern = re.fullmatch(
            r"(\d+)\s*(s|m|h|d|w)",
            duration.lower().strip(),
        )

        if not pattern:
            return None

        amount = int(pattern.group(1))
        unit = pattern.group(2)

        multipliers = {
            "s": 1,
            "m": 60,
            "h": 3600,
            "d": 86400,
            "w": 604800,
        }

        seconds = amount * multipliers[unit]

        if seconds < 10:
            return None

        if seconds > 60 * 60 * 24 * 30:
            return None

        return seconds

    # =====================================================
    # EMBED
    # =====================================================

    def giveaway_embed(self, giveaway, entries: int = 0):

        end_time = int(float(giveaway["end_time"]))

        embed = discord.Embed(
            title="🎉 GIVEAWAY",
            description=(
                f"## 🎁 {giveaway['prize']}\n\n"
                f"{giveaway['description'] or ''}\n\n"
                f"👑 **Host:** <@{giveaway['host_id']}>\n"
                f"🏆 **Winners:** `{giveaway['winners']}`\n"
                f"👥 **Entries:** `{entries}`\n"
                f"⏰ **Ends:** <t:{end_time}:R>\n\n"
                "Click **🎉 Enter** to participate!"
            ),
            color=discord.Color.blurple(),
            timestamp=datetime.now(timezone.utc),
        )

        if giveaway["image_url"]:
            embed.set_image(url=giveaway["image_url"])

        embed.set_footer(
            text=f"KYŌKA • Giveaway #{giveaway['message_id']}"
        )

        return embed

    # =====================================================
    # GIVEAWAY GROUP
    # =====================================================

    @commands.hybrid_group(
        name="giveaway",
        description="Manage giveaways.",
    )
    @commands.has_permissions(manage_guild=True)
    @guild_only()
    async def giveaway(self, ctx):

        if ctx.invoked_subcommand is None:
            await ctx.send(
                embed=info(
                    "🎉 Giveaway",
                    (
                        "`k!giveaway start`\n"
                        "`k!giveaway end`\n"
                        "`k!giveaway reroll`\n"
                        "`k!giveaway cancel`\n"
                        "`k!giveaway list`"
                    ),
                )
            )

    # =====================================================
    # START
    # =====================================================

    @giveaway.command(
        name="start",
        description="Start a giveaway.",
    )
    async def giveaway_start(
        self,
        ctx,
        duration: str,
        winners: int,
        *,
        prize: str,
    ):

        seconds = self.parse_duration(duration)

        if seconds is None:
            await ctx.send(
                embed=error(
                    "Invalid duration.\n\n"
                    "Examples: `10m`, `2h`, `1d`, `1w`\n"
                    "Maximum: `30d`"
                )
            )
            return

        if winners < 1 or winners > 100:
            await ctx.send(
                embed=error(
                    "Winners must be between **1 and 100**."
                )
            )
            return

        if len(prize) > 256:
            await ctx.send(
                embed=error(
                    "Prize name must be 256 characters or less."
                )
            )
            return

        end_time = (
            datetime.now(timezone.utc).timestamp()
            + seconds
        )

        # message_id is the PRIMARY KEY in the actual database.
        # We temporarily use a unique negative ID until Discord
        # creates the giveaway message.
        temp_id = -int(
            datetime.now(timezone.utc).timestamp() * 1000000
        )

        await db.execute(
            """
            INSERT INTO giveaways
            (
                message_id,
                guild_id,
                channel_id,
                host_id,
                prize,
                winners,
                end_time,
                ended,
                created_at,
                description,
                image_url
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?)
            """,
            (
                temp_id,
                ctx.guild.id,
                ctx.channel.id,
                ctx.author.id,
                prize,
                winners,
                end_time,
                datetime.now(timezone.utc).isoformat(),
                "",
                "",
            ),
        )

        giveaway = await self.get_giveaway(temp_id)

        if not giveaway:
            await ctx.send(
                embed=error(
                    "Failed to create the giveaway."
                )
            )
            return

        view = GiveawayView(
            self,
            temp_id,
        )

        message = await ctx.send(
            embed=self.giveaway_embed(
                giveaway,
                0,
            ),
            view=view,
        )

        # Replace temporary ID with the actual Discord message ID.
        await db.execute(
            """
            UPDATE giveaways
            SET message_id = ?
            WHERE message_id = ?
            """,
            (
                message.id,
                temp_id,
            ),
        )

        # Update the persistent view to use the real message ID.
        view.message_id = message.id

        giveaway = await self.get_giveaway(message.id)

        await message.edit(
            embed=self.giveaway_embed(
                giveaway,
                0,
            ),
            view=view,
        )

    # =====================================================
    # ENTER
    # =====================================================

    async def enter_giveaway(
        self,
        interaction: discord.Interaction,
        message_id: int,
    ):

        giveaway = await self.get_giveaway(message_id)

        if not giveaway:
            await interaction.response.send_message(
                "❌ Giveaway not found.",
                ephemeral=True,
            )
            return

        if giveaway["ended"]:
            await interaction.response.send_message(
                "❌ This giveaway has already ended.",
                ephemeral=True,
            )
            return

        now = datetime.now(timezone.utc).timestamp()

        if now >= float(giveaway["end_time"]):
            await interaction.response.send_message(
                "❌ This giveaway has ended.",
                ephemeral=True,
            )
            return

        existing = await db.fetchone(
            """
            SELECT *
            FROM giveaway_entries
            WHERE message_id = ?
            AND user_id = ?
            """,
            (
                message_id,
                interaction.user.id,
            ),
        )

        if existing:
            await interaction.response.send_message(
                "⚠️ You are already entered!",
                ephemeral=True,
            )
            return

        await db.execute(
            """
            INSERT INTO giveaway_entries
            (
                message_id,
                user_id
            )
            VALUES (?, ?)
            """,
            (
                message_id,
                interaction.user.id,
            ),
        )

        entries = await self.get_entries(message_id)

        await interaction.response.send_message(
            "🎉 You entered the giveaway!",
            ephemeral=True,
        )

        await self.update_giveaway_message(
            message_id,
            len(entries),
        )

    # =====================================================
    # LEAVE
    # =====================================================

    async def leave_giveaway(
        self,
        interaction: discord.Interaction,
        message_id: int,
    ):

        giveaway = await self.get_giveaway(message_id)

        if not giveaway:
            await interaction.response.send_message(
                "❌ Giveaway not found.",
                ephemeral=True,
            )
            return

        deleted = await db.execute(
            """
            DELETE FROM giveaway_entries
            WHERE message_id = ?
            AND user_id = ?
            """,
            (
                message_id,
                interaction.user.id,
            ),
        )

        if deleted.rowcount == 0:
            await interaction.response.send_message(
                "⚠️ You are not entered in this giveaway.",
                ephemeral=True,
            )
            return

        entries = await self.get_entries(message_id)

        await interaction.response.send_message(
            "🚪 You left the giveaway.",
            ephemeral=True,
        )

        await self.update_giveaway_message(
            message_id,
            len(entries),
        )

    # =====================================================
    # UPDATE MESSAGE
    # =====================================================

    async def update_giveaway_message(
        self,
        message_id: int,
        entries: int,
    ):

        giveaway = await self.get_giveaway(message_id)

        if not giveaway:
            return

        guild = self.bot.get_guild(
            int(giveaway["guild_id"])
        )

        if not guild:
            return

        channel = guild.get_channel(
            int(giveaway["channel_id"])
        )

        if not channel:
            return

        try:
            message = await channel.fetch_message(
                int(giveaway["message_id"])
            )

            if giveaway["ended"]:
                await message.edit(
                    embed=self.giveaway_embed(
                        giveaway,
                        entries,
                    ),
                    view=None,
                )
            else:
                await message.edit(
                    embed=self.giveaway_embed(
                        giveaway,
                        entries,
                    )
                )

        except discord.HTTPException:
            pass

    # =====================================================
    # END
    # =====================================================

    @giveaway.command(
        name="end",
        description="End a giveaway immediately.",
    )
    async def giveaway_end(
        self,
        ctx,
        message_id: int,
    ):

        giveaway = await self.get_giveaway(message_id)

        if not giveaway:
            await ctx.send(
                embed=error(
                    "Giveaway not found."
                )
            )
            return

        if giveaway["guild_id"] != ctx.guild.id:
            await ctx.send(
                embed=error(
                    "That giveaway belongs to another server."
                )
            )
            return

        if giveaway["ended"]:
            await ctx.send(
                embed=error(
                    "This giveaway has already ended."
                )
            )
            return

        await self.finish_giveaway(message_id)

        await ctx.send(
            embed=success(
                f"🏁 Giveaway **#{message_id}** ended."
            )
        )

    # =====================================================
    # CANCEL
    # =====================================================

    @giveaway.command(
        name="cancel",
        description="Cancel a giveaway.",
    )
    async def giveaway_cancel(
        self,
        ctx,
        message_id: int,
    ):

        giveaway = await self.get_giveaway(message_id)

        if not giveaway:
            await ctx.send(
                embed=error(
                    "Giveaway not found."
                )
            )
            return

        if giveaway["guild_id"] != ctx.guild.id:
            await ctx.send(
                embed=error(
                    "That giveaway belongs to another server."
                )
            )
            return

        await db.execute(
            """
            UPDATE giveaways
            SET ended = 1
            WHERE message_id = ?
            """,
            (message_id,),
        )

        await db.execute(
            """
            DELETE FROM giveaway_entries
            WHERE message_id = ?
            """,
            (message_id,),
        )

        await self.update_giveaway_message(
            message_id,
            0,
        )

        await ctx.send(
            embed=success(
                f"🛑 Giveaway **#{message_id}** cancelled."
            )
        )

    # =====================================================
    # REROLL
    # =====================================================

    @giveaway.command(
        name="reroll",
        description="Reroll giveaway winners.",
    )
    async def giveaway_reroll(
        self,
        ctx,
        message_id: int,
    ):

        giveaway = await self.get_giveaway(message_id)

        if not giveaway:
            await ctx.send(
                embed=error(
                    "Giveaway not found."
                )
            )
            return

        if not giveaway["ended"]:
            await ctx.send(
                embed=error(
                    "The giveaway has not ended yet."
                )
            )
            return

        entries = await self.get_entries(message_id)

        if not entries:
            await ctx.send(
                embed=error(
                    "There are no eligible entries."
                )
            )
            return

        winners_count = min(
            int(giveaway["winners"]),
            len(entries),
        )

        winners = random.sample(
            entries,
            winners_count,
        )

        mentions = " ".join(
            f"<@{user_id}>"
            for user_id in winners
        )

        await ctx.send(
            embed=success(
                f"🎉 **Rerolled winners!**\n\n"
                f"🎁 Prize: **{giveaway['prize']}**\n"
                f"🏆 Winners: {mentions}"
            )
        )

    # =====================================================
    # LIST
    # =====================================================

    @giveaway.command(
        name="list",
        description="List giveaways in this server.",
    )
    async def giveaway_list(self, ctx):

        rows = await db.fetchall(
            """
            SELECT *
            FROM giveaways
            WHERE guild_id = ?
            ORDER BY message_id DESC
            LIMIT 20
            """,
            (ctx.guild.id,),
        )

        if not rows:
            await ctx.send(
                embed=info(
                    "🎉 Giveaways",
                    "No giveaways found.",
                )
            )
            return

        lines = []

        for row in rows:

            status = (
                "🟢 Active"
                if not row["ended"]
                else "🔴 Ended"
            )

            lines.append(
                f"`#{row['message_id']}` • "
                f"**{row['prize']}** • "
                f"{status}"
            )

        await ctx.send(
            embed=info(
                "🎉 Server Giveaways",
                "\n".join(lines),
            )
        )

    # =====================================================
    # FINISH
    # =====================================================

    async def finish_giveaway(
        self,
        message_id: int,
    ):

        giveaway = await self.get_giveaway(message_id)

        if not giveaway:
            return

        if giveaway["ended"]:
            return

        entries = await self.get_entries(message_id)

        await db.execute(
            """
            UPDATE giveaways
            SET ended = 1
            WHERE message_id = ?
            """,
            (message_id,),
        )

        guild = self.bot.get_guild(
            int(giveaway["guild_id"])
        )

        if not guild:
            return

        channel = guild.get_channel(
            int(giveaway["channel_id"])
        )

        if not channel:
            return

        if not entries:

            await self.update_giveaway_message(
                message_id,
                0,
            )

            try:
                await channel.send(
                    f"🎉 Giveaway **#{message_id}** ended, "
                    "but there were no eligible entries."
                )
            except discord.HTTPException:
                pass

            return

        winners_count = min(
            int(giveaway["winners"]),
            len(entries),
        )

        winners = random.sample(
            entries,
            winners_count,
        )

        mentions = " ".join(
            f"<@{user_id}>"
            for user_id in winners
        )

        await self.update_giveaway_message(
            message_id,
            len(entries),
        )

        try:
            await channel.send(
                f"🎉 **GIVEAWAY ENDED!**\n\n"
                f"🎁 Prize: **{giveaway['prize']}**\n"
                f"🏆 Winner(s): {mentions}"
            )
        except discord.HTTPException:
            pass

    # =====================================================
    # BACKGROUND LOOP
    # =====================================================

    @tasks.loop(seconds=5)
    async def giveaway_loop(self):

        try:

            now = datetime.now(
                timezone.utc
            ).timestamp()

            rows = await db.fetchall(
                """
                SELECT message_id
                FROM giveaways
                WHERE ended = 0
                AND end_time <= ?
                """,
                (now,),
            )

            for row in rows:

                try:

                    await self.finish_giveaway(
                        int(row["message_id"])
                    )

                except Exception as exc:

                    print(
                        f"[KYŌKA] Giveaway "
                        f"#{row['message_id']} "
                        f"failed: "
                        f"{type(exc).__name__}: {exc}"
                    )

        except Exception as exc:

            print(
                f"[KYŌKA] Giveaway loop error: "
                f"{type(exc).__name__}: {exc}"
            )

    @giveaway_loop.before_loop
    async def before_giveaway_loop(self):
        await self.bot.wait_until_ready()


# =========================================================
# SETUP
# =========================================================

async def setup(bot):
    await bot.add_cog(
        Giveaways(bot)
    )
