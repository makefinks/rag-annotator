import logging
from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QPushButton,
    QStyle,
)
from PySide6.QtCore import Signal

logger = logging.getLogger(__name__)

class BottomPanel(QWidget):
    """Bottom panel containing navigation and confirmation buttons."""
    
    # Signals for button clicks
    prev_clicked = Signal()
    confirm_clicked = Signal()
    next_clicked = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.prev_button = None
        self.confirm_button = None
        self.next_button = None
        
        self._init_ui()
    
    def _init_ui(self):
        """Initialize the UI components of the bottom panel."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        
        self.prev_button = QPushButton("Previous")
        self.confirm_button = QPushButton("Confirm")
        self.next_button = QPushButton("Next")
        
        # Add icons and tooltips
        style = self.style()
        self.prev_button.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_ArrowLeft))
        self.next_button.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_ArrowRight))
        self.confirm_button.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_DialogApplyButton))
        
        self.prev_button.setToolTip("Go to previous point")
        self.next_button.setToolTip("Go to next point")
        self.confirm_button.setToolTip("Toggle evaluation state")
        
        # Connect signals
        self.prev_button.clicked.connect(self.prev_clicked)
        self.confirm_button.clicked.connect(self.confirm_clicked)
        self.next_button.clicked.connect(self.next_clicked)
        
        layout.addStretch()
        layout.addWidget(self.prev_button)
        layout.addWidget(self.confirm_button)
        layout.addWidget(self.next_button)
        layout.addStretch()
    
    def set_prev_enabled(self, enabled):
        """Enable or disable the previous button."""
        self.prev_button.setEnabled(enabled)
    
    def set_next_enabled(self, enabled):
        """Enable or disable the next button."""
        self.next_button.setEnabled(enabled)
    
    def set_confirm_text(self, text):
        """Set the text of the confirm button."""
        self.confirm_button.setText(text)
