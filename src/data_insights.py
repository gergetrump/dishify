from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterator
import ast
import csv


@dataclass(slots=True, frozen=True)
class RecipeDataPoint:
    """Represents one row from `data/full_dataset.csv`."""

    title: str  # Example: "No-Bake Nut Cookies"
    ingredients: tuple[
        str, ...
    ]  # Example: ("1 c. sugar", "1/2 c. milk", "1 stick margarine")
    directions: tuple[
        str, ...
    ]  # Example: ("In a heavy 2-quart saucepan mix sugar, cocoa, milk and margarine.", ...)
    link: str  # Example: "www.cookbooks.com/Recipe-Details.aspx?id=44874"
    source: str  # Example: "Gathered"
    ner: tuple[str, ...]  # Example: ("sugar", "milk", "margarine", "vanilla")

    @classmethod
    def from_csv_row(cls, row: dict[str, str]) -> "RecipeDataPoint":
        """Build one datapoint from a CSV DictReader row."""
        return cls(
            title=row.get("title", ""),
            ingredients=_parse_list_like_field(row.get("ingredients", "")),
            directions=_parse_list_like_field(row.get("directions", "")),
            link=row.get("link", ""),
            source=row.get("source", ""),
            ner=_parse_list_like_field(row.get("NER", "")),
        )


def _parse_list_like_field(value: str) -> tuple[str, ...]:
    """Parse a stringified Python list into an immutable tuple of strings."""
    try:
        parsed = ast.literal_eval(value)
        if isinstance(parsed, list):
            return tuple(str(item) for item in parsed)
    except (ValueError, SyntaxError):
        pass

    if not value:
        return tuple()

    return (value,)


def iter_recipe_datapoints(csv_path: str | Path) -> Iterator[RecipeDataPoint]:
    """Yield each dataset row as a `RecipeDataPoint` without loading the full file into memory."""
    path = Path(csv_path)
    with path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        for row in reader:
            yield RecipeDataPoint.from_csv_row(row)


if __name__ == "__main__":
    dataset_path = Path(__file__).parent / "dishify" / "data" / "dataset.csv"
    first_item = next(iter_recipe_datapoints(dataset_path), None)
    print(first_item)
