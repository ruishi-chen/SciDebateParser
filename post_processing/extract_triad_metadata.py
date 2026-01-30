#!/usr/bin/env python3
"""
Script to extract metadata from all triad folders in PDFs directory.
Reads summary.json files and outputs a CSV with triad metadata.
"""

import os
import json
import csv
from pathlib import Path


def extract_triad_metadata(pdfs_dir: str, output_csv: str):
    """
    Extract metadata from all triad folders and write to CSV.

    Args:
        pdfs_dir: Path to the PDFs directory
        output_csv: Path to output CSV file
    """
    pdfs_path = Path(pdfs_dir)

    # Find all final_generation folders (with or without numbers)
    generation_folders = sorted([
        f for f in pdfs_path.iterdir()
        if f.is_dir() and f.name.startswith('final_generation')
    ])

    print(f"Found {len(generation_folders)} generation folders:")
    for folder in generation_folders:
        print(f"  - {folder.name}")

    # Collect all metadata
    all_metadata = []
    missing_summary = []  # Track triads without summary.json

    for gen_folder in generation_folders:
        # Find all triad folders
        triad_folders = sorted([
            f for f in gen_folder.iterdir()
            if f.is_dir() and f.name.startswith('triad_')
        ], key=lambda x: int(x.name.split('_')[1]))  # Sort by triad number

        print(f"\nProcessing {gen_folder.name}: {len(triad_folders)} triads")

        for triad_folder in triad_folders:
            triad_id = triad_folder.name  # e.g., "triad_0"
            summary_path = triad_folder / "final_outputs" / "summary.json"

            # Initialize record with defaults
            record = {
                "generation_folder": gen_folder.name,
                "triad_id": triad_id,
                "prediction_label": None,
                "papers_talking_to_each_other": None,
                "flag": None,
                "explanation": None
            }

            if summary_path.exists():
                try:
                    with open(summary_path, 'r', encoding='utf-8') as f:
                        summary = json.load(f)

                    # Extract prediction_label from quality section
                    if 'quality' in summary:
                        record['prediction_label'] = summary['quality'].get('prediction_label')

                    # Extract fields from summary section
                    if 'summary' in summary:
                        record['papers_talking_to_each_other'] = summary['summary'].get('papers_talking_to_each_other')
                        record['flag'] = summary['summary'].get('flag')
                        record['explanation'] = summary['summary'].get('explanation')

                except json.JSONDecodeError as e:
                    print(f"  Warning: Could not parse JSON in {summary_path}: {e}")
                except Exception as e:
                    print(f"  Warning: Error reading {summary_path}: {e}")
            else:
                print(f"  Warning: summary.json not found for {triad_id} in {gen_folder.name}")
                missing_summary.append({
                    "generation_folder": gen_folder.name,
                    "triad_id": triad_id
                })

            all_metadata.append(record)

    # Write to CSV
    fieldnames = [
        "generation_folder",
        "triad_id",
        "prediction_label",
        "papers_talking_to_each_other",
        "flag",
        "explanation"
    ]

    with open(output_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_metadata)

    # Write missing summary.json list to separate CSV
    missing_csv = output_csv.replace('.csv', '_missing.csv')
    with open(missing_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=["generation_folder", "triad_id"])
        writer.writeheader()
        writer.writerows(missing_summary)

    print(f"\n{'='*50}")
    print(f"Total triad folders processed: {len(all_metadata)}")
    print(f"Triads with summary.json: {len(all_metadata) - len(missing_summary)}")
    print(f"Triads missing summary.json: {len(missing_summary)}")
    print(f"\nOutput written to: {output_csv}")
    print(f"Missing list written to: {missing_csv}")


if __name__ == "__main__":
    # Define paths
    script_dir = Path(__file__).parent
    pdfs_dir = script_dir / "PDFs"
    output_csv = script_dir / "triad_metadata.csv"

    extract_triad_metadata(str(pdfs_dir), str(output_csv))
