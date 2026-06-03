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

def selecionar_imagem(nicho="marketing", rede="linkedin", estilo="premium"):
    try:
        print("\n🔎 BUSCANDO IMAGEM")
        print("NICHO:", nicho)
        print("REDE:", rede)
        print("ESTILO:", estilo)

        # Busca inicial no nicho solicitado
        response = supabase.table("media_library")\
            .select("*")\
            .eq("nicho", nicho.lower())\
            .ilike("rede", rede.lower())\
            .eq("estilo", estilo)\
            .eq("ativo", True)\
            .execute()

        imagens = response.data
        print(f"📸 TOTAL IMAGENS NO NICHO: {len(imagens)}")

        if imagens:
            valid_images = [img for img in imagens if img.get("image_url")]
            if valid_images:
                selecionada = random.choice(valid_images)
                print("✅ IMAGEM SELECIONADA:", selecionada["image_url"])
                return selecionada["image_url"]

        # Busca todos os nichos ativos para fallback, exceto o nicho atual
        nichos_resp = supabase.table("media_library")\
            .select("nicho", distinct=True)\
            .eq("ativo", True)\
            .execute()

        nichos_ativos = list({item['nicho'] for item in nichos_resp.data or []})
        nicho_atual_lower = nicho.lower()
        nichos_ativos = [n for n in nichos_ativos if n.lower() != nicho_atual_lower]

        print(f"⚠️ FALLBACK EM TODOS OS NICHOS, exceto '{nicho}': {nichos_ativos}")

        for fallback_nicho in nichos_ativos:
            response = supabase.table("media_library")\
                .select("*")\
                .eq("nicho", fallback_nicho)\
                .ilike("rede", rede.lower())\
                .eq("estilo", estilo)\
                .eq("ativo", True)\
                .execute()

            imagens = response.data
            if imagens:
                valid_images = [img for img in imagens if img.get("image_url")]
                if valid_images:
                    selecionada = random.choice(valid_images)
                    print(f"✅ IMAGEM FALLBACK SELECIONADA DO NICHO {fallback_nicho}: {selecionada['image_url']}")
                    return selecionada["image_url"]

        print("❌ SEM IMAGENS DISPONÍVEIS NEM NO FALLBACK")
        return None

    except Exception as e:
        print("❌ ERRO NO MEDIA SELECTOR:", str(e))
        return None

# =========================
# TESTE
# =========================

if __name__ == "__main__":
    selecionar_imagem(nicho="marketing")
