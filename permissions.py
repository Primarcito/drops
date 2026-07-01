import os

import discord


def _split_env_list(name: str) -> set[str]:
    raw = os.getenv(name, "")
    return {item.strip() for item in raw.split(",") if item.strip()}


DEFAULT_DROP_ADMIN_ROLE_IDS = {
    "1473624624964173952",
    "1336825861466488975",
    "983987481961717782",
}

DROP_ADMIN_ROLE_IDS = DEFAULT_DROP_ADMIN_ROLE_IDS | _split_env_list("DROP_ADMIN_ROLE_IDS")
DROP_ADMIN_ROLE_NAMES = {name.lower() for name in _split_env_list("DROP_ADMIN_ROLE_NAMES")}


def has_drop_admin_role(member) -> bool:
    roles = getattr(member, "roles", []) or []
    for role in roles:
        if str(getattr(role, "id", "")) in DROP_ADMIN_ROLE_IDS:
            return True
        if getattr(role, "name", "").lower() in DROP_ADMIN_ROLE_NAMES:
            return True
    return False


def can_manage_drops(interaction: discord.Interaction) -> bool:
    if has_drop_admin_role(interaction.user):
        return True

    permissions = getattr(interaction.user, "guild_permissions", None)
    if not permissions:
        return False
    return bool(
        permissions.administrator
        or permissions.manage_guild
        or permissions.manage_messages
    )


def can_manage_drop_participants(interaction: discord.Interaction) -> bool:
    return has_drop_admin_role(interaction.user)
