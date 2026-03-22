---
sidebar_position: 3
---

# Build Custom Tools

Create custom tools to extend your agent with any functionality.

## Tool Architecture

Custom tools connect your agent to your backend services:

```
Agent → Synkora → Your Webhook → Your Service → Response
```

## Creating a Custom Tool

### Step 1: Define the Tool Schema

```typescript
const createTicketTool = {
  name: 'create_support_ticket',
  description: 'Creates a new support ticket in the system. Use when customer needs escalation or tracking.',
  parameters: {
    type: 'object',
    properties: {
      title: {
        type: 'string',
        description: 'Brief summary of the issue',
        maxLength: 200,
      },
      description: {
        type: 'string',
        description: 'Detailed description of the issue',
      },
      priority: {
        type: 'string',
        enum: ['low', 'medium', 'high', 'urgent'],
        description: 'Ticket priority level',
      },
      category: {
        type: 'string',
        enum: ['billing', 'technical', 'account', 'other'],
      },
    },
    required: ['title', 'description', 'priority'],
  },
};
```

### Step 2: Register with Handler

```typescript
await synkora.agents.registerTool(agent.id, {
  ...createTicketTool,
  handler: {
    type: 'webhook',
    url: 'https://api.yourcompany.com/synkora/tools/create-ticket',
    method: 'POST',
    headers: {
      'Authorization': 'Bearer ${SUPPORT_API_KEY}',
    },
    timeout: 30000,
  },
});
```

### Step 3: Implement the Handler

```typescript
// Express.js handler
import express from 'express';
import { verifyWebhookSignature } from './auth';

const app = express();

app.post('/synkora/tools/create-ticket', async (req, res) => {
  // Verify the request is from Synkora
  if (!verifyWebhookSignature(req)) {
    return res.status(401).json({ error: 'Unauthorized' });
  }

  const { title, description, priority, category } = req.body;

  try {
    // Create ticket in your system
    const ticket = await ticketService.create({
      title,
      description,
      priority,
      category: category || 'other',
      source: 'synkora_agent',
      metadata: {
        conversation_id: req.headers['x-synkora-conversation-id'],
        agent_id: req.headers['x-synkora-agent-id'],
      },
    });

    // Return success response
    return res.json({
      success: true,
      ticket_id: ticket.id,
      message: `Ticket #${ticket.id} created successfully`,
      url: `https://support.yourcompany.com/tickets/${ticket.id}`,
    });
  } catch (error) {
    return res.json({
      success: false,
      message: 'Failed to create ticket. Please try again.',
    });
  }
});
```

## Advanced Tool Patterns

### Multi-Step Tools

Tools that require multiple operations:

```typescript
const bookAppointmentTool = {
  name: 'book_appointment',
  description: 'Book an appointment with a specialist',
  parameters: {
    type: 'object',
    properties: {
      service_type: {
        type: 'string',
        enum: ['consultation', 'demo', 'support'],
      },
      preferred_date: {
        type: 'string',
        format: 'date',
        description: 'Preferred date (YYYY-MM-DD)',
      },
      preferred_time: {
        type: 'string',
        description: 'Preferred time slot (e.g., "morning", "afternoon", "14:00")',
      },
      timezone: {
        type: 'string',
        description: 'Customer timezone (e.g., "America/New_York")',
      },
    },
    required: ['service_type', 'preferred_date'],
  },
};
```

Handler implementation:

```typescript
app.post('/synkora/tools/book-appointment', async (req, res) => {
  const { service_type, preferred_date, preferred_time, timezone } = req.body;

  // Find available slots
  const slots = await calendar.getAvailableSlots({
    date: preferred_date,
    service: service_type,
    preference: preferred_time,
  });

  if (slots.length === 0) {
    return res.json({
      success: false,
      message: 'No available slots on that date',
      alternative_dates: await calendar.getNextAvailableDates(service_type, 3),
    });
  }

  // If time preference matches, book it
  const matchingSlot = slots.find(s => matchesPreference(s, preferred_time));

  if (matchingSlot) {
    const booking = await calendar.book(matchingSlot.id);
    return res.json({
      success: true,
      booking_id: booking.id,
      datetime: booking.datetime,
      message: `Booked for ${formatDate(booking.datetime)}`,
    });
  }

  // Otherwise, return available options
  return res.json({
    success: false,
    message: 'Preferred time not available',
    available_slots: slots.map(s => ({
      id: s.id,
      time: s.time,
      formatted: formatTime(s.time, timezone),
    })),
  });
});
```

### Database Query Tools

Tools that query your database:

```typescript
const searchProductsTool = {
  name: 'search_products',
  description: 'Search product catalog',
  parameters: {
    type: 'object',
    properties: {
      query: { type: 'string' },
      category: { type: 'string' },
      min_price: { type: 'number' },
      max_price: { type: 'number' },
      in_stock: { type: 'boolean' },
    },
    required: ['query'],
  },
};
```

```typescript
app.post('/synkora/tools/search-products', async (req, res) => {
  const { query, category, min_price, max_price, in_stock } = req.body;

  const products = await db.products.search({
    query,
    filters: {
      ...(category && { category }),
      ...(min_price && { price: { $gte: min_price } }),
      ...(max_price && { price: { $lte: max_price } }),
      ...(in_stock !== undefined && { inStock: in_stock }),
    },
    limit: 5,
  });

  return res.json({
    success: true,
    count: products.length,
    products: products.map(p => ({
      id: p.id,
      name: p.name,
      price: `$${p.price}`,
      in_stock: p.inStock,
      url: `https://shop.example.com/products/${p.slug}`,
    })),
  });
});
```

## Security Best Practices

### Verify Requests

Always verify webhook signatures:

```typescript
import crypto from 'crypto';

