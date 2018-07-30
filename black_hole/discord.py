__all__ = ['Discord']

import asyncio
import logging

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

    def resolve_avatar(self, member):
        mappings = self.config['discord'].get('jid_map', {})
        user_id = mappings.get(str(member.direct_jid))
        user = self.client.get_user(user_id)

        if not user:
            return None

        return user.avatar_url_as(format='png')

    async def bridge(self, room, msg, member, source):
        """Add a MUC message to the queue to be processed."""
        content = msg.body.any()
        nick = member.nick

        if len(content) > 1900:
            content = content[:1900] + '... (trimmed)'

        payload = {
            'username': nick,
            'content': clean_content(content),
            'avatar_url': self.resolve_avatar(member),
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
            except aiohttp.ClientError:
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
