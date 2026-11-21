IIT Delhi Economics Education-to-Career Pathways Study
======================================================

FILES
1. Economics_Education_to_Career_Study_Framework.docx
   Editable institutional research proposal and methodology.
2. Economics_Education_to_Career_Study_Framework.pdf
   Shareable PDF version.
3. Economics_Career_Research_Databases_Template.xlsx
   Structured templates for course, employer, competency, mapping and interview data.
4. classify_placement_pdfs_ocr.py
   OCR-enabled PDF text extraction and baseline keyword classification.
5. run_classifier_background.sh
   macOS background runner. Edit PDF_DIR before running.

RUN OCR CLASSIFIER (macOS)
--------------------------
brew install tesseract
python3 -m pip install pymupdf pytesseract pillow
chmod +x run_classifier_background.sh
./run_classifier_background.sh

IMPORTANT
---------
- Edit PDF_DIR in the shell script to point to your actual JNF folder.
- The classifier copies PDFs by default; it does not delete originals.
- It uses keyword matching as a transparent baseline, not an NLP/LLM-grade understanding system.
- Documents with ties or no keyword matches go to NeedsReview.
- OCR can make recognition errors. Review low-text and OCR-processed records manually.
- The eight functional categories are retained, with NeedsReview and Errors added for quality control.
- Verify course access, prerequisites and current curriculum rules from official IIT Delhi sources.
- Employer eligibility must be taken verbatim from each notification; skill similarity does not prove eligibility.
- This package is a research framework and starter toolkit, not a completed empirical report. Actual findings require the course catalogue, JNFs and stakeholder data.
