{{ config(materialized='table', schema='gold') }}

with livros as (
    select
        id,
        titulo,
        preco,
        avaliacao,
        estoque,
        estoque_baixo,
        categoria,
        url,
        coletado_em,
        nivel_estoque,
        nivel_avaliacao
    from {{ ref('silver_livros_todos') }}
),

categorias as (
    select
        categoria_id,
        categoria
    from {{ ref('gold_dim_categorias') }}
)

select
    l.id as livro_id,
    c.categoria_id,
    l.titulo,
    l.preco,
    l.avaliacao,
    l.estoque,
    l.estoque_baixo,
    l.nivel_estoque,
    l.nivel_avaliacao,
    l.url,
    l.coletado_em,
    current_timestamp as processado_em
from livros l
left join categorias c on l.categoria = c.categoria
