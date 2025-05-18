# RAG Annotation Tool for Ground Truth Creation

The annotation tool can be used to create a ground truth for evaluating retrieval systems.

It allows for selecting a set of texts that are relevant to a given Text / Description.
## Installation
### Clone the repository

```bash
git clone https://github.com/makefinks/rag-annotator.git
cd rag-annotator
```

### Install requriements (uv is recommended)
```bash
uv sync
```

### Activate the virtual environment
```bash
source .venv/bin/activate
```


## How it works

### Input preperation
The usage of this tool requires a specific input format (JSON).
The detailed format can be seen in `utils/ground_truth_schema.json`.

#### Ground Truth Schema Explanation
The input JSON must contain the following main fields:

- **points**: An array of objects, each representing an evaluation point. Each point contains:
  - `id`: Integer identifier for the point.
  - `title`: Title string for the point.
  - `description`: Description or query string.
  - `keywords (optional)`: Array of keywords relevant to the points description. Highlighted inside retrieved texts.
  - `fetched_texts`: Array of text objects fetched for this point. Each has:
    - `id`: Integer identifier for the text.
    - `text`: The text content.
    - `source`: The source string.
    - `metadata` (optional): Additional metadata (e.g., description).
    - `highlights` (optional): Array of strings to highlight in the text.
  - `selected_texts`: Array of selected text objects (same structure as `fetched_texts`).
  - `evaluated`: Boolean indicating if the point has been evaluated.
- **all_texts**: An array of all possible text objects in the dataset, each with:
  - `id`: Integer identifier.
  - `text`: The text content.

Refer to `app/utils/ground_truth_schema.json` for the complete and up-to-date schema.

### Usage of the tool
```bash
python annotation_tool.py
```
Upon selecting the file in the prepared format the tool will load the data and display the GUI:

- **Top Panel**: The current index of the evaluation object / point, a title dropdown, and the description / text of the object.
- **Left Panel**: The list of texts that were fetched and are supposed to be selected as relevant.
- **Right Panel**: A BM25 seach bar and result display, that allows you to search for a specific texts for all texts in the dataset. 
- **Bottom Panel**: Buttons for Navigation and saving the current state of the annotation.
