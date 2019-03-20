"""This module exposes a Cog that can be added to Discord.py bots.

It allows management of the JID map.
"""

__all__ = ['Management']

import discord
from discord.ext import commands
from ruamel.yaml import YAML


def managers_only():
    def predicate(ctx):
        return ctx.author.id in ctx.cog.config['discord'].get('managers', [])
    return commands.check(predicate)


class Management(commands.Cog):
    def __init__(self, bot, config):
        self.bot = bot
        self.config = config

    def save_config(self):
        yaml = YAML(typ='safe')
        yaml.default_flow_style = False
        with open('config.yaml', 'w') as fp:
            yaml.dump(self.config, fp)

    @commands.group(name='rooms', aliases=['room'])
    @managers_only()
    async def rooms_group(self, ctx):
        """Manages rooms."""

    @rooms_group.command(name='toggle')
    async def rooms_toggle(self, ctx, room_jid=None):
        """Toggles a room from being bridged both ways."""
        if not room_jid and ctx.guild:
            room_jid = discord.utils.find(
                lambda room: room['channel_id'] == ctx.channel.id,
                self.config['rooms']
            )['jid']

        room = discord.utils.find(
            lambda room: room['jid'] == room_jid,
            self.config['rooms']
        )

        if not room:
            await ctx.send('MUC not found.')
            return

        room['disabled'] = not room.get('disabled', False)
        state = 'disabled' if room['disabled'] else 'enabled'
        await ctx.send(
            f'\N{CRAB} Bridging to and from {room_jid} is now {state}.'
        )
        self.save_config()

    @commands.group(name='jid')
    @managers_only()
    async def jid_group(self, ctx):
        """Manage the JID map."""

    @jid_group.command(name='list', aliases=['show'])
    async def jid_list(self, ctx):
        """Show the entire JID map."""
        formatted = ', '.join(map(
            lambda entry: f'{entry[0]} → {entry[1]}',
            self.config['discord']['jid_map'].items()
        ))
        if len(formatted) > 2000:
            await ctx.send('The JID map is too big.')
            return
        await ctx.send(formatted)

    @jid_group.command(name='set', aliases=['add'])
    async def jid_set(self, ctx, jid: commands.clean_content,
                      member: discord.Member):
        """Assign a JID to a Discord user."""
        self.config['discord']['jid_map'][jid] = member.id
        self.save_config()
        await ctx.send(f'\N{MEMO} {jid} → {member.id}')

    @jid_group.command(name='delete', aliases=['del', 'rm'])
    async def jid_delete(self, ctx, jid: commands.clean_content):
        """Delete a JID from the JID map."""
        try:
            del self.config['discord']['jid_map'][jid]
        except KeyError:
            pass
        self.save_config()
        await ctx.send(f'\N{BOMB} {jid}')
