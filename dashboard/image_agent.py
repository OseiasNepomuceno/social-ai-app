import os
import requests
import tempfile
import uuid

from services.supabase_storage import upload_image

# =========================
# FAL AI
# =========================

FAL_API_KEY = os.getenv(
    "FAL_API_KEY"
)

# =========================
# GERAR IMAGEM IA
# =========================

def gerar_imagem(tema):

    try:

        prompt = f"""
Imagem profissional premium para LinkedIn e Instagram.

Tema:
{tema}

Regras:
- ultra realista
- marketing corporativo
- visual moderno
- iluminação cinematográfica
- design premium
- ambiente empresarial
- aparência profissional
- composição única
- cores diferentes
- nunca repetir layout
- social media profissional
- alta qualidade
- sem textos na imagem
- imagem diferente para cada geração
"""

        headers = {

            "Authorization": f"Bearer {FAL_API_KEY}",

            "Content-Type": "application/json"

        }

    
        payload = {

            "prompt": prompt,

            "image_size": "square_hd",

            "num_inference_steps": 28,

            "guidance_scale": 7.5,

            "num_images": 1

        }

        response = requests.post(

            "https://fal.run/fal-ai/flux/dev",

            headers=headers,

            json=payload

        )

        print("STATUS FAL:")

        print(response.status_code)

        print("TEXTO FAL:")

        print(response.text)

        data = response.json()

        print("RESPOSTA FAL:")

        print(data)

        image_url = data["images"][0]["url"]

        # =========================
        # DOWNLOAD IMAGEM FAL
        # =========================

        img_response = requests.get(
            image_url
        )

        temp = tempfile.NamedTemporaryFile(
            delete=False,
            suffix=".png"
        )

        temp.write(
            img_response.content
        )

        temp.close()

        # =========================
        # CONVERTER PARA FILE
        # =========================

        class TempFile:

            def __init__(self, path):

                self.filename = (
                    str(uuid.uuid4()) + ".png"
                )

                self.path = path

            def read(self):

                with open(
                    self.path,
                    "rb"
                ) as f:

                    return f.read()

        temp_file = TempFile(
            temp.name
        )

        # =========================
        # UPLOAD SUPABASE
        # =========================

        upload_result = upload_image(
            temp_file
        )

        if upload_result["success"]:

            image_url = upload_result[
                "public_url"
            ]

            print(
                "UPLOAD SUPABASE OK"
            )

        else:

            print(
                "ERRO UPLOAD SUPABASE"
            )

        print("IMAGEM GERADA:")

        print(image_url)

        return image_url

    except Exception as e:

        print("ERRO IMAGE AGENT:")

        print(str(e))

        return None
