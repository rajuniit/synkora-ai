'use client'

import { useState, useCallback } from 'react'
import { Modal } from '@/components/ui/Modal'
import { Copy, Check, Globe, ExternalLink } from 'lucide-react'
import { cn } from '@/lib/utils/cn'

interface ConnectAgentModalProps {
  isOpen: boolean
  onClose: () => void
  shareToken: string
  topic: string
}

type Language = 'python' | 'nodejs' | 'shell' | 'curl' | 'web'
type Provider = 'anthropic' | 'openai' | 'ollama'

const LANG_TABS: { id: Language; label: string }[] = [
  { id: 'python', label: 'Python' },
  { id: 'nodejs', label: 'Node.js' },
  { id: 'shell', label: 'Shell' },
  { id: 'curl', label: 'cURL / REST' },
  { id: 'web', label: 'Web UI' },
]

const PROVIDERS: { id: Provider; label: string; pyPkg: string; npmPkg: string; envVar: string; envHint: string }[] = [
  { id: 'anthropic', label: 'Anthropic (Claude)', pyPkg: 'anthropic', npmPkg: '@anthropic-ai/sdk', envVar: 'ANTHROPIC_API_KEY', envHint: 'sk-ant-...' },
  { id: 'openai', label: 'OpenAI (GPT)', pyPkg: 'openai', npmPkg: 'openai', envVar: 'OPENAI_API_KEY', envHint: 'sk-...' },
  { id: 'ollama', label: 'Ollama (Local)', pyPkg: '', npmPkg: '', envVar: '', envHint: '' },
]

function CopyBtn({ text }: { text: string }) {
  const [copied, setCopied] = useState(false)
  const handleCopy = useCallback(() => {
    navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }, [text])
  return (
    <button
      onClick={handleCopy}
      className="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium rounded-md border border-gray-300 text-gray-600 hover:bg-gray-50 hover:border-gray-400 transition-colors"
    >
      {copied ? <Check className="w-3 h-3 text-green-500" /> : <Copy className="w-3 h-3" />}
      {copied ? 'Copied' : 'Copy'}
    </button>
  )
}

function CodeBlock({ code, label }: { code: string; label?: string }) {
  return (
    <div>
      {label && (
        <div className="flex items-center justify-between mb-1.5">
          <span className="text-xs font-medium text-gray-700">{label}</span>
          <CopyBtn text={code} />
        </div>
      )}
      {!label && (
        <div className="flex justify-end mb-1.5">
          <CopyBtn text={code} />
        </div>
      )}
      <pre className="bg-gray-900 text-gray-100 text-[11px] p-3 rounded-lg overflow-x-auto font-mono leading-relaxed whitespace-pre-wrap">
        {code}
      </pre>
    </div>
  )
}

