"""
Batch processor for processing all triads from sample.csv.

New folder structure for each triad:
triad_{index}/
├── raw_data/                     # Original input files
│   ├── original_*.pdf
│   ├── critique_*.pdf
│   ├── response_*.pdf
│   └── metadata.json
├── intermediate_results/         # All intermediate processing files
│   ├── output_orginal_*.xml
│   ├── original_info_from_xml.json
│   ├── extracted_texts/
│   ├── openai_structured/
│   └── relationship_analysis/
└── final_outputs/                # Final outputs
    ├── original_paper_final.json
    ├── critique_final.json
    ├── response_final.json
    └── summary.json
"""

import csv
import json
import shutil
from pathlib import Path
from typing import Dict, List, Optional
import os
import sys
from dotenv import load_dotenv

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src" / "pdf_extract"))

from triad_processor_batch import TriadProcessorBatch

# Load environment variables
load_dotenv()


class BatchTriadProcessor:
    """Process all triads from sample.csv with resume capability."""

    def __init__(self, csv_path: Path, output_base_dir: Path,
                 pdfs_dir: Path = None,
                 grobid_url: str = "http://localhost:8070",
                 openai_api_key: Optional[str] = None):
        """
        Initialize batch processor.

        Args:
            csv_path: Path to sample.csv
            output_base_dir: Base directory for output (e.g., data/triad_samples_batch)
            pdfs_dir: Directory containing PDFs named by work_id (cloud or local path)
            grobid_url: GROBID service URL
            openai_api_key: OpenAI API key
        """
        self.csv_path = Path(csv_path)
        self.output_base_dir = Path(output_base_dir)
        # Default to Google Drive cloud storage path
        default_cloud_path = Path("/Users/haijingzhang/Library/CloudStorage/GoogleDrive-zhanghaijing0601@gmail.com/.shortcut-targets-by-id/1owFXwTE8aTJXIqpD3rFCZbJ0Ly-nWyX3/pdfs")
        self.pdfs_dir = Path(pdfs_dir) if pdfs_dir else default_cloud_path
        self.grobid_url = grobid_url
        self.openai_api_key = openai_api_key or os.environ.get("OPENAI_API_KEY")

        if not self.openai_api_key:
            raise ValueError("OpenAI API key not found. Set OPENAI_API_KEY environment variable.")

        # Create base output directory
        self.output_base_dir.mkdir(parents=True, exist_ok=True)

    def read_csv(self) -> List[Dict]:
        """Read sample.csv and return list of triad records."""
        records = []
        with open(self.csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                records.append(row)
        return records

    def is_already_processed(self, triad_dir: Path, force_regenerate: bool = False) -> bool:
        """
        Check if a triad has already been processed.

        Args:
            triad_dir: Path to triad directory
            force_regenerate: If True, always return False (force reprocessing)

        Returns:
            True if summary.json exists in final_outputs, False otherwise
        """
        if force_regenerate:
            return False
        summary_file = triad_dir / "final_outputs" / "summary.json"
        return summary_file.exists()

    def setup_triad_directory(self, record: Dict, force_regenerate: bool = False) -> Optional[Path]:
        """
        Setup triad directory with new folder structure.

        Args:
            record: CSV row as dictionary
            force_regenerate: If True, skip the already-processed check

        Returns:
            Path to created triad directory or None if setup failed
        """
        index = record['index']
        triad_id = record['triad_id']

        # Create triad directory with index
        triad_dir = self.output_base_dir / f"triad_{index}"

        # Check if already processed (unless force_regenerate is True)
        if self.is_already_processed(triad_dir, force_regenerate):
            print(f"  ⏭️  Already processed, skipping")
            return None

        # Create subdirectories
        raw_data_dir = triad_dir / "raw_data"
        intermediate_dir = triad_dir / "intermediate_results"
        final_outputs_dir = triad_dir / "final_outputs"

        raw_data_dir.mkdir(parents=True, exist_ok=True)
        intermediate_dir.mkdir(parents=True, exist_ok=True)
        final_outputs_dir.mkdir(parents=True, exist_ok=True)

        # Extract work IDs from record
        # Check if using old format (work_id_* columns) or new format (triad_id split)
        if 'work_id_original' in record:
            # Old format: sample.csv
            work_id_original = record['work_id_original']
            work_id_critique = record['work_id_critique']
            work_id_response = record['work_id_response']
        else:
            # New format: sample_new_100.csv (triad_id is concatenated)
            # Format: W{original}_{critique}_{response}
            parts = triad_id.split('_')
            if len(parts) == 3:
                work_id_original = parts[0]
                work_id_critique = parts[1]
                work_id_response = parts[2]
            else:
                print(f"  ❌ Invalid triad_id format: {triad_id}")
                return None

        # Copy PDFs from cloud storage (or custom pdfs_dir) using work IDs
        pdf_mapping = {
            'original': work_id_original,
            'critique': work_id_critique,
            'response': work_id_response
        }

        copied_count = 0
        for pdf_type, work_id in pdf_mapping.items():
            source_pdf = self.pdfs_dir / f"{work_id}.pdf"
            if source_pdf.exists():
                target_pdf = raw_data_dir / f"{pdf_type}_{work_id}.pdf"
                if not target_pdf.exists():
                    shutil.copy2(source_pdf, target_pdf)
                    print(f"  ✓ Copied: {pdf_type}_{work_id}.pdf")
                    copied_count += 1
                else:
                    print(f"  ⏭ Already exists: {pdf_type}_{work_id}.pdf")
                    copied_count += 1
            else:
                print(f"  ⚠️  Missing: {work_id}.pdf for {pdf_type}")

        if copied_count < 3:
            print(f"  ⚠️  Warning: Only {copied_count}/3 PDFs available")

        # Create metadata.json in raw_data
        metadata = {
            "triad_id": triad_id,
            "original_id": work_id_original,
            "critique_id": work_id_critique,
            "response_id": work_id_response,
            "csv_row": record
        }

        metadata_file = raw_data_dir / "metadata.json"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

        print(f"  ✓ Created directory structure")
        return triad_dir

    def process_all_triads(self, start_from: int = 0, limit: Optional[int] = None,
                          start_from_step: int = 1, force_regenerate: bool = False,
                          skip_indices: Optional[List[str]] = None):
        """
        Process all triads from CSV.

        Args:
            start_from: Start from this index (0-based)
            limit: Process only this many triads (None for all)
            start_from_step: Which step to start from (1-6, default: 1)
            force_regenerate: If True, regenerate outputs even if summary.json exists
            skip_indices: List of triad indices to skip (e.g., ['6925', '6930'])
        """
        print("="*70)
        print("BATCH TRIAD PROCESSING")
        print("="*70)
        print(f"CSV: {self.csv_path}")
        print(f"Output: {self.output_base_dir}")
        print(f"PDFs source: {self.pdfs_dir}")
        if force_regenerate:
            print(f"Mode: FORCE REGENERATE (will reprocess all triads)")
        if skip_indices:
            print(f"Skipping indices: {', '.join(skip_indices)}")
        print("="*70)

        # Read CSV
        records = self.read_csv()
        print(f"\nTotal records in CSV: {len(records)}")

        # Apply start_from and limit
        if limit:
            records = records[start_from:start_from + limit]
        else:
            records = records[start_from:]

        print(f"Processing records: {len(records)} (starting from index {start_from})")

        # Process each record
        results = {}
        processed_count = 0
        skipped_count = 0
        failed_count = 0

        for i, record in enumerate(records):
            index = record['index']
            triad_id = record['triad_id']

            # Check if this index should be skipped
            if skip_indices and index in skip_indices:
                print(f"\n{'='*70}")
                print(f"[{i+1}/{len(records)}] Skipping Triad Index: {index} (in skip list)")
                print(f"{'='*70}")
                skipped_count += 1
                results[index] = "SKIPPED (in skip list)"
                continue

            print(f"\n{'='*70}")
            print(f"[{i+1}/{len(records)}] Processing Triad Index: {index}")
            print(f"Triad ID: {triad_id}")
            # Handle optional status_label column (exists in sample.csv but not sample_new_100.csv)
            if 'status_label' in record:
                print(f"Status Label: {record['status_label']}")
            print(f"{'='*70}")

            # Setup directory structure and copy PDFs from pdfs_dir
            triad_dir = self.setup_triad_directory(record, force_regenerate)

            if triad_dir is None:
                # Already processed
                skipped_count += 1
                results[index] = "SKIPPED (already processed)"
                continue

            # Check if PDFs exist in raw_data
            raw_data_dir = triad_dir / "raw_data"
            pdf_count = len(list(raw_data_dir.glob("*.pdf")))

            if pdf_count < 3:
                print(f"  ⚠️  Warning: Only {pdf_count} PDF(s) found in raw_data/")
                print(f"  Skipping processing - please add PDFs manually")
                results[index] = f"FAILED (only {pdf_count} PDFs found)"
                failed_count += 1
                continue

            # Process triad
            try:
                processor = TriadProcessorBatch(
                    triad_dir=triad_dir,
                    grobid_url=self.grobid_url,
                    openai_api_key=self.openai_api_key
                )
                success = processor.run_full_workflow(start_from_step=start_from_step)

                if success:
                    results[index] = "SUCCESS"
                    processed_count += 1
                else:
                    results[index] = "FAILED"
                    failed_count += 1

            except Exception as e:
                print(f"\n❌ Error processing triad {index}: {e}")
                results[index] = f"ERROR: {str(e)[:100]}"
                failed_count += 1

        # Print final summary
        print("\n" + "="*70)
        print("BATCH PROCESSING SUMMARY")
        print("="*70)
        print(f"Total records: {len(records)}")
        print(f"Successfully processed: {processed_count}")
        print(f"Skipped (already done): {skipped_count}")
        print(f"Failed: {failed_count}")
        print("="*70)

        # Print detailed results
        print("\nDetailed Results:")
        for index, status in results.items():
            status_icon = "✓" if status == "SUCCESS" else ("⏭" if "SKIPPED" in status else "❌")
            print(f"{status_icon} Triad {index}: {status}")

        print("="*70 + "\n")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Batch process all triads from sample.csv")
    parser.add_argument(
        "--csv",
        type=str,
        default="data/sample.csv",
        help="Path to sample.csv (default: data/sample.csv)"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="data/triad_samples_batch",
        help="Output base directory (default: data/triad_samples_batch)"
    )
    parser.add_argument(
        "--pdfs-dir",
        type=str,
        default=None,
        help="Directory containing PDFs named by work_id (default: Google Drive cloud storage)"
    )
    parser.add_argument(
        "--start-from",
        type=int,
        default=0,
        help="Start processing from this index (0-based)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Process only this many triads (default: all)"
    )
    parser.add_argument(
        "--grobid-url",
        type=str,
        default="http://localhost:8070",
        help="GROBID service URL (default: http://localhost:8070)"
    )
    parser.add_argument(
        "--triad-index",
        type=str,
        help="Process only a specific triad by index (e.g., '6925')"
    )
    parser.add_argument(
        "--start-from-step",
        type=int,
        choices=[1, 2, 3, 4, 5, 6],
        default=1,
        help="Which step to start from (1-6). Use 6 for final outputs only (default: 1)"
    )
    parser.add_argument(
        "--force-regenerate",
        action="store_true",
        help="Force regenerate outputs even if already processed. Useful with --start-from-step 6 to regenerate all final outputs"
    )
    parser.add_argument(
        "--skip-indices",
        type=str,
        help="Comma-separated list of triad indices to skip (e.g., '6925,6930,6935')"
    )

    args = parser.parse_args()

    # Check for OpenAI API key
    if not os.environ.get("OPENAI_API_KEY"):
        print("❌ Error: OPENAI_API_KEY not set")
        print("\nTo set your API key:")
        print("1. Environment variable: export OPENAI_API_KEY='your-key-here'")
        print("2. Create .env file with: OPENAI_API_KEY=your-key-here")
        sys.exit(1)

    # Create batch processor
    processor = BatchTriadProcessor(
        csv_path=args.csv,
        output_base_dir=args.output_dir,
        pdfs_dir=args.pdfs_dir,
        grobid_url=args.grobid_url
    )

    # Handle single triad processing
    if args.triad_index:
        # Process single triad
        triad_dir = Path(args.output_dir) / f"triad_{args.triad_index}"

        if not triad_dir.exists():
            print(f"❌ Error: Triad directory not found: {triad_dir}")
            print(f"\nMake sure triad_{args.triad_index} exists in {args.output_dir}")
            sys.exit(1)

        print("="*70)
        print(f"PROCESSING SINGLE TRIAD: triad_{args.triad_index}")
        print(f"Starting from step: {args.start_from_step}")
        print("="*70)

        from triad_processor_batch import TriadProcessorBatch

        try:
            triad_processor = TriadProcessorBatch(
                triad_dir=triad_dir,
                grobid_url=args.grobid_url,
                openai_api_key=os.environ.get("OPENAI_API_KEY")
            )
            success = triad_processor.run_full_workflow(start_from_step=args.start_from_step)

            if success:
                print("\n✓ Processing completed successfully!")
                sys.exit(0)
            else:
                print("\n❌ Processing failed!")
                sys.exit(1)
        except Exception as e:
            print(f"\n❌ Error: {e}")
            sys.exit(1)
    else:
        # Process all triads
        # Parse skip_indices if provided
        skip_indices_list = None
        if args.skip_indices:
            skip_indices_list = [idx.strip() for idx in args.skip_indices.split(',')]

        processor.process_all_triads(
            start_from=args.start_from,
            limit=args.limit,
            start_from_step=args.start_from_step,
            force_regenerate=args.force_regenerate,
            skip_indices=skip_indices_list
        )


if __name__ == "__main__":
    main()
