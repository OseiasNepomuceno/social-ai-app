import os
from apscheduler.schedulers.blocking import BlockingScheduler
from datetime import datetime
import json

print("Executor automático iniciado 🚀")

scheduler = BlockingScheduler()

# =========================
# VERIFICAR AGENDAMENTOS
# =========================

def verificar_agendamentos():

    try:

        with open(
            "scheduler/agendamentos.json",
            "r",
            encoding="utf-8"
        ) as file:

            agendamentos = json.load(file)

        agora = datetime.now()

        print(
            f"\n⏰ Verificando: {agora}"
        )

        data_atual = agora.strftime(
            "%d/%m/%Y"
        )

        hora_atual = agora.strftime(
            "%H:%M:%S"
        )

        alterado = False

        for post in agendamentos:

            if (
                post["data"] == data_atual
                and
                post["hora"] == hora_atual
                and
                post["status"] == "pendente"
            ):

                print("\n🚀 EXECUTANDO POSTAGEM")
                print(f"Tema: {post['tema']}")
                print(f"Rede: {post['rede']}")
                print(f"Arquivo: {post['arquivo']}")

                # =========================
                # LER CONTEÚDO
                # =========================

                with open(
                    post["arquivo"],
                    "r",
                    encoding="utf-8"
                ) as file:

                    conteudo = file.read()

                print("\n===== CONTEÚDO =====")
                print(conteudo)

                # =========================
                # PUBLICAÇÃO LINKEDIN
                # =========================

                if post["rede"] == "linkedin":
                    print(
                        "\n🚀 Enviando para LinkedIn..."
                    )

                    os.system(
                        "python linkedin/postar.py"
                    )

                # =========================
                # PUBLICAÇÃO INSTAGRAM
                # =========================

                if post["rede"] == "instagram":
                    print(
                        "\n🚀 Instagram ainda será integrado"
                    )



                # =========================
                # ALTERAR STATUS
                # =========================

                post["status"] = "executado"

                alterado = True

        # =========================
        # SALVAR ALTERAÇÕES
        # =========================

        if alterado:

            with open(
                "scheduler/agendamentos.json",
                "w",
                encoding="utf-8"
            ) as file:

                json.dump(
                    agendamentos,
                    file,
                    indent=4,
                    ensure_ascii=False
                )

                print("\n✅ Status atualizado.")

    except FileNotFoundError:

        print(
            "Arquivo JSON não encontrado."
        )

# =========================
# EXECUTAR A CADA 60 SEGUNDOS
# =========================

scheduler.add_job(
    verificar_agendamentos,
    "interval",
    seconds=1
)

print("Monitorando agendamentos...")

print(
    "\nSistema inteligente ativo 🚀"
)

scheduler.start()