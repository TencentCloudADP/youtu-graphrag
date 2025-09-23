
# **LLM Tool Use – A Comprehensive Technical Report**

*Prepared by: Senior Researcher – Aug 2025*

---

## Table of Contents
- [**LLM Tool Use – A Comprehensive Technical Report**](#llm-tool-use--a-comprehensive-technical-report)
    - [Table of Contents](#table-of-contents)
    - [1️⃣ Executive Summary](#1️⃣-executive-summary)
    - [2️⃣ Foundations of LLM‑Driven Tool Use](#2️⃣-foundations-of-llmdriven-tool-use)
        - [2.1 OpenAI Function‑Calling (now “Tools”)](#21-openai-functioncalling-now-tools)
        - [2.2 LangChain’s Tool Interface](#22-langchains-tool-interface)
        - [2.3 ChatGPT / GPT‑4 Plugins (Custom‑Tool Plugins)](#23-chatgpt--gpt4plugins-customtool-plugins)
    - [3️⃣ Interaction Design for Tool‑Enabled Agents](#3️⃣-interaction-design-for-toolenabled-agents)
        - [3.1 UI Taxonomy \& Divergent‑Convergent Workflows](#31-ui-taxonomy--divergentconvergent-workflows)
        - [3.2 Canvas‑Based Exploration Model (Extended OntoChat)](#32-canvasbased-exploration-model-extended-ontochat)
    - [4️⃣ Security \& Safety Considerations](#4️⃣-security--safety-considerations)
        - [4.1 Threat Landscape](#41-threat-landscape)
        - [4.2 Sandboxing \& Isolation Strategies](#42-sandboxing--isolation-strategies)
        - [4.3 Validation \& Policy Enforcement Frameworks](#43-validation--policy-enforcement-frameworks)
    - [5️⃣ Cost‑Aware \& Latency‑Optimised Engineering](#5️⃣-costaware--latencyoptimised-engineering)
        - [5.1 Model‑Level Tool‑Cost Penalties](#51-modellevel-toolcost-penalties)
        - [5.2 Runtime Optimisations (Engineering Tactics)](#52-runtime-optimisations-engineering-tactics)
    - [6️⃣ Evaluation Metrics \& Benchmarks](#6️⃣-evaluation-metrics--benchmarks)
        - [6.1 Core Metrics](#61-core-metrics)
        - [6.2 Benchmark Suites](#62-benchmark-suites)
    - [7️⃣ Best‑Practice Guideline for Production Deployments](#7️⃣-bestpractice-guideline-for-production-deployments)
        - [7.1 Prompt Engineering \& System‑Prompt Tool Disclosure](#71-prompt-engineering--systemprompt-tool-disclosure)
        - [7.2 Schema Design \& Strict Mode](#72-schema-design--strict-mode)
        - [7.3 Observability, Logging \& Version Control](#73-observability-logging--version-control)
        - [7.4 Runtime DSL \& Parser Integration](#74-runtime-dsl--parser-integration)
        - [7.5 Safety Gate‑keeping (Defense‑in‑Depth)](#75-safety-gatekeeping-defenseindepth)
    - [8️⃣ Case Studies \& Real‑World Deployments](#8️⃣-case-studies--realworld-deployments)
        - [8.1 Industrial PDF‑Extraction Agent (AID‑agent, 2025)](#81-industrial-pdfextraction-agent-aidagent-2025)
        - [8.2 Finance Bot (Real‑time Stock Insight)](#82-finance-bot-realtime-stock-insight)
        - [8.3 Travel Assistant](#83-travel-assistant)
        - [8.4 Legal Clause Analyzer](#84-legal-clause-analyzer)
        - [8.5 Market‑Research Synthesizer](#85-marketresearch-synthesizer)
        - [8.6 ReAct / ZERO\_SHOT\_REACT as a Generic Pattern](#86-react--zero_shot_react-as-a-generic-pattern)
    - [9️⃣ Future Directions \& Open Research Questions](#9️⃣-future-directions--open-research-questions)
    - [🔟 References \& Further Reading](#-references--further-reading)
---

## 1️⃣ Executive Summary

Large Language Models (LLMs) have moved beyond pure text generation to become **orchestrators of external tools** – search engines, code interpreters, database connectors, custom APIs, and even physical device controllers.  This shift unlocks *real‑world utility* (e.g., up‑to‑date weather, transactional finance) while also introducing new engineering challenges: **schema definition, reliable invocation, latency, cost, security, and evaluation**.

This report synthesises the most recent public guidance (OpenAI function‑calling, Azure OpenAI, LangChain, ChatGPT plugin pipeline), interaction‑design research, security taxonomies, cost‑aware training strategies, benchmark suites, and production case studies.  It culminates in a concrete **best‑practice playbook** that developers can adopt for robust, maintainable, and scalable LLM‑augmented services.

---

## 2️⃣ Foundations of LLM‑Driven Tool Use

### 2.1 OpenAI Function‑Calling (now “Tools”)

| Element | Description | Key Tips |
|---------|-------------|----------|
| **Tool definition** | JSON‑Schema‑like object under the `tools` array: `type`, `name`, `description`, `parameters` (object with `properties`, `required`, optional `additionalProperties:false`). | Use `strict:true` to enforce exact schema compliance; keep schemas shallow to minimise token usage. |
| **Call flow** | 1️⃣ Send request with tools. 2️⃣ Model may respond with `tool_call` (name + arguments). 3️⃣ Application executes the function, captures output, and returns `tool_call_output`. 4️⃣ Model receives the observation and can continue reasoning. 5️⃣ Final response is emitted. | Follow the 5‑step loop; treat the `tool_call_output` as a new observation in the conversation. |
| **Configuration** | `tool_choice` (`auto`, `required`, specific name, or `none`). `parallel_tool_calls` (default **true**) – enables multiple tool calls in a single turn. | Set `tool_choice=required` for deterministic workflows; disable parallel calls when ordering matters. |
| **Streaming** | `stream:true` sends incremental JSON fragments and a distinct `function_call_output` event. | Useful for UI‑side low‑latency UX; buffer until a complete JSON is received. |
| **Best‑practice highlights** | – Clear, concise tool names & descriptions. – ≤ 20 tools per request (token budget). – Mark enumerations (`enum`) and required fields. – Keep parameter types unambiguous (avoid `any`). – Place static context outside the schema. | See Section 7 for a checklist. |

**Security note:** Even with strict mode, the model can be coaxed into “prompt‑injection” attacks that try to trick it into constructing malicious arguments. Validation should occur **after** the model emits the call, before executing any side‑effect. 

---

### 2.2 LangChain’s Tool Interface

LangChain abstracts the raw API contract into a **Tool** class:
```python
class Tool:
    name: str
    description: str
    func: Callable[[str], str]
```
* **Binding** – `.bind_tools([...])` attaches a list of tools to a language model or an agent. The model decides **when** to call them, similarly to OpenAI’s `tool_choice=auto`.
* **Toolkits** – Groups of related tools (e.g., *SearchToolkit*, *SQLDatabaseToolkit*) simplify onboarding; they expose a unified schema to the LLM.
* **Ecosystem categories** (per the LangChain docs):
  - **Search** – Bing, Google, DuckDuckGo, Serper, Tavily.
  - **Code Interpreter** – Azure Container Apps, Bearly, Riza.
  - **Productivity** – GitHub, Gmail, Jira, Slack, Twilio.
  - **Web Browsing** – Playwright, Hyperbrowser, pure `requests`.
  - **Database** – SQLDatabase, Cassandra, Spark SQL.
  - **Finance** – GOAT, Stripe wrappers.
* **Custom tools** – Implement the `Tool` interface, provide a JSON schema or use LangChain’s `StructuredTool` for automatic validation.

LangChain thus **decouples the LLM‑model from the transport layer**, letting developers focus on *function semantics* while the library handles prompting, retry logic, and parallelisation.

---

### 2.3 ChatGPT / GPT‑4 Plugins (Custom‑Tool Plugins)

A **four‑step pipeline** moves an arbitrary HTTP API into a first‑class LLM tool:
1. **Expose** the desired functionality as a public HTTPS endpoint (REST/GraphQL).  
2. **Write an OpenAPI (Swagger) spec** that fully describes routes, parameters, auth, response schemas.  
3. **Create `ai-plugin.json`** manifest: name, description, `openapi_url`, authentication method, icons, usage instructions.  
4. **Register** the plugin on the OpenAI developer portal (requires ChatGPT‑Plus or wait‑list). After verification, the model can invoke the API automatically.

*Implementation tip*: a minimal Flask app with a single route, environment‑protected API keys, and deployment on a public HTTPS host (Vercel, Railway, Repl.it) is sufficient for prototyping.

**No‑code alternatives** (Plus AI, BotPenguin, custom GPT builders) auto‑generate the OpenAPI spec and manifest, but the core requirements (reachable API, compliant spec, manifest) remain unchanged.

---

## 3️⃣ Interaction Design for Tool‑Enabled Agents

### 3.1 UI Taxonomy & Divergent‑Convergent Workflows

Recent HCI research proposes a **taxonomy of UI patterns** that support the *divergent → convergent* workflow typical of LLM tool use:

| Pattern | Description | Example Implementations |
|---------|-------------|--------------------------|
| **Spatial navigation (pan/zoom canvas)** | Users explore a 2‑D plane where each node = an LLM‑generated action or tool call. | Luminate, Spellburst canvas graphs |
| **Zoom‑and‑filter lists** | List/grid view with dynamic filters; supports quick pruning of irrelevant suggestions. | Genquery, adaptive suggestion panels |
| **Node‑based linking / brushing** | Drag‑and‑drop connections between actions, visualising dependencies (e.g., “fetch weather → summarize”). | Node‑graph editors in language‑agent IDEs |
| **Details‑on‑demand tooltips** | Hover cards reveal full JSON arguments, execution logs, and allow inline edits. | Tooltip‑driven editing in Promptify |
| **Parameter sliders** | Real‑time manipulation of numeric or categorical parameters (temperature, top‑p, tool‑specific thresholds). | Slider controls in LangChain Playground |

These patterns embody Shneiderman’s mantra **overview → zoom & filter → details‑on‑demand**, encouraging users to generate many alternatives (divergent) and then focus on a refined subset (convergent).

### 3.2 Canvas‑Based Exploration Model (Extended OntoChat)

A concrete interaction model builds on the **OntoChat** system:
1. **Seed**: User provides a domain description (e.g., “supplier metadata extraction”).
2. **Generation**: LLM produces a set of candidate actions, plotted on a 2‑D canvas.
3. **Explore**: Users pan/zoom for an overview; clicking a region triggers **augmentation** – the LLM creates more actions focused on that semantic zone.
4. **Filter**: Semantic or keyword search highlights relevant items.
5. **Inspect**: Selecting an item opens a tooltip with full JSON arguments and a preview of tool output.
6. **Edit & Iterate**: Edits are sent back to the LLM, which refines the plan, possibly adding new tool calls.

The canvas‑plus‑inline‑controls workflow **keeps the user in a single surface**, enabling rapid iteration without context switching, and works equally for exploratory research and production decision‑making.

---

## 4️⃣ Security & Safety Considerations

### 4.1 Threat Landscape

| Threat | Impact | Typical Trigger |
|--------|--------|-----------------|
| **Prompt‑injection** | Malicious tool call, data exfiltration, arbitrary code execution. | Attacker crafts user text that influences the model to generate a harmful `arguments` payload. |
| **Unrestricted file‑system / network access** | Reads/writes sensitive data, SSRF, DoS, exfiltration. | Tool implementation inadvertently exposes OS‑level APIs. |
| **Cross‑tenant leakage** | One user’s data appears in another’s session. | Shared inference service without per‑session isolation. |
| **Mobile/embedded agent hijack** | Device compromise, privacy breach. | Agents that automate GUI actions or run background services. |

### 4.2 Sandboxing & Isolation Strategies

1. **Container‑level isolation** – Run each tool invocation in lightweight containers (Docker, gVisor, Firecracker). Enforce:
   - Read‑only file‑system mounts.
   - Network egress filtering (allow only whitelisted destinations).
   - Cgroup limits on CPU & memory.
2. **Language‑level sandbox** – Use restricted REPLs (e.g., Pyodide, Subprocess sandbox) for code execution; whitelist safe modules only.
3. **API Gateway Enforcement** – Every external call passes through a gateway that validates:
   - Authentication & scoped permissions.
   - Rate limiting.
   - Auditable logs for anomaly detection.
4. **Per‑session memory isolation** – Clear caches after each user session; encrypt any transient storage with short‑lived keys.

### 4.3 Validation & Policy Enforcement Frameworks

| Layer | Mechanism | Example |
|-------|-----------|---------|
| **Pre‑execution** | Schema validation (`strict:true`, JSON‑Schema) + safe‑argument filters (regex, whitelist). | Reject arguments containing `rm -rf`, URLs not in allowed list. |
| **Runtime DSL** | Custom policy language (`\tool` system) parsed via ANTLR4; triggers, predicates, actions (allow, ask‑user, abort). | “If tool=`web_search` and query contains `password`, abort.” |
| **Post‑execution** | Observation sanitisation – strip PII, limit length, redact secrets before feeding back to LLM. |
| **Continuous testing** | **SandboxEval** (malicious‑code suite) & **AgentScan** (mobile vector) – run nightly CI pipelines to detect regressions. |

The combination of **hard sandboxing**, **strict schema enforcement**, and **automated security testing** forms a defense‑in‑depth posture for production LLM‑tool pipelines.

---

## 5️⃣ Cost‑Aware & Latency‑Optimised Engineering

### 5.1 Model‑Level Tool‑Cost Penalties

Recent research (e.g., *Alignment for Efficient Tool Calling*) introduces an explicit **tool‑cost penalty α** into the training loss:
```
Loss_total = Loss_task + α * Cost(tool_calls)
```
Typical values:
- **α≈0.2** for cheap calculators (local execution).
- **α≈0.4** for web search.
- **α≈0.6** for heavyweight external reasoning (e.g., invoking a separate LLM).

**Outcome:** The model learns to **avoid unnecessary tool calls**, reducing latency and compute by up to **≈50 %** while preserving answer accuracy.

### 5.2 Runtime Optimisations (Engineering Tactics)

| Lever | Description | Expected Gains |
|------|-------------|----------------|
| **Parallel / speculative execution** | Launch moderation, retrieval, or computation in parallel with token generation; discard if later reasoning decides they’re unnecessary. | 20‑30 % lower wall‑clock time. |
| **Request consolidation** | Combine tool‑selection, argument preparation, and invocation into a **single prompt** to avoid multiple round‑trips. | Fewer network RTTs → 15‑25 % latency cut. |
| **Model tiering** | Route lightweight tool tasks (e.g., arithmetic) to smaller models (GPT‑3.5, Claude Sonnet) while delegating complex reasoning to larger models. | Cost per token drops dramatically (up to 60 %). |
| **Semantic caching & batching** | Cache exact or high‑similarity tool responses (similarity > 0.95). Batch low‑priority calls to a shared endpoint. | Repeated queries become essentially free; batch latency amortised. |

**Implementation tip:** Provide a **cost‑budget** field in the system prompt (`{budget: 0.05 USD}`) and let the model self‑regulate; combine with the α‑penalty for a double‑layer guard.

---

## 6️⃣ Evaluation Metrics & Benchmarks

### 6.1 Core Metrics
1. **Tool Correctness** – Exact‑match between the tool(s) the model *should* have called and the ones it actually called. ✅ Binary or fractional.
2. **Tool Selection Accuracy** – Node‑F1 (precision/recall on chosen tool nodes) and Edge‑F1 (ordering/dependency links).
3. **Invocation Accuracy** – Did the model correctly decide *whether* a tool was needed?
4. **Parameter‑Name F1** – Precision/recall on argument field names.
5. **Argument Value Distance** – Levenshtein distance or absolute error for numeric values.
6. **Tool Success Rate** – Fraction of tool calls that executed without runtime error (important for real‑world reliability).

### 6.2 Benchmark Suites
| Benchmark | Size | Domains | Notable Features |
|-----------|------|---------|------------------|
| **UltraTool (ACL 2024)** | 5.8 k samples, 22 domains, 2 032 distinct tools | Comprehensive plan‑step evaluation (accuracy, completeness, executability, syntactic soundness, structural rationality, efficiency). | Multi‑dimensional scoring via LLM‑as‑Judge; reports nested calls (~40 % of cases). |
| **TaskBench** | ~2 k queries | Focus on selection & ordering of tool calls. | Provides Node‑F1/Edge‑F1, Invocation Accuracy. |
| **T‑eval** | 1.5 k samples | Emphasises parameter filling quality. | Parameter‑Name F1 + Levenshtein on values. |

Open‑source models typically lag behind proprietary LLMs (GPT‑4 ≈ 76 % UltraTool score) – highlighting an *open research gap* in tool awareness and schema adherence.

---

## 7️⃣ Best‑Practice Guideline for Production Deployments

Below is a **step‑by‑step playbook** that integrates the insights above.

### 7.1 Prompt Engineering & System‑Prompt Tool Disclosure
```text
System Prompt:
You are an assistant equipped with the following tools. Use a tool **only** when the user request cannot be answered from the conversation history.

TOOLS:
- `search_web(query: string, top_k: integer = 3) -> list[dict]` – fetches up‑to‑date web results.
- `calc(expression: string) -> number` – safe arithmetic evaluator.
- `pdf_extract(file_id: string, fields: list[string]) -> dict` – extracts structured data from a PDF stored in the vector store.

When you decide to call a tool, output **exactly** the JSON snippet shown in the example below.

Example:
{ "tool": "search_web", "arguments": { "query": "latest S&P 500 price" } }
```
*Rationale:* Embedding a short, human‑readable description of each tool inside the system prompt informs the model’s *semantic* understanding, reducing missed calls.

### 7.2 Schema Design & Strict Mode
* Use **JSON‑Schema Draft‑07** compatible definitions.
* Mark `additionalProperties: false` to prevent stray fields.
* Prefer **enums** for categorical inputs and **numeric ranges** for limits.
* Enable `strict:true` on the API request to force exact schema compliance.

### 7.3 Observability, Logging & Version Control
| Artifact | What to Log | Retention |
|----------|-------------|-----------|
| **Request payload** | user prompt, system prompt, temperature, model version, tool list. | 30 days (GDPR‑compliant anonymised). |
| **Model output** | raw JSON (including `tool_calls`), token usage, latency. | 90 days.
| **Tool execution** | input arguments, stdout/stderr, exit status, execution time, resource usage. | 90 days.
| **Outcome** | final assistant reply, success/failure flag, user feedback (rating). | 180 days.

Store logs in an immutable append‑only store (e.g., CloudWatch Logs, ELK) and tag each version with a git SHA of the prompt‑tool bundle.

### 7.4 Runtime DSL & Parser Integration
* **Parser layer** – Immediately after model output, run a **schema‑driven parser** (e.g., `llm-exe` parser). It extracts the JSON, validates against the schema, and either returns a typed object or raises an exception.
* **DSL enforcement** – Define a lightweight rule language (`\tool`) that can express policies such as:
  ```
  when tool=search_web and arguments.query contains "password" => abort
  when tool=calc and arguments.expression length > 200 => reject
  ```
  The rule engine evaluates before the actual function is called.

### 7.5 Safety Gate‑keeping (Defense‑in‑Depth)
1. **Sanitise arguments** (regex whitelist, length caps).
2. **Run tools in isolated containers** with network egress filters.
3. **Ask for user confirmation** on side‑effectful actions (e.g., sending email, making a payment).
4. **Audit & alert** on anomalous patterns (e.g., sudden burst of `search_web` calls).

---

## 8️⃣ Case Studies & Real‑World Deployments

### 8.1 Industrial PDF‑Extraction Agent (AID‑agent, 2025)
* **Goal:** Pull supplier‑metadata and chemical‑composition fields from 44 heterogeneous technical‑report PDFs.
* **Tool Stack:**
  - Azure Document Intelligence OCR.
  - Table‑reconstruction tool (custom Python library).
  - Vision module for extracting image‑embedded tables.
  - Rule‑based validator (schema‑enforced JSON).  
* **Workflow:**
  1. LLM receives a high‑level request (e.g., *"Extract all copper percentages"*).
  2. It **plans** a sequence: `ocr → locate tables → extract rows → validate → aggregate`.
  3. Each step invokes the appropriate tool; the LLM observes the output and decides the next action (ReAct pattern).
* **Results:** End‑to‑end **F1 = 0.926** (vs. 0.842 baseline OCR‑only). Ablation shows the vision module adds +0.04, validator +0.06.
* **Lessons:** Robust preprocessing (deskew, rotate) is essential; strict schema dramatically lowered downstream parsing errors.

### 8.2 Finance Bot (Real‑time Stock Insight)
* **Tools:** `yfinance` API wrapper, `calc` for portfolio metrics, `search_web` for news headlines.
* **Pattern:** Parallel tool calls – fetch prices for 5 tickers and news in a single model turn; the model merges observations and produces a concise recommendation.
* **Latency:** 1.8 s average (parallel + caching).

### 8.3 Travel Assistant
* **Tools:** `openweather`, `flight_search`, `hotel_lookup`.
* **Interaction:** Canvas UI with a *trip‑timeline* node graph; each node represents a tool call (flight → weather → packing list).
* **User Study:** 72 % of participants preferred the node‑graph over a linear chat flow for itinerary building.

### 8.4 Legal Clause Analyzer
* **Tools:** `pdf_extract`, `search_web` (for precedent), `gpt‑4o` for reasoning.
* **Security:** Enforced per‑session isolation on document storage; all extracted text sanitized to avoid leaking client PII.
* **Accuracy:** Clause‑extraction precision 0.94, recall 0.91.

### 8.5 Market‑Research Synthesizer
* **Tools:** Multi‑source web scrapers (Playwright), `calc` for trend‑line fitting, `search_web` for competitor data.
* **Orchestration:** ReAct loop with **speculative execution** – the scraper starts while the LLM is still reasoning about the report outline, yielding total turnaround < 4 s for a 3‑page brief.

### 8.6 ReAct / ZERO_SHOT_REACT as a Generic Pattern
* **Core Idea:** LLM produces a **chain‑of‑thought** statement, decides whether to call a tool, receives an observation, and repeats.
* **Implementation in LangChain:** `ZeroShotAgent` with a `toolkit` – one line of code `agent = ZeroShotAgent.from_llm_and_tools(llm, tools)`.
* **Benefits:** Uniform API across domains, explainable reasoning trace, easy logging of intermediate steps.

---

## 9️⃣ Future Directions & Open Research Questions
1. **Adaptive Tool‑Cost Scheduling** – Dynamically adjusting α based on real‑time budget (e.g., user‑specified latency SLA).  
2. **Hierarchical Tool Discovery** – Allow the model to *create* new tool wrappers on‑the‑fly (e.g., generate OpenAPI spec from a description).  
3. **Cross‑Modal Tool Integration** – Combining vision, audio, and tactile sensors with language reasoning in a unified tool‑calling framework.  
4. **Standardised Benchmark Expansion** – Adding more domains (robotics, IoT) and measuring *security‑aware* metrics (percentage of disallowed calls prevented).  
5. **Self‑Auditing LLMs** – Models that predict the *cost* and *risk* of a proposed tool call before emitting it, enabling a two‑stage verification loop.  
6. **Explainability for Tool Decisions** – Rendering the tool‑selection rationale as a user‑facing narrative (e.g., “I used `search_web` because the question asked for the latest policy, which I cannot retrieve from memory”).

---

## 🔟 References & Further Reading
1. **OpenAI Function Calling – Core Guide** (2023‑2024).  
2. **Azure OpenAI – Function‑Calling Integration** (2024).  
3. **LangChain Documentation – Tools & Toolkits** (v0.2+).  
4. **ChatGPT Plugins – Development Guide** (OpenAI, 2024).  
5. **Interaction Design for LLM‑Based Tools** – Survey (2024).  
6. **LLM‑Driven Tool Use – Security Threats** – Whitepaper (2024).  
7. **SandboxEval & AgentScan** – Security testing frameworks (2024).  
8. **Alignment for Efficient Tool Calling** – ACL 2024 paper.  
9. **UltraTool Benchmark Suite** – ACL 2024 Findings.  
10. **ReAct: Synergizing Reasoning and Acting** – arXiv 2023.  
11. **ZERO_SHOT_REACT – LangChain Implementation** (2024).  
12. **AID‑agent PDF Extraction Case Study** – Proceedings of the 2025 Industrial AI Conference.  
13. **Runtime‑Constraint DSL – \tool System** – Workshop paper (2024).  
14. **llm‑exe Parser Module** – GitHub repository (2024).  
15. **Best‑Practice Prompt & Tool Design** – OpenAI Cookbook (2024).  

---

**End of Report**

*Prepared for internal distribution. Any reuse requires proper citation of the sources listed above.*