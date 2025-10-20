import streamlit as st
import boto3
import json
from PyPDF2 import PdfReader
from fpdf import FPDF
from io import BytesIO

import streamlit as st

# ---------------- Hide default stream lit options ----------------


# Must be the first Streamlit call
st.set_page_config(
    page_title="SkillBridge — AI Career Gap Analyzer",
    page_icon="💼",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Hide Streamlit's default menu, footer, and deploy button
hide_streamlit_style = """
    <style>
    #MainMenu {visibility: hidden;}     /* Hides hamburger menu */
    footer {visibility: hidden;}        /* Hides footer */
    header {visibility: hidden;}        /* Hides deploy menu on top-right */
    </style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# ---------------- AWS CONFIG ----------------
S3_BUCKET = "skillbridge-assets"
TEMPLATE_PATH = "templates/SkillBridge_Template.pdf"
LAMBDA_FUNCTION = "skillbridge-bedrock-analyzer"
REGION = "us-east-1"

s3 = boto3.client("s3", region_name=REGION)
lambda_client = boto3.client("lambda", region_name=REGION)

# ---------------- STYLING ----------------
st.set_page_config(page_title="SkillBridge — AI Career Gap Analyzer", page_icon="💼", layout="centered")
st.markdown("""
    <style>
        body, .stApp, [data-testid="stAppViewContainer"] {
            background: linear-gradient(180deg, #1a1a1a 0%, #2b2b2b 100%) !important;
            color: #f5f5f5 !important;
            font-family: 'Inter', sans-serif;
        }
        .main-title { text-align:center; font-size:2.5rem; font-weight:800; color:#ff8c1a; }
        .subtext { text-align:center; font-size:1.05rem; color:#ddd; margin-bottom:2rem; }
        label { color:#ffb347 !important; font-weight:600; }
        div.stButton > button { background:linear-gradient(90deg,#ff8800,#ff6600); color:white; border:none; border-radius:10px; padding:0.8rem 1.5rem; width:100%; font-weight:600; }
        div.stButton > button:hover { background:linear-gradient(90deg,#ff9933,#ff6600); }
    </style>
""", unsafe_allow_html=True)

# ---------------- HEADER ----------------
st.markdown("<h1 class='main-title'>💼 SkillBridge — AI Career Gap Analyzer</h1>", unsafe_allow_html=True)
st.markdown("<p class='subtext'>Bridge your skills to your dream career using AI-powered analysis from Amazon Bedrock.</p>", unsafe_allow_html=True)

# ---------------- INPUTS ----------------
uploaded_resume = st.file_uploader("📄 Upload your resume (PDF)", type=["pdf"])
target_role = st.text_input("🎯 Target Role (e.g., Cloud Architect, Data Scientist)")

# ---------------- PDF TEXT EXTRACTION ----------------
def extract_text_from_pdf(file):
    reader = PdfReader(file)
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    return text.strip()

# ---------------- AI ANALYSIS ----------------
def analyze_with_lambda(resume_text, target_role):
    try:
        payload = {"resume_text": resume_text, "target_role": target_role}
        response = lambda_client.invoke(
            FunctionName=LAMBDA_FUNCTION,
            InvocationType="RequestResponse",
            Payload=json.dumps(payload)
        )
        result = json.loads(response["Payload"].read())
        return json.loads(result.get("body", "{}"))
    except Exception as e:
        st.error(f"Error invoking Bedrock Lambda: {e}")
        return None

# ---------------- PDF TEMPLATE + GENERATOR ----------------
def generate_pdf_from_template(ai_result, target_role):
    try:
        # Download base template from S3
        s3_obj = s3.get_object(Bucket=S3_BUCKET, Key=TEMPLATE_PATH)
        template_data = s3_obj["Body"].read()

        # Create PDF in memory
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Helvetica", size=14, style="B")
        pdf.cell(200, 10, txt="SkillBridge — AI Career Gap Report", ln=True, align="C")
        pdf.ln(10)
        pdf.set_font("Helvetica", size=12)
        pdf.multi_cell(0, 8, txt=f"Target Role: {target_role}")
        pdf.ln(5)

        if "missing_skills" in ai_result:
            pdf.set_font("Helvetica", "B", 12)
            pdf.cell(0, 8, "Missing Skills:", ln=True)
            pdf.set_font("Helvetica", size=11)
            for skill in ai_result["missing_skills"]:
                pdf.cell(0, 8, f" - {skill}", ln=True)

        if "certifications" in ai_result:
            pdf.ln(8)
            pdf.set_font("Helvetica", "B", 12)
            pdf.cell(0, 8, "Recommended Certifications:", ln=True)
            pdf.set_font("Helvetica", size=11)
            for cert in ai_result["certifications"]:
                pdf.cell(0, 8, f" - {cert}", ln=True)

        if "learning_links" in ai_result:
            pdf.ln(8)
            pdf.set_font("Helvetica", "B", 12)
            pdf.cell(0, 8, "Learning Resources:", ln=True)
            pdf.set_font("Helvetica", size=11)
            for link in ai_result["learning_links"]:
                pdf.multi_cell(0, 8, f" - {link}")

        # Output in memory
        output_buffer = BytesIO()
        pdf_bytes = pdf.output(dest='S').encode('latin-1', 'replace')
        output_buffer.write(pdf_bytes)
        output_buffer.seek(0)
        return output_buffer

    except Exception as e:
        st.error(f"Error creating PDF report: {e}")
        return None

# ---------------- MAIN LOGIC ----------------
if st.button("✨ Analyze My Resume"):
    if not uploaded_resume or not target_role:
        st.warning("Please upload a resume and enter your target role.")
    else:
        with st.spinner("Analyzing your resume via Amazon Bedrock..."):
            resume_text = extract_text_from_pdf(uploaded_resume)
            ai_result = analyze_with_lambda(resume_text, target_role)
            if ai_result:
                st.success("✅ AI Analysis Completed!")
                st.subheader("📊 AI Recommendations")
                st.json(ai_result)

                report_pdf = generate_pdf_from_template(ai_result, target_role)
                if report_pdf:
                    st.download_button(
                        label="📥 Download Personalized Report",
                        data=report_pdf,
                        file_name=f"SkillBridge_{target_role.replace(' ', '_')}_Report.pdf",
                        mime="application/pdf"
                    )

# ---------------- FOOTER ----------------
st.markdown("<p style='text-align:center; color:#ff9933; margin-top:2rem;'>🏆 AWS AI Agent Hackathon 2025 — SkillBridge by Jill Stan</p>", unsafe_allow_html=True)