import os
import requests

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

            "Authorization": f"Key {FAL_API_KEY}",

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

        print("🖼️ RESPOSTA FAL:")

        print(data)

        image_url = data["images"][0]["url"]

        print("✅ IMAGEM GERADA:")

        print(image_url)

        return image_url

    except Exception as e:

        print("❌ ERRO IMAGE AGENT:")

        print(str(e))

        return None
