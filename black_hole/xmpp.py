__all__ = ["XMPP"]

import asyncio
import logging
from collections import namedtuple

import aioxmpp
import discord
from discord.ext.commands import clean_content

from .room import Room

log = logging.getLogger(__name__)

FakeContext = namedtuple("FakeContext", ("message", "guild", "bot"))


def extract_message_content(message: discord.Message) -> str:
    """Extract a message's content, along with any attachment URLs."""
    base_content = message.system_content

    if message.attachments:
        urls = " ".join(attachment.proxy_url for attachment in message.attachments)
        base_content += " " + urls

    if message.embeds:
        s = "" if len(message.embeds) == 1 else "s"
        base_content += f" ({len(message.embeds)} embed{s})"

    return base_content


async def format_discord_message(client, message: discord.Message) -> str:
    """Format a Discord message into a string for XMPP."""
    content = extract_message_content(message)

    # Clean any mentions from the message using the clean_content converter,
    # which is normally not supposed to be used in these circumstances (thus
    # requiring a fake Context class).
    cleaner = clean_content(use_nicknames=False)
    ctx = FakeContext(message, message.guild, client)
    content = await cleaner.convert(ctx, content)

    # If someone else in this channel has the same username as the author,
    # present the user's discriminator in the forwarded message as well as the
    # username.
    presented_name = message.author.name
    users = list(
        filter(lambda user: user.name == message.author.name, message.channel.members)
    )
    if len(users) > 1:
        presented_name = str(message.author)

    return f"<{presented_name}> {content}"


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
        rooms = self.config["rooms"]
        for room_config in rooms:
            # Room needs a reference to self in order to call _handle_message
            room = Room(self, config=room_config)
            room.join(self.muc)

    async def bridge(self, client, message, *, edited=False):
        """Take a discord message and send it over to the MUC."""
        room = discord.utils.find(
            lambda room: room["channel_id"] == message.channel.id, self.config["rooms"]
        )

        if not room or room.get("disabled", False):
            return

        if room.get("discord_log", False):
            content = extract_message_content(message)
            log.info("[discord] <%s> %s", message.author, content)

        reply = aioxmpp.Message(
            type_=aioxmpp.MessageType.GROUPCHAT,
            to=aioxmpp.JID.fromstr(room["jid"]),
        )

        formatted_content = await format_discord_message(client, message)

        if edited:
            formatted_content += " (edited)"

        reply.body[None] = formatted_content
        await self.client.send(reply)

    async def boot(self):
        log.info("connecting to xmpp...")

        async with self.client.connected() as stream:
            log.debug("obtained stream: %s", stream)

            self.join_rooms()

            while True:
                await asyncio.sleep(60)
