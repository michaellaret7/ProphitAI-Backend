"""Count tiktoken tokens for docs/algo_trading/failure_modes.md."""

from pathlib import Path

import tiktoken

REPO_ROOT = Path(__file__).resolve().parent
MD_PATH = REPO_ROOT / "docs" / "algo_trading" / "failure_modes.md"

ENCODING_NAME = "cl100k_base"


def main() -> None:
    text = MD_PATH.read_text(encoding="utf-8")
    enc = tiktoken.get_encoding(ENCODING_NAME)
    n = len(enc.encode(text))
    print(f"file: {MD_PATH}")
    print(f"encoding: {ENCODING_NAME}")
    print(f"tokens: {n}")


if __name__ == "__main__":
    main()
