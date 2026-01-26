"""
Process extracted texts from triad_1 using OpenAI to extract structured information.
Extracts title, authors, and main body from critique and response documents.
"""
from openai import OpenAI
from pathlib import Path
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def load_extracted_text(json_path: Path) -> str:
    """
    Load extracted text from a JSON file.

    Args:
        json_path: Path to the JSON file containing extracted text

    Returns:
        The text content
    """
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        return data.get('text', '')


def process_with_openai(text: str, source_file: str, api_key: str, max_retries: int = 3) -> dict:
    """
    Use OpenAI to extract structured information from text.

    Args:
        text: The text to process
        source_file: Name of the source file
        api_key: OpenAI API key
        max_retries: Maximum number of retry attempts for API calls

    Returns:
        Dictionary containing extracted structure
    """
    client = OpenAI(api_key=api_key)

    prompt = """
The text below may contain multiple short scientific letters or replies merged together.
For each distinct article, extract:
- title
- authors (as a comma-separated string)
- main body text (KEEP ALL IN-TEXT CITATIONS INTACT, e.g., (Author, Year) or [1])
- references (list of reference strings from the bibliography/reference section)

**CRITICAL REQUIREMENT - REFERENCES ARE MANDATORY:**
- Each article MUST include a "references" field
- The "references" field must contain a list (array) of all reference strings found in the bibliography/reference section of that article
- Even if the article has no references, include an empty list: "references": []
- References are typically found at the end of each article in sections labeled "References", "Bibliography", "Works Cited", etc.
- Extract the complete reference string for each citation (e.g., "Smith, J. (2020). Title of paper. Journal Name, 15(3), 123-145.")
- DO NOT skip or omit the references field - it is essential for downstream processing

Return JSON array with one object per article.

Format:
{
    "articles": [
        {
            "title": "extracted title",
            "authors": "author1, author2, author3",
            "body": "main body text with citations preserved",
            "references": ["reference 1", "reference 2", ...]
        }
    ]
}

IMPORTANT:
- Keep all in-text citations in the body text exactly as they appear
- Extract all references from the bibliography/reference section as a separate list
- If there is only one article, return an array with one object
- Make sure the JSON is valid and properly formatted
- Every article object MUST have a "references" field!
- Ensure all string values are properly escaped (quotes, newlines, backslashes)

Text:
""" + text

    print(f"  Calling OpenAI API (gpt-4o-mini)...")

    # Retry loop to handle transient errors and malformed JSON
    result_text = None
    for attempt in range(max_retries):
        try:
            # On first attempt, use normal prompt
            # On retry after truncation, use concise mode
            current_prompt = prompt
            current_max_tokens = 16000

            if attempt > 0 and hasattr(process_with_openai, '_last_truncated'):
                # Retry with instructions to be more concise
                current_prompt = """
The text below may contain multiple short scientific letters or replies merged together.
For each distinct article, extract:
- title
- authors (as a comma-separated string)
- main body text (KEEP IN-TEXT CITATIONS, but SUMMARIZE to fit within token limits)
- references (list of reference strings from the bibliography/reference section)

**CRITICAL - DUE TO LENGTH CONSTRAINTS:**
- Every article MUST have a "references" field (array of reference strings)
- SUMMARIZE the body text while keeping essential citations
- Prioritize completeness over detail - include ALL articles even if body is brief
- Extract complete reference list for each article

Return JSON:
{
    "articles": [
        {
            "title": "...",
            "authors": "...",
            "body": "... (summarized with key citations)",
            "references": ["ref1", "ref2", ...]
        }
    ]
}

Text:
""" + text
                current_max_tokens = 32000  # Try with higher limit
                print(f"  Retrying with concise mode and higher token limit...")

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that extracts structured information from scientific text. Always preserve in-text citations exactly as they appear. IMPORTANT: Every article must include a 'references' field with all bibliography entries - this is mandatory. Ensure all JSON strings are properly escaped."},
                    {"role": "user", "content": current_prompt}
                ],
                temperature=0,
                response_format={"type": "json_object"},
                max_tokens=current_max_tokens
            )

            result_text = response.choices[0].message.content

            # Check if response was truncated
            if response.choices[0].finish_reason == 'length':
                print(f"  ⚠ Warning: Response truncated (hit token limit at {current_max_tokens} tokens)")

                # Mark for retry with concise mode
                if attempt < max_retries - 1:
                    process_with_openai._last_truncated = True
                    print(f"  Will retry with summarization strategy...")
                    continue  # Retry with concise prompt
                else:
                    print(f"  ⚠ Proceeding with truncated response (may be incomplete)")
            else:
                # Clear truncation flag on success
                if hasattr(process_with_openai, '_last_truncated'):
                    delattr(process_with_openai, '_last_truncated')

            break  # Success, exit retry loop

        except Exception as e:
            error_msg = str(e)
            print(f"  ⚠ API call attempt {attempt + 1}/{max_retries} failed: {e}")

            if attempt < max_retries - 1:
                import time
                import re

                # Check if it's a rate limit error
                if 'rate limit' in error_msg.lower():
                    # Try to extract wait time from error message
                    # Pattern: "Please try again in 46ms" or "Please try again in 2.5s"
                    wait_match = re.search(r'try again in (\d+(?:\.\d+)?)(ms|s)', error_msg)

                    if wait_match:
                        wait_value = float(wait_match.group(1))
                        wait_unit = wait_match.group(2)

                        # Convert to seconds
                        if wait_unit == 'ms':
                            wait_time = wait_value / 1000.0
                        else:
                            wait_time = wait_value

                        # Add small buffer
                        wait_time += 0.5
                        print(f"  Rate limit hit - waiting {wait_time:.2f} seconds as suggested...")
                    else:
                        # Default wait for rate limits
                        wait_time = 5
                        print(f"  Rate limit hit - waiting {wait_time} seconds...")
                else:
                    # Standard exponential backoff for other errors
                    wait_time = 2 ** attempt  # 1s, 2s, 4s
                    print(f"  Retrying in {wait_time} seconds...")

                time.sleep(wait_time)
            else:
                raise  # Re-raise if all retries exhausted

    # Parse the JSON response
    try:
        result = json.loads(result_text)
    except json.JSONDecodeError as e:
        print(f"  Warning: Failed to parse JSON response: {e}")
        print(f"  Error details: {e.msg} at position {e.pos}")

        # Try to salvage partial JSON by fixing common issues
        try:
            # Attempt 1: Fix unterminated strings by adding closing quotes/braces
            fixed_text = result_text
            if not fixed_text.rstrip().endswith('}'):
                # Try to close incomplete JSON
                fixed_text = result_text.rstrip().rstrip(',') + ']}}'
            result = json.loads(fixed_text)
            print(f"  ✓ Successfully recovered JSON by adding missing closing braces")
        except:
            # Attempt 2: Use regex to extract whatever valid JSON we can
            import re
            try:
                # Try to find the articles array even if JSON is incomplete
                articles_match = re.search(r'"articles"\s*:\s*\[(.*)\]', result_text, re.DOTALL)
                if articles_match:
                    # Manually construct a minimal valid response
                    result = {
                        "articles": [],
                        "error": f"Partial parse after error: {str(e)}",
                        "raw_response": result_text[:1000]  # Truncate for debugging
                    }
                    print(f"  ⚠ Could not recover full JSON, returning empty articles")
                else:
                    result = {"articles": [], "error": str(e), "raw_response": result_text[:1000]}
            except:
                result = {"articles": [], "error": str(e), "raw_response": result_text[:1000]}

    # Add metadata
    result['source_file'] = source_file
    result['model'] = 'gpt-4o-mini'
    result['input_length'] = len(text)

    return result


def process_triad_texts(triad_dir: Path, api_key: str):
    """
    Process all extracted text files from triad_1 directory.

    Args:
        triad_dir: Path to the triad directory
        api_key: OpenAI API key
    """
    # Define paths
    extracted_texts_dir = triad_dir / "extracted_texts"
    output_dir = triad_dir / "openai_structured"

    # Check if extracted texts directory exists
    if not extracted_texts_dir.exists():
        print(f"Error: {extracted_texts_dir} does not exist")
        print("Please run extract_text_from_pdf.py first to extract text from PDFs")
        return

    # Find all text JSON files (critique and response)
    text_files = list(extracted_texts_dir.glob("*_text.json"))

    if not text_files:
        print(f"No text files found in {extracted_texts_dir}")
        return

    print(f"Found {len(text_files)} text file(s) to process\n")

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    results = {}

    for text_file in text_files:
        print(f"Processing: {text_file.name}")

        # Load extracted text
        text = load_extracted_text(text_file)
        print(f"  Text length: {len(text)} characters")

        # Process with OpenAI
        try:
            structured_data = process_with_openai(text, text_file.name, api_key)

            # Save structured data
            output_filename = text_file.stem.replace('_text', '_structured') + '.json'
            output_path = output_dir / output_filename

            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(structured_data, f, ensure_ascii=False, indent=2)

            print(f"  ✓ Saved to: {output_path}")

            # Print summary
            articles = structured_data.get('articles', [])
            print(f"  Found {len(articles)} article(s)")
            for i, article in enumerate(articles, 1):
                title = article.get('title', 'N/A')
                authors = article.get('authors', 'N/A')
                body_len = len(article.get('body', ''))
                print(f"    Article {i}:")
                print(f"      Title: {title[:70]}..." if len(title) > 70 else f"      Title: {title}")
                print(f"      Authors: {authors[:70]}..." if len(authors) > 70 else f"      Authors: {authors}")
                print(f"      Body length: {body_len} characters")

            results[text_file.name] = structured_data
            print()

        except Exception as e:
            print(f"  ✗ Error processing {text_file.name}: {e}\n")
            continue

    print("="*60)
    print(f"✓ Successfully processed {len(results)}/{len(text_files)} file(s)")
    print(f"✓ Output saved to: {output_dir}")
    print("="*60)

    return results


if __name__ == "__main__":
    # Get API key from environment variable
    api_key = os.environ.get("OPENAI_API_KEY")

    if not api_key:
        print("Error: OPENAI_API_KEY not set")
        print("\nTo set your API key:")
        print("1. Environment variable: export OPENAI_API_KEY='your-key-here'")
        print("2. Create .env file with: OPENAI_API_KEY=your-key-here")
        exit(1)

    # Define triad_1 directory
    triad_1_dir = Path("data/triad_samples/triad_1")

    if not triad_1_dir.exists():
        print(f"Error: {triad_1_dir} does not exist")
        exit(1)

    # Process texts
    print("="*60)
    print("Processing triad_1 extracted texts with OpenAI")
    print("="*60)
    print()

    process_triad_texts(triad_1_dir, api_key)
