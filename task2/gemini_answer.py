import os, json
from google import genai
from google.genai import types

def load_api_key():
    path = os.path.join("modules", "config", "secrets.local.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)["GEMINI_API_KEY"]

def answer_with_gemini(query: str, context_blocks):
    api_key = load_api_key()
    client = genai.Client(api_key=api_key)

    system_prompt = (
        "You are Helix HR Intelligence Bot.\n"
        "RULES:\n"
        "1) Answer ONLY using the provided CONTEXT.\n"
        "2) If context is insufficient, reply starting with: INSUFFICIENT_DATA.\n"
        "3) Add citations like [source] for each key statement.\n"
        "4) Do NOT invent numbers, employee facts, or policy rules.\n"
    )

    ctx = ""
    for b in context_blocks:
        ctx += f"\n---\nSOURCE: {b['source']}\nTITLE: {b['title']}\nTEXT:\n{b['text']}\n"

    user_prompt = f"CONTEXT:\n{ctx}\n\nQUESTION:\n{query}\n\nAnswer with citations."

    # IMPORTANT: your SDK accepts roles user/model, so system goes via config
    resp = client.models.generate_content(
        model="models/gemini-flash-lite-latest",
        contents=[types.Content(role="user", parts=[types.Part(text=user_prompt)])],
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=0.0,
            top_p=0.1,
            max_output_tokens=512,
        ),
    )

    text = (resp.text or "").strip()
    # Extra guardrail: if no citations, refuse
    if "INSUFFICIENT_DATA" not in text and ("[" not in text or "]" not in text):
        return "INSUFFICIENT_DATA: Model response missing citations."
    return text
