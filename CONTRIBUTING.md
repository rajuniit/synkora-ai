# Contributing to Synkora

First off, thank you for considering contributing to Synkora! It's people like you that make Synkora such a great tool for building AI agents.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Architecture Overview](#architecture-overview)
- [How Can I Contribute?](#how-can-i-contribute)
  - [Reporting Bugs](#reporting-bugs)
  - [Suggesting Enhancements](#suggesting-enhancements)
  - [Your First Code Contribution](#your-first-code-contribution)
  - [Pull Requests](#pull-requests)
- [Development Setup](#development-setup)
- [Style Guidelines](#style-guidelines)
  - [Git Commit Messages](#git-commit-messages)
  - [Python Style Guide](#python-style-guide)
  - [TypeScript/JavaScript Style Guide](#typescriptjavascript-style-guide)
- [Testing](#testing)
- [Documentation](#documentation)

## Code of Conduct

This project and everyone participating in it is governed by our [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code. Please report unacceptable behavior to the project maintainers.

## Architecture Overview

Before contributing, familiarize yourself with the codebase architecture. See [ARCHITECTURE.md](ARCHITECTURE.md) for the full technical analysis.

### Backend Structure (`api/src/`)

```
api/src/
├── app.py              # Application factory & middleware stack
├── router_registry.py  # Declarative router registration (45+ routes)
├── config/             # Pydantic Settings (modular composition)
├── controllers/        # HTTP handlers (thin, delegate to services)
├── services/           # Business logic & orchestration
├── models/             # SQLAlchemy ORM (70+ models, mixin-based)
├── schemas/            # Pydantic request/response validation
├── middleware/         # Auth, rate limiting, CSRF, security headers
├── tasks/              # Celery background jobs
└── core/               # Database, WebSocket, errors, providers
```

### Frontend Structure (`web/`)

```
web/
├── app/                # Next.js 15 App Router pages
├── components/         # React components (chat, agents, UI)
├── lib/
│   ├── api/           # Domain-separated API modules
│   ├── store/         # Zustand state stores
│   ├── auth/          # Secure token storage
│   ├── hooks/         # Custom React hooks
│   └── types/         # TypeScript definitions
```

### Key Design Patterns

| Pattern | Location | Purpose |
|---------|----------|---------|
| **Service Layer** | `services/` | Business logic separated from HTTP |
| **Mixin Pattern** | `models/base.py` | Composable model traits (`TenantMixin`, `SoftDeleteMixin`) |
| **Circuit Breaker** | `services/performance/` | External service resilience |
| **Dead Letter Queue** | `celery_app.py` | Failed task recovery |
| **Pub/Sub** | `core/websocket.py` | Cross-pod WebSocket messaging |

### Where to Find Things

| Looking for... | Location |
|----------------|----------|
| API endpoints | `api/src/controllers/` |
| Database models | `api/src/models/` |
| Business logic | `api/src/services/` |
| Background tasks | `api/src/tasks/` |
| Frontend pages | `web/app/` |
| API client | `web/lib/api/` |
| State management | `web/lib/store/` |
| Tests | `api/tests/`, `web/lib/__tests__/` |
| Load tests | `api/tests/load/` |

## How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check the existing issues as you might find out that you don't need to create one. When you are creating a bug report, please include as many details as possible:

**Bug Report Template:**

```markdown
**Describe the bug**
A clear and concise description of what the bug is.

**To Reproduce**
Steps to reproduce the behavior:
1. Go to '...'
2. Click on '....'
3. Scroll down to '....'
4. See error

**Expected behavior**
A clear and concise description of what you expected to happen.

**Screenshots**
If applicable, add screenshots to help explain your problem.

**Environment:**
- OS: [e.g. macOS, Ubuntu]
- Python Version: [e.g. 3.11]
- Node Version: [e.g. 18.17]
- Docker Version: [e.g. 24.0.6]

**Additional context**
Add any other context about the problem here.
```

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. When creating an enhancement suggestion, please include:

- **Use a clear and descriptive title**
- **Provide a detailed description** of the suggested enhancement
- **Explain why this enhancement would be useful** to most Synkora users
- **List some examples** of how this enhancement would be used
- **Specify which version** of Synkora you're using

### Your First Code Contribution

Unsure where to begin contributing to Synkora? You can start by looking through `good-first-issue` and `help-wanted` issues:

- **good-first-issue** - issues which should only require a few lines of code
- **help-wanted** - issues which are a bit more involved than beginner issues

### Pull Requests

The process described here has several goals:

- Maintain Synkora's quality
- Fix problems that are important to users
- Engage the community in working toward the best possible Synkora
- Enable a sustainable system for maintainers to review contributions

Please follow these steps:

1. **Fork the repo** and create your branch from `main`
2. **Make your changes** following our style guidelines
3. **Add tests** if you've added code that should be tested
4. **Ensure the test suite passes**
5. **Update documentation** as needed
6. **Create a pull request** with a clear title and description

**Pull Request Template:**

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update

## Testing
- [ ] I have added tests that prove my fix is effective or that my feature works
- [ ] All new and existing tests passed locally
- [ ] I have tested this in a development environment

## Checklist
- [ ] My code follows the style guidelines of this project
- [ ] I have performed a self-review of my own code
- [ ] I have commented my code, particularly in hard-to-understand areas
- [ ] I have made corresponding changes to the documentation
- [ ] My changes generate no new warnings
- [ ] Any dependent changes have been merged and published

## Screenshots (if applicable)
```

## Development Setup

### Prerequisites

- Docker and Docker Compose
- Python 3.11+ with uv package manager
- Node.js 18+ with pnpm
- PostgreSQL 14+ (for local development)
- Redis 7+

### Backend Setup

```bash
cd api

# Install dependencies
uv sync

# Set up environment
cp .env.example .env
# Edit .env with your local configuration

# Run database migrations
alembic upgrade head

# Create super admin
python create_super_admin.py

# Run tests
pytest

# Run development server
uvicorn src.app:app --reload --host 0.0.0.0 --port 5001
```

### Frontend Setup

```bash
cd web

# Install dependencies
pnpm install

# Set up environment
cp .env.example .env.local

# Run development server
pnpm dev

# Run type checking
pnpm type-check

# Run linting
pnpm lint
```

### Docker Development

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f api

# Run migrations in container
docker-compose exec api alembic upgrade head

# Run tests in container
docker-compose exec api pytest
```

## Style Guidelines

### Git Commit Messages

- Use the present tense ("Add feature" not "Added feature")
- Use the imperative mood ("Move cursor to..." not "Moves cursor to...")
- Limit the first line to 72 characters or less
- Reference issues and pull requests liberally after the first line
- Consider starting the commit message with an applicable emoji:
  - 🎨 `:art:` when improving the format/structure of the code
  - 🐎 `:racehorse:` when improving performance
  - 📝 `:memo:` when writing docs
  - 🐛 `:bug:` when fixing a bug
  - 🔥 `:fire:` when removing code or files
  - ✅ `:white_check_mark:` when adding tests
  - 🔒 `:lock:` when dealing with security
  - ⬆️ `:arrow_up:` when upgrading dependencies
  - ⬇️ `:arrow_down:` when downgrading dependencies

**Example:**

```
✨ Add voice transcription feature

- Integrate ElevenLabs API for speech-to-text
- Add VoiceInput component to chat interface
- Update agent configuration to support voice
- Add tests for voice transcription service

Closes #123
```

### Python Style Guide

We follow PEP 8 with some modifications. We use **Ruff** for linting and formatting.

**Key Points:**

- **Line length**: Maximum 100 characters (not 79)
- **Imports**: Use absolute imports, organize with `isort`
- **Type hints**: Use type hints for all function signatures
- **Docstrings**: Use Google-style docstrings for all public functions/classes
- **Naming**:
  - Classes: `PascalCase`
  - Functions/Variables: `snake_case`
  - Constants: `UPPER_SNAKE_CASE`

**Example:**

```python
from typing import Optional

from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.models.agent import Agent


class AgentService:
    """Service for managing AI agents.
    
    This service handles CRUD operations for agents and provides
    additional functionality for agent configuration and deployment.
    """
    
    def __init__(self, db: Session):
        """Initialize the agent service.
        
        Args:
            db: Database session for queries
        """
        self.db = db
    
    def create_agent(
        self,
        name: str,
        description: Optional[str] = None,
    ) -> Agent:
        """Create a new agent.
        
        Args:
            name: The name of the agent
            description: Optional description of the agent
            
        Returns:
            The newly created agent
            
        Raises:
            ValueError: If agent name is invalid
        """
        if not name or len(name) < 3:
            raise ValueError("Agent name must be at least 3 characters")
        
        agent = Agent(name=name, description=description)
        self.db.add(agent)
        self.db.commit()
        self.db.refresh(agent)
        
        return agent
```

**Code Quality Commands:**

```bash
# Format code
ruff format .

# Lint code
ruff check .

# Fix linting issues automatically
ruff check --fix .

# Type checking
basedpyright
```

### TypeScript/JavaScript Style Guide

We use **ESLint** and **Prettier** for code quality and formatting.

**Key Points:**

- **Line length**: Maximum 100 characters
- **Semicolons**: Use semicolons
- **Quotes**: Use single quotes for strings (unless template literals)
- **Arrow functions**: Prefer arrow functions for callbacks
- **Async/await**: Prefer async/await over promises
- **Types**: Always provide types (no `any` unless absolutely necessary)
- **Naming**:
  - Components: `PascalCase`
  - Functions/Variables: `camelCase`
  - Constants: `UPPER_SNAKE_CASE`
  - Interfaces/Types: `PascalCase`

**Example:**

```typescript
import { useState, useEffect } from 'react';
import type { Agent } from '@/types/agent';

interface AgentCardProps {
  agent: Agent;
  onSelect?: (agent: Agent) => void;
}

/**
 * AgentCard component displays a summary of an AI agent
 * with options to view details or perform actions.
 */
export function AgentCard({ agent, onSelect }: AgentCardProps) {
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    // Component initialization logic
  }, [agent.id]);

  const handleClick = async () => {
    setIsLoading(true);
    try {
      await fetchAgentDetails(agent.id);
      onSelect?.(agent);
    } catch (error) {
      console.error('Failed to fetch agent details:', error);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="agent-card" onClick={handleClick}>
      <h3>{agent.name}</h3>
      <p>{agent.description}</p>
      {isLoading && <Spinner />}
    </div>
  );
}
```

**Code Quality Commands:**

```bash
# Lint
pnpm lint

# Fix linting issues
pnpm lint:fix

# Type check
pnpm type-check

# Format (if Prettier is configured separately)
pnpm format
```

## Testing

### Backend Testing

We use **pytest** for backend testing.

**Writing Tests:**

```python
import pytest
from sqlalchemy.orm import Session

from src.services.agents.agent_service import AgentService
from src.models.agent import Agent


def test_create_agent(db: Session):
    """Test creating a new agent."""
    service = AgentService(db)
    
    agent = service.create_agent(
        name="Test Agent",
        description="A test agent"
    )
    
    assert agent.id is not None
    assert agent.name == "Test Agent"
    assert agent.description == "A test agent"


def test_create_agent_invalid_name(db: Session):
    """Test that creating an agent with invalid name raises error."""
    service = AgentService(db)
    
    with pytest.raises(ValueError, match="at least 3 characters"):
        service.create_agent(name="ab")
```

**Running Tests:**

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/unit/services/test_agent_service.py

# Run tests matching pattern
pytest -k "test_create"

# Run with verbose output
pytest -v
```

### Frontend Testing

We encourage adding tests for new features using React Testing Library or similar tools.

```bash
# Run tests (when configured)
pnpm test

# Run tests in watch mode
pnpm test:watch

# Run tests with coverage
pnpm test:coverage
```

## Documentation

### Code Documentation

- **Python**: Use Google-style docstrings
- **TypeScript**: Use JSDoc comments for complex functions
- **README files**: Update relevant README files in subdirectories

### API Documentation

- FastAPI automatically generates OpenAPI documentation
- Ensure all endpoints have proper descriptions and examples
- Document request/response models with Pydantic

### User Documentation

- Update the main README.md if adding user-facing features
- Add examples and usage instructions
- Include screenshots for UI changes

## Questions?

Don't hesitate to ask questions by:

- Opening an issue with the `question` label
- Reaching out to maintainers
- Checking existing documentation

## License

By contributing to Synkora, you agree that your contributions will be licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---

**Thank you for contributing to Synkora! 🚀**
