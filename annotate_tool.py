import sys
import json
import os
import re 
import logging
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog, # Added for file selection
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QLineEdit,
    QScrollArea,
    QGroupBox,
    QFrame,
    QSizePolicy,
    QMessageBox,
    QComboBox 
)

from PySide6.QtCore import Qt, Signal, Slot
from jsonschema import ValidationError
from utils.search.bm25_handler import get_or_build_index, extract_texts_from_ground_truth
from utils.validation import validate_ground_truth


# --- Logger Configuration ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


# --- Custom Widget for List Items ---
class ListItemWidget(QFrame):
    button_clicked_signal = Signal(QWidget)
    item_clicked_signal = Signal(QWidget)

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

    def __init__(self, item_id, text, source, button_text, parent=None):
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

        # Vertically align
        self.source_label.setMinimumWidth(85)
        self.source_label.setAlignment(Qt.AlignCenter)
        self.source_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        # Label to display text
        self.label = QLabel(text)
        self.label.setTextFormat(Qt.RichText)
        self.label.setWordWrap(True)
        self.label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        # Button (Add or Remove)
        self.button = QPushButton(button_text)
        self.button.clicked.connect(self._emit_button_clicked)
        self.button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        item_layout.addWidget(self.source_label)
        item_layout.addWidget(self.label)
        item_layout.addWidget(self.button)

        self.setFrameShape(QFrame.StyledPanel)
        self.setCursor(Qt.PointingHandCursor)

        # State tracking for styling
        self._selected = False
        self._update_style()  # Apply initial style

    def _emit_button_clicked(self):
        self.button_clicked_signal.emit(self)

    def _emit_item_clicked(self):
        self.item_clicked_signal.emit(self)

    # Override mousePressEvent to detect clicks on the frame
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
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
            self.setCursor(Qt.PointingHandCursor)
        else:
            self.setCursor(Qt.ArrowCursor)
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
            base_style = "border-radius: 3px; background-color: #252525; margin-bottom: 3px;"  # Darker background
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


