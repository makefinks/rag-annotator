import logging
import markdown
from bs4 import BeautifulSoup

# Set up basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def fix_markdown_table(text: str):
    """
    Fixes markdown tables with cells spanning multiple lines while preserving
    any non-table text before, between, or after the table.
    
    Logic:
      - A line containing a pipe ('|') starts (or continues) a table row.
      - If a line does not contain a pipe but directly follows a table row (i.e.,
        we have buffered a row) and is not blank, we assume it's a continuation.
      - If a blank line is encountered while a table row is in progress,
        flush the current row, then output the blank line.
      - Non-table lines (when not buffering a table row) are output as-is.
      
    This heuristic assumes that table rows are contiguous and that any non‐empty,
    non‑pipe line following a table row is indeed part of that row.
    """
    text = text.replace('\r\n', '\n') 
    text = text.replace('\n\n', '\n') 

    def process_row(row):
        # Split on '|' and remove extraneous spaces & empty parts.
        parts = [cell.strip() for cell in row.split('|') if cell.strip() != '']
        return "| " + " | ".join(parts) + " |"
    
    lines = text.splitlines()
    result_lines = []
    current_row = None

    for line in lines:
        if '|' in line:
            # Found a table line.
            stripped = line.strip()
            if current_row is None:
                # Starting a new row.
                current_row = stripped
            else:
                # If the buffer already ends with a pipe, we consider that row complete.
                # Otherwise, assume the line is a continuation of the current row.
                if current_row.rstrip().endswith('|'):
                    result_lines.append(process_row(current_row))
                    current_row = stripped
                else:
                    current_row += " " + stripped
        else:
            # No pipe in this line.
            if current_row is not None:
                # If the line isn't blank, consider it a continuation of the table row.
                if line.strip():
                    current_row += " " + line.strip()
                else:
                    # A blank line implies the table row ended.
                    result_lines.append(process_row(current_row))
                    current_row = None
                    result_lines.append(line)
            else:
                result_lines.append(line)
    
    if current_row is not None:
        result_lines.append(process_row(current_row))
    
    return "\n".join(result_lines)


def format_md_text_to_html(text: str) -> str:
    """
    Formats the given text to HTML using markdown.
    It also attempts to fix markdown tables that are not properly formatted.
    Applies !important styling to table elements for visible borders.
    """
    fixed_text = fix_markdown_table(text)
    html = markdown.markdown(fixed_text, extensions=['tables', 'fenced_code'])
    soup = BeautifulSoup(html, 'html.parser')

    # Apply styles to table, th, and td
    for table in soup.find_all('table'):
        table['style'] = 'border-collapse: collapse !important; border: 1px solid black !important;'

    for th in soup.find_all('th'):
        th['style'] = 'border: 1px solid black !important; padding: 4px !important;'

    for td in soup.find_all('td'):
        td['style'] = 'border: 1px solid black !important; padding: 4px !important;'

    return str(soup)
    
