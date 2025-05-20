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
    already_marked: list[tuple[int, int]] = []  # (start, end) ranges after each insert

    def _overlaps(start: int, end: int) -> bool:
        """Simple interval overlap check."""
        for s, e in already_marked:
            if not (end <= s or start >= e):
                return True
        return False

    for kw in keywords:
        if not kw:
            continue

        # 1) exact, whole-word match
        pattern = rf"(\b{re.escape(kw)}\b)"
        exact_hits = list(re.finditer(pattern, result, flags=re.IGNORECASE))

        if exact_hits:
            for m in reversed(exact_hits):  # right-to-left so offsets stay valid
                s, e = m.span()
                if _overlaps(s, e):
                    continue
                fragment = m.group(1)
                replacement = (
                    f"<span style='background-color:{color};'>{fragment}</span>"
                )
                result = result[:s] + replacement + result[e:]
                already_marked.append((s, s + len(replacement)))
            continue  # next keyword ✅

        # 2) fuzzy match
        if not enable_fuzzy:
            continue

        _similarity = lambda a, b: fuzz.ratio(a, b) / 100.0
        kw_norm = kw.lower().strip()
        # Heuristic: ≥ 6 words treat it as a sentence, else treat it as a short phrase
        if len(kw_norm.split()) >= 6:
            # --- sentence mode ---
            for sent_match in re.finditer(r"[^.!?]+[.!?]?", result):
                sent = sent_match.group(0)
                if _similarity(kw_norm, sent.lower()) >= min_score:
                    s, e = sent_match.span()
                    if _overlaps(s, e):
                        continue
                    replacement = (
                        f"<span style='background-color:{color};'>{sent}</span>"
                    )
                    result = result[:s] + replacement + result[e:]
                    already_marked.append((s, s + len(replacement)))
                    break
        else:
            # --- short-phrase mode (character sliding window of same length) ---
            text_lower = result.lower()
            win_len = len(kw_norm)

            best_span = None  # (start, end) of the best window
            best_score = -1.0  # highest similarity seen so far

            for i in range(0, len(text_lower) - win_len + 1):
                s, e = i, i + win_len
                if _overlaps(s, e):
                    continue

                score = _similarity(kw_norm, text_lower[s:e])

                # keep the highest-scoring window that clears the threshold
                if score >= min_score and score > best_score:
                    best_score = score
                    best_span = (s, e)

                    # perfect match, break
                    if score == 1.0:
                        break

            if best_span:
                s, e = best_span
                replacement = (
                    f"<span style='background-color:{color};'>{result[s:e]}</span>"
                )
                result = result[:s] + replacement + result[e:]
                already_marked.append((s, s + len(replacement)))

    return result
