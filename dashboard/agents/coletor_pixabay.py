import os
import requests
import tempfile
import uuid

from supabase import create_client

# =========================
# ENV
# =========================

PIXABAY_API_KEY = os.getenv(
    "PIXABAY_API_KEY"
)

SUPABASE_URL = os.getenv(
    "SUPABASE_URL"
)

SUPABASE_KEY = os.getenv(
    "SUPABASE_KEY"
)

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
# BUSCAR IMAGENS PIXABAY
# =========================

def buscar_imagens_pixabay(

    termo="marketing",

    quantidade=10

):

    try:

        print("🔎 BUSCANDO IMAGENS PIXABAY")

        url = (
            "https://pixabay.com/api/"
        )

        params = {

            "key": PIXABAY_API_KEY,

            "q": termo,

            "image_type": "photo",

            "per_page": quantidade,

            "safesearch": "true"

        }

        response = requests.get(

            url,

            params=params

        )

        data = response.json()

        print("✅ RESPOSTA PIXABAY")

        print(data.keys())

        return data.get(
            "hits",
            []
        )

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

        with open(
            path_arquivo,
            "rb"
        ) as f:

            supabase.storage.from_(

                BUCKET_NAME

            ).upload(

                nome_arquivo,

                f,

                {
                    "content-type":
                    "image/jpeg"
                }

            )

        public_url = supabase.storage.from_(

            BUCKET_NAME

        ).get_public_url(
            nome_arquivo
        )

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

            "tags": nicho

        }).execute()

        print("✅ SALVO DATABASE")

    except Exception as e:

        print("❌ ERRO DATABASE")

        print(str(e))

# =========================
# PROCESSO COMPLETO
# =========================

def executar_coleta(

    nicho="marketing",

    quantidade=10

):

    imagens = buscar_imagens_pixabay(

        nicho,

        quantidade

    )

    print(
        f"📸 TOTAL ENCONTRADO: {len(imagens)}"
    )

    for item in imagens:

        try:

            image_url = item.get(

                "largeImageURL"

            )

            if not image_url:

                continue

            print("⬇️ BAIXANDO")

            arquivo = baixar_imagem(
                image_url
            )

            if not arquivo:

                continue

            print("☁️ ENVIANDO SUPABASE")

            nova_url = upload_supabase(

                arquivo,

                nicho

            )

            if not nova_url:

                continue

            salvar_database(

                nicho,

                nova_url

            )

            print("✅ IMAGEM PROCESSADA")

        except Exception as e:

            print("❌ ERRO PROCESSAMENTO")

            print(str(e))

# =========================
# START
# =========================

if __name__ == "__main__":

    executar_coleta(

        nicho="marketing",

        quantidade=10

    )
