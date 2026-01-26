# Debate Triad Processor

Automated pipeline for processing academic paper triads (original paper, critique, and response) to analyze scientific debates.

## Overview

This project provides a complete workflow to process scientific paper debates consisting of three papers:
- **Original Paper**: The initial research publication
- **Critique**: A critical response or comment on the original paper
- **Response**: The original authors' reply to the critique

The pipeline extracts, structures, and analyzes these papers to determine if they form a genuine scientific debate and classifies the quality of the triad.

## Features

- **Automated PDF Processing**: Converts PDFs to structured data using GROBID and OpenAI
- **Metadata Extraction**: Extracts titles, authors, abstracts, and references
- **Relationship Analysis**: Determines if papers are truly debating each other
- **Quality Classification**: Labels triads as Perfect (P), Broken (B), or Invalid (IV)
- **Resume Capability**: Automatically skips already-processed triads
- **Robust Error Handling**: Handles API rate limits, token limits, and malformed responses
- **Batch Processing**: Process hundreds of triads efficiently

## Project Structure

```
debate-triad-processor/
├── process_batch_triads.py          # Main entry point
├── triad_processor_batch.py         # Core processing logic
├── batch_processing_helpers.py      # Helper functions
├── src/
│   └── pdf_extract/
│       ├── extractor.py             # PDF text extraction
│       └── xml_preprocessor.py      # XML metadata extraction
├── utils/
│   ├── extract_text_from_pdf.py     # PDF text extraction utility
│   ├── process_triad_with_openai.py # OpenAI structuring
│   └── analyze_triad_relationships.py # Relationship analysis
├── scripts/
│   ├── sample_random_triads.py      # Sample triads from dataset
│   ├── calculate_accuracy.py        # Calculate prediction accuracy
│   ├── generate_results_csv.py      # Generate results CSV
│   └── analyze_results.py           # Analyze processing results
├── .gitignore
└── README.md
```

## Prerequisites

### 1. GROBID Service

GROBID is required for converting PDFs to structured XML. Start it using Docker:

```bash
docker run -p 8070:8070 lfoppiano/grobid:0.8.0
```

Verify it's running:
```bash
curl http://localhost:8070/api/isalive
```

### 2. OpenAI API Key

Set your OpenAI API key as an environment variable:

```bash
export OPENAI_API_KEY='your-api-key-here'
```

Or create a `.env` file:
```
OPENAI_API_KEY=your-api-key-here
```

### 3. Python Dependencies

Install required packages:

```bash
pip install openai python-dotenv pdfminer.six requests
```

## Usage

### Quick Start

Process triads from a CSV file:

```bash
python process_batch_triads.py \
  --csv data/sample.csv \
  --output-dir data/triad_output \
  --pdfs-dir data/pdfs
```

### Processing Options

**Process subset of triads:**
```bash
# First 10 triads
python process_batch_triads.py --csv data/sample.csv --limit 10

# Triads 20-30
python process_batch_triads.py --csv data/sample.csv --start-from 20 --limit 10
```

**Process single triad:**
```bash
python process_batch_triads.py --csv data/sample.csv --triad-index 42
```

**Resume from specific step:**
```bash
# Re-generate only final outputs (step 6)
python process_batch_triads.py --csv data/sample.csv --start-from-step 6

# Start from relationship analysis (step 5)
python process_batch_triads.py --csv data/sample.csv --start-from-step 5
```

**Force regeneration:**
```bash
python process_batch_triads.py --csv data/sample.csv --force-regenerate
```

**Skip specific triads:**
```bash
python process_batch_triads.py --csv data/sample.csv --skip-indices "6925,6930,6935"
```

### Command-Line Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| `--csv` | Path to CSV file with triad information | `data/sample.csv` |
| `--output-dir` | Output directory for processed triads | `data/triad_samples_batch` |
| `--pdfs-dir` | Directory containing PDFs named by Work ID | Google Drive path |
| `--start-from` | Start from CSV row index (0-based) | `0` |
| `--limit` | Process only N triads | All |
| `--triad-index` | Process single triad by index | None |
| `--start-from-step` | Start from step N (1-6) | `1` |
| `--force-regenerate` | Regenerate even if already processed | `false` |
| `--skip-indices` | Comma-separated indices to skip | None |
| `--grobid-url` | GROBID service URL | `http://localhost:8070` |

