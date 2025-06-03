import os
import logging
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QSplitter,
)
from PySide6.QtCore import Qt, Slot
from app.widgets.top_panel import TopPanel
from app.widgets.left_panel import LeftPanel
from app.widgets.right_panel import RightPanel
from app.widgets.bottom_panel import BottomPanel
from app.utils.ui_helpers import highlight_keywords
from app.utils.data_handler import save_ground_truth
from app.utils.bm25_handler import (
    get_or_build_index,
    extract_texts_from_ground_truth,
)
from app.utils.formatting import format_md_text_to_html

logger = logging.getLogger(__name__)

class AnnotationApp(QWidget):
    # Highlight color used for keywords within text descriptions and fetched texts.
    HIGHLIGHT_COLOR = "rgba(255, 255, 0, 0.2)"  # Yellow for general keywords
    ITEM_HIGHLIGHT_COLOR = (
        "rgba(135, 206, 250, 0.3)"  # Light blue for item-specific highlights
    )

    def __init__(self, data_file_path, ground_truth_data):
        super().__init__()
        self.data_file_path = data_file_path
        self.ground_truth_data = ground_truth_data
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

        # --- Main Layout ---
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(15, 15, 15, 15)
        self.main_layout.setSpacing(10)

        # --- Initialize Panels ---
        self._init_panels()

        # --- Apply Stylesheet ---
        self._apply_stylesheet()

        # --- Load Initial Point ---
        if self.ground_truth_data["points"]:
            # Find first non-evaluated point or default to first point
            self.current_point_index = next(
                (
                    i
                    for i, point in enumerate(self.ground_truth_data["points"])
                    if not point.get("evaluated", False)
                ),
                0,
            )
            self._load_point(self.current_point_index)
        else:
            logger.warning("No subobjects found in the data file.")
            self.top_panel.set_description_text("No subobjects loaded.")
            self.bottom_panel.set_prev_enabled(False)
            self.bottom_panel.set_next_enabled(False)
            self.bottom_panel.set_confirm_text("Confirm")

    def _init_panels(self):
        """Initialize all panels and connect their signals."""
        # Top Panel
        self.top_panel = TopPanel()
        self.top_panel.navigator_changed.connect(self._navigate_via_navigator)
        self.top_panel.remove_point_clicked.connect(self._remove_point)
        self.top_panel.temp_keywords_changed.connect(self._on_temp_keywords_changed)
        self.main_layout.addWidget(self.top_panel)

        # Middle Panels (Left and Right in a Splitter)
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left Panel
        self.left_panel = LeftPanel()
        self.left_panel.item_clicked.connect(self.mark_text_as_selected)
        self.left_panel.item_remove_clicked.connect(self.remove_fetched_text)
        self.splitter.addWidget(self.left_panel)
        
        # Right Panel
        self.right_panel = RightPanel()
        self.right_panel.search_requested.connect(self.perform_bm25_search)
        self.right_panel.item_add_clicked.connect(self.add_bm25_result_to_fetched)
        self.splitter.addWidget(self.right_panel)
        
        self.main_layout.addWidget(self.splitter, 1)
        self.splitter.setSizes([1, 1])

        # Bottom Panel
        self.bottom_panel = BottomPanel()
        self.bottom_panel.prev_clicked.connect(self.navigate_previous)
        self.bottom_panel.confirm_clicked.connect(self.confirm_point)
        self.bottom_panel.next_clicked.connect(self.navigate_next)
        self.main_layout.addWidget(self.bottom_panel)

    def _apply_stylesheet(self):
        """Loads and applies the stylesheet from an external CSS file."""
        try:
            css_file_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                "resources", 
                "dark_theme.css"
            )
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
        save_ground_truth(self.ground_truth_data, self.data_file_path)

    # --- UI Population ---
    def _load_point(self, point_index):
        """Populates the UI with data from the specified point index."""
        if (
            not self.ground_truth_data["points"]
            or point_index < 0
            or point_index >= len(self.ground_truth_data["points"])
        ):
            logger.warning(f"Error: Point index {point_index} is out of range.")
            return

        self.current_point_index = point_index
        point_data = self.ground_truth_data["points"][point_index]

        # --- Clear existing UI elements ---
        self.left_panel.clear()
        self.right_panel.clear()
        self.right_panel.set_search_text("")

        # Scroll both panels to the top
        self.left_panel.scroll_to_top()
        self.right_panel.scroll_to_top()

        # --- Populate Top Panel ---
        self.top_panel.set_position_text(
            f"Point {point_index + 1} of {len(self.ground_truth_data['points'])}"
        )

        # Display the point ID if it exists
        point_id = point_data.get("id", "N/A")
        self.top_panel.set_id_text(str(point_id))

        # Populate navigator dropdown
        navigator_items = []
        for idx, p_data in enumerate(self.ground_truth_data["points"]):
            title = p_data.get("title", f"Point {idx + 1}")
            is_eval = p_data.get("evaluated", False)
            navigator_items.append((title, idx, is_eval))
        self.top_panel.populate_navigator(navigator_items, point_index)

        # --- Populate Description ---
        keywords = point_data.get("keywords", [])
        description = point_data.get("description", "No description provided.")
        self.top_panel.set_description_text(description, keywords)

        # --- Populate Left Panel (Fetched Texts) ---
        is_evaluated = point_data.get("evaluated", False)
        point_keywords = point_data.get("keywords", [])

        for item_data in point_data.get("fetched_texts", []):
            item_id = item_data.get("id")
            text = item_data.get("text", "")
            source = item_data.get("source", "unknown")
            metadata = item_data.get("metadata", {})
            item_specific_highlights = item_data.get("highlights", [])

            if item_id is None:
                logger.warning("Found fetched_text item without an ID. Skipping.")
                continue

            temp_highlighted_text = text  # Start with original text
            if item_specific_highlights:
                temp_highlighted_text = highlight_keywords(
                    temp_highlighted_text,
                    item_specific_highlights,
                    self.ITEM_HIGHLIGHT_COLOR,
                )

            if point_keywords:
                temp_highlighted_text = highlight_keywords(
                    temp_highlighted_text, point_keywords, self.HIGHLIGHT_COLOR
                )

            highlighted_text = temp_highlighted_text
            formatted_text = format_md_text_to_html(highlighted_text)

            # Check if this item is selected
            is_selected = any(
                sel_item.get("id") == item_id
                for sel_item in point_data.get("selected_texts", [])
            )

            # Add item to the left panel
            item_widget = self.left_panel.add_item(
                item_id, formatted_text, source, metadata
            )

            # Set initial selected state
            if item_widget:
                item_widget.set_selected(is_selected)

        # --- Update Button States ---
        self.bottom_panel.set_prev_enabled(point_index > 0)
        self.bottom_panel.set_next_enabled(
            point_index < len(self.ground_truth_data["points"]) - 1
        )
        # Confirm button is always enabled, but text changes
        self.bottom_panel.set_confirm_text("Unconfirm" if is_evaluated else "Confirm")

        # --- Disable/Enable Left Panel Items based on evaluation status ---
        self.left_panel.set_enabled(not is_evaluated)

    def _remove_point(self):
        """Removes the current evaluation point from the ground truth without confirmation"""
        if self.current_point_index is None or not self.ground_truth_data["points"]:
            logger.error("No point selected to remove")
            return

        current_index = self.current_point_index

        # Verify the index is valid before removing
        if current_index < 0 or current_index >= len(self.ground_truth_data["points"]):
            logger.error(
                f"Invalid point index {current_index}. Valid range: 0-{len(self.ground_truth_data['points']) - 1}"
            )
            return

        del self.ground_truth_data["points"][current_index]

        # Handle index adjustment after removal
        if len(self.ground_truth_data["points"]) == 0:
            # No more points left
            logger.info("All points removed")
            self.current_point_index = None
            self.top_panel.set_description_text("No points remaining.")
            self.bottom_panel.set_prev_enabled(False)
            self.bottom_panel.set_next_enabled(False)
            self.bottom_panel.set_confirm_text("Confirm")
        else:
            # Adjust index if we removed the last point
            if current_index >= len(self.ground_truth_data["points"]):
                self.current_point_index = len(self.ground_truth_data["points"]) - 1
            else:
                self.current_point_index = current_index

            # Load the point at the adjusted index
            self._load_point(self.current_point_index)

        # update the ground truth
        self._save_ground_truth()

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
        self.bottom_panel.set_confirm_text("Unconfirm" if new_state else "Confirm")
        self.left_panel.set_enabled(not new_state)  # Enable if new_state is False

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

    @Slot(int)
    def _navigate_via_navigator(self, combo_box_index):
        """Navigates to the point selected in the title navigator dropdown."""
        if combo_box_index == -1:  # Should not happen unless list is empty
            return

        target_point_index = self.top_panel.title_navigator.itemData(combo_box_index)

        # Check if it's a valid index and different from the current one
        if (
            target_point_index is not None
            and target_point_index != self.current_point_index
        ):
            logger.info(
                f"Navigating via title navigator to point index: {target_point_index}"
            )
            # Save current state before navigating
            self._save_ground_truth()
            # Load the selected point
            self._load_point(target_point_index)
    
    @Slot(list)
    def _on_temp_keywords_changed(self, temp_keywords):
        """Handle changes in temporary keyword selection from description."""
        if self.current_point_index is None or not self.ground_truth_data["points"]:
            return
            
        point_data = self.ground_truth_data["points"][self.current_point_index]
        
        # Re-highlight all fetched texts with new temporary keywords
        for item_widget in self.left_panel.get_all_items():
            if hasattr(item_widget, 'item_id'):
                # Find the corresponding item data
                for item_data in point_data.get("fetched_texts", []):
                    if item_data.get("id") == item_widget.item_id:
                        text = item_data.get("text", "")
                        item_specific_highlights = item_data.get("highlights", [])
                        
                        # Apply highlighting: item-specific first, then temp keywords
                        temp_highlighted_text = text
                        if item_specific_highlights:
                            temp_highlighted_text = highlight_keywords(
                                temp_highlighted_text,
                                item_specific_highlights,
                                self.ITEM_HIGHLIGHT_COLOR,
                            )
                        
                        if temp_keywords:
                            temp_highlighted_text = highlight_keywords(
                                temp_highlighted_text, temp_keywords, self.HIGHLIGHT_COLOR
                            )
                        
                        formatted_text = format_md_text_to_html(temp_highlighted_text)
                        item_widget.set_text(formatted_text)
                        break

    @Slot(str)
    def perform_bm25_search(self, search_query=None):
        """
        Performs a BM25 search based on the input from the search bar and displays the results on the right panel
        """
        if self.current_point_index is None or not self.ground_truth_data["points"]:
            logger.warning("No current point selected.")
            return

        point_data = self.ground_truth_data["points"][self.current_point_index]

        # Clear previous results
        self.right_panel.clear()

        keywords = point_data.get("keywords", [])
        description = point_data.get("description", "")
        if not description:
            logger.warning("No description provided for the current point.")

        # If no search query provided, use the one from the search input
        if search_query is None or not search_query:
            search_query = self.right_panel.get_search_text()
            
        # If still empty, use description
        if not search_query:
            search_query = description

        logger.info(f"Performing BM25 search with query: {search_query}")

        # Perform the search using the BM25 index
        results = self.bm25_index.get_top_n(search_query, self.bm25_texts, n=20)

        logger.info(f"Found {len(results)} BM25 search results")

        # Display results in the right panel
        if not results:
            # Show a message when no results are found
            self.right_panel.add_message("No results found for this query.")
            return

        used_ids = [
            item["id"]
            for item in point_data.get("fetched_texts", [])
            if item.get("id") is not None
        ]

        # Add each result to the right panel
        results_added = False
        for result_text in results:
            # get the id
            actual_id = self.text_to_id_map.get(result_text)

            # do not display bm25 search when already visible in left panel
            if actual_id in used_ids:
                continue

            # Determine terms to highlight based on original logic
            # Use temporary keywords from description if available
            temp_keywords = self.top_panel.get_temp_selected_words()
            effective_keywords = temp_keywords if temp_keywords else keywords
            
            terms_to_highlight_in_bm25 = []
            search_terms_list = [term for term in search_query.split() if term.strip()]

            if search_query and len(search_terms_list) == 1:
                terms_to_highlight_in_bm25 = list(set(effective_keywords + search_terms_list))
            else:
                terms_to_highlight_in_bm25 = list(set(effective_keywords))

            highlighted_text = highlight_keywords(
                result_text, terms_to_highlight_in_bm25, self.HIGHLIGHT_COLOR
            )
            formatted_text = format_md_text_to_html(highlighted_text)
            
            # Add the result to the right panel
            self.right_panel.add_item(actual_id, formatted_text)
            results_added = True

        # If no widgets were added, search returned nothing
        if not results_added:
            self.right_panel.add_message(
                "No results found for this query, or results already on left side."
            )

    @Slot(QWidget)
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

    @Slot(QWidget)
    def remove_fetched_text(self, item_widget):
        """
        Handles clicking the 'Remove' button on a fetched text item in the left panel.
        Removes the item from the 'fetched_texts' list in the data model,
        and also removes it from 'selected_texts' if it was selected.
        Does nothing if the current point is marked as 'evaluated'.
        """
        if self.current_point_index is None or not self.ground_truth_data["points"]:
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
        highlighted_text = highlight_keywords(
            result_text, keywords, self.HIGHLIGHT_COLOR
        )
        formatted_text = format_md_text_to_html(highlighted_text)
        self.left_panel.add_item(result_id, formatted_text, "bm25-appended")

        # Note: Saving happens on navigation or confirm
