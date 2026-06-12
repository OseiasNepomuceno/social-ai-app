import re
import subprocess
import difflib
import unicodedata
import os
import requests

PICOCLAW_BIN = '/opt/render/project/src/tools/picoclaw'


# ─────────────────────────────────────────────
# API PORTAL DA TRANSPARENCIA
# ─────────────────────────────────────────────

API_TOKEN = os.getenv("API_TOKEN_TRANSPARENCIA")

def buscar_programas_federais():
    if not API_TOKEN:
        print("❌ ERRO: Token não configurado!")
        return []
        
    url = "https://api.portaldatransparencia.gov.br/api-de-dados/programas"
    
    # É AQUI que o header é montado conforme a instrução do site:
    headers = {
        "chave-api-dados": API_TOKEN
    }
    
    try:
        # A requisição passa o header como um dicionário
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ Erro na API: {response.status_code} - {response.text}")
            return []
    except Exception as e:
        print(f"❌ Erro ao conectar: {e}")
        return []


# ─────────────────────────────────────────────
# NÚCLEO — chama o PicoClaw gateway
# ─────────────────────────────────────────────
def chamar_picoclaw(mensagem: str, timeout: int = 90) -> dict:
    """Envia prompt ao PicoClaw gateway e retorna conteúdo limpo."""
    print(f"🦞 PICOCLAW ACIONADO — {len(mensagem)} chars no prompt")
    try:
        resultado = subprocess.run(
            [PICOCLAW_BIN, 'agent', '-m', mensagem],
            capture_output=True,
            text=True,
            timeout=timeout
        )
        saida = resultado.stdout.strip()

        # Remove linhas de UI do terminal (bordas, ícones, progresso)
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

        # Remove markdown desnecessário
        resposta = re.sub(r'\*\*(.*?)\*\*', r'\1', resposta)
        resposta = re.sub(r'\*(.*?)\*', r'\1', resposta)

        # Garante parágrafos separados por linha em branco
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
        return {"success": True, "conteudo": resposta}

    except subprocess.TimeoutExpired:
        print("⏱️ PICOCLAW TIMEOUT")
        return {"success": False, "erro": "Timeout: PicoClaw demorou demais para responder"}
    except Exception as e:
        print(f"❌ PICOCLAW EXCEÇÃO: {str(e)}")
        return {"success": False, "erro": str(e)}


# ─────────────────────────────────────────────
# UTILITÁRIOS
# ─────────────────────────────────────────────
def normalize(text: str) -> str:
    return ''.join(
        c for c in unicodedata.normalize('NFD', text)
        if unicodedata.category(c) != 'Mn'
    ).lower()


def inferir_nicho(tema: str, lista_nichos: list) -> str:
    """Usa o PicoClaw para inferir o nicho mais adequado ao tema."""
    prompt = f"""Com base no tema abaixo, identifique qual é o nicho/segmento mais adequado.
Tema: {tema}
Nichos disponíveis: {', '.join(lista_nichos)}
Responda APENAS com o nome exato do nicho da lista, sem explicações."""

    resultado = chamar_picoclaw(prompt, timeout=30)
    if resultado.get("success"):
        nicho_inferido = resultado["conteudo"].strip()
        nicho_inferido_norm = normalize(nicho_inferido)
        lista_norm = [normalize(n) for n in lista_nichos]

        for i, n_norm in enumerate(lista_norm):
            if n_norm == nicho_inferido_norm:
                return lista_nichos[i]

        match = difflib.get_close_matches(nicho_inferido_norm, lista_norm, n=1, cutoff=0.6)
        if match:
            idx = lista_norm.index(match[0])
            return lista_nichos[idx]

    return lista_nichos[0]


# ─────────────────────────────────────────────
# GERAÇÃO DE POST
# ─────────────────────────────────────────────
def gerar_post(tema: str, rede: str, modo: str, nicho: str) -> dict:
    """Gera post para redes sociais via PicoClaw."""
    print(f"📝 GERANDO POST: tema='{tema}' rede='{rede}' modo='{modo}' nicho='{nicho}'")

    prompt = f"""Crie um post profissional para {rede} sobre: {tema}
Nicho: {nicho}
Objetivo: {modo}
Idioma: Português do Brasil

FORMATAÇÃO OBRIGATÓRIA:
- Título impactante na primeira linha
- Uma linha em branco entre cada parágrafo
- Máximo 3 parágrafos curtos e diretos
- Emoji no início de cada parágrafo
- Hashtags relevantes na última linha (mínimo 5)
- SEM markdown como ** ou *
- Texto humanizado e conversacional
- Tom de autoridade no nicho"""

    return chamar_picoclaw(prompt)


# ─────────────────────────────────────────────
# GERAÇÃO DE ROTEIRO TIKTOK
# ─────────────────────────────────────────────
def gerar_roteiro_tiktok(tema: str, nicho: str = "geral", duracao: int = 60) -> dict:
    """Gera roteiro para vídeo no TikTok via PicoClaw."""
    print(f"🎬 GERANDO ROTEIRO TIKTOK: tema='{tema}' nicho='{nicho}' duração={duracao}s")

    prompt = f"""Crie um roteiro de vídeo para TikTok sobre: {tema}
Nicho: {nicho}
Duração alvo: {duracao} segundos
Idioma: Português do Brasil

ESTRUTURA OBRIGATÓRIA:
[GANCHO - 0 a 3s]
(frase de impacto que prende atenção imediatamente)

[PROBLEMA/CONTEXTO - 3 a 15s]
(apresente o problema ou situação que o espectador se identifica)

[DESENVOLVIMENTO - 15 a 45s]
(3 dicas ou pontos principais, cada um em 1-2 frases diretas)

[CTA FINAL - 45 a {duracao}s]
(chamada para ação: curtir, seguir, comentar ou acessar link na bio)

REGRAS:
- Linguagem informal e direta
- Frases curtas (máximo 15 palavras cada)
- SEM markdown
- Inclua sugestão de legenda e 5 hashtags no final"""

    return chamar_picoclaw(prompt, timeout=90)


