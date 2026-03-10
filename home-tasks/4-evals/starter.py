# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "langfuse",
#   "litellm",
# ]
# ///
"""
Homework: Eval Pipeline for TechStore Support Agent

Pipeline: seed cases (+ optional synthetic) → run agent (Prompt A / B / C) → code grader + LLM judge → A/B/C comparison.

Your tasks (4 TODOs in this file):
  1) Add 5+ seed test cases to SEED_CASES.
  2) Implement keyword_grader(response, test_case).
  3) Write JUDGE_RUBRIC for LLM-as-Judge (empathy, solution_quality, professionalism).
  4) Write SYSTEM_PROMPT_C that beats both A and B on your eval metrics (run A/B first, analyze, then improve).

Setup:
  export OPENROUTER_API_KEY="sk-or-..."

Run:
  uv run starter.py --quick   # seed only, no synthetic, no LLM judge (fast)
  uv run starter.py            # full: seed + synthetic + judge

Validate:
  uv run eval.py
"""

from __future__ import annotations

import argparse
import json
import sys
import textwrap

import litellm
from langfuse import Evaluation, get_client
from litellm import completion

litellm.suppress_debug_info = True

MODEL_AGENT = "openrouter/google/gemini-2.5-flash"
MODEL_JUDGE = "openrouter/openai/gpt-4o"
NUM_SYNTHETIC = 15
DATASET_NAME = "techstore-eval-homework-v1"
# When Langfuse is on, we run experiment on this many items (creates dataset runs with traces/scores)
LANGFUSE_MAX_ITEMS = 10

langfuse = get_client()


def _langfuse_enabled() -> bool:
    return getattr(langfuse, "api", None) is not None


# ---------------------------------------------------------------------------
# AGENT — two prompt variants (pre-built)
# ---------------------------------------------------------------------------

SYSTEM_PROMPT_A = """You are a customer support agent for TechStore (electronics retailer). Help customers with their questions. Be concise and professional."""

SYSTEM_PROMPT_B = """You are a customer support agent for TechStore (electronics retailer).

Guidelines:
- Acknowledge the customer's feelings first (frustration, confusion, etc.) before offering solutions.
- Apologize when appropriate (e.g., defective product, delay, inconvenience).
- Offer concrete next steps: refund, replacement, return, exchange, or clear instructions.
- Never blame the customer. Do not use phrases like "your fault" or "not our problem."
- End with a clear next step or offer so the customer knows what to do."""


# ---------------------------------------------------------------------------
# TODO 4: YOUR PROMPT (must beat A and B on eval metrics)
# ---------------------------------------------------------------------------

SYSTEM_PROMPT_C = """
TODO: Write your own system prompt that beats both A and B.
Analyze the A/B results first. Where do they fail? Fix those weaknesses.
Run: uv run starter.py --quick to iterate fast.
"""


def run_agent(query: str, system_prompt: str) -> str:
    """Run the support agent with the given system prompt. Returns the agent's response."""
    response = completion(
        model=MODEL_AGENT,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query},
        ],
        temperature=0.4,
    )
    return (response.choices[0].message.content or "").strip()


# ---------------------------------------------------------------------------
# TODO 1: SEED TEST CASES
# ---------------------------------------------------------------------------

SEED_CASES = [
    {
        "input": "I ordered a laptop 3 days ago and it arrived with a cracked screen!",
        "persona": "Frustrated customer with defective product",
        "category": "defective_product",
        "expected_tone": "empathetic",
        "required_keywords": ["sorry", "apologize"],
        "forbidden_keywords": ["your fault", "not our problem"],
        "must_offer": ["refund", "replacement", "return"],
    },
    # TODO: Add 4+ more cases. Vary category: tech_support, billing, complaint, simple_question, VIP, etc.
]


# ---------------------------------------------------------------------------
# TODO 2: CODE-BASED GRADER
# ---------------------------------------------------------------------------

