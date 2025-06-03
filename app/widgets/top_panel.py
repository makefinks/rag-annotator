import logging
import re
from PySide6.QtWidgets import (
    QWidget,
    QGroupBox,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QComboBox,
    QStyle,
    QMessageBox,
    QTextBrowser,
)
from PySide6.QtCore import Qt, Signal

logger = logging.getLogger(__name__)


class TopPanel(QWidget):
    """Top panel containing point description, position, title, and ID."""

    # Signal emitted when the navigator dropdown selection changes
    navigator_changed = Signal(int)
    # Signal emitted when the remove button is clicked
    remove_point_clicked = Signal()
    # Signal emitted when temporary keywords change
    temp_keywords_changed = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.point_description_label = None
        self.position_label = None
        self.id_label = None
        self.title_navigator = None
        self.remove_point_button = None

        # Temporary keyword selection (not saved to ground truth)
        self.temp_selected_words = set()
        self.original_description_text = ""
        self.ground_truth_keywords = []

        self._init_ui()

    def _init_ui(self):
        """Initialize the UI components of the top panel."""
        # Create group boxes
        top_group_desc = QGroupBox("Description (Click words to highlight)")
        top_group_pos = QGroupBox("Position")
        top_group_title = QGroupBox("Title")
        top_group_id = QGroupBox("ID")

        # Layouts for each group box
        top_desc_layout = QVBoxLayout(top_group_desc)
        top_pos_layout = QVBoxLayout(top_group_pos)
        top_title_layout = QVBoxLayout(top_group_title)
        top_id_layout = QVBoxLayout(top_group_id)

        # Position label in Position group
        self.position_label = QLabel("")
        self.position_label.setStyleSheet(
            "color: #90CAF9; font-weight: bold; padding: 2px;"
        )
        top_pos_layout.addWidget(self.position_label)
        top_group_pos.setSizePolicy(
            QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred
        )

        # ID label in ID group
        self.id_label = QLabel("")
        self.id_label.setStyleSheet("color: #90CAF9; font-weight: bold; padding: 2px;")
        top_id_layout.addWidget(self.id_label)
        top_group_id.setSizePolicy(
            QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred
        )

        # Title Navigator (Dropdown)
        self.title_navigator = QComboBox()
        self.title_navigator.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self.title_navigator.setStyleSheet("combobox-popup: 0;")
        top_title_layout.addWidget(self.title_navigator)
        # Connect the signal
        self.title_navigator.currentIndexChanged.connect(self._on_navigator_changed)

        # Description browser with clickable words in Description group
        self.point_description_label = QTextBrowser()
        self.point_description_label.setHtml(
            "This is where the detailed point description will be displayed."
        )
        self.point_description_label.setOpenExternalLinks(False)
        self.point_description_label.anchorClicked.connect(self._on_word_clicked)

        self.point_description_label.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.point_description_label.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.point_description_label.setLineWrapMode(
            QTextBrowser.LineWrapMode.WidgetWidth
        )

        # Match QLabel styling exactly
        self.point_description_label.setStyleSheet("""
            QTextBrowser {
                padding: 5px;
                border: none;
                background-color: transparent;
                color: #E0E0E0;
                font-size: 10pt;
                max-height: 30;
                min-height: 0px;
            }
        """)

        top_desc_layout.addWidget(self.point_description_label)
        top_group_desc.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )

        # Create a horizontal layout for the group boxes
        top_panel_layout = QHBoxLayout(self)
        top_panel_layout.setContentsMargins(0, 0, 0, 0)
        top_panel_layout.addWidget(top_group_pos)
        top_panel_layout.addWidget(top_group_title)
        top_panel_layout.addWidget(top_group_id)
        top_panel_layout.addWidget(top_group_desc, stretch=1)

        # Add A button to remove points fully
        self.remove_point_button = QPushButton("Remove")
        self.remove_point_button.clicked.connect(self._on_remove_clicked)
        top_panel_layout.addWidget(self.remove_point_button)

        # Add icon and tooltip to remove button
        style = self.style()
        self.remove_point_button.setIcon(
            style.standardIcon(QStyle.StandardPixmap.SP_DialogCancelButton)
        )
        self.remove_point_button.setToolTip("Remove this point")

    def _create_clickable_html(self, text):
        """Convert text to HTML with clickable words."""
        if not text:
            return ""

        # Strip existing HTML tags and get plain text
        # Handle simple HTML like <i>, <b>, etc.
        import html

        if "<" in text and ">" in text:
            # Simple HTML stripping for now - preserve formatting intent
            clean_text = re.sub(r"<[^>]+>", "", text)
        else:
            clean_text = text

        # Split text into words while preserving punctuation and whitespace
        word_pattern = r"(\w+|[^\w\s]|\s+)"
        tokens = re.findall(word_pattern, clean_text)

        html_parts = [
            '<div style="color: #E0E0E0; font-size: 10pt;">'
        ]  # Match CSS exactly
        for token in tokens:
            if re.match(r"^\w+$", token):  # It's a word
                word_lower = token.lower()
                is_selected = word_lower in self.temp_selected_words

                if is_selected:
                    # Selected word - highlighted in yellow
                    html_parts.append(
                        f'<a href="word:{token}" style="background-color: rgba(255, 255, 0, 0.4); color: black; text-decoration: none; padding: 1px 2px; border-radius: 2px;">{token}</a>'
                    )
                else:
                    # Unselected word - use theme color, clickable
                    html_parts.append(
                        f'<a href="word:{token}" style="color: #E0E0E0; text-decoration: none; padding: 1px; border-radius: 2px;" onmouseover="this.style.backgroundColor=\'rgba(255, 255, 255, 0.1)\'" onmouseout="this.style.backgroundColor=\'transparent\'">{token}</a>'
                    )
            else:
                # Punctuation or whitespace - keep as is, escape HTML
                html_parts.append(html.escape(token))

        html_parts.append("</div>")
        return "".join(html_parts)

    def _on_word_clicked(self, url):
        """Handle clicking on a word in the description."""
        url_str = url.toString()
        if url_str.startswith("word:"):
            word = url_str[5:]  # Remove "word:" prefix
            word_lower = word.lower()

            # Toggle word selection
            if word_lower in self.temp_selected_words:
                self.temp_selected_words.remove(word_lower)
            else:
                self.temp_selected_words.add(word_lower)

            # Re-render the description with updated selection
            self._update_description_display()

            # Emit signal with current temporary keywords
            self.temp_keywords_changed.emit(list(self.temp_selected_words))

    def _update_description_display(self):
        """Update the description display with current word selections."""
        if self.original_description_text:
            clickable_html = self._create_clickable_html(self.original_description_text)
            self.point_description_label.setHtml(clickable_html)

    def _on_navigator_changed(self, index):
        """Handle navigator dropdown selection change."""
        self.navigator_changed.emit(index)

    def _on_remove_clicked(self):
        """Handle remove button click by confirming with the user."""
        reply = QMessageBox.question(
            self,
            "Remove Point",
            "Are you sure you want to remove this point? "
            "This action will remove the point from the source file and is not reversible.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self.remove_point_clicked.emit()

    def set_position_text(self, text):
        """Set the position label text."""
        self.position_label.setText(text)

    def set_id_text(self, text):
        """Set the ID label text."""
        self.id_label.setText(text)

    def set_description_text(self, text, keywords=None):
        """Set the description text with optional ground truth keywords."""
        # Store original text and keywords
        self.original_description_text = text
        self.ground_truth_keywords = keywords or []

        # Initialize temporary selection with ground truth keywords
        self.temp_selected_words = set(kw.lower() for kw in self.ground_truth_keywords)

        # Render clickable HTML
        self._update_description_display()

    def get_temp_selected_words(self):
        """Get the current temporary selected words."""
        return list(self.temp_selected_words)

    def reset_temp_selection(self):
        """Reset temporary selection to ground truth keywords."""
        self.temp_selected_words = set(kw.lower() for kw in self.ground_truth_keywords)
        self._update_description_display()

    def populate_navigator(self, items, current_index):
        """Populate the title navigator dropdown."""
        self.title_navigator.blockSignals(True)
        self.title_navigator.clear()
        for title, idx, is_evaluated in items:
            prefix = "✓ " if is_evaluated else ""
            self.title_navigator.addItem(f"{prefix}{title}", userData=idx)
        self.title_navigator.setCurrentIndex(current_index)
        self.title_navigator.blockSignals(False)
