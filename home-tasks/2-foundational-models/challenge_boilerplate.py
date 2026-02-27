# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "litellm",
# ]
# ///
"""
Challenge boilerplate — fill in YOUR_PROMPT and tweak MODELS / TEMPERATURES.

Uses LiteLLM so you can run any model through a single unified API:
  - Cloud via OpenRouter (GPT-4o, Llama, Gemma, Mistral, …)
  - Local via Ollama (llama3.2, mistral, phi3, …)

Setup (cloud):
  export OPENROUTER_API_KEY="sk-or-..."

Setup (local):
  ollama pull llama3.2

Run:
  uv run challange_boilerplate.py
"""

import os
from pathlib import Path

import litellm
from litellm import completion

litellm.suppress_debug_info = True

PROMPT = "YOUR PROMPT HERE"

MODELS = [
    # --- OpenRouter (cloud) ---
    # prefix every OpenRouter model id with "openrouter/"
    "openrouter/openai/gpt-4o",
    "openrouter/meta-llama/llama-4-scout",
    # "openrouter/google/gemma-3-4b-it",
    # "openrouter/mistralai/mistral-small-3.1-24b-instruct:free",

    # --- Local Ollama ---
    # 1. Install Ollama: https://ollama.com
    # 2. Pull a model:   ollama pull llama3.2
    # 3. Uncomment the line below (Ollama runs on localhost:11434 by default)
    # "ollama/llama3.2",
]

TEMPERATURES = [0.1, 0.7, 1.2]
SEED = 42


def ask(model: str, prompt: str, temperature: float = 0.7, seed: int | None = SEED) -> str:
    resp = completion(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
        #seed=seed,
        max_tokens=1024,
    )
    return resp.choices[0].message.content


def save_response(out_dir: Path, short_name: str, temp: float, text: str):
    slug = short_name.replace("/", "_").replace(" ", "_")
    path = out_dir / f"{slug}_t{temp}.txt"
    path.write_text(text + "\n")
    print(f"  → saved {path}")


def main():
    out_dir = Path(__file__).parent / "responses"
    out_dir.mkdir(exist_ok=True)

    print("=" * 70)
    print(f"Prompt: {PROMPT}")
    print("=" * 70)

    for model in MODELS:
        for temp in TEMPERATURES:
            short_name = model.removeprefix("openrouter/").removeprefix("ollama/")
            print(f"\n{'─' * 70}")
            print(f"Model: {short_name}  |  T={temp}")
            print("─" * 70)
            try:
                result = ask(model, PROMPT, temp)
                print(result)
                save_response(out_dir, short_name, temp, result)
            except Exception as e:
                print(f"ERROR: {e}")


if __name__ == "__main__":
    main()
