import os
from google import genai
from dotenv import load_dotenv

load_dotenv()
client = genai.Client()
for model in client.models.list():
    if "flash" in model.name:
        print(model.name)
