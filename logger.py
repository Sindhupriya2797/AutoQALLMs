import json
import os
from datetime import datetime


# This is the file where all training data will be saved
DATASET_FILE = "training_dataset.json"


def load_existing_data():
    """
    Loads existing training records from the dataset file.
    If the file doesn't exist yet, returns an empty list.
    """
    if os.path.exists(DATASET_FILE):
        with open(DATASET_FILE, "r") as f:
            return json.load(f)
    return []


def save_record(record):
    """
    Adds one new record to the dataset file.
    Each record = one website run.
    """
    all_data = load_existing_data()
    all_data.append(record)

    with open(DATASET_FILE, "w") as f:
        json.dump(all_data, f, indent=2)

    print(f"\n[LOGGER] Record saved. Total records in dataset: {len(all_data)}")


def build_element_fingerprints(parsed_data):
    """
    For each element found in the parsed HTML, we store multiple
    attributes. This is the fingerprint used later for self-healing.
    If the primary locator (e.g. id) breaks, we can use the others
    to find the same element.
    """
    fingerprints = []

    # Fingerprint each input field
    for inp in parsed_data.get("inputs", []):
        fingerprints.append({
            "element_type": "input",
            "id": inp.get("id", ""),
            "name": inp.get("name", ""),
            "placeholder": inp.get("placeholder", ""),
            "input_type": inp.get("type", ""),
            "tag": "input"
        })

    # Fingerprint each button
    for btn in parsed_data.get("buttons", []):
        fingerprints.append({
            "element_type": "button",
            "id": btn.get("id", ""),
            "name": btn.get("name", ""),
            "text": btn.get("text", ""),
            "tag": "button"
        })

    # Fingerprint each link
    for link in parsed_data.get("links", []):
        fingerprints.append({
            "element_type": "link",
            "href": link,
            "tag": "a"
        })

    # Fingerprint each select dropdown
    for sel in parsed_data.get("selects", []):
        fingerprints.append({
            "element_type": "select",
            "id": sel.get("id", ""),
            "name": sel.get("name", ""),
            "options": sel.get("options", []),
            "tag": "select"
        })

    return fingerprints


def build_record(url, model_used, parsed_data,
                 generation_time, execution_time,
                 tests_passed, tests_failed):
    """
    Builds one complete training record for a single website run.
    Call this function after each website test completes.
    """

    total_tests = tests_passed + tests_failed
    failure_rate = round((tests_failed / total_tests) * 100, 2) if total_tests > 0 else 0.0

    # Count total elements found across all categories
    elements_found = (
        len(parsed_data.get("inputs", [])) +
        len(parsed_data.get("buttons", [])) +
        len(parsed_data.get("links", [])) +
        len(parsed_data.get("selects", [])) +
        len(parsed_data.get("forms", [])) +
        len(parsed_data.get("images", []))
    )

    record = {
        "url": url,
        "timestamp": datetime.now().isoformat(),
        "model_used": model_used,
        "elements_found": elements_found,
        "tests_generated": total_tests,
        "tests_passed": tests_passed,
        "tests_failed": tests_failed,
        "failure_rate": failure_rate,
        "generation_time_seconds": round(generation_time, 2),
        "execution_time_seconds": round(execution_time, 2),
        "element_fingerprints": build_element_fingerprints(parsed_data),
        "parsed_summary": {
            "title": parsed_data.get("title", ""),
            "num_links": len(parsed_data.get("links", [])),
            "num_inputs": len(parsed_data.get("inputs", [])),
            "num_buttons": len(parsed_data.get("buttons", [])),
            "num_forms": len(parsed_data.get("forms", [])),
            "num_images": len(parsed_data.get("images", [])),
            "num_selects": len(parsed_data.get("selects", []))
        }
    }

    return record