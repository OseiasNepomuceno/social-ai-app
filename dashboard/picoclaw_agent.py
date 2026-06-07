import subprocess
import re

PICOCLAW_BIN = '/opt/render/project/src/tools/picoclaw'

def chamar_picoclaw(mensagem: str, timeout: int = 60) -> dict:
    try:
        resultado = subprocess.run(
            [PICOCLAW_BIN, 'agent', '-m', mensagem],
            capture_output=True,
            text=True,
            timeout=timeout
        )

        # Remove o banner ASCII da saída
        saida = resultado.stdout.strip()
        linhas = saida.split('\n')
        linhas_limpas = [
            l for l in linhas
            if l.strip()
            and '█' not in l
            and '╚' not in l
            and '╔' not in l
            and '╗' not in l
            and '╝' not in l
            and '🦞' not in l
            and not l.startswith('0')  # remove timestamps de log
        ]

        resposta = '\n'.join(linhas_limpas).strip()

        if resultado.returncode != 0 or not resposta:
            return {
                "success": False,
                "erro": resultado.stderr.strip() or "Sem resposta do agente"
            }

        return {
            "success": True,
            "conteudo": resposta
        }

    except subprocess.TimeoutExpired:
        return {"success": False, "erro": "Timeout: PicoClaw demorou demais para responder"}
    except Exception as e:
        return {"success": False, "erro": str(e)}


def gerar_post_picoclaw(tema: str, rede: str, modo: str, nicho: str) -> dict:
    prompt = f"""
Crie um post profissional para {rede} sobre o tema: {tema}.
Nicho: {nicho}.
Formato: {modo}.
Escreva apenas o conteúdo do post, sem explicações adicionais.
Use emojis relevantes e hashtags no final.
Linguagem: Português do Brasil.
"""
    return chamar_picoclaw(prompt.strip())
