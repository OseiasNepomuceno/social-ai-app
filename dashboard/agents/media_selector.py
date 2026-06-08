import os
import random
import unicodedata
import difflib
from supabase import create_client

# =========================
# ENV
# =========================

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# =========================
# SUPABASE
# =========================

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# =========================
# UTILS
# =========================

def normalize(text: str) -> str:
    """Remove acentos e coloca em minúsculas para comparação consistente"""
    return ''.join(
        c for c in unicodedata.normalize('NFD', text)
        if unicodedata.category(c) != 'Mn'
    ).lower()

def closest_match(target: str, options: list) -> str:
    """Retorna o item mais parecido com target dentro de options"""
    match = difflib.get_close_matches(target, options, n=1, cutoff=0.6)
    return match[0] if match else None

# =========================
# INFERIR NICHO
# =========================

def inferir_nicho(tema: str, lista_nichos: list) -> str:
    prompt = f"""Com base no tema abaixo, identifique qual é o nicho/segmento mais adequado.
Tema: {tema}
Nichos disponíveis: {', '.join(lista_nichos)}
Responda APENAS com o nome exato do nicho da lista, sem explicações."""
    
    resultado = chamar_picoclaw(prompt, timeout=30)
    if resultado.get("success"):
        nicho_inferido = resultado["conteudo"].strip()
        nicho_inferido_norm = normalize(nicho_inferido)
        lista_norm = [normalize(n) for n in lista_nichos]

        # tenta casar exatamente
        for i, n_norm in enumerate(lista_norm):
            if n_norm == nicho_inferido_norm:
                return lista_nichos[i]

        # se não casar, pega o mais parecido
        match = closest_match(nicho_inferido_norm, lista_norm)
        if match:
            idx = lista_norm.index(match)
            return lista_nichos[idx]

    # fallback final: primeiro da lista
    return lista_nichos[0]

# =========================
# SELECIONAR IMAGEM
# =========================

def selecionar_imagem(nicho="marketing", rede="linkedin", estilo="premium"):
    try:
        print("\n🔎 BUSCANDO IMAGEM")
        print("NICHO:", nicho)
        print("REDE:", rede)
        print("ESTILO:", estilo)

        nicho_norm = normalize(nicho)

        # Busca inicial sem filtrar por nicho no SQL, filtrando em Python com normalize
        response = supabase.table("media_library")\
            .select("*")\
            .eq("ativo", True)\
            .ilike("rede", rede.lower())\
            .eq("estilo", estilo)\
            .execute()

        imagens = [img for img in response.data if normalize(img["nicho"]) == nicho_norm]

        # Se não achou nada, tenta similaridade
        if not imagens:
            lista_norm = [normalize(img["nicho"]) for img in response.data]
            match = closest_match(nicho_norm, lista_norm)
            if match:
                imagens = [img for img in response.data if normalize(img["nicho"]) == match]

        print(f"📸 TOTAL IMAGENS NO NICHO: {len(imagens)}")

        if imagens:
            valid_images = [img for img in imagens if img.get("image_url")]
            if valid_images:
                selecionada = random.choice(valid_images)
                print("✅ IMAGEM SELECIONADA:", selecionada["image_url"])
                return selecionada["image_url"]

        # Busca todos os nichos ativos
        nichos_resp = supabase.table("media_library")\
            .select("nicho")\
            .eq("ativo", True)\
            .execute()

        nichos_ativos = list({normalize(item['nicho']) for item in nichos_resp.data or []})
        nichos_ativos = [n for n in nichos_ativos if n != nicho_norm]

        print(f"⚠️ FALLBACK EM TODOS OS NICHOS, exceto '{nicho}': {nichos_ativos}")

        for fallback_nicho in nichos_ativos:
            response = supabase.table("media_library")\
                .select("*")\
                .eq("ativo", True)\
                .ilike("rede", rede.lower())\
                .eq("estilo", estilo)\
                .execute()

            imagens = [img for img in response.data if normalize(img["nicho"]) == fallback_nicho]
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
