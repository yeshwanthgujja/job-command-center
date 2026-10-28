# tailor.py
import os
from fpdf import FPDF
from scorer import get_gemini_model

def read_master_resume():
    if os.path.exists("resume.txt"):
        with open("resume.txt", "r", encoding="utf-8") as f:
            return f.read()
    return "Resume text not found."

def generate_application_packet(job):
    model = get_gemini_model()
    resume_text = read_master_resume()
    
    if not model:
        return None, None
        
    prompt = f"""
    You are an expert career coach. Based on my Master Resume below, write:
    1. A tailored resume summary (max 3 sentences).
    2. A custom cover letter (max 150 words).
    3. A list of 5 technical interview questions based on the JD.

    JOB: {job['title']} at {job['company']}
    JD SNIPPET: {job['snippet']}
    
    MASTER RESUME: {resume_text}
    
    Output format strictly:
    --- SUMMARY ---
    (text)
    --- COVER LETTER ---
    (text)
    --- INTERVIEW PREP ---
    (text)
    """
    
    try:
        response = model.generate_content(prompt)
        output = response.text
        
        # Generate PDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=11)
        
        # Add Header
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(200, 10, txt="APPLICATION PACKET", ln=True, align='C')
        pdf.set_font("Arial", size=11)
        pdf.cell(200, 10, txt=f"Role: {job['title']} at {job['company']}", ln=True, align='C')
        pdf.ln(10)
        
        # Add AI Output
        # Clean up text for basic PDF compatibility
        clean_text = output.replace('---', '').encode('latin-1', 'replace').decode('latin-1')
        pdf.multi_cell(0, 6, txt=clean_text)
        
        filename = f"job_data/packets/{job['company']}_{job['title']}.pdf".replace("/", "_").replace(" ", "_")
        os.makedirs("job_data/packets", exist_ok=True)
        pdf.output(filename)
        
        return filename, output
    except Exception as e:
        print(f"Tailoring failed: {e}")
        return None, None