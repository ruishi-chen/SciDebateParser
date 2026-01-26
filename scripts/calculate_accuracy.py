"""
Calculate accuracy rate for triad predictions.

This script:
1. Reads all summary.json files from processed triads
2. Compares prediction_label vs ground_truth_label
3. Calculates overall accuracy rate
4. Generates a detailed report of false predictions
"""
import json
from pathlib import Path
from typing import List, Dict, Tuple
import pandas as pd


def load_summary_file(summary_path: Path) -> Dict:
    """Load a summary.json file."""
    with open(summary_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def extract_triad_index(triad_path: Path) -> str:
    """Extract triad index from path (e.g., 'triad_50' -> '50')."""
    return triad_path.parent.parent.name.replace('triad_', '')


def analyze_all_triads(base_dir: Path = Path("data/triad_samples_batch")) -> Tuple[List[Dict], Dict]:
    """
    Analyze all triads and collect prediction results.

    Returns:
        Tuple of (results_list, statistics_dict)
    """
    summary_files = list(base_dir.glob("*/final_outputs/summary.json"))

    print(f"Found {len(summary_files)} triads with summary files\n")

    results = []
    correct = 0
    total = 0

    # Statistics counters
    label_stats = {
        'P': {'total': 0, 'correct': 0},
        'B': {'total': 0, 'correct': 0},
        'IV': {'total': 0, 'correct': 0}
    }

    for summary_path in sorted(summary_files):
        triad_index = extract_triad_index(summary_path)
        summary_data = load_summary_file(summary_path)

        quality = summary_data.get('quality', {})
        prediction = quality.get('prediction_label')
        ground_truth = quality.get('ground_truth_label')
        explanation = quality.get('explanation', '')

        # Skip if either label is missing
        if prediction is None or ground_truth is None:
            print(f"⚠️  Triad {triad_index}: Missing labels (prediction={prediction}, ground_truth={ground_truth})")
            continue

        total += 1
        # Consider prediction correct if:
        # 1. Exact match (prediction == ground_truth)
        # 2. Prediction is IV and ground_truth is B (treat as equivalent)
        # 3. Prediction is B and ground_truth is IV (treat as equivalent)
        is_correct = (prediction == ground_truth) or \
                     (prediction == 'IV' and ground_truth == 'B') or \
                     (prediction == 'B' and ground_truth == 'IV')

        if is_correct:
            correct += 1

        # Update statistics
        if ground_truth in label_stats:
            label_stats[ground_truth]['total'] += 1
            if is_correct:
                label_stats[ground_truth]['correct'] += 1

        # Collect result
        result = {
            'triad_index': triad_index,
            'prediction_label': prediction,
            'ground_truth_label': ground_truth,
            'is_correct': is_correct,
            'explanation': explanation,
            'summary_path': str(summary_path)
        }
        results.append(result)

    # Calculate accuracy
    accuracy = (correct / total * 100) if total > 0 else 0

    statistics = {
        'total_triads': total,
        'correct_predictions': correct,
        'false_predictions': total - correct,
        'accuracy_rate': accuracy,
        'label_breakdown': label_stats
    }

    return results, statistics


def generate_false_predictions_report(results: List[Dict]) -> pd.DataFrame:
    """Generate a report of false predictions."""
    false_predictions = [r for r in results if not r['is_correct']]

    df = pd.DataFrame(false_predictions)

    if not df.empty:
        # Reorder columns for better readability
        df = df[['triad_index', 'prediction_label', 'ground_truth_label', 'explanation']]
        df = df.sort_values('triad_index')

    return df


def print_statistics(statistics: Dict):
    """Print detailed statistics."""
    print("="*70)
    print("ACCURACY ANALYSIS RESULTS")
    print("="*70)
    print()

    print(f"Total Triads Analyzed: {statistics['total_triads']}")
    print(f"Correct Predictions: {statistics['correct_predictions']}")
    print(f"False Predictions: {statistics['false_predictions']}")
    print(f"Overall Accuracy: {statistics['accuracy_rate']:.2f}%")
    print()

    print("-"*70)
    print("Breakdown by Ground Truth Label:")
    print("-"*70)

    label_breakdown = statistics['label_breakdown']
    for label in ['P', 'B', 'IV']:
        if label in label_breakdown:
            stats = label_breakdown[label]
            total = stats['total']
            correct = stats['correct']
            acc = (correct / total * 100) if total > 0 else 0
            print(f"  {label}: {correct}/{total} correct ({acc:.1f}% accuracy)")

    print()


def generate_confusion_matrix(results: List[Dict]) -> pd.DataFrame:
    """Generate confusion matrix."""
    labels = ['P', 'B', 'IV']

    # Initialize confusion matrix
    confusion = pd.DataFrame(0, index=labels, columns=labels)

    for result in results:
        pred = result['prediction_label']
        truth = result['ground_truth_label']
        if pred in labels and truth in labels:
            confusion.loc[truth, pred] += 1

    return confusion


def main():
    """Main execution function."""
    # Analyze all triads
    results, statistics = analyze_all_triads()

    # Print statistics
    print_statistics(statistics)

    # Generate false predictions report
    false_pred_df = generate_false_predictions_report(results)

    print("-"*70)
    print(f"False Predictions: {len(false_pred_df)} triads")
    print("-"*70)
    print()

    if not false_pred_df.empty:
        print(false_pred_df.to_string(index=False))
        print()

        # Save false predictions to CSV
        output_file = "false_predictions_report.csv"
        false_pred_df.to_csv(output_file, index=False)
        print(f"✓ False predictions saved to: {output_file}")
        print()
    else:
        print("No false predictions found!")
        print()

    # Generate confusion matrix
    confusion_matrix = generate_confusion_matrix(results)

    print("-"*70)
    print("Confusion Matrix:")
    print("(Rows = Ground Truth, Columns = Predictions)")
    print("-"*70)
    print(confusion_matrix)
    print()

    # Save full results
    full_results_df = pd.DataFrame(results)
    if not full_results_df.empty:
        full_results_file = "all_predictions_results.csv"
        full_results_df.to_csv(full_results_file, index=False)
        print(f"✓ Full results saved to: {full_results_file}")

    # Save statistics as JSON
    stats_file = "accuracy_statistics.json"
    with open(stats_file, 'w', encoding='utf-8') as f:
        json.dump(statistics, f, indent=2)
    print(f"✓ Statistics saved to: {stats_file}")

    print()
    print("="*70)
    print("Analysis Complete!")
    print("="*70)


if __name__ == "__main__":
    main()
