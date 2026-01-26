"""
Extract text from response and critique PDFs in triad_1 folder.
Saves the extracted text to a separate folder.
"""
from pdfminer.high_level import extract_text
from pathlib import Path
import json


def extract_and_save_pdf_text(pdf_path: Path, output_dir: Path) -> dict:
    """
    Extract text from a PDF file and save it to a JSON file.

    Args:
        pdf_path: Path to the PDF file
        output_dir: Directory to save the extracted text

    Returns:
        Dictionary containing the extracted text and metadata
    """
    print(f"\nExtracting text from: {pdf_path.name}")

    # Extract text from PDF
    text = extract_text(str(pdf_path))

    # Create result dictionary
    result = {
        'source_file': pdf_path.name,
        'text': text,
        'text_length': len(text)
    }

    # Save to JSON file
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{pdf_path.stem}_text.json"

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"  Saved to: {output_path}")
    print(f"  Text length: {len(text)} characters")
    print(f"  Preview: {text[:200]}...")

    return result


def process_triad_pdfs(triad_dir: Path, output_folder_name: str = "extracted_texts"):
    """
    Process all response and critique PDFs in a triad directory.

    Args:
        triad_dir: Path to the triad directory
        output_folder_name: Name of the output folder (default: "extracted_texts")
    """
    # Create output directory
    output_dir = triad_dir / output_folder_name

    # Find response and critique PDFs
    response_pdfs = list(triad_dir.glob("response_*.pdf"))
    critique_pdfs = list(triad_dir.glob("critique_*.pdf"))

    all_pdfs = response_pdfs + critique_pdfs

    if not all_pdfs:
        print(f"No response or critique PDFs found in {triad_dir}")
        return

    print(f"Found {len(all_pdfs)} PDF(s) to process:")
    print(f"  - {len(response_pdfs)} response PDF(s)")
    print(f"  - {len(critique_pdfs)} critique PDF(s)")

    results = {}

    # Process each PDF
    for pdf_path in all_pdfs:
        result = extract_and_save_pdf_text(pdf_path, output_dir)
        results[pdf_path.name] = result

    print(f"\n✓ Successfully processed {len(results)} PDF(s)")
    print(f"✓ Output saved to: {output_dir}")

    return results


if __name__ == "__main__":
    # Define triad_1 directory
    triad_1_dir = Path("data/triad_samples/triad_1")

    # Process PDFs
    print("Processing triad_1 PDFs...")
    process_triad_pdfs(triad_1_dir)
