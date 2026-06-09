{{ config(materialized='view', schema='silver') }}

with base as (
    select
        id,
        titulo,
        preco,
        avaliacao_texto,
        avaliacao,
        disponibilidade,
        estoque,
        estoque_baixo,
        categoria,
        url,
        coletado_em
    from {{ ref('bronze_livros_todos') }}
)

select
    id,
    titulo,
    preco,
    avaliacao_texto,
    avaliacao,
    disponibilidade,
    estoque,
    estoque_baixo,
    categoria,
    url,
    coletado_em,
    -- Campos derivados
    case 
        when estoque_baixo then 'BAIXO'
        when estoque >= 10 then 'SUFICIENTE'
        else 'MODERADO'
    end as nivel_estoque,
    case 
        when avaliacao >= 4 then 'ALTA'
        when avaliacao >= 2 then 'MEDIA'
        else 'BAIXA'
    end as nivel_avaliacao
from base
