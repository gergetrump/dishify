import ast
import json
import time
from collections import Counter
from pathlib import Path

import pandas as pd
from ingredient_parser import parse_ingredient


def parse_ingredient_names(raw_list: list[str]) -> list[str]:
    """Extract item names from raw ingredient strings using ingredient_parser."""
    names = []
    for raw in raw_list:
        try:
            parsed = parse_ingredient(raw)
            item = parsed.name[0].text if parsed.name else None
            if item:
                names.append(item.strip().lower())
        except Exception:
            pass
    return names


def annotate_row(ingredient_names: list[str], rules: dict[str, list[str]]) -> list[str]:
    """Return list of triggered restrictions for a recipe."""
    text = " ".join(ingredient_names)
    triggered = []
    for restriction, keywords in rules.items():
        if any(kw in text for kw in keywords):
            triggered.append(restriction)
    return triggered


def main():
    csv_path = Path("./data/dataset_full_normalized.csv")
    out_path = Path("./data/dataset_full_annotated.csv")
    rules_path = Path("./data/restriction_rules.json")
    chunk_size = 10_000

    # Load restriction rules from JSON.
    with rules_path.open("r", encoding="utf-8") as f:
        rules = json.load(f)
    print(f"Loaded rules for {len(rules)} restrictions")

    # Annotate the full dataset in chunks.
    results: list[list[str]] = []
    total_rows = 0
    t0 = time.time()

    print("Annotating dataset...")
    for chunk in pd.read_csv(
        csv_path, usecols=["ingredients"], chunksize=chunk_size, low_memory=False
    ):
        for val in chunk["ingredients"]:
            try:
                raw_list = ast.literal_eval(str(val))
            except Exception:
                raw_list = []
            names = parse_ingredient_names(raw_list)
            results.append(annotate_row(names, rules))

        total_rows += len(chunk)
        elapsed = time.time() - t0
        print(f"  {total_rows:,} rows annotated  ({elapsed:.0f}s)")

    print(f"\nDone in {time.time() - t0:.0f}s")
    avg_restrictions = (sum(len(r) for r in results) / len(results)) if results else 0.0
    print(f"Average restrictions per row: {avg_restrictions:.2f}")

    # Merge annotations back into the full dataframe and save.
    df = pd.read_csv(csv_path, low_memory=False)
    df["exclusion_restrictions"] = [json.dumps(r) for r in results]

    # Quick stats for the most common restrictions.
    all_flags = [r for row in results for r in row]
    top = Counter(all_flags).most_common(15)
    print("\nTop 15 most common restrictions:")
    for restriction, count in top:
        print(f"  {restriction}: {count:,} recipes ({count / len(results) * 100:.1f}%)")

    df.to_csv(out_path, index=False)
    print(f"Saved annotated dataset to {out_path}")


if __name__ == "__main__":
    main()
