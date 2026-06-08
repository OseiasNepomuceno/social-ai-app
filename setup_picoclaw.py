import json
import os

config_path = '/opt/render/.picoclaw/config.json'
security_path = '/opt/render/.picoclaw/.security.yml'
openrouter_key = os.environ.get('OPENROUTER_API_KEY', '')
gemini_key = os.environ.get('GEMINI_API_KEY', '')
groq_key = os.environ.get('GROQ_API_KEY', '')

with open(config_path) as f:
    c = json.load(f)

# Groq como modelo principal
c['agents']['defaults']['model_name'] = 'llama-3.3-70b'
c['agents']['defaults']['provider'] = 'groq'

for m in c['model_list']:
    if m.get('model_name') == 'llama-3.3-70b':
        m['api_keys'] = [groq_key]
    if m.get('model_name') == 'gemini-2.0-flash':
        m['api_keys'] = [gemini_key]
        m['model'] = 'gemini-2.5-flash'
    if m.get('model_name') == 'openrouter-auto':
        m['api_keys'] = [openrouter_key]

c['model_list'] = [m for m in c['model_list'] if not (
    m.get('model_name') == 'openrouter-auto' and 'groq' in m.get('api_base', '')
)]

with open(config_path, 'w') as f:
    json.dump(c, f, indent=2)

with open(security_path, 'w') as f:
    f.write(
        f'model_list:\n'
        f'  llama-3.3-70b:8:\n'
        f'    api_keys:\n'
        f'      - "{groq_key}"\n'
        f'  gemini-2.0-flash:0:\n'
        f'    api_keys:\n'
        f'      - "{gemini_key}"\n'
        f'  openrouter-auto:0:\n'
        f'    api_keys:\n'
        f'      - "{openrouter_key}"\n'
    )

print('PicoClaw config OK - Groq como modelo principal')
