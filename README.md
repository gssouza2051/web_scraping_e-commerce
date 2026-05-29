# Web Scraping de E-commerce com Análise de Concorrência (Books to Scrape)

Projeto para treinar extração massiva de dados em um ambiente controlado que simula uma loja virtual real (sem o risco de bloqueio por IP).

## Fonte de dados

- Site: [Books to Scrape](https://books.toscrape.com/) (sandbox para testes)
https://books.toscrape.com/

## Objetivo

- Navegar por múltiplas páginas usando o botão "Next"
- Mapear elementos dinâmicos e extrair dados que podem mudar de posição
- (Opcional) Abrir a página do produto para extrair detalhes adicionais

## Dados a extrair

- Título do livro
- Preço
- Avaliação (estrelas)
- Disponibilidade em estoque

## Regras de negócio

- Converter a avaliação em texto (ex.: "Three") para número (ex.: 3)
- Identificar livros com estoque baixo (ex.: menos de 5 unidades)

## Saída esperada

- Dashboard em Excel
  - Livros divididos por categorias automaticamente
