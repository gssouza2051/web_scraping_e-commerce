import os
import re
from datetime import datetime

import psycopg2
from psycopg2.extras import execute_values


def obter_config_postgres() -> dict:
    return {
        "host": os.getenv("POSTGRES_HOST", "localhost"),
        "port": int(os.getenv("POSTGRES_PORTA", "5432")),
        "user": os.getenv("POSTGRES_USUARIO", "postgres"),
        "password": os.getenv("POSTGRES_SENHA", "secreta007"),
        "dbname": os.getenv("POSTGRES_BANCO", "postgres"),
        "connect_timeout": int(os.getenv("POSTGRES_TIMEOUT_SEGUNDOS", "10")),
    }


def criar_conexao_postgres():
    config = obter_config_postgres()
    return psycopg2.connect(**config)


def normalizar_nome_tabela(nome: str) -> str:
    base = (nome or "").strip().lower()
    base = re.sub(r"[^a-z0-9]+", "_", base).strip("_")
    if not base:
        base = "tabela"
    if base[0].isdigit():
        base = f"t_{base}"
    return base[:63]


def garantir_tabela_livros(conexao, schema: str, tabela: str) -> None:
    sql = f"""
    CREATE TABLE IF NOT EXISTS {schema}.{tabela} (
        id BIGSERIAL PRIMARY KEY,
        titulo TEXT,
        titulo_original TEXT,
        preco NUMERIC,
        preco_gbp NUMERIC,
        avaliacao_texto TEXT,
        avaliacao INTEGER,
        disponibilidade TEXT,
        estoque INTEGER,
        estoque_baixo BOOLEAN,
        categoria TEXT,
        url TEXT NOT NULL,
        coletado_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        UNIQUE (url)
    );
    """
    with conexao.cursor() as cursor:
        cursor.execute(sql)
        cursor.execute(f"ALTER TABLE {schema}.{tabela} ADD COLUMN IF NOT EXISTS titulo_original TEXT")
        cursor.execute(f"ALTER TABLE {schema}.{tabela} ADD COLUMN IF NOT EXISTS preco_gbp NUMERIC")
    conexao.commit()


def garantir_tabela_dashboard(conexao, schema: str, tabela: str) -> None:
    sql = f"""
    CREATE TABLE IF NOT EXISTS {schema}.{tabela} (
        id BIGSERIAL PRIMARY KEY,
        categoria TEXT NOT NULL,
        qtd_livros INTEGER,
        preco_medio NUMERIC,
        qtd_estoque_baixo INTEGER,
        coletado_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        UNIQUE (categoria)
    );
    """
    with conexao.cursor() as cursor:
        cursor.execute(sql)
    conexao.commit()


def registro_ja_existe(conexao, schema: str, tabela: str, coluna_chave: str, valor_chave) -> bool:
    sql = f"SELECT 1 FROM {schema}.{tabela} WHERE {coluna_chave} = %s LIMIT 1"
    with conexao.cursor() as cursor:
        cursor.execute(sql, (valor_chave,))
        return cursor.fetchone() is not None


def inserir_livros_sem_duplicidade(conexao, schema: str, tabela: str, linhas: list[dict]) -> int:
    if not linhas:
        return 0

    colunas = [
        "titulo",
        "titulo_original",
        "preco",
        "preco_gbp",
        "avaliacao_texto",
        "avaliacao",
        "disponibilidade",
        "estoque",
        "estoque_baixo",
        "categoria",
        "url",
        "coletado_em",
    ]
    coletado_em = datetime.now().astimezone()
    valores = [
        tuple((linha.get(c) if c != "coletado_em" else coletado_em) for c in colunas) for linha in linhas
    ]

    sql = f"""
    INSERT INTO {schema}.{tabela} ({", ".join(colunas)})
    VALUES %s
    ON CONFLICT (url) DO NOTHING
    """

    with conexao.cursor() as cursor:
        execute_values(cursor, sql, valores, page_size=500)
    conexao.commit()

    return len(valores)


def inserir_dashboard_upsert(conexao, schema: str, tabela: str, linhas: list[dict]) -> int:
    if not linhas:
        return 0

    colunas = ["categoria", "qtd_livros", "preco_medio", "qtd_estoque_baixo", "coletado_em"]
    coletado_em = datetime.now().astimezone()
    valores = [
        (
            linha.get("categoria"),
            linha.get("qtd_livros"),
            linha.get("preco_medio"),
            linha.get("qtd_estoque_baixo"),
            coletado_em,
        )
        for linha in linhas
        if linha.get("categoria") is not None
    ]

    sql = f"""
    INSERT INTO {schema}.{tabela} ({", ".join(colunas)})
    VALUES %s
    ON CONFLICT (categoria)
    DO UPDATE SET
        qtd_livros = EXCLUDED.qtd_livros,
        preco_medio = EXCLUDED.preco_medio,
        qtd_estoque_baixo = EXCLUDED.qtd_estoque_baixo,
        coletado_em = EXCLUDED.coletado_em
    """

    with conexao.cursor() as cursor:
        execute_values(cursor, sql, valores, page_size=500)
    conexao.commit()

    return len(valores)
