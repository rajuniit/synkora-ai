import type {ReactNode} from 'react';
import Link from '@docusaurus/Link';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import Layout from '@theme/Layout';
import Heading from '@theme/Heading';

import styles from './index.module.css';

function HeroSection() {
  return (
    <header className={styles.hero}>
      <div className={styles.heroInner}>
        <div className={styles.heroContent}>
          <Heading as="h1" className={styles.heroTitle}>
            Build AI Agents<br />
            <span className={styles.heroTitleAccent}>That Actually Work</span>
          </Heading>
          <p className={styles.heroSubtitle}>
            The complete platform for building, deploying, and managing
            production-ready AI agents with RAG, tools, and multi-channel integrations.
          </p>
          <div className={styles.heroButtons}>
            <Link className={styles.heroButtonPrimary} to="/docs/">
              Get Started
            </Link>
            <Link className={styles.heroButtonSecondary} to="/docs/api-reference/overview">
              API Reference
            </Link>
          </div>
        </div>
        <div className={styles.heroVisual}>
          <div className={styles.codeBlock}>
            <div className={styles.codeHeader}>
              <span className={styles.codeDot} style={{background: '#ef4444'}}></span>
              <span className={styles.codeDot} style={{background: '#fbbf24'}}></span>
              <span className={styles.codeDot} style={{background: '#22c55e'}}></span>
            </div>
            <pre className={styles.codeContent}>
{`const agent = await synkora.agents.create({
  name: 'Support Bot',
  model: 'gpt-4',
  tools: ['web_search', 'calculator'],
  knowledgeBase: 'docs-kb'
});

// Stream responses in real-time
for await (const chunk of agent.chat(message)) {
  console.log(chunk.content);
}`}
            </pre>
          </div>
        </div>
      </div>
    </header>
  );
}

function FeatureCard({icon, title, description}: {icon: string; title: string; description: string}) {
  return (
    <div className={styles.featureCard}>
      <div className={styles.featureIcon}>{icon}</div>
      <h3 className={styles.featureTitle}>{title}</h3>
      <p className={styles.featureDescription}>{description}</p>
    </div>
  );
}

function FeaturesSection() {
  const features = [
    {
      icon: '🤖',
      title: 'AI Agents',
      description: 'Create intelligent agents with built-in RAG, custom tools, and support for OpenAI, Anthropic, Google, and more.',
    },
    {
      icon: '📚',
      title: 'Knowledge Bases',
      description: 'Upload documents, websites, and files. Automatic chunking, embedding, and vector search with Qdrant or Pinecone.',
    },
    {
      icon: '🔧',
      title: 'Custom Tools',
      description: 'Extend agents with web search, calculators, API integrations, or build your own custom tools.',
    },
    {
      icon: '💬',
      title: 'Multi-Channel',
      description: 'Deploy to Slack, Teams, WhatsApp, Telegram, or embed as a widget on your website.',
    },
    {
      icon: '⚡',
      title: 'Real-time Streaming',
      description: 'Server-sent events for instant responses. No waiting for complete generations.',
    },
    {
      icon: '🔒',
      title: 'Enterprise Ready',
      description: 'Multi-tenancy, SSO, API keys, rate limiting, and usage analytics built-in.',
    },
  ];

  return (
    <section className={styles.features}>
      <div className={styles.featuresInner}>
        <div className={styles.featuresHeader}>
          <h2 className={styles.featuresTitle}>Everything you need to build AI agents</h2>
          <p className={styles.featuresSubtitle}>
            From prototype to production in minutes, not months.
          </p>
        </div>
        <div className={styles.featuresGrid}>
          {features.map((feature, idx) => (
            <FeatureCard key={idx} {...feature} />
          ))}
        </div>
      </div>
    </section>
  );
}

function CTASection() {
  return (
    <section className={styles.cta}>
      <div className={styles.ctaInner}>
        <h2 className={styles.ctaTitle}>Ready to build?</h2>
        <p className={styles.ctaSubtitle}>
          Get started with Synkora in under 5 minutes.
        </p>
        <div className={styles.ctaButtons}>
          <Link className={styles.ctaButtonPrimary} to="/docs/getting-started/quick-start">
            Quick Start Guide
          </Link>
          <Link className={styles.ctaButtonSecondary} href="https://github.com/rajuniit/synkora-ai">
            View on GitHub
          </Link>
        </div>
      </div>
    </section>
  );
}

export default function Home(): ReactNode {
  const {siteConfig} = useDocusaurusContext();
  return (
    <Layout
      title="Home"
      description="Build, deploy, and manage AI agents at scale with Synkora">
      <main>
        <HeroSection />
        <FeaturesSection />
        <CTASection />
      </main>
    </Layout>
  );
}
