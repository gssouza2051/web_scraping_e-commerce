# Web Scraping de E-commerce com Análise de Concorrência (Books to Scrape)

Projeto para treinar extração massiva de dados em um ambiente controlado que simula uma loja virtual real (sem o risco de bloqueio por IP), com pipeline completo até transformação (dbt) e orquestração (Airflow).

## Fonte de dados

- Site: [Books to Scrape](https://books.toscrape.com/) (sandbox para testes)

## Objetivo

- Navegar por múltiplas páginas usando o botão "Next"
- Mapear elementos dinâmicos e extrair dados que podem mudar de posição
- Abrir a página do produto em nova aba para extrair detalhes adicionais
- Persistir dados em PostgreSQL (com deduplicidade por URL)
- Exportar dados em Excel com painel por categoria
- Transformar dados em camadas `bronze`, `silver` e `gold` no dbt
- Orquestrar o dbt via Airflow (Cosmos)

## Dados a extrair

- Título do livro
- Preço
- Avaliação (estrelas)
- Disponibilidade em estoque
- Categoria
- URL do produto

## Regras de negócio

- Converter a avaliação em texto (ex.: "Three") para número (ex.: 3)
- Identificar livros com estoque baixo (ex.: menos de 5 unidades)
- Tradução de títulos para pt-BR (via serviço público)
- Conversão de moeda GBP -> BRL (via serviço público, com fallback por variável)

## Saída esperada

- Excel (`.xlsx`) com:
  - Aba `Todos`: itens completos
  - Aba `Painel`: agregações por categoria
  - Abas por categoria
- PostgreSQL com tabelas por aba (prefixo configurável)
- dbt com camadas `bronze`, `silver`, `gold` (views e tabelas finais)

## Estrutura do repositório

```
.
├── 1_scraping_setup/
│   ├── main.py
│   ├── banco_postgres.py
│   ├── docker-compose.yml
│   ├── requirements.txt
│   └── saida/
├── 2_data_warehouse/
│   └── dw_e_commerce/                # projeto dbt (execução local)
├── 3_airflow/
│   ├── dags/dag.py                   # DAG (Cosmos) para executar dbt
│   └── dbt/dw_e_commerce/            # projeto dbt copiado/montado para o Airflow
└── .github/workflows/ci.yml          # CI (GitHub Actions)
```

## Requisitos

- Python 3.13 (ou compatível com suas dependências locais)
- Google Chrome + ChromeDriver compatível (para Selenium)
- Docker Desktop (para PostgreSQL via compose)

## Como executar (scraping)

1) Instalar dependências do scraping:

```bash
python -m pip install --upgrade pip
pip install -r 1_scraping_setup/requirements.txt
```

2) (Opcional) Subir PostgreSQL via Docker:

```bash
cd 1_scraping_setup
docker compose up -d
```

3) Executar o scraping:

```bash
cd 1_scraping_setup
python main.py
```

## Variáveis de ambiente (scraping)

O scraping lê variáveis via ambiente. Principais:

- `AMBIENTE` = `dev` | `prod`
- `HEADLESS` = `0` | `1`
- `LIMITE_PRODUTOS` (ex.: `100`)
- `LIMITE_PAGINAS` (ex.: `0` para ilimitado)
- `HABILITAR_POSTGRES` = `0` | `1`
- `POSTGRES_HOST` (padrão `localhost`)
- `POSTGRES_PORTA` (padrão `5432`)
- `POSTGRES_USUARIO` (padrão `postgres`)
- `POSTGRES_SENHA`
- `POSTGRES_BANCO` (padrão `postgres`)
- `POSTGRES_SCHEMA` (padrão `scraping_e_commerce`)
- `POSTGRES_PREFIXO_TABELA` (padrão `livros_`)
- `TRADUZIR_TITULOS` = `0` | `1`
- `COTACAO_ONLINE` = `0` | `1`
- `TAXA_GBP_BRL` (ex.: `6.25`, usado como fallback quando cotação online não estiver disponível)

## Data Warehouse (dbt)

O projeto dbt está em [dw_e_commerce](file:///d:/Projetos/web_scraping_e-commerce/2_data_warehouse/dw_e_commerce).

### Camadas

- `bronze`: leitura bruta da fonte
- `silver`: tratamento e enriquecimento (derivações e padronizações)
- `gold`: tabelas finais (dimensão, fato e agregações)

### Comandos principais

```bash
cd 2_data_warehouse/dw_e_commerce
dbt deps --profiles-dir .
dbt seed --profiles-dir .
dbt run --profiles-dir .
```

### Observação sobre fontes do dbt

O dbt precisa apontar para a fonte que realmente existe no banco alvo:

- Quando você carrega seeds (`dbt seed`), elas são materializadas em `public_seeds`.
- Quando o scraping grava tabelas, elas ficam no schema configurado do scraping (`POSTGRES_SCHEMA`).

Se você mudar onde os dados estão, ajuste o arquivo [sources.yml](file:///d:/Projetos/web_scraping_e-commerce/2_data_warehouse/dw_e_commerce/models/sources.yml) para refletir o schema/tabela corretos.

## Airflow (orquestração dbt)

O Airflow está em `3_airflow/` e usa Cosmos para construir o DAG a partir do projeto dbt.

- DAG: [dag.py](file:///d:/Projetos/web_scraping_e-commerce/3_airflow/dags/dag.py)
- dbt montado no Airflow: `3_airflow/dbt/dw_e_commerce/`

### Problemas comuns

- `Invalid auth token: The token is not yet valid (iat)`:
  - normalmente é relógio dessincronizado entre host/WSL/Docker. Sincronize o horário e reinicie Docker/WSL.
- `The conn_id docker_postgres_db isn't defined`:
  - significa que a conexão não foi cadastrada no Airflow (Admin -> Connections) com esse `conn_id`.

## CI (GitHub Actions)

Workflow em [ci.yml](file:///d:/Projetos/web_scraping_e-commerce/.github/workflows/ci.yml) com validações:

- Instalação de dependências do scraping
- Import/compilação de módulos Python
- Validação de YAML dos `docker-compose`
- `dbt deps` e `dbt parse` no projeto dbt
