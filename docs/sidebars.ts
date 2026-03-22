import type { SidebarsConfig } from '@docusaurus/plugin-content-docs';

const sidebars: SidebarsConfig = {
  docsSidebar: [
    'intro',
    {
      type: 'category',
      label: 'Getting Started',
      collapsed: false,
      items: [
        'getting-started/quick-start',
        'getting-started/installation',
        'getting-started/configuration',
        'getting-started/first-agent',
        'getting-started/authentication',
      ],
    },
    {
      type: 'category',
      label: 'Core Concepts',
      items: [
        'concepts/agents',
        'concepts/knowledge-bases',
        'concepts/tools',
        'concepts/conversations',
        'concepts/multi-tenancy',
        'concepts/billing',
        'concepts/security',
      ],
    },
    {
      type: 'category',
      label: 'API Reference',
      items: [
        'api-reference/overview',
        {
          type: 'category',
          label: 'Agents',
          items: [
            'api-reference/agents/index',
            'api-reference/agents/chat',
            'api-reference/agents/conversations',
            'api-reference/agents/tools',
            'api-reference/agents/knowledge-bases',
            'api-reference/agents/llm-configs',
          ],
        },
        {
          type: 'category',
          label: 'Knowledge Bases',
          items: [
            'api-reference/knowledge-bases/index',
            'api-reference/knowledge-bases/documents',
            'api-reference/knowledge-bases/search',
          ],
        },
        {
          type: 'category',
          label: 'Billing',
          items: [
            'api-reference/billing/subscriptions',
            'api-reference/billing/credits',
            'api-reference/billing/usage',
          ],
        },
        {
          type: 'category',
          label: 'Integrations',
          items: [
            'api-reference/integrations/slack',
            'api-reference/integrations/telegram',
            'api-reference/integrations/whatsapp',
            'api-reference/integrations/teams',
            'api-reference/integrations/oauth',
          ],
        },
        'api-reference/webhooks',
        'api-reference/errors',
        'api-reference/rate-limits',
      ],
    },
    {
      type: 'category',
      label: 'Guides',
      items: [
        {
          type: 'category',
          label: 'Agents',
          items: [
            'guides/agents/create-rag-agent',
            'guides/agents/add-tools',
            'guides/agents/custom-tools',
            'guides/agents/mcp-servers',
          ],
        },
        {
          type: 'category',
          label: 'Integrations',
          items: [
            'guides/integrations/slack-bot',
            'guides/integrations/telegram-bot',
            'guides/integrations/whatsapp-bot',
            'guides/integrations/teams-bot',
            'guides/integrations/embed-widget',
          ],
        },
        {
          type: 'category',
          label: 'Knowledge Base',
          items: [
            'guides/knowledge-base/setup-qdrant',
            'guides/knowledge-base/setup-pinecone',
            'guides/knowledge-base/document-processing',
            'guides/knowledge-base/advanced-rag',
          ],
        },
        {
          type: 'category',
          label: 'Authentication',
          items: [
            'guides/auth/sso-okta',
            'guides/auth/oauth-providers',
            'guides/auth/api-keys',
          ],
        },
        {
          type: 'category',
          label: 'Deployment',
          items: [
            'guides/deployment/docker',
            'guides/deployment/kubernetes',
            'guides/deployment/production',
          ],
        },
      ],
    },
    {
      type: 'category',
      label: 'SDK',
      items: [
        {
          type: 'category',
          label: 'TypeScript',
          items: [
            'sdk/typescript/installation',
            'sdk/typescript/quick-start',
            'sdk/typescript/agents',
            'sdk/typescript/chat',
            'sdk/typescript/reference',
          ],
        },
        {
          type: 'category',
          label: 'Python',
          items: [
            'sdk/python/installation',
            'sdk/python/quick-start',
          ],
        },
      ],
    },
    {
      type: 'category',
      label: 'Architecture',
      items: [
        'architecture/overview',
        'architecture/backend',
        'architecture/frontend',
        'architecture/database',
        'architecture/caching',
        'architecture/background-jobs',
        'architecture/streaming',
        'architecture/multi-tenancy',
      ],
    },
  ],
};

export default sidebars;
