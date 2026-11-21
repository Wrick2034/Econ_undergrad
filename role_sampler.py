
import os
import re
import random
import pandas as pd
import pdfplumber
import pytesseract

# =====================================================
# 1. CONFIGURATION
# =====================================================

BASE_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "JNF_placement",
    "Placement 2023-24"
)

SAMPLE_SIZE = 4
random.seed(42)

# =====================================================
# 2. SKILL KEYWORD DICTIONARY
# =====================================================

SKILL_KEYWORDS = {
    "Machine Learning": [
        "machine learning", "random forest", "xgboost",
        "gradient boosting", "supervised learning",
        "unsupervised learning", "classification",
        "clustering", "scikit-learn"
    ],

    "Artificial Intelligence": [
        "artificial intelligence", "deep learning",
        "neural network", "generative ai",
        "natural language processing", "nlp"
    ],

    "Statistics": [
        "statistical analysis", "statistical modelling",
        "statistical modeling", "probability",
        "hypothesis testing", "statistical methods"
    ],

    "Econometrics and Regression": [
        "econometrics", "regression analysis",
        "linear regression", "logistic regression",
        "panel data", "causal inference"
    ],

    "Programming": [
        "python", "r programming", "sql", "c++",
        "java", "programming", "coding",
        "pandas", "numpy"
    ],

    "Data Analytics": [
        "data analytics", "data analysis",
        "data-driven", "data visualization",
        "business analytics", "tableau",
        "power bi", "excel"
    ],

    "Forecasting": [
        "forecasting", "time series",
        "predictive modelling", "predictive modeling",
        "demand prediction"
    ],

    "Financial Analysis": [
        "financial modelling", "financial modeling",
        "valuation", "discounted cash flow",
        "financial statements", "financial analysis",
        "due diligence", "investment analysis"
    ],

    "Research and Market Analysis": [
        "market research", "industry research",
        "research analysis", "market analysis",
        "competitive analysis"
    ],

    "Optimization": [
        "optimization", "optimisation",
        "operations research", "linear programming"
    ],

    "Communication and Consulting": [
        "stakeholder management", "client interaction",
        "client engagement", "business presentation",
        "problem solving", "problem-solving"
    ]
}

# =====================================================
# 3. COURSEWORK MAPPING
# =====================================================

COURSE_MAPPING = {
    "Machine Learning": [
        "Algorithms, Data Structures and Programming in Economics",
        "Economics Labs",
        "Relevant electives and projects"
    ],

    "Artificial Intelligence": [
        "Programming in Economics",
        "Economics Labs",
        "Relevant electives and projects"
    ],

    "Statistics": [
        "Probability and Statistics",
        "Econometrics",
        "Advanced Econometrics"
    ],

    "Econometrics and Regression": [
        "Econometrics",
        "Advanced Econometrics",
        "Economics Labs"
    ],

    "Programming": [
        "Algorithms, Data Structures and Programming in Economics",
        "Economics Labs"
    ],

    "Data Analytics": [
        "Econometrics",
        "Economics Labs",
        "Research Methods"
    ],

    "Forecasting": [
        "Time Series and Forecasting",
        "Econometrics"
    ],

    "Financial Analysis": [
        "Relevant finance electives and projects"
    ],

    "Research and Market Analysis": [
        "Research Methods",
        "Econometrics",
        "Economics Labs"
    ],

    "Optimization": [
        "Mathematics for Economics",
        "Relevant electives and projects"
    ],

    "Communication and Consulting": [
        "Research Methods",
        "Economics Labs",
        "Project-based learning"
    ]
}

# =====================================================
# 4. EXTRACT PDF TEXT WITH AUTOMATIC OCR
# =====================================================

def extract_pdf_text(pdf_path):

    all_text = []
    ocr_used = False

    try:
        with pdfplumber.open(pdf_path) as pdf:

            for page in pdf.pages:

                text = page.extract_text() or ""

                # If page has little or no extractable text,
                # use OCR on that page.
                if len(text.strip()) < 40:

                    ocr_used = True

                    image = page.to_image(
                        resolution=300
                    ).original

                    text = pytesseract.image_to_string(
                        image,
                        config="--psm 6"
                    )

                all_text.append(text)

    except Exception as e:
        print(f"Error reading {pdf_path}: {e}")

    return "\n".join(all_text), ocr_used


