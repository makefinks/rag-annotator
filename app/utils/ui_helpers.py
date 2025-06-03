import logging
import re
from PySide6.QtWidgets import QLayout
from rapidfuzz import fuzz

logger = logging.getLogger(__name__)


def clear_layout(layout: QLayout | None) -> None:
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


def _check_overlap(start: int, end: int, marked_ranges: list[tuple[int, int]]) -> bool:
    """Check if a text range overlaps with any already marked ranges."""
    for marked_start, marked_end in marked_ranges:
        if not (end <= marked_start or start >= marked_end):
            return True
    return False


def _create_highlight_span(text: str, color: str) -> str:
    """Create a highlighted span element for the given text."""
    return f"<span style='background-color:{color};'>{text}</span>"


def _calculate_similarity(text1: str, text2: str) -> float:
    """Calculate similarity score between two text strings (0.0 to 1.0)."""
    return fuzz.ratio(text1, text2) / 100.0


def _apply_exact_highlighting(
    text: str, keyword: str, color: str, marked_ranges: list[tuple[int, int]]
) -> tuple[str, bool]:
    """Apply exact word-boundary matching for a keyword."""
    pattern = rf"(\b{re.escape(keyword)}\b)"
    exact_matches = list(re.finditer(pattern, text, flags=re.IGNORECASE))

    if not exact_matches:
        return text, False

    result = text
    for match in reversed(exact_matches):  # Process right-to-left to preserve offsets
        start, end = match.span()
        if _check_overlap(start, end, marked_ranges):
            continue

        matched_text = match.group(1)
        replacement = _create_highlight_span(matched_text, color)
        result = result[:start] + replacement + result[end:]
        marked_ranges.append((start, start + len(replacement)))

    return result, True


def _find_best_phrase_match(
    text: str,
    keyword_normalized: str,
    min_score: float,
    marked_ranges: list[tuple[int, int]],
) -> tuple[int, int] | None:
    """Find the best matching phrase using sliding window approach."""
    text_lower = text.lower()
    window_length = len(keyword_normalized)

    best_span = None
    best_score = -1.0

    for i in range(len(text_lower) - window_length + 1):
        start, end = i, i + window_length

        if _check_overlap(start, end, marked_ranges):
            continue

        window_text = text_lower[start:end]
        score = _calculate_similarity(keyword_normalized, window_text)

        if score >= min_score and score > best_score:
            best_score = score
            best_span = (start, end)

            if score == 1.0:  # Perfect match found
                break

    return best_span


def _apply_sentence_fuzzy_matching(
    text: str,
    keyword_normalized: str,
    color: str,
    min_score: float,
    marked_ranges: list[tuple[int, int]],
) -> tuple[str, bool]:
    """Apply fuzzy matching for sentence-length keywords."""
    sentence_pattern = r"[^.!?]+[.!?]?"

    for sentence_match in re.finditer(sentence_pattern, text):
        sentence = sentence_match.group(0)
        sentence_similarity = _calculate_similarity(
            keyword_normalized, sentence.lower()
        )

        if sentence_similarity >= min_score:
            start, end = sentence_match.span()

            if _check_overlap(start, end, marked_ranges):
                continue

            replacement = _create_highlight_span(sentence, color)
            result = text[:start] + replacement + text[end:]
            marked_ranges.append((start, start + len(replacement)))
            return result, True

    return text, False


def _apply_phrase_fuzzy_matching(
    text: str,
    keyword_normalized: str,
    color: str,
    min_score: float,
    marked_ranges: list[tuple[int, int]],
) -> tuple[str, bool]:
    """Apply fuzzy matching for short phrases using sliding window."""
    best_span = _find_best_phrase_match(
        text, keyword_normalized, min_score, marked_ranges
    )

    if best_span:
        start, end = best_span
        matched_text = text[start:end]
        replacement = _create_highlight_span(matched_text, color)
        result = text[:start] + replacement + text[end:]
        marked_ranges.append((start, start + len(replacement)))
        return result, True

    return text, False


def _apply_fuzzy_highlighting(
    text: str,
    keyword: str,
    color: str,
    min_score: float,
    marked_ranges: list[tuple[int, int]],
) -> tuple[str, bool]:
    """Apply fuzzy matching for a keyword (sentence or phrase mode)."""
    keyword_normalized = keyword.lower().strip()
    word_count = len(keyword_normalized.split())

    # Use sentence mode for longer keywords (6+ words)
    if word_count >= 6:
        return _apply_sentence_fuzzy_matching(
            text, keyword_normalized, color, min_score, marked_ranges
        )
    else:
        return _apply_phrase_fuzzy_matching(
            text, keyword_normalized, color, min_score, marked_ranges
        )


def highlight_keywords(
    text: str,
    keywords: list[str],
    color: str,
    *,
    min_score: float = 0.7,  # 0-1 Levenshtein similarity needed for a fuzzy match
    enable_fuzzy: bool = True,
) -> str:
    """
    Highlight exact or approximately-matching keywords/phrases/sentences.

    1. **Exact layer** – uses the original whole-word regex you wrote.
    2. **Fuzzy layer** – only runs if the exact layer found nothing for that
       keyword *and* `enable_fuzzy` is True.
         - Single words / short phrases -> sliding-window substring search
         - Longer sentences (≥ 6 words)  -> sentence-by-sentence similarity

    Parameters
    ----------
    text : str
        Full text you want to mark up.
    keywords : list[str]
        Words, phrases, or whole sentences you’d like to flag.
    color : str
        Any valid CSS colour – '#ff0', 'rgba(255,0,0,.25)', …
    min_score : float, default 0.85
        Minimum similarity (0-1) for the fuzzy layer to accept a match.
    enable_fuzzy : bool, default True
        Turn fuzzy matching on/off globally.
    """
    if not keywords:
        return text

    result = text
    marked_ranges: list[tuple[int, int]] = []

    for keyword in keywords:
        if not keyword:
            continue

        # Try exact matching first
        result, found_exact = _apply_exact_highlighting(
            result, keyword, color, marked_ranges
        )

        if found_exact:
            continue

        # Fall back to fuzzy matching if enabled
        if enable_fuzzy:
            result, _ = _apply_fuzzy_highlighting(
                result, keyword, color, min_score, marked_ranges
            )

    return result
