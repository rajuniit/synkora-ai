---
sidebar_position: 5
---

# Embed Chat Widget

Add a Synkora chat widget to your website.

## Quick Start

Add this script to your website:

```html
<!-- Replace YOUR_INSTANCE_URL with your Synkora deployment URL -->
<script>
  (function(w, d, s, o, f, js, fjs) {
    w['SynkoraWidget'] = o;
    w[o] = w[o] || function() { (w[o].q = w[o].q || []).push(arguments) };
    js = d.createElement(s); fjs = d.getElementsByTagName(s)[0];
    js.id = o; js.src = f; js.async = 1;
    fjs.parentNode.insertBefore(js, fjs);
  }(window, document, 'script', 'synkora', 'https://YOUR_INSTANCE_URL/widget.js'));

  synkora('init', {
    agentId: 'YOUR_AGENT_ID',
    token: 'YOUR_WIDGET_TOKEN'
  });
</script>
```

## Generate Widget Token

```typescript
const { token } = await synkora.agents.createWidgetToken(agentId, {
  allowedOrigins: ['https://example.com'],
  expiresIn: '30d',
});
```

## Configuration Options

```javascript
synkora('init', {
  agentId: 'YOUR_AGENT_ID',
  token: 'YOUR_WIDGET_TOKEN',

  // Appearance
  position: 'bottom-right',  // bottom-right, bottom-left
  primaryColor: '#0066cc',
  title: 'Support Chat',
  subtitle: 'Ask us anything!',
  placeholder: 'Type your message...',

  // Behavior
  autoOpen: false,
  autoOpenDelay: 5000,
  showOnMobile: true,

  // User context
  user: {
    id: 'user-123',
    name: 'John Doe',
    email: 'john@example.com',
  },
});
```

## Programmatic Control

```javascript
// Open chat
synkora('open');

// Close chat
synkora('close');

// Toggle chat
synkora('toggle');

// Send message programmatically
synkora('send', 'Hello!');

// Update user
synkora('identify', {
  id: 'user-123',
  name: 'John Doe',
});
```

## Custom Styling

Override widget styles:

```css
:root {
  --synkora-primary: #0066cc;
  --synkora-background: #ffffff;
  --synkora-text: #333333;
  --synkora-border-radius: 12px;
}
```

## Events

Listen to widget events:

```javascript
synkora('on', 'open', () => {
  console.log('Chat opened');
});

synkora('on', 'message', (message) => {
  console.log('New message:', message);
});

synkora('on', 'close', () => {
  console.log('Chat closed');
});
```

## React Component

> **Note:** A `@synkora/react` npm package is not yet published. Wrap the script-tag embed in a `useEffect` instead:

```jsx
import { useEffect } from 'react';

function SynkoraWidget({ agentId, token, instanceUrl }) {
  useEffect(() => {
    const script = document.createElement('script');
    script.src = `${instanceUrl}/widget.js`;
    script.async = true;
    script.onload = () => window.synkora?.('init', { agentId, token });
    document.body.appendChild(script);
    return () => document.body.removeChild(script);
  }, [agentId, token, instanceUrl]);

  return null;
}

// <SynkoraWidget
//   instanceUrl="https://YOUR_INSTANCE_URL"
//   agentId="YOUR_AGENT_ID"
//   token="YOUR_WIDGET_TOKEN"
// />
```

## Next Steps

- Customize [agent behavior](/docs/concepts/agents)
- Add [knowledge base](/docs/guides/agents/create-rag-agent)
