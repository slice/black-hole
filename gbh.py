import asyncio
import logging
import sys

import aiohttp
import aioxmpp
import discord
import toml

logging.basicConfig(level='INFO')
log = logging.getLogger('gajimbo.black-hole')


class GajimboBH:
    def __init__(self, jid, password, *, loop, config={}):
        self.loop = loop
        self.config = config

        self.jid = aioxmpp.JID.fromstr(jid)
        self.password = password

        self.selectors = [
            aioxmpp.structs.LanguageRange.fromstr('*'),
        ]

        self.session = aiohttp.ClientSession(loop=loop)
        self.discord = discord.Client()
        self.client = aioxmpp.PresenceManagedClient(
            self.jid,
            aioxmpp.make_security_layer(password, no_verify=True),
        )

    async def _version_xso_handler(self, iq):
        log.info('received iq request from %s', iq.from_)
        iq = aioxmpp.version.xso.Query()
        iq.name = 'gajimbo black hole'
        iq.version = '0.0.0'
        iq.os = sys.platform
        return iq

    async def _handle_message(self, msg):
        log.info('>>> %s', msg)

    def _register(self):
        messages = self.client.summon(aioxmpp.dispatcher.SimpleMessageDispatcher)
        messages.register_callback(aioxmpp.MessageType.CHAT, None, self._handle_message)

        self.client.stream.register_iq_request_handler(
            aioxmpp.IQType.GET,
            aioxmpp.version.xso.Query,
            self._version_xso_handler,
        )

    def resolve_avatar(self, nick):
        mappings = self.config['discord'].get('mappings', {})
        user_id = mappings.get(nick)
        if user_id:
            user = self.discord.get_user(user_id)
        else:
            user = discord.utils.get(self.discord.users, name=nick)

        if not user:
            return None
        return user.avatar_url_as(format='png')

    def _clean_content(self, content):
        return content \
            .replace('@everyone', '@\u200beveryone') \
            .replace('@here', '@\u200bhere') \
            .replace('<@', '<\u200b@')

    async def _bridge(self, nick, content):
        url = self.config['discord']['webhook']
        payload = {
            'username': nick,
            'content': self._clean_content(content),
            'avatar_url': self.resolve_avatar(nick),
        }

        try:
            await self.session.post(url, json=payload)
        except aiohttp.ClientError:
            log.exception('failed to bridge content')

    def _on_muc_message(self, msg, member, source, **kwargs):
        nick = member.nick
        content = msg.body.lookup(self.selectors)

        if self.config.get('muc', {}).get('log', False):
            log.info('<%s> %s', member.direct_jid, content)

        self.loop.create_task(self._bridge(member, content))

    def _join_mucs(self):
        muc = self.client.summon(aioxmpp.MUCClient)

        muc_config = self.config.get('muc', {})
        nick = muc_config.get('nick', 'gajimbo')
        room_names = muc_config.get('rooms', [])
        server = muc_config.get('server')

        if not server or not room_names:
            log.warn('not connecting to mucs, not setup')
            return

        for room_name in room_names:
            log.info('joining %s at %s', room_name, server)
            room, fut = muc.join(
                aioxmpp.JID.fromstr(
                    f'{room_name}@{server}'
                ),
                nick,
                history=aioxmpp.muc.xso.History(maxstanzas=0),
            )
            room.on_message.connect(self._on_muc_message)

    def _set_presence(self):
        self.client.set_presence(
            aioxmpp.PresenceState(available=True, show=aioxmpp.PresenceShow.CHAT),
            'absorbing matter',
        )

    async def _boot_discord(self):
        log.info('connecting to discord...')
        await self.discord.start(self.config['discord']['token'])

    async def _boot_xmpp(self):
        log.info('connecting to xmpp...')
        async with self.client.connected() as stream:
            log.info('obtained stream: %s', stream)
            self._register()
            self._set_presence()
            self._join_mucs()

            while True:
                await asyncio.sleep(60)

    def run(self):
        log.info('booting services')
        self.loop.create_task(self._boot_xmpp())
        self.loop.create_task(self._boot_discord())
        try:
            self.loop.run_forever()
        except KeyboardInterrupt:
            log.info('*** stopping ***')
            self.client.stop()
            self.loop.run_until_complete(self.discord.logout())
        finally:
            self.loop.close()
        log.info('run() exit')


if __name__ == '__main__':
    config = toml.load('config.toml')
    jid = config['xmpp']['jid']

    log.info('using jid: %s', jid)
    log.info('connecting...')

    gbh = GajimboBH(
        jid,
        config['xmpp']['password'],
        loop=asyncio.get_event_loop(),
        config=config,
    )
    gbh.run()
