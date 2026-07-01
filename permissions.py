import discord


def can_manage_drops(interaction: discord.Interaction) -> bool:
    permissions = getattr(interaction.user, "guild_permissions", None)
    if not permissions:
        return False
    return bool(
        permissions.administrator
        or permissions.manage_guild
        or permissions.manage_messages
    )

