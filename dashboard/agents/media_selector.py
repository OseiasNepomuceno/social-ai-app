import os
import random

from supabase import create_client

# =========================
# ENV
# =========================

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

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
        print("NICHO:", nicho)
        print("REDE:", rede)
        print("ESTILO:", estilo)

        # Busca principal com filtros completos
        response = supabase.table("media_library")\
            .select("*")\
            .eq("nicho", nicho)\
            .eq("rede", rede)\
            .eq("estilo", estilo)\
            .eq("ativo", True)\
            .execute()

        imagens = response.data

        print(f"📸 TOTAL IMAGENS NO NICHO: {len(imagens)}")

        # Fallback mais robusto: tenta nichos relacionados se não encontrar imagens
        if not imagens:
            print("⚠️ FALLBACK POR NICHOS RELACIONADOS")

            nichos_relacionados = ["marketing", "negocios", "empreendedorismo", "contabilidade"]

            # Remove o nicho atual da lista para não tentar novamente
            nichos_relacionados = [n for n in nichos_relacionados if n != nicho]

            for fallback_nicho in nichos_relacionados:
                print(f"Tentando fallback para nicho: {fallback_nicho}")

                response = supabase.table("media_library")\
                    .select("*")\
                    .eq("nicho", fallback_nicho)\
                    .eq("rede", rede)\
                    .eq("ativo", True)\
                    .execute()

                imagens = response.data
                if imagens:
                    print(f"📸 TOTAL IMAGENS FALLBACK para {fallback_nicho}: {len(imagens)}")
                    break  # Sai no primeiro nicho que encontrar

        if not imagens:
            print("❌ SEM IMAGENS DISPONÍVEIS")
            return None

        # Filtrar imagens com URL válida
        valid_images = [img for img in imagens if img.get("image_url")]
        if not valid_images:
            print("❌ Nenhuma imagem com URL válida encontrada")
            return None

        imagem = random.choice(valid_images)
        print("✅ IMAGEM SELECIONADA:", imagem["image_url"])

        return imagem["image_url"]

    except Exception as e:
        print("❌ ERRO NO MEDIA SELECTOR:", str(e))
        return None

# =========================
# TESTE
# =========================

if __name__ == "__main__":
    selecionar_imagem(nicho="marketing")
