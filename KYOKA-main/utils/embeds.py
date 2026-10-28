import discord

from config import BOT_NAME, VERSION


def base_embed(
    title: str = None,
    description: str = None,
    color: discord.Color = None
) -> discord.Embed:
    """Create a standard KYŌKA embed."""

    embed = discord.Embed(
        title=title,
        description=description,
        color=color or discord.Color.blurple(),
        timestamp=discord.utils.utcnow()
    )

    embed.set_footer(
        text=f"{BOT_NAME} • v{VERSION}"
    )

    return embed


def success(
    title: str = "Success",
    description: str = None
) -> discord.Embed:
    return base_embed(
        title=title,
        description=description,
        color=discord.Color.green()
    )


def error(
    title: str = "Error",
    description: str = None
) -> discord.Embed:
    return base_embed(
        title=title,
        description=description,
        color=discord.Color.red()
    )


def warning(
    title: str = "Warning",
    description: str = None
) -> discord.Embed:
    return base_embed(
        title=title,
        description=description,
        color=discord.Color.orange()
    )


def info(
    title: str = "Information",
    description: str = None
) -> discord.Embed:
    return base_embed(
        title=title,
        description=description,
        color=discord.Color.blue()
    )


def premium(
    title: str = "KYŌKA Premium",
    description: str = None
) -> discord.Embed:
    return base_embed(
        title=title,
        description=description,
        color=discord.Color.gold()
    )


def creator(
    title: str = "Creator",
    description: str = None
) -> discord.Embed:
    return base_embed(
        title=title,
        description=description,
        color=discord.Color.dark_red()
    )


def set_author(
    embed: discord.Embed,
    user: discord.abc.User
) -> discord.Embed:
    """Add a Discord user's identity to an embed."""

    embed.set_author(
        name=str(user),
        icon_url=user.display_avatar.url
    )

    return embed


def add_user_footer(
    embed: discord.Embed,
    user: discord.abc.User
) -> discord.Embed:
    """Add the user's name to the footer."""

    embed.set_footer(
        text=f"{BOT_NAME} • Requested by {user}"
    )

    return embed
