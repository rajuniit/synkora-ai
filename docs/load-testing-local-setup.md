# Load Testing - Local Development Setup

This guide explains how to run the load testing infrastructure locally using Docker Compose.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         LOCAL DOCKER ENVIRONMENT                             │
│                                                                              │
│  ┌─────────────────────────────┐    ┌─────────────────────────────────────┐ │
│  │   MAIN SERVICES             │    │   LOAD TESTING SERVICES             │ │
│  │                             │    │                                      │ │
│  │  ┌─────────┐ ┌───────────┐ │    │  ┌─────────────┐ ┌─────────────┐    │ │
│  │  │   API   │ │   Redis   │ │    │  │  LLM Proxy  │ │  K6 Runner  │    │ │
│  │  │ :5001   │ │  :6379    │ │    │  │   :8090     │ │             │    │ │
│  │  └─────────┘ └───────────┘ │    │  └─────────────┘ └─────────────┘    │ │
│  │                             │    │                                      │ │
│  │  ┌─────────┐ ┌───────────┐ │    │  ┌─────────────┐ ┌─────────────┐    │ │
│  │  │Postgres │ │  Celery   │ │    │  │Redis (LT)   │ │Celery (LT)  │    │ │
│  │  │ :5432   │ │  Worker   │ │    │  │  :6381      │ │  Worker     │    │ │
│  │  └─────────┘ └───────────┘ │    │  └─────────────┘ └─────────────┘    │ │
│  └─────────────────────────────┘    └─────────────────────────────────────┘ │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Quick Start

### 1. Start All Services (Main + Load Testing)

```bash
# Start everything
docker-compose -f docker-compose.yml -f docker-compose.load-testing.yml up -d

# View logs
docker-compose -f docker-compose.yml -f docker-compose.load-testing.yml logs -f llm-proxy k6-runner
```

### 2. Start Only Load Testing Services

If you're running the main API locally (not in Docker):

```bash
# Start just the load testing services
docker-compose -f docker-compose.yml -f docker-compose.load-testing.yml up -d \
  llm-proxy redis-loadtest k6-runner
```

### 3. Verify Services

```bash
# Check LLM Proxy health
curl http://localhost:8090/health
# Expected: {"status":"healthy","service":"llm-proxy","mode":"standalone"}

# Check API documentation
open http://localhost:8090/docs
```

## Using the LLM Proxy

### Step 1: Create a Proxy Configuration

```bash
# Via the UI
open http://localhost:3005/load-testing/proxy/create

# Or via API
curl -X POST http://localhost:5001/api/v1/proxy/configs \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "name": "Test Proxy",
    "provider": "openai",
    "rate_limit": 1000,
    "mock_config": {
      "latency": {
        "ttft_min_ms": 100,
        "ttft_max_ms": 300
      },
      "response": {
        "min_tokens": 50,
        "max_tokens": 200
      }
    }
  }'
```

This returns an API key like: `sk-proxy-abc123...`

### Step 2: Configure Your AI Agent

Change your agent's LLM configuration to use the proxy:

**Before (Production):**
```python
client = OpenAI(
    api_key="sk-real-openai-key",
    base_url="https://api.openai.com/v1"
)
```

**After (Load Testing):**
```python
client = OpenAI(
    api_key="sk-proxy-abc123...",  # Proxy API key
    base_url="http://localhost:8090/proxy/v1"  # Local proxy
)
```

### Step 3: Test the Proxy

```bash
# Test OpenAI-compatible endpoint
curl http://localhost:8090/proxy/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-proxy-abc123..." \
  -d '{
    "model": "gpt-4",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

You should get a mock response without any real API calls!

## Running Load Tests

### Option 1: Via the Web UI

1. Go to http://localhost:3005/load-testing
2. Create a new load test
3. Configure target URL, load settings, and proxy
4. Click "Run Test"
5. Watch real-time results in the dashboard

### Option 2: Via API

```bash
# 1. Create a load test
curl -X POST http://localhost:5001/api/v1/load-tests \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "name": "My Load Test",
    "target_url": "http://your-agent:8000/api/chat",
    "target_type": "openai_compatible",
    "proxy_config_id": "PROXY_CONFIG_ID",
    "load_config": {
      "stages": [
        {"duration": "30s", "target": 10},
        {"duration": "1m", "target": 50},
        {"duration": "30s", "target": 0}
      ]
    }
  }'

