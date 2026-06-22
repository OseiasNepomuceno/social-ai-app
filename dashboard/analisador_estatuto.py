"""
analisador_estatuto.py — Motor de análise de estatutos de ONGs/OSCs

Verifica se o estatuto está adequado para captação de recursos com base em:
- Lei Federal nº 13.019/2014 (MROSC)
- Decreto Federal nº 8.726/2016
- Lei nº 8.313/1991 (Lei Rouanet)
- Instrução Normativa MinC nº 29/2026
- Legislação complementar (Lei 13.204/2015, Lei 13.019 alterações)
"""

import os
import json
import re
import tempfile
from datetime import datetime
from fpdf import FPDF
import requests  # <-- adicionado para API direta

# Tenta importar PyMuPDF para extrair texto de PDF
try:
    import fitz  # PyMuPDF
    PYMUPDF_OK = True
except ImportError:
    PYMUPDF_OK = False

# ---------- CHECKLIST DE CONFORMIDADE LEGAL ----------

REQUISITOS_MROSC = [
    {
        "id": "clausula_objetivos",
        "titulo": "Cláusula de Objetivos Sociais",
        "descricao": "O estatuto deve definir claramente os objetivos sociais da OSC, alinhados a atividades de interesse público.",
        "base_legal": "Lei 13.019/2014, Art. 2º",
        "peso": 5
    },
    {
        "id": "clausula_gestao",
        "titulo": "Estrutura de Gestão e Administração",
        "descricao": "Deve prever diretoria, conselho fiscal e assembleia geral com regras claras de eleição, mandato e atribuições.",
        "base_legal": "Lei 13.019/2014, Art. 33; Decreto 8.726/2016, Art. 2º",
        "peso": 5
    },
    {
        "id": "clausula_conselho_fiscal",
        "titulo": "Conselho Fiscal",
        "descricao": "O conselho fiscal é obrigatório e deve ter no mínimo 3 membros, com mandato definido e vedação a parentes da diretoria.",
        "base_legal": "Decreto 8.726/2016, Art. 2º, §2º",
        "peso": 4
    },
    {
        "id": "clausula_sem_fins_lucrativos",
        "titulo": "Declaração de Sem Fins Lucrativos",
        "descricao": "O estatuto deve declarar expressamente que a organização não distribui lucros ou resultados entre seus membros.",
        "base_legal": "Lei 13.019/2014, Art. 2º, I",
        "peso": 5
    },
    {
        "id": "clausula_aplicacao_recursos",
        "titulo": "Aplicação de Recursos no País",
        "descricao": "Deve prever que os recursos serão aplicados integralmente no território nacional e na manutenção dos objetivos sociais.",
        "base_legal": "Lei 13.019/2014, Art. 2º, II",
        "peso": 4
    },
    {
        "id": "clausula_prestacao_contas",
        "titulo": "Prestação de Contas",
        "descricao": "O estatuto deve prever a obrigatoriedade de prestação de contas e transparência na gestão dos recursos.",
        "base_legal": "Lei 13.019/2014, Art. 2º, III; Art. 64",
        "peso": 5
    },
    {
        "id": "clausula_escrituracao",
        "titulo": "Escrituração Contábil",
        "descricao": "Deve prever a manutenção de escrituração contábil regular, de acordo com as normas brasileiras de contabilidade.",
        "base_legal": "Decreto 8.726/2016, Art. 4º",
        "peso": 4
    },
    {
        "id": "clausula_constituicao_regular",
        "titulo": "Constituição Legal Regular",
        "descricao": "Deve comprovar constituição há pelo menos 1 ano (para MROSC) ou 3 anos (para Lei Rouanet) como pessoa jurídica.",
        "base_legal": "Lei 13.019/2014, Art. 33, I; Lei 8.313/1991",
        "peso": 3
    },
    {
        "id": "clausula_alteracao_estatuto",
        "titulo": "Procedimento de Alteração do Estatuto",
        "descricao": "Deve prever como o estatuto pode ser alterado, com quórum mínimo e aprovação da assembleia.",
        "base_legal": "Código Civil, Art. 59",
        "peso": 4
    },
    {
        "id": "clausula_extincao",
        "titulo": "Destinação do Patrimônio em Caso de Extinção",
        "descricao": "Em caso de extinção, o patrimônio deve ser destinado a outra OSC com objetivos similares ou a entidade pública.",
        "base_legal": "Lei 13.019/2014, Art. 2º, IV; Código Civil, Art. 61",
        "peso": 4
    },
    {
        "id": "clausula_assembleia",
        "titulo": "Assembleia Geral",
        "descricao": "Deve prever assembleia geral como órgão soberano, com regras de convocação, quórum e deliberação.",
        "base_legal": "Código Civil, Arts. 59 e 60",
        "peso": 4
    },
    {
        "id": "clausula_publicidade_atos",
        "titulo": "Publicidade dos Atos",
        "descricao": "Deve prever a divulgação pública dos atos de gestão, relatórios financeiros e parcerias firmadas.",
        "base_legal": "Lei 13.019/2014, Art. 11",
        "peso": 3
    },
    {
        "id": "clausula_impedimentos",
        "titulo": "Vedações e Impedimentos de Dirigentes",
        "descricao": "Deve prever impedimentos para dirigentes que tenham parentesco ou vínculo com poder público.",
        "base_legal": "Lei 13.019/2014, Art. 39",
        "peso": 4
    },
    {
        "id": "clausula_transparencia",
        "titulo": "Transparência e Controle Social",
        "descricao": "Deve prever mecanismos de transparência e participação social na fiscalização das atividades.",
        "base_legal": "Lei 13.019/2014, Arts. 10 e 11",
        "peso": 3
    },
]


