import asyncio
from pyrogram import Client
from pyrogram.enums import ChatMembersFilter
from pyrogram.errors import FloodWait, ChannelPrivate, ChatAdminRequired


async def scrape_members(client: Client, group: str, limit: int = 0,
                         filter_type: str = "all", keyword: str = "") -> list[dict]:
    """
    Scrape members from a group/channel.
    filter_type: all, recent, admins, bots
    keyword: filter by name/username substring
    """
    members = []
    chat_filter = {
        "recent": ChatMembersFilter.RECENT,
        "admins": ChatMembersFilter.ADMINISTRATORS,
        "bots": ChatMembersFilter.BOTS,
    }.get(filter_type)

    try:
        count = 0
        if chat_filter:
            iter_ = client.get_chat_members(group, filter=chat_filter)
        else:
            iter_ = client.get_chat_members(group)

        async for member in iter_:
            user = member.user
            if user.is_deleted:
                continue

            entry = {
                "user_id": user.id,
                "first_name": user.first_name or "",
                "last_name": user.last_name or "",
                "username": user.username or "",
                "phone": user.phone_number or "",
                "is_bot": user.is_bot,
                "status": str(member.status).split(".")[-1] if member.status else "",
            }

            if keyword:
                haystack = f"{entry['first_name']} {entry['last_name']} {entry['username']}".lower()
                if keyword.lower() not in haystack:
                    continue

            members.append(entry)
            count += 1
            if limit and count >= limit:
                break

    except FloodWait as e:
        await asyncio.sleep(e.value)
        raise
    except (ChannelPrivate, ChatAdminRequired) as e:
        raise ValueError(str(e))

    return members


async def join_group(client: Client, group: str) -> dict:
    """Join a group/channel by username or invite link."""
    try:
        if "joinchat" in group or group.startswith("+"):
            chat = await client.join_chat(group)
        else:
            chat = await client.join_chat(group.lstrip("@"))
        return {"ok": True, "chat_id": chat.id, "title": chat.title}
    except FloodWait as e:
        await asyncio.sleep(e.value)
        raise
    except Exception as e:
        return {"ok": False, "error": str(e)}
