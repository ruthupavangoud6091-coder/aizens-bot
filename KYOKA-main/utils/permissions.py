import discord

from config import OWNER_ID


def is_creator(user: discord.abc.User) -> bool:
    """Check if the user is the KYŌKA creator."""
    return user.id == OWNER_ID


def is_admin(member: discord.Member) -> bool:
    """Check Discord Administrator permission."""
    return member.guild_permissions.administrator


def is_moderator(member: discord.Member) -> bool:
    """Check common moderation permissions."""
    permissions = member.guild_permissions

    return any([
        permissions.administrator,
        permissions.manage_guild,
        permissions.manage_messages,
        permissions.kick_members,
        permissions.ban_members,
        permissions.moderate_members,
    ])


def can_manage_messages(member: discord.Member) -> bool:
    return (
        member.guild_permissions.administrator
        or member.guild_permissions.manage_messages
    )


def can_manage_members(member: discord.Member) -> bool:
    return (
        member.guild_permissions.administrator
        or member.guild_permissions.kick_members
        or member.guild_permissions.ban_members
        or member.guild_permissions.moderate_members
    )


def can_manage_roles(member: discord.Member) -> bool:
    return (
        member.guild_permissions.administrator
        or member.guild_permissions.manage_roles
    )


def can_manage_channels(member: discord.Member) -> bool:
    return (
        member.guild_permissions.administrator
        or member.guild_permissions.manage_channels
    )


def can_manage_guild(member: discord.Member) -> bool:
    return (
        member.guild_permissions.administrator
        or member.guild_permissions.manage_guild
    )


def is_bot(member: discord.abc.User) -> bool:
    return getattr(member, "bot", False)


def same_or_higher_role(
    member: discord.Member,
    target: discord.Member
) -> bool:
    """Check whether member's highest role is >= target's highest role."""
    if member.guild.id != target.guild.id:
        return False

    return member.top_role >= target.top_role


def can_act_on(
    actor: discord.Member,
    target: discord.Member
) -> bool:
    """
    Check whether actor can moderate target.

    The server owner and KYŌKA creator cannot be moderated
    through normal moderation commands.
    """

    if target.id == actor.guild.owner_id:
        return False

    if target.id == OWNER_ID:
        return False

    if target.id == actor.id:
        return False

    if target.top_role >= actor.top_role:
        return False

    return True
