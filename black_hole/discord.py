__all__ = ['Discord']

import asyncio
import logging
import time

import aiohttp
from discord.ext import commands

from .management import Management
from .utils import clean_content

log = logging.getLogger(__name__)

class Discord:
    """A wrapper around a Discord client that mirrors XMPP messages to a room's
    configured webhook.
    """

    def __init__(self, *, config):
        self.config = config
        self.client = commands.Bot(command_prefix=commands.when_mentioned)
        self.client.add_cog(Management(self.client, self.config))
        self.session = aiohttp.ClientSession(loop=self.client.loop)

        self.client.loop.create_task(self._sender())

        self._queue = []
        self._incoming = asyncio.Event()

        #: { int: (timestamp, str) }
        self._avatar_cache = {}

    async def _get_from_cache(self, user_id: int) -> str:
        """Get an avatar in cache."""

        # if we insert anything into the cache, invalidation_ts
        # represents when that value will become invalidated.

        # it uses time.monotonic() because the monotonic clock
        # is way more stable than the general clock.
        current = time.monotonic()

        # the default is 30 minutes when not provided
        cache_period = self.config['discord'].get('avatar_cache', 80 * 60)

        invalidation_ts = current + cache_period

        value = self._avatar_cache.get(user_id)

        if value is None:
            # try get_user_info, which has a 1/1 ratelimit.
            # since it has that low of a ratelimit we cache
            # the resulting avatar url internally for 30 minutes.
            user = await self.client.get_user_info(user_id)

            # user not found, write that in cache so we don't need
            # to keep checking later on.
            if user is None:
                self._avatar_cache[user_id] = (invalidation_ts, None)
                return None

            # user found, store its avatar url in cache and return it
            avatar_url = user.avatar_url_as(format='png')
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

    async def resolve_avatar(self, member) -> str:
        """Resolve an avatar url, given a XMPP member.

        This caches the given avatar url for a set period of time.
        """
        mappings = self.config['discord'].get('jid_map', {})
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
            return user.avatar_url_as(format='png')

        return await self._get_from_cache(user_id)

    async def bridge(self, room, msg, member, source):
        """Add a MUC message to the queue to be processed."""
        content = msg.body.any()
        nick = member.nick

        if len(content) > 1900:
            content = content[:1900] + '... (trimmed)'

        payload = {
            'username': nick,
            'content': clean_content(content),
            'avatar_url': await self.resolve_avatar(member),
        }

        log.debug('adding message to queue')

        # add this message to the queue
        self._queue.append({
            'webhook_url': room.config['webhook'],
            'payload': payload,
        })

        self._incoming.set()

    async def _send_all(self):
        """Send all pending webhook messages."""
        log.debug('working on %d jobs...', len(self._queue))
        for job in self._queue:
            try:
                await self.session.post(job['webhook_url'], json=job['payload'])
                await asyncio.sleep(self.config['discord'].get('delay', 0.25))
            except (discord.DiscordException, aiohttp.ClientError):
                log.exception('failed to bridge content')
        self._queue.clear()
        self._incoming.clear()

    async def _sender(self):
        while True:
            log.debug('waiting for messages...')
            await self._incoming.wait()

            log.debug('emptying queue')
            await self._send_all()

    async def boot(self):
        log.info('connecting to discord...')
        await self.client.start(self.config['discord']['token'])