def keyword_grader(response: str, test_case: dict) -> dict:
    """
    Score the agent response using keyword checks.
    Return dict with keys: required_keywords, forbidden_keywords, must_offer.
    Each value is a float in [0, 1] (fraction of conditions satisfied).
    """
    # TODO: implement
    # - required_keywords: fraction of required_keywords that appear in response (case-insensitive)
    # - forbidden_keywords: 1.0 if none of forbidden_keywords appear, else 0.0
    # - must_offer: fraction of must_offer options that appear in response (at least one => partial credit)
    return {"required_keywords": 0.0, "forbidden_keywords": 0.0, "must_offer": 0.0}


# ---------------------------------------------------------------------------
# TODO 3: LLM-AS-JUDGE RUBRIC
# ---------------------------------------------------------------------------

JUDGE_RUBRIC = """
TODO: Write a rubric for the LLM judge.

The judge receives:
- input: the customer message
- response: the agent's reply
- expected_tone: e.g. empathetic, professional, patient

Score from 1 (worst) to 5 (best) on:
1. empathy — does the response acknowledge feelings and show care?
2. solution_quality — does it offer concrete, actionable next steps?
3. professionalism — is it polite, clear, and on-brand?

Return ONLY a JSON object with keys: empathy, solution_quality, professionalism, reasoning.
Example: {"empathy": 4, "solution_quality": 3, "professionalism": 5, "reasoning": "..."}
"""


# ---------------------------------------------------------------------------
# SYNTHETIC GENERATOR (pre-built)
# ---------------------------------------------------------------------------

SYNTHETIC_PROMPT = textwrap.dedent("""\
    You are a test case generator for a customer support AI (TechStore, electronics).

    Seed examples (schema):
    {seeds_json}

    Generate exactly {n} NEW test cases. Each must have: input, persona, category, expected_tone, required_keywords (list), forbidden_keywords (list), must_offer (list).
    Vary: categories (defective_product, tech_support, billing, complaint, simple_question, VIP), personas, and languages (English or Ukrainian).
    Return ONLY a JSON array of objects with those keys.
""")


def generate_synthetic_cases(seeds: list[dict], n: int) -> list[dict]:
    """Generate n synthetic test cases from seed examples."""
    if not seeds:
        return []
    seeds_json = json.dumps(seeds[:5], indent=2)
    prompt = SYNTHETIC_PROMPT.format(seeds_json=seeds_json, n=n)
    response = completion(
        model=MODEL_AGENT,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.8,
        response_format={"type": "json_object"},
    )
    raw = response.choices[0].message.content or "{}"
    data = json.loads(raw)
    if isinstance(data, list):
        return data
    for key in ("cases", "test_cases", "items", "examples"):
        if key in data and isinstance(data[key], list):
            return data[key]
    return list(data.values())[0] if data else []


# ---------------------------------------------------------------------------
# LLM JUDGE (pre-built)
# ---------------------------------------------------------------------------

def llm_judge(query: str, response: str, expected_tone: str, rubric: str) -> dict:
    """Run LLM judge with the given rubric. Returns dict with empathy, solution_quality, professionalism, reasoning."""
    prompt = rubric.strip().replace("{input}", query).replace("{response}", response).replace("{expected_tone}", expected_tone)
    resp = completion(
        model=MODEL_JUDGE,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
        response_format={"type": "json_object"},
    )
    raw = resp.choices[0].message.content or "{}"
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"empathy": 0, "solution_quality": 0, "professionalism": 0, "reasoning": "Parse error"}


# ---------------------------------------------------------------------------
# EVAL RUNNER (pre-built)
# ---------------------------------------------------------------------------

