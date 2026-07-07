import os
from pydantic import BaseModel
from typing import List

# Output Models
class ExtractionOutput(BaseModel):
    onset: str
    duration: str
    key_symptoms: List[str]
    red_flag_keywords: List[str]

class AssessorOutput(BaseModel):
    priority: str
    confidence: float
    reasoning: str

class FinalOutput(BaseModel):
    priority: str
    confidence: float
    reasoning: str
    counterfactual: str

class TriageAgents:
    def __init__(self, client):
        self.client = client
        # Use a stable fast model
        self.model_name = "gemini-2.5-flash"
        self.base_dir = os.path.dirname(os.path.abspath(__file__))

    def run_pipeline(self, symptom_text: str) -> FinalOutput:
        """1. ORCHESTRATOR - Routes input through the pipeline"""
        # Step 2: Extract
        extraction = self._run_extractor(symptom_text)
        
        # Step 3: Assess Severity
        assessment = self._run_assessor(extraction)
        
        # Step 4: Escalate (Add Counterfactual)
        final_result = self._run_escalation(assessment, extraction)
        
        return final_result

    def _run_extractor(self, text: str) -> ExtractionOutput:
        """2. SYMPTOM-EXTRACTOR AGENT"""
        prompt = f"""
You are a Symptom-Extractor agent. Turn messy human language into structured data.
Extract the onset, duration, key_symptoms, and red_flag_keywords from the text.
Do NOT infer anything the patient didn't say. Only extract what is present.
If a value is not mentioned, put "Not specified".
Red flag keywords are individual alarming words related to medical conditions (e.g. chest, arm, pressure, breathless, wheezing, cough, bleeding, fracture, unconscious).

Patient text: "{text}"
"""
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "response_schema": ExtractionOutput,
                "temperature": 0.0
            },
        )
        # Parse output
        return ExtractionOutput.model_validate_json(response.text)

    def _get_relevant_skills(self, keywords: List[str]) -> str:
        """Conditionally load skill files based on keywords."""
        keywords_lower = [k.lower() for k in keywords]
        skills_loaded = []
        
        # Map keyword patterns to skill files
        cardiac_keys = ['chest', 'arm', 'jaw', 'pressure', 'tightness', 'heart', 'palpitations', 'sweating', 'diaphoresis']
        resp_keys = ['breath', 'breathless', 'wheezing', 'cough', 'choking', 'air', 'lungs', 'phlegm']
        trauma_keys = ['bleeding', 'fracture', 'unconscious', 'cut', 'bone', 'head', 'fall', 'hit', 'burn', 'swollen', 'bruise']
        
        has_cardiac = any(any(k in kw for k in cardiac_keys) for kw in keywords_lower)
        has_resp = any(any(k in kw for k in resp_keys) for kw in keywords_lower)
        has_trauma = any(any(k in kw for k in trauma_keys) for kw in keywords_lower)
        
        if has_cardiac:
            skills_loaded.append("cardiac/SKILL.md")
        if has_resp:
            skills_loaded.append("respiratory/SKILL.md")
        if has_trauma:
            skills_loaded.append("trauma/SKILL.md")
            
        if not skills_loaded:
            skills_loaded.append("general/SKILL.md")
            
        skill_contents = []
        for sf in skills_loaded:
            path = os.path.join(self.base_dir, "skills", sf)
            if os.path.exists(path):
                with open(path, "r") as f:
                    skill_contents.append(f.read())
                    
        return "\n\n".join(skill_contents)

    def _run_assessor(self, extraction: ExtractionOutput) -> AssessorOutput:
        """3. SEVERITY-ASSESSOR AGENT"""
        skill_text = self._get_relevant_skills(extraction.red_flag_keywords + extraction.key_symptoms)
        
        prompt = f"""
You are a Severity-Assessor agent. Decide the triage tier (NORMAL, URGENT, or EMERGENCY) using domain-specific knowledge.
Use ONLY the following skill rules to make your decision:

--- SKILL RULES ---
{skill_text}
--- END SKILL RULES ---

Extracted Symptoms:
Onset: {extraction.onset}
Duration: {extraction.duration}
Key Symptoms: {extraction.key_symptoms}
Keywords: {extraction.red_flag_keywords}

Determine the priority (must be exactly NORMAL, URGENT, or EMERGENCY).
Provide a confidence score between 0.0 and 1.0.
Provide a plain-language reasoning string referencing the specific skill file criteria.
"""
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "response_schema": AssessorOutput,
                "temperature": 0.0
            },
        )
        return AssessorOutput.model_validate_json(response.text)

    def _run_escalation(self, assessment: AssessorOutput, extraction: ExtractionOutput) -> FinalOutput:
        """4. ESCALATION AGENT"""
        prompt = f"""
You are an Escalation agent. Your job is to add a counterfactual to a triage assessment.
Never silently downgrade. You must add ONE additional explicit sentence: "Would escalate to [more severe tier] if [specific missing factor] were present."
If the priority is already EMERGENCY, state what factor would confirm or worsen the critical nature (e.g., "Would become immediately life-threatening if [X] occurred.").

Current Priority: {assessment.priority}
Current Reasoning: {assessment.reasoning}
Symptoms: {extraction.key_symptoms}

Return the original priority, confidence, and reasoning, and add your single counterfactual string.
"""
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "response_schema": FinalOutput,
                "temperature": 0.0
            },
        )
        return FinalOutput.model_validate_json(response.text)
