import json
import os

config_path = '/opt/render/.picoclaw/config.json'
security_path = '/opt/render/.picoclaw/.security.yml'
openrouter_key = os.environ.get('OPENROUTER_API_KEY', '')
gemini_key = os.environ.get('GEMINI_API_KEY', '')

with open(config_path) as f:
    c = json.load(f)

# Define Gemini como modelo padrão
c['agents']['defaults']['model_name'] = 'gemini-2.0-flash'
c['agents']['defaults']['provider'] = 'gemini'

# Atualiza a key do Gemini no model_list
for m in c['model_list']:
    if m.get('model_name') == 'gemini-2.0-flash':
        m['api_keys'] = [gemini_key]
    if m.get('model_name') == 'openrouter-auto':
        m['api_keys'] = [openrouter_key]

# Remove entrada duplicada openrouter com groq
c['model_list'] = [m for m in c['model_list'] if not (m.get('model_name') == 'openrouter-auto' and 'groq' in m.get('api_base', ''))]

with open(config_path, 'w') as f:
    json.dump(c, f, indent=2)

# Atualiza o .security.yml com Gemini como primário
with open(security_path, 'w') as f:
    f.write(f'model_list:\n  gemini-2.0-flash:0:\n    api_keys:\n      - "{gemini_key}"\n  openrouter-auto:0:\n    api_keys:\n      - "{openrouter_key}"\n')

print('PicoClaw config OK - Gemini como modelo principal')
