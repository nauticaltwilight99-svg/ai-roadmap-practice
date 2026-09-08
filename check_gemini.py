import os
from pathlib import Path

env = Path('.env')
ns = {}
exec(compile(env.read_text(encoding='utf-8'), str(env), 'exec'), ns)
os.environ.update({k: v for k, v in ns.items() if isinstance(v, str)})

from google import genai

api_key = os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY')
print('HAS_KEY', bool(api_key))
client = genai.Client(api_key=api_key)
for model in ['gemini-2.5-flash-lite', 'gemini-2.5-flash', 'gemini-2.5-pro', 'gemini-3.6-flash']:
    try:
        resp = client.models.generate_content(
            model=model,
            contents='Reply in one short Russian sentence: hello from Gemini'
        )
        print('MODEL_OK', model)
        print(resp.text)
        break
    except Exception as e:
        print('MODEL_FAIL', model, type(e).__name__, str(e)[:250])
