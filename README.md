# RAG Annotation Tooling for ground truth creation

The annotation tool can be used to create a ground truth for evaluating retrieval systems.

The tools allows selecting a set of texts that are relevant to a given Text / Description.
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

### Usage of the tool
```bash
python annotation_tool.py
```
Upon selecting the file in the prepared format the tool will load the data and display the GUI:

- **Top Panel**: The current index of the evaluation object / point, a title dropdown, and the description / text of the object.
- **Left Panel**: The list of texts that were fetched and are supposed to selected as relevant.
- **Right Panel**: A BM25 seach bar and result display, that allows you to search for a specific texts for all texts in the dataset. 
- **Bottom Panel**: Buttons for Navigation and saving the current state of the annotation.
