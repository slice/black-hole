import logging

import aiohttp
import discord

from .utils import clean_content

__all__ = ['Discord']
log = logging.getLogger(__name__)


class DiscordClient(discord.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.message_handlers = []

    def add_on_message(self, callback):
        self.message_handlers.append(callback)

    async def on_message(self, message):
        for handler in self.message_handlers:
            await handler(message)


class Discord:
    """
    A wrapper around a Discord client that mirrors XMPP messages to a room's
    configured webhook.
    """

    def __init__(self, *, config):
        self.config = config
        self.client = DiscordClient()
        self.session = aiohttp.ClientSession(loop=self.client.loop)

    def resolve_avatar(self, member):
        mappings = self.config['discord'].get('jid_map', {})
        user_id = mappings.get(str(member.direct_jid))
        user = self.client.get_user(user_id)

        if not user:
            return None

        return user.avatar_url_as(format='png')

    async def bridge(self, room, msg, member, source):
        """POSTs to a room's webhook URL."""
        content = msg.body.any()
        nick = member.nick

        if len(content) > 1900:
            content = content[:1900] + '... (trimmed)'

        payload = {
            'username': nick,
            'content': clean_content(content),
            'avatar_url': self.resolve_avatar(member),
        }

        try:
            webhook_url = room.config['webhook']
            await self.session.post(webhook_url, json=payload)
        except aiohttp.ClientError:
            log.exception('failed to bridge content')

    async def boot(self):
        log.info('connecting to discord...')
        await self.client.start(self.config['discord']['token'])
