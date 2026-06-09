{{ config(materialized='view', schema='bronze') }}

select
    row_number() over (order by titulo, url) as id,
    titulo,
    cast(preco as numeric) as preco,
    avaliacao_texto,
    avaliacao,
    disponibilidade,
    estoque,
    case
        when upper(coalesce(estoque_baixo, '')) in ('TRUE', 'T', '1', 'SIM', 'VERDADEIRO') then true
        else false
    end as estoque_baixo,
    coalesce(categoria_ptbr, categoria) as categoria,
    url,
    current_timestamp as coletado_em
from {{ source('public_seeds', 'books_to_scrape_20260528_235554') }}
