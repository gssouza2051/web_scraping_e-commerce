# Data Warehouse - E-commerce (dbt)

Projeto dbt para transformação dos dados extraídos do Books to Scrape.

## Estrutura

```
models/
├── bronze/           # Views com leitura bruta das fontes
│   ├── bronze_livros_todos.sql
│   └── bronze_livros_painel.sql
├── silver/           # Views com tratamento e enriquecimento
│   ├── silver_livros_todos.sql
│   └── silver_livros_painel.sql
├── gold/             # Tabelas de consumo analitico
│   ├── gold_dim_categorias.sql
│   ├── gold_fato_livros.sql
│   └── gold_agg_estoque_por_categoria.sql
└── sources.yml       # Definição das fontes de dados
```

## Configuração

1. **PostgreSQL Docker** (rodando na porta 5433):
   ```bash
   cd ../1_scraping_setup
   docker-compose up -d
   ```

2. **Executar scraping** para popular as tabelas:
   ```bash
   python main.py
   ```

3. **Testar conexão dbt**:
   ```bash
   dbt debug
   ```

4. **Executar transformações**:
   ```bash
   dbt run
   ```

5. **Testar modelos**:
   ```bash
   dbt test
   ```

## Schemas

- `public`: Tabelas originais do scraping
- `bronze`: Views com leitura bruta das tabelas de origem
- `silver`: Views com tratamento e padronizacao dos dados
- `gold`: Tabelas finais para consumo analitico

## Variáveis de ambiente

O dbt usa o arquivo `profiles.yml` com as credenciais:
- Host: `localhost`
- Porta: `5433`
- Database: `dbt_db`
- Usuário: `postgres`
- Senha: `postgres`

## Pipeline

1. **Extração**: `main.py` (Selenium) → tabelas `public.livros_*`
2. **Bronze**: `bronze_*.sql` (views) → schema `bronze`
3. **Silver**: `silver_*.sql` (views) → schema `silver`
4. **Gold**: `gold_*.sql` (tabelas) → schema `gold`