function verifyWebhookSignature(req) {
  const signature = req.headers['x-synkora-signature'];
  const timestamp = req.headers['x-synkora-timestamp'];

  // Verify timestamp is recent (prevent replay attacks)
  const now = Date.now() / 1000;
  if (Math.abs(now - parseInt(timestamp)) > 300) {
    return false;
  }

  const payload = `${timestamp}.${JSON.stringify(req.body)}`;
  const expected = crypto
    .createHmac('sha256', process.env.SYNKORA_WEBHOOK_SECRET)
    .update(payload)
    .digest('hex');

  return crypto.timingSafeEqual(
    Buffer.from(signature),
    Buffer.from(expected)
  );
}
```

### Sanitize Inputs

Never trust tool inputs blindly:

```typescript
app.post('/synkora/tools/query', async (req, res) => {
  const { query } = req.body;

  // ❌ Bad: SQL injection risk
  // const result = await db.raw(`SELECT * FROM products WHERE name = '${query}'`);

  // ✅ Good: Parameterized query
  const result = await db.products.where('name', 'like', `%${sanitize(query)}%`);
});
```

### Rate Limiting

Protect your endpoints:

```typescript
import rateLimit from 'express-rate-limit';

const toolLimiter = rateLimit({
  windowMs: 60 * 1000, // 1 minute
  max: 100, // 100 requests per minute
});

app.use('/synkora/tools', toolLimiter);
```

## Testing Tools

### Manual Testing

Test your tool handler directly:

```bash
curl -X POST https://api.yourcompany.com/synkora/tools/create-ticket \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Test ticket",
    "description": "Testing the tool",
    "priority": "low"
  }'
```

### Integration Testing

Test via the agent:

```typescript
const response = await synkora.agents.chat(agent.id, {
  message: 'Create a high priority ticket about login issues',
});

console.log(response.toolCalls);
// [{ name: 'create_support_ticket', result: { ticket_id: '123' } }]
```

## Next Steps

- [Connect MCP servers](/docs/guides/agents/mcp-servers)
- [Deploy to Slack](/docs/guides/integrations/slack-bot)
