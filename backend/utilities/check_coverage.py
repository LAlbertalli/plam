import json
import os
import sys

# Default threshold for files under app/
DEFAULT_THRESHOLD = 70.0

# Specific file thresholds (e.g. security helpers)
SPECIFIC_THRESHOLDS = {
    "app/core/crypto_helper.py": 80.0,
}

# Exemptions / Allowed lower coverage due to infrastructure mocking
EXEMPTIONS = {
    "app/services/docker_manager.py": 60.0,
    "app/services/huggingface_downloader.py": 40.0,
}

def main():
    coverage_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "coverage.json"))
    if not os.path.exists(coverage_file):
        print(f"Error: Coverage JSON file not found at {coverage_file}", file=sys.stderr)
        print("Please run pytest with coverage first (e.g. pytest --cov=app --cov-report=json)", file=sys.stderr)
        sys.exit(1)

    with open(coverage_file, "r") as f:
        data = json.load(f)

    files_data = data.get("files", {})
    failed = False
    checked_count = 0

    print("Checking per-file code coverage...")
    print("=" * 60)

    for file_path, file_info in sorted(files_data.items()):
        # Only check files in the app/ directory
        if not file_path.startswith("app/"):
            continue

        # Ignore empty or __init__.py files with 0 statements
        summary = file_info.get("summary", {})
        if summary.get("num_statements", 0) == 0:
            continue

        percent_covered = summary.get("percent_covered", 0.0)
        
        # Determine expected threshold
        if file_path in SPECIFIC_THRESHOLDS:
            expected = SPECIFIC_THRESHOLDS[file_path]
            desc = " (Custom minimum)"
        elif file_path in EXEMPTIONS:
            expected = EXEMPTIONS[file_path]
            desc = " (Exemption)"
        else:
            expected = DEFAULT_THRESHOLD
            desc = ""

        checked_count += 1

        if percent_covered < expected:
            print(f"FAIL: {file_path}")
            print(f"      Coverage: {percent_covered:.2f}% < Expected: {expected:.2f}%{desc}")
            failed = True
        else:
            print(f"PASS: {file_path} ({percent_covered:.2f}% >= {expected:.2f}%{desc})")

    print("=" * 60)
    if failed:
        print("Coverage check FAILED! Some files do not meet their coverage threshold.", file=sys.stderr)
        sys.exit(1)
    else:
        print(f"Coverage check PASSED! All {checked_count} checked files met their thresholds.")
        sys.exit(0)

if __name__ == "__main__":
    main()
