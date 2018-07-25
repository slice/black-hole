# black-hole

black-hole is a configurable XMPP to Discord bridge.

## Configuring

Here is a sample `config.yaml`:

```yaml
xmpp:
  jid: 'bot@xmpp.server'
  password: 'ramen'
rooms:
  - jid: 'general@muc.xmpp.server'
    nick: 'black-hole'
    webhook: 'https://discordapp.com/api/webhooks/...'
    # Enable logging to stdout?
    # log: true
discord:
  token: 'NDU...'
  # Channel to gather messages from and
  # send them to the MUC
  channel_id: 123456789012345678
  # Enable logging to stdout?
  # log: true

  # A map of JIDs to Discord user IDs.
  #
  # Allows black-hole to specify the avatar URL of a JID's associated Discord
  # account when posting to the webhook.
  jid_map:
    'user_a@xmpp.server': 123
    'user_b@xmpp.server': 456
```
