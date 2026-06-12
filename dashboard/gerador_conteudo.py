import json
import os
from datetime import datetime
from dashboard.picoclaw_agent import chamar_picoclaw

class GeradorConteudo:
    """Gera múltiplos conteúdos a partir de vídeo/imagem"""
    
    def __init__(self):
        self.tema = "Marketing Digital Básico"
        
    def processar_arquivo(self, caminho_arquivo, tipo, modulo):
        """
        Processa vídeo/imagem e gera conteúdos
        
        tipo: 'video' ou 'imagem'
        modulo: 1, 2 ou 3
        """
        
        print(f"📹 Processando {tipo}: {caminho_arquivo}")
        
        # Analisar arquivo com PicoClaw
        analise = self._analisar_com_picoclaw(caminho_arquivo, tipo)
        
        if not analise:
            return {"success": False, "erro": "Falha na análise com PicoClaw"}
        
        # Gerar conteúdos
        clips = self._gerar_clips(analise, modulo)
        videos = self._gerar_videos(analise, modulo)
        tiktok = self._gerar_post_tiktok(analise)
        linkedin = self._gerar_post_linkedin(analise)
        metadata = self._gerar_metadata(analise, modulo)
        
        return {
            "success": True,
            "conteudos": {
                "clips": clips,
                "videos": videos,
                "tiktok_caption": tiktok["caption"],
                "tiktok_hashtags": tiktok["hashtags"],
                "linkedin_caption": linkedin,
                "metadata": metadata
            }
        }
    
    def _analisar_com_picoclaw(self, caminho_arquivo, tipo):
    """Analisa arquivo com tratamento melhorado de erros"""
    
    prompt = f"""Analise este conteúdo de {tipo} sobre Marketing Digital:

ARQUIVO: {caminho_arquivo}

Extraia APENAS em JSON puro (sem markdown, sem backticks):
{{
  "titulo_principal": "título do conteúdo",
  "tema_principal": "tema abordado",
  "pontos_chave": ["ponto 1", "ponto 2", "ponto 3"],
  "target_audience": "público-alvo",
  "tone": "tom do conteúdo",
  "cta_principal": "call-to-action"
}}"""
    
    try:
        resultado = chamar_picoclaw(prompt, timeout=120)
        
        if not resultado.get("success"):
            print(f"⚠️ PicoClaw retornou sucesso=False: {resultado}")
            return None
        
        resposta = resultado["conteudo"]
        
        # Debug: imprimir resposta bruta
        print(f"📄 Resposta bruta do PicoClaw ({len(resposta)} chars):")
        print(resposta[:500])  # Primeiros 500 chars
        
        # Limpar resposta
        resposta = resposta.replace("```json", "").replace("```", "").strip()
        
        # Tentar parse JSON
        dados = json.loads(resposta)
        
        # Validar campos obrigatórios
        campos_obrig = ["titulo_principal", "tema_principal", "pontos_chave"]
        if not all(campo in dados for campo in campos_obrig):
            print(f"⚠️ JSON incompleto. Campos encontrados: {list(dados.keys())}")
            return None
        
        print(f"✅ Análise bem-sucedida!")
        return dados
        
    except json.JSONDecodeError as e:
        print(f"❌ Erro ao fazer parse JSON: {e}")
        print(f"   Resposta: {resposta[:200]}")
        return None
    except Exception as e:
        print(f"❌ Erro na análise: {e}")
        return None
    
    def _gerar_clips(self, analise, modulo):
        """Gera 2-3 clips de 15-30 segundos"""
        
        clips = []
        duracoes = [15, 30]
        
        for i, duracao in enumerate(duracoes, 1):
            clip = {
                "id": f"clip_m{modulo}_{i}",
                "titulo": f"Clip {i}: {analise.get('pontos_chave', [''])[i-1]}",
                "duracao": duracao,
                "tipo": "gratis",
                "modulo": modulo,
                "aula": i
            }
            clips.append(clip)
        
        return clips
    
    def _gerar_videos(self, analise, modulo):
        """Gera 2-3 vídeos de 1-2 minutos para módulos"""
        
        videos = []
        duracoes = ["1 min", "2 min"]
        
        for i, duracao in enumerate(duracoes, 1):
            video = {
                "id": f"video_m{modulo}_{i+1}",
                "titulo": f"Aula {i+1}: {analise.get('titulo_principal', 'Conteúdo')}",
                "duracao": duracao,
                "tipo": "pago",
                "modulo": modulo,
                "aula": i+1,
                "descricao": f"Aprenda sobre {analise.get('tema_principal', 'Marketing Digital')}"
            }
            videos.append(video)
        
        return videos
    
    def _gerar_post_tiktok(self, analise):
        """Gera caption e hashtags para TikTok"""
        
        prompt = f"""Crie um post para TikTok sobre Marketing Digital.

Tema: {analise.get('titulo_principal', '')}
Pontos-chave: {', '.join(analise.get('pontos_chave', []))}
Tom: descontraído, rápido, viral
Duração vídeo: 15-30 segundos

Responda em JSON (sem markdown):
{{
  "caption": "texto do caption (max 150 chars)",
  "hashtags": "#hash1 #hash2 #hash3"
}}"""
        
        resultado = chamar_picoclaw(prompt, timeout=30)
        
        if not resultado.get("success"):
            return {
                "caption": f"Aprenda sobre {analise.get('titulo_principal', 'Marketing Digital')} 📱",
                "hashtags": "#MarketingDigital #Marketing #Básico #Aula"
            }
        
        try:
            resposta = resultado["conteudo"]
            resposta = resposta.replace("```json", "").replace("```", "").strip()
            return json.loads(resposta)
        except:
            return {
                "caption": f"Aprenda sobre {analise.get('titulo_principal', 'Marketing Digital')} 📱",
                "hashtags": "#MarketingDigital #Marketing #Básico"
            }
    
    def _gerar_post_linkedin(self, analise):
        """Gera post profissional para LinkedIn"""
        
        prompt = f"""Crie um post para LinkedIn sobre Marketing Digital.

Tema: {analise.get('titulo_principal', '')}
Pontos-chave: {', '.join(analise.get('pontos_chave', []))}
Tom: profissional, educacional, B2B

Responda APENAS o texto do post (sem JSON):"""
        
        resultado = chamar_picoclaw(prompt, timeout=30)
        
        if not resultado.get("success"):
            return f"Explorando {analise.get('titulo_principal', 'Marketing Digital')}...\n\n{', '.join(analise.get('pontos_chave', []))}\n\nSaiba mais em nossa trilha de conhecimento."
        
        return resultado["conteudo"].strip()
    
    def _gerar_metadata(self, analise, modulo):
        """Gera metadata para trilha de conhecimento"""
        
        titulo = analise.get('titulo_principal', f'Módulo {modulo} - Marketing Digital')
        slug = titulo.lower().replace(' ', '-').replace('á', 'a').replace('é', 'e')
        descricao = f"Aprenda sobre {analise.get('tema_principal', 'Marketing Digital')}. " \
                   f"Nesta aula você vai conhecer: {', '.join(analise.get('pontos_chave', [])[:2])}"
        tags = ['marketing', 'digital', 'basico', analise.get('tema_principal', 'marketing').lower()]
        
        return {
            "titulo": titulo,
            "slug": slug,
            "descricao": descricao,
            "tags": tags,
            "modulo": modulo,
            "tema": self.tema,
            "data_criacao": datetime.now().isoformat()
        }


# Usar assim:
def processar_conteudo_upload(file_path, tipo, modulo):
    """API endpoint para processar arquivo"""
    gerador = GeradorConteudo()
    return gerador.processar_arquivo(file_path, tipo, modulo)
