"""
Triad processor with support for new folder structure (raw_data + intermediate_results).

This is an adapted version of TriadProcessor that works with the new directory structure:
- raw_data/: Original PDFs and metadata
- intermediate_results/: All processing intermediates
- final_outputs/: Final output files
"""

import subprocess
from pathlib import Path
import json
import os
import sys
from typing import Optional, Dict
from dotenv import load_dotenv

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src" / "pdf_extract"))

from xml_preprocessor import extract_metadata_from_xml
from extract_text_from_pdf import extract_and_save_pdf_text
from batch_processing_helpers import process_triad_texts_batch
from analyze_triad_relationships import analyze_triad_relationships, load_json_file
from generate_final_outputs_batch import generate_all_final_outputs_batch

# Load environment variables
load_dotenv()


class TriadProcessorBatch:
    """Triad processor for batch processing with new folder structure."""

    def __init__(self, triad_dir: Path, grobid_url: str = "http://localhost:8070",
                 openai_api_key: Optional[str] = None):
        """
        Initialize the triad processor.

        Args:
            triad_dir: Path to the triad directory (with raw_data/, intermediate_results/, final_outputs/)
            grobid_url: URL for GROBID service
            openai_api_key: OpenAI API key
        """
        self.triad_dir = Path(triad_dir)
        self.raw_data_dir = self.triad_dir / "raw_data"
        self.intermediate_dir = self.triad_dir / "intermediate_results"
        self.final_outputs_dir = self.triad_dir / "final_outputs"
        self.grobid_url = grobid_url
        self.openai_api_key = openai_api_key or os.environ.get("OPENAI_API_KEY")

        if not self.openai_api_key:
            raise ValueError("OpenAI API key not found.")

        # Ensure directories exist
        self.intermediate_dir.mkdir(parents=True, exist_ok=True)
        self.final_outputs_dir.mkdir(parents=True, exist_ok=True)

    def print_section_header(self, title: str):
        """Print a formatted section header."""
        print("\n" + "="*70)
        print(f"  {title}")
        print("="*70 + "\n")

    def step1_generate_xml_from_pdf(self) -> Optional[Path]:
        """Step 1: Generate XML from original paper PDF using GROBID."""
        self.print_section_header("STEP 1: Generate XML from Original Paper PDF")

        # Find original PDF in raw_data
        original_pdfs = list(self.raw_data_dir.glob("original_*.pdf"))

        if not original_pdfs:
            print("❌ No original PDF found in raw_data/")
            return None

        original_pdf = original_pdfs[0]
        print(f"Found original PDF: {original_pdf.name}")

        # Generate output XML in intermediate_results
        xml_output = self.intermediate_dir / f"output_orginal_{original_pdf.stem.replace('original_', '')}.xml"

        # Check if XML already exists
        if xml_output.exists():
            print(f"✓ XML file already exists: {xml_output.name}")
            print("  Skipping GROBID processing")
            return xml_output

        # Call GROBID service
        print(f"Calling GROBID service at {self.grobid_url}...")

        try:
            curl_command = [
                'curl', '-v',
                '--form', f'input=@{original_pdf}',
                f'{self.grobid_url}/api/processFulltextDocument',
                '-o', str(xml_output)
            ]

            result = subprocess.run(
                curl_command,
                capture_output=True,
                text=True,
                timeout=300
            )

            if xml_output.exists() and xml_output.stat().st_size > 0:
                print(f"✓ Successfully generated XML: {xml_output.name}")
                print(f"  File size: {xml_output.stat().st_size} bytes")
                return xml_output
            else:
                print(f"❌ Failed to generate XML")
                print(f"  Error: {result.stderr}")
                return None

        except subprocess.TimeoutExpired:
            print("❌ GROBID request timed out after 5 minutes")
            return None
        except Exception as e:
            print(f"❌ Error calling GROBID: {e}")
            return None

    def step2_extract_metadata_from_xml(self, xml_path: Path) -> Optional[Dict]:
        """Step 2: Extract metadata from original paper XML."""
        self.print_section_header("STEP 2: Extract Metadata from XML")

        print(f"Processing XML: {xml_path.name}")

        try:
            # Extract metadata
            metadata = extract_metadata_from_xml(xml_path)

            # Save to intermediate_results
            output_path = self.intermediate_dir / "original_info_from_xml.json"

            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)

            print(f"✓ Metadata extracted and saved to: {output_path.name}")
            print(f"  Title: {metadata.get('title', 'N/A')[:80]}...")
            print(f"  Authors: {metadata.get('authors', 'N/A')[:80]}...")
            print(f"  Abstract length: {len(metadata.get('abstract', ''))} characters")

            return metadata

        except Exception as e:
            print(f"❌ Error extracting metadata: {e}")
            return None

    def step3_extract_text_from_pdfs(self) -> Dict[str, Dict]:
        """Step 3: Extract text from critique and response PDFs."""
        self.print_section_header("STEP 3: Extract Text from Critique and Response PDFs")

        # Create output directory in intermediate_results
        output_dir = self.intermediate_dir / "extracted_texts"
        output_dir.mkdir(parents=True, exist_ok=True)

        # Find critique and response PDFs in raw_data
        critique_pdfs = list(self.raw_data_dir.glob("critique_*.pdf"))
        response_pdfs = list(self.raw_data_dir.glob("response_*.pdf"))

        all_pdfs = critique_pdfs + response_pdfs

        if not all_pdfs:
            print("❌ No critique or response PDFs found in raw_data/")
            return {}

        print(f"Found {len(all_pdfs)} PDF(s):")
        print(f"  - {len(critique_pdfs)} critique PDF(s)")
        print(f"  - {len(response_pdfs)} response PDF(s)")

        results = {}

        for pdf_path in all_pdfs:
            try:
                result = extract_and_save_pdf_text(pdf_path, output_dir)
                results[pdf_path.name] = result
            except Exception as e:
                print(f"❌ Error processing {pdf_path.name}: {e}")

        print(f"\n✓ Successfully extracted text from {len(results)}/{len(all_pdfs)} PDF(s)")
        print(f"✓ Output saved to: {output_dir}")

        return results

    def step4_structure_with_openai(self) -> Dict[str, Dict]:
        """Step 4: Process extracted texts with OpenAI to get structured data."""
        self.print_section_header("STEP 4: Structure Texts with OpenAI")

        try:
            # Use batch version that looks in intermediate_results
            results = process_triad_texts_batch(self.triad_dir, self.openai_api_key)
            return results or {}
        except Exception as e:
            print(f"❌ Error during OpenAI processing: {e}")
            return {}

    def step5_analyze_relationships(self) -> Optional[Dict]:
        """Step 5: Analyze relationships between original, critique, and response."""
        self.print_section_header("STEP 5: Analyze Triad Relationships")

        # Load original metadata from intermediate_results
        original_metadata_file = self.intermediate_dir / "original_info_from_xml.json"
        if not original_metadata_file.exists():
            print(f"❌ Original metadata not found: {original_metadata_file}")
            return None

        print(f"Loading original metadata...")
        original_metadata = load_json_file(original_metadata_file)
        print(f"  Title: {original_metadata.get('title', 'N/A')[:60]}...")

        # Load structured critique data from intermediate_results
        openai_structured_dir = self.intermediate_dir / "openai_structured"
        critique_files = list(openai_structured_dir.glob("critique_*_structured.json"))

        if critique_files:
            critique_data = load_json_file(critique_files[0])
            print(f"  Loaded {len(critique_data.get('articles', []))} critique article(s)")
        else:
            print("  Warning: No critique structured file found")
            critique_data = {"articles": []}

        # Load structured response data from intermediate_results
        response_files = list(openai_structured_dir.glob("response_*_structured.json"))

        if response_files:
            response_data = load_json_file(response_files[0])
            print(f"  Loaded {len(response_data.get('articles', []))} response article(s)")
        else:
            print("  Warning: No response structured file found")
            response_data = {"articles": []}

        # Perform analysis
        print("\nPerforming relationship analysis...")

        try:
            analysis_result = analyze_triad_relationships(
                original_metadata,
                critique_data,
                response_data,
                self.openai_api_key
            )

            # Save result in intermediate_results
            output_dir = self.intermediate_dir / "relationship_analysis"
            output_dir.mkdir(parents=True, exist_ok=True)

            output_path = output_dir / "triad_relationship_analysis.json"
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(analysis_result, f, ensure_ascii=False, indent=2)

            print(f"\n✓ Analysis saved to: {output_path}")

            # Print summary
            print("\n" + "-"*70)
            print("ANALYSIS SUMMARY:")
            print("-"*70)

            related_critiques = analysis_result.get('related_critiques', [])
            related_responses = analysis_result.get('related_responses', [])
            talk_to_each_other = analysis_result.get('talk_to_each_other', False)
            flag = analysis_result.get('flag')

            print(f"Related Critiques: {len(related_critiques)}")
            for critique in related_critiques:
                print(f"  - {critique.get('title', 'N/A')[:60]}...")

            print(f"\nRelated Responses: {len(related_responses)}")
            for response in related_responses:
                print(f"  - {response.get('title', 'N/A')[:60]}...")

            print(f"\nTalk to Each Other: {talk_to_each_other}")
            print(f"Flag: {flag if flag else 'None'}")

            if analysis_result.get('explanation'):
                print(f"\nExplanation: {analysis_result['explanation']}")

            return analysis_result

        except Exception as e:
            print(f"❌ Error during analysis: {e}")
            return None

    def step6_generate_final_outputs(self) -> bool:
        """Step 6: Generate all final output files."""
        self.print_section_header("STEP 6: Generate Final Output Files")

        try:
            # Use batch version that works with new structure
            generate_all_final_outputs_batch(self.triad_dir)
            return True
        except Exception as e:
            print(f"❌ Error generating final outputs: {e}")
            return False

    def run_full_workflow(self, start_from_step: int = 1) -> bool:
        """
        Run the complete workflow from start to finish.

        Args:
            start_from_step: Which step to start from (1-6)

        Returns:
            True if successful, False otherwise
        """
        print("\n" + "█"*70)
        print("  TRIAD PROCESSING WORKFLOW (BATCH MODE)")
        print(f"  Directory: {self.triad_dir.name}")
        print("█"*70)

        if not self.triad_dir.exists():
            print(f"\n❌ Triad directory does not exist: {self.triad_dir}")
            return False

        # Step 1: Generate XML
        if start_from_step <= 1:
            xml_path = self.step1_generate_xml_from_pdf()
            if not xml_path:
                print("\n❌ Workflow failed at Step 1")
                return False
        else:
            xml_files = list(self.intermediate_dir.glob("output_orginal_*.xml"))
            if not xml_files:
                print("\n❌ No XML file found. Please run from Step 1.")
                return False
            xml_path = xml_files[0]

        # Step 2: Extract metadata
        if start_from_step <= 2:
            metadata = self.step2_extract_metadata_from_xml(xml_path)
            if not metadata:
                print("\n❌ Workflow failed at Step 2")
                return False

        # Step 3: Extract text from PDFs
        if start_from_step <= 3:
            text_results = self.step3_extract_text_from_pdfs()
            if not text_results:
                print("\n❌ Workflow failed at Step 3")
                return False

        # Step 4: Structure with OpenAI
        if start_from_step <= 4:
            structured_results = self.step4_structure_with_openai()
            if not structured_results:
                print("\n❌ Workflow failed at Step 4")
                return False

        # Step 5: Analyze relationships
        if start_from_step <= 5:
            analysis_result = self.step5_analyze_relationships()
            if not analysis_result:
                print("\n❌ Workflow failed at Step 5")
                return False

        # Step 6: Generate final outputs
        if start_from_step <= 6:
            final_outputs_success = self.step6_generate_final_outputs()
            if not final_outputs_success:
                print("\n❌ Workflow failed at Step 6")
                return False

        # Success!
        print("\n" + "█"*70)
        print("  ✓ WORKFLOW COMPLETED SUCCESSFULLY!")
        print("█"*70 + "\n")

        return True
