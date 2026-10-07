"""Lexlynx: summarise a case law PDF with an OpenAI-compatible chat model.

    python lexlynx.py judgment.pdf                        # OpenAI (OPENAI_API_KEY)
    python lexlynx.py judgment.pdf --output summary.md
    python lexlynx.py judgment.pdf --base-url http://localhost:11434/v1 --model qwen3:14b   # local Ollama, free

Long judgments are split into chunks, each chunk is summarised, and the chunk summaries are combined into
one summary.
"""
import argparse
import os
import re
import sys

import pymupdf
from openai import OpenAI
from tqdm import tqdm

DEFAULT_MODEL = "gpt-4o-mini"
CHUNK_PROMPT = ("Summarise this part of a judgment. Note the parties, the legal issues, the court's findings and "
                "reasoning, and any precedents relied on. Be precise and do not invent details.")
COMBINE_PROMPT = ("These are summaries of consecutive parts of one judgment. Combine them into a single summary "
                  "with these headings: Case, Facts, Issues, Holding, Reasoning, Precedents. Remove repetition; "
                  "do not invent details.")


def extract_text_from_pdf(pdf_path):
    with pymupdf.open(pdf_path) as doc:
        return "\n".join(page.get_text("text") for page in doc)


def chunk_text(text, chunk_size=8000):
    """Split on paragraph breaks where possible, so a chunk does not end mid-sentence."""
    chunks, current = [], ""
    for paragraph in re.split(r"\n\s*\n", text):
        if current and len(current) + len(paragraph) > chunk_size:
            chunks.append(current)
            current = ""
        while len(paragraph) > chunk_size:
            chunks.append(paragraph[:chunk_size])
            paragraph = paragraph[chunk_size:]
        current += paragraph + "\n\n"
    if current.strip():
        chunks.append(current)
    return chunks


def ask(client, model, instruction, content, max_tokens):
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": instruction}, {"role": "user", "content": content}],
        max_tokens=max_tokens,
    )
    reply = response.choices[0].message.content or ""
    return re.sub(r"<think>.*?</think>", "", reply, flags=re.S).strip()  # reasoning models' thinking, if any


def summarise(text, client, model, chunk_size=8000, max_tokens=1500):
    chunks = chunk_text(text, chunk_size)
    parts = [ask(client, model, CHUNK_PROMPT, chunk, max_tokens)
             for chunk in tqdm(chunks, desc="Summarising", unit="chunk")]
    if len(parts) == 1:
        return parts[0]
    return ask(client, model, COMBINE_PROMPT, "\n\n---\n\n".join(parts), max_tokens * 2)


def main():
    parser = argparse.ArgumentParser(description="Summarise a case law PDF.")
    parser.add_argument("pdf", help="Path to the judgment PDF.")
    parser.add_argument("--model", default=os.environ.get("LEXLYNX_MODEL", DEFAULT_MODEL),
                        help=f"Chat model (default: $LEXLYNX_MODEL or {DEFAULT_MODEL}).")
    parser.add_argument("--base-url", default=os.environ.get("OPENAI_BASE_URL"),
                        help="OpenAI-compatible endpoint, e.g. http://localhost:11434/v1 for Ollama.")
    parser.add_argument("--output", help="Also write the summary to this file.")
    parser.add_argument("--chunk-size", type=int, default=8000, help="Characters per chunk (default 8000).")
    args = parser.parse_args()

    api_key = os.environ.get("OPENAI_API_KEY") or ("ollama" if args.base_url else None)
    if not api_key:
        sys.exit("Set OPENAI_API_KEY, or pass --base-url for a local OpenAI-compatible server such as Ollama.")
    if not os.path.exists(args.pdf):
        sys.exit(f"No such file: {args.pdf}")

    client = OpenAI(api_key=api_key, base_url=args.base_url)
    text = extract_text_from_pdf(args.pdf)
    if not text.strip():
        sys.exit("No text found in the PDF (is it a scanned image?).")
    summary = summarise(text, client, args.model, args.chunk_size)
    print("\nSummary of Case Law:\n")
    print(summary)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(summary + "\n")
        print(f"\nSaved to {args.output}")


if __name__ == "__main__":
    main()
