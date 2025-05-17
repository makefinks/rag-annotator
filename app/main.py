import sys
import os
import logging
from PySide6.QtWidgets import QApplication, QFileDialog
from PySide6.QtWidgets import QMessageBox
from app.widgets.annotation_app import AnnotationApp
from app.utils.data_handler import load_and_validate_data
# --- Logger Configuration ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

def main() -> None:
    app: QApplication = QApplication(sys.argv)

    # --- File Selection Dialog ---
    file_dialog: QFileDialog = QFileDialog()
    file_dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
    file_dialog.setNameFilter("JSON files (*.json)")
    file_dialog.setDirectory(os.getcwd())

    if file_dialog.exec():
        selected_files: list[str] = file_dialog.selectedFiles()
        if selected_files:
            data_file_path: str = selected_files[0]
            logger.info(f"Selected file: {data_file_path}")

            # load and validate data
            ground_truth_data: list[dict[str, any]] | None = load_and_validate_data(data_file_path)

            if ground_truth_data:
                # launch app with valid data
                window: AnnotationApp = AnnotationApp(
                    data_file_path=data_file_path, ground_truth_data=ground_truth_data
                )
                window.show()
                sys.exit(app.exec())
            else:
                QMessageBox.critical(
                    None,
                    "Data Loading/Validation Error",
                    "Failed to load or validate the selected data file. Please check the file format and content."
                )
                logger.error("Exiting due to data loading/validation error.")
                sys.exit(1)
        else:
            logger.info("No file selected.")
            sys.exit(0)
    else:
        logger.info("File dialog cancelled.")
        sys.exit(0)

if __name__ == "__main__":
    main()