def extrair_texto_pdf(caminho_pdf):
    """Extrai texto de um arquivo PDF usando PyMuPDF."""
    if not PYMUPDF_OK:
        return None, "Biblioteca PyMuPDF não disponível para extrair PDF."
    try:
        doc = fitz.open(caminho_pdf)
        texto = ""
        for pagina in doc:
            texto += pagina.get_text()
        doc.close()
        if not texto.strip():
            return None, "Não foi possível extrair texto do PDF. O arquivo pode ser composto apenas de imagens."
        return texto.strip(), None
    except Exception as e:
        return None, f"Erro ao extrair texto do PDF: {str(e)}"


def analisar_estatuto_picoclaw(texto_estatuto, nome_org=""):
    """
    Envia o estatuto para o PicoClaw analisar.
    Retorna dict com análise estruturada.
    """
    from dashboard.picoclaw_agent import chamar_picoclaw

    prompt = f"""
Você é um especialista em direito do terceiro setor e captação de recursos para OSCs.

Analise o estatuto social abaixo da organização "{nome_org}" e identifique se ele está adequado para captação de recursos públicos e privados.

LEGISLAÇÃO DE REFERÊNCIA:
1. Lei Federal nº 13.019/2014 (MROSC) — Marco Regulatório das Organizações da Sociedade Civil
2. Decreto Federal nº 8.726/2016 — Regulamenta o MROSC
3. Lei nº 8.313/1991 (Lei Rouanet) — Incentivo à cultura
4. Instrução Normativa MinC nº 29/2026 — Diretrizes culturais
5. Lei nº 13.204/2015 — Alterações do MROSC
6. Código Civil Brasileiro (Arts. 53 a 61) — Associações

CRITÉRIOS PARA ANALISAR (verifique cada um):
1. Cláusula de Objetivos Sociais — Define claramente os objetivos?
2. Estrutura de Gestão — Diretoria, conselho fiscal, assembleia?
3. Sem Fins Lucrativos — Declara expressamente?
4. Aplicação de Recursos — Prevê aplicação no país?
5. Prestação de Contas — Obrigatoriedade prevista?
6. Escrituração Contábil — Prevê contabilidade regular?
7. Conselho Fiscal — Mínimo 3 membros, mandato definido?
8. Alteração do Estatuto — Procedimento claro?
9. Destinação de Patrimônio — Em caso de extinção?
10. Transparência — Mecanismos previstos?
11. Vedações a Dirigentes — Impedimentos previstos?
12. Assembleia Geral — Convocação, quórum?

IMPORTANTE: Responda APENAS com o JSON abaixo. NÃO adicione texto antes ou depois do JSON. NÃO use markdown. Apenas o JSON bruto.

{{
  "orgao": "{nome_org}",
  "data_analise": "{datetime.now().strftime('%Y-%m-%d')}",
  "status_geral": "adequado|parcial|inadequado",
  "pontuacao": 0-100,
  "itens_analisados": [
    {{
      "id": "item_1",
      "item": "Objetivos Sociais",
      "status": "ok|atencao|falta",
      "descricao": "Descrição do que foi encontrado",
      "base_legal": "Lei 13.019/2014, Art. 2º",
      "recomendacao": "O que precisa ser alterado"
    }}
  ],
  "pontos_fortes": ["Lista de pontos positivos"],
  "pontos_criticos": ["Lista de pontos que impedem captação"],
  "recomendacoes_gerais": "Resumo das recomendações",
  "pode_captar_recursos": true/false,
  "resumo_curto": "Resumo de 2-3 frases para o relatório"
}}

ESTATUTO:
{texto_estatuto[:8000]}
"""

    try:
        resultado = chamar_picoclaw(prompt)
        if not resultado or not resultado.get("success"):
            return None, resultado.get("erro", "Falha na análise da IA")

        conteudo = resultado.get("conteudo", "")

        # Usar raw_decode para extrair o primeiro JSON válido,
        # ignorando qualquer texto extra antes ou depois
        decoder = json.JSONDecoder()
        idx = 0
        # Pular texto antes do primeiro {
        primeiro_brace = conteudo.find('{')
        if primeiro_brace >= 0:
            idx = primeiro_brace

        try:
            dados, idx_lido = decoder.raw_decode(conteudo, idx)
            return dados, None
        except json.JSONDecodeError:
            # Fallback: tentar achar bloco JSON entre chaves
            json_match = re.search(r'\{.*\}', conteudo, re.DOTALL)
            if json_match:
                try:
                    dados = json.loads(json_match.group())
                    return dados, None
                except json.JSONDecodeError:
                    pass

            # Fallback final: retornar dict parcial com o que temos
            return {
                "orgao": nome_org,
                "status_geral": "parcial",
                "pontuacao": 50,
                "resumo_curto": conteudo[:500]
            }, None

    except Exception as e:
        return None, f"Erro na análise: {str(e)}"


