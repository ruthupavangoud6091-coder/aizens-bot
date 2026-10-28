import discord
from discord.ext import commands

from database.database import db
from utils.checks import guild_only
from utils.embeds import success, error, info


class CustomCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ─────────────────────────────────────────────
    # CUSTOM COMMAND GROUP
    # ─────────────────────────────────────────────

    @commands.hybrid_group(
        name="custom",
        description="Manage custom server commands."
    )
    @guild_only()
    async def custom(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send(
                embed=info(
                    "Custom Commands",
                    "Use `k!custom list` to view custom commands."
                )
            )

    # ─────────────────────────────────────────────
    # ADD
    # ─────────────────────────────────────────────

    @custom.command(
        name="add",
        description="Create a custom command."
    )
    @commands.has_permissions(manage_guild=True)
    async def custom_add(self, ctx, name: str, *, response: str):
        name = name.lower().strip()

        if not name:
            await ctx.send(embed=error("Invalid command name."))
            return

        if name.startswith("k!"):
            name = name[2:]

        # Prevent dangerous command names
        protected = {
            "help",
            "ping",
            "botinfo",
            "afk",
            "ban",
            "kick",
            "mute",
            "warn",
            "purge",
            "clear",
            "ticket",
            "giveaway",
            "economy",
            "balance",
            "daily",
            "work",
            "pay",
            "mine",
            "flip",
            "hunt",
            "play",
            "stop",
            "skip",
            "queue",
            "ai",
            "owner",
            "shutdown",
            "restart",
            "reload",
        }

        if name in protected:
            await ctx.send(
                embed=error(
                    f"`k!{name}` is already reserved by KYŌKA."
                )
            )
            return

        existing = await db.fetchone(
            """
            SELECT * FROM custom_commands
            WHERE guild_id = ? AND name = ?
            """,
            (ctx.guild.id, name)
        )

        if existing:
            await ctx.send(
                embed=error(
                    f"Custom command `k!{name}` already exists."
                )
            )
            return

        await db.execute(
            """
            INSERT INTO custom_commands
            (guild_id, name, response, creator_id)
            VALUES (?, ?, ?, ?)
            """,
            (
                ctx.guild.id,
                name,
                response,
                ctx.author.id
            ),
            commit=True
        )

        await ctx.send(
            embed=success(
                f"Created custom command **`k!{name}`**."
            )
        )

    # ─────────────────────────────────────────────
    # EDIT
    # ─────────────────────────────────────────────

    @custom.command(
        name="edit",
        description="Edit a custom command."
    )
    @commands.has_permissions(manage_guild=True)
    async def custom_edit(self, ctx, name: str, *, response: str):
        name = name.lower().strip()

        existing = await db.fetchone(
            """
            SELECT * FROM custom_commands
            WHERE guild_id = ? AND name = ?
            """,
            (ctx.guild.id, name)
        )

        if not existing:
            await ctx.send(
                embed=error(
                    f"Custom command `k!{name}` doesn't exist."
                )
            )
            return

        await db.execute(
            """
            UPDATE custom_commands
            SET response = ?
            WHERE guild_id = ? AND name = ?
            """,
            (
                response,
                ctx.guild.id,
                name
            ),
            commit=True
        )

        await ctx.send(
            embed=success(
                f"Updated **`k!{name}`**."
            )
        )

    # ─────────────────────────────────────────────
    # REMOVE
    # ─────────────────────────────────────────────

    @custom.command(
        name="remove",
        description="Remove a custom command."
    )
    @commands.has_permissions(manage_guild=True)
    async def custom_remove(self, ctx, name: str):
        name = name.lower().strip()

        existing = await db.fetchone(
            """
            SELECT * FROM custom_commands
            WHERE guild_id = ? AND name = ?
            """,
            (ctx.guild.id, name)
        )

        if not existing:
            await ctx.send(
                embed=error(
                    f"Custom command `k!{name}` doesn't exist."
                )
            )
            return

        await db.execute(
            """
            DELETE FROM custom_commands
            WHERE guild_id = ? AND name = ?
            """,
            (
                ctx.guild.id,
                name
            ),
            commit=True
        )

        await ctx.send(
            embed=success(
                f"Removed **`k!{name}`**."
            )
        )

    # ─────────────────────────────────────────────
    # LIST
    # ─────────────────────────────────────────────

    @custom.command(
        name="list",
        description="List all custom commands."
    )
    async def custom_list(self, ctx):
        rows = await db.fetchall(
            """
            SELECT name
            FROM custom_commands
            WHERE guild_id = ?
            ORDER BY name
            """,
            (ctx.guild.id,)
        )

        if not rows:
            await ctx.send(
                embed=info(
                    "Custom Commands",
                    "This server has no custom commands yet."
                )
            )
            return

        commands_list = "\n".join(
            f"• `k!{row['name']}`"
            for row in rows
        )

        embed = info(
            "Custom Commands",
            commands_list
        )

        await ctx.send(embed=embed)

    # ─────────────────────────────────────────────
    # INFO
    # ─────────────────────────────────────────────

    @custom.command(
        name="info",
        description="View a custom command."
    )
    async def custom_info(self, ctx, name: str):
        name = name.lower().strip()

        row = await db.fetchone(
            """
            SELECT *
            FROM custom_commands
            WHERE guild_id = ? AND name = ?
            """,
            (ctx.guild.id, name)
        )

        if not row:
            await ctx.send(
                embed=error(
                    f"Custom command `k!{name}` doesn't exist."
                )
            )
            return

        creator = ctx.guild.get_member(row["creator_id"])

        creator_text = (
            creator.mention
            if creator
            else f"`{row['creator_id']}`"
        )

        embed = info(
            f"Custom Command • k!{name}",
            (
                f"**Response:**\n"
                f"{row['response']}\n\n"
                f"**Created by:** {creator_text}"
            )
        )

        await ctx.send(embed=embed)

    # ─────────────────────────────────────────────
    # CUSTOM COMMAND HANDLER
    # ─────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):

        if message.author.bot:
            return

        if not message.guild:
            return

        if not message.content.lower().startswith("k!"):
            return

        # Don't interfere with normal KYŌKA commands
        command_name = message.content[2:].split(" ", 1)[0].lower()

        if not command_name:
            return

        # If KYŌKA already has a real command with this name,
        # let the normal command system handle it.
        real_command = self.bot.get_command(command_name)

        if real_command is not None:
            return

        row = await db.fetchone(
            """
            SELECT *
            FROM custom_commands
            WHERE guild_id = ? AND name = ?
            """,
            (
                message.guild.id,
                command_name
            )
        )

        if not row:
            return

        response = row["response"]

        # ─────────────────────────────────────────
        # VARIABLES
        # ─────────────────────────────────────────

        replacements = {
            "{user}": message.author.mention,
            "{username}": message.author.name,
            "{displayname}": message.author.display_name,
            "{server}": message.guild.name,
            "{membercount}": str(message.guild.member_count),
            "{channel}": message.channel.mention,
        }

        for variable, value in replacements.items():
            response = response.replace(variable, value)

        # Delete command message if possible
        try:
            await message.delete()
        except (discord.Forbidden, discord.NotFound):
            pass

        try:
            await message.channel.send(response)
        except discord.HTTPException:
            pass


async def setup(bot):
    await bot.add_cog(CustomCommands(bot))
