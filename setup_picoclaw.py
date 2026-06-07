import json
import os

config_path = '/opt/render/.picoclaw/config.json'
api_key = os.environ.get('OPENROUTER_API_KEY', '')

with open(config_path) as f:
    c = json.load(f)

c['agents']['defaults']['model_name'] = 'openrouter-auto'
c['agents']['defaults']['provider'] = 'openrouter'
c['model_list'] = [m for m in c['model_list'] if not (m.get('model_name') == 'openrouter-auto' and 'groq' in m.get('api_base', ''))]

for m in c['model_list']:
    if m.get('model_name') == 'openrouter-auto':
        m['api_keys'] = [api_key]

with open(config_path, 'w') as f:
    json.dump(c, f, indent=2)

print('PicoClaw config OK')
