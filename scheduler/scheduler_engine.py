from apscheduler.schedulers.blocking import (
    BlockingScheduler
)

from datetime import datetime

from supabase import create_client

import os
import requests

# =========================
# SUPABASE
# =========================

SUPABASE_URL = os.getenv(
    "SUPABASE_URL"
)

SUPABASE_KEY = os.getenv(
    "SUPABASE_KEY"
)

supabase = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)

# =========================
# PUBLICAR LINKEDIN
# =========================

def publicar_linkedin(post):

    try:

        print(
            f"🚀 Publicando: {post['tema']}"
        )

        # =========================
        # AQUI ENTRARÁ
        # LINKEDIN API REAL
        # =========================

        # TEMPORÁRIO
        print(post["conteudo"])

        return True

    except Exception as e:

        print(
            "ERRO LINKEDIN:"
        )

        print(str(e))

        return False

# =========================
# VERIFICAR AGENDAMENTOS
# =========================

def verificar_agendamentos():

    print(
        "⏰ Verificando agendamentos..."
    )

    try:

        posts = supabase.table(
            "posts"
        ).select("*").eq(
            "status",
            "pendente"
        ).execute().data

        agora = datetime.now()

        for post in posts:

            try:

                data_post = (
                    post["data_postagem"]
                )

                hora_post = (
                    post["hora_postagem"]
                )

                data_hora = datetime.strptime(

                    f"{data_post} {hora_post}",

                    "%Y-%m-%d %H:%M"

                )

                # =========================
                # PUBLICAR SOMENTE
                # NO HORÁRIO CERTO
                # =========================

                if agora >= data_hora:

                    sucesso = False

                    # =========================
                    # LINKEDIN
                    # =========================

                    if post["rede"] == "linkedin":

                        sucesso = publicar_linkedin(
                            post
                        )

                    # =========================
                    # INSTAGRAM
                    # =========================

                    elif post["rede"] == "instagram":

                        print(
                            "Instagram em breve"
                        )

                    # =========================
                    # STATUS
                    # =========================

                    novo_status = (
                        "executado"
                        if sucesso
                        else "erro"
                    )

                    supabase.table(
                        "posts"
                    ).update({

                        "status": novo_status

                    }).eq(
                        "id",
                        post["id"]
                    ).execute()

                    print(
                        f"✅ Post atualizado: {novo_status}"
                    )

            except Exception as post_error:

                print(
                    "ERRO POST:"
                )

                print(str(post_error))

    except Exception as e:

        print(
            "ERRO SCHEDULER:"
        )

        print(str(e))

# =========================
# APSCHEDULER
# =========================

scheduler = BlockingScheduler()

scheduler.add_job(

    verificar_agendamentos,

    "interval",

    seconds=60

)

print(
    "🚀 Scheduler iniciado..."
)

scheduler.start()
