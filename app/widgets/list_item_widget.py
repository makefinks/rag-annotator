from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
)
from PySide6.QtCore import Qt, Signal


class ListItemWidget(QFrame):
    button_clicked_signal = Signal(QFrame)
    item_clicked_signal = Signal(QFrame)

    # Color mapping for different text sources. Used for the source label background.
    SOURCE_COLORS = {
        "llm": "#AEC6CF",  # Pastel Blue
        "semantic": "#C1E1C1",  # Pale Green
        "bm25-appended": "#FFD8B1",  # Light Apricot
        "both": "#FF0000",  # Bright Red
        "default": "#E0E0E0",  # Default light gray
    }

    SOURCE_TEXT_COLORS = {
        "llm": "#000000",
        "semantic": "#000000",
        "bm25-appended": "#000000",
        "both": "#000000",
        "default": "#000000",
    }

    def __init__(self, item_id, text, source, button_text, metadata=None, parent=None):
        super().__init__(parent)
        self.item_id = item_id
        self.source = source
        self.original_text = text

        # Layout for the item (text label + button)
        item_layout = QHBoxLayout(self)
        item_layout.setContentsMargins(5, 5, 5, 5)
        item_layout.setSpacing(5)

        # Source Label (colored box)
        self.source_label = QLabel(source)
        source_bg_color = self.SOURCE_COLORS.get(source, self.SOURCE_COLORS["default"])
        source_text_color = self.SOURCE_TEXT_COLORS.get(
            source, self.SOURCE_TEXT_COLORS["default"]
        )
        self.source_label.setStyleSheet(
            f"background-color: {source_bg_color}; color: {source_text_color}; padding: 2px 4px; border-radius: 3px; font-size: 8pt;"
        )
        # Format metadata as a table for the tooltip
        if metadata:
            tooltip = (
                "<table border='1' cellpadding='3' style='border-collapse: collapse;'>"
            )
            tooltip += "<tr><th colspan='2'>Metadata</th></tr>"
            for key, value in metadata.items():
                tooltip += f"<tr><td><b>{key}</b></td><td>{value}</td></tr>"
            tooltip += "</table>"
            self.source_label.setToolTip(tooltip)
        else:
            self.source_label.setToolTip("No metadata available")

        # Vertically align
        self.source_label.setMinimumWidth(85)
        self.source_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.source_label.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed
        )

        # Label to display text
        self.label = QLabel(text)
        self.label.setTextFormat(Qt.TextFormat.RichText)
        self.label.setWordWrap(True)
        self.label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )

        # Button (Add or Remove)
        self.button = QPushButton(button_text)
        self.button.clicked.connect(self._emit_button_clicked)
        self.button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        item_layout.addWidget(self.source_label)
        item_layout.addWidget(self.label)
        item_layout.addWidget(self.button)

        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        # State tracking for styling
        self._selected = False
        self._update_style()

    def _emit_button_clicked(self):
        self.button_clicked_signal.emit(self)

    def _emit_item_clicked(self):
        self.item_clicked_signal.emit(self)

    # Override mousePressEvent to detect clicks on the frame
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._emit_item_clicked()
        super().mousePressEvent(event)

    def get_text(self):
        return self.original_text

    def get_formatted_text(self):
        return self.label.text()

    def set_text(self, text):
        self.label.setText(text)

    def set_enabled_state(self, enabled):
        """Enable/disable interaction with the widget."""
        self.button.setEnabled(enabled)
        self.setEnabled(enabled)
        if enabled:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)
        self._update_style()  # Update style when enabled state changes

    def set_selected(self, selected):
        """Set the selected state and update the style."""
        self._selected = selected
        self._update_style()

    def _update_style(self):
        """
        Applies dynamic styling based on the widget's selected and enabled state.
        Overrides parts of the base stylesheet applied in AnnotationApp._apply_stylesheet.
        """
        # Base style properties (applied regardless of state unless overridden below)
        base_style = (
            "border-radius: 3px; background-color: #383838; margin-bottom: 3px;"
        )
        border_style = "border: 1px solid #555555;"
        text_color = "color: #E0E0E0;"

        # State-specific overrides
        if not self.isEnabled():
            # Style for disabled state (dimmed)
            base_style = (
                "border-radius: 3px; background-color: #252525; margin-bottom: 3px;"
            )
            text_color = "color: #888888;"  # Grayed out text
            if self._selected:
                # Dimmer orange border for selected but disabled
                border_style = "border: 2px solid #805300;"  # Darker orange
            else:
                # Dimmer default border for non-selected disabled
                border_style = "border: 1px solid #444444;"
        elif self._selected:
            # Style for selected and enabled state (highlighted border)
            # Bright orange border for selected and enabled
            border_style = "border: 2px solid #FFA500;"

        # Apply the combined style to the widget itself using setStyleSheet.
        self.setStyleSheet(f"ListItemWidget {{ {base_style} {border_style} }}")
        self.label.setStyleSheet(text_color)
