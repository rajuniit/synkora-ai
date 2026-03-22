---
sidebar_position: 3
---

# Deploy a WhatsApp Bot

Deploy your Synkora agent on WhatsApp Business.

## Prerequisites

- WhatsApp Business API access
- Meta Business account
- Verified phone number

## Step 1: Set Up WhatsApp Business API

1. Go to [Meta Business Suite](https://business.facebook.com/)
2. Create a WhatsApp Business app
3. Get your Phone Number ID and Access Token

## Step 2: Create Synkora Integration

```typescript
const integration = await synkora.integrations.whatsapp.create({
  agentId: agent.id,
  phoneNumberId: 'YOUR_PHONE_NUMBER_ID',
  accessToken: 'YOUR_ACCESS_TOKEN',
  verifyToken: 'YOUR_WEBHOOK_VERIFY_TOKEN',
  config: {
    welcomeMessage: 'Hello! How can I help you?',
    businessHours: {
      enabled: true,
      timezone: 'America/New_York',
      awayMessage: 'We are currently offline.',
    },
  },
});
```

## Step 3: Configure Webhook

In Meta Business settings, set webhook URL to:

```
https://api.synkora.io/webhooks/whatsapp/{integration_id}
```

Subscribe to:
- `messages`
- `messaging_postbacks`

## Template Messages

For business-initiated conversations:

```typescript
await synkora.integrations.whatsapp.sendTemplate(integrationId, {
  to: '+1234567890',
  templateName: 'order_confirmation',
  language: 'en_US',
  components: [
    { type: 'body', parameters: [{ type: 'text', text: 'ORD-123' }] },
  ],
});
```

## Next Steps

- [Deploy to Microsoft Teams](/docs/guides/integrations/teams-bot)
- [Embed chat widget](/docs/guides/integrations/embed-widget)
