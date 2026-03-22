---
sidebar_position: 1
---

# Deploy a Slack Bot

Deploy your Synkora agent as a Slack bot for team-wide access.

## Prerequisites

- Synkora agent created
- Slack workspace admin access
- Slack app created

## Step 1: Create a Slack App

1. Go to [api.slack.com/apps](https://api.slack.com/apps)
2. Click **Create New App**
3. Choose **From scratch**
4. Enter app name and select workspace

## Step 2: Configure Bot Permissions

Navigate to **OAuth & Permissions** and add these scopes:

### Bot Token Scopes

| Scope | Purpose |
|-------|---------|
| `app_mentions:read` | Receive mentions |
| `chat:write` | Send messages |
| `im:history` | Read DM history |
| `im:read` | Access DMs |
| `im:write` | Send DMs |
| `channels:history` | Read channel history |

## Step 3: Enable Events

Navigate to **Event Subscriptions**:

1. Enable events
2. Set Request URL: `https://api.synkora.io/webhooks/slack/{integration_id}`
3. Subscribe to bot events:
   - `app_mention`
   - `message.im`
   - `message.channels` (optional)

## Step 4: Install App to Workspace

1. Go to **Install App**
2. Click **Install to Workspace**
3. Authorize the app
4. Copy the **Bot User OAuth Token** (starts with `xoxb-`)

## Step 5: Create Synkora Integration

### Via Dashboard

1. Go to your agent's page
2. Click **Integrations** > **Add Slack**
3. Paste your Bot Token and Signing Secret
4. Configure response settings
5. Click **Connect**

### Via API

```bash
curl -X POST "https://api.synkora.io/api/v1/integrations/slack" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "agent-123",
    "bot_token": "xoxb-your-bot-token",
    "signing_secret": "your-signing-secret",
    "config": {
      "respond_to_mentions": true,
      "respond_in_threads": true,
      "dm_enabled": true
    }
  }'
```

### Via SDK

```typescript
const integration = await synkora.integrations.slack.create({
  agentId: agent.id,
  botToken: process.env.SLACK_BOT_TOKEN,
  signingSecret: process.env.SLACK_SIGNING_SECRET,
  config: {
    respondToMentions: true,
    respondInThreads: true,
    dmEnabled: true,
  },
});

console.log('Webhook URL:', integration.webhookUrl);
```

## Step 6: Update Slack Event URL

Copy the webhook URL from the integration and update it in Slack:

1. Go to **Event Subscriptions**
2. Update the **Request URL** with your integration's webhook URL
3. Verify the URL (Slack will send a challenge)

## Configuration Options

### Response Behavior

```typescript
await synkora.integrations.slack.update(integrationId, {
  config: {
    respondToMentions: true,      // Respond when @mentioned
    respondInThreads: true,       // Reply in thread
    dmEnabled: true,              // Allow direct messages
    allowedChannels: ['C123'],    // Restrict to specific channels
    typingIndicator: true,        // Show typing indicator
  },
});
```

### Channel Restrictions

Limit the bot to specific channels:

```typescript
config: {
  allowedChannels: ['C123456', 'C789012'],
  blockedChannels: ['C000000'],
}
```

## Using the Bot

### Mention in Channel

```
@YourBot What is the status of order #12345?
```

### Direct Message

Simply send a DM to the bot.

### Thread Replies

The bot automatically replies in threads to keep channels clean.

## Advanced Features

### Rich Messages

Your agent can send formatted messages:

```typescript
// The agent's response can include Slack formatting
const systemPrompt = `
You are a helpful assistant in Slack.

When formatting responses:
- Use *bold* for emphasis
- Use \`code\` for technical terms
- Use bullet points for lists
- Keep responses concise for chat
`;
```

### Interactive Buttons

```typescript
// Configure interactive components
await synkora.integrations.slack.update(integrationId, {
  config: {
    interactiveComponents: true,
    interactionsUrl: 'https://api.synkora.io/webhooks/slack/{id}/interactions',
  },
});
```

## Monitoring

### Check Bot Status

```typescript
const status = await synkora.integrations.slack.getStatus(integrationId);

console.log(status);
// {
//   connected: true,
//   lastMessage: '2024-01-15T10:30:00Z',
//   messageCount: 1500,
//   activeChannels: 5
// }
```

### View Logs

```typescript
const logs = await synkora.integrations.slack.getLogs(integrationId, {
  limit: 50,
});
```

## Troubleshooting

### Bot Not Responding

1. Check bot is invited to the channel
2. Verify webhook URL in Slack settings
3. Check Synkora integration status
4. Review Slack app event subscriptions

### Rate Limiting

Slack has rate limits. If you hit them:

- Implement message queuing
- Batch responses when possible
- Consider upgrading Slack plan

### Permission Errors

Ensure all required scopes are added and app is reinstalled after scope changes.

## Next Steps

- Add [knowledge bases](/docs/guides/agents/create-rag-agent) for context
- Configure [tools](/docs/guides/agents/add-tools) for actions
- Set up [analytics](/docs/api-reference/billing/usage) monitoring
