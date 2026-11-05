"""Mock Longitudinal EHR Database for demonstrating Agentic Pre-Chart Summarization.

Contains multi-year clinical records across 5 EHR domains:
1. Demographics, Active Problems, Allergies & Today's Visit Context
2. Hospitalizations, ED Visits & Specialist Clinical Notes
3. Longitudinal Medication History, Discharge Changes & Pharmacy Dispense Status
4. Longitudinal Lab Panels & Diagnostic Imaging Reports
5. Unresolved Clinical Trackers, Unreviewed Results & Preventive Care Gaps
"""

from typing import Any, Dict

MOCK_EHR_DB: Dict[str, Dict[str, Any]] = {
    "PAT-1001": {
        "demographics": {
            "patient_id": "PAT-1001",
            "name": "Arthur Pendelton",
            "dob": "1958-03-14",
            "age": 68,
            "sex": "Male",
            "primary_care_physician": "Dr. Sarah Chen, MD",
            "allergies": [
                {"substance": "Penicillin", "reaction": "Anaphylaxis (hives, airway swelling)", "severity": "Severe"},
                {"substance": "Contrast Dye (Iodinated)", "reaction": "Mild urticaria", "severity": "Moderate"},
            ],
            "active_problem_list": [
                {"icd10": "I50.22", "condition": "Chronic systolic (congestive) heart failure (HFrEF, EF 35%)", "onset": "2022-06"},
                {"icd10": "N18.32", "condition": "Chronic kidney disease, stage 3b (baseline Cr ~1.4 mg/dL)", "onset": "2023-01"},
                {"icd10": "E11.22", "condition": "Type 2 diabetes mellitus with diabetic chronic kidney disease", "onset": "2018-09"},
                {"icd10": "I48.91", "condition": "Paroxysmal atrial fibrillation", "onset": "2023-11"},
                {"icd10": "I10", "condition": "Essential hypertension", "onset": "2015-04"},
            ],
        },
        "todays_visit": {
            "visit_date": "2026-11-04",
            "appointment_type": "Primary Care Post-Hospitalization / Follow-up",
            "chief_complaint": "Increasing shortness of breath on exertion and bilateral ankle swelling over the past 5 days.",
            "triage_vitals_today": {
                "bp": "148/90 mmHg",
                "hr": "88 bpm (irregularly irregular)",
                "rr": "20 /min",
                "spo2": "93% on room air",
                "temp": "98.4 F",
                "weight_lbs": 191.5,
                "bmi": 29.8,
                "ma_intake_note": (
                    "Patient states he feels winded walking from the parking lot. "
                    "2+ pitting edema noted up to mid-shins bilaterally. Brought pill bottles; "
                    "admits he reduced his water pill back to 1 pill a day last week because it made him "
                    "urinate too frequently. Also states the pharmacy wanted $180 for the new diabetes/heart "
                    "pill prescribed in the hospital so he never picked it up."
                ),
            },
        },
        "encounters_and_notes": [
            {
                "encounter_id": "ENC-9042",
                "date": "2026-10-10 to 2026-10-14",
                "type": "Inpatient Hospitalization (Discharge Summary)",
                "facility": "Mercy General Hospital",
                "author": "Dr. Kevin Patel, MD (Hospitalist)",
                "primary_diagnosis": "Acute on Chronic Systolic Heart Failure Exacerbation (ADHF); Acute Kidney Injury (AKI) on Stage 3b CKD",
                "summary_note": (
                    "68M with HFrEF (EF 35%), AFib on Apixaban, T2DM, and Stage 3b CKD admitted 10/10/2026 "
                    "with dyspnea, orthopnea, and 12-lb weight gain (admission weight 196 lbs). "
                    "NT-proBNP on admission was 4,420 pg/mL. Creatinine on admission was elevated at 2.3 mg/dL "
                    "(baseline 1.4 mg/dL), attributed to cardiorenal syndrome. "
                    "Hospital Course: Diuresed aggressively with IV Furosemide with 5.5L net negative fluid balance; "
                    "discharge weight 184.0 lbs. Creatinine improved to 1.75 mg/dL at discharge. "
                    "Lisinopril 20mg and Metformin 1000mg BID were HELD during admission due to AKI. "
                    "Initiated Empagliflozin (Jardiance) 10mg daily for HFrEF/CKD/T2DM benefit. "
                    "Discharged on Furosemide 40mg PO BID for 7 days, then instructed to step down to 40mg PO daily. "
                    "Incidental Finding on Admission CT Chest (10/10/2026): 7mm solid non-calcified pulmonary nodule "
                    "in the right upper lobe (RUL). Radiology recommends 6-month follow-up low-dose CT chest (April 2027) "
                    "per Fleischner Society high-risk guidelines."
                ),
            },
            {
                "encounter_id": "ENC-9045",
                "date": "2026-10-13",
                "type": "Inpatient Cardiology Consult Note",
                "facility": "Mercy General Hospital",
                "author": "Dr. Elena Vance, MD (Cardiology)",
                "primary_diagnosis": "HFrEF Optimization & GDMT Plan",
                "summary_note": (
                    "Transthoracic Echocardiogram (10/12/2026) shows LVEF 30-35% (unchanged from 2024), "
                    "moderate mitral regurgitation, and mildly dilated RV. "
                    "Recommendations for Outpatient PCP / Cardiology Follow-up:\n"
                    "1. Keep Lisinopril HELD until outpatient BMP shows serum creatinine < 1.6 mg/dL and K+ < 5.0.\n"
                    "2. Once renal function returns to baseline (Cr < 1.6), strongly recommend transitioning from "
                    "Lisinopril to Sacubitril/Valsartan (Entresto) 24/26mg BID (ensure 36-hour washout if ACEi was taken) "
                    "or at minimum restarting ACEi.\n"
                    "3. Continue Carvedilol 25mg BID and Apixaban 5mg BID.\n"
                    "4. Start Empagliflozin 10mg PO daily.\n"
                    "5. Patient scheduled for Heart Failure Clinic follow-up on 2026-10-24."
                ),
            },
            {
                "encounter_id": "ENC-8810",
                "date": "2026-05-19",
                "type": "Outpatient Primary Care Progress Note",
                "facility": "Valley Internal Medicine",
                "author": "Dr. Sarah Chen, MD",
                "primary_diagnosis": "Routine Chronic Disease Management (HFrEF, CKD3b, T2DM)",
                "summary_note": (
                    "Patient clinically euvolemic, weight 183 lbs, BP 124/76. "
                    "Baseline Creatinine 1.4 mg/dL (eGFR 52), HbA1c 7.1%, K+ 4.4 mEq/L. "
                    "Stable on Furosemide 20mg daily, Lisinopril 20mg daily, Carvedilol 25mg BID, "
                    "Metformin 1000mg BID, Apixaban 5mg BID."
                ),
            },
            {
                "encounter_id": "ENC-7402",
                "date": "2024-08-12",
                "type": "Outpatient Pulmonology / Smoking History Note",
                "facility": "Valley Pulmonary Associates",
                "author": "Dr. Marcus Reed, MD",
                "primary_diagnosis": "Former 35-pack-year smoker (quit 2019)",
                "summary_note": (
                    "PFTs show mild airflow obstruction (FEV1/FVC 0.68, FEV1 78% predicted). "
                    "High-risk former smoker; eligible for annual lung cancer screening."
                ),
            },
        ],
        "medications": {
            "active_prescriptions": [
                {
                    "medication": "Furosemide (Lasix)",
                    "prescribed_dose": "40 mg PO BID x7 days (10/14-10/21), then 40 mg PO daily",
                    "previous_dose": "20 mg PO daily (prior to 10/10/2026 admission)",
                    "change_type": "DOSE INCREASED at hospital discharge (10/14/2026)",
                    "actual_patient_adherence": "NON-ADHERENT: Patient self-reduced back to 20 mg PO daily on 10/26/2026 due to urinary frequency.",
                },
                {
                    "medication": "Empagliflozin (Jardiance)",
                    "prescribed_dose": "10 mg PO daily",
                    "previous_dose": "None",
                    "change_type": "NEW START at hospital discharge (10/14/2026) for HFrEF/T2DM/CKD",
                    "actual_patient_adherence": "NEVER STARTED: Pharmacy claim rejected on 10/15/2026 (Prior Authorization required by payer; $180 copay quoted). Prescription still sitting at pharmacy.",
                },
                {
                    "medication": "Carvedilol (Coreg)",
                    "prescribed_dose": "25 mg PO BID",
                    "previous_dose": "25 mg PO BID",
                    "change_type": "UNCHANGED",
                    "actual_patient_adherence": "Adherent (last refill picked up 10/02/2026)",
                },
                {
                    "medication": "Apixaban (Eliquis)",
                    "prescribed_dose": "5 mg PO BID",
                    "previous_dose": "5 mg PO BID",
                    "change_type": "UNCHANGED",
                    "actual_patient_adherence": "Adherent (last refill picked up 10/02/2026)",
                },
                {
                    "medication": "Atorvastatin (Lipitor)",
                    "prescribed_dose": "40 mg PO nightly",
                    "previous_dose": "40 mg PO nightly",
                    "change_type": "UNCHANGED",
                    "actual_patient_adherence": "Adherent",
                },
            ],
            "held_or_discontinued_medications": [
                {
                    "medication": "Lisinopril",
                    "prior_dose": "20 mg PO daily",
                    "status": "HELD on 2026-10-10 during hospital admission",
                    "reason": "Acute Kidney Injury (Cr peaked at 2.3 mg/dL).",
                    "reinitiation_criteria": "Cardiology recommended restarting ACEi or switching to Sacubitril/Valsartan (Entresto) once outpatient Creatinine < 1.6 mg/dL and K+ < 5.0.",
                },
                {
                    "medication": "Metformin",
                    "prior_dose": "1000 mg PO BID",
                    "status": "HELD on 2026-10-10 during hospital admission",
                    "reason": "Held due to acute renal dysfunction (eGFR dropped to 29 mL/min) and IV contrast administration.",
                    "reinitiation_criteria": "Safe to resume at reduced or full dose once eGFR > 45 mL/min/1.73m2.",
                },
            ],
        },
        "labs_and_diagnostics": {
            "longitudinal_labs": [
                {
                    "test": "Serum Creatinine (mg/dL)",
                    "ref_range": "0.7 - 1.3",
                    "history": [
                        {"date": "2026-05-19", "value": 1.40, "flag": "H", "context": "Outpatient Baseline"},
                        {"date": "2026-10-10", "value": 2.30, "flag": "HH (Critical)", "context": "Hospital Admission (AKI)"},
                        {"date": "2026-10-14", "value": 1.75, "flag": "H", "context": "Hospital Discharge"},
                        {"date": "2026-11-02", "value": 1.50, "flag": "H", "context": "Outpatient Pre-Visit Lab (2 days ago)"},
                    ],
                },
                {
                    "test": "eGFR (mL/min/1.73m2)",
                    "ref_range": "> 60",
                    "history": [
                        {"date": "2026-05-19", "value": 52, "flag": "L", "context": "Outpatient Baseline"},
                        {"date": "2026-10-10", "value": 29, "flag": "LL", "context": "Hospital Admission"},
                        {"date": "2026-10-14", "value": 40, "flag": "L", "context": "Hospital Discharge"},
                        {"date": "2026-11-02", "value": 48, "flag": "L", "context": "Outpatient Pre-Visit Lab (2 days ago)"},
                    ],
                },
                {
                    "test": "NT-proBNP (pg/mL)",
                    "ref_range": "< 125",
                    "history": [
                        {"date": "2026-05-19", "value": 640, "flag": "H", "context": "Outpatient Baseline"},
                        {"date": "2026-10-10", "value": 4420, "flag": "HH", "context": "Hospital Admission"},
                        {"date": "2026-10-14", "value": 920, "flag": "H", "context": "Hospital Discharge"},
                        {"date": "2026-11-02", "value": 1850, "flag": "HH", "context": "Outpatient Pre-Visit Lab (re-elevated!)"},
                    ],
                },
                {
                    "test": "Potassium (mEq/L)",
                    "ref_range": "3.5 - 5.1",
                    "history": [
                        {"date": "2026-05-19", "value": 4.4, "flag": "N", "context": "Outpatient Baseline"},
                        {"date": "2026-10-10", "value": 5.3, "flag": "H", "context": "Hospital Admission"},
                        {"date": "2026-10-14", "value": 4.1, "flag": "N", "context": "Hospital Discharge"},
                        {"date": "2026-11-02", "value": 4.2, "flag": "N", "context": "Outpatient Pre-Visit Lab"},
                    ],
                },
                {
                    "test": "Hemoglobin A1c (%)",
                    "ref_range": "< 5.7",
                    "history": [
                        {"date": "2026-01-12", "value": 6.9, "flag": "H", "context": "Outpatient"},
                        {"date": "2026-05-19", "value": 7.1, "flag": "H", "context": "Outpatient"},
                        {"date": "2026-11-02", "value": 7.9, "flag": "H", "context": "Outpatient Pre-Visit Lab (worsened while Metformin held & Jardiance not started)"},
                    ],
                },
            ],
            "imaging_and_procedures": [
                {
                    "date": "2026-10-12",
                    "modality": "Transthoracic Echocardiogram (TTE)",
                    "findings": "LVEF 30-35%, global hypokinesis, moderate functional mitral regurgitation, RVSP 42 mmHg.",
                },
                {
                    "date": "2026-10-10",
                    "modality": "CT Chest without Contrast",
                    "findings": (
                        "Bilateral pleural effusions (small) and interstitial pulmonary edema. "
                        "INCIDENTAL FINDING: 7mm solid non-calcified nodule in the right upper lobe (RUL, series 4, image 42). "
                        "Impression: In a patient with >30 pack-year smoking history, recommend 6-month follow-up CT chest "
                        "(due April 2027) per Fleischner guidelines."
                    ),
                },
            ],
        },
        "unresolved_items_and_care_gaps": [
            {
                "item_id": "OPEN-101",
                "category": "Early Volume Overload / Re-hospitalization Risk",
                "priority": "CRITICAL",
                "details": (
                    "Patient gained 7.5 lbs since hospital discharge (184.0 -> 191.5 lbs), NT-proBNP doubled "
                    "(920 -> 1,850 pg/mL), and he self-reduced Furosemide from 40mg daily to 20mg daily while "
                    "never starting Empagliflozin due to a Prior Authorization block."
                ),
            },
            {
                "item_id": "OPEN-102",
                "category": "Held Medications Ready for Re-evaluation (Renal Recovery)",
                "priority": "HIGH",
                "details": (
                    "Outpatient Creatinine improved to 1.50 mg/dL (eGFR 48) and K+ is 4.2 mEq/L on 2026-11-02. "
                    "Meets Cardiology criteria (Cr < 1.6) to restart RAAS inhibition (Lisinopril or switch to Entresto) "
                    "to control rising BP (148/90) and remodel HFrEF, AND meets criteria (eGFR > 45) to resume Metformin."
                ),
            },
            {
                "item_id": "OPEN-103",
                "category": "Unordered Incidental Imaging Follow-Up",
                "priority": "HIGH",
                "details": (
                    "7mm RUL solid pulmonary nodule discovered on 2026-10-10 hospital CT Chest in a 35-pack-year "
                    "former smoker. 6-month follow-up CT Chest (for April 2027) has NOT been ordered or added to problem list."
                ),
            },
            {
                "item_id": "OPEN-104",
                "category": "Missed Specialty Appointment",
                "priority": "MEDIUM",
                "details": "Patient No-Showed to scheduled Heart Failure Clinic appointment on 2026-10-24 (transportation issue).",
            },
            {
                "item_id": "OPEN-105",
                "category": "Preventive Care Gap",
                "priority": "LOW",
                "details": "Diabetic retinal exam overdue (last completed 2024-09-15) and annual Influenza/RSV vaccination due.",
            },
        ],
    },
    "PAT-1002": {
        "demographics": {
            "patient_id": "PAT-1002",
            "name": "Elena Rostova",
            "dob": "1972-07-22",
            "age": 54,
            "sex": "Female",
            "primary_care_physician": "Dr. Sarah Chen, MD",
            "allergies": [
                {"substance": "Sulfa Antibiotics (TMP-SMX)", "reaction": "Maculopapular rash", "severity": "Moderate"},
            ],
            "active_problem_list": [
                {"icd10": "M05.79", "condition": "Seropositive rheumatoid arthritis", "onset": "2021-03"},
                {"icd10": "E03.9", "condition": "Hypothyroidism", "onset": "2019-11"},
                {"icd10": "K29.70", "condition": "NSAID-induced gastritis without bleeding", "onset": "2026-09"},
                {"icd10": "D50.9", "condition": "Iron deficiency anemia", "onset": "2026-09"},
            ],
        },
        "todays_visit": {
            "visit_date": "2026-11-04",
            "appointment_type": "Primary Care Follow-up",
            "chief_complaint": "Persistent fatigue, mild nausea, morning hand stiffness, and reviewing recent lab results.",
            "triage_vitals_today": {
                "bp": "118/74 mmHg",
                "hr": "76 bpm",
                "rr": "14 /min",
                "spo2": "99% on room air",
                "temp": "98.1 F",
                "weight_lbs": 142.0,
                "bmi": 23.6,
                "ma_intake_note": (
                    "Patient reports feeling exhausted all day and mildly nauseous for the last 2 weeks since "
                    "increasing her weekly Methotrexate dose. Epigastric burning has improved on Pantoprazole."
                ),
            },
        },
        "encounters_and_notes": [
            {
                "encounter_id": "ENC-9110",
                "date": "2026-10-05",
                "type": "Outpatient Rheumatology Consult Note",
                "facility": "Metro Rheumatology",
                "author": "Dr. Priya Nair, MD (Rheumatology)",
                "primary_diagnosis": "Active Seropositive Rheumatoid Arthritis Flare",
                "summary_note": (
                    "54F with active synovitis in bilateral MCP/PIP joints following discontinuation of NSAIDs. "
                    "Plan: Increase Methotrexate from 15mg PO weekly to 20mg PO weekly + Folic Acid 1mg daily. "
                    "Prescribed 21-day Prednisone taper (completed 10/26/2026). "
                    "Plan to add Adalimumab (Humira) 40mg SC every 2 weeks once infectious screening labs "
                    "(QuantiFERON-TB Gold and Hepatitis B/C panel) are confirmed negative. Ordered CMP, CBC in 4 weeks."
                ),
            },
            {
                "encounter_id": "ENC-8990",
                "date": "2026-09-18",
                "type": "Emergency Department Visit Note",
                "facility": "Mercy General Hospital ED",
                "author": "Dr. Thomas Wright, MD (Emergency Medicine)",
                "primary_diagnosis": "Acute NSAID-Induced Gastritis; Microcytic Anemia",
                "summary_note": (
                    "Presented with 1 week of sharp epigastric pain and dark stools after taking OTC Ibuprofen "
                    "600mg TID for 3 weeks for RA flare. Hemoglobin 9.8 g/dL (down from 12.4 in April), Ferritin 12 ng/mL. "
                    "Rectal exam hemoccult borderline positive, no brisk GI bleed. "
                    "Discharged on Pantoprazole 40mg PO daily, Oral Ferrous Sulfate 325mg every other day, "
                    "strictly instructed to avoid all NSAIDs. "
                    "Discharge Recommendation: PCP to order H. pylori stool antigen test (after 2-week PPI washout or serology) "
                    "and refer to Gastroenterology for outpatient EGD to rule out peptic ulcer disease."
                ),
            },
        ],
        "medications": {
            "active_prescriptions": [
                {
                    "medication": "Methotrexate",
                    "prescribed_dose": "20 mg PO once weekly",
                    "previous_dose": "15 mg PO once weekly",
                    "change_type": "DOSE INCREASED by Rheumatology on 2026-10-05",
                    "actual_patient_adherence": "Adherent (experiencing new nausea and transaminitis)",
                },
                {
                    "medication": "Pantoprazole (Protonix)",
                    "prescribed_dose": "40 mg PO daily",
                    "previous_dose": "None",
                    "change_type": "NEW START at ED discharge on 2026-09-18",
                    "actual_patient_adherence": "Adherent",
                },
                {
                    "medication": "Ferrous Sulfate",
                    "prescribed_dose": "325 mg PO every other day",
                    "previous_dose": "None",
                    "change_type": "NEW START at ED discharge on 2026-09-18",
                    "actual_patient_adherence": "Adherent",
                },
                {
                    "medication": "Levothyroxine (Synthroid)",
                    "prescribed_dose": "75 mcg PO daily",
                    "previous_dose": "75 mcg PO daily",
                    "change_type": "UNCHANGED (Note: taking concurrently with morning Ferrous Sulfate!)",
                    "actual_patient_adherence": "Takes at 7 AM alongside iron supplement (causes malabsorption!)",
                },
                {
                    "medication": "Folic Acid",
                    "prescribed_dose": "1 mg PO daily",
                    "previous_dose": "1 mg PO daily",
                    "change_type": "UNCHANGED",
                    "actual_patient_adherence": "Adherent",
                },
            ],
            "held_or_discontinued_medications": [
                {
                    "medication": "Ibuprofen (OTC)",
                    "prior_dose": "600 mg PO TID",
                    "status": "DISCONTINUED permanently on 2026-09-18",
                    "reason": "NSAID-induced gastritis and GI blood loss anemia.",
                    "reinitiation_criteria": "Contraindicated.",
                },
                {
                    "medication": "Prednisone",
                    "prior_dose": "15 mg taper over 21 days",
                    "status": "COMPLETED course on 2026-10-26",
                    "reason": "Bridge therapy for RA flare.",
                    "reinitiation_criteria": "Completed as scheduled.",
                },
            ],
        },
        "labs_and_diagnostics": {
            "longitudinal_labs": [
                {
                    "test": "ALT (U/L)",
                    "ref_range": "7 - 35",
                    "history": [
                        {"date": "2026-04-10", "value": 19, "flag": "N", "context": "Baseline on MTX 15mg"},
                        {"date": "2026-09-18", "value": 24, "flag": "N", "context": "ED Visit"},
                        {"date": "2026-11-01", "value": 92, "flag": "HH (>2.5x ULN)", "context": "4 weeks after MTX increase to 20mg"},
                    ],
                },
                {
                    "test": "AST (U/L)",
                    "ref_range": "8 - 33",
                    "history": [
                        {"date": "2026-04-10", "value": 22, "flag": "N", "context": "Baseline on MTX 15mg"},
                        {"date": "2026-09-18", "value": 25, "flag": "N", "context": "ED Visit"},
                        {"date": "2026-11-01", "value": 78, "flag": "HH (>2x ULN)", "context": "4 weeks after MTX increase to 20mg"},
                    ],
                },
                {
                    "test": "TSH (mIU/L)",
                    "ref_range": "0.45 - 4.50",
                    "history": [
                        {"date": "2026-04-10", "value": 2.4, "flag": "N", "context": "Outpatient"},
                        {"date": "2026-11-01", "value": 6.8, "flag": "H", "context": "Elevated since starting oral Iron (malabsorption interaction)"},
                    ],
                },
                {
                    "test": "Hemoglobin (g/dL)",
                    "ref_range": "12.0 - 16.0",
                    "history": [
                        {"date": "2026-04-10", "value": 12.4, "flag": "N", "context": "Outpatient"},
                        {"date": "2026-09-18", "value": 9.8, "flag": "L", "context": "ED Visit (Gastritis)"},
                        {"date": "2026-11-01", "value": 10.9, "flag": "L", "context": "Improving on oral iron + PPI"},
                    ],
                },
                {
                    "test": "QuantiFERON-TB Gold Plus",
                    "ref_range": "Negative",
                    "history": [
                        {
                            "date": "2026-10-12",
                            "value": "INDETERMINATE (Low Mitogen Response, likely due to Prednisone)",
                            "flag": "ABNORMAL",
                            "context": "Pre-biologic screening for Adalimumab (Humira)",
                        },
                    ],
                },
            ],
            "imaging_and_procedures": [],
        },
        "unresolved_items_and_care_gaps": [
            {
                "item_id": "OPEN-201",
                "category": "Drug-Induced Hepatotoxicity (Methotrexate)",
                "priority": "CRITICAL",
                "details": (
                    "ALT jumped from 24 -> 92 U/L and AST from 25 -> 78 U/L on 2026-11-01 following Methotrexate "
                    "increase to 20mg/week, accompanied by nausea. Needs dose reduction/hold and Folic Acid increase "
                    "in coordination with Rheumatology."
                ),
            },
            {
                "item_id": "OPEN-202",
                "category": "Drug-Drug Absorption Interaction (Levothyroxine + Iron)",
                "priority": "HIGH",
                "details": (
                    "TSH rose from 2.4 -> 6.8 mIU/L (contributing to fatigue) after starting Ferrous Sulfate on 9/18. "
                    "Patient is taking iron at the same time as morning Levothyroxine, chelating thyroid hormone absorption. "
                    "Needs counseling to separate by >= 4 hours before increasing Levothyroxine dose."
                ),
            },
            {
                "item_id": "OPEN-203",
                "category": "Unresolved Pre-Biologic TB Screening",
                "priority": "HIGH",
                "details": (
                    "QuantiFERON-TB Gold resulted 'Indeterminate' on 10/12 (while on Prednisone). "
                    "Adalimumab (Humira) initiation is stalled until repeat TB test (now off steroids) or Chest X-ray is ordered."
                ),
            },
            {
                "item_id": "OPEN-204",
                "category": "Uncompleted ED Follow-Up Referral (GI / EGD)",
                "priority": "MEDIUM",
                "details": "ED discharge (9/18) recommended Gastroenterology referral for EGD to evaluate iron deficiency anemia / gastritis; referral not yet placed.",
            },
        ],
    },
    "PAT-1003": {
        "demographics": {
            "patient_id": "PAT-1003",
            "name": "Marcus Vance",
            "dob": "1984-02-10",
            "age": 42,
            "sex": "Male",
            "primary_care_physician": "Dr. Sarah Chen, MD",
            "allergies": [{"substance": "No Known Drug Allergies (NKDA)", "reaction": "None", "severity": "None"}],
            "active_problem_list": [
                {"icd10": "I10", "condition": "Resistant essential hypertension", "onset": "2023-05"},
                {"icd10": "E87.6", "condition": "Hypokalemia", "onset": "2025-11"},
                {"icd10": "G47.33", "condition": "Obstructive sleep apnea", "onset": "2024-02"},
            ],
        },
        "todays_visit": {
            "visit_date": "2026-11-04",
            "appointment_type": "Post-ED Hospital Follow-up",
            "chief_complaint": "Follow-up after ER visit 4 days ago for blood pressure 210/118 and severe occipital headache.",
            "triage_vitals_today": {
                "bp": "168/102 mmHg",
                "hr": "78 bpm",
                "rr": "16 /min",
                "spo2": "98% on room air",
                "temp": "98.6 F",
                "weight_lbs": 210.0,
                "bmi": 30.1,
                "ma_intake_note": (
                    "Headache is mild today (2/10), but patient complains of muscle cramps in his calves "
                    "and generalized weakness over the last 2 days after starting the new water pill (Chlorthalidone) "
                    "from the ER."
                ),
            },
        },
        "encounters_and_notes": [
            {
                "encounter_id": "ENC-9201",
                "date": "2026-10-31",
                "type": "Emergency Department Visit Note",
                "facility": "Mercy General Hospital ED",
                "author": "Dr. Hannah Kim, MD (Emergency Medicine)",
                "primary_diagnosis": "Hypertensive Urgency; Hypokalemia",
                "summary_note": (
                    "42M presented with throbbing occipital headache and home BP 210/118 mmHg despite compliance "
                    "with Lisinopril 40mg daily and Amlodipine 5mg daily. "
                    "CT Head without contrast negative for acute hemorrhage or mass. Troponin normal, Cr 0.9 mg/dL. "
                    "ED BMP notable for Potassium 3.2 mEq/L (given 40 mEq PO KCl in ED). "
                    "BP improved to 164/96 after oral clonidine and Amlodipine 10mg. "
                    "Discharged on increased Amlodipine 10mg daily, continued Lisinopril 40mg daily, and ADDED "
                    "Chlorthalidone 25mg PO daily. Follow up with PCP in 3-5 days for BP and electrolyte check."
                ),
            },
            {
                "encounter_id": "ENC-8650",
                "date": "2026-08-14",
                "type": "Outpatient Hypertension Workup Note",
                "facility": "Valley Internal Medicine",
                "author": "Dr. Sarah Chen, MD",
                "primary_diagnosis": "Secondary Hypertension Workup in Young Adult",
                "summary_note": (
                    "42M with persistent BP 165/104 on two agents and borderline low potassium (3.5 mEq/L) "
                    "despite not taking any diuretics. Ordered morning Plasma Aldosterone Concentration (PAC) "
                    "and Direct Renin Activity to screen for Primary Hyperaldosteronism."
                ),
            },
        ],
        "medications": {
            "active_prescriptions": [
                {
                    "medication": "Chlorthalidone",
                    "prescribed_dose": "25 mg PO daily",
                    "previous_dose": "None",
                    "change_type": "NEW START at ED discharge (2026-10-31)",
                    "actual_patient_adherence": "Adherent for 4 days (now experiencing calf cramps/weakness — high risk of severe hypokalemia!)",
                },
                {
                    "medication": "Amlodipine (Norvasc)",
                    "prescribed_dose": "10 mg PO daily",
                    "previous_dose": "5 mg PO daily",
                    "change_type": "DOSE INCREASED at ED discharge (2026-10-31)",
                    "actual_patient_adherence": "Adherent",
                },
                {
                    "medication": "Lisinopril",
                    "prescribed_dose": "40 mg PO daily",
                    "previous_dose": "40 mg PO daily",
                    "change_type": "UNCHANGED",
                    "actual_patient_adherence": "Adherent",
                },
            ],
            "held_or_discontinued_medications": [],
        },
        "labs_and_diagnostics": {
            "longitudinal_labs": [
                {
                    "test": "Potassium (mEq/L)",
                    "ref_range": "3.5 - 5.1",
                    "history": [
                        {"date": "2025-11-10", "value": 3.4, "flag": "L", "context": "Outpatient (not on diuretics)"},
                        {"date": "2026-08-14", "value": 3.5, "flag": "N (Borderline Low)", "context": "Outpatient"},
                        {"date": "2026-10-31", "value": 3.2, "flag": "LL", "context": "ED Visit (PRIOR to Chlorthalidone start!)"},
                    ],
                },
                {
                    "test": "Plasma Aldosterone Concentration (ng/dL)",
                    "ref_range": "4.0 - 21.0",
                    "history": [
                        {"date": "2026-08-18", "value": 28.5, "flag": "HH", "context": "Secondary HTN Screen (UNREVIEWED)"},
                    ],
                },
                {
                    "test": "Plasma Renin Activity (ng/mL/hr)",
                    "ref_range": "0.6 - 4.3",
                    "history": [
                        {"date": "2026-08-18", "value": 0.3, "flag": "LL (Suppressed)", "context": "Secondary HTN Screen (UNREVIEWED)"},
                    ],
                },
                {
                    "test": "Aldosterone-to-Renin Ratio (ARR)",
                    "ref_range": "< 20",
                    "history": [
                        {"date": "2026-08-18", "value": 95.0, "flag": "CRITICAL HIGH (Diagnostic threshold > 30)", "context": "Strongly positive for Primary Hyperaldosteronism (Conn's Syndrome)"},
                    ],
                },
            ],
            "imaging_and_procedures": [
                {
                    "date": "2026-10-31",
                    "modality": "CT Head without Contrast",
                    "findings": "No acute intracranial hemorrhage, mass effect, or territorial infarction.",
                },
            ],
        },
        "unresolved_items_and_care_gaps": [
            {
                "item_id": "OPEN-301",
                "category": "CRITICAL Medication Safety Alert (Chlorthalidone + Hypokalemia)",
                "priority": "CRITICAL",
                "details": (
                    "ED started Chlorthalidone 25mg daily on 10/31 despite baseline hypokalemia (K+ 3.2 mEq/L). "
                    "Patient now has calf cramps and weakness today — requires immediate STAT BMP/Potassium check "
                    "and discontinuation of Chlorthalidone."
                ),
            },
            {
                "item_id": "OPEN-302",
                "category": "Unreviewed Diagnostic Lab (Primary Hyperaldosteronism)",
                "priority": "CRITICAL",
                "details": (
                    "Send-out lab from 2026-08-18 resulted with Aldosterone 28.5 ng/dL, Renin 0.3 ng/mL/hr, "
                    "ARR = 95 (diagnostic for Primary Hyperaldosteronism), which explains both resistant HTN "
                    "and spontaneous hypokalemia. Needs Adrenal CT protocol, Endocrine referral, and transition "
                    "to a mineralocorticoid receptor antagonist (Spironolactone or Eplerenone)."
                ),
            },
        ],
    },
}
