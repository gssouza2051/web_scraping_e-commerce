{{ config(materialized='table', schema='gold') }}

select
    c.categoria,
    count(*) as total_livros,
    sum(case when f.estoque_baixo then 1 else 0 end) as livros_estoque_baixo,
    avg(f.preco) as preco_medio,
    min(f.estoque) as estoque_minimo,
    max(f.estoque) as estoque_maximo,
    avg(f.avaliacao) as avaliacao_media,
    current_timestamp as atualizado_em
from {{ ref('gold_fato_livros') }} f
join {{ ref('gold_dim_categorias') }} c on f.categoria_id = c.categoria_id
group by 1
order by 2 desc
