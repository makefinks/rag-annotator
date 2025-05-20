import logging
import markdown
from bs4 import BeautifulSoup
import re

# Set up basic logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def fix_markdown_table(text: str) -> str:
    """
    Preprocesses a block of Markdown text to repair tables that contain
    multi-line cells or rows broken over several lines.

    The function attempts to:
      - Detect table rows that span multiple lines (e.g., a table cell's contents
        continues on lines that do not start with a '|').
      - Join such lines together so that each table row appears as a single line,
        enabling standard Markdown parsers to interpret the table correctly.
      - Preserve all blank lines and non-table text outside tables, so that paragraphs,
        lists, and multiple tables remain correctly separated in the output.

    Args:
        text (str): Markdown source text that may contain tables with line breaks.

    Returns:
        str: Markdown text with tables rewritten so that each table row is on one line,
             and all non-table content and blank lines preserved.
    """

    def process_row(row: str) -> str:
        parts = [
            cell.strip()  # trim
            for cell in re.split(r"(?<!\\)\|", row)  # ignore \| escapes
            if cell.strip() != ""
        ]
        return "| " + " | ".join(parts) + " |"

    lines = text.replace("\r\n", "\n").splitlines()
    result = []
    current_row = None

    for line in lines:
        if "|" in line:
            stripped = line.rstrip()
            if current_row is None:
                current_row = stripped
            else:
                # If the buffered row is already closed (ends with '|'),
                # push it and start a new one. Otherwise, we’re still
                # collecting a multi-line cell.
                if current_row.rstrip().endswith("|"):
                    result.append(process_row(current_row))
                    current_row = stripped
                else:
                    current_row += " " + stripped
        else:
            if current_row is not None:
                if current_row.rstrip().endswith("|"):
                    # Row complete -> flush before handling this line
                    result.append(process_row(current_row))
                    current_row = None
                    result.append(line)
                else:
                    # Continuation of an open cell – unless its blank
                    if line.strip():
                        current_row += " " + line.strip()
                    else:
                        result.append(process_row(current_row))
                        current_row = None
                        result.append(line)
            else:
                result.append(line)

    if current_row is not None:
        result.append(process_row(current_row))

    return "\n".join(result)


def format_md_text_to_html(text: str) -> str:
    """
    Formats the given text to HTML using markdown.
    It also attempts to fix markdown tables that are not properly formatted.
    Applies !important styling to table elements for visible borders.
    """
    fixed_text = fix_markdown_table(text)
    html = markdown.markdown(fixed_text, extensions=["tables", "fenced_code"])
    soup = BeautifulSoup(html, "html.parser")

    # Apply styles to table, th, and td
    for table in soup.find_all("table"):
        table["style"] = (
            "border-collapse: collapse !important; border: 1px solid black !important;"
        )

    for th in soup.find_all("th"):
        th["style"] = "border: 1px solid black !important; padding: 4px !important;"

    for td in soup.find_all("td"):
        td["style"] = "border: 1px solid black !important; padding: 4px !important;"

    return str(soup)
