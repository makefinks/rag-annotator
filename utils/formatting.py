import re
import logging
from typing import List, Tuple

# Set up basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def _parse_md_line(line: str) -> List[str]:
    """
    Parses a single line of a Markdown table, splitting it by '|' and stripping whitespace.
    Handles leading/trailing pipes.
    """
    if line.startswith('|'):
        line = line[1:]
    if line.endswith('|'):
        line = line[:-1]
    return [cell.strip() for cell in line.split('|')]


def _replace_table(match: re.Match) -> str:
    """
    Callback function for re.sub. Takes a matched Markdown table
    and returns its HTML representation with borders. Alignment is NOT processed.
    """
    md_table_block = match.group(1)
    lines = md_table_block.strip().split('\n')

    if len(lines) < 2:
        # Not a valid table (needs header and separator)
        logging.warning(f"Skipping potential table block, too few lines: {md_table_block}")
        return match.group(0) # Return original text if not valid

    header_line = lines[0]
    separator_line = lines[1]
    data_lines = lines[2:]

    # --- Basic validation of separator ---
    # Check if separator line looks plausible (contains hyphens and pipes if not just hyphens)
    # We still need the separator line structure for matching, even if we don't parse alignment.
    sep_check = separator_line.replace('|', '').replace(':', '').replace(' ', '')
    if not sep_check or not all(c == '-' for c in sep_check):
         logging.warning(f"Skipping potential table block, invalid separator line: {separator_line}")
         return match.group(0) # Return original text if separator is invalid

    # --- Parse Header ---
    header_cells = _parse_md_line(header_line)
    num_columns = len(header_cells)

    # --- Build HTML ---
    html_rows = []
    # Use !important to override any stylesheet rules
    html_rows.append('<table style="border: 1px solid #666666 !important; border-collapse: collapse !important; width: 100%; table-layout: fixed;">')

    # Header Row
    html_rows.append('  <thead>')
    html_rows.append('    <tr>')
    for cell in header_cells:
        # Use !important to ensure borders are visible
        html_rows.append(f'      <th style="border: 1px solid #666666 !important; text-align: left; padding: 4px !important;">{cell}</th>')
    html_rows.append('    </tr>')
    html_rows.append('  </thead>')

    # Data Rows
    html_rows.append('  <tbody>')
    for line in data_lines:
        if not line.strip(): # Skip empty lines that might be caught
            continue
        data_cells = _parse_md_line(line)
        html_rows.append('    <tr>')
        for i in range(num_columns): # Iterate based on header columns
            if i < len(data_cells):
                cell_content = data_cells[i]
                # Use !important to ensure borders are visible
                html_rows.append(f'      <td style="border: 1px solid #666666 !important; text-align: left; padding: 4px !important;">{cell_content}</td>')
            else:
                # Add empty cell if data row is shorter than header
                html_rows.append(f'      <td style="border: 1px solid #666666 !important; text-align: left; padding: 4px !important;"></td>')
        html_rows.append('    </tr>')
    html_rows.append('  </tbody>')

    html_rows.append('</table>')

    logging.info(f"Successfully converted MD table block to HTML (with borders, no alignment).")
    return '\n'.join(html_rows)


