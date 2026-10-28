import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timedelta
import random

from config import OWNER_ID


class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db

    # =========================
    # HELPERS
    # =========================

    async def get_user(self, user_id):
        return await self.db.get_user(user_id)

    async def balance_of(self, user_id):
        user = await self.get_user(user_id)
        return user["balance"]

    async def log_transaction(
        self,
        user_id,
        transaction_type,
        amount,
        description=""
    ):
        await self.db.log_transaction(
            user_id,
            transaction_type,
            amount,
            description
        )

    # =========================
    # BALANCE
    # =========================

    @commands.hybrid_command(
        name="balance",
        aliases=["bal"],
        description="Check your balance."
    )
    async def balance(self, ctx, member: discord.Member = None):
        member = member or ctx.author

        user = await self.get_user(member.id)

        total = user["balance"] + user["bank"]

        embed = discord.Embed(
            title=f"💰 {member.display_name}'s Balance",
            color=discord.Color.gold()
        )

        embed.set_thumbnail(
            url=member.display_avatar.url
        )

        embed.add_field(
            name="Wallet",
            value=f"🪙 `{user['balance']:,}`",
            inline=True
        )

        embed.add_field(
            name="Bank",
            value=f"🏦 `{user['bank']:,}`",
            inline=True
        )

        embed.add_field(
            name="Total",
            value=f"💎 `{total:,}`",
            inline=True
        )

        await ctx.send(embed=embed)

    # =========================
    # DAILY
    # =========================

    @commands.hybrid_command(
        name="daily",
        description="Claim your daily reward."
    )
    async def daily(self, ctx):
        user = await self.get_user(ctx.author.id)

        now = datetime.utcnow()

        if user["last_daily"]:
            try:
                last = datetime.fromisoformat(user["last_daily"])
                cooldown = timedelta(hours=24)

                if now - last < cooldown:
                    remaining = cooldown - (now - last)

                    hours = int(
                        remaining.total_seconds() // 3600
                    )

                    minutes = int(
                        (remaining.total_seconds() % 3600) // 60
                    )

                    await ctx.send(
                        f"⏳ You already claimed your daily.\n"
                        f"Come back in **{hours}h {minutes}m**."
                    )
                    return

            except ValueError:
                pass

        reward = 100

        await self.db.add_balance(
            ctx.author.id,
            reward
        )

        await self.db.execute(
            """
            UPDATE users
            SET last_daily = ?
            WHERE user_id = ?
            """,
            (
                now.isoformat(),
                ctx.author.id
            )
        )

        await self.log_transaction(
            ctx.author.id,
            "daily",
            reward,
            "Daily reward"
        )

        embed = discord.Embed(
            title="🎁 Daily Reward",
            description=(
                f"You received **🪙 {reward:,} coins**!"
            ),
            color=discord.Color.green()
        )

        await ctx.send(embed=embed)

    # =========================
    # WORK
    # =========================

    @commands.hybrid_command(
        name="work",
        description="Work for some coins."
    )
    async def work(self, ctx):
        user = await self.get_user(ctx.author.id)

        now = datetime.utcnow()

        if user["last_work"]:
            try:
                last = datetime.fromisoformat(
                    user["last_work"]
                )

                cooldown = timedelta(minutes=5)

                if now - last < cooldown:
                    remaining = cooldown - (now - last)

                    seconds = int(
                        remaining.total_seconds()
                    )

                    await ctx.send(
                        f"⏳ You're tired!\n"
                        f"Try again in **{seconds}s**."
                    )
                    return

            except ValueError:
                pass

        jobs = [
            "worked at a restaurant",
            "completed a delivery",
            "fixed a computer",
            "finished a freelance job",
            "helped a merchant",
            "completed a bounty"
        ]

        job = random.choice(jobs)

        amount = random.randint(50, 250)

        await self.db.add_balance(
            ctx.author.id,
            amount
        )

        await self.db.execute(
            """
            UPDATE users
            SET last_work = ?
            WHERE user_id = ?
            """,
            (
                now.isoformat(),
                ctx.author.id
            )
        )

        await self.log_transaction(
            ctx.author.id,
            "work",
            amount,
            job
        )

        await ctx.send(
            f"💼 You **{job}** and earned "
            f"**🪙 {amount:,} coins**!"
        )

    # =========================
    # PAY
    # =========================

    @commands.hybrid_command(
        name="pay",
        description="Pay another member."
    )
    @app_commands.describe(
        member="Member to pay.",
        amount="Amount to send."
    )
    async def pay(
        self,
        ctx,
        member: discord.Member,
        amount: int
    ):
        if member.bot:
            await ctx.send(
                "❌ You cannot pay bots."
            )
            return

        if member.id == ctx.author.id:
            await ctx.send(
                "❌ You cannot pay yourself."
            )
            return

        if amount <= 0:
            await ctx.send(
                "❌ Amount must be greater than 0."
            )
            return

        success = await self.db.remove_balance(
            ctx.author.id,
            amount
        )

        if not success:
            await ctx.send(
                "❌ You don't have enough coins."
            )
            return

        await self.db.add_balance(
            member.id,
            amount
        )

        await self.log_transaction(
            ctx.author.id,
            "pay",
            -amount,
            f"Paid {member.id}"
        )

        await self.log_transaction(
            member.id,
            "pay",
            amount,
            f"Received from {ctx.author.id}"
        )

        await ctx.send(
            f"💸 {ctx.author.mention} paid "
            f"**🪙 {amount:,}** to {member.mention}."
        )

    # =========================
    # DEPOSIT
    # =========================

    @commands.hybrid_command(
        name="deposit",
        aliases=["dep"],
        description="Deposit coins into your bank."
    )
    async def deposit(self, ctx, amount: str):
        user = await self.get_user(ctx.author.id)

        if amount.lower() == "all":
            amount = user["balance"]
        else:
            try:
                amount = int(amount)
            except ValueError:
                await ctx.send(
                    "❌ Enter a valid amount or `all`."
                )
                return

        if amount <= 0:
            await ctx.send(
                "❌ Amount must be greater than 0."
            )
            return

        if user["balance"] < amount:
            await ctx.send(
                "❌ You don't have enough coins."
            )
            return

        await self.db.remove_balance(
            ctx.author.id,
            amount
        )

        await self.db.add_bank(
            ctx.author.id,
            amount
        )

        await self.log_transaction(
            ctx.author.id,
            "deposit",
            amount,
            "Bank deposit"
        )

        await ctx.send(
            f"🏦 Deposited **🪙 {amount:,}** into your bank."
        )

    # =========================
    # WITHDRAW
    # =========================

    @commands.hybrid_command(
        name="withdraw",
        aliases=["with"],
        description="Withdraw coins from your bank."
    )
    async def withdraw(self, ctx, amount: str):
        user = await self.get_user(ctx.author.id)

        if amount.lower() == "all":
            amount = user["bank"]
        else:
            try:
                amount = int(amount)
            except ValueError:
                await ctx.send(
                    "❌ Enter a valid amount or `all`."
                )
                return

        if amount <= 0:
            await ctx.send(
                "❌ Amount must be greater than 0."
            )
            return

        if user["bank"] < amount:
            await ctx.send(
                "❌ You don't have enough in your bank."
            )
            return

        await self.db.remove_bank(
            ctx.author.id,
            amount
        )

        await self.db.add_balance(
            ctx.author.id,
            amount
        )

        await self.log_transaction(
            ctx.author.id,
            "withdraw",
            amount,
            "Bank withdrawal"
        )

        await ctx.send(
            f"💵 Withdrew **🪙 {amount:,}** from your bank."
        )

    # =========================
    # SHOP
    # =========================

    @commands.hybrid_command(
        name="shop",
        description="View the economy shop."
    )
    async def shop(self, ctx):
        embed = discord.Embed(
            title="🛒 KYŌKA Shop",
            description="Use `k!buy <item>` to purchase an item.",
            color=discord.Color.blurple()
        )

        embed.add_field(
            name="🍀 Lucky Charm",
            value="`lucky_charm` — 🪙 1,000",
            inline=False
        )

        embed.add_field(
            name="💎 Gem",
            value="`gem` — 🪙 5,000",
            inline=False
        )

        embed.add_field(
            name="🎟️ Premium Ticket",
            value="`premium_ticket` — 🪙 10,000",
            inline=False
        )

        await ctx.send(embed=embed)

    # =========================
    # BUY
    # =========================

    @commands.hybrid_command(
        name="buy",
        description="Buy an item from the shop."
    )
    async def buy(self, ctx, item: str, amount: int = 1):
        prices = {
            "lucky_charm": 1000,
            "gem": 5000,
            "premium_ticket": 10000
        }

        item = item.lower()

        if item not in prices:
            await ctx.send(
                "❌ That item doesn't exist."
            )
            return

        if amount <= 0:
            await ctx.send(
                "❌ Amount must be greater than 0."
            )
            return

        total = prices[item] * amount

        success = await self.db.remove_balance(
            ctx.author.id,
            total
        )

        if not success:
            await ctx.send(
                f"❌ You need **🪙 {total:,} coins**."
            )
            return

        await self.db.add_item(
            ctx.author.id,
            item,
            amount
        )

        await self.log_transaction(
            ctx.author.id,
            "purchase",
            -total,
            f"Bought {amount}x {item}"
        )

        await ctx.send(
            f"🛒 Bought **{amount}x {item}** "
            f"for **🪙 {total:,}**."
        )

    # =========================
    # INVENTORY
    # =========================

    @commands.hybrid_command(
        name="inventory",
        aliases=["inv"],
        description="View your inventory."
    )
    async def inventory(self, ctx):
        items = await self.db.get_inventory(
            ctx.author.id
        )

        if not items:
            await ctx.send(
                "🎒 Your inventory is empty."
            )
            return

        lines = []

        for item in items:
            lines.append(
                f"• `{item['item_id']}` × **{item['amount']:,}**"
            )

        embed = discord.Embed(
            title=f"🎒 {ctx.author.display_name}'s Inventory",
            description="\n".join(lines),
            color=discord.Color.blurple()
        )

        await ctx.send(embed=embed)

    # =========================
    # LEADERBOARD
    # =========================

    @commands.hybrid_command(
        name="rich",
        aliases=["leaderboard", "lb"],
        description="View the richest users."
    )
    async def rich(self, ctx):
        rows = await self.db.fetchall(
            """
            SELECT user_id, balance, bank,
                   (balance + bank) AS total
            FROM users
            ORDER BY total DESC
            LIMIT 10
            """
        )

        if not rows:
            await ctx.send(
                "📭 No economy data yet."
            )
            return

        lines = []

        for index, row in enumerate(rows, start=1):
            member = ctx.guild.get_member(
                row["user_id"]
            )

            name = (
                member.display_name
                if member
                else f"User {row['user_id']}"
            )

            lines.append(
                f"**{index}.** {name} — "
                f"🪙 `{row['total']:,}`"
            )

        embed = discord.Embed(
            title="🏆 Richest Members",
            description="\n".join(lines),
            color=discord.Color.gold()
        )

        await ctx.send(embed=embed)

    # =========================
    # REP
    # =========================

    @commands.hybrid_command(
        name="rep",
        description="Give reputation to a member."
    )
    async def rep(self, ctx, member: discord.Member):
        if member.bot:
            await ctx.send(
                "❌ You cannot give reputation to bots."
            )
            return

        if member.id == ctx.author.id:
            await ctx.send(
                "❌ You cannot rep yourself."
            )
            return

        await self.db.ensure_user(member.id)

        await self.db.execute(
            """
            UPDATE users
            SET reputation = reputation + 1
            WHERE user_id = ?
            """,
            (member.id,)
        )

        await ctx.send(
            f"⭐ {ctx.author.mention} gave "
            f"reputation to {member.mention}!"
        )

    # =========================
    # REPUTATION
    # =========================

    @commands.hybrid_command(
        name="reputation",
        aliases=["reps"],
        description="Check a member's reputation."
    )
    async def reputation(
        self,
        ctx,
        member: discord.Member = None
    ):
        member = member or ctx.author

        user = await self.db.get_user(
            member.id
        )

        await ctx.send(
            f"⭐ **{member.display_name}** has "
            f"**{user['reputation']:,} reputation**."
        )

    # ==================================================
    # OWNER ECONOMY CONTROLS
    # ==================================================

    async def owner_check(self, ctx):
        if ctx.author.id != OWNER_ID:
            await ctx.send(
                "❌ Creator-only command."
            )
            return False

        return True

    async def owner_log(
        self,
        ctx,
        action,
        target_id=None,
        details=""
    ):
        await self.db.log_owner_action(
            ctx.author.id,
            action,
            target_id,
            details
        )

    # =========================
    # ADD MONEY
    # =========================

    @commands.hybrid_command(
        name="addmoney",
        description="Creator only: add coins."
    )
    async def addmoney(
        self,
        ctx,
        member: discord.Member,
        amount: int
    ):
        if not await self.owner_check(ctx):
            return

        if amount <= 0:
            await ctx.send(
                "❌ Amount must be greater than 0."
            )
            return

        await self.db.add_balance(
            member.id,
            amount
        )

        await self.owner_log(
            ctx,
            "addmoney",
            member.id,
            f"Added {amount}"
        )

        await ctx.send(
            f"✅ Added **🪙 {amount:,}** to "
            f"{member.mention}."
        )

    # =========================
    # REMOVE MONEY
    # =========================

    @commands.hybrid_command(
        name="removemoney",
        description="Creator only: remove coins."
    )
    async def removemoney(
        self,
        ctx,
        member: discord.Member,
        amount: int
    ):
        if not await self.owner_check(ctx):
            return

        if amount <= 0:
            await ctx.send(
                "❌ Amount must be greater than 0."
            )
            return

        success = await self.db.remove_balance(
            member.id,
            amount
        )

        if not success:
            await ctx.send(
                "❌ User doesn't have enough coins."
            )
            return

        await self.owner_log(
            ctx,
            "removemoney",
            member.id,
            f"Removed {amount}"
        )

        await ctx.send(
            f"✅ Removed **🪙 {amount:,}** from "
            f"{member.mention}."
        )

    # =========================
    # SET MONEY
    # =========================

    @commands.hybrid_command(
        name="setmoney",
        description="Creator only: set a user's coins."
    )
    async def setmoney(
        self,
        ctx,
        member: discord.Member,
        amount: int
    ):
        if not await self.owner_check(ctx):
            return

        if amount < 0:
            await ctx.send(
                "❌ Amount cannot be negative."
            )
            return

        await self.db.set_balance(
            member.id,
            amount
        )

        await self.owner_log(
            ctx,
            "setmoney",
            member.id,
            f"Set balance to {amount}"
        )

        await ctx.send(
            f"✅ Set {member.mention}'s balance to "
            f"**🪙 {amount:,}**."
        )

    # =========================
    # RESET MONEY
    # =========================

    @commands.hybrid_command(
        name="resetmoney",
        description="Creator only: reset a user's wallet and bank."
    )
    async def resetmoney(
        self,
        ctx,
        member: discord.Member
    ):
        if not await self.owner_check(ctx):
            return

        await self.db.set_balance(
            member.id,
            0
        )

        await self.db.set_bank(
            member.id,
            0
        )

        await self.owner_log(
            ctx,
            "resetmoney",
            member.id,
            "Reset wallet and bank"
        )

        await ctx.send(
            f"♻️ Reset {member.mention}'s economy."
        )

    # =========================
    # GIVE ITEM
    # =========================

    @commands.hybrid_command(
        name="giveitem",
        description="Creator only: give an item."
    )
    async def giveitem(
        self,
        ctx,
        member: discord.Member,
        item: str,
        amount: int = 1
    ):
        if not await self.owner_check(ctx):
            return

        if amount <= 0:
            await ctx.send(
                "❌ Amount must be greater than 0."
            )
            return

        await self.db.add_item(
            member.id,
            item.lower(),
            amount
        )

        await self.owner_log(
            ctx,
            "giveitem",
            member.id,
            f"Gave {amount}x {item}"
        )

        await ctx.send(
            f"🎁 Gave **{amount}x {item}** "
            f"to {member.mention}."
        )

    # =========================
    # REMOVE ITEM
    # =========================

    @commands.hybrid_command(
        name="removeitem",
        description="Creator only: remove an item."
    )
    async def removeitem(
        self,
        ctx,
        member: discord.Member,
        item: str,
        amount: int = 1
    ):
        if not await self.owner_check(ctx):
            return

        if amount <= 0:
            await ctx.send(
                "❌ Amount must be greater than 0."
            )
            return

        success = await self.db.remove_item(
            member.id,
            item.lower(),
            amount
        )

        if not success:
            await ctx.send(
                "❌ User doesn't have that item amount."
            )
            return

        await self.owner_log(
            ctx,
            "removeitem",
            member.id,
            f"Removed {amount}x {item}"
        )

        await ctx.send(
            f"🗑️ Removed **{amount}x {item}** "
            f"from {member.mention}."
        )


async def setup(bot):
    await bot.add_cog(Economy(bot))
