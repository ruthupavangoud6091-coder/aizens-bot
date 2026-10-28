import asyncio
import random
from typing import Optional

import discord
from discord.ext import commands

from utils.embeds import base_embed, success, error, premium
from config import OWNER_ID


class MusicPlayer:
    def __init__(self, guild_id: int):
        self.guild_id = guild_id
        self.queue = []
        self.current = None
        self.loop = False
        self.volume = 100
        self.twenty_four_seven = False
        self.voice_client = None
        self.text_channel = None
        self.playing = False

    def clear(self):
        self.queue.clear()
        self.current = None
        self.playing = False


class MusicControlView(discord.ui.View):
    def __init__(self, cog):
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(
        label="Pause",
        emoji="⏸️",
        style=discord.ButtonStyle.primary,
        custom_id="kyoka_music_pause"
    )
    async def pause(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        player = self.cog.get_player(interaction.guild.id)

        if not player.voice_client:
            await interaction.response.send_message(
                "❌ I'm not connected to a voice channel.",
                ephemeral=True
            )
            return

        if player.voice_client.is_playing():
            player.voice_client.pause()
            await interaction.response.send_message(
                "⏸️ Music paused.",
                ephemeral=True
            )
        elif player.voice_client.is_paused():
            player.voice_client.resume()
            await interaction.response.send_message(
                "▶️ Music resumed.",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "❌ Nothing is currently playing.",
                ephemeral=True
            )

    @discord.ui.button(
        label="Skip",
        emoji="⏭️",
        style=discord.ButtonStyle.success,
        custom_id="kyoka_music_skip"
    )
    async def skip(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        player = self.cog.get_player(interaction.guild.id)

        if not player.voice_client:
            await interaction.response.send_message(
                "❌ I'm not connected to voice.",
                ephemeral=True
            )
            return

        player.voice_client.stop()

        await interaction.response.send_message(
            "⏭️ Skipped.",
            ephemeral=True
        )

    @discord.ui.button(
        label="Loop",
        emoji="🔁",
        style=discord.ButtonStyle.secondary,
        custom_id="kyoka_music_loop"
    )
    async def loop(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        player = self.cog.get_player(interaction.guild.id)

        player.loop = not player.loop

        await interaction.response.send_message(
            f"🔁 Loop: **{'ON' if player.loop else 'OFF'}**",
            ephemeral=True
        )

    @discord.ui.button(
        label="Shuffle",
        emoji="🔀",
        style=discord.ButtonStyle.secondary,
        custom_id="kyoka_music_shuffle"
    )
    async def shuffle(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        player = self.cog.get_player(interaction.guild.id)

        if len(player.queue) < 2:
            await interaction.response.send_message(
                "❌ Not enough songs in the queue.",
                ephemeral=True
            )
            return

        random.shuffle(player.queue)

        await interaction.response.send_message(
            "🔀 Queue shuffled.",
            ephemeral=True
        )

    @discord.ui.button(
        label="Stop",
        emoji="⏹️",
        style=discord.ButtonStyle.danger,
        custom_id="kyoka_music_stop"
    )
    async def stop(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        player = self.cog.get_player(interaction.guild.id)

        player.queue.clear()
        player.current = None

        if player.voice_client:
            player.voice_client.stop()

        await interaction.response.send_message(
            "⏹️ Music stopped and queue cleared.",
            ephemeral=True
        )


class MusicCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.players = {}

    # =========================================================
    # PLAYER
    # =========================================================

    def get_player(self, guild_id: int):
        if guild_id not in self.players:
            self.players[guild_id] = MusicPlayer(
                guild_id
            )

        return self.players[guild_id]

    # =========================================================
    # PREMIUM CHECK
    # =========================================================

    async def premium_check(
        self,
        ctx: commands.Context
    ):
        if ctx.author.id == OWNER_ID:
            return True

        premium_cog = self.bot.get_cog("PremiumCog")

        if not premium_cog:
            await ctx.send(
                embed=error(
                    "Premium Unavailable",
                    "The Premium system is not loaded."
                )
            )
            return False

        if not await premium_cog.is_premium(
            ctx.guild.id
        ):
            await ctx.send(
                embed=premium(
                    "💎 Premium Required",
                    (
                        "Music is a **KYŌKA Premium** feature.\n\n"
                        "This server needs Premium to use music."
                    )
                )
            )
            return False

        return True

    # =========================================================
    # JOIN VOICE
    # =========================================================

    async def connect_to_voice(
        self,
        ctx: commands.Context
    ):
        if not ctx.author.voice:
            await ctx.send(
                embed=error(
                    "Voice Channel Required",
                    "You need to join a voice channel first."
                )
            )
            return None

        channel = ctx.author.voice.channel
        voice = ctx.guild.voice_client

        try:
            if voice:
                if voice.channel.id != channel.id:
                    await voice.move_to(channel)

                return voice

            voice = await channel.connect(
                self_deaf=True
            )

            return voice

        except discord.Forbidden:
            await ctx.send(
                embed=error(
                    "Voice Permission Missing",
                    (
                        "I need **Connect** and **Speak** "
                        "permissions in that voice channel."
                    )
                )
            )
            return None

        except discord.ClientException:
            await ctx.send(
                embed=error(
                    "Voice Error",
                    "I couldn't connect to the voice channel."
                )
            )
            return None

    # =========================================================
    # PLAY
    # =========================================================

    @commands.hybrid_command(
        name="play",
        description="Play music in your voice channel."
    )
    @commands.guild_only()
    async def play(
        self,
        ctx: commands.Context,
        *,
        query: str
    ):
        if not await self.premium_check(ctx):
            return

        voice = await self.connect_to_voice(ctx)

        if not voice:
            return

        player = self.get_player(
            ctx.guild.id
        )

        player.voice_client = voice
        player.text_channel = ctx.channel

        # This is the music request layer.
        # Lavalink / Wavelink should be connected here.
        player.queue.append({
            "title": query,
            "url": query,
            "requester": ctx.author.id
        })

        if player.playing:
            await ctx.send(
                embed=success(
                    "Added to Queue",
                    f"🎵 **{query}** has been added to the queue."
                )
            )
            return

        player.current = player.queue.pop(0)
        player.playing = True

        await ctx.send(
            embed=success(
                "🎵 Music",
                (
                    f"**Now Playing**\n"
                    f"🎶 {player.current['title']}\n\n"
                    f"🔊 Volume: `{player.volume}%`\n"
                    f"🔁 Loop: `{'ON' if player.loop else 'OFF'}`"
                )
            ),
            view=MusicControlView(self)
        )

    # =========================================================
    # SEARCH
    # =========================================================

    @commands.hybrid_command(
        name="search",
        description="Search for a song."
    )
    @commands.guild_only()
    async def search(
        self,
        ctx: commands.Context,
        *,
        query: str
    ):
        if not await self.premium_check(ctx):
            return

        await ctx.send(
            embed=base_embed(
                "🔎 Music Search",
                (
                    f"Searching for:\n"
                    f"**{query}**\n\n"
                    "Your Lavalink music backend will provide "
                    "the playable results."
                )
            )
        )

    # =========================================================
    # PAUSE
    # =========================================================

    @commands.hybrid_command(
        name="pause",
        description="Pause the current song."
    )
    async def pause(
        self,
        ctx: commands.Context
    ):
        if not await self.premium_check(ctx):
            return

        voice = ctx.guild.voice_client

        if not voice or not voice.is_playing():
            await ctx.send(
                embed=error(
                    "Nothing Playing",
                    "There is no music currently playing."
                )
            )
            return

        voice.pause()

        await ctx.send(
            embed=success(
                "Paused",
                "⏸️ Music has been paused."
            )
        )

    # =========================================================
    # RESUME
    # =========================================================

    @commands.hybrid_command(
        name="resume",
        description="Resume paused music."
    )
    async def resume(
        self,
        ctx: commands.Context
    ):
        if not await self.premium_check(ctx):
            return

        voice = ctx.guild.voice_client

        if not voice or not voice.is_paused():
            await ctx.send(
                embed=error(
                    "Nothing Paused",
                    "There is no paused music."
                )
            )
            return

        voice.resume()

        await ctx.send(
            embed=success(
                "Resumed",
                "▶️ Music has resumed."
            )
        )

    # =========================================================
    # SKIP
    # =========================================================

    @commands.hybrid_command(
        name="skip",
        description="Skip the current song."
    )
    async def skip(
        self,
        ctx: commands.Context
    ):
        if not await self.premium_check(ctx):
            return

        voice = ctx.guild.voice_client

        if not voice:
            await ctx.send(
                embed=error(
                    "Not Connected",
                    "I'm not connected to a voice channel."
                )
            )
            return

        voice.stop()

        await ctx.send(
            embed=success(
                "Skipped",
                "⏭️ Current song skipped."
            )
        )

    # =========================================================
    # STOP
    # =========================================================

    @commands.hybrid_command(
        name="stop",
        description="Stop music and clear the queue."
    )
    async def stop(
        self,
        ctx: commands.Context
    ):
        if not await self.premium_check(ctx):
            return

        player = self.get_player(
            ctx.guild.id
        )

        player.clear()

        voice = ctx.guild.voice_client

        if voice:
            voice.stop()

        await ctx.send(
            embed=success(
                "Music Stopped",
                "⏹️ Music stopped and queue cleared."
            )
        )

    # =========================================================
    # LEAVE
    # =========================================================

    @commands.hybrid_command(
        name="leave",
        description="Leave the voice channel."
    )
    async def leave(
        self,
        ctx: commands.Context
    ):
        if not await self.premium_check(ctx):
            return

        voice = ctx.guild.voice_client

        if not voice:
            await ctx.send(
                "❌ I'm not in a voice channel."
            )
            return

        player = self.get_player(
            ctx.guild.id
        )

        player.clear()
        player.voice_client = None

        await voice.disconnect()

        await ctx.send(
            embed=success(
                "Disconnected",
                "👋 Left the voice channel."
            )
        )

    # =========================================================
    # QUEUE
    # =========================================================

    @commands.hybrid_command(
        name="queue",
        description="Show the music queue."
    )
    async def queue(
        self,
        ctx: commands.Context
    ):
        if not await self.premium_check(ctx):
            return

        player = self.get_player(
            ctx.guild.id
        )

        if not player.current and not player.queue:
            await ctx.send(
                embed=error(
                    "Queue Empty",
                    "There are no songs in the queue."
                )
            )
            return

        lines = []

        if player.current:
            lines.append(
                f"🎵 **Now:** {player.current['title']}"
            )

        for index, song in enumerate(
            player.queue[:20],
            start=1
        ):
            lines.append(
                f"`{index}.` {song['title']}"
            )

        embed = base_embed(
            "📜 Music Queue",
            "\n".join(lines)
        )

        await ctx.send(embed=embed)

    # =========================================================
    # NOW PLAYING
    # =========================================================

    @commands.hybrid_command(
        name="nowplaying",
        description="Show the current song."
    )
    async def nowplaying(
        self,
        ctx: commands.Context
    ):
        if not await self.premium_check(ctx):
            return

        player = self.get_player(
            ctx.guild.id
        )

        if not player.current:
            await ctx.send(
                embed=error(
                    "Nothing Playing",
                    "There is no current song."
                )
            )
            return

        await ctx.send(
            embed=base_embed(
                "🎵 Now Playing",
                (
                    f"**{player.current['title']}**\n\n"
                    f"🔊 Volume: `{player.volume}%`\n"
                    f"🔁 Loop: `{'ON' if player.loop else 'OFF'}`"
                )
            ),
            view=MusicControlView(self)
        )

    # =========================================================
    # SHUFFLE
    # =========================================================

    @commands.hybrid_command(
        name="shuffle",
        description="Shuffle the queue."
    )
    async def shuffle(
        self,
        ctx: commands.Context
    ):
        if not await self.premium_check(ctx):
            return

        player = self.get_player(
            ctx.guild.id
        )

        if len(player.queue) < 2:
            await ctx.send(
                "❌ You need at least 2 songs in the queue."
            )
            return

        random.shuffle(
            player.queue
        )

        await ctx.send(
            embed=success(
                "Queue Shuffled",
                "🔀 The queue has been shuffled."
            )
        )

    # =========================================================
    # LOOP
    # =========================================================

    @commands.hybrid_command(
        name="loop",
        description="Toggle song looping."
    )
    async def loop(
        self,
        ctx: commands.Context
    ):
        if not await self.premium_check(ctx):
            return

        player = self.get_player(
            ctx.guild.id
        )

        player.loop = not player.loop

        await ctx.send(
            embed=success(
                "Loop Updated",
                (
                    f"🔁 Loop is now "
                    f"**{'ON' if player.loop else 'OFF'}**."
                )
            )
        )

    # =========================================================
    # VOLUME
    # =========================================================

    @commands.hybrid_command(
        name="volume",
        description="Change music volume."
    )
    async def volume(
        self,
        ctx: commands.Context,
        amount: int
    ):
        if not await self.premium_check(ctx):
            return

        if amount < 0 or amount > 200:
            await ctx.send(
                embed=error(
                    "Invalid Volume",
                    "Volume must be between `0` and `200`."
                )
            )
            return

        player = self.get_player(
            ctx.guild.id
        )

        player.volume = amount

        voice = ctx.guild.voice_client

        if voice and voice.source:
            try:
                voice.source.volume = amount / 100
            except AttributeError:
                pass

        await ctx.send(
            embed=success(
                "Volume Updated",
                f"🔊 Volume set to **{amount}%**."
            )
        )

    # =========================================================
    # JOIN
    # =========================================================

    @commands.hybrid_command(
        name="join",
        description="Join your voice channel."
    )
    async def join(
        self,
        ctx: commands.Context
    ):
        if not await self.premium_check(ctx):
            return

        voice = await self.connect_to_voice(ctx)

        if voice:
            player = self.get_player(
                ctx.guild.id
            )

            player.voice_client = voice

            await ctx.send(
                embed=success(
                    "Connected",
                    f"🔊 Joined **{voice.channel.name}**."
                )
            )

    # =========================================================
    # 24/7
    # =========================================================

    @commands.hybrid_command(
        name="247",
        description="Toggle 24/7 voice mode."
    )
    async def twenty_four_seven(
        self,
        ctx: commands.Context
    ):
        if not await self.premium_check(ctx):
            return

        player = self.get_player(
            ctx.guild.id
        )

        player.twenty_four_seven = (
            not player.twenty_four_seven
        )

        status = (
            "enabled"
            if player.twenty_four_seven
            else "disabled"
        )

        await ctx.send(
            embed=success(
                "24/7 Mode",
                f"♾️ 24/7 mode **{status}**."
            )
        )

    # =========================================================
    # DJ ROLE
    # =========================================================

    @commands.hybrid_command(
        name="dj",
        description="Set the DJ role."
    )
    @commands.has_permissions(
        manage_guild=True
    )
    async def dj(
        self,
        ctx: commands.Context,
        role: discord.Role
    ):
        if not await self.premium_check(ctx):
            return

        await ctx.send(
            embed=success(
                "DJ Role",
                f"🎧 DJ role set to {role.mention}."
            )
        )

    # =========================================================
    # COG UNLOAD
    # =========================================================

    def cog_unload(self):
        for player in self.players.values():
            if player.voice_client:
                asyncio.create_task(
                    player.voice_client.disconnect()
                )


async def setup(bot):
    await bot.add_cog(
        MusicCog(bot)
    )