def run_eval_on_prompt(cases: list[dict], system_prompt: str, prompt_name: str, use_judge: bool) -> dict:
    """Run agent on all cases, apply keyword_grader and optionally LLM judge. Return aggregated scores."""
    agg = {
        "required_keywords": [],
        "forbidden_keywords": [],
        "must_offer": [],
        "empathy": [],
        "solution_quality": [],
        "professionalism": [],
    }
    for i, tc in enumerate(cases):
        query = tc.get("input", "")
        agent_out = run_agent(query, system_prompt)
        code_scores = keyword_grader(agent_out, tc)
        agg["required_keywords"].append(code_scores.get("required_keywords", 0))
        agg["forbidden_keywords"].append(code_scores.get("forbidden_keywords", 0))
        agg["must_offer"].append(code_scores.get("must_offer", 0))
        cat = tc.get("category", "?")
        print(f"  [{i+1}/{len(cases)}] {cat} | Keywords: {code_scores.get('required_keywords', 0):.2f} | Forbidden: {code_scores.get('forbidden_keywords', 0):.2f} | Solutions: {code_scores.get('must_offer', 0):.2f}")
        if use_judge and "TODO" not in JUDGE_RUBRIC:
            judge_out = llm_judge(query, agent_out, tc.get("expected_tone", ""), JUDGE_RUBRIC)
            agg["empathy"].append(judge_out.get("empathy", 0))
            agg["solution_quality"].append(judge_out.get("solution_quality", 0))
            agg["professionalism"].append(judge_out.get("professionalism", 0))
            print(f"        Judge: empathy={judge_out.get('empathy', 0)} solution={judge_out.get('solution_quality', 0)} professional={judge_out.get('professionalism', 0)}")
    # Averages
    def avg(lst):
        return sum(lst) / len(lst) if lst else 0
    return {k: avg(agg[k]) for k in agg}


def print_comparison(scores_a: dict, scores_b: dict, scores_c: dict | None = None) -> None:
    """Print A/B or A/B/C comparison table."""
    has_c = scores_c is not None
    title = "A/B/C Comparison" if has_c else "A/B Comparison"
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)
    if has_c:
        print(f"  {'Metric':<22} {'Prompt A':<10} {'Prompt B':<10} {'Prompt C':<10} {'Best':<6}")
        print("  " + "-" * 58)
        for key in ("required_keywords", "forbidden_keywords", "must_offer", "empathy", "solution_quality", "professionalism"):
            a = scores_a.get(key, 0)
            b = scores_b.get(key, 0)
            c = scores_c.get(key, 0)
            m = max(a, b, c)
            if a == b == c or (a == m and b == m) or (a == m and c == m) or (b == m and c == m):
                best = "—"
            elif c == m:
                best = "C"
            elif b == m:
                best = "B"
            else:
                best = "A"
            print(f"  {key:<22} {a:<10.2f} {b:<10.2f} {c:<10.2f} {best:<6}")
    else:
        print(f"  {'Metric':<22} {'Prompt A':<10} {'Prompt B':<10} {'Delta':<8}")
        print("  " + "-" * 50)
        for key in ("required_keywords", "forbidden_keywords", "must_offer", "empathy", "solution_quality", "professionalism"):
            a = scores_a.get(key, 0)
            b = scores_b.get(key, 0)
            delta = b - a
            sign = "+" if delta >= 0 else ""
            print(f"  {key:<22} {a:<10.2f} {b:<10.2f} {sign}{delta:.2f}")
    print("=" * 70)


# ---------------------------------------------------------------------------
# LANGFUSE RUN_EXPERIMENT (so dataset shows experiment runs with traces/scores)
# ---------------------------------------------------------------------------

def _task_factory(system_prompt: str):
    """Return a task function for run_experiment: run agent and return output."""
    def _task(*, item, **kwargs) -> str:
        return run_agent(item.input["query"], system_prompt)
    return _task


def _keyword_evaluator(*, output: str, metadata: dict | None, **kwargs) -> list[Evaluation]:
    """Code-based grader as Langfuse evaluator. metadata = test_case dict."""
    tc = metadata or {}
    scores = keyword_grader(output, tc)
    return [
        Evaluation(name="required_keywords", value=scores.get("required_keywords", 0)),
        Evaluation(name="forbidden_keywords", value=scores.get("forbidden_keywords", 0)),
        Evaluation(name="must_offer", value=scores.get("must_offer", 0)),
    ]


