
#!/usr/bin/env bash

set -euo pipefail

if [[ $# -lt 1 ]]; then
    echo "Usage: bash $0 <folder-path>"
    exit 1
fi

PDF_DIR="$(cd "$1" && pwd)"
OUTPUT_DIR="$PDF_DIR/Classified_Output"

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/classify_placement_pdfs_ocr.py"
LOG_FILE="$SCRIPT_DIR/placement_classifier.log"
PID_FILE="$SCRIPT_DIR/placement_classifier.pid"
PROGRESS_FILE="$SCRIPT_DIR/placement_classifier_progress.txt"

WORKERS=4

if [[ ! -f "$PYTHON_SCRIPT" ]]; then
    echo "Python script not found: $PYTHON_SCRIPT"
    exit 1
fi

python3 -c "import fitz, pytesseract, PIL, tqdm" 2>/dev/null || {
    echo "Install dependencies:"
    echo "python3 -m pip install pymupdf pytesseract pillow tqdm"
    exit 1
}

command -v tesseract >/dev/null 2>&1 || {
    echo "Tesseract not found."
    exit 1
}

if [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
    echo "Already running; PID $(cat "$PID_FILE")"
    exit 0
fi

mkdir -p "$OUTPUT_DIR"
rm -f "$PROGRESS_FILE"

nohup python3 -u "$PYTHON_SCRIPT" "$PDF_DIR" \
    --output "$OUTPUT_DIR" \
    --workers "$WORKERS" \
    --progress-file "$PROGRESS_FILE" \
    > "$LOG_FILE" 2>&1 < /dev/null &

echo $! > "$PID_FILE"

echo "Classifier started."
echo "PID: $(cat "$PID_FILE")"
echo "Workers: $WORKERS"
echo "Input: $PDF_DIR"
echo "Output: $OUTPUT_DIR"
echo
echo "To monitor live progress, run:"
echo "watch -n 1 cat \"$PROGRESS_FILE\""