
#!/usr/bin/env python3
"""Parallel OCR-enabled IIT Delhi placement JNF classifier.

Usage:
  python3 classify_placement_pdfs_ocr.py INPUT_DIR \
      --output OUTPUT_DIR --workers 4 --progress-file progress.txt

Requires:
  pip install pymupdf pytesseract pillow tqdm
  Tesseract OCR installed on the system.
"""

import argparse
import csv
import os
import re
import shutil
import sys
import time
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed

# Avoid excessive internal threading by OCR dependencies
os.environ["OMP_THREAD_LIMIT"] = "1"

import fitz
import pytesseract
from PIL import Image
from tqdm import tqdm


CATEGORIES = {
    "Finance": [
        "private equity", "investment banking", "venture capital",
        "equity research", "financial modelling", "financial modeling",
        "valuation", "portfolio management", "asset management",
        "risk management", "credit risk", "investment analyst",
        "quantitative finance", "capital markets", "m&a",
        "financial due diligence"
    ],
    "Analytics": [
        "data analytics", "business analytics", "data science",
        "machine learning", "statistical modelling",
        "statistical modeling", "predictive modelling",
        "predictive modeling", "forecasting", "econometrics",
        "python", "sql", "power bi", "tableau",
        "quantitative research", "model validation",
        "business intelligence"
    ],
    "Consulting": [
        "management consulting", "strategy consulting",
        "business consulting", "economic consulting",
        "market research", "industry research", "due diligence",
        "business strategy", "competitive benchmarking",
        "strategic advisory", "consultant"
    ],
    "Management": [
        "product management", "product manager",
        "program management", "project management",
        "business development", "operations management",
        "product strategy", "category management",
        "general management"
    ],
    "InformationTechnology": [
        "software development", "software engineer",
        "machine learning engineer", "data engineer",
        "cloud computing", "full stack", "backend development",
        "frontend development", "cybersecurity", "devops",
        "database administration", "artificial intelligence engineer"
    ],
    "Core(Technical)": [
        "mechanical engineering", "electrical engineering",
        "civil engineering", "chemical engineering",
        "production engineering", "electronics",
        "manufacturing", "process engineering", "technical design"
    ],
    "Teaching&Research": [
        "research associate", "research assistant",
        "research analyst", "teaching assistant",
        "academic research", "economic research",
        "policy research", "public policy",
        "development economics", "economist", "research fellow"
    ],
    "Other": [
        "human resources", "recruitment", "sales executive",
        "customer relations", "administration",
        "corporate communications", "business operations",
        "customer success"
    ]
}


def extract_page_text(page, dpi=220):
    text = page.get_text("text") or ""

    if len(text.strip()) >= 40:
        return text, "text"

    pix = page.get_pixmap(
        matrix=fitz.Matrix(dpi / 72, dpi / 72),
        alpha=False
    )

    img = Image.frombytes(
        "RGB",
        [pix.width, pix.height],
        pix.samples
    )

    return pytesseract.image_to_string(img), "ocr"


def extract_pdf(path):
    chunks, modes = [], []

    with fitz.open(path) as doc:
        for page in doc:
            text, mode = extract_page_text(page)
            chunks.append(text)
            modes.append(mode)

    return (
        "\n".join(chunks).lower(),
        len(chunks),
        "+".join(sorted(set(modes)))
    )


def count_phrase(text, phrase):
    pattern = (
        r"(?<!\w)"
        + r"\s+".join(re.escape(x) for x in phrase.lower().split())
        + r"(?!\w)"
    )
    return len(re.findall(pattern, text, re.I))


def classify(text):
    scores, matches = {}, {}

    for cat, keywords in CATEGORIES.items():
        hits = [k for k in keywords if count_phrase(text, k)]
        scores[cat] = len(hits)
        matches[cat] = hits

    top = max(scores.values(), default=0)

    if top == 0:
        return "NeedsReview", scores, matches

    winners = [k for k, v in scores.items() if v == top]

    if len(winners) > 1:
        return "NeedsReview", scores, matches

    return winners[0], scores, matches


# Each worker processes one PDF independently.
# It does not copy or move files.
def process_one(pdf_path):
    path = Path(pdf_path)

    text, pages, mode = extract_pdf(path)
    category, scores, matches = classify(text)

    return {
        "source_file": str(path),
        "category": category,
        "pages": pages,
        "extraction_mode": mode,
        "extracted_characters": len(text.strip()),
        "matched_keywords": "; ".join(matches.get(category, [])),
        "status": "success",
        **{f"score_{k}": v for k, v in scores.items()}
    }


