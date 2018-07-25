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