# --- Main Application Window ---
class AnnotationApp(QWidget):
    # Highlight color used for keywords within text descriptions and fetched texts.
    HIGHLIGHT_COLOR = "rgba(255, 255, 0, 0.2)"

    def __init__(self, data_file_path, ground_truth_data): 
        super().__init__()
        self.data_file_path = data_file_path
        self.ground_truth_data = ground_truth_data 
        # Ensure points exists in ground_truth_data
        if "points" not in self.ground_truth_data:
            self.ground_truth_data["points"] = []
        self.current_point_index = None

        self.setWindowTitle(
            f"Annotation Tool - File: {os.path.basename(self.data_file_path)}"
        )
        self.setGeometry(100, 100, 1400, 900)

        # --- BM25 Setup ---
        # Generate a unique base name for the pickle file from the JSON filename
        pickle_base_name = os.path.splitext(os.path.basename(self.data_file_path))[0]
        pickle_path = f"bm25_index_{pickle_base_name}.pkl"
        logger.info(f"Using BM25 index file: {pickle_path}")
        self.bm25_index = get_or_build_index(self.ground_truth_data, pickle_path)

        # Create a map for quick text-to-ID lookup
        self.text_to_id_map = {
            item["text"]: item["id"]
            for item in self.ground_truth_data.get("all_texts", [])
        }
        self.bm25_texts = extract_texts_from_ground_truth(self.ground_truth_data)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setSpacing(10)

        # --- Top Panel (Point Description) ---
        self._create_top_panel()

        # --- Middle Panels (Lists) ---
        self.middle_layout = QHBoxLayout()
        self.middle_layout.setSpacing(10)
        self._create_left_panel()
        self._create_right_panel()
        self.main_layout.addLayout(self.middle_layout, 1)

        # --- Bottom Panel (Navigation) ---
        self._create_bottom_panel()

        # Apply Stylesheet
        self._apply_stylesheet()

        # --- Load Initial Point ---
        if self.ground_truth_data["points"]:
            # Find first non-evaluated point or default to first point
            self.current_point_index = next(
                (i for i, point in enumerate(self.ground_truth_data["points"]) if not point.get("evaluated", False)),
                0
            )
            self._load_point(self.current_point_index)
        else:
            logger.warning("No subobjects found in the data file.")
            # Ensure UI elements exist before trying to set text/stat
            if hasattr(self, 'point_description_label'):
                 self.point_description_label.setText("No subobjects loaded.")
            if hasattr(self, 'prev_button'):
                 self.prev_button.setEnabled(False)
            if hasattr(self, 'next_button'):
                 self.next_button.setEnabled(False)
            if hasattr(self, 'confirm_button'):
                 self.confirm_button.setEnabled(False)

    def _create_top_panel(self):
        # Create group boxes
        top_group_desc = QGroupBox("Description")
        top_group_pos = QGroupBox("Position")
        top_group_title = QGroupBox("Title")

        # Layouts for each group box
        top_desc_layout = QVBoxLayout(top_group_desc)
        top_pos_layout = QVBoxLayout(top_group_pos)
        top_title_layout = QVBoxLayout(top_group_title)

        # Position label in Position group
        self.position_label = QLabel("")
        self.position_label.setStyleSheet("color: #90CAF9; font-weight: bold; padding: 2px;")
        top_pos_layout.addWidget(self.position_label)
        top_group_pos.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Preferred)

        # Title Navigator (Dropdown)
        self.title_navigator = QComboBox()
        self.title_navigator.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed) 
        self.title_navigator.setStyleSheet("combobox-popup: 0;") 
        top_title_layout.addWidget(self.title_navigator)
        # Removed setSizePolicy for the group, let the combobox control expansion
        self.title_navigator.currentIndexChanged.connect(self._navigate_via_navigator)

        # Description label in Description group
        self.point_description_label = QLabel(
            "This is where the detailed point description will be displayed."
        )
        self.point_description_label.setWordWrap(True)
        self.point_description_label.setAlignment(Qt.AlignTop)
        self.point_description_label.setStyleSheet("padding: 5px;")

        top_desc_layout.addWidget(self.point_description_label)
        top_group_desc.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        # Create a horizontal layout for the group boxes
        top_panel_layout = QHBoxLayout()
        top_panel_layout.addWidget(top_group_pos)
        top_panel_layout.addWidget(top_group_title)
        top_panel_layout.addWidget(top_group_desc, stretch=1)

        # Add A button to remove points fully 
        self.remove_point_button = QPushButton("Remove")
        self.remove_point_button.clicked.connect(self._remove_point)
        top_panel_layout.addWidget(self.remove_point_button)

        # Add the horizontal layout to the main layout
        self.main_layout.addLayout(top_panel_layout)

        # Ensure the top panels don't stretch vertically
        self.main_layout.setStretchFactor(top_panel_layout, 0)

            
    def _remove_point(self):
        """Removes the current evaluation point from the ground truth without confirmation"""
        
        if self.current_point_index is None or not self.ground_truth_data["points"]:
            logger.error("No point selected to remove")
            return
            
        current_index = self.current_point_index

        logger.info(f"Removing point at index {current_index}")  
        logger.info(str(self.ground_truth_data["points"]))
        
        # Verify the index is valid before removing
        if current_index < 0 or current_index >= len(self.ground_truth_data["points"]):
            logger.error(f"Invalid point index {current_index}. Valid range: 0-{len(self.ground_truth_data['points'])-1}")
            return
            
        # Remove point from ground truth data
        try:
            del self.ground_truth_data["points"][current_index]
            logger.info(f"Successfully removed point at index {current_index}")
        except Exception as e:
            logger.error(f"Error removing point: {e}")
            return

        # Handle index adjustment after removal
        if len(self.ground_truth_data["points"]) == 0:
            # No more points left
            logger.info("All points removed")
            self.current_point_index = None
            self.point_description_label.setText("No points remaining.")
            self.prev_button.setEnabled(False)
            self.next_button.setEnabled(False)
            self.confirm_button.setEnabled(False)
            self.remove_point_button.setEnabled(False)
        else:
            # Adjust index if we removed the last point
            if current_index >= len(self.ground_truth_data["points"]):
                self.current_point_index = len(self.ground_truth_data["points"]) - 1
            else:
                self.current_point_index = current_index
                
            # Load the point at the adjusted index
            self._load_point(self.current_point_index)
            # we also need to repopulate the title navigator
            self._populate_combo_box(self.current_point_index)

        # update the ground truth
        self._save_ground_truth()

    def _create_left_panel(self):
        """Creates the left panel containing the scrollable list of fetched text items."""
        left_groupbox = QGroupBox("Fetched Texts (Click to Select, Button to Remove)")
        left_outer_layout = QVBoxLayout(left_groupbox)

        # Scroll Area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)

        # Container widget inside ScrollArea
        self.left_list_widget = QWidget()
        self.left_list_layout = QVBoxLayout(self.left_list_widget)
        self.left_list_layout.setAlignment(Qt.AlignTop)
        self.left_list_layout.setContentsMargins(0, 0, 0, 0)
        self.left_list_layout.setSpacing(5)  

        scroll_area.setWidget(self.left_list_widget)  
        left_outer_layout.addWidget(scroll_area)  
        # Allow the left panel to stretch horizontally within the middle layout.
        self.middle_layout.addWidget(left_groupbox, 1)

    def _create_right_panel(self):
        """Creates the right panel displaying the currently selected text items."""
        right_groupbox = QGroupBox("BM25 Search")
        right_outer_layout = QVBoxLayout(right_groupbox)

        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("search field")
        self.search_button = QPushButton("Search")

        # connect search button and enter on field to bm25 search
        self.search_button.clicked.connect(self.perform_bm25_search)
        self.search_input.returnPressed.connect(self.perform_bm25_search)

        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.search_button)
        right_outer_layout.addLayout(search_layout)

        # Scroll Area for results
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)

        # Container widget for results
        self.right_list_widget = QWidget()
        self.right_list_layout = QVBoxLayout(self.right_list_widget)
        self.right_list_layout.setAlignment(Qt.AlignTop)
        self.right_list_layout.setContentsMargins(0, 0, 0, 0)
        self.right_list_layout.setSpacing(5)

        scroll_area.setWidget(self.right_list_widget)
        right_outer_layout.addWidget(scroll_area)
        # Allow the right panel to stretch horizontally within the middle layout.
        self.middle_layout.addWidget(right_groupbox, 1)

    def _create_bottom_panel(self):
        """Creates the bottom panel containing navigation and confirmation buttons."""
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(10)

        self.prev_button = QPushButton("Previous")
        self.confirm_button = QPushButton("Confirm")
        self.next_button = QPushButton("Next")

        bottom_layout.addStretch()
        bottom_layout.addWidget(self.prev_button)
        bottom_layout.addWidget(self.confirm_button)
        bottom_layout.addWidget(self.next_button)
        bottom_layout.addStretch()

        self.main_layout.addLayout(bottom_layout)
        # Ensure the bottom panel doesn't stretch vertically.
        self.main_layout.setStretchFactor(bottom_layout, 0)

        # --- Connect Signals ---
        self.prev_button.clicked.connect(self.navigate_previous)
        self.confirm_button.clicked.connect(self.confirm_point)
        self.next_button.clicked.connect(self.navigate_next)

    def _apply_stylesheet(self):
        """Loads and applies the stylesheet from an external CSS file."""
        try:
            css_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dark_theme.css")
            # Check if the file exists
            if not os.path.exists(css_file_path):
                logger.error(f"Stylesheet file not found: {css_file_path}")
                return
                
            with open(css_file_path, "r") as f:
                stylesheet = f.read()
                
            # Apply the stylesheet 
            self.setStyleSheet(stylesheet)
            logger.info(f"Applied stylesheet from {css_file_path}")
            
        except Exception as e:
            logger.error(f"Error applying stylesheet: {e}")

    # --- Data Loading and Saving ---
    def _save_ground_truth(self):
        """Saves the current state of ground_truth_data back to the JSON file."""
        if self.ground_truth_data is None:
            logger.error("No data to save.")
            return
        try:
            with open(self.data_file_path, "w", encoding="utf-8") as f:
                json.dump(self.ground_truth_data, f, indent=4, ensure_ascii=False)
            logger.info(f"Data saved to {self.data_file_path}")
        except Exception as e:
            logger.error(f"Error writing file {self.data_file_path}: {e}")

    # --- UI Population ---
    def _load_point(self, point_index):
        """Populates the UI with data from the specified point index."""
        if not self.ground_truth_data["points"] or point_index < 0 or point_index >= len(self.ground_truth_data["points"]):
            logger.warning(f"Error: Point index {point_index} is out of range.")
            return

        self.current_point_index = point_index
        point_data = self.ground_truth_data["points"][point_index]

        # --- Clear existing UI elements ---
        self.clear_layout(self.left_list_layout)

        # --- Populate Top Panel ---
        self.position_label.setText(
            f"Point {point_index + 1} of {len(self.ground_truth_data['points'])}"
        )

        self._populate_combo_box(point_index)

        # --- Populate Description ---
        keywords = point_data.get("keywords", [])
        description = point_data.get("description", "No description provided.")
        highlighted_description = self._highlight_keywords(
            description, keywords
        )  
        self.point_description_label.setText(
            highlighted_description
        )  

        # --- Populate Left Panel (Fetched Texts) ---
        is_evaluated = point_data.get("evaluated", False)

        for item_data in point_data.get("fetched_texts", []):
            item_id = item_data.get("id")
            text = item_data.get("text", "")
            source = item_data.get("source", "unknown")

            if item_id is None:
                logger.warning("Found fetched_text item without an ID. Skipping.")
                continue

            # Highlight keywords
            highlighted_text = self._highlight_keywords(text, keywords)

            # Check if this item is selected
            is_selected = any(
                sel_item.get("id") == item_id
                for sel_item in point_data.get("selected_texts", [])
            )

            # Add item to the left panel
            item_widget = self.add_item_to_left_panel(
                item_id, highlighted_text, source
            )

            # Set initial selected state
            if item_widget:
                item_widget.set_selected(is_selected)

        # --- Update Button States ---
        self.prev_button.setEnabled(point_index > 0)
        self.next_button.setEnabled(point_index < len(self.points) - 1)
        # Confirm button is always enabled, but text changes
        self.confirm_button.setText("Unconfirm" if is_evaluated else "Confirm")

        # --- Disable/Enable Left Panel Items based on evaluation status ---
        self._set_left_panel_enabled(
            not is_evaluated
        )  # Pass True if NOT evaluated (i.e., enabled)

    def _populate_combo_box(self, point_index: int):
        # --- Populate Title Navigator ---
        # Block signals to prevent triggering navigation when we set the index inside the combo box
        self.title_navigator.blockSignals(True)
        self.title_navigator.clear()
        for idx, p_data in enumerate(self.ground_truth_data["points"]):
            title = p_data.get("title", f"Point {idx + 1}")
            is_eval = p_data.get("evaluated", False)
            prefix = "✓ " if is_eval else ""
            self.title_navigator.addItem(f"{prefix}{title}", userData=idx) 
            
        # Set the current item in the navigator without triggering the signal
        self.title_navigator.setCurrentIndex(point_index)
        self.title_navigator.blockSignals(False) 

    def _set_left_panel_enabled(self, enabled):
        """Enable or disable all ListItemWidgets in the left panel."""
        for i in range(self.left_list_layout.count()):
            widget = self.left_list_layout.itemAt(i).widget()
            if isinstance(widget, ListItemWidget):
                widget.set_enabled_state(enabled)

    def _highlight_keywords(self, text, keywords):
        """
        Highlights specified keywords within a given text string.
        Uses regex with word boundaries to avoid partial matches and applies
        HTML span tags with the defined HIGHLIGHT_COLOR for visual styling.
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
            replacement = (
                f"<span style='background-color:{self.HIGHLIGHT_COLOR};'>\\1</span>"
            )
            try:
                highlighted_text = re.sub(
                    pattern, replacement, highlighted_text, flags=re.IGNORECASE
                )
            except re.error as e:
                logger.error(f"Regex error highlighting keyword '{keyword}': {e}")
        return highlighted_text

    # --- Slots for UI Interaction ---
    @Slot()
    def navigate_previous(self):
        logger.info("Navigate Previous clicked")
        if self.current_point_index is None or not self.ground_truth_data["points"]:
            return

        if self.current_point_index > 0:
            # Save current state before navigating
            self._save_ground_truth()
            # Load previous
            self._load_point(self.current_point_index - 1)

    @Slot()
    def confirm_point(self):
        """Toggles the 'evaluated' state of the current point."""
        logger.info("Confirm/Unconfirm clicked")
        if self.current_point_index is None or not self.ground_truth_data["points"]:
            return

        point_data = self.ground_truth_data["points"][self.current_point_index]

        # Toggle the evaluated state / reverse if already evaluated
        current_state = point_data.get("evaluated", False)
        new_state = not current_state
        point_data["evaluated"] = new_state

        logger.info(
            f"Point at index {self.current_point_index} marked as evaluated: {new_state}"
        )

        # Update UI elements
        self.confirm_button.setText("Unconfirm" if new_state else "Confirm")
        self._set_left_panel_enabled(not new_state)  # Enable if new_state is False

        # Save the change
        self._save_ground_truth()

    @Slot()
    def navigate_next(self):
        logger.info("Navigate Next clicked")
        if self.current_point_index is None or not self.ground_truth_data["points"]:
            return

        if self.current_point_index < len(self.ground_truth_data["points"]) - 1:
            # Save current state before navigating
            self._save_ground_truth()
            # Load next
            self._load_point(self.current_point_index + 1)

    @Slot(int) # Slot receives the new index from the QComboBox signal
    def _navigate_via_navigator(self, combo_box_index):
        """Navigates to the point selected in the title navigator dropdown."""
        if combo_box_index == -1: # Should not happen unless list is empty
             return

        target_point_index = self.title_navigator.itemData(combo_box_index)

        # Check if it's a valid index and different from the current one
        if target_point_index is not None and target_point_index != self.current_point_index:
            logger.info(f"Navigating via title navigator to point index: {target_point_index}")
            # Save current state before navigating
            self._save_ground_truth()
            # Load the selected point
            self._load_point(target_point_index)

    @Slot()
    def perform_bm25_search(self):
        """
        Performs a BM25 search based on the input from the search bar and displays the results on the right panel
        """
        if self.current_point_index is None or not self.ground_truth_data["points"]:
            logger.warning("No current point selected.")
            return

        point_data = self.ground_truth_data["points"][self.current_point_index]

        # clear previous results
        self.clear_layout(self.right_list_layout)

        keywords = point_data.get("keywords", [])
        description = point_data.get("description", "")
        if not description:
            logger.warning("No description provided for the current point.")

        search_query = self.search_input.text()
        if not search_query:
            # use current description as the query if no search query is provided
            search_query = description

        logger.info(f"Performing BM25 search with query: {search_query}")

        # Perform the search using the BM25 index
        results = self.bm25_index.get_top_n(search_query, self.bm25_texts, n=10)

        logger.info(f"Found {len(results)} BM25 search results")

        # Display results in the right panel
        if not results:
            # Show a message when no results are found
            no_results_label = QLabel("No results found for this query.")
            no_results_label.setStyleSheet("padding: 10px; color: #888888;")
            self.right_list_layout.addWidget(no_results_label)
            return

        used_ids = [item["id"] for item in point_data.get("fetched_texts", []) if item.get("id") is not None]
        # Add each result to the right panel
        for i, result_text in enumerate(results):

            # get the id
            actual_id = self.text_to_id_map.get(result_text)

            # do not display bm25 search when already visible in left panel
            if actual_id in used_ids:
                continue

            # Highlight keywords in the result text
            highlighted_text = self._highlight_keywords(result_text, keywords)

            # create the widget for the result
            item_widget = ListItemWidget(
                actual_id, highlighted_text, "bm25-appended", "Add"
            )

            # Connect the button click to add this result to fetched_texts
            item_widget.button_clicked_signal.connect(self.add_bm25_result_to_fetched)
            self.right_list_layout.addWidget(item_widget)

        # if no widgets were added, search returned nothing
        if self.right_list_layout.count() == 0:
            no_results_label = QLabel("No results found for this query, or results already on left side.")
            no_results_label.setStyleSheet("padding: 10px; color: #888888;")
            self.right_list_layout.addWidget(no_results_label)

    @Slot(QWidget)  # Connected to ListItemWidget's item_clicked_signal
    def mark_text_as_selected(self, item_widget):
        """
        Handles clicking on a fetched text item in the left panel.
        If the item is not already selected, it adds it to the 'selected_texts'
        list in the data model and updates the UI.
        If the item is already selected, it removes it (deselects).
        Does nothing if the current point is marked as 'evaluated'.
        """
        if self.current_point_index is None or not self.ground_truth_data["points"]:
            return
        if not isinstance(item_widget, ListItemWidget):
            return

        point_data = self.ground_truth_data["points"][self.current_point_index]
        if point_data.get("evaluated", False):
            logger.warning("Cannot modify evaluated point.")
            return  # Don't allow changes if evaluated

        item_id_to_add = item_widget.item_id
        logger.info(f"Item clicked (potential select): ID {item_id_to_add}")

        # Find the original item data in fetched_texts
        original_item_data = None
        for item in point_data.get("fetched_texts", []):
            if item.get("id") == item_id_to_add:
                original_item_data = item
                break

        if not original_item_data:
            logger.error(
                f"Could not find fetched text with ID {item_id_to_add} in data."
            )
            return

        # Check if it's already selected
        selected_texts = point_data.setdefault("selected_texts", [])
        is_already_selected = any(
            sel_item.get("id") == item_id_to_add for sel_item in selected_texts
        )

        if not is_already_selected:
            # Add a copy to selected_texts 
            selected_texts.append(original_item_data.copy())
            item_widget.set_selected(True)  # Update visual state
            logger.info(f"Added item ID {item_id_to_add} to selected_texts.")
        else:
            # If already selected, clicking again should de-select it
            point_data["selected_texts"] = [
                item for item in selected_texts if item.get("id") != item_id_to_add
            ]
            item_widget.set_selected(False)  # Update visual state
            logger.info(f"Removed item ID {item_id_to_add} from selected_texts.")

    @Slot(
        QWidget
    )  # Connected to ListItemWidget's button_clicked_signal (Remove button)
    def remove_fetched_text(self, item_widget):
        """
        Handles clicking the 'Remove' button on a fetched text item in the left panel.
        Removes the item from the 'fetched_texts' list in the data model,
        removes its widget from the UI, and also removes it from 'selected_texts'
        if it was selected.
        Does nothing if the current point is marked as 'evaluated'.
        """
        if self.current_point_index is None or not self.ground_truth_data["points"]:
            return
        if not isinstance(item_widget, ListItemWidget):
            return

        point_data = self.ground_truth_data["points"][self.current_point_index]
        if point_data.get("evaluated", False):
            logger.warning("Cannot modify evaluated point.")
            return  # Don't allow changes if evaluated

        item_id_to_remove = item_widget.item_id
        logger.info(f"Remove button clicked for item ID: {item_id_to_remove}")

        # Find and remove the item from fetched_texts list
        fetched_texts = point_data.get("fetched_texts", [])
        initial_length = len(fetched_texts)
        point_data["fetched_texts"] = [
            item for item in fetched_texts if item.get("id") != item_id_to_remove
        ]

        if len(point_data["fetched_texts"]) < initial_length:
            logger.info(f"Removed item ID {item_id_to_remove} from fetched_texts.")
            # Remove the widget from the UI
            self.left_list_layout.removeWidget(item_widget)
            item_widget.deleteLater()

            # Also remove from selected_texts if it was there
            selected_texts = point_data.get("selected_texts", [])
            initial_selected_length = len(selected_texts)
            point_data["selected_texts"] = [
                item for item in selected_texts if item.get("id") != item_id_to_remove
            ]
            if len(point_data["selected_texts"]) < initial_selected_length:
                logger.info(
                    f"Also removed item ID {item_id_to_remove} from selected_texts."
                )
        else:
            logger.error(f"Could not find item ID {item_id_to_remove} to remove.")

    @Slot(QWidget)
    def add_bm25_result_to_fetched(self, item_widget):
        """
        Handles clicking the 'Add' button on a BM25 search result in the right panel.
        Adds the item to the 'fetched_texts' list in the data model and to the left panel UI.
        Does nothing if the current point is marked as 'evaluated'.
        """
        if self.current_point_index is None or not self.ground_truth_data["points"]:
            return
        if not isinstance(item_widget, ListItemWidget):
            return

        point_data = self.ground_truth_data["points"][self.current_point_index]
        if point_data.get("evaluated", False):
            logger.warning("Cannot modify evaluated point.")
            return  # Don't allow changes if evaluated

        # Check if the item is already in fetched_texts
        fetched_texts = point_data.get("fetched_texts", [])
        if any(item.get("id") == item_widget.item_id for item in fetched_texts):
            logger.warning(f"Item ID {item_widget.item_id} already in fetched_texts.")
            return

        # Get the text and item id from the widget
        result_text = item_widget.get_text()
        result_id = item_widget.item_id

        # Create a new item for fetched_texts
        new_item = {
            "id": result_id,
            "text": result_text,
            "source": "bm25-appended",  
        }

        # Add to fetched_texts in the data model
        fetched_texts = point_data.setdefault("fetched_texts", [])
        fetched_texts.append(new_item)

        logger.info(f"Added BM25 result as new fetched text with ID: {result_id}")

        # Add to the left panel UI
        keywords = point_data.get("keywords", [])
        highlighted_text = self._highlight_keywords(result_text, keywords)
        self.add_item_to_left_panel(
            result_id, highlighted_text, "bm25-appended"
        )

        # remove from right panel
        item_widget.deleteLater()  # Remove the widget from the right panel
        # Note: Saving happens on navigation or confirm

    # --- Helper Methods ---
    def add_item_to_left_panel(self, item_id, text, source):
        """Adds a fetched text item widget to the left scrollable list."""
        item_widget = ListItemWidget(item_id, text, source, "Remove")

        # Connect the REMOVE button signal
        item_widget.button_clicked_signal.connect(self.remove_fetched_text)
        # Connect the ITEM CLICK signal (for selecting)
        item_widget.item_clicked_signal.connect(self.mark_text_as_selected)

        self.left_list_layout.addWidget(item_widget)
        return (
            item_widget  
        )

    def clear_layout(self, layout):
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
                self.clear_layout(child.layout())
                # The layout item (representing the nested layout) is removed by takeAt(0)

def load_and_validate_data(data_file_path):
    """Loads and validates the JSON data """
    if not os.path.exists(data_file_path):
        raise FileNotFoundError(f"Data file {data_file_path} does not exist.")
    try:
        with open(data_file_path, "r", encoding="utf-8") as f:
            ground_truth_data = json.load(f)
        # Validate against schema
        validate_ground_truth(ground_truth_data)
        logger.info("Ground truth data loaded and validated successfully.")
        return ground_truth_data
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {e.msg}")
        QMessageBox.critical(None, "Error", f"JSON decode error in file:\n{e.msg}")
        return None
    except ValidationError as e:
        logger.error(f"Validation error: {e.message}")
        QMessageBox.critical(None, "Error", f"Validation error in ground truth data:\n{e.message}")
        return None
    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        QMessageBox.critical(None, "Error", str(e))
        return None

# --- Run the Application ---
if __name__ == "__main__":
    app = QApplication(sys.argv)

    # --- File Selection Dialog ---
    file_dialog = QFileDialog()
    file_dialog.setFileMode(QFileDialog.ExistingFile)
    file_dialog.setNameFilter("JSON files (*.json)")
    file_dialog.setDirectory(os.getcwd())

    if file_dialog.exec():
        selected_files = file_dialog.selectedFiles()
        if selected_files:
            data_file_path = selected_files[0]
            logger.info(f"Selected file: {data_file_path}")

            # load and validate data 
            ground_truth_data = load_and_validate_data(data_file_path)

            if ground_truth_data:
                # launch app with valid data
                window = AnnotationApp(
                    data_file_path=data_file_path,
                    ground_truth_data=ground_truth_data 
                )
                window.show()
                sys.exit(app.exec())
            else:
                logger.error("Exiting due to data loading/validation error.")
                sys.exit(1) 
        else:
            logger.info("No file selected.")
            sys.exit(0)
    else:
        logger.info("File dialog cancelled.")
        sys.exit(0)
