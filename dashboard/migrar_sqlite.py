"""
Script de migração: cria o banco SQLite e (opcionalmente) importa dados do Supabase.

Modo de uso:
    # Apenas criar schema (primeira execução no HF Spaces)
    python dashboard/migrar_sqlite.py
    
    # Exportar dados do Supabase e importar para SQLite
    python dashboard/migrar_sqlite.py --export
"""

import os
import sys
import json
import argparse

# Garantir que o diretório raiz do projeto está no path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Garantir diretórios persistentes
os.makedirs("/data/db", exist_ok=True)
os.makedirs("/data/uploads", exist_ok=True)
os.makedirs("/data/storage", exist_ok=True)

print("📦 COREGOV - Migração SQLite")
print("=" * 50)

# =========================
# 1. CRIAR SCHEMA
# =========================
print("\n🔧 Criando schema SQLite...")

from dashboard.database import db, DB_PATH

print(f"   Banco criado em: {DB_PATH}")
print("   ✅ Schema SQLite pronto!")

# =========================
# 2. IMPORTAR DADOS (opcional)
# =========================
parser = argparse.ArgumentParser()
parser.add_argument("--export", action="store_true", help="Exportar dados do Supabase e importar no SQLite")
args = parser.parse_args()

if args.export:
    print("\n📤 Exportando dados do Supabase...")
    
    # Usar Supabase para buscar dados
    from supabase import create_client
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    
    if not supabase_url or not supabase_key:
        print("   ❌ SUPABASE_URL e SUPABASE_KEY precisam estar configurados!")
        sys.exit(1)
    
    supabase = create_client(supabase_url, supabase_key)
    
    # Dados a exportar
    dados = {}
    
    tabelas = [
        "users", "posts", "conteudos", "analytics_acessos",
        "media_library", "nichos_tiktok", "vagas_assinantes",
        "analises_estatuto", "oportunidades_analisadas"
    ]
    
    for tabela in tabelas:
        try:
            res = supabase.table(tabela).select("*").execute()
            dados[tabela] = res.data or []
            print(f"   📋 {tabela}: {len(dados[tabela])} registros")
        except Exception as e:
            print(f"   ⚠️ {tabela}: erro ao exportar - {e}")
            dados[tabela] = []
    
    # Salvar como JSON backup
    backup_path = "/data/db/supabase_backup.json"
    with open(backup_path, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2, default=str)
    print(f"\n   💾 Backup salvo em: {backup_path}")
    
    # Importar para SQLite
    print("\n📥 Importando para SQLite...")
    from dashboard.database import importar_para_sqlite
    importar_para_sqlite(dados)
    
    print("\n✅ Migração concluída com sucesso!")
else:
    print("\n💡 Para importar dados do Supabase, use: python dashboard/migrar_sqlite.py --export")
    print("   (As variáveis SUPABASE_URL e SUPABASE_KEY precisam estar configuradas)")

print("\n🚀 Banco SQLite pronto para uso!")
print(f"   Localização: {DB_PATH}")
