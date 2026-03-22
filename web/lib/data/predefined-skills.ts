/**
 * Pre-defined skills library
 *
 * These skills are sourced from the claude-skills repository
 * and can be selected by users when configuring their agents.
 *
 * Skills are organized by category and include:
 * - id: Unique identifier for the skill
 * - name: Display name
 * - description: Trigger description (used for skill matching at runtime)
 * - category: Skill category for grouping in UI
 */

export interface PredefinedSkill {
  id: string
  name: string
  description: string
  category: string
  icon: string
}

export interface SkillCategory {
  id: string
  name: string
  icon: string
  description: string
}

export const SKILL_CATEGORIES: SkillCategory[] = [
  {
    id: 'engineering-team',
    name: 'Engineering',
    icon: '⚙️',
    description: 'Software development, DevOps, security, and architecture skills'
  },
  {
    id: 'marketing-skill',
    name: 'Marketing',
    icon: '📣',
    description: 'Content creation, SEO, demand generation, and social media'
  },
  {
    id: 'product-team',
    name: 'Product',
    icon: '🎯',
    description: 'Product management, UX research, and design systems'
  },
  {
    id: 'project-management',
    name: 'Project Management',
    icon: '📋',
    description: 'Project management, agile, and Atlassian tools'
  }
]

export const PREDEFINED_SKILLS: PredefinedSkill[] = [
  // Engineering Team
  {
    id: 'aws-solution-architect',
    name: 'AWS Solution Architect',
    description: 'Design AWS architectures for startups using serverless patterns and IaC templates. Use when asked to design serverless architecture, create CloudFormation templates, optimize AWS costs, set up CI/CD pipelines, or migrate to AWS. Covers Lambda, API Gateway, DynamoDB, ECS, Aurora, and cost optimization.',
    category: 'engineering-team',
    icon: '☁️'
  },
  {
    id: 'code-reviewer',
    name: 'Code Reviewer',
    description: 'Code review automation for TypeScript, JavaScript, Python, Go, Swift, Kotlin. Analyzes PRs for complexity and risk, checks code quality for SOLID violations and code smells, generates review reports. Use when reviewing pull requests, analyzing code quality, identifying issues, generating review checklists.',
    category: 'engineering-team',
    icon: '🔍'
  },
  {
    id: 'senior-architect',
    name: 'Senior Software Architect',
    description: 'Use when asked to design system architecture, evaluate microservices vs monolith, create architecture diagrams, analyze dependencies, choose a database, plan for scalability, make technical decisions, or review system design. Use for architecture decision records (ADRs), tech stack evaluation, system design reviews.',
    category: 'engineering-team',
    icon: '🏗️'
  },
  {
    id: 'senior-backend',
    name: 'Senior Backend Engineer',
    description: 'Use when asked to design REST APIs, optimize database queries, implement authentication, build microservices, review backend code, set up GraphQL, handle database migrations, or load test APIs. Use for Node.js/Express/Fastify development, PostgreSQL optimization, API security.',
    category: 'engineering-team',
    icon: '🔧'
  },
  {
    id: 'senior-computer-vision',
    name: 'Senior Computer Vision Engineer',
    description: 'Computer vision engineering skill for object detection, image segmentation, and visual AI systems. Covers CNN and Vision Transformer architectures, YOLO/Faster R-CNN/DETR detection, Mask R-CNN/SAM segmentation. Use when building detection pipelines, training custom models, optimizing inference.',
    category: 'engineering-team',
    icon: '👁️'
  },
  {
    id: 'senior-data-engineer',
    name: 'Senior Data Engineer',
    description: 'Data engineering skill for building scalable data pipelines, ETL/ELT systems, and data infrastructure. Expertise in Python, SQL, Spark, Airflow, dbt, Kafka. Use when designing data architectures, building data pipelines, optimizing data workflows, implementing data governance.',
    category: 'engineering-team',
    icon: '📊'
  },
  {
    id: 'senior-data-scientist',
    name: 'Senior Data Scientist',
    description: 'Data science skill for statistical modeling, experimentation, causal inference, and advanced analytics. Expertise in Python (NumPy, Pandas, Scikit-learn), R, SQL. Use when designing experiments, building predictive models, performing causal analysis, or driving data-driven decisions.',
    category: 'engineering-team',
    icon: '📈'
  },
  {
    id: 'senior-devops',
    name: 'Senior DevOps Engineer',
    description: 'Comprehensive DevOps skill for CI/CD, infrastructure automation, containerization, and cloud platforms (AWS, GCP, Azure). Includes pipeline setup, infrastructure as code, deployment automation. Use when setting up pipelines, deploying applications, managing infrastructure.',
    category: 'engineering-team',
    icon: '🚀'
  },
  {
    id: 'senior-frontend',
    name: 'Senior Frontend Engineer',
    description: 'Frontend development skill for React, Next.js, TypeScript, and Tailwind CSS applications. Use when building React components, optimizing Next.js performance, analyzing bundle sizes, scaffolding frontend projects, implementing accessibility, or reviewing frontend code quality.',
    category: 'engineering-team',
    icon: '⚛️'
  },
  {
    id: 'senior-fullstack',
    name: 'Senior Fullstack Engineer',
    description: 'Fullstack development toolkit with project scaffolding for Next.js/FastAPI/MERN/Django stacks and code quality analysis. Use when scaffolding new projects, analyzing codebase quality, or implementing fullstack architecture patterns.',
    category: 'engineering-team',
    icon: '🔄'
  },
  {
    id: 'senior-ml-engineer',
    name: 'Senior ML Engineer',
    description: 'ML engineering skill for productionizing models, building MLOps pipelines, and integrating LLMs. Covers model deployment, feature stores, drift monitoring, RAG systems, and cost optimization.',
    category: 'engineering-team',
    icon: '🤖'
  },
  {
    id: 'senior-prompt-engineer',
    name: 'Senior Prompt Engineer',
    description: 'Use when asked to optimize prompts, design prompt templates, evaluate LLM outputs, build agentic systems, implement RAG, create few-shot examples, analyze token usage, or design AI workflows. Use for prompt engineering patterns, LLM evaluation frameworks, agent architectures.',
    category: 'engineering-team',
    icon: '✨'
  },
  {
    id: 'senior-qa',
    name: 'Senior QA Engineer',
    description: 'Use when asked to generate tests, write unit tests, analyze test coverage, scaffold E2E tests, set up Playwright, configure Jest, implement testing patterns, or improve test quality. Use for React/Next.js testing with Jest, React Testing Library, and Playwright.',
    category: 'engineering-team',
    icon: '🧪'
  },
  {
    id: 'senior-secops',
    name: 'Senior SecOps Engineer',
    description: 'Comprehensive SecOps skill for application security, vulnerability management, compliance, and secure development practices. Use when implementing security controls, conducting security audits, responding to vulnerabilities, or ensuring compliance requirements.',
    category: 'engineering-team',
    icon: '🛡️'
  },
  {
    id: 'senior-security',
    name: 'Senior Security Engineer',
    description: 'Comprehensive security engineering skill for application security, penetration testing, security architecture, and compliance auditing. Use when designing security architecture, conducting penetration tests, implementing cryptography, or performing security audits.',
    category: 'engineering-team',
    icon: '🔐'
  },
  {
    id: 'tdd-guide',
    name: 'TDD Guide',
    description: 'Test-driven development workflow with test generation, coverage analysis, and multi-framework support.',
    category: 'engineering-team',
    icon: '✅'
  },
  {
    id: 'tech-stack-evaluator',
    name: 'Tech Stack Evaluator',
    description: 'Technology stack evaluation and comparison with TCO analysis, security assessment, and ecosystem health scoring. Use when comparing frameworks, evaluating technology stacks, calculating total cost of ownership, assessing migration paths.',
    category: 'engineering-team',
    icon: '⚖️'
  },

  // Marketing
  {
    id: 'app-store-optimization',
    name: 'App Store Optimization',
    description: 'Complete App Store Optimization (ASO) toolkit for researching, optimizing, and tracking mobile app performance on Apple App Store and Google Play Store.',
    category: 'marketing-skill',
    icon: '📱'
  },
  {
    id: 'content-creator',
    name: 'Content Creator',
    description: 'Create SEO-optimized marketing content with consistent brand voice. Includes brand voice analyzer, SEO optimizer, content frameworks, and social media templates. Use when writing blog posts, creating social media content, analyzing brand voice, optimizing SEO.',
    category: 'marketing-skill',
    icon: '✍️'
  },
  {
    id: 'marketing-demand-acquisition',
    name: 'Marketing Demand & Acquisition',
    description: 'Multi-channel demand generation, paid media optimization, SEO strategy, and partnership programs for Series A+ startups.',
    category: 'marketing-skill',
    icon: '📈'
  },
  {
    id: 'marketing-strategy-pmm',
    name: 'Marketing Strategy & PMM',
    description: 'Product marketing skill for positioning, GTM strategy, competitive intelligence, and product launches. Covers April Dunford positioning, ICP definition, competitive battlecards, launch playbooks.',
    category: 'marketing-skill',
    icon: '🎯'
  },
  {
    id: 'social-media-analyzer',
    name: 'Social Media Analyzer',
    description: 'Social media campaign analysis and performance tracking. Calculates engagement rates, ROI, and benchmarks across platforms. Use for analyzing social media performance, measuring campaign ROI.',
    category: 'marketing-skill',
    icon: '📊'
  },

  // Product Team
  {
    id: 'agile-product-owner',
    name: 'Agile Product Owner',
    description: 'Agile product ownership toolkit including INVEST-compliant user story generation, sprint planning, backlog management, and velocity tracking. Use for story writing, sprint planning, stakeholder communication.',
    category: 'product-team',
    icon: '🏃'
  },
  {
    id: 'product-manager-toolkit',
    name: 'Product Manager Toolkit',
    description: 'Comprehensive toolkit for product managers including RICE prioritization, customer interview analysis, PRD templates, discovery frameworks. Use for feature prioritization, user research synthesis, requirement documentation.',
    category: 'product-team',
    icon: '📋'
  },
  {
    id: 'product-strategist',
    name: 'Product Strategist',
    description: 'Strategic product leadership toolkit for Head of Product including OKR cascade generation, market analysis, vision setting, and team scaling. Use for strategic planning, goal alignment, competitive analysis.',
    category: 'product-team',
    icon: '🎯'
  },
  {
    id: 'ui-design-system',
    name: 'UI Design System',
    description: 'UI design system toolkit including design token generation, component documentation, responsive design calculations, and developer handoff tools. Use for creating design systems, maintaining visual consistency.',
    category: 'product-team',
    icon: '🎨'
  },
  {
    id: 'ux-researcher-designer',
    name: 'UX Researcher & Designer',
    description: 'UX research and design toolkit including data-driven persona generation, journey mapping, usability testing frameworks, and research synthesis. Use for user research, persona creation, journey mapping.',
    category: 'product-team',
    icon: '🔬'
  },

  // Project Management
  {
    id: 'senior-pm',
    name: 'Senior Project Manager',
    description: 'Senior Project Manager for Software, SaaS, and digital web/mobile applications. Use for strategic planning, portfolio management, stakeholder alignment, risk management, roadmap development.',
    category: 'project-management',
    icon: '📊'
  },
  {
    id: 'scrum-master',
    name: 'Scrum Master',
    description: 'Scrum Master for agile software development teams. Use for sprint planning, daily standups, retrospectives, backlog refinement, velocity tracking, removing impediments, facilitating ceremonies, coaching teams on agile practices.',
    category: 'project-management',
    icon: '🏃‍♂️'
  },
  {
    id: 'atlassian-admin',
    name: 'Atlassian Administrator',
    description: 'Atlassian Administrator for managing and organizing Atlassian products, users, customization of the Atlassian suite, permissions, security, integrations, system configuration, and all administrative features. Use for user provisioning, global settings, security policies.',
    category: 'project-management',
    icon: '⚙️'
  },
  {
    id: 'atlassian-templates',
    name: 'Atlassian Templates Expert',
    description: 'Atlassian Template and Files Creator/Modifier expert for creating, modifying, and managing Jira and Confluence templates, blueprints, custom layouts, reusable components, and standardized content structures.',
    category: 'project-management',
    icon: '📄'
  },
  {
    id: 'confluence-expert',
    name: 'Confluence Expert',
    description: 'Atlassian Confluence expert for creating and managing spaces, knowledge bases, documentation, planning, product discovery, page layouts, macros, templates, and all Confluence features. Use for documentation strategy, space architecture.',
    category: 'project-management',
    icon: '📝'
  },
  {
    id: 'jira-expert',
    name: 'Jira Expert',
    description: 'Atlassian Jira expert for creating and managing projects, planning, product discovery, JQL queries, workflows, custom fields, automation, reporting, and all Jira features. Use for Jira project setup, configuration, advanced search, dashboard creation.',
    category: 'project-management',
    icon: '📌'
  }
]

// Helper functions
export function getSkillsByCategory(categoryId: string): PredefinedSkill[] {
  return PREDEFINED_SKILLS.filter(skill => skill.category === categoryId)
}

export function getSkillById(skillId: string): PredefinedSkill | undefined {
  return PREDEFINED_SKILLS.find(skill => skill.id === skillId)
}

export function searchSkills(query: string): PredefinedSkill[] {
  const lowerQuery = query.toLowerCase()
  return PREDEFINED_SKILLS.filter(skill =>
    skill.name.toLowerCase().includes(lowerQuery) ||
    skill.description.toLowerCase().includes(lowerQuery)
  )
}

export function getCategoryById(categoryId: string): SkillCategory | undefined {
  return SKILL_CATEGORIES.find(cat => cat.id === categoryId)
}
