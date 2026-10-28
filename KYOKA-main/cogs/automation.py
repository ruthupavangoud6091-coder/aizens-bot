import asyncio
from datetime import datetime, timezone

import discord
from discord.ext import commands, tasks

from database.database import db
from utils.checks import guild_only
from utils.embeds import success, error, info


class Automation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.task_loop.start()

    def cog_unload(self):
        self.task_loop.cancel()

    # =========================================================
    # DATABASE HELPERS
    # =========================================================

    async def get_tasks(self, guild_id=None):
        if guild_id:
            return await db.fetchall(
                """
                SELECT *
                FROM automation_tasks
                WHERE guild_id = ?
                ORDER BY id ASC
                """,
                (guild_id,)
            )

        return await db.fetchall(
            """
            SELECT *
            FROM automation_tasks
            ORDER BY id ASC
            """
        )

    # =========================================================
    # AUTOMATION GROUP
    # =========================================================

    @commands.hybrid_group(
        name="automation",
        description="Manage automated server tasks."
    )
    @commands.has_permissions(manage_guild=True)
    @guild_only()
    async def automation(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send(
                embed=info(
                    "⚙️ Automation",
                    (
                        "`k!automation add` — Create a scheduled message\n"
                        "`k!automation list` — View automations\n"
                        "`k!automation remove` — Remove an automation\n"
                        "`k!automation trigger` — Create a keyword trigger\n"
                        "`k!automation triggers` — View triggers\n"
                        "`k!automation removetrigger` — Remove a trigger"
                    )
                )
            )

    # =========================================================
    # ADD SCHEDULE
    # =========================================================

    @automation.command(
        name="add",
        description="Create a scheduled automation."
    )
    async def automation_add(
        self,
        ctx,
        channel: discord.TextChannel,
        interval: int,
        *,
        message: str
    ):
        if interval < 10:
            await ctx.send(
                embed=error(
                    "The minimum interval is **10 seconds**."
                )
            )
            return

        if interval > 2592000:
            await ctx.send(
                embed=error(
                    "The maximum interval is **30 days**."
                )
            )
            return

        await db.execute(
            """
            INSERT INTO automation_tasks
            (
                guild_id,
                channel_id,
                message,
                interval_seconds,
                next_run,
                enabled,
                creator_id
            )
            VALUES (?, ?, ?, ?, ?, 1, ?)
            """,
            (
                ctx.guild.id,
                channel.id,
                message,
                interval,
                datetime.now(timezone.utc).timestamp() + interval,
                ctx.author.id
            ),
            commit=True
        )

        await ctx.send(
            embed=success(
                "⚙️ Automation created.\n\n"
                f"Channel: {channel.mention}\n"
                f"Interval: `{interval}` seconds"
            )
        )

    # =========================================================
    # LIST
    # =========================================================

    @automation.command(
        name="list",
        description="List scheduled automations."
    )
    async def automation_list(self, ctx):
        rows = await self.get_tasks(
            ctx.guild.id
        )

        if not rows:
            await ctx.send(
                embed=info(
                    "⚙️ Automations",
                    "No scheduled automations exist."
                )
            )
            return

        lines = []

        for row in rows:
            status = "🟢" if row["enabled"] else "🔴"

            channel = ctx.guild.get_channel(
                int(row["channel_id"])
            )

            channel_name = (
                channel.mention
                if channel
                else f"`{row['channel_id']}`"
            )

            preview = row["message"]

            if len(preview) > 50:
                preview = preview[:47] + "..."

            lines.append(
                f"{status} **ID `{row['id']}`**\n"
                f"Channel: {channel_name}\n"
                f"Every: `{row['interval_seconds']}s`\n"
                f"Message: `{preview}`"
            )

        await ctx.send(
            embed=info(
                "⚙️ Scheduled Automations",
                "\n\n".join(lines)
            )
        )

    # =========================================================
    # REMOVE
    # =========================================================

    @automation.command(
        name="remove",
        description="Remove a scheduled automation."
    )
    async def automation_remove(
        self,
        ctx,
        automation_id: int
    ):
        row = await db.fetchone(
            """
            SELECT *
            FROM automation_tasks
            WHERE id = ? AND guild_id = ?
            """,
            (
                automation_id,
                ctx.guild.id
            )
        )

        if not row:
            await ctx.send(
                embed=error(
                    "Automation not found."
                )
            )
            return

        await db.execute(
            """
            DELETE FROM automation_tasks
            WHERE id = ? AND guild_id = ?
            """,
            (
                automation_id,
                ctx.guild.id
            ),
            commit=True
        )

        await ctx.send(
            embed=success(
                f"🗑️ Removed automation **#{automation_id}**."
            )
        )

    # =========================================================
    # ENABLE / DISABLE
    # =========================================================

    @automation.command(
        name="toggle",
        description="Enable or disable an automation."
    )
    async def automation_toggle(
        self,
        ctx,
        automation_id: int
    ):
        row = await db.fetchone(
            """
            SELECT *
            FROM automation_tasks
            WHERE id = ? AND guild_id = ?
            """,
            (
                automation_id,
                ctx.guild.id
            )
        )

        if not row:
            await ctx.send(
                embed=error(
                    "Automation not found."
                )
            )
            return

        enabled = not bool(row["enabled"])

        await db.execute(
            """
            UPDATE automation_tasks
            SET enabled = ?
            WHERE id = ? AND guild_id = ?
            """,
            (
                int(enabled),
                automation_id,
                ctx.guild.id
            ),
            commit=True
        )

        status = "enabled" if enabled else "disabled"

        await ctx.send(
            embed=success(
                f"⚙️ Automation **#{automation_id}** is now "
                f"**{status}**."
            )
        )

    # =========================================================
    # KEYWORD TRIGGER
    # =========================================================

    @automation.command(
        name="trigger",
        description="Create a keyword automation."
    )
    async def automation_trigger(
        self,
        ctx,
        keyword: str,
        *,
        response: str
    ):
        keyword = keyword.lower().strip()

        if len(keyword) < 2:
            await ctx.send(
                embed=error(
                    "Keyword must contain at least 2 characters."
                )
            )
            return

        existing = await db.fetchone(
            """
            SELECT *
            FROM automation_triggers
            WHERE guild_id = ? AND keyword = ?
            """,
            (
                ctx.guild.id,
                keyword
            )
        )

        if existing:
            await ctx.send(
                embed=error(
                    f"A trigger for `{keyword}` already exists."
                )
            )
            return

        await db.execute(
            """
            INSERT INTO automation_triggers
            (
                guild_id,
                keyword,
                response,
                enabled,
                creator_id
            )
            VALUES (?, ?, ?, 1, ?)
            """,
            (
                ctx.guild.id,
                keyword,
                response,
                ctx.author.id
            ),
            commit=True
        )

        await ctx.send(
            embed=success(
                f"⚡ Trigger created for `{keyword}`."
            )
        )

    # =========================================================
    # TRIGGER LIST
    # =========================================================

    @automation.command(
        name="triggers",
        description="List keyword triggers."
    )
    async def automation_triggers(self, ctx):
        rows = await db.fetchall(
            """
            SELECT *
            FROM automation_triggers
            WHERE guild_id = ?
            ORDER BY id ASC
            """,
            (ctx.guild.id,)
        )

        if not rows:
            await ctx.send(
                embed=info(
                    "⚡ Triggers",
                    "No keyword triggers exist."
                )
            )
            return

        lines = []

        for row in rows:
            status = "🟢" if row["enabled"] else "🔴"

            response = row["response"]

            if len(response) > 60:
                response = response[:57] + "..."

            lines.append(
                f"{status} **ID `{row['id']}`** "
                f"`{row['keyword']}` → {response}"
            )

        await ctx.send(
            embed=info(
                "⚡ Keyword Triggers",
                "\n".join(lines)
            )
        )

    # =========================================================
    # REMOVE TRIGGER
    # =========================================================

    @automation.command(
        name="removetrigger",
        description="Remove a keyword trigger."
    )
    async def automation_remove_trigger(
        self,
        ctx,
        trigger_id: int
    ):
        row = await db.fetchone(
            """
            SELECT *
            FROM automation_triggers
            WHERE id = ? AND guild_id = ?
            """,
            (
                trigger_id,
                ctx.guild.id
            )
        )

        if not row:
            await ctx.send(
                embed=error(
                    "Trigger not found."
                )
            )
            return

        await db.execute(
            """
            DELETE FROM automation_triggers
            WHERE id = ? AND guild_id = ?
            """,
            (
                trigger_id,
                ctx.guild.id
            ),
            commit=True
        )

        await ctx.send(
            embed=success(
                f"🗑️ Removed trigger **#{trigger_id}**."
            )
        )

    # =========================================================
    # TOGGLE TRIGGER
    # =========================================================

    @automation.command(
        name="toggletrigger",
        description="Enable or disable a keyword trigger."
    )
    async def automation_toggle_trigger(
        self,
        ctx,
        trigger_id: int
    ):
        row = await db.fetchone(
            """
            SELECT *
            FROM automation_triggers
            WHERE id = ? AND guild_id = ?
            """,
            (
                trigger_id,
                ctx.guild.id
            )
        )

        if not row:
            await ctx.send(
                embed=error(
                    "Trigger not found."
                )
            )
            return

        enabled = not bool(row["enabled"])

        await db.execute(
            """
            UPDATE automation_triggers
            SET enabled = ?
            WHERE id = ? AND guild_id = ?
            """,
            (
                int(enabled),
                trigger_id,
                ctx.guild.id
            ),
            commit=True
        )

        status = "enabled" if enabled else "disabled"

        await ctx.send(
            embed=success(
                f"⚡ Trigger **#{trigger_id}** is now **{status}**."
            )
        )

    # =========================================================
    # SCHEDULE LOOP
    # =========================================================

    @tasks.loop(seconds=5)
    async def task_loop(self):
        try:
            rows = await self.get_tasks()

            now = datetime.now(timezone.utc).timestamp()

            for row in rows:
                if not row["enabled"]:
                    continue

                next_run = float(
                    row["next_run"] or 0
                )

                if now < next_run:
                    continue

                guild = self.bot.get_guild(
                    int(row["guild_id"])
                )

                if not guild:
                    continue

                channel = guild.get_channel(
                    int(row["channel_id"])
                )

                if not channel:
                    continue

                message = row["message"]

                try:
                    await channel.send(
                        message,
                        allowed_mentions=discord.AllowedMentions(
                            everyone=False,
                            users=True,
                            roles=False
                        )
                    )
                except discord.HTTPException as exc:
                    print(
                        f"[KYŌKA] Automation send failed: "
                        f"{type(exc).__name__}: {exc}"
                    )

                await db.execute(
                    """
                    UPDATE automation_tasks
                    SET next_run = ?
                    WHERE id = ?
                    """,
                    (
                        now + int(row["interval_seconds"]),
                        row["id"]
                    ),
                    commit=True
                )

        except Exception as exc:
            print(
                f"[KYŌKA] Automation loop error: "
                f"{type(exc).__name__}: {exc}"
            )

    @task_loop.before_loop
    async def before_task_loop(self):
        await self.bot.wait_until_ready()

    # =========================================================
    # MESSAGE TRIGGERS
    # =========================================================

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        if not message.guild:
            return

        if not message.content:
            return

        content = message.content.lower()

        rows = await db.fetchall(
            """
            SELECT *
            FROM automation_triggers
            WHERE guild_id = ?
            AND enabled = 1
            """,
            (message.guild.id,)
        )

        if not rows:
            return

        for row in rows:
            keyword = str(
                row["keyword"]
            ).lower()

            if keyword not in content:
                continue

            response = row["response"]

            replacements = {
                "{user}": message.author.mention,
                "{username}": message.author.name,
                "{displayname}": message.author.display_name,
                "{server}": message.guild.name,
                "{membercount}": str(
                    message.guild.member_count
                ),
                "{channel}": message.channel.mention
            }

            for variable, value in replacements.items():
                response = response.replace(
                    variable,
                    value
                )

            try:
                await message.channel.send(
                    response,
                    allowed_mentions=discord.AllowedMentions(
                        everyone=False,
                        users=True,
                        roles=False
                    )
                )
            except discord.HTTPException:
                pass

            # One trigger response per message.
            break


async def setup(bot):
    await bot.add_cog(
        Automation(bot)
    )
