__all__ = ['Room']

import asyncio
import logging

import aioxmpp

log = logging.getLogger(__name__)


class Room:
    """An abstraction over :class:`aioxmpp.muc.Room`."""

    def __init__(self, xmpp, *, config):
        self.loop = asyncio.get_event_loop()
        self.xmpp = xmpp
        self.config = config
        self.room = None

    def _on_topic_changed(self, member, topic, *, nick=None, **kwargs):
        pass

    def _on_message(self, msg, member, source, **kwargs):
        if member == self.room.me:
            return

        content = msg.body.any()

        if self.config.get('log', False):
            log.info('[%s] <%s> %s', self.config['jid'], member.direct_jid, content)

        # Sent the message over to our parent XMPP class.
        self.loop.create_task(
            self.xmpp._handle_message(self, msg, member, source)
        )

    def join(self, muc):
        """Joins this room from a :class:`aioxmpp.MUCClient` using the configuration."""

        room, _future = muc.join(
            mucjid=aioxmpp.JID.fromstr(self.config['jid']),
            nick=self.config.get('nick', 'black-hole'),
            password=self.config.get('password'),
            history=aioxmpp.muc.xso.History(maxstanzas=0),
        )

        room.on_message.connect(self._on_message)
        room.on_topic_changed.connect(self._on_topic_changed)

        self.room = room
