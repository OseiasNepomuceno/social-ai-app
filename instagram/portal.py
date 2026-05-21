import requests

# =========================
# PUBLICAR INSTAGRAM
# =========================

def publicar_instagram(

    access_token,
    ig_user_id,
    texto,
    imagem_url

):

    try:

        print("\n========================")
        print("📸 PUBLICANDO INSTAGRAM")
        print("========================")

        print("IG USER ID:")
        print(ig_user_id)

        print("IMAGEM:")
        print(imagem_url)

        # =========================
        # ETAPA 1
        # CRIAR CONTAINER
        # =========================

        create_url = (

            f"https://graph.facebook.com/"
            f"v23.0/{ig_user_id}/media"

        )

        create_payload = {

            "image_url": imagem_url,

            "caption": texto,

            "access_token": access_token

        }

        print("\n🚀 CRIANDO CONTAINER")

        response = requests.post(

            create_url,

            data=create_payload

        )

        print("STATUS CONTAINER:")
        print(response.status_code)

        print("RESPOSTA CONTAINER:")
        print(response.text)

        data = response.json()

        if "id" not in data:

            print("❌ ERRO CONTAINER")

            return False

        creation_id = data["id"]

        print("✅ CONTAINER CRIADO")

        print(creation_id)

        # =========================
        # ETAPA 2
        # PUBLICAR POST
        # =========================

        publish_url = (

            f"https://graph.facebook.com/"
            f"v23.0/{ig_user_id}/media_publish"

        )

        publish_payload = {

            "creation_id": creation_id,

            "access_token": access_token

        }

        print("\n🚀 PUBLICANDO POST")

        publish_response = requests.post(

            publish_url,

            data=publish_payload

        )

        print("STATUS PUBLICAÇÃO:")
        print(publish_response.status_code)

        print("RESPOSTA PUBLICAÇÃO:")
        print(publish_response.text)

        publish_data = publish_response.json()

        if "id" not in publish_data:

            print("❌ ERRO PUBLICAÇÃO")

            return False

        print("✅ INSTAGRAM PUBLICADO")

        return True

    except Exception as e:

        print("❌ ERRO INSTAGRAM")

        print(str(e))

        return False