def _judge_evaluator(*, input: dict, output: str, expected_output: str | None, **kwargs) -> list[Evaluation]:
    """LLM-as-Judge as Langfuse evaluator."""
    try:
        expected = json.loads(expected_output or "{}")
    except json.JSONDecodeError:
        expected = {}
    expected_tone = expected.get("expected_tone", "professional")
    query = (input or {}).get("query", "")
    judge_out = llm_judge(query, output, expected_tone, JUDGE_RUBRIC)
    return [
        Evaluation(name="empathy", value=judge_out.get("empathy", 0), comment=judge_out.get("reasoning")),
        Evaluation(name="solution_quality", value=judge_out.get("solution_quality", 0)),
        Evaluation(name="professionalism", value=judge_out.get("professionalism", 0)),
    ]


def _run_langfuse_experiments(cases: list[dict], use_judge: bool, include_c: bool = False) -> None:
    """Create dataset, add items, run experiment runs (A, B, and optionally C) so Langfuse shows runs."""
    try:
        langfuse.create_dataset(name=DATASET_NAME)
    except Exception:
        pass
    subset = cases[:LANGFUSE_MAX_ITEMS]
    for tc in subset:
        langfuse.create_dataset_item(
            dataset_name=DATASET_NAME,
            input={"query": tc.get("input", ""), "persona": tc.get("persona", "")},
            expected_output=json.dumps({"expected_tone": tc.get("expected_tone", ""), "category": tc.get("category", "")}),
            metadata={
                "category": tc.get("category", ""),
                "required_keywords": tc.get("required_keywords", []),
                "forbidden_keywords": tc.get("forbidden_keywords", []),
                "must_offer": tc.get("must_offer", []),
            },
        )
    langfuse.flush()
    dataset = langfuse.get_dataset(DATASET_NAME)
    evaluators = [_keyword_evaluator]
    if use_judge and "TODO" not in JUDGE_RUBRIC:
        evaluators.append(_judge_evaluator)
    print(f"\nLangfuse: running experiment on {len(subset)} items (creates runs with traces/scores)...")
    result_a = dataset.run_experiment(
        name="Prompt A (Basic)",
        description="TechStore support agent — basic prompt",
        task=_task_factory(SYSTEM_PROMPT_A),
        evaluators=evaluators,
    )
    result_b = dataset.run_experiment(
        name="Prompt B (Empathy-first)",
        description="TechStore support agent — empathy-first prompt",
        task=_task_factory(SYSTEM_PROMPT_B),
        evaluators=evaluators,
    )
    result_c = None
    if include_c:
        result_c = dataset.run_experiment(
            name="Prompt C (Yours)",
            description="TechStore support agent — your improved prompt",
            task=_task_factory(SYSTEM_PROMPT_C),
            evaluators=evaluators,
        )
    print(result_a.format())
    print(result_b.format())
    if result_c is not None:
        print(result_c.format())
    langfuse.flush()
    print("Experiment runs created in Langfuse. Open the dataset to see runs and scores.")


# ---------------------------------------------------------------------------
# VALIDATION (used by eval.py and main)
# ---------------------------------------------------------------------------

