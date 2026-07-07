import os
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from dotenv import load_dotenv
from google import genai
from agents import TriageAgents

load_dotenv()

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Initialize Gemini Client
api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key) if api_key else None
triage_system = TriageAgents(client) if client else None

class AssessRequest(BaseModel):
    symptoms: str

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/assess")
async def assess_symptoms(request: AssessRequest):
    if not triage_system:
        return {"error": "API key not configured."}
    
    result = triage_system.run_pipeline(request.symptoms)
    return result.model_dump()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
