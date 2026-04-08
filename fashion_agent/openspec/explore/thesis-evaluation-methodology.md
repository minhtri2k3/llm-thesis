# Thesis Evaluation Methodology
## Multi-Model Agentic Fashion System: How to Measure, Compare, and Conclude

---

## 1. The Three Systems to Compare

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Mode A — Baseline (Gemini only)                                            │
│                                                                             │
│  User Query ──► Intent Router ──► Tools (deterministic) ──► Gemini Synth  │
│                                                                             │
│  Token Cost = intent_call + synthesis_call                                  │
│  Orchestration: FIXED code logic (not AI)                                   │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│  Mode B — GPT Session (Gemini orchestrates, GPT-4o synthesizes)            │
│                                                                             │
│  User Query ──► Gemini (function calling loop) ──► Tools ──► GPT-4o Synth │
│                                                                             │
│  Token Cost = intent_call + orchestrator_calls(1-4) + synthesis_call       │
│  Orchestration: AGENTIC — Gemini decides what to search                     │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│  Mode C — Claude Session (GPT-4o orchestrates, Claude synthesizes)         │
│                                                                             │
│  User Query ──► GPT-4o (function calling loop) ──► Tools ──► Claude Synth │
│                                                                             │
│  Token Cost = intent_call + orchestrator_calls(1-4) + synthesis_call       │
│  Orchestration: AGENTIC — GPT-4o decides what to search                     │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Token Cost Accounting Per Mode

### 2.1 What's Already in the Database

The `llm_token_usage` table captures:

| Column | Mode A | Mode B | Mode C |
|---|---|---|---|
| `input_tokens` | intent + synthesis | synthesis only | synthesis only |
| `output_tokens` | intent + synthesis | synthesis | synthesis |
| `orchestrator_input_tokens` | 0 | Gemini (all iterations) | GPT-4o calls |
| `orchestrator_output_tokens` | 0 | Gemini calls | GPT-4o calls |
| `orchestration_mode` | `"direct"` | `"agentic"` | `"agentic"` |
| `tool_calls_json` | `[]` | `[{tool, args, result_count, duration_ms}]` | same |

### 2.2 Total Cost Per Turn Formula

```
Total Tokens (Mode A) = intent_input + intent_output
                       + synthesis_input + synthesis_output

Total Tokens (Mode B/C) = intent_input + intent_output
                         + Σ(orch_input_i + orch_output_i)   ← agentic loop
                         + synthesis_input + synthesis_output
```

### 2.3 Estimated USD Cost Per Turn

Published pricing (early 2025):

| Model | Input ($/1M) | Output ($/1M) |
|---|---|---|
| Gemini 2.0 Flash | $0.075 | $0.30 |
| GPT-4o | $2.50 | $10.00 |
| Claude 3.5 Sonnet | $3.00 | $15.00 |

Mode A = cheapest (Gemini only).
Mode B = Gemini orch (cheap) + GPT-4o synthesis (expensive).
Mode C = GPT-4o orch (expensive) + Claude synthesis (very expensive).

> Thesis insight: Mode A is the cheapest baseline. The question is whether Mode B/C's extra cost buys measurably better recommendations.

### 2.4 SQL Query for Token Cost Report

```sql
SELECT
  orchestration_mode,
  synthesizer_model,
  orchestrator_model,
  COUNT(DISTINCT session_id)                               AS sessions,
  ROUND(AVG(input_tokens + output_tokens
    + orchestrator_input_tokens + orchestrator_output_tokens))
                                                           AS avg_total_tokens_per_turn,
  ROUND(AVG(jsonb_array_length(tool_calls_json)), 2)       AS avg_tool_calls,
  ROUND(AVG(
    CASE WHEN orchestrator_model LIKE 'gemini%'
      THEN (orchestrator_input_tokens * 0.075 + orchestrator_output_tokens * 0.30) / 1e6
      ELSE (orchestrator_input_tokens * 2.50 + orchestrator_output_tokens * 10.00) / 1e6
    END
    +
    CASE
      WHEN synthesizer_model LIKE 'gemini%' THEN (input_tokens * 0.075 + output_tokens * 0.30) / 1e6
      WHEN synthesizer_model LIKE 'gpt%'    THEN (input_tokens * 2.50  + output_tokens * 10.00) / 1e6
      WHEN synthesizer_model LIKE 'claude%' THEN (input_tokens * 3.00  + output_tokens * 15.00) / 1e6
      ELSE 0
    END
  ), 6)                                                    AS avg_usd_per_turn
FROM llm_token_usage
WHERE call_name = 'synthesis'
GROUP BY orchestration_mode, synthesizer_model, orchestrator_model
ORDER BY avg_usd_per_turn;
```

