import requests
import json

# =========================
# LER TOKEN
# =========================

with open(
    "token.json",
    "r",
    encoding="utf-8"
) as file:

    token_data = json.load(file)

ACCESS_TOKEN = token_data[
    "access_token"
]

headers = {
    "Authorization": f"Bearer {ACCESS_TOKEN}",
    }

# =========================
# PEGAR USERINFO (OPENID)
# =========================

profile_response = requests.get(
    "https://api.linkedin.com/v2/userinfo",
    headers=headers
)

profile_data = profile_response.json()

print("\n===== PERFIL =====")
print(profile_data)

person_id = profile_data["sub"]

person_urn = f"urn:li:person:{person_id}"

# =========================
# CONTEÚDO POSTAGEM
# =========================

mensagem = """
🚀 Teste de postagem automática via API LinkedIn

Sistema Social AI funcionando com:
✅ IA
✅ Scheduler
✅ Automação
✅ API oficial LinkedIn

#Python #LinkedInAPI #Automacao #IA
"""

# =========================
# PAYLOAD POSTAGEM
# =========================

payload = {
    "author": person_urn,
    "commentary": mensagem,
    "visibility": "PUBLIC",
    "distribution": {
        "feedDistribution": "MAIN_FEED",
        "targetEntities": [],
        "thirdPartyDistributionChannels": []
    },
    "lifecycleState": "PUBLISHED",
    "isReshareDisabledByAuthor": False
}

headers_post = {
    "Authorization": f"Bearer {ACCESS_TOKEN}",
    "LinkedIn-Version": "202505",
    "X-Restli-Protocol-Version": "2.0.0",
    "Content-Type": "application/json"
}

# =========================
# PUBLICAR
# =========================

response = requests.post(
    "https://api.linkedin.com/rest/posts",
    headers=headers_post,
    json=payload
)

print("\n===== RESPOSTA LINKEDIN =====")
print(response.status_code)
print(response.text)
