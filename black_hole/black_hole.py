__all__ = ["BlackHole"]

import asyncio
import logging

from .xmpp import XMPP
from .discord import Discord

log = logging.getLogger(__name__)


class BlackHole:
    """The main class that boots up an XMPP client and a Discord client,
    and handles message passing between the two.
    """

    def __init__(self, *, config):
        self.config = config

        self.loop = asyncio.get_event_loop()

        self.xmpp = XMPP(
            config["xmpp"]["jid"],
            config["xmpp"]["password"],
            config=config,
        )

        # Register an event handler when we get a message from MUCs.
        self.xmpp.on_message(self.on_xmpp_message)

        self.discord = Discord(config=config)

        self.discord.client.add_listener(self.on_discord_message, "on_message")
        self.discord.client.add_listener(
            self.on_discord_message_edit, "on_message_edit"
        )

    async def on_xmpp_message(self, room, msg, member, source):
        """Bridge a MUC message to its Discord channel."""
        if room.config.get("disabled", False):
            return

        try:
            await self.discord.bridge(room, msg, member, source)
        except Exception:
            log.exception("failed to bridge a message from xmpp to discord")

    async def on_discord_message(self, message):
        """Bridge a Discord message to its MUC."""
        if message.webhook_id is not None:
            return

        try:
            await self.xmpp.bridge(self.discord.client, message)
        except Exception:
            log.exception("failed to bridge a message from discord to xmpp")

    async def on_discord_message_edit(self, before, after):
        if after.webhook_id is not None:
            return

        if before.content == after.content:
            # This message was edited in ways we don't care about, so let's not
            # bother bridging the edit.
            return

        try:
            await self.xmpp.bridge(self.discord.client, after, edited=True)
        except Exception:
            log.exception("failed to bridge an edit from discord to xmpp")

    def run(self):
        log.info("booting services")
        self.loop.create_task(self.discord.boot())
        self.loop.create_task(self.xmpp.boot())

        try:
            self.loop.run_forever()
        except KeyboardInterrupt:
            log.info("stopping")
            self.xmpp.client.stop()
            self.loop.run_until_complete(self.discord.client.logout())
        finally:
            self.loop.close()

        log.debug("run() exit")
