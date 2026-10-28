import random
import asyncio
import discord

from discord.ext import commands

from database.database import db
from utils.checks import guild_only
from utils.embeds import success, error, info


class MinesView(discord.ui.View):
    def __init__(self, cog, ctx, bet, bombs):
        super().__init__(timeout=300)

        self.cog = cog
        self.ctx = ctx
        self.bet = bet
        self.bombs = bombs
        self.safe_tiles = set(range(25)) - bombs
        self.revealed = set()
        self.cashout = False
        self.ended = False

        self.multiplier = 1.0

        # Discord allows max 25 components.
        # We use 24 tiles + a cashout button.
        for i in range(24):
            self.add_item(MineButton(i, self))

        self.add_item(CashoutButton(self))

    async def reveal(self, interaction, index):
        if self.ended:
            return

        if index in self.revealed:
            await interaction.response.send_message(
                "That tile is already revealed.",
                ephemeral=True
            )
            return

        self.revealed.add(index)

        if index in self.bombs:
            self.ended = True
            self.cog.active_mines.pop(self.ctx.author.id, None)

            for child in self.children:
                child.disabled = True

            await interaction.response.edit_message(
                content=(
                    f"💥 **BOOM!**\n"
                    f"You lost **{self.bet:,}** coins."
                ),
                view=self
            )
            return

        self.multiplier += 0.25

        for child in self.children:
            if isinstance(child, MineButton) and child.index == index:
                child.label = "💎"
                child.style = discord.ButtonStyle.success
                child.disabled = True

        await interaction.response.edit_message(
            content=(
                f"💣 **Mines**\n"
                f"Bet: **{self.bet:,}**\n"
                f"Multiplier: **{self.multiplier:.2f}x**\n"
                f"Potential payout: **{int(self.bet * self.multiplier):,}**"
            ),
            view=self
        )

    async def cashout_game(self, interaction):
        if self.ended:
            return

        if not self.revealed:
            await interaction.response.send_message(
                "❌ Reveal at least one safe tile first.",
                ephemeral=True
            )
            return

        self.ended = True
        self.cashout = True

        payout = int(self.bet * self.multiplier)

        await db.add_balance(
            self.ctx.author.id,
            payout
        )

        self.cog.active_mines.pop(self.ctx.author.id, None)

        for child in self.children:
            child.disabled = True

        await interaction.response.edit_message(
            content=(
                f"💰 **Cashed out!**\n\n"
                f"Bet: **{self.bet:,}**\n"
                f"Multiplier: **{self.multiplier:.2f}x**\n"
                f"Payout: **{payout:,}**"
            ),
            view=self
        )

    async def on_timeout(self):
        if not self.ended:
            self.ended = True
            self.cog.active_mines.pop(self.ctx.author.id, None)

            for child in self.children:
                child.disabled = True


class MineButton(discord.ui.Button):
    def __init__(self, index, view):
        super().__init__(
            label="?",
            style=discord.ButtonStyle.secondary,
            row=index // 5
        )
        self.index = index
        self.mine_view = view

    async def callback(self, interaction):
        await self.mine_view.reveal(
            interaction,
            self.index
        )


class CashoutButton(discord.ui.Button):
    def __init__(self, view):
        super().__init__(
            label="💰 Cash Out",
            style=discord.ButtonStyle.success,
            row=4
        )
        self.mine_view = view

    async def callback(self, interaction):
        await self.mine_view.cashout_game(interaction)


