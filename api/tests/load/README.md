# Synkora Load Testing with k6

Load testing suite for Synkora API endpoints using [k6](https://k6.io/).

## ⚠️ IMPORTANT: Avoid Real LLM API Costs

**Before running load tests**, start the API server with `LOAD_TEST_MODE=true` to use mock LLM responses instead of making real API calls:

```bash
# Option 1: Docker Compose (recommended)
LOAD_TEST_MODE=true docker-compose up -d api

# Option 2: Local development
cd api
LOAD_TEST_MODE=true uvicorn src.app:app --reload --port 5001
```

This enables a mock LLM provider that:
- Simulates realistic streaming responses with delays
- Exercises the full request pipeline (auth, rate limiting, RAG, etc.)
- **Does NOT call OpenAI, Anthropic, or any real LLM API**
- Costs $0 regardless of test volume

To disable mock mode and use real LLMs again:
```bash
# Docker Compose
docker-compose up -d api   # LOAD_TEST_MODE defaults to false

# Or explicitly
LOAD_TEST_MODE=false docker-compose up -d api
```

## Prerequisites

```bash
# Install k6
# macOS
brew install k6

# Ubuntu/Debian
sudo gpg -k
sudo gpg --no-default-keyring --keyring /usr/share/keyrings/k6-archive-keyring.gpg --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys C5AD17C747E3415A3642D57D77C6C491D6AC1D69
echo "deb [signed-by=/usr/share/keyrings/k6-archive-keyring.gpg] https://dl.k6.io/deb stable main" | sudo tee /etc/apt/sources.list.d/k6.list
sudo apt-get update
sudo apt-get install k6

# Docker
docker pull grafana/k6
```

## Quick Start

### 1. Get Auth Token

```bash
# Login to get JWT token
curl -X POST http://localhost:5001/console/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com", "password": "password"}'
```

### 2. Run Smoke Test (Quick Sanity Check)

```bash
# Health endpoints only (no auth required)
k6 run --env SCENARIO=smoke tests/load/main.js

# With authentication
k6 run --env SCENARIO=smoke \
  --env AUTH_TOKEN=<your-jwt-token> \
  --env AGENT_NAME=<your-agent-name> \
  tests/load/main.js
```

### 3. Run Load Test (Normal Traffic)

```bash
k6 run --env SCENARIO=load \
  --env AUTH_TOKEN=<your-jwt-token> \
  --env AGENT_NAME=<your-agent-name> \
  tests/load/main.js
```

### 4. Run Stress Test (Find Breaking Point)

```bash
k6 run --env SCENARIO=stress \
  --env AUTH_TOKEN=<your-jwt-token> \
  --env AGENT_NAME=<your-agent-name> \
  tests/load/main.js
```

### 5. Run Chat-Specific Stress Test

```bash
k6 run --env AUTH_TOKEN=<your-jwt-token> \
  --env AGENT_NAME=<your-agent-name> \
  --env MAX_VUS=100 \
  tests/load/chat-stress.js
```

## Test Files

| File | Description |
|------|-------------|
| `main.js` | Multi-endpoint load test with traffic distribution |
| `chat-stress.js` | Focused stress test for chat streaming endpoint |
| `config.js` | Shared configuration and test data generators |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `BASE_URL` | `http://localhost:5001` | API base URL |
| `AUTH_TOKEN` | - | JWT authentication token |
| `AGENT_NAME` | `test-agent` | Agent name for chat tests |
| `AGENT_ID` | - | Agent ID for widget tests |
| `KB_ID` | - | Knowledge base ID for search tests |
| `SCENARIO` | `smoke` | Test scenario (smoke/load/stress/spike/soak) |
| `MAX_VUS` | `50` | Max virtual users for chat-stress.js |

## Test Scenarios

### Smoke Test
- **Duration**: 30 seconds
- **VUs**: 1
- **Purpose**: Verify endpoints work correctly

### Load Test
- **Duration**: 9 minutes
- **VUs**: Ramp 0 → 50 → 0
- **Purpose**: Normal expected traffic

### Stress Test
- **Duration**: 13 minutes
- **VUs**: Ramp 0 → 50 → 100 → 200 → 300 → 0
- **Purpose**: Find breaking point

### Spike Test
- **Duration**: 5 minutes
- **VUs**: 10 → 200 (sudden spike) → 10
- **Purpose**: Test sudden traffic surges

### Soak Test
- **Duration**: 30 minutes
- **VUs**: 30 (constant)
- **Purpose**: Detect memory leaks

## Known Limits

From codebase analysis:

| Resource | Limit | Config Location |
|----------|-------|-----------------|
| DB Pool | 75 + 50 overflow (125 total) | `api/src/config/database.py` |
| Redis Connections | 200 | `api/src/config/redis.py` |
| WebSocket Per User | 10 | `api/src/core/websocket.py` |
| WebSocket Per Tenant | 500 | `api/src/core/websocket.py` |
| WebSocket Total | 10,000 | `api/src/core/websocket.py` |
| Vector DB Pool | 5 per config | `api/src/services/performance/connection_pool.py` |

### Rate Limits

| Endpoint Pattern | Limit |
|-----------------|-------|
| `/api/v1/agents/` | 60 req/min |
| `/v1/chat/` | 30 req/min |
| `/api/v1/files/upload` | 20 req/min |
| `/api/v1/data-analysis/upload` | 10 req/min |
| `/webhook/` | 100 req/min |
| `/health` | 1000 req/min |
| Default | 100 req/min |

## Benchmark Results (March 2026)

Test environment: Single API instance, LOAD_TEST_MODE=true (mock LLM), Docker Compose.

### Smoke Test (1 VU, 30s)

| Metric | Value |
|--------|-------|
| Success Rate | 100% (4/4 requests) |
| Checks Passed | 100% (13/13) |
| Failed Requests | 0% |
| Chat Stream p(95) | 10.62s |
| List Agents | 636ms |

### Load Test (50 VUs, 9 min)

| Metric | Value |
|--------|-------|
| Success Rate | 99.89% (4579/4584) |
| Checks Passed | 99.93% (13744/13753) |
| Failed Requests | 0.04% (2/4585) |
| Total Requests | 4585 (8.4 req/s) |
| Errors | 5 |

| Endpoint | avg | p(90) | p(95) | p(99) | Threshold |
|----------|-----|-------|-------|-------|-----------|
| Chat Stream | 11.16s | 13.77s | 14.29s | 15.9s | p(95)<30s |
| List Agents | 487ms | 930ms | 979ms | 1.02s | p(95)<2s |
| Health | 460ms | 925ms | 980ms | 1.2s | p(95)<2s |
| Ready | 977ms | 1.01s | 1.02s | 1.11s | p(95)<2s |

All thresholds passed.

### Stress Test (300 VUs, 13 min)

Connection pool exhaustion observed at peak concurrency (300 VUs). The `QueuePool` limit was reached, causing 500 errors on some requests. This is expected at the designed stress limit for a single instance.

**Breaking point**: ~200 concurrent VUs per single API instance. Beyond this, horizontal scaling (multiple pods) is required.

### Notes

- Chat stream durations include mock LLM response time (~10s simulated streaming delay)
- Session isolation pattern uses multiple DB connections per chat request (main + prompt builder + parallel resource loading)
- Redis caching (agent config, tools, context files) significantly reduces DB pressure under load
- For production at scale, deploy multiple API pods behind a load balancer

## Interpreting Results

### Key Metrics

```
http_req_duration.............: avg=2.94s   p(95)=12.48s  p(99)=14.35s
http_req_failed...............: 0.04%
chat_stream_duration..........: avg=11.16s  p(95)=14.29s
success_rate..................: 99.89%
errors........................: 5
```

### What to Look For

1. **http_req_duration p(95)**: Should be < 2s for most endpoints
2. **http_req_failed**: Should be < 5% under normal load
3. **chat_stream_duration**: Includes LLM response time, < 30s for p(95)
4. **rate_limited count**: If high, rate limits may be too aggressive
5. **errors**: Any consistent errors indicate bugs

### Red Flags

- **p(99) >> p(95)**: Indicates outliers, possible resource exhaustion
- **Failed rate increasing with VUs**: System hitting limits
- **TTFB increasing linearly with VUs**: DB connection pool exhaustion
- **Consistent 5xx errors**: Server-side issues
- **QueuePool timeout errors**: Need larger pool or horizontal scaling

## Grafana Integration

Export results to Grafana Cloud:

```bash
K6_CLOUD_TOKEN=<token> k6 cloud tests/load/main.js
```

Or output to InfluxDB:

```bash
k6 run --out influxdb=http://localhost:8086/k6 tests/load/main.js
```

## CI/CD Integration

```yaml
# .github/workflows/load-test.yml
name: Load Test
on:
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM
  workflow_dispatch:

jobs:
  load-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: grafana/k6-action@v0.3.1
        with:
          filename: api/tests/load/main.js
        env:
          SCENARIO: load
          BASE_URL: ${{ secrets.STAGING_URL }}
          AUTH_TOKEN: ${{ secrets.LOAD_TEST_TOKEN }}
          AGENT_NAME: load-test-agent
```
