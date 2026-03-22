---
sidebar_position: 3
---

# Frontend Architecture

The Synkora frontend is built with Next.js 15 and the App Router.

## Directory Structure

```
web/
├── app/
│   ├── (auth)/            # Auth pages (public)
│   │   ├── signin/
│   │   ├── signup/
│   │   └── ...
│   ├── (dashboard)/       # Dashboard pages (protected)
│   │   ├── agents/
│   │   ├── knowledge-bases/
│   │   ├── settings/
│   │   └── ...
│   └── layout.tsx
├── components/
│   ├── chat/              # Chat components
│   ├── agents/            # Agent components
│   ├── ui/                # Base UI components
│   └── ...
├── lib/
│   ├── api/
│   │   └── client.ts      # Axios client
│   ├── store/             # Zustand stores
│   ├── hooks/             # Custom hooks
│   └── types/             # TypeScript types
└── ...
```

## State Management

### Zustand Stores

```typescript
// lib/store/auth.ts
import { create } from 'zustand';

interface AuthState {
  user: User | null;
  token: string | null;
  setUser: (user: User) => void;
  logout: () => void;
}

export const useAuth = create<AuthState>((set) => ({
  user: null,
  token: null,
  setUser: (user) => set({ user }),
  logout: () => set({ user: null, token: null }),
}));
```

## API Client

```typescript
// lib/api/client.ts
import axios from 'axios';

export const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL,
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});
```

## Components

### UI Components

Reusable base components:

```typescript
// components/ui/Button.tsx
export function Button({ children, variant = 'primary', ...props }) {
  return (
    <button className={buttonVariants({ variant })} {...props}>
      {children}
    </button>
  );
}
```

### Feature Components

Domain-specific components:

```typescript
// components/agents/AgentCard.tsx
export function AgentCard({ agent }: { agent: Agent }) {
  return (
    <Card>
      <CardHeader>{agent.name}</CardHeader>
      <CardBody>{agent.description}</CardBody>
    </Card>
  );
}
```

## Routing

### Route Groups

```
app/
├── (auth)/           # /signin, /signup (no auth required)
├── (dashboard)/      # /agents, /settings (auth required)
└── (public)/         # / (landing page)
```

### Protected Routes

```typescript
// app/(dashboard)/layout.tsx
export default function DashboardLayout({ children }) {
  const { user } = useAuth();

  if (!user) {
    redirect('/signin');
  }

  return <DashboardShell>{children}</DashboardShell>;
}
```

## Data Fetching

### Server Components

```typescript
// app/(dashboard)/agents/page.tsx
export default async function AgentsPage() {
  const agents = await fetchAgents();
  return <AgentsList agents={agents} />;
}
```

### Client Components

```typescript
// components/agents/AgentsList.tsx
'use client';

export function AgentsList() {
  const { data, isLoading } = useQuery(['agents'], fetchAgents);

  if (isLoading) return <Loading />;
  return data.map(agent => <AgentCard key={agent.id} agent={agent} />);
}
```
