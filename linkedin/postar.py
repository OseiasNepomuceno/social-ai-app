import os
import requests
from supabase import create_client

# =========================
# ENV
# =========================

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)

print("🚀 LinkedIn Poster iniciado")


# =========================
# FUNÇÃO PUBLICAR
# =========================

def publicar_linkedin(user_id, conteudo):

    try:

        # =========================
        # BUSCAR TOKEN USER
        # =========================

        usuario = supabase.table("users") \
            .select("*") \
            .eq("id", user_id) \
            .execute()

        if not usuario.data:

            print("❌ Usuário não encontrado")

            return False

        user = usuario.data[0]

        access_token = user.get("linkedin_token")

        if not access_token:

            print("❌ Usuário sem token LinkedIn")

            return False

        # =========================
        # HEADERS USERINFO
        # =========================

        headers = {
            "Authorization": f"Bearer {access_token}"
        }

        # =========================
        # USERINFO
        # =========================

        profile_response = requests.get(
            "https://api.linkedin.com/v2/userinfo",
            headers=headers
        )

        profile_data = profile_response.json()

        # =========================
        # VALIDAR TOKEN
        # =========================

        if "sub" not in profile_data:

            print("❌ Token LinkedIn inválido")

            print(profile_data)

            return False

        print("\n===== PERFIL =====")

        print(profile_data)

        person_id = profile_data["sub"]

        person_urn = f"urn:li:person:{person_id}"

        # =========================
        # PAYLOAD
        # =========================

        payload = {
            "author": person_urn,
            "commentary": conteudo,
            "visibility": "PUBLIC",
            "distribution": {
                "feedDistribution": "MAIN_FEED",
                "targetEntities": [],
                "thirdPartyDistributionChannels": []
            },
            "lifecycleState": "PUBLISHED",
            "isReshareDisabledByAuthor": False
        }

        # =========================
        # HEADERS POSTAGEM
        # =========================

        headers_post = {
            "Authorization": f"Bearer {access_token}",
            "X-Restli-Protocol-Version": "2.0.0",
            "Content-Type": "application/json"
        }

        # =========================
        # POSTAGEM
        # =========================

        response = requests.post(
            "https://api.linkedin.com/v2/ugcPosts",
            headers=headers_post,
            json=payload
        )

        print("\n===== RESPOSTA LINKEDIN =====")

        print(response.status_code)

        print(response.text)

        # =========================
        # SUCESSO
        # =========================

        if response.status_code in [200, 201]:

            print("✅ PUBLICADO COM SUCESSO")

            return True

        # =========================
        # ERRO API
        # =========================

        print("❌ ERRO LINKEDIN")

        return False

    except Exception as e:

        print("❌ ERRO POSTAR LINKEDIN:")

        print(str(e))

        return False
