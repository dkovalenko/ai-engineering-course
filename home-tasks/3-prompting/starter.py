# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "litellm",
#   "pydantic",
# ]
# ///
"""
Homework: PDF Table Extraction → JSON

Pipeline:  PDF → extract_text (you implement) → LLM (your prompt) → JSON

Your tasks:
  1) Implement extract_text(pdf_path) — return the full PDF text as a string.
  2) Write the PROMPT below so the LLM returns JSON matching the expected schema.

Setup:
  export OPENROUTER_API_KEY="sk-or-..."

Run:
  uv run starter.py                        # all PDFs
  uv run starter.py pdfs/01_split_headers.pdf   # single PDF

Evaluate:
  uv run eval.py                            # all files
  uv run eval.py 01_split_headers           # single file
"""

from __future__ import annotations

import json
import sys
import unicodedata
from pathlib import Path
from typing import Optional

import litellm
from litellm import completion
from pydantic import BaseModel, ConfigDict, Field, ValidationError

litellm.suppress_debug_info = True

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------
MODEL = "openrouter/google/gemini-2.5-flash"
TEMPERATURE = 0.0
MAX_TOKENS = 20000

PDF_DIR = Path(__file__).parent / "pdfs"
OUTPUT_DIR = Path(__file__).parent / "output"

# ---------------------------------------------------------------------------
# PROMPT — write your extraction prompt here
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """
You are a data extraction engine.
"""

PROMPT = """
TODO: Write your extraction prompt here.

The PDF should be appended after this prompt.
"""


# ---------------------------------------------------------------------------
# Schema — same as expected JSON (flat list in "rows")
# ---------------------------------------------------------------------------
class PlayerRow(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    league: str = Field(min_length=2)
    team: str = Field(min_length=2)
    name: str = Field(min_length=2)
    position: Optional[str]
    number: Optional[int] = Field(ge=0, le=999)
    age: Optional[int] = Field(ge=15, le=60)
    nationality: Optional[str]
    phone: Optional[str]
    address: Optional[str]


class PlayerRowsEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")
    rows: list[PlayerRow]


# ---------------------------------------------------------------------------
# PDF text extraction — YOU IMPLEMENT THIS
# ---------------------------------------------------------------------------
def extract_text(pdf_path: Path) -> str:
    """Extract all text from a PDF. Return the full document text as a single string."""
    # TODO: implement
    return ""


# ---------------------------------------------------------------------------
# LLM and parsing
# ---------------------------------------------------------------------------
def _normalize_text(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return s.strip().lower()


def call_llm(user_prompt: str) -> str:
    schema = PlayerRowsEnvelope.model_json_schema()
    resp = completion(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "player_rows",
                "schema": schema,
                "strict": True,
            },
        },
        temperature=TEMPERATURE,
        max_tokens=MAX_TOKENS,
    )
    return resp.choices[0].message.content or ""


def _dedupe_rows(rows: list[PlayerRow]) -> list[PlayerRow]:
    seen: set[tuple[str, str, str, int]] = set()
    out: list[PlayerRow] = []
    for r in rows:
        key = (
            _normalize_text(r.league),
            _normalize_text(r.team),
            _normalize_text(r.name),
            int(r.number) if r.number is not None else -1,
        )
        if key in seen:
            continue
        seen.add(key)
        out.append(r)
    return out


def _sort_rows(rows: list[PlayerRow]) -> list[PlayerRow]:
    return sorted(
        rows,
        key=lambda r: (
            _normalize_text(r.league),
            _normalize_text(r.team),
            _normalize_text(r.name),
        ),
    )


def parse_response(raw: str) -> list[PlayerRow]:
    """Parse raw LLM response as JSON. On failure, print raw output and return []."""
    try:
        validated = PlayerRowsEnvelope.model_validate_json(raw.strip())
    except (ValidationError, json.JSONDecodeError) as e:
        preview_len = 2000
        preview = raw[:preview_len] + ("..." if len(raw) > preview_len else "")
        print("  Parse failed. Raw LLM response:")
        print("  " + "-" * 56)
        for line in preview.splitlines():
            print("  ", line)
        print("  " + "-" * 56)
        print(f"  Error: {e}")
        print("  Hint: LLM may have wrapped JSON in markdown (```json ... ```).")
        print("  Fix the prompt or strip the wrapper before parsing.")
        return []
    return _sort_rows(_dedupe_rows(validated.rows))


def save_extracted_text_markdown(pdf_path: Path, text: str) -> Path:
    OUTPUT_DIR.mkdir(exist_ok=True)
    out_path = OUTPUT_DIR / f"extracted_{pdf_path.stem}_text.md"
    out_path.write_text(text + "\n", encoding="utf-8")
    return out_path


def process_pdf(pdf_path: Path) -> list[PlayerRow]:
    print(f"\n{'─' * 60}")
    print(f"Processing: {pdf_path.name}")
    print("─" * 60)
    text = extract_text(pdf_path)
    print(f"  Extracted {len(text)} chars")
    extracted_text_path = save_extracted_text_markdown(pdf_path, text)
    print(f"  Saved extracted text -> {extracted_text_path}")
    raw = call_llm(f"{PROMPT}\n\n{text}")
    rows = parse_response(raw)
    print(f"  Parsed rows: {len(rows)}")
    return rows


def main() -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)
    if len(sys.argv) > 1:
        pdfs = [Path(p) for p in sys.argv[1:]]
    else:
        pdfs = sorted(PDF_DIR.glob("*.pdf"))

    if not pdfs:
        print("No PDFs found.")
        return

    for pdf_path in pdfs:
        rows = process_pdf(pdf_path)
        out_path = OUTPUT_DIR / pdf_path.with_suffix(".json").name
        payload = [r.model_dump() for r in rows]
        out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"  Saved -> {out_path}")

    print("\nDone.")
    print("Run: uv run eval.py   (or: uv run eval.py 01_split_headers  for one file)")


if __name__ == "__main__":
    main()
