#!/usr/bin/env python3
"""
Convert the Kaggle "Fashion Product Images Dataset" (styles.csv) into the
"metadata.csv" manifest format expected by the search platform's ingestion
connector.

Standalone script, no project dependency — only the Python standard library.
Run this wherever you download the dataset; it does not need to live inside
or next to the project repository.

Expected input columns (Kaggle: paramaggarwal/fashion-product-images-dataset):
    id, gender, masterCategory, subCategory, articleType, baseColour, season,
    year, usage, productDisplayName

Output columns (the platform's metadata.csv format):
    filename, id, title, category, tags
    plus gender, season, year, usage, masterCategory passed through unchanged
    — the ingestion connector automatically keeps any extra column as
    additional metadata; it does not need to be declared anywhere.

Usage:
    python convert_fashion_dataset_to_metadata_csv.py \
        --input styles.csv --output metadata.csv \
        [--image-ext .jpg] [--images-dir /path/to/images]

With --images-dir, rows whose image file does not exist are reported and
left out of metadata.csv instead of producing an entry with nothing to match.
"""
import argparse
import csv
from pathlib import Path

# styles.csv columns folded into the pipe-separated "tags" field (searchable
# keyword text on the platform; category/title alone are not enough detail).
TAG_SOURCE_COLUMNS = ["masterCategory", "articleType", "baseColour", "season", "usage", "gender"]
CATEGORY_COLUMN = "subCategory"  # more specific than masterCategory, still a short, facet-friendly value
TITLE_COLUMN = "productDisplayName"
ID_COLUMN = "id"
# Carried through as extra columns; the ingestion connector stores unmapped
# columns as additional (non-searchable) metadata automatically.
PASSTHROUGH_COLUMNS = ["gender", "season", "year", "usage", "masterCategory"]


def clean(value):
    return (value or "").strip()


def build_tags(row):
    seen, tags = set(), []
    for column in TAG_SOURCE_COLUMNS:
        value = clean(row.get(column))
        if value and value.casefold() not in seen:
            seen.add(value.casefold())
            tags.append(value)
    return "|".join(tags)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--input", required=True, help="Path to the dataset's styles.csv")
    parser.add_argument("--output", required=True, help="Path to write metadata.csv to")
    parser.add_argument("--image-ext", default=".jpg", help="Image file extension (default .jpg)")
    parser.add_argument("--images-dir", help="Optional: images folder, to skip rows with no matching file")
    args = parser.parse_args()

    images_dir = Path(args.images_dir) if args.images_dir else None
    written = skipped_no_id = skipped_no_image = 0
    fieldnames = ["filename", "id", "title", "category", "tags", *PASSTHROUGH_COLUMNS]

    with open(args.input, newline="", encoding="utf-8-sig", errors="replace") as infile:
        reader = csv.DictReader(infile)
        with open(args.output, "w", newline="", encoding="utf-8") as outfile:
            writer = csv.DictWriter(outfile, fieldnames=fieldnames)
            writer.writeheader()
            for row in reader:
                item_id = clean(row.get(ID_COLUMN))
                if not item_id:
                    skipped_no_id += 1
                    continue
                filename = f"{item_id}{args.image_ext}"
                if images_dir and not (images_dir / filename).exists():
                    skipped_no_image += 1
                    continue
                writer.writerow({
                    "filename": filename,
                    "id": item_id,
                    "title": clean(row.get(TITLE_COLUMN)) or filename,
                    "category": clean(row.get(CATEGORY_COLUMN)) or "Uncategorized",
                    "tags": build_tags(row),
                    **{col: clean(row.get(col)) for col in PASSTHROUGH_COLUMNS},
                })
                written += 1

    print(f"Wrote {written} rows to {args.output}")
    if skipped_no_id:
        print(f"Skipped {skipped_no_id} rows with no id")
    if skipped_no_image:
        print(f"Skipped {skipped_no_image} rows with no matching image file in {images_dir}")


if __name__ == "__main__":
    main()
