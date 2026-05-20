import sys
import os
import time
print("EXECUTOR SAAS INICIANDO")

from datetime import datetime
from zoneinfo import ZoneInfo

# =========================
# PATH ROOT PROJETO
# =========================

ROOT_DIR = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        ".."
    )
)

sys.path.append(ROOT_DIR)



# =========================
# IMPORTS
# =========================

from supabase import create_client
from linkedin.postar import publicar_linkedin

print("ROOT_DIR:", ROOT_DIR)
print("IMPORTS OK")
print("EXECUTOR SAAS INICIANDO")

# =========================
# ENV
# =========================

SUPABASE_URL = os.getenv(
    "SUPABASE_URL",
    ""
).strip()

SUPABASE_KEY = os.getenv(
    "SUPABASE_KEY",
    ""
).strip()

print("SUPABASE_URL:", bool(SUPABASE_URL))
print("SUPABASE_KEY:", bool(SUPABASE_KEY))
print("URL USADA:")
print(SUPABASE_URL)

if not SUPABASE_URL or not SUPABASE_KEY:

    raise Exception(
        "Variáveis Supabase ausentes"
    )

# =========================
# SUPABASE
# =========================

supabase = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)

print("SUPABASE CONECTADO")

# =========================
# VERIFICAR LIMITE
# =========================

def pode_publicar(user):

    plano = user.get(
        "plano",
        "gratuito"
    )

    usados = user.get(
        "posts_usados",
        0
    )

    limite = user.get(
        "posts_limite",
        10
    )

    if plano == "business":

        return True

    return usados < limite

# =========================
# EXECUTAR POST
# =========================

def executar_post(post, user):

    try:

        print("\n🚀 EXECUTANDO POST")

        print(
            "Usuário:",
            user.get("email")
        )

        print(
            "Tema:",
            post.get("tema")
        )

        print(
            "Rede:",
            post.get("rede")
        )

        conteudo = post.get(
            "conteudo",
            ""
        )

        print("\n===== CONTEÚDO =====")

        print(conteudo)

        # =========================
        # REDE SOCIAL
        # =========================

        rede = post.get(
            "rede",
            ""
        ).lower()

        # =========================
        # LINKEDIN
        # =========================

        if rede == "linkedin":

            print(
                "🚀 Publicando no LinkedIn..."
            )

            image_url = post.get(
                "imagem_url"
            )

            sucesso = publicar_linkedin(

                user["id"],

                conteudo,

                image_url

            )

            if not sucesso:

                print(
                    "❌ Falha publicação LinkedIn"
                )

                supabase.table(
                    "posts"
                ).update({

                    "status": "erro"

                }).eq(

                    "id",
                    post["id"]

                ).execute()

                return

        # =========================
        # INSTAGRAM
        # =========================

        elif rede == "instagram":

            print(
                "🚀 Instagram futuramente"
            )

        # =========================
        # REDE INVÁLIDA
        # =========================

        else:

            print(
                "❌ Rede social inválida"
            )

            supabase.table(
                "posts"
            ).update({

                "status": "erro"

            }).eq(

                "id",
                post["id"]

            ).execute()

            return

        # =========================
        # ALTERAR STATUS
        # =========================

        supabase.table(
            "posts"
        ).update({

            "status": "executado"

        }).eq(

            "id",
            post["id"]

        ).execute()

        # =========================
        # INCREMENTAR USO
        # =========================

        usuario = supabase.table(
            "users"
        ).select("*").eq(
            "id",
            user["id"]
        ).execute()

        if usuario.data:

            u = usuario.data[0]

            novo_total = u.get(
                "posts_usados",
                0
            ) + 1

            supabase.table(
                "users"
            ).update({

                "posts_usados": novo_total

            }).eq(

                "id",
                user["id"]

            ).execute()

        print("✅ Post executado")

    except Exception as e:

        print(
            "❌ ERRO EXECUTANDO POST:",
            str(e)
        )

        supabase.table(
            "posts"
        ).update({

            "status": "erro"

        }).eq(

            "id",
            post["id"]

        ).execute()

# =========================
# LOOP PRINCIPAL
# =========================

def loop_executor():

    while True:

        try:

            print(
                "\n⏰ Verificando posts pendentes..."
            )

            # =========================
            # BUSCAR POSTS
            # =========================

            posts = supabase.table(
                "posts"
            ).select("*").eq(
                "status",
                "pendente"
            ).execute()

            posts = posts.data

            if not posts:

                print(
                    "Nenhum post pendente"
                )

                time.sleep(10)

                continue

            # =========================
            # LOOP POSTS
            # =========================

            for post in posts:

                try:

                    user_id = post.get(
                        "user_id"
                    )

                    print("USER_ID POST:")

                    print(user_id)

                    print(type(user_id))

                    if not user_id:

                        print(
                            "❌ Post sem user_id"
                        )

                        continue

                    # =========================
                    # BUSCAR USER
                    # =========================

                    user_res = supabase.table(
                        "users"
                    ).select("*").eq(
                        "id",
                        user_id
                    ).execute()

                    print("RESULTADO USER:")

                    print(user_res.data)

                    print("BUSCANDO USER...")

                    if not user_res.data:

                        print(
                            "❌ Usuário não encontrado"
                        )

                        continue

                    user = user_res.data[0]

                    # =========================
                    # VALIDAR LIMITE
                    # =========================

                    permitido = pode_publicar(
                        user
                    )

                    if not permitido:

                        print(
                            "🚫 Limite atingido:",
                            user.get("email")
                        )

                        supabase.table(
                            "posts"
                        ).update({

                            "status": "bloqueado"

                        }).eq(

                            "id",
                            post["id"]

                        ).execute()

                        continue

                    # =========================
                    # VALIDAR HORÁRIO
                    # =========================

                   data_post = post.get(
                       "data_postagem"
                   ) or post.get(
                       "data"
                   )

                   hora_post = post.get(
                       "hora_postagem"
                   ) or post.get(
                       "hora"
                   )

                    if not data_post or not hora_post:

                        print(
                            "❌ Data/Hora ausente"
                        )

                        continue

                    try:

                        data_hora = datetime.strptime(

                            f"{data_post} {hora_post}",

                            "%Y-%m-%d %H:%M:%S"

                        )

                    except:

                        data_hora = datetime.strptime(

                            f"{data_post} {hora_post}",

                            "%Y-%m-%d %H:%M"

                        )

                    agora = datetime.now(
                        ZoneInfo(
                            "America/Sao_Paulo"
                        )
                    ).replace(
                        tzinfo=None
                    )

                    print(
                        "🕒 Agora:",
                        agora
                    )

                    print(
                        "📅 Agendado:",
                        data_hora
                    )

                    # =========================
                    # AINDA NÃO CHEGOU
                    # =========================

                    if agora < data_hora:

                        print(
                            "⌛ Aguardando horário..."
                        )

                        continue

                    # =========================
                    # EVITAR DUPLICAÇÃO
                    # =========================

                    supabase.table(
                        "posts"
                    ).update({

                        "status": "processando"

                    }).eq(

                        "id",
                        post["id"]

                    ).execute()

                    # =========================
                    # EXECUTAR
                    # =========================

                    executar_post(
                        post,
                        user
                    )

                except Exception as e:

                    print(
                        "❌ Erro no loop do post:",
                        str(e)
                    )

        except Exception as e:

            print(
                "❌ ERRO GERAL:",
                str(e)
            )

        # =========================
        # INTERVALO
        # =========================

        time.sleep(10)

# =========================
# START
# =========================

if __name__ == "__main__":

    loop_executor()
