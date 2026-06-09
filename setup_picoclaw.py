import json
import os

config_path = '/opt/render/.picoclaw/config.json'
security_path = '/opt/render/.picoclaw/.security.yml'
deepseek_key = os.environ.get('DEEPSEEK_API_KEY', '')

with open(config_path) as f:
    c = json.load(f)

# Configurando para o DeepSeek direto
c['agents']['defaults']['model_name'] = 'deepseek-chat'
c['agents']['defaults']['provider'] = 'deepseek' # Alterado para o provider oficial

# Atualizando a lista de modelos
for m in c['model_list']:
    if m.get('model_name') == 'deepseek-chat':
        m['api_keys'] = [deepseek_key]
        m['api_base'] = 'https://api.deepseek.com' # Endpoint oficial
        m['model'] = 'deepseek-chat' 

with open(config_path, 'w') as f:
    json.dump(c, f, indent=2)

with open(security_path, 'w') as f:
    f.write(
        f'model_list:\n'
        f'  deepseek-chat:0:\n'
        f'    api_keys:\n'
        f'      - "{deepseek_key}"\n'
    )

print('PicoClaw config OK - DeepSeek Oficial Direto')
