{{ config(materialized='view', schema='silver') }}

select
    categoria,
    qtd_livros,
    preco_medio,
    qtd_estoque_baixo,
    coletado_em
from {{ ref('bronze_livros_painel') }}
