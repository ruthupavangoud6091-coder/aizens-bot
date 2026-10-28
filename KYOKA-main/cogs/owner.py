import discord
from discord.ext import commands

from config import OWNER_ID, BOT_NAME, VERSION
from utils.embeds import success, error, info, creator


class OwnerCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def is_creator(self, user_id: int) -> bool:
        return user_id == OWNER_ID

    async def deny(self, ctx):
        await ctx.send(
            embed=error(
                "Access Denied",
                "This command is restricted to the KYŌKA creator."
            ),
            ephemeral=True
        )

    async def check_owner(self, ctx):
        if not self.is_creator(ctx.author.id):
            await self.deny(ctx)
            return False
        return True

    @commands.hybrid_command(
        name="botinfo",
        description="Creator only: show bot information."
    )
    async def botinfo(self, ctx):
        if not await self.check_owner(ctx):
            return

        embed = creator(
            "KYŌKA — Creator Panel",
            (
                f"**Bot:** {BOT_NAME}\n"
                f"**Version:** `{VERSION}`\n"
                f"**Servers:** `{len(self.bot.guilds)}`\n"
                f"**Users:** `{sum(g.member_count or 0 for g in self.bot.guilds):,}`\n"
                f"**Owner ID:** `{OWNER_ID}`"
            )
        )

        await ctx.send(embed=embed)

    @commands.hybrid_command(
        name="setstatus",
        description="Creator only: change KYŌKA's status."
    )
    async def setstatus(self, ctx, *, status: str):
        if not await self.check_owner(ctx):
            return

        await self.bot.change_presence(
            status=discord.Status.online,
            activity=discord.Game(name=status)
        )

        await ctx.send(
            embed=success(
                "Status Updated",
                f"KYŌKA status changed to:\n**{status}**"
            )
        )

    @commands.hybrid_command(
        name="maintenance",
        description="Creator only: toggle maintenance mode."
    )
    async def maintenance(self, ctx, mode: str):
        if not await self.check_owner(ctx):
            return

        mode = mode.lower()

        if mode not in ("on", "off"):
            await ctx.send(
                embed=error(
                    "Invalid Mode",
                    "Use `on` or `off`."
                )
            )
            return

        self.bot.maintenance_mode = mode == "on"

        state = "enabled 🔒" if mode == "on" else "disabled 🔓"

        await ctx.send(
            embed=success(
                "Maintenance Mode",
                f"Global maintenance mode is now **{state}**."
            )
        )

    @commands.hybrid_command(
        name="servers",
        description="Creator only: list servers."
    )
    async def servers(self, ctx):
        if not await self.check_owner(ctx):
            return

        lines = []

        for guild in self.bot.guilds:
            lines.append(
                f"**{guild.name}**\n"
                f"ID: `{guild.id}` • Members: `{guild.member_count or 0}`"
            )

        if not lines:
            lines.append("KYŌKA isn't in any servers.")

        text = "\n\n".join(lines)

        if len(text) > 4000:
            text = text[:3900] + "\n..."

        await ctx.send(
            embed=creator(
                "KYŌKA Servers",
                text
            )
        )

    @commands.hybrid_command(
        name="serverinfo",
        description="Creator only: inspect a server."
    )
    async def serverinfo(
        self,
        ctx,
        guild_id: str = None
    ):
        if not await self.check_owner(ctx):
            return

        if guild_id is None:
            guild = ctx.guild
        else:
            try:
                guild = self.bot.get_guild(int(guild_id))
            except ValueError:
                guild = None

        if guild is None:
            await ctx.send(
                embed=error(
                    "Server Not Found",
                    "KYŌKA isn't connected to that server."
                )
            )
            return

        owner = guild.owner

        embed = creator(
            f"Server Info — {guild.name}",
            (
                f"**ID:** `{guild.id}`\n"
                f"**Owner:** {owner.mention if owner else 'Unknown'}\n"
                f"**Members:** `{guild.member_count or 0}`\n"
                f"**Channels:** `{len(guild.channels)}`\n"
                f"**Roles:** `{len(guild.roles)}`\n"
                f"**Boosts:** `{guild.premium_subscription_count}`\n"
                f"**Created:** <t:{int(guild.created_at.timestamp())}:F>"
            )
        )

        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)

        await ctx.send(embed=embed)

    @commands.hybrid_command(
        name="leave",
        description="Creator only: make KYŌKA leave a server."
    )
    async def leave(self, ctx, guild_id: str):
        if not await self.check_owner(ctx):
            return

        try:
            guild = self.bot.get_guild(int(guild_id))
        except ValueError:
            guild = None

        if guild is None:
            await ctx.send(
                embed=error(
                    "Server Not Found",
                    "KYŌKA isn't connected to that server."
                )
            )
            return

        guild_name = guild.name
        guild_id_int = guild.id

        await guild.leave()

        await ctx.send(
            embed=success(
                "Server Left",
                f"KYŌKA left **{guild_name}** (`{guild_id_int}`)."
            )
        )

    @commands.hybrid_command(
        name="broadcast",
        description="Creator only: send a message to every server."
    )
    async def broadcast(self, ctx, *, message: str):
        if not await self.check_owner(ctx):
            return

        sent = 0
        failed = 0

        for guild in self.bot.guilds:
            channel = guild.system_channel

            if channel is None:
                for candidate in guild.text_channels:
                    if candidate.permissions_for(guild.me).send_messages:
                        channel = candidate
                        break

            if channel is None:
                failed += 1
                continue

            try:
                await channel.send(message)
                sent += 1
            except Exception:
                failed += 1

        await ctx.send(
            embed=success(
                "Broadcast Complete",
                (
                    f"**Sent:** `{sent}`\n"
                    f"**Failed:** `{failed}`"
                )
            )
        )

    @commands.hybrid_command(
        name="globalmsg",
        description="Creator only: send a global KYŌKA message."
    )
    async def globalmsg(self, ctx, *, message: str):
        if not await self.check_owner(ctx):
            return

        embed = discord.Embed(
            title="KYŌKA",
            description=message,
            color=discord.Color.dark_purple()
        )

        embed.set_footer(text="Creator Broadcast")

        sent = 0
        failed = 0

        for guild in self.bot.guilds:
            channel = guild.system_channel

            if channel is None:
                for candidate in guild.text_channels:
                    if candidate.permissions_for(guild.me).send_messages:
                        channel = candidate
                        break

            if channel is None:
                failed += 1
                continue

            try:
                await channel.send(embed=embed)
                sent += 1
            except Exception:
                failed += 1

        await ctx.send(
            embed=success(
                "Global Message Sent",
                f"Sent to `{sent}` servers. Failed: `{failed}`."
            )
        )

    @commands.hybrid_command(
        name="sync",
        description="Creator only: sync slash commands."
    )
    async def sync(self, ctx):
        if not await self.check_owner(ctx):
            return

        try:
            synced = await self.bot.tree.sync()

            await ctx.send(
                embed=success(
                    "Commands Synced",
                    f"Successfully synced `{len(synced)}` commands."
                )
            )
        except Exception as exc:
            await ctx.send(
                embed=error(
                    "Sync Failed",
                    f"`{type(exc).__name__}: {exc}`"
                )
            )

    @commands.hybrid_command(
        name="reload",
        description="Creator only: reload a cog."
    )
    async def reload(self, ctx, cog: str):
        if not await self.check_owner(ctx):
            return

        extension = cog

        if not extension.startswith("cogs."):
            extension = f"cogs.{extension}"

        try:
            await self.bot.reload_extension(extension)

            await ctx.send(
                embed=success(
                    "Cog Reloaded",
                    f"Successfully reloaded `{extension}`."
                )
            )

        except Exception as exc:
            await ctx.send(
                embed=error(
                    "Reload Failed",
                    f"`{type(exc).__name__}: {exc}`"
                )
            )

    @commands.hybrid_command(
        name="shutdown",
        description="Creator only: shut down KYŌKA."
    )
    async def shutdown(self, ctx):
        if not await self.check_owner(ctx):
            return

        await ctx.send(
            embed=success(
                "KYŌKA Shutdown",
                "Shutting down the bot..."
            )
        )

        await self.bot.close()

    @commands.hybrid_command(
        name="debug",
        description="Creator only: show debug information."
    )
    async def debug(self, ctx):
        if not await self.check_owner(ctx):
            return

        latency = round(self.bot.latency * 1000)

        embed = creator(
            "KYŌKA Debug",
            (
                f"**Latency:** `{latency}ms`\n"
                f"**Guilds:** `{len(self.bot.guilds)}`\n"
                f"**Cogs:** `{len(self.bot.cogs)}`\n"
                f"**Commands:** `{len(self.bot.tree.get_commands())}`"
            )
        )

        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(OwnerCog(bot))
