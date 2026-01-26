"""
Preprocessor for extracting metadata from GROBID XML files.
Extracts title, authors, and abstract from TEI-encoded XML documents.
Only processes original XML files (not critique or response files).
"""
from pathlib import Path
import xml.etree.ElementTree as ET
from typing import Dict, Optional
import json


def extract_title(root: ET.Element, ns: Dict[str, str]) -> str:
    """
    Extract the main title from TEI XML.

    Args:
        root: XML root element
        ns: Namespace dictionary

    Returns:
        Title string or empty string if not found
    """
    # Try multiple locations for title
    title_paths = [
        ".//tei:titleStmt/tei:title[@type='main']",
        ".//tei:analytic/tei:title[@type='main']",
        ".//tei:titleStmt/tei:title"
    ]

    for path in title_paths:
        title_elem = root.find(path, ns)
        if title_elem is not None:
            # Extract text, removing any nested elements
            title_text = ''.join(title_elem.itertext()).strip()
            # Clean up the title (remove extra whitespace)
            title_text = ' '.join(title_text.split())
            if title_text and title_text.lower() not in ['warwick.ac.uk/lib-publications']:
                return title_text

    return ""


def extract_authors(root: ET.Element, ns: Dict[str, str]) -> str:
    """
    Extract authors from TEI XML (only the primary paper authors, not references).

    Args:
        root: XML root element
        ns: Namespace dictionary

    Returns:
        String of author names separated by commas
    """
    authors = []
    seen_authors = set()  # Track unique authors to avoid duplicates

    # Find author elements in the analytic section (paper authors)
    author_elements = root.findall(".//tei:sourceDesc//tei:analytic/tei:author", ns)

    # If not found, try fileDesc/titleStmt
    if not author_elements:
        author_elements = root.findall(".//tei:fileDesc//tei:titleStmt/tei:author", ns)

    for author in author_elements:
        # Skip dummy authors
        dummy_note = author.find("tei:note[@type='dummy_author']", ns)
        if dummy_note is not None:
            continue

        person_name = author.find("tei:persName", ns)
        if person_name is not None:
            surname_elem = person_name.find("tei:surname", ns)
            forename_elem = person_name.find("tei:forename[@type='first']", ns)

            forename = ""
            surname = ""

            if surname_elem is not None:
                surname = ''.join(surname_elem.itertext()).strip()
                # Remove trailing commas or other punctuation
                surname = surname.rstrip('.,;')

            if forename_elem is not None:
                forename = ''.join(forename_elem.itertext()).strip()

            # Format author name
            if forename and surname:
                author_name = f"{forename} {surname}"
            elif surname:
                author_name = surname
            else:
                continue

            # Only add if we haven't seen this author before
            if author_name not in seen_authors:
                authors.append(author_name)
                seen_authors.add(author_name)

                # Limit to first 10 authors to avoid including reference authors
                if len(authors) >= 10:
                    break

    return ', '.join(authors)


def extract_abstract(root: ET.Element, ns: Dict[str, str]) -> str:
    """
    Extract abstract from TEI XML.

    Args:
        root: XML root element
        ns: Namespace dictionary

    Returns:
        Abstract text or empty string if not found
    """
    # Look for abstract in profileDesc
    abstract_paths = [
        ".//tei:profileDesc/tei:abstract",
        ".//tei:abstract"
    ]

    for path in abstract_paths:
        abstract_elem = root.find(path, ns)
        if abstract_elem is not None:
            # Extract all text from abstract
            abstract_text = ''.join(abstract_elem.itertext()).strip()
            # Clean up the abstract (remove extra whitespace)
            abstract_text = ' '.join(abstract_text.split())

            # Filter out non-abstract content
            skip_phrases = [
                'Copies of full items can be used for personal research',
                'Publisher\'s statement:',
                'Title page Title:',
                'warwick.ac.uk/lib-publications'
            ]

            # Check if this looks like actual abstract content
            is_actual_abstract = True
            for phrase in skip_phrases:
                if phrase.lower() in abstract_text[:200].lower():
                    is_actual_abstract = False
                    break

            if is_actual_abstract and len(abstract_text) > 50:
                return abstract_text

    # Try to find abstract in notes with specific type
    abstract_note = root.find(".//tei:note[@type='<abstract>']", ns)
    if abstract_note is not None:
        abstract_text = ''.join(abstract_note.itertext()).strip()
        abstract_text = ' '.join(abstract_text.split())
        if len(abstract_text) > 50:
            return abstract_text

    return ""


