import discord
from ruamel.yaml import YAML
from discord.ext import commands

__all__ = ['Management']


def managers_only():
    def predicate(ctx):
        cog = ctx.command.instance
        return ctx.author.id in cog.config['discord'].get('managers', [])
    return commands.check(predicate)


class Management:
    def __init__(self, bot, config):
        self.bot = bot
        self.config = config

    def save_config(self):
        yaml = YAML(typ='safe')
        yaml.default_flow_style = False
        with open('config.yaml', 'w') as fp:
            yaml.dump(self.config, fp)

    @commands.group(name='jid')
    @managers_only()
    async def jid_group(self, ctx):
        """Manages the JID map."""
        pass

    @jid_group.command(name='list', aliases=['show'])
    async def jid_list(self, ctx):
        """Shows the JID map."""
        formatted = ', '.join(map(
            lambda entry: f'{entry[0]} → {entry[1]}',
            self.config['discord']['jid_map'].items()
        ))
        if len(formatted) > 2000:
            await ctx.send('The JID map is too big.')
            return
        await ctx.send(formatted)

    @jid_group.command(name='set', aliases=['add'])
    async def jid_set(self, ctx, jid: commands.clean_content, member: discord.Member):
        """Assigns a JID to a Discord user."""
        self.config['discord']['jid_map'][jid] = member.id
        self.save_config()
        await ctx.send(f'\N{MEMO} {jid} → {member.id}')

    @jid_group.command(name='delete', aliases=['del', 'rm'])
    async def jid_delete(self, ctx, jid: commands.clean_content):
        """Deletes a JID from the JID map."""
        try:
            del self.config['discord']['jid_map'][jid]
        except KeyError:
            pass
        self.save_config()
        await ctx.send(f'\N{BOMB} {jid}')
