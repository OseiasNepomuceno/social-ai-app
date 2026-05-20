import os
import requests
import tempfile

from supabase import create_client

# =========================
# ENV
# =========================

SUPABASE_URL = os.getenv("SUPABASE_URL")

SUPABASE_KEY = os.getenv("SUPABASE_KEY")

print("POSTAR SUPABASE URL:")
print(SUPABASE_URL)

print("POSTAR SUPABASE KEY:")
print(bool(SUPABASE_KEY))

supabase = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)

print("🚀 LinkedIn Poster iniciado")


# =========================
# DOWNLOAD IMAGEM
# =========================

def baixar_imagem(image_url):

    response = requests.get(image_url)

    if response.status_code != 200:

        return None

    temp = tempfile.NamedTemporaryFile(
        delete=False,
        suffix=".jpg"
    )

    temp.write(response.content)

    temp.close()

    return temp.name


# =========================
# PUBLICAR
# =========================

def publicar_linkedin(
    user_id,
    conteudo,
    image_url=None
):

    try:

        # =========================
        # USER
        # =========================

        usuario = supabase.table(
            "users"
        ).select("*").eq(
            "id",
            user_id
        ).execute()

        if not usuario.data:

            print("❌ Usuário não encontrado")

            return False

        user = usuario.data[0]

        access_token = user.get(
            "linkedin_token"
        )

        if not access_token:

            print("❌ Token ausente")

            return False

        # =========================
        # USER INFO
        # =========================

        headers = {

            "Authorization":
            f"Bearer {access_token}"

        }

        profile_response = requests.get(

            "https://api.linkedin.com/v2/userinfo",

            headers=headers

        )

        profile_data = profile_response.json()

        if "sub" not in profile_data:

            print("❌ Token inválido")

            print(profile_data)

            return False

        person_id = profile_data["sub"]

        person_urn = f"urn:li:person:{person_id}"

        print("\n===== PERFIL =====")

        print(profile_data)

        # =========================
        # SEM IMAGEM
        # =========================

        media_payload = {

            "shareCommentary": {
                "text": conteudo
            },

            "shareMediaCategory": "NONE"

        }

        # =========================
        # COM IMAGEM
        # =========================

        if image_url:

            print("🖼️ Baixando imagem...")

            image_path = baixar_imagem(
                image_url
            )

            if image_path:

                # =========================
                # REGISTER UPLOAD
                # =========================

                register_payload = {

                    "registerUploadRequest": {

                        "recipes": [

                            "urn:li:digitalmediaRecipe:feedshare-image"

                        ],

                        "owner": person_urn,

                        "serviceRelationships": [

                            {

                                "relationshipType": "OWNER",

                                "identifier":
                                "urn:li:userGeneratedContent"

                            }

                        ]

                    }

                }

                headers_upload = {

                    "Authorization":
                    f"Bearer {access_token}",

                    "X-Restli-Protocol-Version":
                    "2.0.0",

                    "Content-Type":
                    "application/json"

                }

                register_response = requests.post(

                    "https://api.linkedin.com/v2/assets?action=registerUpload",

                    headers=headers_upload,

                    json=register_payload

                )

                register_data = register_response.json()

                print("\n===== REGISTER =====")

                print(register_data)

                upload_url = register_data[
                    "value"
                ][
                    "uploadMechanism"
                ][
                    "com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"
                ][
                    "uploadUrl"
                ]

                asset = register_data[
                    "value"
                ][
                    "asset"
                ]

                # =========================
                # UPLOAD BINÁRIO
                # =========================

                with open(image_path, "rb") as img:

                    upload_response = requests.put(

                        upload_url,

                        data=img,

                        headers={
                            "Authorization":
                            f"Bearer {access_token}"
                        }

                    )

                print("\n===== UPLOAD =====")

                print(upload_response.status_code)

                # =========================
                # PAYLOAD MEDIA
                # =========================

                media_payload = {

                    "shareCommentary": {
                        "text": conteudo
                    },

                    "shareMediaCategory": "IMAGE",

                    "media": [

                        {

                            "status": "READY",

                            "media": asset

                        }

                    ]

                }

        # =========================
        # PAYLOAD FINAL
        # =========================

        payload = {

            "author": person_urn,

            "lifecycleState": "PUBLISHED",

            "specificContent": {

                "com.linkedin.ugc.ShareContent":
                media_payload

            },

            "visibility": {

                "com.linkedin.ugc.MemberNetworkVisibility":
                "PUBLIC"

            }

        }

        headers_post = {

            "Authorization":
            f"Bearer {access_token}",

            "X-Restli-Protocol-Version":
            "2.0.0",

            "Content-Type":
            "application/json"

        }

        # =========================
        # PUBLICAR
        # =========================

        response = requests.post(

            "https://api.linkedin.com/v2/ugcPosts",

            headers=headers_post,

            json=payload

        )

        print("\n===== RESPOSTA LINKEDIN =====")

        print(response.status_code)

        print(response.text)

        if response.status_code in [200, 201]:

            print("✅ PUBLICADO COM SUCESSO")

            return True

        print("❌ ERRO LINKEDIN")

        return False

    except Exception as e:

        print("❌ ERRO POSTAR LINKEDIN:")

        print(str(e))

        return False
