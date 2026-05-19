from apscheduler.schedulers.blocking import (
    BlockingScheduler
)

from datetime import datetime

from zoneinfo import ZoneInfo

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
            f"🚀 Publicando no LinkedIn: {post['tema']}"
        )

        print(
            f"🖼️ Imagem: {post.get('imagem_url')}"
        )

        print(
            f"📝 Conteúdo:\n{post['conteudo']}"
        )

        # =========================
        # FUTURA API LINKEDIN
        # =========================

        return True

    except Exception as e:

        print(
            "❌ ERRO LINKEDIN:"
        )

        print(str(e))

        return False

# =========================
# VERIFICAR AGENDAMENTOS
# =========================

def verificar_agendamentos():

    print(
        "\n⏰ Verificando agendamentos..."
    )

    try:

        posts = supabase.table(
            "posts"
        ).select("*").eq(
            "status",
            "pendente"
        ).execute().data

        # =========================
        # HORÁRIO BRASIL
        # =========================

        agora = datetime.now(
            ZoneInfo("America/Sao_Paulo")
        ).replace(tzinfo=None)

        print(
            f"🕒 Horário atual: {agora}"
        )

        print(
            f"📦 Total pendentes: {len(posts)}"
        )

        for post in posts:

            try:

                print(
                    "\n========================="
                )

                print(
                    f"📌 Post encontrado: {post['tema']}"
                )

                print(
                    f"🌐 Rede: {post['rede']}"
                )

                print(
                    f"📅 Data: {post['data_postagem']}"
                )

                print(
                    f"⏰ Hora: {post['hora_postagem']}"
                )

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

                print(
                    f"🕓 Agendado para: {data_hora}"
                )

                # =========================
                # PUBLICAR SOMENTE
                # NO HORÁRIO CERTO
                # =========================

                if agora >= data_hora:

                    print(
                        "✅ Horário atingido"
                    )

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
                            "📸 Instagram em breve"
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

                else:

                    print(
                        "⌛ Ainda não chegou o horário"
                    )

            except Exception as post_error:

                print(
                    "❌ ERRO POST:"
                )

                print(str(post_error))

    except Exception as e:

        print(
            "❌ ERRO SCHEDULER:"
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

print(
    "🇧🇷 Timezone: America/Sao_Paulo"
)

scheduler.start()
