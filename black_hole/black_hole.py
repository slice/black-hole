import asyncio
import logging

from .xmpp import XMPP
from .discord import Discord

__all__ = ['BlackHole']
log = logging.getLogger(__name__)


class BlackHole:
    """
    The main class that boots up an XMPP client and a Discord client, and handles
    message passing between the two.
    """

    def __init__(self, *, config):
        self.config = config

        self.loop = asyncio.get_event_loop()

        self.xmpp = XMPP(
            config['xmpp']['jid'],
            config['xmpp']['password'],
            config=config,
        )

        # register an event handler when we get a message from MUC rooms
        self.xmpp.on_message(self.on_message)

        self.discord = Discord(
            config=config
        )

        self.discord.client.add_on_message(self.on_discord_message)

    async def on_message(self, room, msg, member, source):
        """Called when a message in a MUC room is sent."""
        # directly bridge everything to discord
        await self.discord.bridge(room, msg, member, source)

    async def on_discord_message(self, client, message):
        """Called when a message in a discord"""
        # ignore messages from webhooks (which are very probably ourselves),
        # but not from bots
        if message.webhook_id is not None:
            return

        await self.xmpp.bridge(client, message)

    def run(self):
        log.info('booting services')
        self.loop.create_task(self.discord.boot())
        self.loop.create_task(self.xmpp.boot())

        try:
            self.loop.run_forever()
        except KeyboardInterrupt:
            log.info('stopping')
            self.xmpp.client.stop()
            self.loop.run_until_complete(self.discord.client.logout())
        finally:
            self.loop.close()

        log.debug('run() exit')