def save_progress(progress_file, completed, total, start_time, current_file=""):
    elapsed = time.time() - start_time

    percentage = completed / total * 100 if total else 100
    speed = completed / elapsed if elapsed > 0 else 0
    remaining = (total - completed) / speed if speed > 0 else 0

    width = 30
    filled = int(width * percentage / 100)
    bar = "#" * filled + "-" * (width - filled)

    content = (
        "PDF CLASSIFICATION PROGRESS\n"
        f"[{bar}] {percentage:.1f}%\n"
        f"Completed: {completed}/{total} PDFs\n"
        f"Elapsed: {elapsed / 60:.1f} minutes\n"
        f"Estimated remaining: {remaining / 60:.1f} minutes\n"
        f"Speed: {speed:.2f} PDFs/second\n"
        f"Current PDF: {current_file}\n"
    )

    temp_file = progress_file.with_suffix(".tmp")
    temp_file.write_text(content, encoding="utf-8")
    os.replace(temp_file, progress_file)


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("input_dir")
    parser.add_argument("--output", default=None)
    parser.add_argument("--move", action="store_true")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--progress-file", default=None)

    args = parser.parse_args()

    if args.workers < 1:
        parser.error("--workers must be at least 1")

    src = Path(args.input_dir).expanduser().resolve()

    if not src.is_dir():
        print(f"Input directory not found: {src}")
        return 2

    out = (
        Path(args.output).expanduser().resolve()
        if args.output
        else src / "Classified_Output"
    )

    out.mkdir(parents=True, exist_ok=True)

    for category in list(CATEGORIES) + ["NeedsReview", "Errors"]:
        (out / category).mkdir(exist_ok=True)

    progress_file = (
        Path(args.progress_file).expanduser().resolve()
        if args.progress_file
        else out / "progress.txt"
    )

    # Find input PDFs, excluding the output directory.
    pdfs = sorted(
        p for p in src.rglob("*")
        if p.is_file()
        and p.suffix.lower() == ".pdf"
        and out not in p.parents
    )

    total = len(pdfs)
    rows = []
    completed = 0
    start_time = time.time()

    print(f"\nFound {total} PDF files.")
    print(f"Workers: {args.workers}")
    print(f"Input: {src}")
    print(f"Output: {out}\n")

    save_progress(progress_file, 0, total, start_time)

    if total == 0:
        print("No PDF files found.")
        return 0

    # Only the main process writes output files and CSV records.
    with ProcessPoolExecutor(max_workers=args.workers) as executor:

        futures = {
            executor.submit(process_one, str(pdf)): pdf
            for pdf in pdfs
        }

        with tqdm(
            total=total,
            desc="Classifying PDFs",
            unit="PDF",
            dynamic_ncols=True
        ) as progress:

            for future in as_completed(futures):

                pdf = futures[future]

                try:
                    result = future.result()

                    category = result["category"]

                    dest = out / category / pdf.name
                    n = 2

                    while dest.exists():
                        dest = (
                            out / category /
                            f"{pdf.stem}_{n}{pdf.suffix}"
                        )
                        n += 1

                    (shutil.move if args.move else shutil.copy2)(
                        str(pdf), str(dest)
                    )

                    result["output_file"] = str(dest)
                    rows.append(result)

                    progress.set_postfix_str(
                        f"{category}: {pdf.name[:20]}"
                    )

                except Exception as error:

                    rows.append({
                        "source_file": str(pdf),
                        "output_file": "",
                        "category": "Errors",
                        "pages": "",
                        "extraction_mode": "",
                        "extracted_characters": "",
                        "matched_keywords": "",
                        "status": str(error)
                    })

                    progress.set_postfix_str(
                        f"ERROR: {pdf.name[:20]}"
                    )

                completed += 1
                progress.update(1)

                save_progress(
                    progress_file,
                    completed,
                    total,
                    start_time,
                    pdf.name
                )

    # Save CSV report
    if rows:
        fields = list(dict.fromkeys(
            key for row in rows for key in row
        ))

        report_path = out / "Job_Classification_Report.csv"

        with report_path.open(
            "w",
            newline="",
            encoding="utf-8-sig"
        ) as file:
            writer = csv.DictWriter(file, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)

    successful = sum(
        row["status"] == "success" for row in rows
    )
    failed = total - successful

    print("\n" + "=" * 50)
    print("CLASSIFICATION COMPLETED")
    print("=" * 50)
    print(f"Total PDFs: {total}")
    print(f"Successful: {successful}")
    print(f"Errors: {failed}")
    print(f"Output: {out}")
    print(f"Report: {out / 'Job_Classification_Report.csv'}")
    print("=" * 50)

    print("\nReview NeedsReview and verify OCR output.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
