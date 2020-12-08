__all__ = ["Discord"]

import asyncio
import logging
import time
from typing import Optional

import aiohttp
from discord.ext import commands
from discord import DiscordException, Intents
from expiringdict import ExpiringDict

from .management import Management
from .utils import clean_content

log = logging.getLogger(__name__)


def ensure_valid_nick(nick: str) -> str:
    """Ensure that a nickname from XMPP is valid to be used as a webhook
    username in Discord.
    """
    if len(nick) < 2:
        return f"<{nick}>"
    if len(nick) > 32:
        return nick[:32]
    return nick


class Discord:
    """A wrapper around a Discord client that mirrors XMPP messages to a room's
    configured webhook.
    """

    def __init__(self, *, config):
        self.config = config
        intents = Intents.default()

        # members intent is required to resolve discord.User/discord.Member
        # on command parameters
        intents.members = True
        intents.typing = False

        self.client = commands.Bot(
            intents=intents, command_prefix=commands.when_mentioned
        )
        self.client.add_cog(Management(self.client, self.config))
        self.session = aiohttp.ClientSession(loop=self.client.loop)

        self.client.loop.create_task(self._sender())

        self._queue = []
        self._incoming = asyncio.Event()

        #: { int: (timestamp, str) }
        self._avatar_cache = {}

        #: { (jid, xmpp_message_id): discord_message_id }
        # the message id store serves as a way for edited messages coming
        # from a xmpp room to have the edit reflected on the discord channel.
        #
        # the high level overview is as follows:
        #  when sending a message, check if its an edit and the edited id exists in the cache
        #   if so, issue a patch (since we have the webhook url AND message id)
        #   if not, issue a post, and store the message id for later
        #
        # the store has a maximum of 1k messages, and lets an xmpp message
        # be last corrected for an hour
        self._message_id_store = ExpiringDict(max_len=1000, max_age_seconds=3600)

    async def _get_from_cache(self, user_id: int) -> Optional[str]:
        """Get an avatar in cache."""

        # if we insert anything into the cache, invalidation_ts
        # represents when that value will become invalidated.

        # it uses time.monotonic() because the monotonic clock
        # is way more stable than the general clock.
        current = time.monotonic()

        # the default is 30 minutes when not provided
        cache_period = self.config["discord"].get("avatar_cache", 80 * 60)

        invalidation_ts = current + cache_period

        value = self._avatar_cache.get(user_id)

        if value is None:
            # try get_user_info, which has a 1/1 ratelimit.
            # since it has that low of a ratelimit we cache
            # the resulting avatar url internally for 30 minutes.
            user = await self.client.fetch_user(user_id)

            # user not found, write that in cache so we don't need
            # to keep checking later on.
            if user is None:
                self._avatar_cache[user_id] = (invalidation_ts, None)
                return None

            # user found, store its avatar url in cache and return it
            avatar_url = user.avatar_url_as(format="png")
            self._avatar_cache[user_id] = (invalidation_ts, avatar_url)
            return avatar_url

        user_ts, avatar_url = value

        # if the user cache value is invalid,
        # we recall _get_from_cache with the given user id deleted
        # so that it calls get_user_info and writes the new data
        # to cache.
        if current > user_ts:
            self._avatar_cache.pop(user_id)
            return await self._get_from_cache(user_id)

        return avatar_url

    async def resolve_avatar(self, member) -> Optional[str]:
        """Resolve an avatar url, given a XMPP member.

        This caches the given avatar url for a set period of time.
        """
        mappings = self.config["discord"].get("jid_map", {})
        user_id = mappings.get(str(member.direct_jid))

        # if nothing on the map, there isn't a need
        # to check our caches
        if user_id is None:
            return None

        user = self.client.get_user(user_id)

        # if the user is already in the client's cache,
        # we use it (it will also be better updated
        # due to USER_UPDATE events)
        if user is not None:
            return str(user.avatar_url_as(format="png"))

        return await self._get_from_cache(user_id)

    async def bridge(self, room, msg, member, source):
        """Add a MUC message to the queue to be processed."""
        content = msg.body.any()

        if len(content) > 1900:
            content = content[:1900] + "... (trimmed)"

        payload = {
            "username": ensure_valid_nick(member.nick),
            "content": clean_content(content),
            "avatar_url": await self.resolve_avatar(member),
        }

        log.debug("adding message to queue")

        # incoming messages that aren't edits have the attribute set to None
        original_xmpp_message_id = (
            None if msg.xep0308_replace is None else msg.xep0308_replace.id_
        )

        # add this message to the queue (processed later by _send_all)
        self._queue.append(
            {
                "author_jid": str(member.direct_jid),
                "xmpp_message_id": msg.id_,
                "original_xmpp_message_id": original_xmpp_message_id,
                "webhook_url": room.config["webhook"],
                "payload": payload,
            }
        )

        self._incoming.set()

    async def _send_all(self):
        """Send all pending webhook messages."""
        log.debug("working on %d jobs...", len(self._queue))
        for job in self._queue:
            xmpp_message_id: Optional[str] = job["xmpp_message_id"]
            original_xmpp_message_id: Optional[str] = job["original_xmpp_message_id"]

            # key used to write to the store
            store_key = (job["author_jid"], xmpp_message_id)

            # key used to lookup the message (as the replace message has a different id,
            # using upstream_message_id directly would always yield non-hits to the
            # message id store)
            lookup_key = (job["author_jid"], original_xmpp_message_id)
            webhook_url = job["webhook_url"]
            resp = None

            try:
                # by checking if original id is none or not beforehand, we
                # prevent unecessary lookups in the message store
                if (
                    original_xmpp_message_id is not None
                    and lookup_key in self._message_id_store
                ):
                    discord_message_id = self._message_id_store[lookup_key]
                    resp = await self.session.patch(
                        f"{webhook_url}/messages/{discord_message_id}",
                        json=job["payload"],
                        params={"wait": "true"},
                    )
                else:
                    resp = await self.session.post(
                        webhook_url, json=job["payload"], params={"wait": "true"}
                    )
            except Exception:
                log.exception("failed to bridge content")

                # if we failed to bridge for any reason (not just the network)
                # on this piece of code (even though the network is the most
                # likely cause), we skip the job, and go to the next one.
                continue

            assert resp is not None
            await asyncio.sleep(self.config["discord"].get("delay", 0.25))

            if resp.status == 200:
                discord_message = await resp.json()
                if xmpp_message_id is not None:
                    self._message_id_store[store_key] = discord_message["id"]
            else:
                # by using wait=true, we basically force discord to always
                # give us 200. this means 204's are considered an error
                # condition

                try:
                    body = await resp.read()
                except Exception:
                    body = "<none>"

                log.warning(
                    "failed to bridge discord -> xmpp. status=%d, body=%r, payload=%r",
                    resp.status,
                    body,
                    job["payload"],
                )

        self._queue.clear()
        self._incoming.clear()

    async def _sender(self):
        while True:
            log.debug("waiting for messages...")
            await self._incoming.wait()

            log.debug("emptying queue")
            await self._send_all()

    async def boot(self):
        log.info("connecting to discord...")
        await self.client.start(self.config["discord"]["token"])
