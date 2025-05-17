import logging
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
)
from PySide6.QtCore import Qt, Signal

logger = logging.getLogger(__name__)

class TopPanel(QWidget):
    """Top panel containing point description, position, title, and ID."""
    
    # Signal emitted when the navigator dropdown selection changes
    navigator_changed = Signal(int)
    # Signal emitted when the remove button is clicked
    remove_point_clicked = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.point_description_label = None
        self.position_label = None
        self.id_label = None
        self.title_navigator = None
        self.remove_point_button = None
        
        self._init_ui()
        
    def _init_ui(self):
        """Initialize the UI components of the top panel."""
        # Create group boxes
        top_group_desc = QGroupBox("Description")
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

        # Description label in Description group
        self.point_description_label = QLabel(
            "This is where the detailed point description will be displayed."
        )
        self.point_description_label.setWordWrap(True)
        self.point_description_label.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.point_description_label.setStyleSheet("padding: 5px;")

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
    
    def _on_navigator_changed(self, index):
        """Handle navigator dropdown selection change."""
        self.navigator_changed.emit(index)
    
    def _on_remove_clicked(self):
        """Handle remove button click."""
        self.remove_point_clicked.emit()
    
    def set_position_text(self, text):
        """Set the position label text."""
        self.position_label.setText(text)
    
    def set_id_text(self, text):
        """Set the ID label text."""
        self.id_label.setText(text)
    
    def set_description_text(self, text):
        """Set the description label text."""
        self.point_description_label.setText(text)
    
    def populate_navigator(self, items, current_index):
        """Populate the title navigator dropdown."""
        self.title_navigator.blockSignals(True)
        self.title_navigator.clear()
        for title, idx, is_evaluated in items:
            prefix = "✓ " if is_evaluated else ""
            self.title_navigator.addItem(f"{prefix}{title}", userData=idx)
        self.title_navigator.setCurrentIndex(current_index)
        self.title_navigator.blockSignals(False)
