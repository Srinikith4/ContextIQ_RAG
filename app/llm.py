import json
import os

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
if not os.getenv("GEMINI_API_KEY") or not os.getenv("GEMINI_MODEL"):
    raise RuntimeError("GEMINI_API_KEY or GEMINI_MODEL is not set. Copy .env.example to .env and fill it in.")
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
MODEL = os.getenv("GEMINI_MODEL")


def generate_answer(prompt):
    response = client.models.generate_content(model=MODEL, contents=prompt)
    return response.text


def generate_json(prompt):
    response = client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(response_mime_type="application/json"),
    )
    return json.loads(response.text)