# =====================================================
# 5. IDENTIFY SKILLS
# =====================================================

def identify_skills(text):

    text_lower = text.lower()

    identified_skills = []

    for skill, keywords in SKILL_KEYWORDS.items():

        matched = [
            keyword for keyword in keywords
            if re.search(
                r"(?<!\w)" + re.escape(keyword) + r"(?!\w)",
                text_lower
            )
        ]

        if matched:
            identified_skills.append(skill)

    return identified_skills


# =====================================================
# 6. EXTRACT SUPPORTING EVIDENCE
# =====================================================

def extract_evidence(text, skills):

    lines = [
        re.sub(r"\s+", " ", line).strip()
        for line in text.splitlines()
        if line.strip()
    ]

    evidence = []

    for line in lines:

        line_lower = line.lower()

        for skill in skills:

            keywords = SKILL_KEYWORDS[skill]

            if any(keyword in line_lower for keyword in keywords):

                if line not in evidence:
                    evidence.append(line)

                break

    return " | ".join(evidence[:12])


# =====================================================
# 7. MAP SKILLS TO COURSEWORK
# =====================================================

def map_coursework(skills):

    courses = []

    for skill in skills:

        for course in COURSE_MAPPING.get(skill, []):

            if course not in courses:
                courses.append(course)

    return " | ".join(courses)


# =====================================================
# 8. EXTRACT COMPANY AND ROLE
# =====================================================

def extract_company_role(filename):

    name = os.path.splitext(filename)[0]

    if "(" in name and ")" in name:

        company = name.split("(")[0].strip()

        role = name.split("(", 1)[1].rsplit(")", 1)[0].strip()

    else:

        company = name
        role = "Not separately identified"

    return company, role


# =====================================================
# 9. RANDOM SAMPLING
# =====================================================

if not os.path.isdir(BASE_DIR):
    raise FileNotFoundError(
        f"Classification folder not found: {BASE_DIR}"
    )

sampled_files = []

for category in sorted(os.listdir(BASE_DIR)):

    folder_path = os.path.join(BASE_DIR, category)

    if not os.path.isdir(folder_path):
        continue

    pdf_files = []

    # Supports PDFs in nested subfolders too
    for root, dirs, files in os.walk(folder_path):

        for file in files:

            if file.lower().endswith(".pdf"):
                pdf_files.append(os.path.join(root, file))

    if not pdf_files:
        continue

    selected = random.sample(
        pdf_files,
        min(SAMPLE_SIZE, len(pdf_files))
    )

    print(f"\nProcessing category: {category}")

    for pdf_path in selected:

        file = os.path.basename(pdf_path)

        company, role = extract_company_role(file)

        print(f"  Processing: {company} - {role}")

        # Extract text
        text, ocr_used = extract_pdf_text(pdf_path)

        # Identify skills
        skills = identify_skills(text)

        # Supporting evidence
        evidence = extract_evidence(text, skills)

        # Coursework mapping
        coursework = map_coursework(skills)

        sampled_files.append({

            "Company": company,

            "Job Role": role,

            "Classification": category,

            "JNF Skills Mentioned": " | ".join(skills),

            "Supporting JNF Evidence": evidence,

            "Relevant Economics Coursework": coursework,

            "OCR Used": ocr_used

        })


# =====================================================
# 10. CREATE FINAL DATAFRAME
# =====================================================

df = pd.DataFrame(sampled_files)

columns = [
    "Company",
    "Job Role",
    "Classification",
    "JNF Skills Mentioned",
    "Supporting JNF Evidence",
    "Relevant Economics Coursework",
    "OCR Used"
]

df = df[columns]

# Display sample
print("\n\nFINAL SAMPLE")
print("=" * 80)

print(
    df[
        [
            "Company",
            "Job Role",
            "Classification",
            "JNF Skills Mentioned"
        ]
    ].to_string(index=False)
)

# Save CSV
output_path = os.path.join(
    BASE_DIR,
    "Random_Sample_Companies.csv"
)

df.to_csv(
    output_path,
    index=False,
    encoding="utf-8-sig"
)

print("\n" + "=" * 80)
print("Total sampled companies:", len(df))
print("Saved at:", output_path)
