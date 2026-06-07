import subprocess
import re

PICOCLAW_BIN = '/opt/render/project/src/tools/picoclaw'

def chamar_picoclaw(mensagem: str, timeout: int = 90) -> dict:
    print("🦞 PICOCLAW ACIONADO")
    try:
        resultado = subprocess.run(
            [PICOCLAW_BIN, 'agent', '-m', mensagem],
            capture_output=True,
            text=True,
            timeout=timeout
        )

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
            and not l.startswith('0')
        ]

        resposta = '\n'.join(linhas_limpas).strip()
        # Remove códigos ANSI de cor/formatação do terminal
        
        resposta = re.sub(r'\x1b\[[0-9;]*m', '', resposta)
        resposta = re.sub(r'\[0m', '', resposta)

        # Garante linha em branco entre parágrafos para LinkedIn
        resposta = '\n\n'.join(
            p.strip() for p in resposta.split('\n') if p.strip()
        )

        if resultado.returncode != 0 or not resposta:
            print(f"❌ PICOCLAW ERRO: {resultado.stderr.strip()}")
            return {
                "success": False,
                "erro": resultado.stderr.strip() or "Sem resposta do agente"
            }

        print(f"✅ PICOCLAW RESPONDEU: {len(resposta)} caracteres")
        return {
            "success": True,
            "conteudo": resposta
        }

    except subprocess.TimeoutExpired:
        print("⏱️ PICOCLAW TIMEOUT")
        return {"success": False, "erro": "Timeout: PicoClaw demorou demais para responder"}
    except Exception as e:
        print(f"❌ PICOCLAW EXCEÇÃO: {str(e)}")
        return {"success": False, "erro": str(e)}


def inferir_nicho(tema: str, lista_nichos: list) -> str:
    prompt = f"""Com base no tema abaixo, identifique qual é o nicho/segmento mais adequado.
Tema: {tema}
Nichos disponíveis: {', '.join(lista_nichos)}
Responda APENAS com o nome exato do nicho da lista, sem explicações."""
    
    resultado = chamar_picoclaw(prompt, timeout=30)
    if resultado.get("success"):
        nicho_inferido = resultado["conteudo"].strip()
        # Verifica se o nicho inferido está na lista
        for n in lista_nichos:
            if n.lower() in nicho_inferido.lower() or nicho_inferido.lower() in n.lower():
                return n
    return "Negócios"  # fallback padrão


def gerar_post_picoclaw(tema: str, rede: str, modo: str, nicho: str) -> dict:
    print(f"📝 GERANDO POST PICOCLAW: tema='{tema}' rede='{rede}' modo='{modo}' nicho='{nicho}'")
    prompt = f"""Crie um post profissional para {rede} sobre: {tema}
Nicho: {nicho}
Objetivo: {modo}
Idioma: Português do Brasil

FORMATAÇÃO OBRIGATÓRIA:
- Título impactante na primeira linha
- Uma linha em branco entre cada parágrafo
- Máximo 3 parágrafos curtos e diretos
- Emoji no início de cada parágrafo
- Hashtags na última linha
- SEM markdown como ** ou *
- Texto humanizado e conversacional"""

    return chamar_picoclaw(prompt)
