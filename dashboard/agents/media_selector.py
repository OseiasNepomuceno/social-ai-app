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

        print("\n🔎 BUSCANDO IMAGEM")

        print("NICHO:")
        print(nicho)

        print("REDE:")
        print(rede)

        print("ESTILO:")
        print(estilo)

        # =========================
        # BUSCA PRINCIPAL
        # =========================

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

        ).eq(

            "ativo",
            True

        ).execute()

        imagens = response.data

        print(
            f"📸 TOTAL IMAGENS NICHO: {len(imagens)}"
        )

        # =========================
        # FALLBACK
        # =========================

        if not imagens:

            print(
                "⚠️ FALLBACK MARKETING"
            )

            response = supabase.table(

                "media_library"

            ).select("*").eq(

                "nicho",
                "marketing"

            ).eq(

                "ativo",
                True

            ).execute()

            imagens = response.data

            print(
                f"📸 TOTAL FALLBACK: {len(imagens)}"
            )

        # =========================
        # SEM IMAGEM
        # =========================

        if not imagens:

            print("❌ SEM IMAGENS")

            return None

        # =========================
        # RANDOM
        # =========================

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
