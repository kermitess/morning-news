#!/usr/bin/env python3
"""Run the morning news pipeline."""

from __future__ import annotations

import json
from pathlib import Path

from graph import graph


def run_pipeline() -> dict:
    """Run the full pipeline and return the final state."""
    initial_state: dict = {}

    # graph.invoke runs the full pipeline
    final_state = graph.invoke(initial_state)

    # Save intermediate results to data/
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)

    if "articles" in final_state:
        save_json(data_dir / "fetched.json", final_state["articles"])
    if "processed" in final_state:
        save_json(data_dir / "processed.json", final_state["processed"])
    if "scored" in final_state:
        save_json(data_dir / "scored.json", final_state["scored"])
    if "ranked" in final_state:
        save_json(data_dir / "ranked.json", final_state["ranked"])
    if "limited" in final_state:
        save_json(data_dir / "limited.json", final_state["limited"])

    # Print final output
    if "output" in final_state:
        print(final_state["output"])

    return final_state


def save_json(path: Path, data: list | dict) -> None:
    """Save data as JSON."""
    with open(path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Saved {path}", flush=True)


if __name__ == "__main__":
    run_pipeline()
