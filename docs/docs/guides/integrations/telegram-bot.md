---
sidebar_position: 2
---

# Deploy a Telegram Bot

Deploy your Synkora agent as a Telegram bot.

## Prerequisites

- Synkora agent created
- Telegram account
- Bot token from @BotFather

## Step 1: Create a Telegram Bot

1. Open Telegram and search for **@BotFather**
2. Send `/newbot` command
3. Follow prompts to name your bot
4. Copy the **bot token**

## Step 2: Create Synkora Integration

```typescript
const integration = await synkora.integrations.telegram.create({
  agentId: agent.id,
  botToken: 'YOUR_BOT_TOKEN',
  config: {
    welcomeMessage: 'Hello! How can I help you today?',
    commands: [
      { command: 'start', description: 'Start conversation' },
      { command: 'help', description: 'Get help' },
      { command: 'reset', description: 'Reset conversation' },
    ],
  },
});
```

## Step 3: Configure Commands

Set bot commands in Telegram:

```typescript
await synkora.integrations.telegram.setCommands(integrationId, [
  { command: 'start', description: 'Start conversation' },
  { command: 'help', description: 'Get help' },
]);
```

## Configuration Options

```typescript
config: {
  welcomeMessage: 'Hello!',        // Message on /start
  allowedUsers: [],                 // Empty = all users
  groupsEnabled: true,              // Allow in groups
  inlineMode: false,                // Inline query support
}
```

## Using the Bot

- **Direct chat**: Send any message
- **Groups**: Mention the bot or reply to its messages
- **Commands**: Use /start, /help, etc.

## Next Steps

- [Deploy to WhatsApp](/docs/guides/integrations/whatsapp-bot)
- [Add knowledge base](/docs/guides/agents/create-rag-agent)