def extract_sections(root: ET.Element, ns: Dict[str, str]) -> Dict[str, str]:
    """
    Extract all academic sections from TEI XML body.

    Args:
        root: XML root element
        ns: Namespace dictionary

    Returns:
        Dictionary mapping section titles to their content
    """
    sections = {}

    # Find all div elements in the body
    body_element = root.find(".//tei:text/tei:body", ns)

    if body_element is None:
        return sections

    # Extract all divs (sections)
    div_elements = body_element.findall(".//tei:div", ns)

    for div in div_elements:
        # Get section heading
        head_elem = div.find("tei:head", ns)

        if head_elem is not None:
            section_title = ''.join(head_elem.itertext()).strip()
            section_title = ' '.join(section_title.split())

            # Get all paragraph text in this section
            paragraphs = []
            for p in div.findall(".//tei:p", ns):
                p_text = ''.join(p.itertext()).strip()
                p_text = ' '.join(p_text.split())
                if p_text:
                    paragraphs.append(p_text)

            section_content = '\n\n'.join(paragraphs)

            if section_title and section_content:
                sections[section_title] = section_content

    return sections


def extract_references(root: ET.Element, ns: Dict[str, str]) -> list:
    """
    Extract references/bibliography from TEI XML.

    Args:
        root: XML root element
        ns: Namespace dictionary

    Returns:
        List of reference strings
    """
    references = []

    # Find bibliography section
    bibl_elements = root.findall(".//tei:text/tei:back//tei:listBibl/tei:biblStruct", ns)

    for bibl in bibl_elements:
        # Extract reference text
        ref_text = ''.join(bibl.itertext()).strip()
        ref_text = ' '.join(ref_text.split())
        if ref_text:
            references.append(ref_text)

    return references


def extract_metadata_from_xml(xml_path: Path, include_full_content: bool = False) -> Dict[str, any]:
    """
    Extract title, authors, and abstract from GROBID TEI XML file.
    Optionally extract all sections and references.

    Args:
        xml_path: Path to the XML file
        include_full_content: If True, extract all sections and references

    Returns:
        Dictionary containing extracted metadata
    """
    # Parse XML
    tree = ET.parse(xml_path)
    root = tree.getroot()

    # Define namespace
    ns = {'tei': 'http://www.tei-c.org/ns/1.0'}

    # Extract basic metadata
    metadata = {
        'title': extract_title(root, ns),
        'authors': extract_authors(root, ns),
        'abstract': extract_abstract(root, ns),
        'source_file': str(xml_path.name)
    }

    # Optionally extract full content
    if include_full_content:
        metadata['sections'] = extract_sections(root, ns)
        metadata['references'] = extract_references(root, ns)

    return metadata


def process_xml_file(xml_path: Path, output_dir: Optional[Path] = None) -> Dict[str, any]:
    """
    Process a single XML file and optionally save the extracted metadata.

    Args:
        xml_path: Path to the XML file
        output_dir: Optional output directory for JSON metadata

    Returns:
        Dictionary containing extracted metadata
    """
    metadata = extract_metadata_from_xml(xml_path)

    # Save to JSON if output directory is specified
    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{xml_path.stem}_metadata.json"

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

        print(f"Metadata saved to: {output_path}")

    return metadata


def process_triad_xmls(triad_dir: Path, output_dir: Optional[Path] = None) -> Dict[str, Dict[str, any]]:
    """
    Process only the original XML file in a triad directory.

    Args:
        triad_dir: Path to the triad directory containing XML files
        output_dir: Optional output directory for metadata files

    Returns:
        Dictionary mapping XML filenames to their metadata
    """
    results = {}

    # Find only the original XML file (note: "orginal" is a typo in the filename)
    xml_files = list(triad_dir.glob("output_orginal_*.xml"))

    if not xml_files:
        print(f"No original XML file found in {triad_dir}")
        return results

    for xml_path in xml_files:
        print(f"\nProcessing: {xml_path.name}")
        metadata = process_xml_file(xml_path, output_dir)

        # Print summary
        print(f"  Title: {metadata['title'][:80]}..." if len(metadata['title']) > 80 else f"  Title: {metadata['title']}")
        print(f"  Authors: {metadata['authors']}")
        print(f"  Abstract length: {len(metadata['abstract'])} characters")

        results[xml_path.name] = metadata

    return results


if __name__ == "__main__":
    # Example usage
    from pathlib import Path

    # Process triad_1
    triad_1_dir = Path("/Users/haijingzhang/Research/debate-traid-agent/data/triad_samples/triad_1")
    output_dir = triad_1_dir / "metadata"

    print("Processing triad_1 original XML file...")
    results = process_triad_xmls(triad_1_dir, output_dir)

    print(f"\n\nProcessed {len(results)} XML file(s)")
