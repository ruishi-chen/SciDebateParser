#!/usr/bin/env python3
"""
Script to move invalid triads (listed in IV_triads.csv) to a separate folder.
"""

import csv
import shutil
from pathlib import Path


def move_invalid_triads(csv_path: str, pdfs_dir: str):
    """
    Move triads listed in the CSV to the Invalid_triads folder.

    Args:
        csv_path: Path to IV_triads.csv
        pdfs_dir: Path to the PDFs directory
    """
    pdfs_path = Path(pdfs_dir)
    invalid_dir = pdfs_path / "Invalid_triads"

    # Create Invalid_triads folder if it doesn't exist
    invalid_dir.mkdir(exist_ok=True)
    print(f"Destination folder: {invalid_dir}")

    # Read the CSV and move folders
    moved_count = 0
    error_count = 0
    not_found_count = 0

    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)

        for row in reader:
            generation_folder = row['generation_folder']
            triad_id = row['triad_id']

            source_path = pdfs_path / generation_folder / triad_id
            dest_path = invalid_dir / triad_id

            if not source_path.exists():
                print(f"  Warning: Source not found - {source_path}")
                not_found_count += 1
                continue

            if dest_path.exists():
                print(f"  Warning: Destination already exists - {dest_path}")
                error_count += 1
                continue

            try:
                shutil.move(str(source_path), str(dest_path))
                moved_count += 1
            except Exception as e:
                print(f"  Error moving {triad_id}: {e}")
                error_count += 1

    print(f"\n{'='*50}")
    print(f"Total triads moved: {moved_count}")
    print(f"Not found: {not_found_count}")
    print(f"Errors: {error_count}")
    print(f"\nInvalid triads moved to: {invalid_dir}")


if __name__ == "__main__":
    # Define paths (script is in post_processing/, so go up one level for project root)
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    csv_path = project_root / "data" / "IV_triads.csv"
    pdfs_dir = project_root / "PDFs"

    move_invalid_triads(str(csv_path), str(pdfs_dir))
