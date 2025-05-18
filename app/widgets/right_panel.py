import logging
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QScrollArea,
    QLineEdit,
    QPushButton,
    QLabel,
    QFrame,
)
from PySide6.QtCore import Qt, Signal, Slot
from app.widgets.list_item_widget import ListItemWidget
from app.utils.ui_helpers import clear_layout

logger = logging.getLogger(__name__)

class RightPanel(QWidget):
    """Right panel for BM25 search and results."""
    
    # Signal emitted when search is requested
    search_requested = Signal(str)
    # Signal emitted when an item's add button is clicked
    item_add_clicked = Signal(QWidget)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.search_input = None
        self.search_button = None
        self.scroll_area = None
        self.list_widget = None
        self.list_layout = None
        
        self._init_ui()
    
    def _init_ui(self):
        """Initialize the UI components of the right panel."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        groupbox = QGroupBox("BM25 Search")
        groupbox.setMinimumWidth(350)
        
        outer_layout = QVBoxLayout(groupbox)
        
        # Search controls
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setMinimumWidth(200)
        self.search_input.setPlaceholderText("search field")
        self.search_button = QPushButton("Search")
        
        # Connect signals
        self.search_button.clicked.connect(self._on_search_clicked)
        self.search_input.returnPressed.connect(self._on_search_clicked)
        
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.search_button)
        outer_layout.addLayout(search_layout)
        
        # Scroll Area for results
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        
        # Container widget for results
        self.list_widget = QWidget()
        self.list_layout = QVBoxLayout(self.list_widget)
        self.list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout.setSpacing(5)
        
        self.scroll_area.setWidget(self.list_widget)
        outer_layout.addWidget(self.scroll_area)
        
        main_layout.addWidget(groupbox)
    
    def add_item(self, item_id, text, source="bm25-appended"):
        """Add a new search result item to the panel."""
        item_widget = ListItemWidget(item_id, text, source, "Add")
        
        # Connect signal
        item_widget.button_clicked_signal.connect(self._on_item_button_clicked)
        
        self.list_layout.addWidget(item_widget)
        return item_widget
    
    def add_message(self, message):
        """Add a message label to the panel."""
        label = QLabel(message)
        label.setStyleSheet("padding: 10px; color: #888888;")
        self.list_layout.addWidget(label)
    
    def clear(self):
        """Clear all items from the panel."""
        clear_layout(self.list_layout)
    
    def scroll_to_top(self):
        """Scroll the panel to the top."""
        self.scroll_area.verticalScrollBar().setValue(0)
    
    def get_search_text(self):
        """Get the current search text."""
        return self.search_input.text()
    
    def set_search_text(self, text):
        """Set the search text."""
        self.search_input.setText(text)
    
    @Slot()
    def _on_search_clicked(self):
        """Handle search button click or Enter key press."""
        self.search_requested.emit(self.search_input.text())
    
    @Slot(QWidget)
    def _on_item_button_clicked(self, item_widget):
        """Handle item button click."""
        self.item_add_clicked.emit(item_widget)
        # Remove the widget after it's been added
        self.list_layout.removeWidget(item_widget)
        item_widget.deleteLater()
