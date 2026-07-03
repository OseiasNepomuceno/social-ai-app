"""
Adaptador de banco de dados COREGOV.
Usa SQLite se USE_SQLITE=true, senão usa Supabase.

Assim NÃO precisamos reescrever o app.py inteiro — só mudar o import.
"""

import os

USE_SQLITE = os.getenv("USE_SQLITE", "false").lower() in ("true", "1", "yes")

if USE_SQLITE:
    print("🔋 Usando SQLite (local)")
    from .database import create_client, db as _db
    supabase = _db
else:
    print("☁️ Usando Supabase (nuvem)")
    from supabase import create_client
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def criar_cliente():
    """Retorna o cliente ativo (compatível com supabase.create_client)"""
    return supabase