export function ConnectAgentModal({ isOpen, onClose, shareToken, topic }: ConnectAgentModalProps) {
  const [lang, setLang] = useState<Language>('python')
  const [provider, setProvider] = useState<Provider>('anthropic')
  const [agentName, setAgentName] = useState('External Agent')

  const apiBase = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5001'
  const joinUrl = `${apiBase}/api/v1/war-room/${shareToken}/join`
  const roundsUrl = `${apiBase}/api/v1/war-room/${shareToken}/rounds`
  const respondUrl = `${apiBase}/api/v1/war-room/${shareToken}/respond`
  const scriptUrl = `${apiBase}/api/v1/war-room/${shareToken}/agent-script?provider=${provider}&agent_name=${encodeURIComponent(agentName)}`
  const webJoinUrl = `${typeof window !== 'undefined' ? window.location.origin : ''}/war-room/${shareToken}/join`

  const sel = PROVIDERS.find((p) => p.id === provider)!

  const showProviders = lang === 'python' || lang === 'nodejs'

  // --- Python ---
  const pythonOneLiner = `curl -s "${scriptUrl}" | python3 -`
  const pythonSave = `curl -s "${scriptUrl}" -o debate_agent.py\n${sel.envVar ? `export ${sel.envVar}=${sel.envHint}` : '# No API key needed'}\npython3 debate_agent.py`
  const pythonInstall = sel.pyPkg ? `pip install ${sel.pyPkg}` : '# Ollama runs locally — no pip install needed'

  // --- Node.js ---
  const nodeScript = `#!/usr/bin/env node
/**
 * Synkora War Room — Node.js Agent
 * Topic: ${topic}
 *
 * Usage:
 *   ${sel.npmPkg ? `npm install ${sel.npmPkg}` : '# No install needed for Ollama'}
 *   ${sel.envVar ? `export ${sel.envVar}=${sel.envHint}` : ''}
 *   node debate_agent.mjs
 */

const API_BASE = "${apiBase}";
const SHARE_TOKEN = "${shareToken}";
const AGENT_NAME = "${agentName}";
const MODEL = "${provider === 'anthropic' ? 'claude-sonnet-4-20250514' : provider === 'openai' ? 'gpt-4o' : 'llama3.1'}";

async function joinDebate() {
  const res = await fetch(\`\${API_BASE}/api/v1/war-room/\${SHARE_TOKEN}/join\`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ agent_name: AGENT_NAME }),
  });
  if (!res.ok) throw new Error(\`Join failed: \${await res.text()}\`);
  const data = await res.json();
  console.log(\`Joined as "\${AGENT_NAME}" | Topic: \${data.debate_topic}\`);
  console.log(\`Participants: \${data.participants.map(p => p.agent_name).join(", ")}\`);
  return { participantId: data.participant_id, totalRounds: data.total_rounds };
}

async function getRoundContext(round) {
  const res = await fetch(\`\${API_BASE}/api/v1/war-room/\${SHARE_TOKEN}/rounds/\${round}\`);
  return res.json();
}

async function postResponse(participantId, round, content) {
  const res = await fetch(\`\${API_BASE}/api/v1/war-room/\${SHARE_TOKEN}/respond\`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ participant_id: participantId, round, content }),
  });
  if (!res.ok && res.status !== 409) throw new Error(\`Respond failed: \${await res.text()}\`);
}

async function generateArgument(topic, round, totalRounds, prior, current) {
  const context = [
    ...prior.map(m => \`[\${m.agent_name}] (R\${m.round}): \${m.content.slice(0, 500)}\`),
    ...current.map(m => \`[\${m.agent_name}]: \${m.content.slice(0, 500)}\`),
  ].join("\\n") || "This is the opening round.";

  const prompt = \`You are "\${AGENT_NAME}" in a structured debate.
Topic: \${topic}
Round \${round}/\${totalRounds}.

\${context}

Provide a compelling argument. 2-4 paragraphs. Use markdown.\`;
${provider === 'anthropic' ? `
  const { default: Anthropic } = await import("@anthropic-ai/sdk");
  const client = new Anthropic();
  const msg = await client.messages.create({
    model: MODEL, max_tokens: 1500,
    messages: [{ role: "user", content: prompt }],
  });
  return msg.content[0].text;` : provider === 'openai' ? `
  const { default: OpenAI } = await import("openai");
  const client = new OpenAI();
  const res = await client.chat.completions.create({
    model: MODEL, max_tokens: 1500,
    messages: [{ role: "user", content: prompt }],
  });
  return res.choices[0].message.content;` : `
  const res = await fetch("http://localhost:11434/api/generate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ model: MODEL, prompt, stream: false }),
  });
  const data = await res.json();
  return data.response;`}
}

async function main() {
  console.log("=".repeat(50));
  console.log(\`Synkora War Room Agent | \${AGENT_NAME} | \${MODEL}\`);
  console.log("=".repeat(50));

  const { participantId, totalRounds } = await joinDebate();
  const responded = new Set();

  while (true) {
    await new Promise(r => setTimeout(r, 3000));
    for (let r = 1; r <= totalRounds; r++) {
      if (responded.has(r)) continue;
      try {
        const ctx = await getRoundContext(r);
        if (["completed", "error"].includes(ctx.status)) { console.log("Debate ended."); return; }
        if (ctx.current_round < r) continue;
        if (ctx.current_round_messages.some(m => m.agent_name === AGENT_NAME)) {
          responded.add(r); continue;
        }
        console.log(\`\\nRound \${r}/\${totalRounds} — generating...\`);
        const arg = await generateArgument(ctx.debate_topic, r, totalRounds, ctx.prior_messages, ctx.current_round_messages);
        console.log(\`Posting (\${arg.length} chars)...\`);
        await postResponse(participantId, r, arg);
        responded.add(r);
        console.log("Done!");
      } catch (e) {
        if (String(e).includes("409")) { responded.add(r); continue; }
      }
    }
    if (responded.size >= totalRounds) {
      const ctx = await getRoundContext(totalRounds);
      if (["completed", "synthesizing"].includes(ctx.status)) { console.log("\\nDebate complete!"); return; }
    }
  }
}

main().catch(console.error);`

  const nodeOneLiner = `# Save and run\ncurl -s "${apiBase}/api/v1/war-room/${shareToken}/agent-script?provider=${provider}&agent_name=${encodeURIComponent(agentName)}&language=nodejs" -o debate_agent.mjs\n${sel.envVar ? `export ${sel.envVar}=${sel.envHint}` : '# No API key needed'}\nnode debate_agent.mjs`

  // --- Shell ---
  const shellScript = `#!/bin/bash
# Synkora War Room — Shell Agent
# Topic: ${topic}
# This script joins a debate and submits static responses.
# Edit the RESPONSE variable for each round.

API="${apiBase}"
TOKEN="${shareToken}"
NAME="${agentName}"

echo "Joining debate..."
JOIN=$(curl -s -X POST "$API/api/v1/war-room/$TOKEN/join" \\
  -H "Content-Type: application/json" \\
  -d "{\\"agent_name\\": \\"$NAME\\"}")

PID=$(echo "$JOIN" | grep -o '"participant_id":"[^"]*"' | cut -d'"' -f4)
ROUNDS=$(echo "$JOIN" | grep -o '"total_rounds":[0-9]*' | cut -d: -f2)

echo "Joined! participant_id=$PID rounds=$ROUNDS"

for ROUND in $(seq 1 $ROUNDS); do
  echo ""
  echo "--- Round $ROUND ---"
  echo "Waiting for round to start..."

  while true; do
    CTX=$(curl -s "$API/api/v1/war-room/$TOKEN/rounds/$ROUND")
    CURRENT=$(echo "$CTX" | grep -o '"current_round":[0-9]*' | cut -d: -f2)
    STATUS=$(echo "$CTX" | grep -o '"status":"[^"]*"' | head -1 | cut -d'"' -f4)

    if [ "$STATUS" = "completed" ] || [ "$STATUS" = "error" ]; then
      echo "Debate ended ($STATUS)"; exit 0
    fi
    if [ "$CURRENT" -ge "$ROUND" ] 2>/dev/null; then break; fi
    sleep 4
  done

  # Generate your response here — replace with your own logic
  RESPONSE="This is ${agentName}'s argument for round $ROUND of the debate on: ${topic}. [Edit this script to add real arguments or pipe in from an LLM]"

  echo "Submitting response..."
  curl -s -X POST "$API/api/v1/war-room/$TOKEN/respond" \\
    -H "Content-Type: application/json" \\
    -d "{\\"participant_id\\": \\"$PID\\", \\"round\\": $ROUND, \\"content\\": \\"$RESPONSE\\"}"
  echo ""
  echo "Round $ROUND done!"
done

echo ""
echo "All rounds complete!"`;

  // --- cURL ---
  const curlScript = `# 1. Join the debate
curl -s -X POST ${joinUrl} \\
  -H "Content-Type: application/json" \\
  -d '{"agent_name": "${agentName}"}'

# Response: {"participant_id": "abc-123", "debate_topic": "...", ...}
# Save the participant_id!

# 2. Poll for round context (wait until current_round >= your round)
curl -s ${roundsUrl}/1

# 3. Submit your argument
curl -s -X POST ${respondUrl} \\
  -H "Content-Type: application/json" \\
  -d '{"participant_id": "YOUR_PARTICIPANT_ID", "round": 1, "content": "Your argument here..."}'

# Repeat steps 2-3 for each round.`

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Connect External Agent" className="max-w-2xl">
      <div className="space-y-4">
        {/* Language tabs */}
        <div className="flex gap-1 p-1 bg-gray-100 rounded-lg">
          {LANG_TABS.map(({ id, label }) => (
            <button
              key={id}
              onClick={() => setLang(id)}
              className={cn(
                'flex-1 px-2 py-1.5 text-[11px] font-medium rounded-md transition-colors',
                lang === id ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'
              )}
            >
              {label}
            </button>
          ))}
        </div>

        {/* Agent Name */}
        {lang !== 'web' && (
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">Agent Display Name</label>
            <input
              type="text"
              value={agentName}
              onChange={(e) => setAgentName(e.target.value)}
              className="w-full px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500/20 focus:border-red-400 outline-none"
              placeholder="My Claude Agent"
            />
          </div>
        )}

        {/* Provider selector (Python & Node.js only) */}
        {showProviders && (
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">LLM Provider</label>
            <div className="flex gap-2">
              {PROVIDERS.map((p) => (
                <button
                  key={p.id}
                  onClick={() => setProvider(p.id)}
                  className={cn(
                    'flex-1 px-2 py-1.5 text-[11px] font-medium rounded-lg border transition-colors',
                    provider === p.id
                      ? 'border-red-300 bg-red-50 text-red-700'
                      : 'border-gray-200 text-gray-600 hover:border-gray-300 hover:bg-gray-50'
                  )}
                >
                  {p.label}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Python */}
        {lang === 'python' && (
          <div className="space-y-3">
            <CodeBlock label="Quick Run (one-liner)" code={pythonOneLiner} />
            <CodeBlock label="Save & Run" code={pythonSave} />
            <div className="flex items-start gap-2 p-2.5 bg-amber-50 border border-amber-200 rounded-lg">
              <span className="text-amber-600 text-[11px] mt-px">Requires:</span>
              <code className="text-[11px] text-amber-800 font-mono">{pythonInstall}</code>
            </div>
          </div>
        )}

        {/* Node.js */}
        {lang === 'nodejs' && (
          <div className="space-y-3">
            <CodeBlock label="Save & Run" code={nodeOneLiner} />
            <details className="group">
              <summary className="text-xs font-medium text-gray-600 cursor-pointer hover:text-gray-900 flex items-center gap-1">
                <span className="group-open:rotate-90 transition-transform inline-block">&#9654;</span>
                Preview full script
              </summary>
              <div className="mt-2">
                <CodeBlock code={nodeScript} />
              </div>
            </details>
            {sel.npmPkg && (
              <div className="flex items-start gap-2 p-2.5 bg-amber-50 border border-amber-200 rounded-lg">
                <span className="text-amber-600 text-[11px] mt-px">Requires:</span>
                <code className="text-[11px] text-amber-800 font-mono">npm install {sel.npmPkg}</code>
              </div>
            )}
          </div>
        )}

        {/* Shell */}
        {lang === 'shell' && (
          <div className="space-y-3">
            <CodeBlock label="Bash Script" code={shellScript} />
            <p className="text-[11px] text-gray-500">
              Edit the RESPONSE variable in the script — or pipe in output from any LLM CLI tool (e.g. <code className="bg-gray-100 px-1 rounded">llm</code>, <code className="bg-gray-100 px-1 rounded">ollama run</code>).
            </p>
          </div>
        )}

        {/* cURL */}
        {lang === 'curl' && (
          <div className="space-y-3">
            <CodeBlock label="REST API Commands" code={curlScript} />
            <p className="text-[11px] text-gray-500">
              Use these endpoints from any language or tool. The protocol is simple: join, poll for rounds, submit responses.
            </p>
          </div>
        )}

        {/* Web UI */}
        {lang === 'web' && (
          <div className="space-y-3">
            <p className="text-sm text-gray-600">
              Open the web join page to participate directly from a browser. Anyone with the link can join — no account needed.
            </p>
            <div className="flex items-center gap-2 p-3 bg-gray-50 border border-gray-200 rounded-lg">
              <code className="text-xs text-gray-700 font-mono truncate flex-1">{webJoinUrl}</code>
              <CopyBtn text={webJoinUrl} />
            </div>
            <a
              href={webJoinUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-red-500 to-red-600 text-white text-sm font-medium rounded-lg hover:from-red-600 hover:to-red-700 transition-all"
            >
              <ExternalLink className="w-4 h-4" />
              Open Join Page
            </a>
          </div>
        )}

        {/* Topic reference */}
        <div className="pt-3 border-t border-gray-100">
          <p className="text-[11px] text-gray-400">
            Debate: <span className="text-gray-600">{topic}</span>
          </p>
        </div>
      </div>
    </Modal>
  )
}
