from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import shutil
import os
import uuid
from pyresparser import ResumeParser
import io
from pdfminer3.layout import LAParams
from pdfminer3.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer3.converter import TextConverter
from pdfminer3.pdfpage import PDFPage
import random
import nltk
from Courses import ds_course, web_course, android_course, ios_course, uiux_course

nltk.download('stopwords')

app = FastAPI()

# Allow requests from anywhere
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_FOLDER = "./Uploaded_Resumes"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

class ResumeResponse(BaseModel):
    name: str
    email: str
    mobile_number: str
    degree: list
    skills: list
    candidate_level: str
    recommended_field: str
    recommended_skills: list
    recommended_courses: list
    resume_score: int

def pdf_reader(file_path):
    resource_manager = PDFResourceManager()
    fake_file_handle = io.StringIO()
    converter = TextConverter(resource_manager, fake_file_handle, laparams=LAParams())
    page_interpreter = PDFPageInterpreter(resource_manager, converter)
    with open(file_path, 'rb') as fh:
        for page in PDFPage.get_pages(fh, caching=True, check_extractable=True):
            page_interpreter.process_page(page)
        text = fake_file_handle.getvalue()
    converter.close()
    fake_file_handle.close()
    return text

@app.post("/analyze", response_model=ResumeResponse)
async def analyze_resume(file: UploadFile = File(...)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    save_path = os.path.join(UPLOAD_FOLDER, f"{uuid.uuid4()}_{file.filename}")
    with open(save_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        data = ResumeParser(save_path).get_extracted_data()
        if not data:
            raise Exception("Resume parsing failed.")

        resume_text = pdf_reader(save_path)
        skills = data.get("skills", [])

        # Candidate level
        candidate_level = "Fresher"
        if any(x in resume_text for x in ["INTERNSHIP", "Internships", "Internship"]):
            candidate_level = "Intermediate"
        elif any(x in resume_text for x in ["EXPERIENCE", "Experience", "Work Experience"]):
            candidate_level = "Experienced"

        # Recommendation logic
        ds_keywords = ['tensorflow','keras','pytorch','machine learning','deep Learning','flask','streamlit']
        web_keywords = ['react', 'django', 'node jS', 'react js', 'php', 'laravel', 'magento', 'wordpress','javascript']
        android_keywords = ['android','flutter','kotlin']
        ios_keywords = ['ios','swift','xcode']
        uiux_keywords = ['ux','adobe xd','figma','ui','wireframes']

        recommended_field = "NA"
        recommended_skills = []
        recommended_courses = []

        for skill in skills:
            s = skill.lower()
            if s in ds_keywords:
                recommended_field = "Data Science"
                recommended_skills = ds_keywords
                recommended_courses = [c[0] for c in ds_course[:5]]
                break
            elif s in web_keywords:
                recommended_field = "Web Development"
                recommended_skills = web_keywords
                recommended_courses = [c[0] for c in web_course[:5]]
                break
            elif s in android_keywords:
                recommended_field = "Android Development"
                recommended_skills = android_keywords
                recommended_courses = [c[0] for c in android_course[:5]]
                break
            elif s in ios_keywords:
                recommended_field = "iOS Development"
                recommended_skills = ios_keywords
                recommended_courses = [c[0] for c in ios_course[:5]]
                break
            elif s in uiux_keywords:
                recommended_field = "UI/UX Design"
                recommended_skills = uiux_keywords
                recommended_courses = [c[0] for c in uiux_course[:5]]
                break

        # Resume score
        score = 0
        for key in ["Objective", "Education", "Experience", "Internship", "Skills", "Hobbies", "Interests", "Achievements", "Certifications", "Projects"]:
            if key.lower() in resume_text.lower():
                score += 10

        return ResumeResponse(
            name=data.get("name", ""),
            email=data.get("email", ""),
            mobile_number=data.get("mobile_number", ""),
            degree=data.get("degree", []),
            skills=skills,
            candidate_level=candidate_level,
            recommended_field=recommended_field,
            recommended_skills=recommended_skills,
            recommended_courses=recommended_courses,
            resume_score=score
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
