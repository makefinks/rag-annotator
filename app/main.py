import sys
import os
import logging
from PySide6.QtWidgets import QApplication, QFileDialog
from app.widgets.main_window import AnnotationApp
from app.utils.data_handler import load_and_validate_data

# --- Logger Configuration ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

def main():
    app = QApplication(sys.argv)

    # --- File Selection Dialog ---
    file_dialog = QFileDialog()
    file_dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
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
                    data_file_path=data_file_path, ground_truth_data=ground_truth_data
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

if __name__ == "__main__":
    main()
