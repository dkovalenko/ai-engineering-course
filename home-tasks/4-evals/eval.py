# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "langfuse",
#   "litellm",
# ]
# ///
"""
Quick structural validation of the homework (no API calls).

Checks: SEED_CASES count and schema, keyword_grader return shape, JUDGE_RUBRIC completed.
Also reports whether TODO 4 (SYSTEM_PROMPT_C) is done — optional but recommended.

Run:
  uv run eval.py
"""

import sys

# Import starter to get SEED_CASES, keyword_grader, JUDGE_RUBRIC, validate_homework
try:
    import starter  # type: ignore
except ImportError as e:
    print("Could not import starter.py:", e)
    print("Run this script from the homework directory: uv run eval.py")
    sys.exit(1)


def main() -> None:
    print("=" * 55)
    print("  Homework structure check (no API calls)")
    print("=" * 55)

    ok, errors = starter.validate_homework()

    if ok:
        print("\n  All checks passed.")
        print(f"  - SEED_CASES: {len(starter.SEED_CASES)} items")
        print("  - keyword_grader: returns valid dict with required_keywords, forbidden_keywords, must_offer")
        print("  - JUDGE_RUBRIC: completed (no TODO)")
        if starter.prompt_c_ready():
            print("  - TODO 4 (Prompt C): completed — will run A/B/C comparison")
        else:
            print("  - TODO 4 (Prompt C): not done yet — optional but recommended (write a prompt that beats A and B)")
        print("\n  You can run: uv run starter.py --quick")
        print("=" * 55)
        sys.exit(0)

    print("\n  Some checks failed:")
    for e in errors:
        print(f"    - {e}")
    print("\n  Fix the TODOs in starter.py and run uv run eval.py again.")
    print("=" * 55)
    sys.exit(1)


if __name__ == "__main__":
    main()
