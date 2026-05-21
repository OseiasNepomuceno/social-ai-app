import os
import requests
import tempfile

from supabase import create_client

# =========================
# ENV
# =========================

SUPABASE_URL = os.getenv(
    "SUPABASE_URL"
)

SUPABASE_KEY = os.getenv(
    "SUPABASE_KEY"
)

print("POSTAR SUPABASE URL:")
print(SUPABASE_URL)

print("POSTAR SUPABASE KEY:")
print(bool(SUPABASE_KEY))

# =========================
# SUPABASE
# =========================

supabase = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)

print("🚀 LinkedIn Poster iniciado")

# =========================
# DOWNLOAD IMAGEM
# =========================

def baixar_imagem(image_url):

    try:

        print("⬇️ Download imagem:")

        print(image_url)

        response = requests.get(
            image_url
        )

        print("STATUS DOWNLOAD:")
        print(response.status_code)

        if response.status_code != 200:

            return None

        temp = tempfile.NamedTemporaryFile(

            delete=False,

            suffix=".jpg"

        )

        temp.write(
            response.content
        )

        temp.close()

        print("✅ IMAGEM BAIXADA")

        print(temp.name)

        return temp.name

    except Exception as e:

        print("❌ ERRO DOWNLOAD:")

        print(str(e))

        return None

# =========================
# PUBLICAR LINKEDIN
# =========================

def publicar_linkedin(

    user_id,

    conteudo,

    image_url=None

):

    try:

        print("\n🚀 INICIANDO PUBLICAÇÃO")

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

        print("✅ TOKEN OK")

        # =========================
        # HEADERS
        # =========================

        headers = {

            "Authorization":
            f"Bearer {access_token}"

        }

        # =========================
        # PROFILE
        # =========================

        profile_response = requests.get(

            "https://api.linkedin.com/v2/userinfo",

            headers=headers

        )

        print("PROFILE STATUS:")
        print(profile_response.status_code)

        profile_data = profile_response.json()

        print("\n===== PROFILE =====")

        print(profile_data)

        if "sub" not in profile_data:

            print("❌ Token inválido")

            return False

        person_id = profile_data["sub"]

        person_urn = (
            f"urn:li:person:{person_id}"
        )

        print("PERSON URN:")
        print(person_urn)

        # =========================
        # PAYLOAD BASE
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

            print("\n🖼️ PROCESSANDO IMAGEM")

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

                                "relationshipType":
                                "OWNER",

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

                print("\n🚀 REGISTRANDO ASSET")

                register_response = requests.post(

                    "https://api.linkedin.com/v2/assets?action=registerUpload",

                    headers=headers_upload,

                    json=register_payload

                )

                print("REGISTER STATUS:")
                print(register_response.status_code)

                register_data = (
                    register_response.json()
                )

                print("\n===== REGISTER =====")

                print(register_data)

                if "value" not in register_data:

                    print(
                        "❌ Erro register upload"
                    )

                    return False

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

                print("UPLOAD URL:")
                print(upload_url)

                print("ASSET:")
                print(asset)

                # =========================
                # UPLOAD BINÁRIO
                # =========================

                print("\n⬆️ ENVIANDO BINÁRIO")

                with open(
                    image_path,
                    "rb"
                ) as img:

                    upload_response = requests.put(

                        upload_url,

                        data=img,

                        headers={

                            "Authorization":
                            f"Bearer {access_token}"

                        }

                    )

                print("UPLOAD STATUS:")
                print(upload_response.status_code)

                print(upload_response.text)

                # =========================
                # PAYLOAD MEDIA
                # =========================

                media_payload = {

                    "shareCommentary": {

                        "text": conteudo

                    },

                    "shareMediaCategory":
                    "IMAGE",

                    "media": [

                        {

                            "status": "READY",

                            "media": asset

                        }

                    ]

                }

                print(
                    "✅ PAYLOAD IMAGE OK"
                )

            else:

                print(
                    "❌ Falha download imagem"
                )

        else:

            print("⚠️ SEM IMAGEM")

        # =========================
        # PAYLOAD FINAL
        # =========================

        payload = {

            "author": person_urn,

            "lifecycleState":
            "PUBLISHED",

            "specificContent": {

                "com.linkedin.ugc.ShareContent":
                media_payload

            },

            "visibility": {

                "com.linkedin.ugc.MemberNetworkVisibility":
                "PUBLIC"

            }

        }

        print("\n===== PAYLOAD FINAL =====")

        print(payload)

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

        print("\n🚀 PUBLICANDO")

        response = requests.post(

            "https://api.linkedin.com/v2/ugcPosts",

            headers=headers_post,

            json=payload

        )

        print("\n===== RESPOSTA LINKEDIN =====")

        print(response.status_code)

        print(response.text)

        if response.status_code in [

            200,
            201

        ]:

            print(
                "✅ PUBLICADO COM SUCESSO"
            )

            return True

        print("❌ ERRO LINKEDIN")

        return False

    except Exception as e:

        print(
            "❌ ERRO POSTAR LINKEDIN:"
        )

        print(str(e))

        return False
