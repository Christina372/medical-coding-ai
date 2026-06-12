from flask import Flask, render_template, request, send_file
import pandas as pd
import sqlite3
import os
from datetime import datetime
from reportlab.pdfgen import canvas

app = Flask(__name__)

# =====================================
# CREATE FOLDERS
# =====================================

os.makedirs("database", exist_ok=True)
os.makedirs("reports", exist_ok=True)

# =====================================
# SQLITE DATABASE
# =====================================

conn = sqlite3.connect(
    "medical_codes.db",
    check_same_thread=False
)

cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS coding_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient TEXT,
    diagnosis TEXT,
    procedure TEXT,
    icd TEXT,
    cpt TEXT
)
""")

conn.commit()

# =====================================
# LOAD ICD & CPT FILES
# =====================================

icd_data = pd.read_csv(
    "database/icd_codes.csv"
)

cpt_data = pd.read_csv(
    "database/cpt_codes.csv"
)

latest_report = {}

# =====================================
# HOME PAGE
# =====================================

@app.route("/")
def home():
    return render_template(
        "index.html"
    )

# =====================================
# GENERATE MEDICAL CODES
# =====================================

@app.route(
    "/predict",
    methods=["POST"]
)
def predict():

    global latest_report

    patient = request.form["patient"]

    diagnosis = request.form[
        "diagnosis"
    ].strip().lower()

    procedure = request.form[
        "procedure"
    ].strip().lower()

    # ICD MATCH

    icd_match = icd_data[
        icd_data["Diagnosis"]
        .str.lower()
        == diagnosis
    ]

    if not icd_match.empty:
        icd_code = icd_match.iloc[0]["ICD"]
    else:
        icd_code = "ICD Not Found"

    # CPT MATCH

    cpt_match = cpt_data[
        cpt_data["Procedure"]
        .str.lower()
        == procedure
    ]

    if not cpt_match.empty:
        cpt_code = cpt_match.iloc[0]["CPT"]
    else:
        cpt_code = "CPT Not Found"

    # SAVE TO DATABASE

    cursor.execute(
        """
        INSERT INTO coding_history
        (
        patient,
        diagnosis,
        procedure,
        icd,
        cpt
        )
        VALUES
        (?,?,?,?,?)
        """,
        (
            patient,
            diagnosis,
            procedure,
            icd_code,
            cpt_code
        )
    )

    conn.commit()

    # STORE REPORT

    latest_report = {
        "patient": patient,
        "diagnosis": diagnosis,
        "procedure": procedure,
        "icd": icd_code,
        "cpt": cpt_code
    }

    return render_template(
        "result.html",
        patient=patient,
        diagnosis=diagnosis,
        procedure=procedure,
        icd=icd_code,
        cpt=cpt_code
    )

# =====================================
# DASHBOARD
# =====================================

@app.route("/dashboard")
def dashboard():

    query = """
    SELECT *
    FROM coding_history
    ORDER BY id DESC
    """

    history = pd.read_sql_query(
        query,
        conn
    )

    print(history)

    records = history.to_dict(
        orient="records"
    )

    total_reports = len(
        history
    )

    total_icd = len(
        icd_data
    )

    total_cpt = len(
        cpt_data
    )

    return render_template(
        "dashboard.html",
        records=records,
        total_reports=total_reports,
        total_icd=total_icd,
        total_cpt=total_cpt
    )

# =====================================
# PDF DOWNLOAD
# =====================================

@app.route("/download_pdf")
def download_pdf():

    pdf_file = (
        "reports/medical_report.pdf"
    )

    c = canvas.Canvas(
        pdf_file
    )

    c.setFont(
        "Helvetica-Bold",
        18
    )

    c.drawString(
        180,
        800,
        "Medical Coding Report"
    )

    c.setFont(
        "Helvetica",
        12
    )

    c.drawString(
        50,
        740,
        f"Patient: {latest_report.get('patient','')}"
    )

    c.drawString(
        50,
        710,
        f"Diagnosis: {latest_report.get('diagnosis','')}"
    )

    c.drawString(
        50,
        680,
        f"Procedure: {latest_report.get('procedure','')}"
    )

    c.drawString(
        50,
        650,
        f"ICD Code: {latest_report.get('icd','')}"
    )

    c.drawString(
        50,
        620,
        f"CPT Code: {latest_report.get('cpt','')}"
    )

    c.drawString(
        50,
        590,
        f"Generated On: {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}"
    )

    c.save()

    return send_file(
        pdf_file,
        as_attachment=True
    )

# =====================================
# RUN APPLICATION
# =====================================

if __name__ == "__main__":
    app.run(
        debug=True
    )