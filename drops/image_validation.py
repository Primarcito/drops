from pathlib import Path

import discord


MAX_PRIZE_IMAGE_BYTES = 10 * 1024 * 1024
IMAGE_EXTENSIONS = {
    ".gif": "gif",
    ".jpg": "jpg",
    ".jpeg": "jpg",
    ".png": "png",
    ".webp": "webp",
}
IMAGE_CONTENT_TYPES = {
    "image/gif": "gif",
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}


def drop_image_extension(attachment: discord.Attachment) -> str | None:
    content_type = (attachment.content_type or "").lower()
    if content_type in IMAGE_CONTENT_TYPES:
        return IMAGE_CONTENT_TYPES[content_type]

    suffix = Path(attachment.filename or "").suffix.lower()
    return IMAGE_EXTENSIONS.get(suffix)


def validate_drop_image(attachment: discord.Attachment) -> tuple[bool, str | None, str | None]:
    extension = drop_image_extension(attachment)
    if not extension:
        return False, None, "Sube una imagen PNG, JPG, WEBP o GIF."

    if attachment.size and attachment.size > MAX_PRIZE_IMAGE_BYTES:
        return False, None, "La imagen pesa demasiado. Usa una imagen de 10 MB o menos."

    return True, extension, None
