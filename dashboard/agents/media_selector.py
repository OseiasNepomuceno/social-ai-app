import os
import random

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

# =========================
# SUPABASE
# =========================

supabase = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)

# =========================
# SELECIONAR IMAGEM
# =========================

def selecionar_imagem(

    nicho="marketing",

    rede="linkedin",

    estilo="premium"

):

    try:

        print("🔎 BUSCANDO IMAGEM")

        response = supabase.table(

            "media_library"

        ).select("*").eq(

            "nicho",
            nicho

        ).eq(

            "rede",
            rede

        ).eq(

            "estilo",
            estilo

        ).execute()

        imagens = response.data

        print(
            f"📸 TOTAL IMAGENS: {len(imagens)}"
        )

        if not imagens:

            print("❌ SEM IMAGENS")

            return None

        imagem = random.choice(
            imagens
        )

        print("✅ IMAGEM SELECIONADA")

        print(imagem["image_url"])

        return imagem["image_url"]

    except Exception as e:

        print("❌ ERRO MEDIA SELECTOR")

        print(str(e))

        return None

# =========================
# TESTE
# =========================

if __name__ == "__main__":

    selecionar_imagem(
        nicho="marketing"
    )