def format_md_table_to_html(text: str) -> str:
    """
    Attempts to match markdown tables within a larger text block
    and formats them into an HTML representation with borders, suitable for
    PySide6 widgets. Alignment markers (:) in the separator line are ignored.

    Preserves existing HTML tags (like <span>) within the text and table cells.

    Args:
        text: The input string potentially containing markdown tables and other text/HTML.

    Returns:
        A string with markdown tables converted to HTML tables with borders.
    """
    if not text:
        return ""

    # Regex Explanation: 
    # (                               # Group 1: Capture the whole table block
    #   (?:^[ ]*\|.*\|[ ]*\n)         # Header: Start anchor, optional spaces, |, anything, |, optional spaces, newline
    #   (?:^[ ]*\|[ :-]+[|][ :-]+    # Separator: Start anchor, optional spaces, |, mix of ' ', ':', '-', must have at least one internal |
    #       (?:[|][ :-]+)*           #   followed by zero or more pipe-separated segments
    #       \|[ ]*\n                 #   ending with a pipe, optional spaces, newline
    #   )
    #   (?:                           # Data Rows Block: Non-capturing group for all data rows
    #     (?:^[ ]*\|.*\|[ ]*\n?)+     #   Data Row Line(s): Start anchor, optional spaces, |, anything, |, optional spaces, optional newline. Must have at least one (+) data row.
    #   )
    # )
    # Flags: re.MULTILINE (to make ^ match start of lines), re.VERBOSE (for comments)
    table_pattern = re.compile(r"""
        (                             # Group 1: Capture the whole table block
          (?:^[ ]*\|.*\|[ ]*\n)         # Header line structure
          (?:^[ ]*\|[ :|-]+           # Separator line structure (needs pipes and hyphens/colons)
              (?:[|][ :|-]+)*         # Optional more segments
              \|[ ]*\n                 # Ending pipe and newline
          )
          (?:                           # Data Rows Block: Non-capturing group for all data rows
            (?:^[ ]*\|.*\|[ ]*\n?)+     #   Data Row Line(s): Must have at least one (+) data row.
          )
        )
    """, re.MULTILINE | re.VERBOSE)

    try:
        # Use re.sub with the callback function to replace matches
        formatted_text = table_pattern.sub(_replace_table, text)
        return formatted_text
    except Exception as e:
        logging.error(f"Error during Markdown table formatting: {e}", exc_info=True)
        # Return original text in case of unexpected errors during regex processing
        return text

# Example Usage:
if __name__ == "__main__":
    md_text_simple = """
This is some introductory text.

| Header 1 | Header 2 | Header 3 |
| :------- | :------: | -------: |
| Cell 1.1 | Cell 1.2 | Cell 1.3 |
| Cell 2.1 | Cell 2.2 | Cell 2.3 |

This is some text between tables.

| Feature         | Support | Notes                                    |
|-----------------|:-------:|------------------------------------------|
| Simple Table    |   Yes   | Basic functionality works.               |
| Alignment       |   No    | Alignment markers are ignored now.       |
| Existing HTML |   Yes   | <span>Highlight</span> should be preserved |
| Ragged Rows     | Partial | Extra cells ignored, missing cells empty |

This is text after the tables.
    """

    md_text_with_span = """
Here is text with a <span>highlighted</span> word.

| Column A | Column B (<span>Special</span>) |
|---|:---|
| Data 1 | <span>Value</span> 1 |
| Data 2 | Value <span>2</span> |

More text.
"""

    md_text_no_table = """
This text does not contain any tables.
Just regular paragraphs and maybe some *markdown*.
- List item 1
- List item 2
"""

    md_text_malformed = """
This might look like a table but isn't quite right.
| Header 1 | Header 2 |
|----------|----------|
Cell 1 | Cell 2   <- Missing pipes
| Cell 3 | Cell 4 |

Another attempt:
| Head A | Head B |
|--------|--------X <- Invalid separator char
| Data A | Data B |
"""

    print("--- Simple Table (No Alignment) ---")
    html_output_simple = format_md_table_to_html(md_text_simple)
    print(html_output_simple)
    print("\n" + "="*40 + "\n")

    print("--- Table with Existing Span (No Alignment) ---")
    html_output_span = format_md_table_to_html(md_text_with_span)
    print(html_output_span)
    print("\n" + "="*40 + "\n")

    print("--- No Table ---")
    html_output_no_table = format_md_table_to_html(md_text_no_table)
    print(html_output_no_table)
    print("\n" + "="*40 + "\n")

    print("--- Malformed Table ---")
    html_output_malformed = format_md_table_to_html(md_text_malformed)
    print(html_output_malformed)
    print("\n" + "="*40 + "\n")

    md_text_edge_cases = """
Table with extra spacing:
  | Header 1 | Header 2  |
  | :------- | :-------: |
  |   Val 1  |   Val 2   |

Table with no data rows (should not match ideally by regex):
| H1 | H2 |
|----|----|

Table with only header and separator (should not match):
| Head |
|------|

Table right at the start:
| Start | End |
|-------|-----|
|   A   |  B  |
Rest of text.

Table right at the end:
Previous text.
| Left | Right |
|------|-------|
|  C   |   D   |
"""
    print("--- Edge Cases (No Alignment) ---")
    html_output_edge = format_md_table_to_html(md_text_edge_cases)
    print(html_output_edge)
    print("\n" + "="*40 + "\n")
