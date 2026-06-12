import json
import os
import threading
import time
from datetime import datetime
from gerador_conteudo import GeradorConteudo

class ProcessadorBackground:
    """Processa conteúdo em thread separada (não bloqueia requisição)"""
    
    def __init__(self):
        self.status_cache = {}  # Cache simples de status
    
    def processar_async(self, filepath, tipo, modulo, conteudo_id):
        """
        Inicia processamento em background thread
        Retorna imediatamente
        """
        # Registrar status inicial
        self.status_cache[conteudo_id] = {
            "status": "processando",
            "progresso": 0,
            "mensagem": "Analisando conteúdo com PicoClaw...",
            "inicio": datetime.now().isoformat()
        }
        
        # Criar thread separada
        thread = threading.Thread(
            target=self._processar,
            args=(filepath, tipo, modulo, conteudo_id),
            daemon=True
        )
        thread.start()
        
        print(f"📤 Thread iniciada para: {conteudo_id}")
    
    def _processar(self, filepath, tipo, modulo, conteudo_id):
        """Executa processamento em thread separada"""
        try:
            print(f"\n🔄 INICIANDO PROCESSAMENTO ASSÍNCRONO")
            print(f"   ID: {conteudo_id}")
            print(f"   Arquivo: {filepath}")
            print(f"   Tipo: {tipo}")
            print(f"   Módulo: {modulo}")
            
            # Atualizar status
            self._atualizar_status(conteudo_id, {
                "status": "analisando",
                "progresso": 10,
                "mensagem": "Enviando para PicoClaw..."
            })
            
            # Processar com PicoClaw
            gerador = GeradorConteudo()
            resultado = gerador.processar_arquivo(filepath, tipo, modulo)
            
            if resultado.get("success"):
                print(f"✅ Conteúdo gerado com sucesso!")
                
                # Atualizar status para concluído
                self._atualizar_status(conteudo_id, {
                    "status": "concluido",
                    "progresso": 100,
                    "mensagem": "Processamento concluído!",
                    "conteudos": resultado.get("conteudos"),
                    "fim": datetime.now().isoformat()
                })
            else:
                print(f"❌ Erro no processamento: {resultado.get('erro')}")
                
                self._atualizar_status(conteudo_id, {
                    "status": "erro",
                    "progresso": 0,
                    "mensagem": f"Erro: {resultado.get('erro')}",
                    "fim": datetime.now().isoformat()
                })
        
        except Exception as e:
            print(f"❌ EXCEÇÃO no processamento: {str(e)}")
            
            self._atualizar_status(conteudo_id, {
                "status": "erro",
                "progresso": 0,
                "mensagem": f"Erro: {str(e)}",
                "fim": datetime.now().isoformat()
            })
        
        finally:
            # Limpar arquivo temporário
            if os.path.exists(filepath):
                os.remove(filepath)
                print(f"🗑️  Arquivo temporário removido: {filepath}")
    
    def _atualizar_status(self, conteudo_id, dados):
        """Atualiza status em cache"""
        if conteudo_id in self.status_cache:
            self.status_cache[conteudo_id].update(dados)
        else:
            self.status_cache[conteudo_id] = dados
        
        print(f"📊 Status atualizado: {dados.get('status')} ({dados.get('progresso')}%)")
    
    def obter_status(self, conteudo_id):
        """Retorna status atual do processamento"""
        return self.status_cache.get(conteudo_id, {
            "status": "nao_encontrado",
            "mensagem": "Processamento não encontrado"
        })
    
    def limpar_concluidos(self):
        """Remove itens concluídos do cache (para liberar memória)"""
        ids_para_remover = [
            cid for cid, dados in self.status_cache.items()
            if dados.get("status") in ["concluido", "erro"]
        ]
        
        for cid in ids_para_remover:
            del self.status_cache[cid]
        
        if ids_para_remover:
            print(f"🧹 {len(ids_para_remover)} itens removidos do cache")
