# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""
Evaluate extracted JSON against expected JSON.

Compares output/<name>.json vs expected/<name>.json for each PDF.
Both expected and output are flat lists of players with:
  league, team, name, position, number, age, nationality, phone, address.

Scores: player count accuracy, field-level accuracy.
Weights: 01_split_headers ×1, 02_vertical_header ×2, 03_watermark ×3.

Run:
  uv run eval.py                    # all PDFs
  uv run eval.py 01_split_headers   # single file (by stem)
  uv run eval.py 01_split_headers 03_watermark
"""

import json
import sys
from pathlib import Path
from difflib import SequenceMatcher

EXPECTED_DIR = Path(__file__).parent / "expected"
OUTPUT_DIR = Path(__file__).parent / "output"

FIELDS = ["league", "team", "name", "position", "number", "age", "nationality", "phone", "address"]
WEIGHTS = {"01_split_headers": 1, "02_vertical_header": 2, "03_watermark": 3}


def normalize(value: str | int) -> str:
    return str(value).strip().lower()


def fuzzy_match(a: str, b: str, threshold: float = 0.85) -> bool:
    """Allow minor spelling differences (accents, transliteration)."""
    if normalize(a) == normalize(b):
        return True
    return SequenceMatcher(None, normalize(a), normalize(b)).ratio() >= threshold


def match_player(exp: dict, out_list: list[dict]) -> dict | None:
    """Find best matching output player for an expected player (fuzzy name + league/team)."""
    best = None
    best_score = 0.0
    for out in out_list:
        name_ok = fuzzy_match(exp.get("name", ""), out.get("name", ""))
        league_ok = fuzzy_match(exp.get("league", ""), out.get("league", ""))
        team_ok = fuzzy_match(exp.get("team", ""), out.get("team", ""))
        if not name_ok:
            continue
        score = (1.0 if name_ok else 0) + (0.5 if league_ok else 0) + (0.5 if team_ok else 0)
        if score > best_score:
            best_score = score
            best = out
    return best


def score_file(expected_path: Path, output_path: Path) -> dict:
    """Score a single file. Expected and output are flat lists of player dicts."""
    with open(expected_path, encoding="utf-8") as f:
        expected = json.load(f)
    with open(output_path, encoding="utf-8") as f:
        output = json.load(f)

    if not isinstance(expected, list):
        expected = []
    if not isinstance(output, list):
        output = []

    total_players = len(expected)
    used = set()
    found_players = 0
    field_correct = 0
    field_total = 0
    errors: list[str] = []

    for exp in expected:
        out = match_player(exp, output)
        if out is None:
            errors.append(f"Player not found: {exp.get('name')} ({exp.get('team')})")
            field_total += len(FIELDS)
            continue

        idx = id(out)
        if idx in used:
            errors.append(f"Duplicate match: {exp.get('name')} ({exp.get('team')})")
        used.add(idx)
        found_players += 1

        for field in FIELDS:
            field_total += 1
            exp_val = exp.get(field)
            out_val = out.get(field)
            if exp_val is None and out_val is None:
                field_correct += 1
            elif exp_val is not None and out_val is not None:
                if fuzzy_match(str(exp_val), str(out_val)):
                    if field in {"phone", "address"}:
                        if normalize(str(exp_val)) == normalize(str(out_val)):
                            field_correct += 1
                        else:
                            errors.append(
                                f"  {exp.get('name')}.{field}: expected '{exp_val}', got '{out_val}'"
                            )
                    else:
                        field_correct += 1
                else:
                    errors.append(
                        f"  {exp.get('name')}.{field}: expected '{exp_val}', got '{out_val}'"
                    )
            else:
                errors.append(
                    f"  {exp.get('name')}.{field}: expected '{exp_val}', got '{out_val}'"
                )

    extra_players = len(output) - len(used)
    if extra_players < 0:
        extra_players = 0

    player_accuracy = found_players / total_players if total_players else 0
    field_accuracy = field_correct / field_total if field_total else 0
    overall = 0.4 * player_accuracy + 0.6 * field_accuracy

    return {
        "total_players": total_players,
        "found_players": found_players,
        "extra_players": extra_players,
        "player_accuracy": player_accuracy,
        "field_correct": field_correct,
        "field_total": field_total,
        "field_accuracy": field_accuracy,
        "overall": overall,
        "errors": errors,
    }


def main():
    if not OUTPUT_DIR.exists():
        print("No output/ directory found.")
        print("Run `uv run starter.py` first to generate extraction results.")
        sys.exit(1)

    expected_files = sorted(EXPECTED_DIR.glob("*.json"))
    if not expected_files:
        print("No expected JSON files found in expected/")
        sys.exit(1)

    # If stems given (e.g. 01_split_headers 03_watermark), only evaluate those.
    filter_stems = None
    if len(sys.argv) > 1:
        filter_stems = set(s.replace(".json", "") for s in sys.argv[1:])
        expected_files = [p for p in expected_files if p.stem in filter_stems]
        if not expected_files:
            print("No matching expected files for:", ", ".join(sorted(filter_stems)))
            sys.exit(1)

    print("=" * 65)
    print("  PDF Extraction — Evaluation Results (flat list)")
    print("=" * 65)

    total_weighted = 0
    total_weight = 0

    for exp_path in expected_files:
        stem = exp_path.stem
        out_path = OUTPUT_DIR / exp_path.name
        weight = WEIGHTS.get(stem, 1)

        print(f"\n{'─' * 65}")
        print(f"  {stem}.pdf  (weight: {weight}x)")
        print("─" * 65)

        if not out_path.exists():
            print(f"  SKIP — {out_path.name} not found in output/")
            continue

        try:
            result = score_file(exp_path, out_path)
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            print(f"  ERROR — failed to parse output: {e}")
            continue

        print(f"  Players found:    {result['found_players']}/{result['total_players']}"
              f"  ({result['player_accuracy']:.0%})")
        if result["extra_players"]:
            print(f"  Extra players:    {result['extra_players']} (hallucinated)")
        print(f"  Field accuracy:   {result['field_correct']}/{result['field_total']}"
              f"  ({result['field_accuracy']:.0%})")
        print(f"  Overall score:    {result['overall']:.0%}")

        if result["errors"]:
            print(f"\n  Issues ({len(result['errors'])}):")
            for err in result["errors"][:15]:
                print(f"    • {err}")
            if len(result["errors"]) > 15:
                print(f"    ... and {len(result['errors']) - 15} more")

        total_weighted += result["overall"] * weight
        total_weight += weight

    final = total_weighted / total_weight if total_weight else 0
    print(f"\n{'=' * 65}")
    print(f"  FINAL WEIGHTED SCORE:  {final:.0%}")
    print(f"  (split_headers×1 + vertical_header×2 + watermark×3)")
    print("=" * 65)

    if final >= 0.95:
        print("\n  Excellent work!")
    elif final >= 0.80:
        print("\n  Good result. Try refining your prompt for edge cases.")
    elif final >= 0.60:
        print("\n  Decent start. Review the hints in README.md.")
    else:
        print("\n  Keep iterating on your prompt. Check few-shot and CoT techniques.")


if __name__ == "__main__":
    main()
