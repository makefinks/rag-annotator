import logging
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QGroupBox,
    QScrollArea,
    QFrame,
)
from PySide6.QtCore import Qt, Signal, Slot
from app.widgets.list_item_widget import ListItemWidget
from app.utils.ui_helpers import clear_layout

logger = logging.getLogger(__name__)

class LeftPanel(QWidget):
    """Left panel containing the scrollable list of fetched text items."""
    
    # Signal emitted when an item is clicked (for selection)
    item_clicked = Signal(QWidget)
    # Signal emitted when an item's remove button is clicked
    item_remove_clicked = Signal(QWidget)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scroll_area = None
        self.list_widget = None
        self.list_layout = None
        
        self._init_ui()
    
    def _init_ui(self):
        """Initialize the UI components of the left panel."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        groupbox = QGroupBox("Fetched Texts (Click to Select, Button to Remove)")
        groupbox.setMinimumWidth(300)
        
        outer_layout = QVBoxLayout(groupbox)
        
        # Scroll Area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        
        # Container widget inside ScrollArea
        self.list_widget = QWidget()
        self.list_layout = QVBoxLayout(self.list_widget)
        self.list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout.setSpacing(5)
        
        self.scroll_area.setWidget(self.list_widget)
        outer_layout.addWidget(self.scroll_area)
        
        main_layout.addWidget(groupbox)
    
    def add_item(self, item_id, text, source, metadata=None):
        """Add a new item to the panel."""
        item_widget = ListItemWidget(item_id, text, source, "Remove", metadata)
        
        # Connect signals
        item_widget.button_clicked_signal.connect(self._on_item_button_clicked)
        item_widget.item_clicked_signal.connect(self._on_item_clicked)
        
        self.list_layout.addWidget(item_widget)
        return item_widget
    
    def clear(self):
        """Clear all items from the panel."""
        clear_layout(self.list_layout)
    
    def scroll_to_top(self):
        """Scroll the panel to the top."""
        self.scroll_area.verticalScrollBar().setValue(0)
    
    def set_enabled(self, enabled):
        """Enable or disable all items in the panel."""
        for i in range(self.list_layout.count()):
            widget = self.list_layout.itemAt(i).widget()
            if isinstance(widget, ListItemWidget):
                widget.set_enabled_state(enabled)
    
    @Slot(QWidget)
    def _on_item_clicked(self, item_widget):
        """Handle item click."""
        self.item_clicked.emit(item_widget)
    
    @Slot(QWidget)
    def _on_item_button_clicked(self, item_widget):
        """Handle item button click."""
        self.item_remove_clicked.emit(item_widget)