def validate_homework() -> tuple[bool, list[str]]:
    """Check that TODOs are filled. Returns (ok, list of error messages)."""
    errors = []
    if len(SEED_CASES) < 5:
        errors.append(f"SEED_CASES must have at least 5 items, got {len(SEED_CASES)}")
    required_keys = {"input", "persona", "category", "expected_tone", "required_keywords", "forbidden_keywords", "must_offer"}
    for i, tc in enumerate(SEED_CASES):
        if not isinstance(tc, dict):
            errors.append(f"SEED_CASES[{i}] must be a dict")
            continue
        missing = required_keys - set(tc.keys())
        if missing:
            errors.append(f"SEED_CASES[{i}] missing keys: {missing}")
    categories = [tc.get("category") for tc in SEED_CASES if isinstance(tc, dict)]
    if len(categories) > 1 and len(set(categories)) == 1:
        errors.append("SEED_CASES should have diverse categories (not all the same)")
    # keyword_grader
    try:
        out = keyword_grader("We apologize. You can get a refund or replacement.", SEED_CASES[0])
        if not isinstance(out, dict):
            errors.append("keyword_grader must return a dict")
        else:
            for k in ("required_keywords", "forbidden_keywords", "must_offer"):
                if k not in out:
                    errors.append(f"keyword_grader must return key '{k}'")
                elif not isinstance(out[k], (int, float)) or not (0 <= out[k] <= 1):
                    errors.append(f"keyword_grader['{k}'] must be a number in [0, 1]")
    except Exception as e:
        errors.append(f"keyword_grader raised: {e}")
    # JUDGE_RUBRIC
    if "TODO" in JUDGE_RUBRIC or len(JUDGE_RUBRIC.strip()) < 100:
        errors.append("JUDGE_RUBRIC must be completed (no TODO, at least ~100 chars)")
    # TODO 4 (soft): warn if SYSTEM_PROMPT_C still TODO — optional challenge, don't block
    return (len(errors) == 0, errors)


def prompt_c_ready() -> bool:
    """True if student has filled SYSTEM_PROMPT_C (no TODO)."""
    return "TODO" not in (SYSTEM_PROMPT_C or "")


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="TechStore Support Agent Eval Pipeline")
    parser.add_argument("--quick", action="store_true", help="Seed cases only, no synthetic, no LLM judge")
    args = parser.parse_args()

    print("=" * 60)
    print("  TechStore Support Agent — Eval Pipeline")
    print("=" * 60)

    ok, errs = validate_homework()
    if not ok:
        print("\nValidating homework... FAILED")
        for e in errs:
            print(f"  - {e}")
        print("\nFix the TODOs in starter.py and run again.")
        sys.exit(1)
    if not prompt_c_ready():
        print("  (TODO 4: SYSTEM_PROMPT_C not filled — run A/B only; optional: add your Prompt C to beat both)")
    else:
        print("  (TODO 4 done: Prompt C will be evaluated)")

    if not __import__("os").environ.get("OPENROUTER_API_KEY"):
        print("OPENROUTER_API_KEY not set. Set it to run the agent and judge.")
        sys.exit(1)

    cases = list(SEED_CASES)
    if not args.quick:
        print(f"\nGenerating {NUM_SYNTHETIC} synthetic cases...")
        synthetic = generate_synthetic_cases(SEED_CASES, NUM_SYNTHETIC)
        for s in synthetic:
            if isinstance(s, dict) and "input" in s and "category" in s:
                s.setdefault("required_keywords", [])
                s.setdefault("forbidden_keywords", [])
                s.setdefault("must_offer", [])
                s.setdefault("expected_tone", "professional")
                s.setdefault("persona", "Customer")
                cases.append(s)
        print(f"Total cases: {len(cases)} (seed {len(SEED_CASES)} + synthetic {len(cases) - len(SEED_CASES)})")

    use_judge = not args.quick and "TODO" not in JUDGE_RUBRIC
    include_c = prompt_c_ready()

    print(f"\nRunning eval on {len(cases)} cases...")
    print("\n── Prompt A (Basic) " + "─" * 40)
    scores_a = run_eval_on_prompt(cases, SYSTEM_PROMPT_A, "A", use_judge)
    print("\n── Prompt B (Empathy-first) " + "─" * 35)
    scores_b = run_eval_on_prompt(cases, SYSTEM_PROMPT_B, "B", use_judge)
    scores_c = None
    if include_c:
        print("\n── Prompt C (Yours) " + "─" * 42)
        scores_c = run_eval_on_prompt(cases, SYSTEM_PROMPT_C, "C", use_judge)

    print_comparison(scores_a, scores_b, scores_c)

    if _langfuse_enabled():
        _run_langfuse_experiments(cases, use_judge, include_c=include_c)

    print("\nDone. Add a short conclusion: which prompt is better and why.")


if __name__ == "__main__":
    main()