# ─────────────────────────────────────────────
# GERAÇÃO DE CTA
# ─────────────────────────────────────────────
def gerar_cta(tema: str, nicho: str, objetivo: str, canal: str = "site") -> dict:
    """Gera Call To Action para diferentes canais via PicoClaw."""
    print(f"📣 GERANDO CTA: tema='{tema}' nicho='{nicho}' objetivo='{objetivo}' canal='{canal}'")

    prompt = f"""Crie 5 variações de Call To Action (CTA) para: {tema}
Nicho: {nicho}
Objetivo do CTA: {objetivo}
Canal: {canal}
Idioma: Português do Brasil

PARA CADA CTA ENTREGUE:
- Título curto (máximo 8 palavras) — linha 1
- Subtítulo de apoio (máximo 15 palavras) — linha 2
- Texto do botão (máximo 4 palavras) — linha 3
- Separador: ---

REGRAS:
- Linguagem persuasiva e orientada à ação
- Use verbos de ação no imperativo
- Gere urgência ou benefício claro
- SEM markdown"""

    return chamar_picoclaw(prompt, timeout=60)


# ─────────────────────────────────────────────
# GERAÇÃO DE E-BOOK
# ─────────────────────────────────────────────
def gerar_ebook(tema: str, nicho: str, publico_alvo: str, num_capitulos: int = 5) -> dict:
    """Gera estrutura completa e conteúdo de e-book via PicoClaw."""
    print(f"📚 GERANDO E-BOOK: tema='{tema}' nicho='{nicho}' público='{publico_alvo}'")

    capitulos = ''.join([
        f"CAPÍTULO {i+1}: [título do capítulo]\n"
        f"(3 parágrafos com conteúdo relevante, dicas práticas e exemplos)\n\n"
        for i in range(num_capitulos)
    ])

    prompt = f"""Crie um e-book completo sobre: {tema}
Nicho: {nicho}
P�blico-alvo: {publico_alvo}
Número de capítulos: {num_capitulos}
Idioma: Português do Brasil

ESTRUTURA OBRIGATÓRIA:

TÍTULO DO E-BOOK:
(título chamativo e orientado ao benefício)

SUBTÍTULO:
(complemento que reforça o valor)

INTRODUÇÃO:
(2 parágrafos apresentando o problema e a promessa do e-book)

{capitulos}
CONCLUSÃO:
(1 parágrafo com recapitulação e CTA final)

REGRAS:
- Linguagem profissional mas acessível
- Conteúdo prático e acionável
- SEM markdown como ** ou *
- Cada capítulo com conteúdo real, não resumo"""

    return chamar_picoclaw(prompt, timeout=120)


# ─────────────────────────────────────────────
# GERAÇÃO DE INFOGRÁFICO
# ─────────────────────────────────────────────
def gerar_infografico(tema: str, nicho: str, formato: str = "lista") -> dict:
    """Gera conteúdo textual para infográfico via PicoClaw."""
    print(f"📊 GERANDO INFOGRÁFICO: tema='{tema}' nicho='{nicho}' formato='{formato}'")

    prompt = f"""Crie o conteúdo para um infográfico sobre: {tema}
Nicho: {nicho}
Formato: {formato} (pode ser: lista, processo, comparação, estatísticas, timeline)
Idioma: Português do Brasil

ESTRUTURA OBRIGATÓRIA:

TÍTULO PRINCIPAL:
(título curto e impactante, máximo 8 palavras)

SUBTÍTULO:
(complemento explicativo, máximo 12 palavras)

BLOCOS DE CONTEÚDO (mínimo 5, máximo 8):
BLOCO 1:
- Ícone sugerido: (emoji representativo)
- Título do bloco: (3-5 palavras)
- Texto: (máximo 2 frases diretas)

(repita o padrão para cada bloco)

RODAPÉ:
- Fonte/crédito sugerido
- CTA curto (máximo 6 palavras)

REGRAS:
- Informações factuais e verificáveis
- Linguagem direta e escaneável
- SEM markdown"""

    return chamar_picoclaw(prompt, timeout=90)


# ─────────────────────────────────────────────
# GERAÇÃO DE TEMPLATE
# ─────────────────────────────────────────────
def gerar_template(tipo: str, nicho: str, tema: str) -> dict:
    """Gera template reutilizável de conteúdo via PicoClaw."""
    print(f"📋 GERANDO TEMPLATE: tipo='{tipo}' nicho='{nicho}' tema='{tema}'")

    prompt = f"""Crie um template reutilizável de {tipo} para o nicho: {nicho}
Tema base: {tema}
Idioma: Português do Brasil

O template deve ter variáveis entre colchetes como [TEMA], [BENEFÍCIO], [NÚMERO], etc.
para que possa ser reutilizado facilmente.

ENTREGUE:
1. O template completo com variáveis
2. Exemplo preenchido com dados fictícios do nicho
3. Dicas de personalização (3 sugestões)

REGRAS:
- Template prático e profissional
- Variáveis claramente identificadas com [COLCHETES]
- SEM markdown"""

    return chamar_picoclaw(prompt, timeout=60)


# ─────────────────────────────────────────────
# ALIASES DE COMPATIBILIDADE (legado)
# ─────────────────────────────────────────────
gerar_post_picoclaw = gerar_post
chamar_deepseek = chamar_picoclaw
