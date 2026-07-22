"""Extract valid CSV rows when a dataset was pasted into a Markdown file.

This utility uses only the Python standard library. It keeps the original file
unchanged and writes a clean, ignored CSV suitable for model training.
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    lines = args.input.read_text(encoding="utf-8-sig").splitlines()
    header_index = next((i for i, line in enumerate(lines)
                         if "measured_force_kg" in line and "expected_force_kg" in line), None)
    if header_index is None:
        raise SystemExit("Could not find the expected force-dataset header.")
    header = next(csv.reader([lines[header_index]]))
    valid_rows = []
    for line in lines[header_index + 1:]:
        values = next(csv.reader([line]), [])
        if len(values) != len(header):
            continue
        # A valid training row needs both reference expectation and observation.
        if not values[header.index("expected_force_kg")] or not values[header.index("measured_force_kg")]:
            continue
        valid_rows.append(values)

    if not valid_rows:
        raise SystemExit("No valid data rows found.")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as output:
        writer = csv.writer(output)
        writer.writerow(header)
        writer.writerows(valid_rows)
    print(f"Wrote {len(valid_rows)} valid rows to {args.output}")


if __name__ == "__main__":
    main()
