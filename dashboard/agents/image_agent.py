import urllib.parse

# =========================
# GERAR IMAGEM IA
# =========================

def gerar_imagem(tema):

    try:

        prompt = f"""
        imagem profissional para redes sociais,
        alta qualidade,
        marketing digital,
        tema: {tema},
        estilo moderno,
        iluminação cinematográfica,
        design premium,
        instagram post,
        linkedin post
        """

        prompt_encoded = urllib.parse.quote(
            prompt
        )

        image_url = (
            f"https://image.pollinations.ai/prompt/{prompt_encoded}"
        )

        return image_url

    except Exception as e:

        print("ERRO IMAGE AGENT:")

        print(str(e))

        return None
