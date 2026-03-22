#!/bin/bash
#
# Synkora Load Test Runner
#
# IMPORTANT: Start the API server with LOAD_TEST_MODE=true to avoid real LLM calls:
#
#   Docker Compose:
#     LOAD_TEST_MODE=true docker-compose up -d api
#
#   Local:
#     LOAD_TEST_MODE=true uvicorn src.app:app --reload --port 5001
#
# Usage:
#   ./run.sh smoke                  # Quick sanity check
#   ./run.sh load                   # Normal load test
#   ./run.sh stress                 # Find breaking point
#   ./run.sh spike                  # Sudden traffic surge
#   ./run.sh soak                   # Memory leak detection
#   ./run.sh chat                   # Chat-focused stress test
#
# Environment:
#   AUTH_TOKEN  - JWT token (required for authenticated endpoints)
#   AGENT_NAME  - Agent name to test
#   BASE_URL    - API URL (default: http://localhost:5001)
#   MAX_VUS     - Max virtual users for chat test (default: 50)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_URL="${BASE_URL:-http://localhost:5001}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_header() {
    echo -e "${GREEN}"
    echo "╔═══════════════════════════════════════════════════════════════╗"
    echo "║             Synkora Load Testing Suite                        ║"
    echo "╚═══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

check_k6() {
    if ! command -v k6 &> /dev/null; then
        echo -e "${RED}Error: k6 is not installed${NC}"
        echo "Install with: brew install k6"
        exit 1
    fi
}

check_server() {
    echo -e "${YELLOW}Checking server at ${BASE_URL}...${NC}"
    if ! curl -s "${BASE_URL}/health" > /dev/null 2>&1; then
        echo -e "${RED}Error: Server not reachable at ${BASE_URL}${NC}"
        echo "Make sure the API is running: uvicorn src.app:app --reload --port 5001"
        exit 1
    fi
    echo -e "${GREEN}Server is reachable${NC}"
}

run_test() {
    local scenario=$1
    local script=$2

    echo -e "\n${YELLOW}Running ${scenario} test...${NC}\n"

    local env_args="--env BASE_URL=${BASE_URL}"

    if [ -n "$AUTH_TOKEN" ]; then
        env_args="$env_args --env AUTH_TOKEN=${AUTH_TOKEN}"
    fi

    if [ -n "$AGENT_NAME" ]; then
        env_args="$env_args --env AGENT_NAME=${AGENT_NAME}"
    fi

    if [ -n "$AGENT_ID" ]; then
        env_args="$env_args --env AGENT_ID=${AGENT_ID}"
    fi

    if [ -n "$KB_ID" ]; then
        env_args="$env_args --env KB_ID=${KB_ID}"
    fi

    if [ -n "$MAX_VUS" ]; then
        env_args="$env_args --env MAX_VUS=${MAX_VUS}"
    fi

    if [ "$script" = "chat-stress.js" ]; then
        k6 run $env_args "${SCRIPT_DIR}/${script}"
    else
        k6 run --env SCENARIO=${scenario} $env_args "${SCRIPT_DIR}/${script}"
    fi
}

print_usage() {
    echo "Usage: $0 <scenario>"
    echo ""
    echo "Scenarios:"
    echo "  smoke   - Quick sanity check (30s, 1 VU)"
    echo "  load    - Normal load test (9min, up to 50 VUs)"
    echo "  stress  - Find breaking point (13min, up to 300 VUs)"
    echo "  spike   - Sudden traffic surge (5min, 10→200 VUs)"
    echo "  soak    - Memory leak detection (30min, 30 VUs)"
    echo "  chat    - Chat-focused stress test (9min, configurable VUs)"
    echo ""
    echo "Environment Variables:"
    echo "  AUTH_TOKEN  - JWT token (required for authenticated endpoints)"
    echo "  AGENT_NAME  - Agent name to test"
    echo "  BASE_URL    - API URL (default: http://localhost:5001)"
    echo "  MAX_VUS     - Max virtual users for chat test (default: 50)"
    echo ""
    echo "Examples:"
    echo "  AUTH_TOKEN=eyJ... AGENT_NAME=my-agent $0 smoke"
    echo "  BASE_URL=https://api.staging.example.com $0 load"
}

main() {
    print_header
    check_k6

    case "${1:-}" in
        smoke|load|stress|spike|soak)
            check_server
            run_test "$1" "main.js"
            ;;
        chat)
            if [ -z "$AUTH_TOKEN" ] || [ -z "$AGENT_NAME" ]; then
                echo -e "${RED}Error: AUTH_TOKEN and AGENT_NAME are required for chat test${NC}"
                echo ""
                echo "Usage: AUTH_TOKEN=<jwt> AGENT_NAME=<name> $0 chat"
                exit 1
            fi
            check_server
            run_test "chat" "chat-stress.js"
            ;;
        -h|--help|help)
            print_usage
            ;;
        "")
            echo -e "${YELLOW}No scenario specified, running smoke test...${NC}"
            check_server
            run_test "smoke" "main.js"
            ;;
        *)
            echo -e "${RED}Unknown scenario: $1${NC}"
            print_usage
            exit 1
            ;;
    esac
}

main "$@"