def sanitizar_texto_pdf(texto):
    """Remove caracteres não suportados pela fonte Helvetica do FPDF."""
    if not texto:
        return texto
    # Substitui emojis e caracteres especiais por alternativas ASCII
    substituicoes = {
        '✅': '[OK]', '⚠️': '[!]', '❌': '[X]', '❓': '[?]',
        '📋': '[LISTA]', '💡': '[DICA]', '🚀': '[AVANCO]',
        '➡': '->', '—': '-', '–': '-', '🔴': '[V]',
        '🟢': '[V]', '🟡': '[!]', '🔵': '[I]',
        '👤': '[USUARIO]', '📅': '[DATA]', '💰': '[DINHEIRO]',
        '🏆': '[VITORIA]', '⭐': '[DESTAQUE]', '🔗': '[LINK]',
        '📝': '[NOTA]', '📄': '[DOC]', '⚡': '[ALERTA]',
        '🎯': '[ALVO]', '💪': '[FORCA]', '🤝': '[PARCERIA]',
        '🌐': '[WEB]', '🔒': '[SEGURO]', '🔓': '[ABERTO]',
    }
    for emoji, replacement in substituicoes.items():
        texto = texto.replace(emoji, replacement)
    # Remove quaisquer outros caracteres não-ASCII que o FPDF não suporta
    import unicodedata
    resultado = []
    for char in texto:
        try:
            char.encode('latin-1')
            resultado.append(char)
        except UnicodeEncodeError:
            # Tenta substituir por similar ASCII ou remove
            try:
                simplificado = unicodedata.normalize('NFKD', char).encode('ascii', 'ignore').decode('ascii')
                if simplificado:
                    resultado.append(simplificado)
            except:
                pass
    return ''.join(resultado)


