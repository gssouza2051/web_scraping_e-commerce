{{ config(materialized='table', schema='gold') }}

with categorias_distintas as (
    select distinct
        categoria
    from {{ ref('silver_livros_todos') }}
    where categoria is not null
)

select
    {{ dbt_utils.generate_surrogate_key(['categoria']) }} as categoria_id,
    categoria,
    current_timestamp as criado_em
from categorias_distintas
