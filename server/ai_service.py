"""
Pharmaco-Llama: Real AI Multimodal Vision & Clinical Reasoning Engine
Powered by live Groq Cloud API (Meta Llama & Vision Models)
Author: Md Mushfiqur Rahim (NIH-Certified in Clinical Pharmacology & Clinical Research)
"""

import os
import base64
import json
import requests
from typing import List, Dict, Any, Optional

def _get_api_key() -> str:
    key = os.getenv("GROQ_API_KEY")
    if key:
        return key
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip().startswith("GROQ_API_KEY="):
                        return line.strip().split("=", 1)[1].strip("\"' ")
        except Exception:
            pass
    return ""

GROQ_API_KEY = _get_api_key()
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

# Primary multimodal vision model on Groq
VISION_MODEL = "qwen/qwen3.8-27b"
# Primary deep reasoning LLM
REASONING_MODEL = "openai/gpt-oss-120b"

def analyze_prescription_image(image_bytes: bytes, mime_type: str = "image/jpeg") -> List[Dict[str, str]]:
    """
    Real Vision Inference: Encodes prescription/pill image to base64 and invokes Groq Vision API.
    Returns structured list of extracted medications: [{'name': '...', 'dose': '...', 'route': '...'}]
    """
    base64_image = base64.b64encode(image_bytes).decode('utf-8')
    data_uri = f"data:{mime_type};base64,{base64_image}"
    
    prompt = (
        "You are an expert clinical pharmacologist. Analyze this handwritten or printed prescription or medication label photo. "
        "Extract every distinct medication, active ingredient, dosage, and frequency. "
        "Return STRICTLY a JSON array of objects with keys: 'name', 'dose', 'class'. "
        "Do NOT include markdown formatting, backticks, or explanatory text. Example:\n"
        '[{"name": "Warfarin", "dose": "5mg", "class": "Anticoagulant"}, {"name": "Aspirin", "dose": "81mg", "class": "Antiplatelet"}]'
    )
    
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": VISION_MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": data_uri}}
                ]
            }
        ],
        "temperature": 0.1,
        "max_tokens": 1024
    }
    
    try:
        response = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=20)
        if response.status_code == 200:
            content = response.json()['choices'][0]['message']['content'].strip()
            # Clean possible markdown fences
            if content.startswith("```"):
                lines = content.splitlines()
                content = "\n".join(lines[1:-1] if lines[-1].startswith("```") else lines[1:])
            
            drugs = json.loads(content)
            if isinstance(drugs, list) and len(drugs) > 0:
                return drugs
            raise ValueError("Vision model returned an empty drug list.")
    except Exception as e:
        print(f"[Vision Error] {e}")
        raise RuntimeError(f"Vision OCR could not detect legible prescription entities: {str(e)}")

def generate_dynamic_clinical_plan(
    medications: List[Dict[str, str]],
    hazard_score: int,
    boxed_warnings: List[Dict[str, Any]],
    pk_data: Optional[Dict[str, Any]]
) -> List[Dict[str, str]]:
    """
    Real Generative Reasoning: Invokes high-capacity LLM to synthesize actionable clinical deprescribing directives.
    """
    med_list_str = ", ".join([f"{m.get('name')} {m.get('dose', '')}" for m in medications])
    warnings_str = "\n".join([f"- {w.get('drug')}: {w.get('title')} ({w.get('text', '')[:100]}...)" for w in boxed_warnings]) if boxed_warnings else "None detected."
    
    prompt = (
        f"You are a clinical pharmacology consultant (Lead: Md Mushfiqur Rahim, NIH Certified). "
        f"A patient is taking: {med_list_str}.\n"
        f"Polypharmacy Hazard Index: {hazard_score}/100.\n"
        f"FDA Warnings:\n{warnings_str}\n\n"
        "Generate 2 to 3 concise, high-priority, evidence-backed clinical action directives. "
        "Return STRICTLY a JSON array of objects with keys: 'type' (e.g. 'DISCONTINUE', 'SUBSTITUTE', 'MONITOR'), "
        "'title' (short headline), 'desc' (clinical rationale and exact dosage alternative). "
        "Do NOT include markdown fences or conversational filler. Example format:\n"
        '[{"type": "DISCONTINUE", "title": "Halt Omeprazole", "desc": "Switch to Pantoprazole 40mg to prevent CYP2C19 blockade of Clopidogrel."}]'
    )
    
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": REASONING_MODEL,
        "messages": [
            {"role": "system", "content": "You are an expert clinical pharmacologist. Output only valid JSON arrays."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2,
        "max_tokens": 1024
    }
    
    try:
        response = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=15)
        if response.status_code == 200:
            content = response.json()['choices'][0]['message']['content'].strip()
            if content.startswith("```"):
                lines = content.splitlines()
                content = "\n".join(lines[1:-1] if lines[-1].startswith("```") else lines[1:])
            actions = json.loads(content)
            if isinstance(actions, list) and len(actions) > 0:
                # Add UI badge styling
                for a in actions:
                    act_type = a.get("type", "").upper()
                    if "DISCONTINUE" in act_type or "HALT" in act_type:
                        a["badgeClass"] = "bg-red-500/20 text-red-400 border-red-500/30"
                    elif "SUBSTITUTE" in act_type or "SWITCH" in act_type:
                        a["badgeClass"] = "bg-emerald-500/20 text-emerald-400 border-emerald-500/30"
                    else:
                        a["badgeClass"] = "bg-cyan-500/20 text-cyan-400 border-cyan-500/30"
                return actions
    except Exception as e:
        print(f"[Reasoning Error] {e}")

    # Truthful Dynamic Fallback: Synthesize action directives strictly from actual detected warnings
    dynamic_actions = []
    if boxed_warnings:
        for w in boxed_warnings[:3]:
            sev = w.get("severity", "HIGH").upper()
            msg = w.get("message", "")
            rec = w.get("recommendation", "Clinical review required.")
            drug = w.get("drug", "Target Drug")
            
            if sev in ["LETHAL", "CRITICAL", "CONTRAINDICATED"]:
                dynamic_actions.append({
                    "type": "EMERGENCY HALT",
                    "title": f"Discontinue or Separate {drug}",
                    "desc": rec if rec else f"Severe interaction flagged: {msg[:120]}...",
                    "badgeClass": "bg-red-500/20 text-red-400 border-red-500/30"
                })
            elif sev in ["HIGH", "HIGH_RISK"]:
                dynamic_actions.append({
                    "type": "SUBSTITUTE",
                    "title": f"Pharmacokinetic Adjustment for {drug}",
                    "desc": rec if rec else f"High-risk conflict: {msg[:120]}...",
                    "badgeClass": "bg-emerald-500/20 text-emerald-400 border-emerald-500/30"
                })
            else:
                dynamic_actions.append({
                    "type": "MONITOR",
                    "title": f"Surveillance Protocol: {drug}",
                    "desc": rec if rec else f"Monitor therapeutic levels and toxicity biomarkers.",
                    "badgeClass": "bg-cyan-500/20 text-cyan-400 border-cyan-500/30"
                })

    if not dynamic_actions and medications:
        med_names = [m.get("name", "medication") for m in medications]
        dynamic_actions.append({
            "type": "SURVEILLANCE",
            "title": "Nominal Regimen Clearance",
            "desc": f"No high-hazard biochemical contraindications detected across {len(med_names)} active drugs ({', '.join(med_names[:4])}). Maintain baseline therapeutic monitoring.",
            "badgeClass": "bg-emerald-500/20 text-emerald-400 border-emerald-500/30"
        })

    return dynamic_actions