# 2. Start a test run
curl -X POST http://localhost:5001/api/v1/test-runs/LOAD_TEST_ID/run \
  -H "Authorization: Bearer YOUR_TOKEN"

# 3. Get results
curl http://localhost:5001/api/v1/test-runs/TEST_RUN_ID/results \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Option 3: Direct K6 Execution

You can also run K6 directly against the proxy:

```bash
# Create a simple K6 script
cat > test.js << 'EOF'
import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '30s', target: 10 },
    { duration: '1m', target: 50 },
    { duration: '30s', target: 0 },
  ],
};

export default function() {
  const payload = JSON.stringify({
    model: 'gpt-4',
    messages: [{ role: 'user', content: 'Hello!' }],
  });

  const res = http.post('http://localhost:8090/proxy/v1/chat/completions', payload, {
    headers: {
      'Content-Type': 'application/json',
      'Authorization': 'Bearer sk-proxy-abc123...',
    },
  });

  check(res, {
    'status is 200': (r) => r.status === 200,
  });

  sleep(1);
}
EOF

# Run the test
docker-compose -f docker-compose.yml -f docker-compose.load-testing.yml \
  exec k6-runner k6 run /scripts/test.js
```

## Service Endpoints

| Service | Port | Description |
|---------|------|-------------|
| Synkora API | 5001 | Main API |
| Synkora Web | 3005 | Frontend (if running) |
| LLM Proxy | 8090 | Mock LLM endpoints |
| Redis (Load Test) | 6381 | Dedicated Redis for load testing |

## LLM Proxy Endpoints

| Endpoint | Provider | Description |
|----------|----------|-------------|
| `POST /proxy/v1/chat/completions` | OpenAI | Chat completions |
| `POST /proxy/v1/messages` | Anthropic | Messages API |
| `POST /proxy/v1/models/:model:generateContent` | Google | Generate content |
| `GET /health` | - | Health check |
| `GET /docs` | - | API documentation |

## Troubleshooting

### LLM Proxy Not Starting

```bash
# Check logs
docker-compose -f docker-compose.yml -f docker-compose.load-testing.yml \
  logs llm-proxy

# Common issues:
# - Database not ready: Wait for postgres to be healthy
# - Port conflict: Check if 8090 is already in use
```

### K6 Tests Failing

```bash
# Check K6 runner logs
docker-compose -f docker-compose.yml -f docker-compose.load-testing.yml \
  logs k6-runner

# Enter the container for debugging
docker-compose -f docker-compose.yml -f docker-compose.load-testing.yml \
  exec k6-runner bash
```

### Connection Refused

Make sure you're using the Docker network hostnames:
- From host machine: `localhost:8090`
- From Docker containers: `llm-proxy:8080`

## Cleanup

```bash
# Stop all load testing services
docker-compose -f docker-compose.yml -f docker-compose.load-testing.yml \
  down llm-proxy redis-loadtest k6-runner celery-worker-loadtest

# Remove volumes (clears all data)
docker-compose -f docker-compose.yml -f docker-compose.load-testing.yml \
  down -v
```

## Performance Tuning

For high-load tests, increase container resources:

```yaml
# In docker-compose.load-testing.yml
llm-proxy:
  deploy:
    resources:
      limits:
        memory: 4G
        cpus: '4'
```

Or scale the proxy:

```bash
docker-compose -f docker-compose.yml -f docker-compose.load-testing.yml \
  up -d --scale llm-proxy=3
```
