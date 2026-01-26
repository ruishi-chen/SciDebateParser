from pdfminer.high_level import extract_pages
from pdfminer.layout import LTTextContainer
from pathlib import Path
import json

def extract_blocks(pdf_path: Path):
    """
    Extract text blocks from a PDF file.

    Args:
        pdf_path: Path to the PDF file

    Returns:
        List of dictionaries containing block information:
        - page: page number (1-indexed)
        - x0, y0, x1, y1: bounding box coordinates
        - text: extracted text content
    """
    blocks = []
    for page_idx, page in enumerate(extract_pages(pdf_path)):
        for el in page:
            if isinstance(el, LTTextContainer):
                blocks.append({
                    "page": page_idx + 1,
                    "x0": el.x0,
                    "y0": el.y0,
                    "x1": el.x1,
                    "y1": el.y1,
                    "text": el.get_text().strip()
                })
    # Sort by page first, then by y-coordinate (top to bottom), then by x-coordinate (left to right)
    blocks.sort(key=lambda b: (b["page"], -b["y0"], b["x0"]))
    return blocks

def save_chunks(work_id: str, blocks, out_dir: Path):
    """
    Save extracted text blocks to a JSON file.

    Args:
        work_id: Identifier for the work (used as filename)
        blocks: List of block dictionaries to save
        out_dir: Output directory path
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    output_path = out_dir / f"{work_id}.json"
    output_path.write_text(
        json.dumps(blocks, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )