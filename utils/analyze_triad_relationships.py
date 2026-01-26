"""
Analyze relationships between original paper, critiques, and responses using OpenAI.
Determines which critiques and responses are related to the original paper and each other.
"""
from openai import OpenAI
from pathlib import Path
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def load_json_file(file_path: Path) -> dict:
    """Load JSON file and return its contents."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def analyze_triad_relationships(original_metadata: dict, critique_data: dict, response_data: dict, api_key: str) -> dict:
    """
    Use OpenAI to analyze relationships between original paper, critique, and response.

    Args:
        original_metadata: Metadata from the original paper (title, authors, abstract)
        critique_data: Structured data from critique
        response_data: Structured data from response
        api_key: OpenAI API key

    Returns:
        Dictionary containing relationship analysis
    """
    client = OpenAI(api_key=api_key)

    # Prepare the input data - add index to each article
    critique_articles = critique_data.get('articles', [])
    response_articles = response_data.get('articles', [])

    # Add index field to each article for identification
    critiques_with_index = [
        {**article, "index": idx}
        for idx, article in enumerate(critique_articles)
    ]
    responses_with_index = [
        {**article, "index": idx}
        for idx, article in enumerate(response_articles)
    ]

    input_data = {
        "original_paper": {
            "title": original_metadata.get('title', ''),
            "authors": original_metadata.get('authors', ''),
            "abstract": original_metadata.get('abstract', '')
        },
        "critiques": critiques_with_index,
        "responses": responses_with_index
    }

    prompt = f"""You are an expert in analyzing academic correspondence and peer debates.

You will be given the following information:
1. Metadata and abstract of an **Original Paper**.
2. A list of **Critique objects** (each with title, authors, text, and an index).
3. A list of **Response objects** (each with title, authors, text, and an index).

Goal:
Find which Critique(s) and Response(s) are truly related to the Original paper and talk to each other.

Judge by:
- The Author of Response should be same with the original paper's Author. And it should talk to the Author of Critique.
- Content relevance to the Original paper
- Whether Response explicitly replies to Critique

Output JSON:
{{
  "related_critiques": [ {{ "title": "...", "authors": "...", "index": 0 }} ],
  "related_responses": [ {{ "title": "...", "authors": "...", "index": 0 }} ],
  "talk_to_each_other": true/false,
  "explanation": "brief explanation of the relationship",
  "flag": null or "no_related_paper_found" or "topic_mismatch"
}}

**IMPORTANT**: You MUST include the "index" field for each related critique and response.
This index corresponds to the position of the article in the input arrays.
Copy the exact index value from the input data for each article you identify as related.

If uncertain, be conservative and exclude weak matches.
If no clear link found, set an appropriate flag.

Here is the data:
{json.dumps(input_data, indent=2)}
"""

    print("  Calling OpenAI API for relationship analysis...")

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        response_format={"type": "json_object"}
    )

    result_text = response.choices[0].message.content

    # Parse the JSON response
    try:
        result = json.loads(result_text)
    except json.JSONDecodeError as e:
        print(f"  Warning: Failed to parse JSON response: {e}")
        result = {
            "error": str(e),
            "raw_response": result_text,
            "related_critiques": [],
            "related_responses": [],
            "talk_to_each_other": False,
            "flag": "parsing_error"
        }

    # Add metadata
    result['analysis_metadata'] = {
        'model': 'gpt-4o-mini',
        'original_title': original_metadata.get('title', ''),
        'num_critiques_analyzed': len(critique_articles),
        'num_responses_analyzed': len(response_articles)
    }

    return result


def process_triad_analysis(triad_dir: Path, api_key: str):
    """
    Analyze relationships in a triad (original, critique, response).

    Args:
        triad_dir: Path to the triad directory
        api_key: OpenAI API key
    """
    print("="*70)
    print("Analyzing Triad Relationships with OpenAI")
    print("="*70)
    print()

    # Define paths
    openai_structured_dir = triad_dir / "openai_structured"
    output_dir = triad_dir / "relationship_analysis"
    original_metadata_file = triad_dir / "original_info_from_xml.json"

    # Check if required files/directories exist
    if not original_metadata_file.exists():
        print(f"Error: {original_metadata_file} does not exist")
        print("Please ensure original_info_from_xml.json exists in the triad directory")
        return

    if not openai_structured_dir.exists():
        print(f"Error: {openai_structured_dir} does not exist")
        print("Please run process_triad_with_openai.py first")
        return

    # Load original metadata file
    print(f"Loading original metadata: {original_metadata_file.name}")
    original_metadata = load_json_file(original_metadata_file)
    print(f"  Title: {original_metadata.get('title', 'N/A')}")
    print(f"  Authors: {original_metadata.get('authors', 'N/A')}")
    print()

    # Find critique structured file
    critique_files = list(openai_structured_dir.glob("critique_*_structured.json"))
    if not critique_files:
        print(f"Warning: No critique structured file found in {openai_structured_dir}")
        critique_data = {"articles": []}
    else:
        critique_file = critique_files[0]
        print(f"Loading critique data: {critique_file.name}")
        critique_data = load_json_file(critique_file)
        print(f"  Found {len(critique_data.get('articles', []))} critique article(s)")
        print()

    # Find response structured file
    response_files = list(openai_structured_dir.glob("response_*_structured.json"))
    if not response_files:
        print(f"Warning: No response structured file found in {openai_structured_dir}")
        response_data = {"articles": []}
    else:
        response_file = response_files[0]
        print(f"Loading response data: {response_file.name}")
        response_data = load_json_file(response_file)
        print(f"  Found {len(response_data.get('articles', []))} response article(s)")
        print()

    # Perform analysis
    print("Starting relationship analysis...")
    try:
        analysis_result = analyze_triad_relationships(
            original_metadata,
            critique_data,
            response_data,
            api_key
        )

        # Create output directory
        output_dir.mkdir(parents=True, exist_ok=True)

        # Save analysis result
        output_path = output_dir / "triad_relationship_analysis.json"
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(analysis_result, f, ensure_ascii=False, indent=2)

        print(f"\n✓ Analysis saved to: {output_path}")
        print()

        # Print summary
        print("="*70)
        print("Analysis Summary")
        print("="*70)

        related_critiques = analysis_result.get('related_critiques', [])
        related_responses = analysis_result.get('related_responses', [])
        talk_to_each_other = analysis_result.get('talk_to_each_other', False)
        flag = analysis_result.get('flag')
        explanation = analysis_result.get('explanation', '')

        print(f"Related Critiques: {len(related_critiques)}")
        for critique in related_critiques:
            title = critique.get('title', 'N/A')
            score = critique.get('relevance_score', 0)
            print(f"  - {title[:60]}... (score: {score})")

        print(f"\nRelated Responses: {len(related_responses)}")
        for response in related_responses:
            title = response.get('title', 'N/A')
            score = response.get('relevance_score', 0)
            print(f"  - {title[:60]}... (score: {score})")

        print(f"\nTalk to Each Other: {talk_to_each_other}")
        print(f"Flag: {flag if flag else 'None'}")

        if explanation:
            print(f"\nExplanation:")
            print(f"  {explanation}")

        print("="*70)

        return analysis_result

    except Exception as e:
        print(f"✗ Error during analysis: {e}")
        return None


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

    # Process analysis
    process_triad_analysis(triad_1_dir, api_key)
