#!/usr/bin/env python3
"""
Analysis script for result_new_100.csv

This script analyzes the prediction results and calculates:
1. Count of P/B/IV labels in prediction_label column
2. Accuracy compared with human annotation (ground_truth_label)
3. For IV labels, count of each type of comment/explanation
"""

import pandas as pd
import numpy as np
from collections import Counter
import re

def analyze_results(csv_file_path):
    """
    Analyze the results CSV file and generate comprehensive statistics.

    Args:
        csv_file_path: Path to the CSV file containing results
    """
    print("=" * 70)
    print("TRIAD ANALYSIS RESULTS")
    print("=" * 70)

    # Load the CSV file
    try:
        df = pd.read_csv(csv_file_path)
        print(f"✓ Loaded CSV file: {csv_file_path}")
        print(f"  Total triads analyzed: {len(df)}")
        print()
    except Exception as e:
        print(f"❌ Error loading CSV file: {e}")
        return

    # 1. Count prediction labels
    print("1. PREDICTION LABEL DISTRIBUTION")
    print("-" * 40)

    prediction_counts = df['prediction_label'].value_counts().sort_index()
    total_predictions = len(df)

    print("Label Counts:")
    for label, count in prediction_counts.items():
        percentage = (count / total_predictions) * 100
        print(f"  {label}: {count:3d} ({percentage:5.1f}%)")

    print(f"\nTotal: {total_predictions} triads")
    print()

    # 2. Calculate accuracy compared to human annotation
    print("2. ACCURACY ANALYSIS")
    print("-" * 40)

    # Check if we have ground truth labels that are not N/A
    valid_ground_truth = df[df['Human Annotation'] != 'N/A']

    if len(valid_ground_truth) > 0:
        print(f"Triads with ground truth labels: {len(valid_ground_truth)}")

        # Calculate accuracy for each label type
        accuracy_by_label = {}

        for label in ['P', 'B', 'IV']:
            # Get triads where prediction is this label and we have ground truth
            predicted_label = valid_ground_truth[valid_ground_truth['prediction_label'] == label]

            if len(predicted_label) > 0:
                # Count correct predictions
                correct = (predicted_label['prediction_label'] == predicted_label['Human Annotation']).sum()
                total = len(predicted_label)
                accuracy = (correct / total) * 100 if total > 0 else 0

                accuracy_by_label[label] = {
                    'correct': correct,
                    'total': total,
                    'accuracy': accuracy
                }

                print(f"  {label} Label Accuracy: {correct}/{total} = {accuracy:.1f}%")

        # Overall accuracy
        all_correct = (valid_ground_truth['prediction_label'] == valid_ground_truth['Human Annotation']).sum()
        overall_accuracy = (all_correct / len(valid_ground_truth)) * 100
        print(f"\nOverall Accuracy: {all_correct}/{len(valid_ground_truth)} = {overall_accuracy:.1f}%")
    else:
        print("⚠ No ground truth labels available (all are 'N/A')")
        print("  Cannot calculate accuracy - this appears to be prediction-only data")

    print()

    # 3. Analyze IV comment types
    print("3. IV LABEL COMMENT ANALYSIS")
    print("-" * 40)

    iv_triads = df[df['prediction_label'] == 'IV']
    print(f"Total IV labels: {len(iv_triads)}")
    print()

    if len(iv_triads) > 0:
        # Categorize IV comments
        iv_categories = {
            'broken_paper': [],
            'not_debating': [],
            'missing_sections': [],
            'other': []
        }

        print("IV Comment Categories:")
        print()

        for idx, row in iv_triads.iterrows():
            explanation = str(row['explanation']).strip()

            # Categorize based on explanation content
            if 'broken' in explanation.lower() and ('sections' in explanation.lower() or 'missing' in explanation.lower()):
                if 'sections too short' in explanation.lower():
                    iv_categories['missing_sections'].append(explanation)
                else:
                    iv_categories['broken_paper'].append(explanation)
            elif 'not debating' in explanation.lower() or 'not talking' in explanation.lower():
                iv_categories['not_debating'].append(explanation)
            else:
                iv_categories['other'].append(explanation)

        # Count and display each category
        category_descriptions = {
            'broken_paper': 'Original paper is broken (general)',
            'missing_sections': 'Original paper missing/insufficient sections',
            'not_debating': 'Papers are not debating each other',
            'other': 'Other IV reasons'
        }

        for category, explanations in iv_categories.items():
            count = len(explanations)
            percentage = (count / len(iv_triads)) * 100 if len(iv_triads) > 0 else 0
            print(f"  {category_descriptions[category]}:")
            print(f"    Count: {count} ({percentage:.1f}% of IV)")

            if count > 0:
                print(f"    Examples:")
                # Show unique explanations in this category
                unique_explanations = list(set(explanations))[:3]  # Show up to 3 unique examples
                for i, example in enumerate(unique_explanations, 1):
                    print(f"      {i}. \"{example}\"")
            print()

        # Detailed breakdown of all unique explanations
        print("4. DETAILED IV EXPLANATIONS")
        print("-" * 40)

        explanation_counts = Counter(iv_triads['explanation'].tolist())

        print("All unique IV explanations with counts:")
        for explanation, count in explanation_counts.most_common():
            percentage = (count / len(iv_triads)) * 100
            print(f"  \"{explanation}\"")
            print(f"    Count: {count} ({percentage:.1f}% of IV)")
            print()

    # 5. Summary statistics
    print("5. SUMMARY STATISTICS")
    print("-" * 40)

    print(f"Dataset Overview:")
    print(f"  Total triads: {len(df)}")
    print(f"  Perfect (P): {prediction_counts.get('P', 0)} ({prediction_counts.get('P', 0)/len(df)*100:.1f}%)")
    print(f"  Broken (B): {prediction_counts.get('B', 0)} ({prediction_counts.get('B', 0)/len(df)*100:.1f}%)")
    print(f"  Invalid (IV): {prediction_counts.get('IV', 0)} ({prediction_counts.get('IV', 0)/len(df)*100:.1f}%)")
    print()

    # Quality distribution
    usable_triads = prediction_counts.get('P', 0) + prediction_counts.get('B', 0)
    print(f"Data Quality:")
    print(f"  Usable triads (P + B): {usable_triads} ({usable_triads/len(df)*100:.1f}%)")
    print(f"  Unusable triads (IV): {prediction_counts.get('IV', 0)} ({prediction_counts.get('IV', 0)/len(df)*100:.1f}%)")

    print()
    print("=" * 70)

def main():
    """Main function to run the analysis."""
    csv_path = "/Users/haijingzhang/Research/debate-traid-agent/data/result_new_100.csv"
    analyze_results(csv_path)

if __name__ == "__main__":
    main()