def gerar_pdf_diagnostico(analise, nome_cliente="", email_cliente=""):
    """Gera PDF com o diagnóstico do estatuto."""
    # Sanitizar todos os campos de texto para evitar erros de fonte no PDF
    for key in ['orgao', 'resumo_curto', 'status_geral', 'recomendacoes_gerais']:
        if key in analise and isinstance(analise[key], str):
            analise[key] = sanitizar_texto_pdf(analise[key])
    for item in analise.get('itens_analisados', []):
        for key in ['item', 'descricao', 'base_legal', 'recomendacao']:
            if key in item and isinstance(item[key], str):
                item[key] = sanitizar_texto_pdf(item[key])
    if 'pontos_fortes' in analise and isinstance(analise['pontos_fortes'], list):
        analise['pontos_fortes'] = [sanitizar_texto_pdf(p) for p in analise['pontos_fortes']]
    if 'pontos_criticos' in analise and isinstance(analise['pontos_criticos'], list):
        analise['pontos_criticos'] = [sanitizar_texto_pdf(p) for p in analise['pontos_criticos']]

    pdf = FPDF()
    pdf.add_page()

    # Cores Coregov
    AZUL = (15, 52, 96)      # #0f3460
    VERMELHO = (233, 69, 96)  # #e94560
    DOURADO = (245, 197, 24)  # #f5c518
    CINZA = (100, 116, 139)

    # === CAPA ===
    pdf.set_fill_color(*AZUL)
    pdf.rect(0, 0, 210, 297, 'F')

    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 28)
    pdf.ln(40)
    pdf.cell(0, 15, "DIAGNOSTICO DE ESTATUTO", ln=True, align="C")
    pdf.set_font("Helvetica", "", 14)
    pdf.cell(0, 10, "Analise de Conformidade Legal para Captacao de Recursos", ln=True, align="C")

    pdf.ln(10)
    pdf.set_font("Helvetica", "", 12)
    pdf.cell(0, 8, f"Organizacao: {analise.get('orgao', nome_cliente)}", ln=True, align="C")
    pdf.cell(0, 8, f"Data: {analise.get('data_analise', datetime.now().strftime('%d/%m/%Y'))}", ln=True, align="C")

    pdf.ln(30)
    pdf.set_font("Helvetica", "I", 10)
    pdf.set_text_color(DOURADO[0], DOURADO[1], DOURADO[2])
    pdf.cell(0, 8, "coregov.com.br  |  @coregov", ln=True, align="C")

    # === PÁGINA 2: RESUMO ===
    pdf.add_page()
    pdf.set_fill_color(*AZUL)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 12, "  RESUMO DA ANALISE", ln=True, fill=True)

    pdf.ln(8)
    status = analise.get("status_geral", "parcial")
    pontuacao = analise.get("pontuacao", 0)

    # Barra de pontuação
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(*AZUL)
    pdf.cell(0, 8, f"Pontuacao de Conformidade: {pontuacao}/100", ln=True)

    # Barra visual
    cor_barra = VERMELHO if pontuacao < 40 else (DOURADO if pontuacao < 70 else (34, 197, 94))
    pdf.set_fill_color(*cor_barra)
    pdf.rect(20, pdf.get_y(), min(170 * pontuacao / 100, 170), 8, 'F')
    pdf.set_fill_color(230, 230, 230)
    pdf.rect(20 + min(170 * pontuacao / 100, 170), pdf.get_y(), 170 - min(170 * pontuacao / 100, 170), 8, 'F')
    pdf.ln(12)

    # Status textual
    status_texto = {
        "adequado": "[OK] ADEQUADO - Estatuto atende aos requisitos legais",
        "parcial": "[ATENCAO] PARCIAL - Estatuto precisa de ajustes",
        "inadequado": "[INADEQUADO] INADEQUADO - Estatuto precisa ser reformulado"
    }
    pdf.set_font("Helvetica", "B", 11)
    cor_status = (34, 197, 94) if status == "adequado" else (DOURADO if status == "parcial" else VERMELHO)
    pdf.set_text_color(*cor_status)
    pdf.cell(0, 8, status_texto.get(status, "Analise pendente"), ln=True)

    pdf.ln(4)
    pdf.set_text_color(*CINZA)
    pdf.set_font("Helvetica", "", 10)
    pode_captar = analise.get("pode_captar_recursos", False)
    if pode_captar:
        pdf.cell(0, 8, "Pode captar recursos: SIM", ln=True)
    else:
        pdf.set_text_color(*VERMELHO)
        pdf.cell(0, 8, "Pode captar recursos: NAO - Estatuto precisa de atualizacao!", ln=True)

    pdf.ln(6)
    pdf.set_text_color(*AZUL)
    pdf.set_font("Helvetica", "", 10)
    resumo = analise.get("resumo_curto", "")
    if resumo:
        pdf.multi_cell(0, 6, resumo)

    # === ITENS ANALISADOS === (omitido na versão gratuita — é o serviço pago)
    # Os detalhes de cada item, recomendações e o que alterar
    # são EXIBIDOS apenas quando o cliente CONTRATA o serviço

    # === RECOMENDAÇÕES ===
    pdf.add_page()
    pdf.set_fill_color(*AZUL)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 12, "  PROXIMOS PASSOS", ln=True, fill=True)
    pdf.ln(8)

    pdf.set_text_color(*AZUL)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, "O que o diagnostico revelou:", ln=True)
    pdf.ln(4)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(*CINZA)
    pdf.multi_cell(0, 6, (
        f"Seu estatuto recebeu uma pontuacao de {pontuacao}/100, "
        f"sendo classificado como \"{status_texto.get(analise.get('status_geral'), 'pendente')}\". "
        f"{'Isso significa que a organizacao ATENDE aos requisitos minimos para captacao.' if pode_captar else 'Isso significa que a organizacao NAO ATENDE aos requisitos e precisa de atualizacoes urgentes.'}"
    ))
    pdf.ln(6)

    pdf.set_text_color(*VERMELHO)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, "Para visualizar as alteracoes necessarias em detalhes:", ln=True)
    pdf.ln(4)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(*CINZA)
    pdf.multi_cell(0, 6, (
        "O relatorio completo com cada clausula analisada, recomendacoes especificas "
        "de alteracao e prioridades e FORNECIDO MEDIANTE CONTRATACAO DO SERVICO "
        "DE ATUALIZACAO DE ESTATUTO pela COREGOV."
    ))

    # === CTA ===
    pdf.ln(10)
    pdf.set_fill_color(*VERMELHO)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 14, "  PRECISA ATUALIZAR SEU ESTATUTO?", ln=True, fill=True, align="C")
    pdf.ln(6)

    pdf.set_text_color(*AZUL)
    pdf.set_font("Helvetica", "", 11)
    pdf.multi_cell(0, 6, (
        "A COREGOV e especialista em regularizacao de OSCs e captacao de recursos. "
        "Podemos atualizar seu estatuto, criar o plano de negocios e preparar sua "
        "organizacao para captar recursos federais e estaduais."
    ))
    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, "Fale conosco: coregov.com.br  |  @coregov", ln=True, align="C")

    # Rodapé
    pdf.ln(10)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(*CINZA)
    pdf.cell(0, 5, f"Documento gerado em {datetime.now().strftime('%d/%m/%Y as %H:%M')} - COREGOV Diagnostico de Estatuto", ln=True, align="C")
    pdf.cell(0, 5, "Este documento e uma analise automatizada e nao substitui consultoria juridica especializada.", ln=True, align="C")

    # Salvar em memória
    pdf_bytes = pdf.output(dest='S').encode('utf-8')
    return pdf_bytes


