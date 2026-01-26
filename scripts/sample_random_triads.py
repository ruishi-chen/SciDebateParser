#!/usr/bin/env python3
"""
Randomly sample 150 triads from final_generation_4, final_generation_5, and final_generation_6 folders
and create a CSV file with triad numbers and predicted labels.
Also copy the sampled triad folders to a separate directory.
"""

import os
import json
import random
import csv
import shutil
from pathlib import Path

def get_triad_folders(base_dir, folder_names):
    """Get all triad folders from specified generation folders."""
    all_triads = []

    for folder_name in folder_names:
        folder_path = os.path.join(base_dir, folder_name)
        if not os.path.exists(folder_path):
            print(f"Warning: {folder_path} does not exist")
            continue

        # Get all triad folders
        triads = [d for d in os.listdir(folder_path)
                 if d.startswith('triad_') and os.path.isdir(os.path.join(folder_path, d))]

        # Store with source folder info
        for triad in triads:
            all_triads.append({
                'folder': folder_name,
                'triad_name': triad,
                'path': os.path.join(folder_path, triad)
            })

    return all_triads

def get_predicted_label(triad_path):
    """Extract predicted label from summary.json file."""
    summary_path = os.path.join(triad_path, 'final_outputs', 'summary.json')

    if not os.path.exists(summary_path):
        return None

    try:
        with open(summary_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('quality', {}).get('prediction_label')
    except Exception as e:
        print(f"Error reading {summary_path}: {e}")
        return None

def main():
    # Configuration
    base_dir = 'data'
    folder_names = ['final_generation_4', 'final_generation_5', 'final_generation_6']
    sample_size = 150
    output_csv = 'sampled_triads_labels.csv'
    output_folder = 'sampled_150_triads'

    # Get all triad folders
    print("Gathering all triad folders...")
    all_triads = get_triad_folders(base_dir, folder_names)
    print(f"Found {len(all_triads)} total triads")

    # Randomly sample 150 triads
    print(f"Randomly sampling {sample_size} triads...")
    random.seed(42)  # For reproducibility
    sampled_triads = random.sample(all_triads, min(sample_size, len(all_triads)))

    # Create output folder
    if os.path.exists(output_folder):
        print(f"Removing existing {output_folder}...")
        shutil.rmtree(output_folder)

    print(f"Creating {output_folder}...")
    os.makedirs(output_folder)

    # Extract triad numbers and predicted labels, and copy folders
    print("Copying triad folders and extracting predicted labels...")
    results = []
    for i, triad_info in enumerate(sampled_triads, 1):
        triad_name = triad_info['triad_name']
        triad_number = triad_name.replace('triad_', '')
        predicted_label = get_predicted_label(triad_info['path'])

        results.append({
            'triad_number': triad_number,
            'predicted_label': predicted_label if predicted_label else 'N/A',
            'source_folder': triad_info['folder']
        })

        # Copy the triad folder to output directory
        dest_path = os.path.join(output_folder, triad_name)
        shutil.copytree(triad_info['path'], dest_path)

        if i % 10 == 0:
            print(f"  Copied {i}/{len(sampled_triads)} triads...")

    # Sort by triad number
    results.sort(key=lambda x: int(x['triad_number']))

    # Write to CSV
    print(f"Writing results to {output_csv}...")
    with open(output_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['triad_number', 'predicted_label', 'source_folder'])
        writer.writeheader()
        writer.writerows(results)

    print(f"\nDone! Sampled {len(results)} triads")
    print(f"Output saved to {output_csv}")
    print(f"Triad folders copied to {output_folder}/")

    # Print statistics
    label_counts = {}
    for result in results:
        label = result['predicted_label']
        label_counts[label] = label_counts.get(label, 0) + 1

    print("\nLabel distribution:")
    for label, count in sorted(label_counts.items()):
        print(f"  {label}: {count}")

    print("\nSource folder distribution:")
    folder_counts = {}
    for result in results:
        folder = result['source_folder']
        folder_counts[folder] = folder_counts.get(folder, 0) + 1

    for folder, count in sorted(folder_counts.items()):
        print(f"  {folder}: {count}")

if __name__ == '__main__':
    main()
