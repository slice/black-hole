# black-hole

black-hole is a configurable XMPP ↔ Discord bridge written in Python 3.6.

It uses [Discord.py@rewrite] and [aioxmpp].

[Discord.py@rewrite]: http://discordpy.readthedocs.io/en/rewrite/index.html
[aioxmpp]: https://docs.zombofant.net/aioxmpp/devel/index.html

## Requirements

- Python 3.6+ (Tested on Python 3.7)

## Configuring

Here is a sample `config.yaml`:

```yaml
# XMPP credentials (JID and password).
xmpp:
  jid: 'bot@xmpp.server'
  password: 'ramen'

# black-hole supports multiple "rooms".
#
# The concept of a "room" in black-hole combines both a MUC and a Discord
# channel. They are linked together with a Discord bot, a Discord webhook,
# and a XMPP client.
rooms:
  - jid: 'general@muc.xmpp.server' # The JID of the MUC.

    # The MUC's password. Omit if password-less.
    # password: 'spicy ramen'

    # The nickname to use when joining the MUC.
    nick: 'black hole'

    # The webhook URL to post to. (MUC → Discord)
    webhook: 'https://discordapp.com/api/webhooks/...'

    # The Discord channel's ID. (Discord → MUC)
    channel_id: 123456789012345678

    # NOTE: The webhook should be pointing to the same channel as channel_id.

    # Log any message sent in the MUC to standard out.
    # log: true

    # Log any message sent in the linked Discord channel to standard out.
    # discord_log: true
discord:
  # Discord bot token, used to receive messages.
  token: 'NDU...'

  # A list of Discord user IDs that will be able to manage the bot from
  # Discord.
  managers:
    - 123
    - 456

  # A map of JIDs to Discord user IDs.
  #
  # Allows black-hole to specify the avatar URL of a JID's associated Discord
  # account when posting to the webhook.
  jid_map:
    'user_a@xmpp.server': 123
    'user_b@xmpp.server': 456
```

## Documentation

### Message Transport

Webhooks are used to transfer messages from the MUC to Discord. The Discord bot
listens for messages in the specified channel and transfers them to the MUC.

We use a webhook because it allows us to customize the "author" and avatar of
the posted message, which makes mirrored messages easier to read.

#### To Discord

##### Mentions

Any message travelling from MUC to Discord are stripped of mentions.

Any role or user mention (including @everyone and @here) are escaped/stripped
and do not mention anyone. Channel mentions are not, but you must send them in
"raw" format (like `<#123>`).

#### To MUC

##### Attachments

Any attachment URLs are appended to the end of the message.

##### Embeds

In the case of bots, the number of embeds present in the message is appended
to the end of the message.

##### Message Edits

When a message is edited on Discord, the edited version will be resent to the
MUC with an "(edited)" prefix. aioxmpp presumably has no [XEP-0308] support,
so we can't use it, and even if it did support it, it would still be quite
clunky due to the way the XEP works.

[XEP-0308]: https://xmpp.org/extensions/xep-0308.html

Any edits made on the MUC are not reflected on Discord.

### JID Map

The JID map allows the XMPP → Discord functionality to resolve the user's
avatar to be displayed through the webhook. It can be managed manually through
the config file or through the Discord bot.

#### Discord Management

Use these commands to manage the JID map from Discord:

```
# Map a JID to a Discord user. You can provide the user ID, mention, or a username.
@bot jid set <jid> <user>

# Deletes a JID from the JID map.
@bot jid del <jid>

# Shows the entire JID map.
@bot jid show
```

The `set` and `del` commands automatically save changes.
