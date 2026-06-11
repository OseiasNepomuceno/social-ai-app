from flask import request, jsonify, render_template
from werkzeug.utils import secure_filename
import os
import json
from datetime import datetime
from gerador_conteudo import processar_conteudo_upload

# Configurações
UPLOAD_FOLDER = '/tmp/coregov-uploads'
ALLOWED_EXTENSIONS = {'mp4', 'mov', 'avi', 'jpg', 'jpeg', 'png', 'gif'}
BUFFER_API_KEY = os.getenv('BUFFER_API_KEY')  # Você vai colocar depois
KIWIFY_URL = os.getenv('KIWIFY_URL')

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def registrar_rotas_gerador_conteudo(app, supabase):
    
    # ========== DASHBOARD DE GERAÇÃO ==========
    @app.route("/gerar-conteudo")
    def pagina_gerar_conteudo():
        """Dashboard para gerar conteúdos"""
        return render_template("gerar_conteudo.html")
    
    
    # ========== PÁGINA DE TRILHAS ==========
    @app.route("/trilhas")
    def pagina_trilhas():
        """Página de trilhas de conhecimento"""
        return render_template("trilhas.html")
    
    
    # ========== PROCESSAR ARQUIVO ==========
    @app.route("/api/processar-conteudo", methods=["POST"])
    def processar_conteudo():
        """
        Processa vídeo/imagem e gera conteúdos automaticamente
        POST: file, tipo (video/imagem), modulo (1/2/3)
        """
        
        # Validar arquivo
        if 'file' not in request.files:
            return jsonify({"success": False, "erro": "Nenhum arquivo enviado"}), 400
        
        file = request.files['file']
        tipo = request.form.get('tipo', 'video')
        modulo = int(request.form.get('modulo', 1))
        
        if not file or file.filename == '':
            return jsonify({"success": False, "erro": "Arquivo inválido"}), 400
        
        if not allowed_file(file.filename):
            return jsonify({"success": False, "erro": "Tipo de arquivo não permitido"}), 400
        
        # Salvar arquivo temporário
        filename = secure_filename(file.filename)
        filepath = os.path.join(UPLOAD_FOLDER, f"{datetime.now().timestamp()}_{filename}")
        file.save(filepath)
        
        try:
            # Processar com PicoClaw
            resultado = processar_conteudo_upload(filepath, tipo, modulo)
            
            if resultado["success"]:
                # Salvar no banco de dados
                conteudo_doc = {
                    "tipo": tipo,
                    "modulo": modulo,
                    "data_criacao": datetime.now().isoformat(),
                    "status": "processado",
                    "conteudos": resultado["conteudos"],
                    "arquivo_original": filename
                }
                
                response = supabase.table("conteudos_gerados").insert(conteudo_doc).execute()
                
                return jsonify({
                    "success": True,
                    "conteudos": resultado["conteudos"],
                    "id": response.data[0]["id"] if response.data else None
                })
            else:
                return jsonify(resultado), 500
                
        except Exception as e:
            print(f"❌ Erro ao processar: {e}")
            return jsonify({"success": False, "erro": str(e)}), 500
        
        finally:
            # Limpar arquivo temporário
            if os.path.exists(filepath):
                os.remove(filepath)
    
    
    # ========== PUBLICAR NO BUFFER ==========
    @app.route("/api/publicar-tiktok", methods=["POST"])
    def publicar_tiktok():
        """
        Publica conteúdo no TikTok via Buffer
        POST: caption, hashtags, video_url, conteudo_id
        """
        
        try:
            data = request.get_json()
            caption = data.get("caption", "")
            hashtags = data.get("hashtags", "")
            video_url = data.get("video_url", "")
            conteudo_id = data.get("conteudo_id")
            
            # Preparar payload para Buffer
            buffer_payload = {
                "profile_ids": [data.get("buffer_profile_id")],
                "text": f"{caption}\n\n{hashtags}",
                "media": {
                    "url": video_url
                }
            }
            
            print(f"📱 Publicando no TikTok via Buffer...")
            print(f"Caption: {caption}")
            print(f"Hashtags: {hashtags}")
            
            # Aqui você usaria requests para fazer POST na API Buffer
            # import requests
            # response = requests.post(
            #     "https://api.bufferapp.com/1/updates/create.json",
            #     headers={"Authorization": f"Bearer {BUFFER_API_KEY}"},
            #     json=buffer_payload
            # )
            
            # Por enquanto, apenas registrar no banco
            if conteudo_id:
                supabase.table("conteudos_gerados").update({
                    "status": "publicado_tiktok",
                    "data_publicacao": datetime.now().isoformat()
                }).eq("id", conteudo_id).execute()
            
            return jsonify({
                "success": True,
                "mensagem": "Conteúdo agendado no TikTok via Buffer",
                "status": "agendado"
            })
            
        except Exception as e:
            print(f"❌ Erro ao publicar: {e}")
            return jsonify({"success": False, "erro": str(e)}), 500
    
    
    # ========== PUBLICAR NO SITE ==========
    @app.route("/api/publicar-trilha", methods=["POST"])
    def publicar_trilha():
        """
        Publica conteúdo na trilha do site
        POST: conteudo_id, metadata
        """
        
        try:
            data = request.get_json()
            conteudo_id = data.get("conteudo_id")
            metadata = data.get("metadata", {})
            
            # Salvar trilha no banco
            trilha_doc = {
                "conteudo_id": conteudo_id,
                "titulo": metadata.get("titulo"),
                "slug": metadata.get("slug"),
                "descricao": metadata.get("descricao"),
                "tags": metadata.get("tags", []),
                "modulo": metadata.get("modulo"),
                "tema": metadata.get("tema"),
                "status": "publicado",
                "data_publicacao": datetime.now().isoformat(),
                "url": f"/trilhas/{metadata.get('slug')}"
            }
            
            response = supabase.table("trilhas_publicadas").insert(trilha_doc).execute()
            
            # Atualizar status do conteúdo gerado
            supabase.table("conteudos_gerados").update({
                "status": "publicado_trilha"
            }).eq("id", conteudo_id).execute()
            
            return jsonify({
                "success": True,
                "mensagem": "Trilha publicada com sucesso",
                "url": f"/trilhas/{metadata.get('slug')}"
            })
            
        except Exception as e:
            print(f"❌ Erro ao publicar trilha: {e}")
            return jsonify({"success": False, "erro": str(e)}), 500
    
    
    # ========== LISTAR CONTEÚDOS GERADOS ==========
    @app.route("/api/conteudos-gerados")
    def listar_conteudos():
        """Lista todos os conteúdos já gerados"""
        try:
            response = supabase.table("conteudos_gerados").select("*").order("data_criacao", desc=True).execute()
            
            return jsonify({
                "success": True,
                "total": len(response.data),
                "conteudos": response.data
            })
            
        except Exception as e:
            return jsonify({"success": False, "erro": str(e)}), 500
    
    
    # ========== OBTER DETALHES CONTEÚDO ==========
    @app.route("/api/conteudo/<conteudo_id>")
    def obter_conteudo(conteudo_id):
        """Obter detalhes de um conteúdo específico"""
        try:
            response = supabase.table("conteudos_gerados").select("*").eq("id", conteudo_id).execute()
            
            if response.data:
                return jsonify({
                    "success": True,
                    "conteudo": response.data[0]
                })
            else:
                return jsonify({"success": False, "erro": "Conteúdo não encontrado"}), 404
                
        except Exception as e:
            return jsonify({"success": False, "erro": str(e)}), 500


# Integrar rotas no app.py
# No seu app.py, adicione:
# from dashboard.rotas_gerador_conteudo import registrar_rotas_gerador_conteudo
# registrar_rotas_gerador_conteudo(app, supabase)
