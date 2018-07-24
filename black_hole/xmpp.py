import asyncio
import logging

import aioxmpp

from .room import Room

__all__ = ['XMPP']
log = logging.getLogger(__name__)


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

    async def boot(self):
        log.info('connecting to xmpp...')

        async with self.client.connected() as stream:
            log.debug('obtained stream: %s', stream)

            self.join_rooms()

            while True:
                await asyncio.sleep(60)
