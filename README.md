# black-hole

black-hole is a configurable XMPP ↔ Discord bridge written in Python 3.6.

It uses Discord.py and aioxmpp.

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
  - jid: 'general@muc.xmpp.server' # The JID of the MUC itself.

    # The nickname to use when joining the MUC.
    nick: 'black hole'

    # The webhook URL to post to.
    # This webhook should be on the same channel as the channel specified in
    # `channel_id`.
    webhook: 'https://discordapp.com/api/webhooks/...'

    # The linked Discord channel. This won't be used to mirror messages from
    # the MUC. Instead, it will be used to receive messages being sent in this
    # channel and mirror them to the MUC.
    channel_id: 123456789012345678

    # Log any message sent in the MUC to stdout.
    # log: true

    # Log any message sent in the linked Discord channel to stdout.
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
