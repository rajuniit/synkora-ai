"""
K6 Script Generator

Generates K6 JavaScript load test scripts from configuration.
"""

import json
import logging
from typing import Any

from src.models.load_test import LoadTest, TargetType
from src.models.test_scenario import TestScenario

logger = logging.getLogger(__name__)


class K6ScriptGenerator:
    """
    Generates K6 load test scripts from LoadTest configuration.

    Supports OpenAI, Anthropic, and custom API formats.
    """

    def __init__(self, load_test: LoadTest, scenarios: list[TestScenario] | None = None):
        """
        Initialize the generator.

        Args:
            load_test: The load test configuration
            scenarios: Optional list of test scenarios
        """
        self.load_test = load_test
        self.scenarios = scenarios or []

    def generate(self) -> str:
        """
        Generate the complete K6 script.

        Returns:
            str: The K6 JavaScript code
        """
        script_parts = [
            self._generate_imports(),
            self._generate_options(),
            self._generate_constants(),
            self._generate_helpers(),
            self._generate_scenarios_data(),
            self._generate_setup(),
            self._generate_default_function(),
            self._generate_teardown(),
        ]

        return "\n\n".join(filter(None, script_parts))

    def _generate_imports(self) -> str:
        """Generate import statements."""
        return """import http from 'k6/http';
import { check, sleep } from 'k6';
import { Counter, Rate, Trend, Gauge } from 'k6/metrics';
import { randomItem, randomIntBetween } from 'https://jslib.k6.io/k6-utils/1.2.0/index.js';"""

    def _generate_options(self) -> str:
        """Generate K6 options configuration."""
        load_config = self.load_test.load_config or {}

        # Build stages from config
        stages = load_config.get(
            "stages",
            [
                {"duration": "30s", "target": 10},
                {"duration": "1m", "target": 50},
                {"duration": "30s", "target": 0},
            ],
        )

        stages_js = json.dumps(stages, indent=2)

        # Build thresholds
        thresholds = load_config.get(
            "thresholds",
            {
                "http_req_duration": ["p(95)<5000", "p(99)<10000"],
                "http_req_failed": ["rate<0.1"],
                "ttft": ["p(95)<2000"],
            },
        )

        thresholds_js = json.dumps(thresholds, indent=2)

        executor = load_config.get("executor", "ramping-vus")
        max_vus = load_config.get("max_vus", 100)

        return f"""// K6 Options
export const options = {{
  scenarios: {{
    load_test: {{
      executor: '{executor}',
      startVUs: 0,
      stages: {stages_js},
      gracefulRampDown: '30s',
    }},
  }},
  thresholds: {thresholds_js},
  maxVUs: {max_vus},
  summaryTrendStats: ['avg', 'min', 'med', 'max', 'p(50)', 'p(90)', 'p(95)', 'p(99)'],
}};"""

    def _generate_constants(self) -> str:
        """Generate constant definitions."""
        target_url = self.load_test.target_url
        auth_config = self.load_test.get_auth_config()
        # Build headers
        headers = {"Content-Type": "application/json"}

        if auth_config:
            api_key = auth_config.get("api_key", "")
            if api_key:
                if self.load_test.target_type == TargetType.ANTHROPIC:
                    headers["x-api-key"] = api_key
                    headers["anthropic-version"] = "2023-06-01"
                elif self.load_test.target_type == TargetType.GOOGLE:
                    headers["x-goog-api-key"] = api_key
                else:
                    headers["Authorization"] = f"Bearer {api_key}"

            # Add custom headers
            custom_headers = auth_config.get("headers", {})
            headers.update(custom_headers)

        headers_js = json.dumps(headers, indent=2)

        # Get think time config
        load_config = self.load_test.load_config or {}
        think_time_min = load_config.get("think_time_min_ms", 1000)
        think_time_max = load_config.get("think_time_max_ms", 3000)

        return f"""// Constants
const TARGET_URL = '{target_url}';
const HEADERS = {headers_js};
const THINK_TIME_MIN_MS = {think_time_min};
const THINK_TIME_MAX_MS = {think_time_max};"""

    def _generate_helpers(self) -> str:
        """Generate helper functions."""
        return """// Custom Metrics
const ttft = new Trend('ttft', true);  // Time to First Token
const tokensPerSec = new Trend('tokens_per_sec');
const totalTokens = new Counter('total_tokens');
const requestErrors = new Rate('request_errors');

// Helper Functions
function randomThinkTime() {
  return randomIntBetween(THINK_TIME_MIN_MS, THINK_TIME_MAX_MS) / 1000;
}

function generatePrompt(template, variables) {
  if (!template) return 'Hello, how are you?';

  let result = template;
  for (const [key, config] of Object.entries(variables || {})) {
    const pattern = new RegExp(`{{${key}}}`, 'g');

    let value;
    if (config.type === 'list' && config.values) {
      value = randomItem(config.values);
    } else if (config.type === 'random_int') {
      value = randomIntBetween(config.min || 0, config.max || 100).toString();
    } else {
      value = '';
    }

    result = result.replace(pattern, value);
  }

  return result;
}

function buildPayload(scenario, requestConfig) {
  const prompts = scenario.prompts || [];
  const messages = prompts.map(p => ({
    role: p.role || 'user',
    content: p.is_template ? generatePrompt(p.content, scenario.variables) : p.content,
  }));

  if (messages.length === 0) {
    messages.push({ role: 'user', content: 'Hello, can you help me with a question?' });
  }

  // Merge with request config
  const overrides = scenario.request_overrides || {};

  return {
    model: overrides.model || requestConfig.model || 'gpt-4-turbo',
    messages: messages,
    temperature: overrides.temperature || requestConfig.temperature || 0.7,
    max_tokens: overrides.max_tokens || requestConfig.max_tokens || 500,
    stream: overrides.stream !== undefined ? overrides.stream : (requestConfig.stream || false),
  };
}

function measureTTFT(response) {
  // Parse timing from response headers if available
  const timing = response.timings;
  if (timing) {
    // TTFT approximation: time to receive first bytes
    return timing.waiting + timing.receiving * 0.1;
  }
  return response.timings.duration;
}"""

    def _generate_scenarios_data(self) -> str:
        """Generate scenario data array."""
        if not self.scenarios:
            # Default scenario if none provided
            default_scenario = {
                "name": "default",
                "weight": 1,
                "prompts": [{"role": "user", "content": "Hello!", "is_template": False}],
                "variables": {},
                "request_overrides": {},
            }
            scenarios_js = json.dumps([default_scenario], indent=2)
        else:
            scenarios_data = []
            for s in self.scenarios:
                scenarios_data.append(
                    {
                        "name": s.name,
                        "weight": s.weight,
                        "prompts": s.prompts or [],
                        "variables": s.variables or {},
                        "request_overrides": s.request_overrides or {},
                    }
                )
            scenarios_js = json.dumps(scenarios_data, indent=2)

        request_config = json.dumps(self.load_test.request_config or {}, indent=2)

        return f"""// Scenarios
const SCENARIOS = {scenarios_js};

// Request Config
const REQUEST_CONFIG = {request_config};

// Build weighted scenario list
const WEIGHTED_SCENARIOS = [];
for (const scenario of SCENARIOS) {{
  for (let i = 0; i < scenario.weight; i++) {{
    WEIGHTED_SCENARIOS.push(scenario);
  }}
}}"""

    def _generate_setup(self) -> str:
        """Generate setup function."""
        return """// Setup Function
export function setup() {
  console.log('Starting load test...');
  console.log('Target URL:', TARGET_URL);
  console.log('Number of scenarios:', SCENARIOS.length);

  // Verify target is reachable
  const testResponse = http.options(TARGET_URL, { headers: HEADERS });
  if (testResponse.status >= 500) {
    console.warn('Target may be unreachable:', testResponse.status);
  }

  return { startTime: Date.now() };
}"""

    def _generate_default_function(self) -> str:
        """Generate the main test function."""
        target_type = self.load_test.target_type

        if target_type == TargetType.ANTHROPIC:
            return self._generate_anthropic_function()
        elif target_type == TargetType.GOOGLE:
            return self._generate_google_function()
        else:
            return self._generate_openai_function()

    def _generate_openai_function(self) -> str:
        """Generate OpenAI-compatible test function."""
        return """// Main Test Function (OpenAI-compatible)
export default function(data) {
  const scenario = randomItem(WEIGHTED_SCENARIOS);
  const payload = buildPayload(scenario, REQUEST_CONFIG);

  const startTime = Date.now();

  const response = http.post(
    TARGET_URL,
    JSON.stringify(payload),
    {
      headers: HEADERS,
      tags: { scenario: scenario.name },
    }
  );

  const duration = Date.now() - startTime;

  // Record TTFT
  ttft.add(measureTTFT(response));

  // Check response
  const success = check(response, {
    'status is 200': (r) => r.status === 200,
    'response has choices': (r) => {
      try {
        const body = JSON.parse(r.body);
        return body.choices && body.choices.length > 0;
      } catch {
        return false;
      }
    },
  });

  if (!success) {
    requestErrors.add(1);
    console.warn('Request failed:', response.status, response.body);
  } else {
    requestErrors.add(0);

    // Track token usage
    try {
      const body = JSON.parse(response.body);
      if (body.usage) {
        totalTokens.add(body.usage.total_tokens || 0);

        // Calculate tokens per second
        const durationSec = duration / 1000;
        const tps = (body.usage.completion_tokens || 0) / durationSec;
        tokensPerSec.add(tps);
      }
    } catch (e) {
      // Ignore parse errors
    }
  }

  // Think time
  sleep(randomThinkTime());
}"""

    def _generate_anthropic_function(self) -> str:
        """Generate Anthropic-compatible test function."""
        return """// Main Test Function (Anthropic)
export default function(data) {
  const scenario = randomItem(WEIGHTED_SCENARIOS);
  const payload = buildPayload(scenario, REQUEST_CONFIG);

  // Convert to Anthropic format
  const anthropicPayload = {
    model: payload.model.startsWith('claude') ? payload.model : 'claude-3-sonnet-20240229',
    messages: payload.messages,
    max_tokens: payload.max_tokens || 1024,
  };

  const startTime = Date.now();

  const response = http.post(
    TARGET_URL,
    JSON.stringify(anthropicPayload),
    {
      headers: HEADERS,
      tags: { scenario: scenario.name },
    }
  );

  const duration = Date.now() - startTime;

  // Record TTFT
  ttft.add(measureTTFT(response));

  // Check response
  const success = check(response, {
    'status is 200': (r) => r.status === 200,
    'response has content': (r) => {
      try {
        const body = JSON.parse(r.body);
        return body.content && body.content.length > 0;
      } catch {
        return false;
      }
    },
  });

  if (!success) {
    requestErrors.add(1);
    console.warn('Request failed:', response.status, response.body);
  } else {
    requestErrors.add(0);

    // Track token usage
    try {
      const body = JSON.parse(response.body);
      if (body.usage) {
        const tokens = (body.usage.input_tokens || 0) + (body.usage.output_tokens || 0);
        totalTokens.add(tokens);

        const durationSec = duration / 1000;
        const tps = (body.usage.output_tokens || 0) / durationSec;
        tokensPerSec.add(tps);
      }
    } catch (e) {
      // Ignore parse errors
    }
  }

  sleep(randomThinkTime());
}"""

    def _generate_google_function(self) -> str:
        """Generate Google-compatible test function."""
        return """// Main Test Function (Google Generative AI)
export default function(data) {
  const scenario = randomItem(WEIGHTED_SCENARIOS);
  const payload = buildPayload(scenario, REQUEST_CONFIG);

  // Convert to Google format
  const googlePayload = {
    contents: payload.messages.map(m => ({
      role: m.role === 'user' ? 'user' : 'model',
      parts: [{ text: m.content }],
    })),
    generationConfig: {
      temperature: payload.temperature,
      maxOutputTokens: payload.max_tokens,
    },
  };

  const startTime = Date.now();

  const response = http.post(
    TARGET_URL,
    JSON.stringify(googlePayload),
    {
      headers: HEADERS,
      tags: { scenario: scenario.name },
    }
  );

  const duration = Date.now() - startTime;

  // Record TTFT
  ttft.add(measureTTFT(response));

  // Check response
  const success = check(response, {
    'status is 200': (r) => r.status === 200,
    'response has candidates': (r) => {
      try {
        const body = JSON.parse(r.body);
        return body.candidates && body.candidates.length > 0;
      } catch {
        return false;
      }
    },
  });

  if (!success) {
    requestErrors.add(1);
    console.warn('Request failed:', response.status, response.body);
  } else {
    requestErrors.add(0);

    // Track token usage
    try {
      const body = JSON.parse(response.body);
      if (body.usageMetadata) {
        totalTokens.add(body.usageMetadata.totalTokenCount || 0);

        const durationSec = duration / 1000;
        const tps = (body.usageMetadata.candidatesTokenCount || 0) / durationSec;
        tokensPerSec.add(tps);
      }
    } catch (e) {
      // Ignore parse errors
    }
  }

  sleep(randomThinkTime());
}"""

    def _generate_teardown(self) -> str:
        """Generate teardown function."""
        return """// Teardown Function
export function teardown(data) {
  const duration = (Date.now() - data.startTime) / 1000;
  console.log('Load test completed in', duration.toFixed(2), 'seconds');
}

// Handle summary
export function handleSummary(data) {
  // Return summary data in JSON format for parsing
  return {
    'stdout': JSON.stringify({
      metrics: {
        http_req_duration: data.metrics.http_req_duration,
        http_req_failed: data.metrics.http_req_failed,
        http_reqs: data.metrics.http_reqs,
        ttft: data.metrics.ttft,
        tokens_per_sec: data.metrics.tokens_per_sec,
        total_tokens: data.metrics.total_tokens,
        iterations: data.metrics.iterations,
        vus: data.metrics.vus,
        vus_max: data.metrics.vus_max,
        data_received: data.metrics.data_received,
        data_sent: data.metrics.data_sent,
      },
      root_group: data.root_group,
      state: data.state,
    }, null, 2),
  };
}"""
