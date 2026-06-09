{{ config(materialized='view', schema='bronze') }}

select
    categoria,
    count(*) as qtd_livros,
    avg(preco) as preco_medio,
    sum(case when estoque_baixo then 1 else 0 end) as qtd_estoque_baixo,
    max(coletado_em) as coletado_em
from {{ ref('bronze_livros_todos') }}
where categoria is not null
group by categoria
