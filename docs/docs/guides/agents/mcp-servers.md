---
sidebar_position: 4
---

# Connect MCP Servers

Model Context Protocol (MCP) servers provide a standardized way to extend agent capabilities with external tools and resources.

## What is MCP?

MCP is an open protocol for connecting AI models to external data and tools. Benefits include:

- Standardized tool interfaces
- Pre-built server implementations
- Community ecosystem
- Secure resource access

## Connecting an MCP Server

### Register the Server

```typescript
await synkora.agents.addMCPServer(agent.id, {
  name: 'database-tools',
  url: 'http://localhost:3001/mcp',
  transport: 'http',
  authentication: {
    type: 'bearer',
    token: process.env.MCP_TOKEN,
  },
});
```

### Available Tools

Once connected, the server's tools become available to your agent:

```typescript
const mcpInfo = await synkora.agents.getMCPServer(agent.id, 'database-tools');

console.log(mcpInfo.tools);
// ['query_database', 'list_tables', 'get_schema']
```

## Popular MCP Servers

### File System Access

```typescript
await synkora.agents.addMCPServer(agent.id, {
  name: 'filesystem',
  url: 'mcp://filesystem',
  config: {
    allowedPaths: ['/data/documents'],
    readOnly: true,
  },
});
```

### Database Access

```typescript
await synkora.agents.addMCPServer(agent.id, {
  name: 'postgres',
  url: 'mcp://postgres',
  config: {
    connectionString: process.env.DATABASE_URL,
    readOnly: true,
    allowedTables: ['products', 'orders'],
  },
});
```

### Git Repository

```typescript
await synkora.agents.addMCPServer(agent.id, {
  name: 'git',
  url: 'mcp://git',
  config: {
    repository: '/path/to/repo',
    branch: 'main',
  },
});
```

## Building a Custom MCP Server

### Server Setup (TypeScript)

```typescript
import { MCPServer, Tool } from '@modelcontextprotocol/sdk';

const server = new MCPServer({
  name: 'my-tools',
  version: '1.0.0',
});

// Define a tool
const searchTool: Tool = {
  name: 'search_inventory',
  description: 'Search product inventory',
  inputSchema: {
    type: 'object',
    properties: {
      query: { type: 'string' },
      category: { type: 'string' },
    },
    required: ['query'],
  },
};

// Register the tool
server.registerTool(searchTool, async (params) => {
  const results = await inventoryService.search(params);
  return { content: JSON.stringify(results) };
});

// Start the server
server.listen(3001);
```

### Connect to Your Server

```typescript
await synkora.agents.addMCPServer(agent.id, {
  name: 'inventory',
  url: 'http://localhost:3001/mcp',
  transport: 'http',
});
```

## Managing MCP Connections

### List Connected Servers

```typescript
const servers = await synkora.agents.listMCPServers(agent.id);

console.log(servers);
// [
//   { name: 'database-tools', status: 'connected', tools: 3 },
//   { name: 'filesystem', status: 'connected', tools: 5 },
// ]
```

### Disconnect a Server

```typescript
await synkora.agents.removeMCPServer(agent.id, 'database-tools');
```

### Update Configuration

```typescript
await synkora.agents.updateMCPServer(agent.id, 'filesystem', {
  config: {
    allowedPaths: ['/data/documents', '/data/reports'],
  },
});
```

## Security Considerations

### Authentication

Always use authentication for MCP servers:

```typescript
await synkora.agents.addMCPServer(agent.id, {
  name: 'secure-tools',
  url: 'https://mcp.example.com',
  authentication: {
    type: 'bearer',
    token: process.env.MCP_SECRET_TOKEN,
  },
});
```

### Network Isolation

Run MCP servers in isolated environments:

- Use private networks
- Implement firewall rules
- Enable TLS encryption

### Audit Logging

Log all tool invocations:

```typescript
server.use(async (req, next) => {
  console.log(`Tool: ${req.tool}, User: ${req.context.userId}`);
  const result = await next();
  console.log(`Result: ${result.success}`);
  return result;
});
```

## Troubleshooting

### Connection Issues

```typescript
const status = await synkora.agents.testMCPConnection(agent.id, 'database-tools');

console.log(status);
// { connected: false, error: 'Connection refused' }
```

### Tool Not Found

Verify tools are registered:

```bash
curl http://localhost:3001/mcp/tools
```

## Next Steps

- Explore [MCP server examples](https://github.com/modelcontextprotocol/servers)
- Learn about [tool best practices](/docs/guides/agents/custom-tools)
