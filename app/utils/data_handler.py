import os
import json
import logging
from jsonschema import ValidationError
from app.utils.validation import validate_ground_truth
from PySide6.QtWidgets import QMessageBox
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

def load_and_validate_data(data_file_path: str) -> Optional[List[Dict[str, Any]]]:
    """Loads and validates the JSON data"""
    if not os.path.exists(data_file_path):
        raise FileNotFoundError(f"Data file {data_file_path} does not exist.")
    try:
        with open(data_file_path, "r", encoding="utf-8") as f:
            ground_truth_data: List[Dict[str, Any]] = json.load(f)
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
        QMessageBox.critical(
            None, "Error", f"Validation error in ground truth data:\n{e.message}"
        )
        return None
    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        QMessageBox.critical(None, "Error", str(e))
        return None

def save_ground_truth(ground_truth_data: Optional[List[Dict[str, Any]]], data_file_path: str) -> None:
    """Saves the current state of ground_truth_data back to the JSON file."""
    if ground_truth_data is None:
        logger.error("No data to save.")
        return
    try:
        with open(data_file_path, "w", encoding="utf-8") as f:
            json.dump(ground_truth_data, f, indent=4, ensure_ascii=False)
        logger.info(f"Data saved to {data_file_path}")
    except Exception as e:
        logger.error(f"Error writing file {data_file_path}: {e}")

