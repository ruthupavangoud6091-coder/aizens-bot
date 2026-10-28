import asyncio
import io
from datetime import datetime, timezone

import discord
from discord.ext import commands, tasks

from database.database import db
from utils.checks import guild_only
from utils.embeds import success, error, info


class TicketCategorySelect(discord.ui.Select):
    def __init__(self, cog):
        self.cog = cog

        options = [
            discord.SelectOption(
                label="General Support",
                value="support",
                emoji="🎫",
                description="Get help from the support team."
            ),
            discord.SelectOption(
                label="Report",
                value="report",
                emoji="🚨",
                description="Report a member or problem."
            ),
            discord.SelectOption(
                label="Giveaway",
                value="giveaway",
                emoji="🎁",
                description="Get help with a giveaway."
            ),
            discord.SelectOption(
                label="Other",
                value="other",
                emoji="📩",
                description="Open another type of ticket."
            ),
        ]

        super().__init__(
            placeholder="Select a ticket category...",
            options=options,
            custom_id="kyoka_ticket_category"
        )

    async def callback(self, interaction: discord.Interaction):
        await self.cog.create_ticket(
            interaction,
            self.values[0]
        )


class TicketPanelView(discord.ui.View):
    def __init__(self, cog):
        super().__init__(timeout=None)
        self.add_item(TicketCategorySelect(cog))


