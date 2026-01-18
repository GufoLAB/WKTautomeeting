# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AuMeet_package is an automated meeting transcript processing system that converts raw meeting transcripts into structured summaries and reports. The system uses AI models to perform topic segmentation, summarization, and intelligent clustering of meeting content.

## Core Processing Pipeline

The meeting transcript processing follows this sequential workflow:

1. **Transcript Preprocessing** (`shorten_transcript.py`)
   - Removes timestamps and merges consecutive speech by same speaker
   - Input: Raw transcript with timestamps 
   - Output: Clean transcript file

2. **Topic Segmentation** (`1topic_spliterG3v2.py`)
   - Uses AI to identify topic boundaries and create segments
   - Generates markdown files for each topic segment
   - Creates `<filename>_topics/` directory with numbered segment files

3. **Summary Generation** (`2chunks_summary.py`)
   - Generates detailed summaries for each topic segment
   - Outputs CSV files and JSONL format for RAG applications

4. **Summary Refinement** (`3brief_summary_reindex.py`)  
   - Simplifies and reindexes summary data
   - Removes unnecessary CSV columns

5. **Topic Clustering** (`4Condense.py`)
   - Groups related summaries by topic using AI
   - Adds clustering information to processed data

6. **Report Generation** (`pipeline_meeting_report.py`)
   - Creates final markdown reports organized by topic clusters
   - Uses continuous writing approach to build comprehensive reports

## Key Configuration

All configuration is managed through `config.py`:

- **AI Backend**: Set via `BACK_END_MODEL` (openai/ollama)
- **Model Selection**: Configure via `AI_MODEL` environment variable  
- **API Keys**: Set `OPENAI_API_KEY` if using OpenAI models
- **Ollama URL**: Configure via `OLLAMA_URL` for local models

Required environment variables should be set in `.env` file:
```
BACK_END_MODEL=openai
AI_MODEL=gpt-4o
OPENAI_API_KEY=your-key-here
OLLAMA_URL=http://127.0.0.1:11434
```

## Running the Pipeline

### Full Integrated Pipeline (Recommended)
```bash
# Complete automated pipeline from transcript to cleaned reports
python integrated_main.py /path/to/shorten.txt

# Test with existing data (steps 4-6 only)
python integrated_main.py --test
```

### Legacy Individual Steps
```bash
# Step 0: Clean transcript (manual preprocessing)
python shorten_transcript.py input.txt > clean.txt

# Step 1: Topic segmentation  
python 1topic_spliterG3v2.py clean.txt

# Step 2: Generate summaries
python 2chunks_summary.py /path/to/topics/directory

# Step 3: Refine summaries
python 3brief_summary_reindex.py summaries.csv

# Step 4: Cluster topics
python 4Condense.py refined_summaries.csv

# Step 5: Generate reports
python pipeline_meeting_report.py --csv clustered_data.csv --output reports/

# Step 6: Clean reports
python clean_md.py report.md -o report_cleaned.md
```

### Enhanced Processing (Experimental)
```bash
# Demonstration of patent-worthy techniques
python enhanced_pipeline.py [input_file]
```

## Input/Output Formats

- **Input**: Text transcripts with speaker labels in format `[Speaker] content`
- **Intermediate**: CSV files with columns like `chunk_id`, `summary`, `cluster_name`  
- **Output**: Markdown reports organized by topic clusters

## File Structure Patterns

The system creates organized directory structures:
```
input_file.txt
└── input_file_topics/          # Topic segments
    ├── 01_topic_name.md
    ├── 02_topic_name.md
    └── chunks_summaries_brief.csv
```

## Development Notes

- Most scripts expect specific input formats and directory structures
- Many file paths are hardcoded and may need adjustment for different environments
- The system is optimized for Chinese language processing (uses zhconv_rs for traditional Chinese conversion)
- AI responses are cached and processed to remove model-specific formatting artifacts

## Alternative Processing Methods

- `Alg_topic_split.py`: Mathematical topic segmentation (faster alternative to AI-based segmentation)
- `crystal_G3.py`: Experimental crystallization-based summarization
- Various experimental files in `openai_only_version_oldfile/` directory

## RAG and Vector Processing

The system generates JSONL files suitable for Retrieval-Augmented Generation:
- Contains original text chunks paired with summaries
- Suitable for building vector databases for semantic search
- See `樹狀LM開發計畫.txt` for NotebookLM-style architecture plans