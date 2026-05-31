import os
import time
import requests
import tempfile
import uuid

from supabase import create_client

# =========================
# CONTROLADORES DO COLETOR
# =========================
PAUSADO = False  # Altere para False quando quiser que ele volte a rodar

# =========================
# ENV
# =========================

PIXABAY_API_KEY = os.getenv("PIXABAY_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

print("PIXABAY_API_KEY:")
print(bool(PIXABAY_API_KEY))

print("SUPABASE_URL:")
print(bool(SUPABASE_URL))

print("SUPABASE_KEY:")
print(bool(SUPABASE_KEY))

# =========================
# SUPABASE
# =========================

supabase = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)

# =========================
# CONFIG
# =========================

BUCKET_NAME = "coregov-media"


# =========================
# LIMITES
# =========================

MAX_IMAGENS_TOTAL = 1000

# 🔥 REBALANCEMENTO: Zerado os cheios e focado 100% no nicho de saúde para reequilibrar
NICHOS = {
    "marketing": 0,
    "negocios": 0,
    "financeiro": 0,
    "tecnologia": 0,
    "vendas": 0,
    "empreendedorismo": 0,
    "contabilidade": 0,   
    "psicologia": 0,
    "limpeza": 500,
    "alimentação": 500,
    "engenharia": 0,       
    "saude": 0           # 🚀 Alvo agressivo focado no crescimento deste nicho
}

# =========================
# CONTADOR TOTAL
# =========================

contador_total = 0

# =========================
# BUSCAR IMAGENS PIXABAY
# =========================

def buscar_imagens_pixabay(
    termo="marketing",
    quantidade=20,
    pagina=1
):
    # Trava do controlador: impede qualquer chamada à API se estiver pausado
    if PAUSADO:
        print("⏸️ O coletor Pixabay está PAUSADO. Nenhuma imagem será buscada ou baixada.")
        return []

    try:
        print("\n🔎 BUSCANDO IMAGENS PIXABAY")
        print("TERMO ENVIADO À API:")
        print(termo)

        print("PÁGINA:")
        print(pagina)

        url = "https://pixabay.com/api/"

        params = {
            "key": PIXABAY_API_KEY,
            "q": termo,
            "image_type": "photo",
            "per_page": quantidade,
            "page": pagina,
            "safesearch": "true"
        }

        response = requests.get(
            url,
            params=params
        )

        print("STATUS PIXABAY:")
        print(response.status_code)

        data = response.json()

        if "hits" not in data:
            print("❌ SEM HITS")
            print(data)
            return []

        print(f"✅ TOTAL RETORNADO: {len(data['hits'])}")

        return data.get("hits", [])

    except Exception as e:
        print("❌ ERRO PIXABAY")
        print(str(e))
        return []

# =========================
# DOWNLOAD IMAGEM
# =========================

def baixar_imagem(url):
    try:
        response = requests.get(url)
        if response.status_code != 200:
            return None

        temp = tempfile.NamedTemporaryFile(
            delete=False,
            suffix=".jpg"
        )
        temp.write(response.content)
        temp.close()
        return temp.name

    except Exception as e:
        print("❌ ERRO DOWNLOAD")
        print(str(e))
        return None

# =========================
# UPLOAD SUPABASE
# =========================

def upload_supabase(
    path_arquivo,
    nicho
):
    try:
        nome_arquivo = (
            f"{nicho}/"
            f"{uuid.uuid4()}.jpg"
        )

        with open(path_arquivo, "rb") as f:
            supabase.storage.from_(
                BUCKET_NAME
            ).upload(
                nome_arquivo,
                f,
                {"content-type": "image/jpeg"}
            )

        public_url = supabase.storage.from_(
            BUCKET_NAME
        ).get_public_url(nome_arquivo)

        return public_url

    except Exception as e:
        print("❌ ERRO UPLOAD")
        print(str(e))
        return None

# =========================
# SALVAR DATABASE
# =========================

def salvar_database(
    nicho,
    image_url,
    origem="pixabay"
):
    try:
        supabase.table(
            "media_library"
        ).insert({
            "nicho": nicho,
            "estilo": "premium",
            "categoria": "corporativo",
            "rede": "linkedin",
            "formato": "quadrado",
            "image_url": image_url,
            "origem": origem,
            "tags": nicho,
            "ativo": True
        }).execute()
        print("✅ SALVO DATABASE")

    except Exception as e:
        print("❌ ERRO DATABASE")
        print(str(e))

# =========================
# PROCESSAR IMAGEM
# =========================

def processar_imagem(
    image_url,
    nicho
):
    global contador_total

    try:
        if contador_total >= MAX_IMAGENS_TOTAL:
            print("\n🚫 LIMITE GLOBAL ATINGIDO")
            return False

        print("⬇️ BAIXANDO")
        arquivo = baixar_imagem(image_url)

        if not arquivo:
            return False

        print("☁️ ENVIANDO SUPABASE")
        nova_url = upload_supabase(
            arquivo,
            nicho
        )

        if not nova_url:
            return False

        salvar_database(
            nicho,
            nova_url
        )

        contador_total += 1
        print(f"✅ IMAGEM PROCESSADA: {contador_total}")
        return True

    except Exception as e:
        print("❌ ERRO PROCESSAMENTO")
        print(str(e))
        return False

# =========================
# EXECUTAR NICHO
# =========================

def executar_nicho(
    nicho,
    total_desejado
):
    print("\n========================")
    print(f"🚀 NICHO: {nicho}")
    print("========================")

    processadas = 0
    pagina = 1

    # 🔥 TRUQUE DE MESTRE: Se o nicho for "saude", busca em inglês na API global do Pixabay
    # Isso multiplica por 50x a quantidade de imagens encontradas, mas salva como "saude" no banco!
    termo_busca = "health, medical" if nicho == "saude" else nicho

    while processadas < total_desejado:
        restantes = total_desejado - processadas
        quantidade = min(restantes, 20)

        imagens = buscar_imagens_pixabay(
            termo=termo_busca,
            quantidade=quantidade,
            pagina=pagina
        )

        # Se o robô estiver pausado, ele retorna uma lista vazia aqui e interrompe o loop do nicho
        if not imagens:
            if PAUSADO:
                break
            print("❌ SEM MAIS IMAGENS DISPONÍVEIS NA API")
            break

        for item in imagens:
            try:
                image_url = item.get("largeImageURL")
                if not image_url:
                    continue

                sucesso = processar_imagem(
                    image_url,
                    nicho
                )

                if sucesso:
                    processadas += 1

                if processadas >= total_desejado:
                    break

                if contador_total >= MAX_IMAGENS_TOTAL:
                    break

            except Exception as e:
                print(str(e))

        pagina += 1

        # =========================
        # RATE LIMIT SAFETY
        # =========================
        print("⏳ AGUARDANDO PRÓXIMA PÁGINA...")
        time.sleep(2)

# =========================
# START
# =========================

if __name__ == "__main__":

    print("\n🚀 COREGOV MEDIA ENGINE")

    if PAUSADO:
        print("⏸️ Execução cancelada: O motor de coleta está definido como PAUSADO.")
    else:
        for nicho, total in NICHOS.items():
            # ⚡ Otimização: pula na hora se o nicho estiver definido como 0
            if total == 0:
                continue
                
            executar_nicho(nicho, total)
            if contador_total >= MAX_IMAGENS_TOTAL:
                break

    print("\n✅ PROCESSAMENTO ENCERRADO")
    print(f"📸 TOTAL FINAL DESTA RODADA: {contador_total}")