class TicketControlView(discord.ui.View):
    def __init__(self, cog):
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(
        label="Claim",
        emoji="🙋",
        style=discord.ButtonStyle.primary,
        custom_id="kyoka_ticket_claim"
    )
    async def claim(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await self.cog.claim_ticket(interaction)

    @discord.ui.button(
        label="Close",
        emoji="🔒",
        style=discord.ButtonStyle.danger,
        custom_id="kyoka_ticket_close"
    )
    async def close(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await self.cog.close_ticket(interaction)

    @discord.ui.button(
        label="Reopen",
        emoji="🔓",
        style=discord.ButtonStyle.success,
        custom_id="kyoka_ticket_reopen"
    )
    async def reopen(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await self.cog.reopen_ticket(interaction)

    @discord.ui.button(
        label="Transcript",
        emoji="📄",
        style=discord.ButtonStyle.secondary,
        custom_id="kyoka_ticket_transcript"
    )
    async def transcript(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await self.cog.send_transcript(interaction)


class Tickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.auto_close_loop.start()

    def cog_unload(self):
        self.auto_close_loop.cancel()

    # =========================================================
    # DATABASE HELPERS
    # =========================================================

    async def get_ticket_settings(self, guild_id: int, category: str):
        return await db.fetchone(
            """
            SELECT *
            FROM ticket_settings
            WHERE guild_id = ? AND category = ?
            """,
            (guild_id, category)
        )

    async def get_staff_role(self, guild_id: int, category: str):
        row = await self.get_ticket_settings(
            guild_id,
            category
        )

        if not row:
            return None

        role_id = row["staff_role_id"]

        if not role_id:
            return None

        return self.bot.get_guild(guild_id).get_role(
            int(role_id)
        )

    async def get_log_channel(self, guild_id: int):
        row = await db.fetchone(
            """
            SELECT log_channel_id
            FROM ticket_settings
            WHERE guild_id = ?
            LIMIT 1
            """,
            (guild_id,)
        )

        if not row or not row["log_channel_id"]:
            return None

        guild = self.bot.get_guild(guild_id)

        if not guild:
            return None

        return guild.get_channel(
            int(row["log_channel_id"])
        )

    # =========================================================
    # SETUP
    # =========================================================

    @commands.hybrid_command(
        name="ticketsetup",
        description="Configure a ticket category staff role."
    )
    @commands.has_permissions(manage_guild=True)
    @guild_only()
    async def ticketsetup(
        self,
        ctx,
        category: str,
        staff_role: discord.Role
    ):
        category = category.lower()

        allowed = {
            "support",
            "report",
            "giveaway",
            "other"
        }

        if category not in allowed:
            await ctx.send(
                embed=error(
                    "Invalid category.\n"
                    "Use: `support`, `report`, `giveaway`, or `other`."
                )
            )
            return

        existing = await self.get_ticket_settings(
            ctx.guild.id,
            category
        )

        if existing:
            await db.execute(
                """
                UPDATE ticket_settings
                SET staff_role_id = ?
                WHERE guild_id = ? AND category = ?
                """,
                (
                    staff_role.id,
                    ctx.guild.id,
                    category
                ),
                commit=True
            )
        else:
            await db.execute(
                """
                INSERT INTO ticket_settings
                (guild_id, category, staff_role_id)
                VALUES (?, ?, ?)
                """,
                (
                    ctx.guild.id,
                    category,
                    staff_role.id
                ),
                commit=True
            )

        await ctx.send(
            embed=success(
                f"🎫 **{category.title()}** tickets will now use "
                f"{staff_role.mention}."
            )
        )

    # =========================================================
    # LOG CHANNEL
    # =========================================================

    @commands.hybrid_command(
        name="ticketlogs",
        description="Set the ticket transcript/log channel."
    )
    @commands.has_permissions(manage_guild=True)
    @guild_only()
    async def ticketlogs(
        self,
        ctx,
        channel: discord.TextChannel
    ):
        categories = [
            "support",
            "report",
            "giveaway",
            "other"
        ]

        for category in categories:
            existing = await self.get_ticket_settings(
                ctx.guild.id,
                category
            )

            if existing:
                await db.execute(
                    """
                    UPDATE ticket_settings
                    SET log_channel_id = ?
                    WHERE guild_id = ? AND category = ?
                    """,
                    (
                        channel.id,
                        ctx.guild.id,
                        category
                    ),
                    commit=True
                )
            else:
                await db.execute(
                    """
                    INSERT INTO ticket_settings
                    (guild_id, category, log_channel_id)
                    VALUES (?, ?, ?)
                    """,
                    (
                        ctx.guild.id,
                        category,
                        channel.id
                    ),
                    commit=True
                )

        await ctx.send(
            embed=success(
                f"📄 Ticket logs will be sent to {channel.mention}."
            )
        )

    # =========================================================
    # PANEL
    # =========================================================

    @commands.hybrid_command(
        name="ticketpanel",
        description="Send the ticket panel."
    )
    @commands.has_permissions(manage_guild=True)
    @guild_only()
    async def ticketpanel(self, ctx):
        embed = discord.Embed(
            title="🎫 KYŌKA Support",
            description=(
                "Need help? Open a ticket below.\n\n"
                "🎫 **General Support**\n"
                "Get help from the support team.\n\n"
                "🚨 **Report**\n"
                "Report a member or issue.\n\n"
                "🎁 **Giveaway**\n"
                "Get help with a giveaway.\n\n"
                "📩 **Other**\n"
                "For anything else."
            ),
            color=discord.Color.blurple()
        )

        if ctx.guild.icon:
            embed.set_thumbnail(
                url=ctx.guild.icon.url
            )

        await ctx.send(
            embed=embed,
            view=TicketPanelView(self)
        )

    # =========================================================
    # CREATE TICKET
    # =========================================================

    async def create_ticket(
        self,
        interaction: discord.Interaction,
        category: str
    ):
        guild = interaction.guild
        user = interaction.user

        existing = await db.fetchone(
            """
            SELECT *
            FROM tickets
            WHERE guild_id = ?
            AND user_id = ?
            AND status = 'open'
            """,
            (
                guild.id,
                user.id
            )
        )

        if existing:
            channel = guild.get_channel(
                int(existing["channel_id"])
            )

            if channel:
                await interaction.response.send_message(
                    f"❌ You already have an open ticket: {channel.mention}",
                    ephemeral=True
                )
                return

            await db.execute(
                """
                UPDATE tickets
                SET status = 'closed'
                WHERE id = ?
                """,
                (existing["id"],),
                commit=True
            )

        staff_role = await self.get_staff_role(
            guild.id,
            category
        )

        if not staff_role:
            await interaction.response.send_message(
                "❌ This ticket category has not been configured yet.",
                ephemeral=True
            )
            return

        category_channel = discord.utils.get(
            guild.categories,
            name="Tickets"
        )

        if not category_channel:
            category_channel = await guild.create_category(
                "Tickets"
            )

        safe_name = (
            user.name.lower()
            .replace(" ", "-")
            .replace("_", "-")
        )

        channel_name = f"{category}-{safe_name}"

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(
                view_channel=False
            ),
            user: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                attach_files=True,
                embed_links=True
            ),
            staff_role: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                manage_messages=True
            ),
            guild.me: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                manage_channels=True,
                manage_messages=True
            )
        }

        channel = await guild.create_text_channel(
            channel_name,
            category=category_channel,
            overwrites=overwrites,
            topic=(
                f"KYŌKA ticket | "
                f"User: {user.id} | "
                f"Category: {category}"
            )
        )

        await db.execute(
            """
            INSERT INTO tickets
            (
                guild_id,
                channel_id,
                user_id,
                category,
                status,
                created_at,
                last_activity
            )
            VALUES (?, ?, ?, ?, 'open', ?, ?)
            """,
            (
                guild.id,
                channel.id,
                user.id,
                category,
                datetime.now(timezone.utc).isoformat(),
                datetime.now(timezone.utc).isoformat()
            ),
            commit=True
        )

        embed = discord.Embed(
            title=f"🎫 {category.title()} Ticket",
            description=(
                f"Welcome {user.mention}!\n\n"
                f"A member of {staff_role.mention} will assist you shortly.\n\n"
                "Please explain your issue clearly and provide "
                "any useful information."
            ),
            color=discord.Color.blurple()
        )

        await channel.send(
            content=f"{user.mention} {staff_role.mention}",
            embed=embed,
            view=TicketControlView(self)
        )

        await interaction.response.send_message(
            f"✅ Ticket created: {channel.mention}",
            ephemeral=True
        )

    # =========================================================
    # CLAIM
    # =========================================================

    async def claim_ticket(
        self,
        interaction: discord.Interaction
    ):
        if not interaction.channel:
            return

        ticket = await db.fetchone(
            """
            SELECT *
            FROM tickets
            WHERE channel_id = ?
            AND status = 'open'
            """,
            (interaction.channel.id,)
        )

        if not ticket:
            await interaction.response.send_message(
                "❌ This isn't an active ticket.",
                ephemeral=True
            )
            return

        staff_role = await self.get_staff_role(
            interaction.guild.id,
            ticket["category"]
        )

        if not staff_role or staff_role not in interaction.user.roles:
            await interaction.response.send_message(
                "❌ You don't have the ticket staff role.",
                ephemeral=True
            )
            return

        await db.execute(
            """
            UPDATE tickets
            SET claimed_by = ?, last_activity = ?
            WHERE channel_id = ?
            """,
            (
                interaction.user.id,
                datetime.now(timezone.utc).isoformat(),
                interaction.channel.id
            ),
            commit=True
        )

        await interaction.response.send_message(
            embed=success(
                f"🙋 Ticket claimed by {interaction.user.mention}."
            )
        )

    # =========================================================
    # CLOSE
    # =========================================================

    async def close_ticket(
        self,
        interaction: discord.Interaction
    ):
        ticket = await db.fetchone(
            """
            SELECT *
            FROM tickets
            WHERE channel_id = ?
            AND status = 'open'
            """,
            (interaction.channel.id,)
        )

        if not ticket:
            await interaction.response.send_message(
                "❌ This ticket is already closed.",
                ephemeral=True
            )
            return

        await db.execute(
            """
            UPDATE tickets
            SET status = 'closed',
                closed_by = ?,
                closed_at = ?,
                last_activity = ?
            WHERE channel_id = ?
            """,
            (
                interaction.user.id,
                datetime.now(timezone.utc).isoformat(),
                datetime.now(timezone.utc).isoformat(),
                interaction.channel.id
            ),
            commit=True
        )

        await interaction.channel.set_permissions(
            interaction.guild.default_role,
            view_channel=False
        )

        member = interaction.guild.get_member(
            int(ticket["user_id"])
        )

        if member:
            await interaction.channel.set_permissions(
                member,
                view_channel=False
            )

        await interaction.response.send_message(
            embed=success(
                "🔒 Ticket closed.\n"
                "Use the **Reopen** button if it needs to be reopened."
            )
        )

    # =========================================================
    # REOPEN
    # =========================================================

    async def reopen_ticket(
        self,
        interaction: discord.Interaction
    ):
        ticket = await db.fetchone(
            """
            SELECT *
            FROM tickets
            WHERE channel_id = ?
            """,
            (interaction.channel.id,)
        )

        if not ticket:
            await interaction.response.send_message(
                "❌ Ticket information wasn't found.",
                ephemeral=True
            )
            return

        staff_role = await self.get_staff_role(
            interaction.guild.id,
            ticket["category"]
        )

        member = interaction.guild.get_member(
            int(ticket["user_id"])
        )

        if member:
            await interaction.channel.set_permissions(
                member,
                view_channel=True,
                send_messages=True,
                read_message_history=True
            )

        if staff_role:
            await interaction.channel.set_permissions(
                staff_role,
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                manage_messages=True
            )

        await db.execute(
            """
            UPDATE tickets
            SET status = 'open',
                last_activity = ?
            WHERE channel_id = ?
            """,
            (
                datetime.now(timezone.utc).isoformat(),
                interaction.channel.id
            ),
            commit=True
        )

        await interaction.response.send_message(
            embed=success(
                "🔓 Ticket reopened."
            )
        )

    # =========================================================
    # ADD USER
    # =========================================================

    @commands.hybrid_command(
        name="ticketadd",
        description="Add a member to the current ticket."
    )
    @guild_only()
    async def ticketadd(
        self,
        ctx,
        member: discord.Member
    ):
        ticket = await db.fetchone(
            """
            SELECT *
            FROM tickets
            WHERE channel_id = ?
            AND status = 'open'
            """,
            (ctx.channel.id,)
        )

        if not ticket:
            await ctx.send(
                embed=error(
                    "This isn't an open ticket."
                )
            )
            return

        await ctx.channel.set_permissions(
            member,
            view_channel=True,
            send_messages=True,
            read_message_history=True
        )

        await ctx.send(
            embed=success(
                f"➕ Added {member.mention} to the ticket."
            )
        )

    # =========================================================
    # REMOVE USER
    # =========================================================

    @commands.hybrid_command(
        name="ticketremove",
        description="Remove a member from the current ticket."
    )
    @guild_only()
    async def ticketremove(
        self,
        ctx,
        member: discord.Member
    ):
        ticket = await db.fetchone(
            """
            SELECT *
            FROM tickets
            WHERE channel_id = ?
            AND status = 'open'
            """,
            (ctx.channel.id,)
        )

        if not ticket:
            await ctx.send(
                embed=error(
                    "This isn't an open ticket."
                )
            )
            return

        await ctx.channel.set_permissions(
            member,
            overwrite=None
        )

        await ctx.send(
            embed=success(
                f"➖ Removed {member.mention} from the ticket."
            )
        )

    # =========================================================
    # TRANSCRIPT
    # =========================================================

    async def send_transcript(
        self,
        interaction: discord.Interaction
    ):
        await interaction.response.defer(
            ephemeral=True
        )

        ticket = await db.fetchone(
            """
            SELECT *
            FROM tickets
            WHERE channel_id = ?
            """,
            (interaction.channel.id,)
        )

        if not ticket:
            await interaction.followup.send(
                "❌ Ticket information wasn't found.",
                ephemeral=True
            )
            return

        messages = []

        try:
            async for message in interaction.channel.history(
                limit=1000,
                oldest_first=True
            ):
                timestamp = message.created_at.strftime(
                    "%Y-%m-%d %H:%M:%S"
                )

                content = message.content

                if message.attachments:
                    attachments = " ".join(
                        attachment.url
                        for attachment in message.attachments
                    )

                    content = (
                        f"{content}\n"
                        f"Attachments: {attachments}"
                    )

                messages.append(
                    f"[{timestamp}] "
                    f"{message.author} ({message.author.id}): "
                    f"{content}"
                )

        except discord.Forbidden:
            await interaction.followup.send(
                "❌ I can't read the ticket history.",
                ephemeral=True
            )
            return

        if not messages:
            messages.append(
                "No messages were found."
            )

        transcript = "\n".join(messages)

        data = io.BytesIO(
            transcript.encode(
                "utf-8",
                errors="replace"
            )
        )

        file = discord.File(
            data,
            filename=f"ticket-{interaction.channel.id}.txt"
        )

        log_channel = await self.get_log_channel(
            interaction.guild.id
        )

        if log_channel:
            await log_channel.send(
                content=(
                    f"📄 Transcript for "
                    f"`{interaction.channel.name}`"
                ),
                file=file
            )

        await interaction.followup.send(
            "✅ Transcript generated.",
            file=discord.File(
                io.BytesIO(
                    transcript.encode(
                        "utf-8",
                        errors="replace"
                    )
                ),
                filename=f"ticket-{interaction.channel.id}.txt"
            ),
            ephemeral=True
        )

    # =========================================================
    # AUTO CLOSE
    # =========================================================

    @tasks.loop(minutes=10)
    async def auto_close_loop(self):
        try:
            rows = await db.fetchall(
                """
                SELECT *
                FROM tickets
                WHERE status = 'open'
                """
            )

            now = datetime.now(timezone.utc)

            for ticket in rows:
                last_activity = ticket["last_activity"]

                if not last_activity:
                    continue

                try:
                    last = datetime.fromisoformat(
                        last_activity
                    )

                    if last.tzinfo is None:
                        last = last.replace(
                            tzinfo=timezone.utc
                        )

                except ValueError:
                    continue

                # 7 days of inactivity
                if (now - last).total_seconds() < 7 * 86400:
                    continue

                guild = self.bot.get_guild(
                    int(ticket["guild_id"])
                )

                if not guild:
                    continue

                channel = guild.get_channel(
                    int(ticket["channel_id"])
                )

                if not channel:
                    await db.execute(
                        """
                        UPDATE tickets
                        SET status = 'closed'
                        WHERE channel_id = ?
                        """,
                        (ticket["channel_id"],),
                        commit=True
                    )
                    continue

                await db.execute(
                    """
                    UPDATE tickets
                    SET status = 'closed',
                        closed_at = ?
                    WHERE channel_id = ?
                    """,
                    (
                        now.isoformat(),
                        ticket["channel_id"]
                    ),
                    commit=True
                )

                try:
                    await channel.send(
                        "🔒 This ticket was automatically closed "
                        "after 7 days of inactivity."
                    )

                    await channel.set_permissions(
                        guild.default_role,
                        view_channel=False
                    )

                    member = guild.get_member(
                        int(ticket["user_id"])
                    )

                    if member:
                        await channel.set_permissions(
                            member,
                            view_channel=False
                        )

                except discord.HTTPException:
                    pass

        except Exception as exc:
            print(
                f"[KYŌKA] Ticket auto-close error: "
                f"{type(exc).__name__}: {exc}"
            )

    @auto_close_loop.before_loop
    async def before_auto_close(self):
        await self.bot.wait_until_ready()

    # =========================================================
    # ACTIVITY TRACKING
    # =========================================================

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        if not message.guild:
            return

        ticket = await db.fetchone(
            """
            SELECT *
            FROM tickets
            WHERE channel_id = ?
            AND status = 'open'
            """,
            (message.channel.id,)
        )

        if not ticket:
            return

        await db.execute(
            """
            UPDATE tickets
            SET last_activity = ?
            WHERE channel_id = ?
            """,
            (
                datetime.now(timezone.utc).isoformat(),
                message.channel.id
            ),
            commit=True
        )


async def setup(bot):
    # Persistent panel/control views
    bot.add_view(
        TicketPanelView(
            None
        )
    )

    cog = Tickets(bot)

    # Replace the temporary panel view with the real cog.
    bot.add_view(
        TicketPanelView(
            cog
        )
    )

    bot.add_view(
        TicketControlView(
            cog
        )
    )

    await bot.add_cog(cog)
