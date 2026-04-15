"""Register diagram generation tools."""

from __future__ import annotations


def register_diagram_tools(registry) -> None:
    """Register diagram generation tools with the ADK tool registry."""
    from src.services.agents.internal_tools.diagram_tools import (
        internal_generate_diagram,
        internal_generate_quick_diagram,
    )

    registry.register_tool(
        name="internal_generate_diagram",
        description=(
            "Generate a publication-quality technical diagram from a structured JSON spec.\n\n"

            "━━ DIAGRAM TYPES — pick template_type based on what you're drawing ━━\n"
            "• architecture — layered system diagrams, microservices, RAG pipelines, agent architecture, "
            "memory architecture, data-flow, network topology. Use containers for tiers (INPUT→CORE→STORAGE→OUTPUT).\n"
            "• sequence — time-ordered message exchanges: auth flows, API protocols, multi-service calls. "
            'Uses participants:[{id,label,color}] + messages:[{from,to,label,type:"sync|reply|async",note?}]\n'
            "• comparison — feature matrix table comparing options side-by-side. "
            'Uses columns:[str or {label,color}] + rows:[{label,values:[...]}]\n'
            "• timeline — Gantt/roadmap with task bars on a time axis. "
            'Uses periods:["Q1","Q2",...] + tracks:[{label,start,end,color?}] + milestones?:[{label,at,color?}]\n'
            "• mind-map — radial concept map from a central topic. "
            'Uses center:"Topic" + branches:[{label,color?,children:[str,...]}]\n'
            "• er-diagram — Entity-Relationship database schema. "
            'Uses entities:[{id,label,color?,attributes:[{name,type,pk?,fk?}]}] + relationships:[{from,to,label?,from_card,to_card}]\n'
            "• class-diagram — UML class hierarchy with attributes and methods. "
            'Uses classes:[{id,name,abstract?,interface?,attributes:[str],methods:[str],x?,y?}] + relationships:[{from,to,type,label?}]\n'
            '  Relationship types: extends, implements, association, aggregation, composition, dependency\n'
            "• use-case — UML actors + system boundary + use case ellipses. "
            'Uses system:"Name" + actors:[{id,label,side:"left|right"}] + use_cases:[{id,label}] '
            '+ relationships:[{actor,use_case} or {from,to,type:"include|extend"}]\n'
            "• state-machine — states and transitions (uses architecture renderer). "
            "Use rounded_rect for states, circle for initial/final, diamond for decisions, arrows for transitions.\n"
            "• flowchart — process/decision flows (uses architecture renderer). "
            "Use diamond for decisions, parallelogram for I/O steps, circle for start/end, rounded_rect for processes.\n\n"

            "━━ NODE KINDS — choose the right shape for the component ━━\n"
            "• rounded_rect — default for services, APIs, apps, gateways, SDKs, processors\n"
            "• double_rect — LLMs, model runtimes, AI inference engines (double border = AI inference)\n"
            "• rect — plain boxes for config/data blocks\n"
            "• circle — user/person nodes, event triggers, start/end circles\n"
            "• cylinder — databases, vector stores, key-value stores, blob storage, queues\n"
            "• diamond — decision points, routers, conditional branches (flowcharts)\n"
            "• hexagon — orchestrators, memory managers, task planners (central coordinator)\n"
            "• parallelogram — data I/O steps, artifacts, input/output in flowcharts\n"
            "• document — file outputs, logs, reports, schemas\n"
            "• gear — background workers, schedulers, transformers\n"
            "• terminal — CLI tools, scripts, shell processes\n"
            "• folder — namespaces, file system groups\n"
            "• speech — chat messages, user utterances, prompts\n\n"

            "━━ ICONS — STRICT RULES ━━\n"
            "ONLY set an icon if the node literally IS that product/service. Never assign icons "
            "to generic architectural concepts.\n"
            "• Set icon='' (empty) for: User, Gateway, Service, Manager, Layer, Store, Builder, "
            "Formatter, Resolver, Router, Planner, Runtime, Response, Results — any generic name.\n"
            "• Set icon only when label matches exactly: 'PostgreSQL'→postgresql, 'Redis'→redis, "
            "'Kafka'→kafka, 'FastAPI'→fastapi, 'Next.js'→nextjs, 'Docker'→docker, "
            "'Kubernetes'→kubernetes, 'OpenAI API'→openai, 'Anthropic'→anthropic, "
            "'AWS'→aws, 'GCP'→gcp, 'GitHub'→github, 'Grafana'→grafana, 'Stripe'→stripe.\n"
            "• NEVER assign nginx/nodejs/anthropic/openai icons to nodes like 'Application', "
            "'Client', 'Gateway', 'Agent', 'User', 'Manager', 'Store' — these get no icon.\n\n"

            "━━ TYPE LABELS — small text shown ABOVE the main label ━━\n"
            "Add type_label for every important node to give context: "
            "'CLIENT', 'SDK', 'MODEL', 'ROUTER', 'PROCESSOR', 'STORAGE', 'ACTION', 'OUTPUT', "
            "'INFERENCE', 'ORCHESTRATION', 'ENTRY', 'WORKING MEMORY', 'ASSEMBLER', etc.\n\n"

            "━━ CONTAINERS — always use for layered architecture diagrams ━━\n"
            "• Define 3-5 containers representing tiers/layers\n"
            "• Each container MUST have id, x, y, width, height — these are the exact pixel bounds\n"
            "• CRITICAL: every node that belongs to a container MUST have a 'container' field set "
            "to that container's id (e.g. 'container': 'input'). This is how the layout engine "
            "knows to place the node inside the container. Nodes without 'container' are placed globally.\n"
            "• Container sizing — height MUST be at least 200px per row of nodes (36 label + 80 node + 84 padding). "
            "For 1 row: height=200. For 2 rows: height=380. Width should be at least 300px per node "
            "(e.g. 4 nodes → width=1200). Containers that are too small will overlap their nodes.\n"
            "• Set fill for colored backgrounds: '#EFF6FF' (blue), '#F0FDF4' (green), "
            "'#FFF7ED' (orange), '#FAF5FF' (purple), '#F0F9FF' (cyan), '#FFFBEB' (amber)\n"
            "• Set label_color to match the fill tint: '#3B82F6', '#16A34A', '#EA580C', '#7C3AED'\n"
            "• Container label: short plain text ONLY. NEVER use numbered prefixes like "
            "'01 //', '02 //', '1.', etc. WRONG: '01 // INPUT LAYER'. RIGHT: 'INPUT LAYER'.\n"
            "• Good labels: 'INPUT LAYER', 'STORAGE', 'CORE', 'OUTPUT / RETRIEVAL', "
            "'MEMORY MANAGER (MEM0 CORE)'\n\n"

            "━━ ARROWS / FLOW TYPES ━━\n"
            "• control — API calls, HTTP requests, orchestration commands (solid)\n"
            "• data — data payloads, responses, streaming (solid)\n"
            "• write — persist/store operations to DB/storage (solid)\n"
            "• read — fetch/retrieve from DB/storage (solid)\n"
            "• async — queue events, pub/sub, async jobs, fire-and-forget (dashed)\n"
            "• feedback — responses back up the stack, iterative loops (solid)\n"
            "• embed — data transformation, embedding generation, vector encoding (purple)\n"
            "Always add label for non-obvious arrows: 'store()', 'retrieve()', 'facts', "
            "'resolved', 'write', 'read', 'embeddings', 'context'.\n\n"

            "━━ STYLES ━━\n"
            "1=Flat  2=Dark Terminal  3=Blueprint  4=Notion Clean (default)  "
            "5=Glassmorphism  6=Claude Official  7=OpenAI Official\n\n"

            "━━ SEQUENCE DIAGRAMS — use template_type: sequence ━━\n"
            "For flows, protocols, API call sequences, auth flows, message passing:\n"
            '{\n'
            '  "template_type": "sequence",\n'
            '  "style": 4,\n'
            '  "title": "OAuth2 Authorization Code Flow",\n'
            '  "participants": [\n'
            '    {"id": "user",     "label": "User",            "color": "#6366F1"},\n'
            '    {"id": "client",   "label": "Client App",      "color": "#3B82F6"},\n'
            '    {"id": "auth",     "label": "Auth Server",     "color": "#10B981"},\n'
            '    {"id": "resource", "label": "Resource Server", "color": "#F59E0B"}\n'
            '  ],\n'
            '  "messages": [\n'
            '    {"from": "user",   "to": "client",   "label": "1. Click Login",                    "type": "sync"},\n'
            '    {"from": "client", "to": "auth",     "label": "2. Authorization Request",          "type": "sync"},\n'
            '    {"from": "auth",   "to": "user",     "label": "3. Login & Consent Screen",         "type": "sync"},\n'
            '    {"from": "user",   "to": "auth",     "label": "4. Grant Consent",                  "type": "sync"},\n'
            '    {"from": "auth",   "to": "client",   "label": "5. Redirect + Auth Code",           "type": "reply"},\n'
            '    {"from": "client", "to": "auth",     "label": "6. Token Request",                  "type": "sync",  "note": "Back-channel"},\n'
            '    {"from": "auth",   "to": "client",   "label": "7. access_token + refresh_token",   "type": "reply"},\n'
            '    {"from": "client", "to": "resource", "label": "8. API Request (Bearer token)",     "type": "sync"},\n'
            '    {"from": "resource","to": "client",  "label": "9. Protected Resource",             "type": "reply"}\n'
            '  ]\n'
            '}\n'
            "Message types: sync (solid →), reply (dashed ←/→), async (dashed, fire-and-forget).\n"
            'Keep labels short — use \\n to split long labels across 2 lines.\n\n'

            "━━ COMPARISON MATRIX — use template_type: comparison ━━\n"
            '{"template_type":"comparison","style":4,"title":"RAG Approaches","subtitle":"Feature comparison",\n'
            ' "columns":[{"label":"Naive RAG","color":"#3B82F6"},{"label":"Advanced RAG","color":"#10B981"},{"label":"Modular RAG","color":"#8B5CF6"}],\n'
            ' "rows":[\n'
            '   {"label":"Accuracy","values":["Medium","High","Very High"]},\n'
            '   {"label":"Latency","values":["Low","Medium","High"]},\n'
            '   {"label":"Setup Effort","values":["Minimal","Moderate","Complex"]},\n'
            '   {"label":"Customizable","values":["✗","Partial","✓"]}\n'
            ' ]}\n\n'

            "━━ TIMELINE — use template_type: timeline ━━\n"
            '{"template_type":"timeline","style":4,"title":"Project Roadmap",\n'
            ' "periods":["Week 1","Week 2","Week 3","Week 4","Week 5","Week 6"],\n'
            ' "tracks":[\n'
            '   {"label":"Design","start":0,"end":2,"color":"#3B82F6"},\n'
            '   {"label":"Backend","start":1,"end":5,"color":"#10B981"},\n'
            '   {"label":"Frontend","start":2,"end":5,"color":"#8B5CF6"},\n'
            '   {"label":"Testing","start":4,"end":6,"color":"#F59E0B"}\n'
            ' ],\n'
            ' "milestones":[{"label":"Design Review","at":2},{"label":"Beta Launch","at":5,"color":"#EF4444"}]}\n\n'

            "━━ MIND MAP — use template_type: mind-map ━━\n"
            '{"template_type":"mind-map","style":4,"title":"AI Platform","center":"AI Platform",\n'
            ' "branches":[\n'
            '   {"label":"Infrastructure","color":"#3B82F6","children":["Kubernetes","Docker","AWS"]},\n'
            '   {"label":"Data Layer","color":"#10B981","children":["Vector DB","PostgreSQL","Redis"]},\n'
            '   {"label":"Models","color":"#8B5CF6","children":["LLM","Embeddings","Classifiers"]},\n'
            '   {"label":"API","color":"#F59E0B","children":["REST","WebSocket","GraphQL"]}\n'
            ' ]}\n\n'

            "━━ ER DIAGRAM — use template_type: er-diagram ━━\n"
            '{"template_type":"er-diagram","style":4,"title":"E-commerce Schema",\n'
            ' "entities":[\n'
            '   {"id":"user","label":"User","color":"#3B82F6","attributes":[{"name":"id","type":"UUID","pk":true},{"name":"email","type":"VARCHAR(255)"},{"name":"name","type":"VARCHAR(100)"}]},\n'
            '   {"id":"order","label":"Order","color":"#10B981","attributes":[{"name":"id","type":"UUID","pk":true},{"name":"user_id","type":"UUID","fk":true},{"name":"total","type":"DECIMAL"}]},\n'
            '   {"id":"product","label":"Product","color":"#8B5CF6","attributes":[{"name":"id","type":"UUID","pk":true},{"name":"name","type":"VARCHAR"},{"name":"price","type":"DECIMAL"}]}\n'
            ' ],\n'
            ' "relationships":[\n'
            '   {"from":"user","to":"order","label":"places","from_card":"1","to_card":"N"},\n'
            '   {"from":"order","to":"product","label":"contains","from_card":"N","to_card":"M"}\n'
            ' ]}\n\n'

            "━━ CLASS DIAGRAM — use template_type: class-diagram ━━\n"
            '{"template_type":"class-diagram","style":4,"title":"Animal Hierarchy",\n'
            ' "classes":[\n'
            '   {"id":"animal","name":"Animal","abstract":true,"attributes":["-name: String","-age: int"],"methods":["+speak(): String","+move(): void"]},\n'
            '   {"id":"dog","name":"Dog","attributes":["-breed: String"],"methods":["+fetch(): void","+speak(): String"]},\n'
            '   {"id":"cat","name":"Cat","attributes":["-indoor: bool"],"methods":["+purr(): void","+speak(): String"]}\n'
            ' ],\n'
            ' "relationships":[\n'
            '   {"from":"dog","to":"animal","type":"extends"},\n'
            '   {"from":"cat","to":"animal","type":"extends"}\n'
            ' ]}\n\n'

            "━━ USE CASE — use template_type: use-case ━━\n"
            '{"template_type":"use-case","style":4,"title":"E-Commerce Use Cases","system":"Online Store",\n'
            ' "actors":[{"id":"customer","label":"Customer","side":"left"},{"id":"admin","label":"Admin","side":"right"}],\n'
            ' "use_cases":[\n'
            '   {"id":"browse","label":"Browse Products"},{"id":"checkout","label":"Checkout"},\n'
            '   {"id":"pay","label":"Process Payment"},{"id":"manage","label":"Manage Inventory"}\n'
            ' ],\n'
            ' "relationships":[\n'
            '   {"actor":"customer","use_case":"browse"},{"actor":"customer","use_case":"checkout"},\n'
            '   {"from":"checkout","to":"pay","type":"include"},\n'
            '   {"actor":"admin","use_case":"manage"}\n'
            ' ]}\n\n'

            "━━ ARCHITECTURE SPEC FORMAT ━━\n"
            '{\n'
            '  "template_type": "architecture",\n'
            '  "style": 4,\n'
            '  "title": "Mem0 Memory Architecture",\n'
            '  "subtitle": "Personalized AI Memory Layer for LLM Applications",\n'
            '  "nodes": [\n'
            '    {"id": "user", "label": "User", "kind": "circle", "icon": "", "type_label": "CLIENT", "container": "input"},\n'
            '    {"id": "app", "label": "AI App / Agent", "kind": "rounded_rect", "icon": "", "type_label": "APPLICATION", "container": "input"},\n'
            '    {"id": "llm", "label": "LLM", "kind": "double_rect", "icon": "", "type_label": "MODEL", "container": "input"},\n'
            '    {"id": "mem0", "label": "mem0 Client", "kind": "double_rect", "icon": "", "type_label": "SDK", "container": "input"},\n'
            '    {"id": "mgr", "label": "Memory Manager", "kind": "hexagon", "icon": "", "type_label": "ORCHESTRATION", "container": "mem_mgr"},\n'
            '    {"id": "vec", "label": "Vector Store", "kind": "cylinder", "icon": "", "type_label": "EMBEDDINGS", "container": "storage"},\n'
            '    {"id": "graph", "label": "Graph DB", "kind": "cylinder", "icon": "", "type_label": "RELATIONS", "container": "storage"},\n'
            '    {"id": "kv", "label": "Key-Value Store", "kind": "cylinder", "icon": "", "type_label": "WORKING MEMORY", "container": "storage"},\n'
            '    {"id": "hist", "label": "History Store", "kind": "document", "icon": "", "type_label": "EPISODIC", "container": "storage"},\n'
            '    {"id": "ctx", "label": "Context Builder", "kind": "rounded_rect", "icon": "", "type_label": "ASSEMBLER", "container": "output"},\n'
            '    {"id": "rank", "label": "Ranked Results", "kind": "rounded_rect", "icon": "", "type_label": "RERANKER", "container": "output"},\n'
            '    {"id": "resp", "label": "Personalized Response", "kind": "rounded_rect", "icon": "", "type_label": "OUTPUT", "container": "output"}\n'
            '  ],\n'
            '  "arrows": [\n'
            '    {"source": "user", "target": "app", "flow": "control"},\n'
            '    {"source": "app", "target": "llm", "flow": "control"},\n'
            '    {"source": "llm", "target": "mem0", "label": "retrieve()", "flow": "control"},\n'
            '    {"source": "mem0", "target": "mgr", "label": "store()", "flow": "write"},\n'
            '    {"source": "mgr", "target": "vec", "label": "write", "flow": "write"},\n'
            '    {"source": "mgr", "target": "graph", "label": "write", "flow": "write"},\n'
            '    {"source": "mgr", "target": "kv", "label": "write", "flow": "write"},\n'
            '    {"source": "mgr", "target": "hist", "label": "write history", "flow": "write"},\n'
            '    {"source": "vec", "target": "ctx", "label": "embeddings", "flow": "read"},\n'
            '    {"source": "graph", "target": "ctx", "label": "entity links", "flow": "read"},\n'
            '    {"source": "kv", "target": "rank", "label": "key facts", "flow": "read"},\n'
            '    {"source": "ctx", "target": "rank", "flow": "data"},\n'
            '    {"source": "rank", "target": "resp", "flow": "data"}\n'
            '  ],\n'
            '  "containers": [\n'
            '    {"id": "input", "label": "INPUT LAYER", "x": 60, "y": 60, "width": 1200, "height": 200,\n'
            '     "fill": "#EFF6FF", "label_color": "#3B82F6"},\n'
            '    {"id": "mem_mgr", "label": "MEMORY MANAGER (MEM0 CORE)", "x": 60, "y": 300, "width": 1200, "height": 200,\n'
            '     "fill": "#FAF5FF", "label_color": "#7C3AED"},\n'
            '    {"id": "storage", "label": "STORAGE LAYER", "x": 60, "y": 540, "width": 1200, "height": 200,\n'
            '     "fill": "#F0FDF4", "label_color": "#16A34A"},\n'
            '    {"id": "output", "label": "OUTPUT / RETRIEVAL", "x": 60, "y": 780, "width": 1200, "height": 200,\n'
            '     "fill": "#FFF7ED", "label_color": "#EA580C"}\n'
            '  ]\n'
            '}\n\n'
            "Nodes omitting x/y/width/height are auto-laid-out within the diagram."
        ),
        parameters={
            "type": "object",
            "properties": {
                "diagram_spec": {
                    "type": "string",
                    "description": "Full JSON spec with template_type, nodes, arrows, containers",
                },
                "title": {"type": "string", "description": "Diagram title"},
                "style": {
                    "type": "integer",
                    "description": "Visual style 1-7",
                    "default": 4,
                },
                "output_format": {
                    "type": "string",
                    "enum": ["svg", "png", "both"],
                    "default": "svg",
                },
            },
            "required": ["diagram_spec"],
        },
        function=internal_generate_diagram,
        tool_category="diagram",
    )

    registry.register_tool(
        name="internal_generate_quick_diagram",
        description=(
            "Quick diagram: provide nodes + edges as JSON arrays, auto-layout handles positions. "
            "Use for simple flows. For architecture diagrams with containers/tiers, use internal_generate_diagram.\n\n"
            'Nodes: [{"id": "a", "label": "API Gateway", "kind": "rounded_rect", "icon": "", "type_label": "ROUTER"}]\n'
            'Edges: [{"from": "a", "to": "b", "label": "routes", "flow": "data"}]\n\n'
            "ICON RULE: Only set icon when the label is the exact product name "
            "(postgresql, redis, kafka, fastapi, docker, kubernetes, aws, github, grafana, stripe). "
            "Generic names like 'Gateway', 'Service', 'Store', 'Manager', 'User' get icon=''.\n\n"
            "KIND GUIDE: rounded_rect=services/APIs, double_rect=LLM/AI models, "
            "circle=users/events, cylinder=databases/storage, hexagon=orchestrators, "
            "diamond=decisions, document=files/logs, gear=workers."
        ),
        parameters={
            "type": "object",
            "properties": {
                "nodes": {
                    "type": "string",
                    "description": "JSON array of nodes: [{id, label, kind, icon?}]",
                },
                "edges": {
                    "type": "string",
                    "description": "JSON array of edges: [{from, to, label?, flow?}]",
                },
                "title": {"type": "string", "default": "Diagram"},
                "diagram_type": {"type": "string", "default": "architecture"},
                "style": {"type": "integer", "default": 4},
            },
            "required": ["nodes", "edges"],
        },
        function=internal_generate_quick_diagram,
        tool_category="diagram",
    )