---

## 3. Accuracy Estimation from User Behaviour

### 3.1 Signals Already Captured

```
User selects item  ──► liked_items[] appended  (in user_sessions)
User buys item     ──► ended_by = 'order'
User rates session ──► ended_by = 'rating'
User leaves        ──► ended_by = 'timeout'
Query history      ──► intents, filters, refinements per turn
```

### 3.2 Four Implicit Accuracy Signals

No human judges needed — these are derived from existing data.

#### A. Selection Rate (SR) — Primary accuracy signal
```
SR(mode) = sessions_with_≥1_selection / total_sessions_in_mode
```
A selection = the recommendation was relevant enough to act on.

#### B. Session Completion Rate (SCR) — Satisfaction signal
```
SCR(mode) = sessions_ended_by_order_or_rating / total_sessions
```
Higher = users satisfied enough to complete the flow.

#### C. Query Refinement Rate (QRR) — Proxy for failure
```
QRR(mode) = avg queries per session
```
Lower = agent got it right the first time. Higher = user had to keep asking.

#### D. Gender Alignment Score (GAS) — A/B sub-metric
```
GAS = selected_items_matching_user_gender / total_selections
```
Compare GAS(gender_hint=TRUE) vs GAS(gender_hint=FALSE) per mode.

### 3.3 Composite Behaviour Accuracy Score

```
BehaviourAccuracy(mode) =
  0.40 × norm(SR)
  + 0.30 × norm(SCR)
  + 0.20 × (1 - norm(QRR))      # inverted: lower QRR = better
  + 0.10 × norm(GAS)
```

Normalize each metric to [0,1] across all 3 modes before combining.

### 3.4 Accuracy SQL Query

```sql
SELECT
  s.preferred_model,
  ltu.orchestration_mode,
  COUNT(DISTINCT s.session_id)                                           AS n_sessions,
  ROUND(100.0 *
    COUNT(DISTINCT CASE WHEN jsonb_array_length(s.liked_items) > 0
                        THEN s.session_id END) / COUNT(DISTINCT s.session_id), 1)
                                                                         AS selection_rate_pct,
  ROUND(100.0 *
    COUNT(DISTINCT CASE WHEN s.ended_by IN ('order','rating')
                        THEN s.session_id END) / COUNT(DISTINCT s.session_id), 1)
                                                                         AS completion_rate_pct,
  ROUND(AVG(jsonb_array_length(s.query_history)), 2)                     AS avg_queries_per_session
FROM user_sessions s
JOIN llm_token_usage ltu USING (session_id)
WHERE ltu.call_name = 'synthesis'
GROUP BY s.preferred_model, ltu.orchestration_mode
ORDER BY selection_rate_pct DESC;
```

---

## 4. The Central Trade-off: Quality vs Cost

### 4.1 Cost-Efficiency Score (CES) — Your Key Thesis Metric

```
CES(mode) = BehaviourAccuracy(mode) / AvgCostPerTurn_USD(mode)
```

Higher CES = better quality per dollar spent.

```
┌──────────────────────────────────────────────────┐
│  Cost vs Quality Trade-off Space                 │
│                                                  │
│  High  ▲                                         │
│  Qual  │         ★ Mode B?                       │
│        │   ★ Mode A                              │
│        │                     ★ Mode C            │
│  Low   └─────────────────────────────►           │
│       Low Cost              High Cost            │
│                                                  │
│  Ideal: top-left (high quality, low cost)        │
└──────────────────────────────────────────────────┘
```

