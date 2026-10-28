import ast
import operator
import discord
from discord.ext import commands

from utils.embeds import success, error, info


class UtilityCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ---------------- CALCULATOR ----------------

    def safe_calculate(self, expression):
        allowed_operators = {
            ast.Add: operator.add,
            ast.Sub: operator.sub,
            ast.Mult: operator.mul,
            ast.Div: operator.truediv,
            ast.FloorDiv: operator.floordiv,
            ast.Mod: operator.mod,
            ast.Pow: operator.pow,
            ast.USub: operator.neg,
            ast.UAdd: operator.pos,
        }

        def calculate(node):
            if isinstance(node, ast.Constant):
                if isinstance(node.value, (int, float)):
                    return node.value
                raise ValueError("Invalid value.")

            if isinstance(node, ast.UnaryOp):
                op = allowed_operators.get(type(node.op))
                if not op:
                    raise ValueError("Invalid operator.")
                return op(calculate(node.operand))

            if isinstance(node, ast.BinOp):
                op = allowed_operators.get(type(node.op))
                if not op:
                    raise ValueError("Invalid operator.")

                left = calculate(node.left)
                right = calculate(node.right)

                if isinstance(node.op, ast.Pow) and abs(right) > 100:
                    raise ValueError("Exponent is too large.")

                return op(left, right)

            raise ValueError("Invalid expression.")

        tree = ast.parse(expression, mode="eval")
        return calculate(tree.body)

    # ---------------- USER INFO ----------------

    @commands.hybrid_command(
        name="userinfo",
        aliases=["ui", "user"],
        description="Show information about a user."
    )
    async def userinfo(
        self,
        ctx,
        member: discord.Member = None
    ):
        member = member or ctx.author

        roles = [
            role.mention
            for role in reversed(member.roles)
            if role != ctx.guild.default_role
        ]

        role_text = " ".join(roles) if roles else "None"

        embed = info(
            f"User Info — {member}",
            (
                f"**Username:** {member}\n"
                f"**Display Name:** {member.display_name}\n"
                f"**ID:** `{member.id}`\n"
                f"**Bot:** {'Yes' if member.bot else 'No'}\n"
                f"**Joined:** <t:{int(member.joined_at.timestamp())}:F>\n"
                f"**Created:** <t:{int(member.created_at.timestamp())}:F>\n\n"
                f"**Roles:** {role_text}"
            )
        )

        embed.set_thumbnail(url=member.display_avatar.url)

        await ctx.send(embed=embed)

    # ---------------- SERVER INFO ----------------

    @commands.hybrid_command(
        name="serverinfo",
        aliases=["si"],
        description="Show information about this server."
    )
    async def serverinfo(self, ctx):
        guild = ctx.guild

        owner = guild.owner.mention if guild.owner else "Unknown"

        embed = info(
            f"Server Info — {guild.name}",
            (
                f"**ID:** `{guild.id}`\n"
                f"**Owner:** {owner}\n"
                f"**Members:** `{guild.member_count or 0}`\n"
                f"**Humans:** `{sum(not m.bot for m in guild.members)}`\n"
                f"**Bots:** `{sum(m.bot for m in guild.members)}`\n"
                f"**Channels:** `{len(guild.channels)}`\n"
                f"**Roles:** `{len(guild.roles)}`\n"
                f"**Boost Level:** `{guild.premium_tier}`\n"
                f"**Boosts:** `{guild.premium_subscription_count}`\n"
                f"**Created:** <t:{int(guild.created_at.timestamp())}:F>"
            )
        )

        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)

        await ctx.send(embed=embed)

    # ---------------- AVATAR ----------------

    @commands.hybrid_command(
        name="avatar",
        aliases=["av"],
        description="Show a user's avatar."
    )
    async def avatar(
        self,
        ctx,
        member: discord.Member = None
    ):
        member = member or ctx.author

        embed = discord.Embed(
            title=f"{member.display_name}'s Avatar",
            color=discord.Color.blurple()
        )

        embed.set_image(url=member.display_avatar.url)
        embed.set_footer(text=f"User ID: {member.id}")

        await ctx.send(embed=embed)

    # ---------------- BANNER ----------------

    @commands.hybrid_command(
        name="banner",
        description="Show a user's Discord banner."
    )
    async def banner(
        self,
        ctx,
        member: discord.Member = None
    ):
        member = member or ctx.author

        try:
            user = await self.bot.fetch_user(member.id)
        except Exception:
            user = member

        if not user.banner:
            await ctx.send(
                embed=error(
                    "No Banner",
                    f"{member.mention} doesn't have a Discord banner."
                )
            )
            return

        embed = discord.Embed(
            title=f"{member.display_name}'s Banner",
            color=discord.Color.blurple()
        )

        embed.set_image(url=user.banner.url)

        await ctx.send(embed=embed)

    # ---------------- ROLES ----------------

    @commands.hybrid_command(
        name="roles",
        description="List all server roles."
    )
    async def roles(self, ctx):
        guild = ctx.guild

        roles = [
            role
            for role in reversed(guild.roles)
            if role != guild.default_role
        ]

        if not roles:
            await ctx.send(
                embed=info(
                    "Server Roles",
                    "This server has no custom roles."
                )
            )
            return

        text = " ".join(role.mention for role in roles)

        if len(text) > 3900:
            text = text[:3900] + "\n..."

        await ctx.send(
            embed=info(
                f"Roles — {guild.name}",
                text
            )
        )

    # ---------------- ROLE INFO ----------------

    @commands.hybrid_command(
        name="roleinfo",
        description="Show information about a role."
    )
    async def roleinfo(
        self,
        ctx,
        role: discord.Role
    ):
        embed = info(
            f"Role Info — {role.name}",
            (
                f"**ID:** `{role.id}`\n"
                f"**Color:** `{role.color}`\n"
                f"**Position:** `{role.position}`\n"
                f"**Members:** `{len(role.members)}`\n"
                f"**Mentionable:** `{role.mentionable}`\n"
                f"**Hoisted:** `{role.hoist}`\n"
                f"**Managed:** `{role.managed}`\n"
                f"**Created:** <t:{int(role.created_at.timestamp())}:F>"
            )
        )

        await ctx.send(embed=embed)

    # ---------------- POLL ----------------

    @commands.hybrid_command(
        name="poll",
        description="Create a yes/no poll."
    )
    async def poll(self, ctx, *, question: str):
        embed = discord.Embed(
            title="📊 Poll",
            description=question,
            color=discord.Color.blurple()
        )

        embed.set_author(
            name=ctx.author.display_name,
            icon_url=ctx.author.display_avatar.url
        )

        embed.set_footer(text="React with 👍 or 👎")

        message = await ctx.send(embed=embed)

        await message.add_reaction("👍")
        await message.add_reaction("👎")

    # ---------------- CALCULATOR ----------------

    @commands.hybrid_command(
        name="calculator",
        aliases=["calc"],
        description="Calculate a mathematical expression."
    )
    async def calculator(
        self,
        ctx,
        *,
        expression: str
    ):
        expression = expression.replace("^", "**")

        if len(expression) > 100:
            await ctx.send(
                embed=error(
                    "Expression Too Long",
                    "Keep the expression under 100 characters."
                )
            )
            return

        try:
            result = self.safe_calculate(expression)

            if isinstance(result, float):
                if result.is_integer():
                    result = int(result)
                else:
                    result = round(result, 10)

            await ctx.send(
                embed=success(
                    "Calculator",
                    f"```text\n{expression} = {result}\n```"
                )
            )

        except ZeroDivisionError:
            await ctx.send(
                embed=error(
                    "Calculator Error",
                    "You can't divide by zero."
                )
            )

        except Exception:
            await ctx.send(
                embed=error(
                    "Calculator Error",
                    "That's not a valid mathematical expression."
                )
            )

    # ---------------- STATISTICS ----------------

    @commands.hybrid_command(
        name="statistics",
        aliases=["stats"],
        description="Show KYŌKA statistics."
    )
    async def statistics(self, ctx):
        guilds = len(self.bot.guilds)

        members = sum(
            guild.member_count or 0
            for guild in self.bot.guilds
        )

        channels = sum(
            len(guild.channels)
            for guild in self.bot.guilds
        )

        embed = info(
            "KYŌKA Statistics",
            (
                f"**Servers:** `{guilds:,}`\n"
                f"**Users:** `{members:,}`\n"
                f"**Channels:** `{channels:,}`\n"
                f"**Latency:** `{round(self.bot.latency * 1000)}ms`\n"
                f"**Python:** `{discord.__version__}`"
            )
        )

        await ctx.send(embed=embed)

    # ---------------- HELP ----------------

    @commands.hybrid_command(
        name="help",
        description="Show KYŌKA's commands."
    )
    async def help_command(self, ctx):
        embed = discord.Embed(
            title="⚡ KYŌKA Help",
            description=(
                "Your all-in-one Discord assistant.\n\n"
                "Use the categories below to explore KYŌKA."
            ),
            color=discord.Color.dark_purple()
        )

        embed.add_field(
            name="🛡️ Moderation",
            value=(
                "`ban` • `kick` • `timeout` • `warn`\n"
                "`purge` • `lock` • `unlock` • `slowmode`"
            ),
            inline=False
        )

        embed.add_field(
            name="💰 Economy",
            value=(
                "`balance` • `daily` • `work` • `pay`\n"
                "`shop` • `buy` • `inventory` • `rich`"
            ),
            inline=False
        )

        embed.add_field(
            name="🎮 Games",
            value=(
                "`flip` • `dice` • `rps` • `slots`\n"
                "`hunt` • `mines` • `blackjack`"
            ),
            inline=False
        )

        embed.add_field(
            name="🎫 Community",
            value=(
                "`ticketpanel` • `giveaway` • `afk`\n"
                "`rank` • `leaderboard` • `rep`"
            ),
            inline=False
        )

        embed.add_field(
            name="🤖 AI",
            value="`ai` • `ask` • `aireset` • `aistatus`",
            inline=False
        )

        embed.add_field(
            name="🔧 Utility",
            value=(
                "`userinfo` • `serverinfo` • `avatar`\n"
                "`banner` • `roles` • `roleinfo` • `poll`\n"
                "`calculator` • `statistics`"
            ),
            inline=False
        )

        embed.set_footer(
            text=f"Prefix: {ctx.prefix} • Slash commands are also available"
        )

        await ctx.send(embed=embed)

    # ---------------- COMMAND ERROR HANDLER ----------------

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandNotFound):
            return

        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(
                embed=error_embed(
                    "Missing Argument",
                    f"You're missing `{error.param.name}`."
                )
            )
            return


def error_embed(title, description):
    return discord.Embed(
        title=f"❌ {title}",
        description=description,
        color=discord.Color.red()
    )


async def setup(bot):
    await bot.add_cog(UtilityCog(bot))
