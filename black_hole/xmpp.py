import asyncio
import logging
from collections import namedtuple

import aioxmpp
from discord.ext.commands import clean_content

from .room import Room

__all__ = ['XMPP']
log = logging.getLogger(__name__)

FakeContext = namedtuple('FakeContext', (
    'message',
    'guild',
    'bot'
))


async def fmt_discord(client, message) -> str:
    """Format a discord message into a string for XMPP."""
    cleaner = clean_content(use_nicknames=False)

    ctx = FakeContext(message, message.guild, client)
    content = await cleaner.convert(ctx, message.content)
    return f'[discord] <{message.author}> {content}'


class XMPP:
    """Abstraction layer over aioxmpp."""

    def __init__(self, jid: str, password: str, *, config):
        self.config = config
        self.client = aioxmpp.PresenceManagedClient(
            aioxmpp.JID.fromstr(jid),
            aioxmpp.make_security_layer(password, no_verify=True),
        )
        self.muc = self.client.summon(aioxmpp.MUCClient)

        self.on_message_handlers = []

    @property
    def selectors(self):
        """Message selectors to use."""
        return [
            aioxmpp.structs.LanguageRange.fromstr('*'),
        ]

    def on_message(self, func):
        """A decorator that adds a handler to be called upon a message."""
        self.on_message_handlers.append(func)

    async def _handle_message(self, room, msg, member, source):
        """This method is called by :class:`blackhole.room.Room` instances."""
        for handler in self.on_message_handlers:
            await handler(room, msg, member, source)

    def join_rooms(self):
        """Joins all rooms as configured in the confuguration file.

        This is automatically called when we connect to XMPP through
        :meth:`boot_xmpp`.
        """
        rooms = self.config['rooms']
        for room_config in rooms:
            # Room needs a reference to self in order to call _handle_message
            room = Room(self, config=room_config)
            room.join(self.muc)

    async def bridge(self, client, message):
        """Take a discord message and send it over to the MUC."""
        rooms = self.config['rooms']

        if self.config['discord'].get('log', False):
            log.info('[discord] <%s> %s', message.author, message.content)

        for room_config in rooms:
            # skip rooms not configured for this message
            if room_config['channel_id'] != message.channel.id:
                continue

            # construct message
            reply = aioxmpp.Message(
                type_=aioxmpp.MessageType.GROUPCHAT,
                to=aioxmpp.JID.fromstr(room_config['jid']),
            )

            reply.body[None] = await fmt_discord(client, message)
            await self.client.send(reply)

    async def boot(self):
        log.info('connecting to xmpp...')

        async with self.client.connected() as stream:
            log.debug('obtained stream: %s', stream)

            self.join_rooms()

            while True:
                await asyncio.sleep(60)