class Games(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_mines = {}

    # =========================================================
    # FLIP
    # =========================================================

    @commands.hybrid_command(
        name="flip",
        description="Flip a coin and bet your coins."
    )
    @guild_only()
    async def flip(self, ctx, amount: int):
        if amount <= 0:
            await ctx.send(embed=error("Bet must be greater than 0."))
            return

        balance = await db.get_balance(ctx.author.id)

        if balance < amount:
            await ctx.send(
                embed=error(
                    f"You only have **{balance:,}** coins."
                )
            )
            return

        await db.remove_balance(
            ctx.author.id,
            amount
        )

        result = random.choice(["heads", "tails"])

        if result == "heads":
            winnings = amount * 2

            await db.add_balance(
                ctx.author.id,
                winnings
            )

            await ctx.send(
                embed=success(
                    f"🪙 **HEADS!**\n\n"
                    f"You won **{amount:,}** coins."
                )
            )
        else:
            await ctx.send(
                embed=error(
                    f"🪙 **TAILS!**\n\n"
                    f"You lost **{amount:,}** coins."
                )
            )

    # =========================================================
    # DICE
    # =========================================================

    @commands.hybrid_command(
        name="dice",
        description="Roll the dice and bet your coins."
    )
    @guild_only()
    async def dice(self, ctx, amount: int):
        if amount <= 0:
            await ctx.send(embed=error("Bet must be greater than 0."))
            return

        balance = await db.get_balance(ctx.author.id)

        if balance < amount:
            await ctx.send(embed=error("You don't have enough coins."))
            return

        await db.remove_balance(
            ctx.author.id,
            amount
        )

        player = random.randint(1, 6)
        bot_roll = random.randint(1, 6)

        if player > bot_roll:
            payout = amount * 2

            await db.add_balance(
                ctx.author.id,
                payout
            )

            result = (
                f"🎲 You rolled **{player}**\n"
                f"🎲 KYŌKA rolled **{bot_roll}**\n\n"
                f"🏆 You won **{amount:,}** coins!"
            )
            await ctx.send(embed=success(result))

        elif player == bot_roll:
            await db.add_balance(
                ctx.author.id,
                amount
            )

            await ctx.send(
                embed=info(
                    "🎲 Draw",
                    f"Both rolled **{player}**.\n"
                    f"Your **{amount:,}** coins were returned."
                )
            )

        else:
            await ctx.send(
                embed=error(
                    f"🎲 You rolled **{player}**\n"
                    f"🎲 KYŌKA rolled **{bot_roll}**\n\n"
                    f"You lost **{amount:,}** coins."
                )
            )

    # =========================================================
    # RPS
    # =========================================================

    @commands.hybrid_command(
        name="rps",
        description="Play rock paper scissors."
    )
    @guild_only()
    async def rps(self, ctx, choice: str, amount: int):
        choice = choice.lower()

        choices = {
            "rock": "rock",
            "paper": "paper",
            "scissors": "scissors",
            "r": "rock",
            "p": "paper",
            "s": "scissors"
        }

        if choice not in choices:
            await ctx.send(
                embed=error(
                    "Choose `rock`, `paper`, or `scissors`."
                )
            )
            return

        if amount <= 0:
            await ctx.send(embed=error("Bet must be greater than 0."))
            return

        balance = await db.get_balance(ctx.author.id)

        if balance < amount:
            await ctx.send(embed=error("You don't have enough coins."))
            return

        await db.remove_balance(
            ctx.author.id,
            amount
        )

        player = choices[choice]
        computer = random.choice(
            ["rock", "paper", "scissors"]
        )

        if player == computer:
            await db.add_balance(
                ctx.author.id,
                amount
            )

            await ctx.send(
                embed=info(
                    "🤝 Draw",
                    f"You both chose **{player}**.\n"
                    f"Your bet was returned."
                )
            )
            return

        wins = {
            ("rock", "scissors"),
            ("paper", "rock"),
            ("scissors", "paper")
        }

        if (player, computer) in wins:
            payout = amount * 2

            await db.add_balance(
                ctx.author.id,
                payout
            )

            await ctx.send(
                embed=success(
                    f"🎮 You: **{player}**\n"
                    f"🤖 KYŌKA: **{computer}**\n\n"
                    f"🏆 You won **{amount:,}** coins!"
                )
            )
        else:
            await ctx.send(
                embed=error(
                    f"🎮 You: **{player}**\n"
                    f"🤖 KYŌKA: **{computer}**\n\n"
                    f"You lost **{amount:,}** coins."
                )
            )

    # =========================================================
    # SLOTS
    # =========================================================

    @commands.hybrid_command(
        name="slots",
        description="Play the slot machine."
    )
    @guild_only()
    async def slots(self, ctx, amount: int):
        if amount <= 0:
            await ctx.send(embed=error("Bet must be greater than 0."))
            return

        balance = await db.get_balance(ctx.author.id)

        if balance < amount:
            await ctx.send(embed=error("You don't have enough coins."))
            return

        await db.remove_balance(
            ctx.author.id,
            amount
        )

        symbols = [
            "🍒",
            "🍋",
            "🍊",
            "🍇",
            "💎",
            "7️⃣"
        ]

        result = [
            random.choice(symbols),
            random.choice(symbols),
            random.choice(symbols)
        ]

        if result[0] == result[1] == result[2]:
            multiplier = 10
        elif result[0] == result[1] or result[1] == result[2]:
            multiplier = 2
        else:
            multiplier = 0

        payout = amount * multiplier

        if payout:
            await db.add_balance(
                ctx.author.id,
                payout
            )

        text = (
            f"🎰 **{' | '.join(result)}**\n\n"
            f"Bet: **{amount:,}**\n"
            f"Payout: **{payout:,}**"
        )

        if payout:
            await ctx.send(embed=success(text))
        else:
            await ctx.send(embed=error(text))

    # =========================================================
    # HUNT
    # =========================================================

    @commands.hybrid_command(
        name="hunt",
        description="Go hunting for collectibles."
    )
    @guild_only()
    async def hunt(self, ctx):
        creatures = [
            ("Rabbit", "Common", 50),
            ("Fox", "Uncommon", 100),
            ("Wolf", "Rare", 250),
            ("Dragon", "Epic", 750),
            ("Phoenix", "Legendary", 2000),
            ("Celestial Beast", "Mythic", 10000),
        ]

        roll = random.random()

        if roll < 0.45:
            creature = creatures[0]
        elif roll < 0.72:
            creature = creatures[1]
        elif roll < 0.90:
            creature = creatures[2]
        elif roll < 0.97:
            creature = creatures[3]
        elif roll < 0.995:
            creature = creatures[4]
        else:
            creature = creatures[5]

        name, rarity, reward = creature

        await db.add_balance(
            ctx.author.id,
            reward
        )

        await db.add_item(
            ctx.author.id,
            name,
            1
        )

        await ctx.send(
            embed=success(
                f"🏹 **Hunt successful!**\n\n"
                f"Creature: **{name}**\n"
                f"Rarity: **{rarity}**\n"
                f"Reward: **{reward:,}** coins"
            )
        )

    # =========================================================
    # COLLECTION
    # =========================================================

    @commands.hybrid_command(
        name="collection",
        description="View your hunting collection."
    )
    @guild_only()
    async def collection(self, ctx):
        items = await db.get_inventory(
            ctx.author.id
        )

        if not items:
            await ctx.send(
                embed=info(
                    "🏹 Collection",
                    "Your collection is empty.\n"
                    "Use `k!hunt` to find creatures."
                )
            )
            return

        lines = []

        for item in items:
            lines.append(
                f"• **{item['item_name']}** × `{item['quantity']}`"
            )

        await ctx.send(
            embed=info(
                f"🏹 {ctx.author.display_name}'s Collection",
                "\n".join(lines)
            )
        )

    # =========================================================
    # INVENTORY
    # =========================================================

    @commands.hybrid_command(
        name="inventory",
        description="View your inventory."
    )
    @guild_only()
    async def inventory(self, ctx):
        items = await db.get_inventory(
            ctx.author.id
        )

        if not items:
            await ctx.send(
                embed=info(
                    "🎒 Inventory",
                    "Your inventory is empty."
                )
            )
            return

        lines = []

        for item in items:
            lines.append(
                f"• **{item['item_name']}** × `{item['quantity']}`"
            )

        await ctx.send(
            embed=info(
                f"🎒 {ctx.author.display_name}'s Inventory",
                "\n".join(lines)
            )
        )

    # =========================================================
    # HUNTBOOK
    # =========================================================

    @commands.hybrid_command(
        name="huntbook",
        description="View all hunt creatures."
    )
    @guild_only()
    async def huntbook(self, ctx):
        text = (
            "🐇 **Common** — Rabbit\n"
            "🦊 **Uncommon** — Fox\n"
            "🐺 **Rare** — Wolf\n"
            "🐉 **Epic** — Dragon\n"
            "🔥 **Legendary** — Phoenix\n"
            "✨ **Mythic** — Celestial Beast"
        )

        await ctx.send(
            embed=info(
                "🏹 KYŌKA Huntbook",
                text
            )
        )

    # =========================================================
    # MINES
    # =========================================================

    @commands.hybrid_command(
        name="mine",
        aliases=["mines"],
        description="Play Mines."
    )
    @guild_only()
    async def mine(self, ctx, amount: int):
        if amount <= 0:
            await ctx.send(embed=error("Bet must be greater than 0."))
            return

        if ctx.author.id in self.active_mines:
            await ctx.send(
                embed=error(
                    "You already have an active Mines game."
                )
            )
            return

        balance = await db.get_balance(
            ctx.author.id
        )

        if balance < amount:
            await ctx.send(
                embed=error(
                    f"You only have **{balance:,}** coins."
                )
            )
            return

        await db.remove_balance(
            ctx.author.id,
            amount
        )

        bombs = set(
            random.sample(
                range(24),
                5
            )
        )

        view = MinesView(
            self,
            ctx,
            amount,
            bombs
        )

        self.active_mines[ctx.author.id] = view

        await ctx.send(
            content=(
                f"💣 **Mines**\n"
                f"Bet: **{amount:,}**\n"
                f"Click safe tiles and cash out before hitting a bomb!"
            ),
            view=view
        )

    # =========================================================
    # BLACKJACK
    # =========================================================

    @commands.hybrid_command(
        name="blackjack",
        description="Play blackjack."
    )
    @guild_only()
    async def blackjack(self, ctx, amount: int):
        if amount <= 0:
            await ctx.send(embed=error("Bet must be greater than 0."))
            return

        balance = await db.get_balance(
            ctx.author.id
        )

        if balance < amount:
            await ctx.send(
                embed=error("You don't have enough coins.")
            )
            return

        await db.remove_balance(
            ctx.author.id,
            amount
        )

        deck = [
            2, 3, 4, 5, 6, 7, 8, 9, 10,
            10, 10, 10, 11
        ] * 4

        random.shuffle(deck)

        player = [deck.pop(), deck.pop()]
        dealer = [deck.pop(), deck.pop()]

        def total(hand):
            value = sum(hand)

            while value > 21 and 11 in hand:
                hand[hand.index(11)] = 1
                value = sum(hand)

            return value

        player_total = total(player)
        dealer_total = total(dealer)

        if player_total == 21:
            payout = int(amount * 2.5)

            await db.add_balance(
                ctx.author.id,
                payout
            )

            await ctx.send(
                embed=success(
                    f"🃏 **BLACKJACK!**\n\n"
                    f"Your hand: `{player}`\n"
                    f"Dealer: `{dealer}`\n\n"
                    f"You won **{payout:,}** coins!"
                )
            )
            return

        while player_total < 17:
            player.append(deck.pop())
            player_total = total(player)

        while dealer_total < 17:
            dealer.append(deck.pop())
            dealer_total = total(dealer)

        if player_total > 21:
            result = "💥 You busted!"
            embed_func = error

        elif dealer_total > 21 or player_total > dealer_total:
            payout = amount * 2

            await db.add_balance(
                ctx.author.id,
                payout
            )

            result = f"🏆 You won **{payout:,}** coins!"
            embed_func = success

        elif player_total == dealer_total:
            await db.add_balance(
                ctx.author.id,
                amount
            )

            result = "🤝 Draw — your bet was returned."
            embed_func = info

        else:
            result = f"💀 You lost **{amount:,}** coins."
            embed_func = error

        await ctx.send(
            embed=embed_func(
                "🃏 Blackjack",
                (
                    f"Your hand: `{player}` → **{player_total}**\n"
                    f"Dealer hand: `{dealer}` → **{dealer_total}**\n\n"
                    f"{result}"
                )
            )
        )


async def setup(bot):
    await bot.add_cog(Games(bot))
