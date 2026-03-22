---
sidebar_position: 4
---

# Deploy a Microsoft Teams Bot

Deploy your Synkora agent on Microsoft Teams.

## Prerequisites

- Azure account
- Microsoft Teams admin access
- Azure Bot Service

## Step 1: Create Azure Bot

1. Go to Azure Portal
2. Create a new **Azure Bot** resource
3. Note the App ID and generate a password

## Step 2: Configure Bot Framework

Set messaging endpoint to:

```
https://api.synkora.io/webhooks/teams/{integration_id}/messages
```

## Step 3: Create Synkora Integration

```typescript
const integration = await synkora.integrations.teams.create({
  agentId: agent.id,
  appId: 'YOUR_AZURE_APP_ID',
  appPassword: 'YOUR_APP_PASSWORD',
  tenantId: 'YOUR_TENANT_ID',
  config: {
    respondToMentions: true,
    respondInChannels: true,
    directMessages: true,
  },
});
```

## Step 4: Create Teams App Manifest

Create `manifest.json`:

```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/teams/v1.14/MicrosoftTeams.schema.json",
  "manifestVersion": "1.14",
  "version": "1.0.0",
  "id": "YOUR_APP_ID",
  "packageName": "com.synkora.bot",
  "name": {
    "short": "Support Bot"
  },
  "bots": [
    {
      "botId": "YOUR_BOT_ID",
      "scopes": ["team", "personal"]
    }
  ]
}
```

## Step 5: Install in Teams

1. Package the manifest as a .zip
2. Go to Teams Admin Center
3. Upload the app package
4. Approve for organization

## Next Steps

- [Embed chat widget](/docs/guides/integrations/embed-widget)