def gerar_relatorio_markdown(analise):
    """Gera relatório textual para exibição na tela."""
    status = analise.get("status_geral", "parcial")
    pontuacao = analise.get("pontuacao", 0)

    emoji_status = {"adequado": "✅", "parcial": "⚠️", "inadequado": "❌"}
    label_status = {"adequado": "Adequado", "parcial": "Atenção necessária", "inadequado": "Reformulação urgente"}

    linhas = []
    linhas.append(f"# Diagnóstico do Estatuto")
    linhas.append(f"")
    linhas.append(f"**Organização:** {analise.get('orgao', 'Não informada')}")
    linhas.append(f"**Data:** {analise.get('data_analise', datetime.now().strftime('%d/%m/%Y'))}")
    linhas.append(f"")
    linhas.append(f"## Pontuação: {pontuacao}/100")
    linhas.append(f"")
    linhas.append(f"**Status: {emoji_status.get(status, '')} {label_status.get(status, 'Pendente')}**")
    linhas.append(f"")
    linhas.append(f"**Pode captar recursos:** {'✅ Sim' if analise.get('pode_captar_recursos') else '❌ Não'}")
    linhas.append(f"")
    if analise.get("resumo_curto"):
        linhas.append(f"### Resumo")
        linhas.append(f"{analise['resumo_curto']}")
        linhas.append(f"")

    if analise.get("pontos_fortes"):
        linhas.append(f"### ✅ Pontos Fortes")
        for p in analise["pontos_fortes"]:
            linhas.append(f"- {p}")
        linhas.append(f"")

    if analise.get("pontos_criticos"):
        linhas.append(f"### ❌ Pontos Críticos")
        for p in analise["pontos_criticos"]:
            linhas.append(f"- {p}")
        linhas.append(f"")

    if analise.get("itens_analisados"):
        linhas.append(f"### 📋 Detalhamento por Item")
        linhas.append(f"")
        for item in analise["itens_analisados"]:
            s = item.get("status", "")
            icone = {"ok": "✅", "atencao": "⚠️", "falta": "❌"}.get(s, "❓")
            linhas.append(f"**{icone} {item.get('item', 'Item')}**")
            if item.get("descricao"):
                linhas.append(f"> {item['descricao']}")
            if item.get("base_legal"):
                linhas.append(f"*Base: {item['base_legal']}*")
            if item.get("recomendacao"):
                linhas.append(f"*Recomendação: {item['recomendacao']}*")
            linhas.append(f"")

    if analise.get("recomendacoes_gerais"):
        linhas.append(f"### 💡 Recomendações Gerais")
        linhas.append(f"{analise['recomendacoes_gerais']}")

    return "\n".join(linhas)
