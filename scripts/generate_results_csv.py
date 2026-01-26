"""
Generate result.csv from all processed triads in triad_samples_new_100.

Extracts prediction labels and explanations from summary.json files.
"""
import csv
import json
from pathlib import Path
from typing import List, Dict

# Paths
triads_dir = Path("data/triad_samples_new_100")
output_file = Path("data/result_new_100.csv")

print("="*70)
print("Generate Results CSV from Processed Triads")
print("="*70)

# Check if directory exists
if not triads_dir.exists():
    print(f"\n❌ Error: Directory not found: {triads_dir}")
    exit(1)

print(f"\n1. Scanning: {triads_dir}")

# Find all triad directories
triad_dirs = sorted([d for d in triads_dir.iterdir() if d.is_dir() and d.name.startswith("triad_")])

print(f"   Found {len(triad_dirs)} triad directories")

# Collect results
results = []
processed_count = 0
missing_summary_count = 0

print(f"\n2. Extracting data from summary.json files...")

for triad_dir in triad_dirs:
    summary_file = triad_dir / "final_outputs" / "summary.json"

    if not summary_file.exists():
        missing_summary_count += 1
        continue

    # Load summary
    try:
        with open(summary_file, 'r', encoding='utf-8') as f:
            summary = json.load(f)

        # Extract triad_id from metadata
        metadata_file = triad_dir / "raw_data" / "metadata.json"
        triad_id = None
        original_id = None
        critique_id = None
        response_id = None

        if metadata_file.exists():
            with open(metadata_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
                triad_id = metadata.get('triad_id', '')
                original_id = metadata.get('original_id', '')
                critique_id = metadata.get('critique_id', '')
                response_id = metadata.get('response_id', '')

        # If metadata not found, try to parse from directory or summary
        if not triad_id:
            # Try to get from summary
            if 'csv_row' in summary.get('quality', {}):
                triad_id = summary['quality']['csv_row'].get('triad_id', '')

        # Extract paper IDs from triad_id if individual IDs not found
        if triad_id and not original_id:
            parts = triad_id.split('_')
            if len(parts) == 3:
                original_id = parts[0]
                critique_id = parts[1]
                response_id = parts[2]

        # Extract prediction label and explanation
        quality = summary.get('quality', {})
        prediction_label = quality.get('prediction_label', 'N/A')
        explanation = quality.get('explanation', 'N/A')
        ground_truth_label = quality.get('ground_truth_label', 'N/A')

        # Extract index from directory name
        index = triad_dir.name.replace('triad_', '')

        # Add to results
        results.append({
            'index': index,
            'triad_id': triad_id,
            'original_id': original_id,
            'critique_id': critique_id,
            'response_id': response_id,
            'prediction_label': prediction_label,
            'explanation': explanation,
            'ground_truth_label': ground_truth_label
        })

        processed_count += 1

        if processed_count % 20 == 0:
            print(f"   Processed {processed_count}/{len(triad_dirs)} triads...")

    except Exception as e:
        print(f"   ⚠ Error processing {triad_dir.name}: {e}")
        continue

print(f"\n3. Results:")
print(f"   Successfully processed: {processed_count} triads")
print(f"   Missing summary.json: {missing_summary_count} triads")

# Sort by index
results.sort(key=lambda x: int(x['index']))

# Save to CSV
print(f"\n4. Saving to: {output_file}")

fieldnames = ['index', 'triad_id', 'original_id', 'critique_id', 'response_id',
              'prediction_label', 'ground_truth_label', 'explanation']

with open(output_file, 'w', encoding='utf-8', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(results)

print(f"   ✓ Saved {len(results)} records")

# Show statistics
print(f"\n5. Prediction Label Distribution:")
from collections import Counter
label_counts = Counter(r['prediction_label'] for r in results)
for label, count in sorted(label_counts.items()):
    percentage = (count / len(results) * 100) if results else 0
    print(f"   {label}: {count} ({percentage:.1f}%)")

# Show ground truth comparison if available
if any(r['ground_truth_label'] != 'N/A' for r in results):
    print(f"\n6. Ground Truth Label Distribution:")
    gt_counts = Counter(r['ground_truth_label'] for r in results if r['ground_truth_label'] != 'N/A')
    for label, count in sorted(gt_counts.items()):
        percentage = (count / len([r for r in results if r['ground_truth_label'] != 'N/A']) * 100)
        print(f"   {label}: {count} ({percentage:.1f}%)")

    # Calculate accuracy
    matches = sum(1 for r in results if r['prediction_label'] == r['ground_truth_label'] and r['ground_truth_label'] != 'N/A')
    total_with_gt = sum(1 for r in results if r['ground_truth_label'] != 'N/A')
    if total_with_gt > 0:
        accuracy = (matches / total_with_gt) * 100
        print(f"\n7. Accuracy:")
        print(f"   Correct predictions: {matches}/{total_with_gt} ({accuracy:.1f}%)")

# Show sample
print(f"\n8. Sample Results (first 5):")
for i, result in enumerate(results[:5]):
    print(f"   {i+1}. {result['triad_id']}")
    print(f"      Prediction: {result['prediction_label']} - {result['explanation'][:60]}...")
    if result['ground_truth_label'] != 'N/A':
        print(f"      Ground Truth: {result['ground_truth_label']}")

print("\n" + "="*70)
print("✓ Results CSV Generated Successfully!")
print(f"✓ Output: {output_file}")
print("="*70)