### 4.2 Agentic Overhead Analysis

For Modes B and C, also track:

```
Agentic Overhead Ratio = orch_total_tokens / turn_total_tokens
  → What fraction of tokens went to the orchestration decision?

Tool Call Efficiency = total_items_found / total_tool_calls
  → Products discovered per tool invocation

Tool Diversity = unique_tool_names / total_calls
  → Did the orchestrator vary its strategy?
```

Core question: *Does the agentic loop find different products than the deterministic router would, or does it mostly replicate the same search?*

---

## 5. Statistical Framework

### 5.1 Test Selection

| Test | When to Use | Applied to |
|---|---|---|
| Chi-square | Comparing proportions | SR, SCR between modes |
| Mann-Whitney U | Non-parametric group compare | Token costs (skewed) |
| Kruskal-Wallis | 3-group non-parametric | QRR across all modes |
| Bootstrap CI | Small sample sizes | CES score intervals |

**Target**: ≥30 sessions per mode (50+ preferred) for valid statistics.

### 5.2 Null Hypotheses to Test

```
H0₁: SR is equal across modes A, B, C
H0₂: SCR is equal across modes
H0₃: Gender hint has no effect on GAS
H0₄: Agentic modes (B,C) produce the same accuracy as baseline (A)
```

Reject if p < 0.05. Report effect size (Cliff's delta) alongside p-values.

### 5.3 Effect Size (for small samples)

```python
def cliff_delta(a, b):
    """Non-parametric effect size. Range: -1 to 1. |d| > 0.33 = medium effect."""
    n = len(a) * len(b)
    return sum(1 if x > y else (-1 if x < y else 0) for x in a for y in b) / n
```

---

## 6. Conclusion Structure for the Thesis Chapter

```
6.1 Token Cost Analysis
    Table: avg_tokens/turn, avg_USD/turn by mode
    Finding: "Mode A is Xx cheaper than Mode C per turn"

6.2 User Behaviour Accuracy
    Table: SR, SCR, QRR, GAS per mode
    Finding: "Mode B achieved highest SR with only Yx cost overhead vs Mode A"

6.3 Cost-Efficiency Score
    Bar chart: CES per mode
    Finding: "Mode A dominates CES for budget deployments;
              Mode B achieves best quality-per-dollar when accuracy matters"

6.4 Agentic Overhead Analysis
    Line chart: avg tool calls vs SR per mode
    Finding: "Agentic routing added X% tool diversity; QRR dropped Y%"

6.5 Gender A/B Test
    Table: GAS(hint=T) vs GAS(hint=F) per mode, with p-value
    Finding: "Gender-aware prompting improved alignment by X% (p<0.05)"

6.6 Mode Comparison Summary Table
    ┌─────────────┬────────┬────────┬────────┐
    │ Metric      │ Mode A │ Mode B │ Mode C │
    ├─────────────┼────────┼────────┼────────┤
    │ SR (%)      │        │        │        │
    │ SCR (%)     │        │        │        │
    │ QRR         │        │        │        │
    │ avg $/turn  │        │        │        │
    │ CES         │        │        │        │
    └─────────────┴────────┴────────┴────────┘
```

---

## 7. Open Questions Worth Discussing

1. **Latency**: Agentic modes will be slower. Should Time-To-First-Token or total response time be a metric? Users may abandon slow responses.

2. **Simulated sessions**: If you can't gather 150 real sessions, can you write a test harness to send scripted queries and track selections? This is a valid research approach (offline evaluation).

3. **Tool call duplication**: A key empirical finding could be "Mode B called `search_fashion` 2.3× per turn but only returned 15% more unique products than Mode A's single deterministic call." That's a concrete claim about agentic overhead.

4. **Qualitative scoring**: Optionally, ask a human evaluator to rate 10 responses per mode on a 1–5 Likert scale for relevance. Small sample but adds credibility to the behavioural signals.

5. **Calibration of weights in BehaviourAccuracy**: The 0.40/0.30/0.20/0.10 weights are reasonable defaults. You can justify them or do a sensitivity analysis showing the ranking of modes is stable across different weight assignments.
