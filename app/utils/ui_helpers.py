import logging
import re
from PySide6.QtWidgets import QLabel

logger = logging.getLogger(__name__)

def clear_layout(layout):
    """
    Removes all widgets and nested layouts from a given QLayout.
    Uses deleteLater() for safe widget removal during the event loop.
    """
    if layout is None:
        return
    # Iterate while the layout still has items
    while layout.count():
        child = layout.takeAt(0)
        if child.widget():
            child.widget().deleteLater()  # Safely delete the widget
        elif child.layout():
            # If a layout contains other layouts, clear them recursively
            clear_layout(child.layout())
            # The layout item (representing the nested layout) is removed by takeAt(0)

def highlight_keywords(text, keywords, color):
    """
    Highlights specified keywords within a given text string using the provided color.
    Uses regex with word boundaries to avoid partial matches and applies
    HTML span tags for visual styling.
    Handles potential regex errors gracefully.
    """
    highlighted_text = text
    if not keywords:
        return highlighted_text

    # Use word boundaries (\b) to match whole words only.
    # Escape keywords in case they contain regex special characters (e.g., '.', '*', '+').
    for keyword in keywords:
        # Skip empty keywords
        if not keyword:
            continue
        pattern = r"(\b" + re.escape(keyword) + r"\b)"
        # Highlight using a span with background color (RGBA)
        replacement = f"<span style='background-color:{color};'>\\1</span>"
        try:
            highlighted_text = re.sub(
                pattern, replacement, highlighted_text, flags=re.IGNORECASE
            )
        except re.error as e:
            logger.error(f"Regex error highlighting keyword '{keyword}': {e}")
    return highlighted_text