## Processing Pipeline

### Step 1: Generate XML from PDF
- Converts original paper PDF to structured XML using GROBID
- **Input**: `raw_data/original_*.pdf`
- **Output**: `intermediate_results/output_orginal_*.xml`

### Step 2: Extract Metadata from XML
- Parses XML to extract title, authors, abstract, sections, references
- **Input**: XML from Step 1
- **Output**: `intermediate_results/original_info_from_xml.json`

### Step 3: Extract Text from PDFs
- Extracts raw text from critique and response PDFs
- **Input**: `raw_data/critique_*.pdf`, `raw_data/response_*.pdf`
- **Output**: `intermediate_results/extracted_texts/*_text.json`

### Step 4: Structure with OpenAI
- Uses GPT-4o to parse text and identify multiple articles
- Extracts title, authors, body text, references for each article
- **Input**: Extracted text from Step 3
- **Output**: `intermediate_results/openai_structured/*_structured.json`
- **Features**: Automatic retry, rate limit handling, JSON recovery

### Step 5: Analyze Relationships
- Determines which articles are truly related to the original paper
- Checks author overlap, content relevance, explicit replies
- **Input**: Metadata from Steps 2 & 4
- **Output**: `intermediate_results/relationship_analysis/triad_relationship_analysis.json`

### Step 6: Generate Final Outputs
- Creates final JSON files with quality labels
- **Outputs**:
  - `final_outputs/original_paper_final.json` - Complete original paper
  - `final_outputs/critique_final.json` - Related critiques only
  - `final_outputs/response_final.json` - Related responses only
  - `final_outputs/summary.json` - Metadata and quality classification

## Output Structure

Each processed triad creates this folder structure:

```
triad_{index}/
├── raw_data/                          # Input files
│   ├── original_W123.pdf
│   ├── critique_W456.pdf
│   ├── response_W789.pdf
│   └── metadata.json                  # CSV metadata
├── intermediate_results/              # Processing outputs
│   ├── output_orginal_*.xml
│   ├── original_info_from_xml.json
│   ├── extracted_texts/
│   │   ├── critique_*_text.json
│   │   └── response_*_text.json
│   ├── openai_structured/
│   │   ├── critique_*_structured.json
│   │   └── response_*_structured.json
│   └── relationship_analysis/
│       └── triad_relationship_analysis.json
└── final_outputs/                     # Final deliverables
    ├── original_paper_final.json
    ├── critique_final.json
    ├── response_final.json
    └── summary.json
```

## Quality Labels

Each triad is automatically classified:

| Label | Meaning | Criteria |
|-------|---------|----------|
| **P** (Perfect) | Clean debate | Papers debate each other AND all articles are related |
| **B** (Broken) | Extra articles | Papers debate but PDFs contain unrelated articles |
| **IV** (Invalid) | Not a debate | Original paper is broken OR papers don't debate |

## Utility Scripts

### Sample Random Triads
```bash
python scripts/sample_random_triads.py --input data/all_triads.csv --output data/sample.csv --n 100
```

### Calculate Accuracy
```bash
python scripts/calculate_accuracy.py --results-dir data/triad_output
```

### Generate Results CSV
```bash
python scripts/generate_results_csv.py --input-dir data/triad_output --output results.csv
```

### Analyze Results
```bash
python scripts/analyze_results.py --csv results.csv
```

## Error Handling

The pipeline includes robust error handling:

- **Rate Limits**: Automatically waits and retries when hitting OpenAI rate limits
- **Token Limits**: Falls back to summarization strategy for large papers
- **JSON Parsing Errors**: Attempts recovery with partial extraction
- **Missing PDFs**: Warns and skips, continues with other triads
- **GROBID Timeouts**: 5-minute timeout with clear error messages
