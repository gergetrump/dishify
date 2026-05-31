import ast
import os
import time
from collections import Counter

import pandas as pd
from ingredient_parser import parse_ingredient


def safe_parse_list(value):
    # Parse list-like strings safely; return empty list on any failure.
    if pd.isna(value):
        return []
    text = str(value).strip()
    if not text:
        return []
    try:
        parsed = ast.literal_eval(text)
        return parsed if isinstance(parsed, list) else []
    except Exception:
        return []


def normalize_ingredients(raw_ingredients):
    # Convert raw ingredient strings into (item, quantity, unit) tuples.
    parsed_tuples = []
    for raw in raw_ingredients:
        parsed = parse_ingredient(raw)
        item = parsed.name[0].text if len(parsed.name) > 0 else None

        quantity = None
        unit = None

        if parsed.amount:
            amount_obj = parsed.amount[0]
            quantity_value = getattr(amount_obj, "quantity", None)
            if quantity_value is not None:
                try:
                    quantity = str(float(quantity_value))
                except ValueError:
                    quantity = str(quantity_value)

            unit_value = getattr(amount_obj, "unit", None)
            if unit_value is not None:
                unit = str(unit_value)

        parsed_tuples.append((item, quantity, unit))
    return parsed_tuples


def main():
    # Load cleaned full dataset for normalization.
    csv_path = "./data/dataset_full_cleaned.csv"
    df = pd.read_csv(csv_path, low_memory=False)

    # Ensure output columns exist with fixed row alignment.

    # Apply normalize_ingredients row by row for easier debugging
    print("Normalizing ingredients row by row...")
    raw_ingredients_list = [None] * len(df)
    normalized_ingredients = [None] * len(df)
    t0 = time.time()

    for idx, raw_value in enumerate(df["ingredients"]):
        # Parse per-row ingredient list, then normalize each ingredient string.
        try:
            raw_list = (
                ast.literal_eval(raw_value) if isinstance(raw_value, str) else raw_value
            )
            normalized_row = normalize_ingredients(raw_list)
            normalized_ingredients[idx] = normalized_row
            only_items = list(map(lambda item: item[0], normalized_row))
            raw_ingredients_list[idx] = only_items

        except Exception as e:
            normalized_ingredients[idx] = []
            raw_ingredients_list[idx] = []
            print(f"Row {idx} failed: {e}")

        if (idx + 1) % 10_000 == 0:
            # Compute processing rate and ETA based on elapsed time.
            elapsed = time.time() - t0
            processed = idx + 1
            rate = processed / elapsed if elapsed > 0 else 0
            remaining = len(df) - processed
            eta = remaining / rate if rate > 0 else 0
            print(
                f"Processed {processed:,} rows in {elapsed:.2f} seconds. "
                f"ETA: {eta / 60:.1f} minutes"
            )

            # Save a rolling backup every 10k rows.
            df["normalized_ingredients"] = normalized_ingredients
            df["raw_ingredients"] = raw_ingredients_list
            backup_path = "./data/backup/dataset_full_normalized_backup.csv"
            os.makedirs(os.path.dirname(backup_path), exist_ok=True)
            df.to_csv(backup_path, index=False)

    df["normalized_ingredients"] = normalized_ingredients
    df["raw_ingredients"] = raw_ingredients_list

    print("Done.")

    print(df[["title", "normalized_ingredients"]].head(3).to_string(index=False))
    print(f"Total time taken: {time.time() - t0:.2f} seconds")

    # Drop rows with failed normalization before final save.
    keep_mask = df["normalized_ingredients"].map(
        lambda v: isinstance(v, list) and len(v) > 0
    )
    keep_mask &= df["raw_ingredients"].map(lambda v: isinstance(v, list) and len(v) > 0)
    final_df = df.loc[keep_mask].copy()
    print(f"Final rows after dropping failed normalizations: {final_df.shape[0]}")

    final_df.to_csv("./data/dataset_full_normalized.csv", index=False)


if __name__ == "__main__":
    main()
