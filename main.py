
# venv\Scripts\activate.bat
# deactivate

from selenium import webdriver

from selenium.webdriver.common.by import By

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from selenium.common.exceptions import NoSuchElementException

import os
import re
import json
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin, quote
from urllib.request import Request, urlopen

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

AMBIENTE = os.getenv("AMBIENTE", "dev").lower()
HEADLESS = os.getenv("HEADLESS", "1" if AMBIENTE == "prod" else "0") == "1"
TELA_MAXIMIZADA = os.getenv("TELA_MAXIMIZADA", "1") == "1"
LIMITE_PAGINAS = int(os.getenv("LIMITE_PAGINAS", "0"))
LIMITE_PRODUTOS = int(os.getenv("LIMITE_PRODUTOS", "100"))
PAUSA_ENTRE_PRODUTOS_SEGUNDOS = float(os.getenv("PAUSA_ENTRE_PRODUTOS_SEGUNDOS", "0"))
TIMEOUT_SEGUNDOS = int(os.getenv("TIMEOUT_SEGUNDOS", "20"))
CAMINHO_SAIDA = Path(os.getenv("CAMINHO_SAIDA", str(Path.cwd() / "saida")))
URL_INICIAL = os.getenv("URL_INICIAL", "https://books.toscrape.com/")
HABILITAR_POSTGRES = os.getenv("HABILITAR_POSTGRES", "1") == "1"
POSTGRES_SCHEMA = os.getenv("POSTGRES_SCHEMA", "scraping_e_commerce")
POSTGRES_PREFIXO_TABELA = os.getenv("POSTGRES_PREFIXO_TABELA", "livros_")
TRADUZIR_TITULOS = os.getenv("TRADUZIR_TITULOS", "1") == "1"
COTACAO_ONLINE = os.getenv("COTACAO_ONLINE", "1") == "1"
TAXA_GBP_BRL = float(os.getenv("TAXA_GBP_BRL", "0") or 0)

try:
    import pandas as pd
except Exception as exc:
    raise RuntimeError("Dependência ausente: pandas") from exc

try:
    from banco_postgres import (
        criar_conexao_postgres,
        garantir_tabela_dashboard,
        garantir_tabela_livros,
        inserir_dashboard_upsert,
        inserir_livros_sem_duplicidade,
        normalizar_nome_tabela,
        registro_ja_existe,
    )
except Exception:
    criar_conexao_postgres = None

options = webdriver.ChromeOptions()

if HEADLESS:
    options.add_argument("--headless=new")
if TELA_MAXIMIZADA:
    options.add_argument("--start-maximized")
options.add_argument("--force-color-profile=srgb")


def criar_driver() -> webdriver.Chrome:
    return webdriver.Chrome(options=options)


def normalizar_nome_aba_excel(nome: str) -> str:
    nome_limpo = re.sub(r"[:\\/?*\\[\\]]+", " ", (nome or "").strip())
    nome_limpo = re.sub(r"\s+", " ", nome_limpo).strip()
    return (nome_limpo or "Categoria")[:31]


MAPA_REPLACE_PTBR = {
    "add_a_comment": "adicionar_comentario",
    "art": "arte",
    "childrens": "crianca",
    "contemporary": "contemporaneo",
    "fiction": "ficcao",
    "business": "negocios",
    "default": "padrao",
    "fantasy": "fantasia",
    "food_and_drink": "comida_e_bebida",
    "health": "saude",
    "historical_fiction": "ficcao_historica",
    "history": "historia",
    "music": "musica",
    "mystery": "misterio",
    "new_adult": "adolescente",
    "nonfiction": "sem_ficcao",
    "philosophy": "filosofia",
    "poetry": "poesia",
    "politics": "politica",
    "science": "ciencia",
    "science_fiction": "ficcao_cientifica",
    "self_help": "auto_ajuda",
    "sequential_art": "arte_sequencial",
    "spirituality": "espiritualidade",
    "thriller": "acao",
    "travel": "viagem",
    "young_adult": "jovem",
}


def traduzir_por_replace(texto: str | None) -> str | None:
    if not texto:
        return texto
    chave = texto.strip().lower()
    chave = re.sub(r"\s+", "_", chave)
    chave = re.sub(r"[^a-z0-9_]+", "", chave)
    return MAPA_REPLACE_PTBR.get(chave, texto)


def converter_avaliacao_para_numero(avaliacao_ingles: str | None) -> int | None:
    if not avaliacao_ingles:
        return None
    mapa = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}
    return mapa.get(avaliacao_ingles)


def obter_taxa_gbp_para_brl() -> float | None:
    if TAXA_GBP_BRL > 0:
        return TAXA_GBP_BRL

    if not COTACAO_ONLINE:
        return None

    try:
        req = Request(
            "https://api.frankfurter.app/latest?from=GBP&to=BRL",
            headers={"User-Agent": "Mozilla/5.0"},
        )
        with urlopen(req, timeout=10) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        taxa = float(payload["rates"]["BRL"])
        if taxa > 0:
            return taxa
    except Exception:
        return None

    return None


_cache_traducao: dict[str, str] = {}


def traduzir_para_ptbr(texto: str | None) -> str | None:
    if not TRADUZIR_TITULOS:
        return texto
    if not texto:
        return texto

    chave = texto.strip()
    if not chave:
        return texto

    if chave in _cache_traducao:
        return _cache_traducao[chave]

    try:
        url = (
            "https://api.mymemory.translated.net/get"
            f"?q={quote(chave)}&langpair=en|pt-br"
        )
        req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(req, timeout=15) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        traducao = (payload.get("responseData") or {}).get("translatedText")
        traducao = (traducao or "").strip()
        if traducao:
            _cache_traducao[chave] = traducao
            return traducao
    except Exception:
        _cache_traducao[chave] = chave
        return chave

    _cache_traducao[chave] = chave
    return chave


def formatar_preco(preco: float | None) -> str:
    if preco is None:
        return "N/A"
    return f"R$ {preco:.2f}"


def formatar_estoque(estoque: int | None) -> str:
    if estoque is None:
        return "N/A"
    return str(estoque)


def imprimir_item(item: dict, indice: int, limite: int) -> None:
    titulo = item.get("titulo") or "N/A"
    preco = formatar_preco(item.get("preco"))
    avaliacao = item.get("avaliacao")
    avaliacao_txt = item.get("avaliacao_texto") or "N/A"
    disponibilidade = (item.get("disponibilidade") or "N/A").replace("\n", " ").strip()
    estoque = formatar_estoque(item.get("estoque"))
    estoque_baixo = "SIM" if item.get("estoque_baixo") else "NAO"
    categoria = item.get("categoria") or "N/A"
    limite_visivel = limite if limite > 0 else indice
    print('\n')
    print(
        f"[{indice:03d}/{limite_visivel:03d}] titulo={titulo} | preco={preco} | "
        f"avaliacao={avaliacao if avaliacao is not None else 'N/A'} ({avaliacao_txt}) | "
        f"disponibilidade={disponibilidade} | estoque={estoque} | estoque_baixo={estoque_baixo} | "
        f"categoria={categoria}"
    )


def extrair_texto(driver: webdriver.Chrome, seletor_css: str) -> str | None:
    try:
        valor = driver.find_element(By.CSS_SELECTOR, seletor_css).text
        valor = (valor or "").strip()
        return valor or None
    except NoSuchElementException:
        return None


def extrair_atributo(driver: webdriver.Chrome, seletor_css: str, atributo: str) -> str | None:
    try:
        valor = driver.find_element(By.CSS_SELECTOR, seletor_css).get_attribute(atributo)
        valor = (valor or "").strip()
        return valor or None
    except NoSuchElementException:
        return None


def extrair_links_produtos(driver: webdriver.Chrome, wait: WebDriverWait) -> list[str]:
    wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "article.product_pod h3 a")))
    elementos = driver.find_elements(By.CSS_SELECTOR, "article.product_pod h3 a")
    links = []
    for el in elementos:
        href = (el.get_attribute("href") or "").strip()
        if href:
            links.append(urljoin(driver.current_url, href))
    return links


def obter_url_proxima_pagina(driver: webdriver.Chrome) -> str | None:
    try:
        href = driver.find_element(By.CSS_SELECTOR, "li.next a").get_attribute("href")
    except NoSuchElementException:
        return None
    if not href:
        return None
    return urljoin(driver.current_url, href)


def extrair_detalhes_produto_em_nova_aba(
    driver: webdriver.Chrome, wait: WebDriverWait, url_produto: str
) -> dict:
    janela_origem = driver.current_window_handle
    abas_antes = set(driver.window_handles)

    driver.execute_script("window.open(arguments[0], '_blank');", url_produto)
    wait.until(lambda d: len(d.window_handles) > len(abas_antes))

    aba_nova = next(h for h in driver.window_handles if h not in abas_antes)
    driver.switch_to.window(aba_nova)

    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.product_main")))

    titulo = extrair_texto(driver, "div.product_main h1")
    preco_texto = extrair_texto(driver, "div.product_main p.price_color")
    categoria = extrair_texto(driver, "ul.breadcrumb li:nth-child(3) a")

    avaliacao_classe = extrair_atributo(driver, "div.product_main p.star-rating", "class") or ""
    avaliacao_ingles = None
    for parte in avaliacao_classe.split():
        if parte in {"One", "Two", "Three", "Four", "Five"}:
            avaliacao_ingles = parte
            break

    disponibilidade_texto = extrair_texto(driver, "div.product_main p.availability")
    estoque = None
    if disponibilidade_texto:
        m = re.search(r"\((\d+)\s+available\)", disponibilidade_texto)
        if m:
            try:
                estoque = int(m.group(1))
            except ValueError:
                estoque = None

    preco = None
    if preco_texto:
        try:
            preco = float(preco_texto.replace("£", "").replace(",", ".").strip())
        except ValueError:
            preco = None

    driver.close()
    driver.switch_to.window(janela_origem)

    avaliacao_numero = converter_avaliacao_para_numero(avaliacao_ingles)

    return {
        "titulo": titulo,
        "preco": preco,
        "avaliacao_texto": avaliacao_ingles,
        "avaliacao": avaliacao_numero,
        "disponibilidade": disponibilidade_texto,
        "estoque": estoque,
        "estoque_baixo": bool(estoque is not None and estoque < 5),
        "categoria": categoria,
        "url": url_produto,
    }


def gerar_planilhas(dados: list[dict]) -> dict[str, "pd.DataFrame"]:
    df = pd.DataFrame(dados)
    if not len(df):
        return {
            "Informacoes": pd.DataFrame([{"mensagem": "Nenhum dado extraído. Verifique seletores."}])
        }

    df["categoria_ptbr"] = df["categoria"].apply(traduzir_por_replace)

    dashboard = (
        df.groupby("categoria_ptbr", dropna=False)
        .agg(
            qtd_livros=("titulo", "count"),
            preco_medio=("preco", "mean"),
            qtd_estoque_baixo=("estoque_baixo", "sum"),
        )
        .reset_index()
        .rename(columns={"categoria_ptbr": "categoria"})
        .sort_values(["qtd_livros", "categoria"], ascending=[False, True])
    )

    planilhas: dict[str, "pd.DataFrame"] = {"Todos": df, "Painel": dashboard}

    categorias = sorted(
        {c for c in df["categoria_ptbr"].dropna().unique().tolist() if str(c).strip()}
    )
    abas_usadas = set(planilhas.keys())

    for categoria in categorias:
        nome_aba = normalizar_nome_aba_excel(str(categoria))
        if nome_aba in abas_usadas:
            base = nome_aba[:28]
            i = 2
            while f"{base}_{i}" in abas_usadas and i < 100:
                i += 1
            nome_aba = f"{base}_{i}"
        abas_usadas.add(nome_aba)
        planilhas[nome_aba] = df[df["categoria_ptbr"] == categoria]

    return planilhas


def exportar_para_excel(planilhas: dict[str, "pd.DataFrame"], caminho_excel: Path) -> None:
    caminho_excel.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(caminho_excel, engine="openpyxl") as writer:
        for nome_aba, df in planilhas.items():
            df.to_excel(writer, sheet_name=nome_aba, index=False)


def sincronizar_postgres(planilhas: dict[str, "pd.DataFrame"]) -> None:
    if not HABILITAR_POSTGRES:
        return
    if criar_conexao_postgres is None:
        print("PostgreSQL: integração indisponível (dependência não carregada).")
        return

    try:
        conexao = criar_conexao_postgres()
    except Exception as exc:
        print(f"PostgreSQL: falha ao conectar ({exc}).")
        return

    try:
        for nome_aba, df in planilhas.items():
            if not len(df):
                continue

            tabela = f"{POSTGRES_PREFIXO_TABELA}{normalizar_nome_tabela(nome_aba)}"
            linhas = df.to_dict("records")

            if nome_aba == "Painel":
                garantir_tabela_dashboard(conexao, POSTGRES_SCHEMA, tabela)
                inseridos = inserir_dashboard_upsert(conexao, POSTGRES_SCHEMA, tabela, linhas)
                print(f"PostgreSQL: tabela={POSTGRES_SCHEMA}.{tabela} registros={inseridos}")
                continue

            if nome_aba == "Informacoes":
                continue

            garantir_tabela_livros(conexao, POSTGRES_SCHEMA, tabela)

            if nome_aba == "Todos":
                novos = []
                for linha in linhas:
                    url = linha.get("url")
                    if not url:
                        continue
                    if not registro_ja_existe(conexao, POSTGRES_SCHEMA, tabela, "url", url):
                        novos.append(linha)
                inseridos = inserir_livros_sem_duplicidade(conexao, POSTGRES_SCHEMA, tabela, novos)
                print(f"PostgreSQL: tabela={POSTGRES_SCHEMA}.{tabela} inseridos={inseridos} (sem duplicidade)")
            else:
                inseridos = inserir_livros_sem_duplicidade(conexao, POSTGRES_SCHEMA, tabela, linhas)
                print(f"PostgreSQL: tabela={POSTGRES_SCHEMA}.{tabela} inseridos={inseridos}")
    finally:
        try:
            conexao.close()
        except Exception:
            pass


def raspar_books_to_scrape() -> Path:
    driver = criar_driver()
    wait = WebDriverWait(driver, TIMEOUT_SEGUNDOS)

    itens: list[dict] = []
    paginas_visitadas = 0
    taxa_gbp_brl = obter_taxa_gbp_para_brl()

    try:
        driver.get(URL_INICIAL)
        if taxa_gbp_brl:
            print(f"Taxa GBP->BRL carregada: {taxa_gbp_brl:.4f}")
        else:
            print("Taxa GBP->BRL indisponível. Mantendo valor original sem conversão.")

        while True:
            paginas_visitadas += 1
            links = extrair_links_produtos(driver, wait)
            print(
                f"Pagina {paginas_visitadas} | produtos_encontrados={len(links)} | total_capturados={len(itens)}"
            )

            for url_produto in links:
                item = extrair_detalhes_produto_em_nova_aba(driver, wait, url_produto)

                titulo_original = item.get("titulo")
                item["titulo_original"] = titulo_original
                item["titulo"] = traduzir_para_ptbr(titulo_original) or titulo_original

                preco_gbp = item.get("preco")
                item["preco_gbp"] = preco_gbp
                if preco_gbp is not None and taxa_gbp_brl:
                    item["preco"] = round(float(preco_gbp) * float(taxa_gbp_brl), 2)

                itens.append(item)
                imprimir_item(item, len(itens), LIMITE_PRODUTOS)
                if PAUSA_ENTRE_PRODUTOS_SEGUNDOS > 0:
                    import time

                    time.sleep(PAUSA_ENTRE_PRODUTOS_SEGUNDOS)
                if LIMITE_PRODUTOS > 0 and len(itens) >= LIMITE_PRODUTOS:
                    break

            if LIMITE_PRODUTOS > 0 and len(itens) >= LIMITE_PRODUTOS:
                print(f"Limite atingido: {LIMITE_PRODUTOS} livros. Encerrando captura.")
                break

            if LIMITE_PAGINAS > 0 and paginas_visitadas >= LIMITE_PAGINAS:
                print(f"Limite de páginas atingido: {LIMITE_PAGINAS}. Encerrando captura.")
                break

            proxima = obter_url_proxima_pagina(driver)
            if not proxima:
                print("Sem próxima página. Encerrando captura.")
                break
            driver.get(proxima)

    finally:
        driver.quit()
        print("Navegador fechado")

    nome_arquivo = f"books_to_scrape_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    caminho_excel = CAMINHO_SAIDA / nome_arquivo
    planilhas = gerar_planilhas(itens)
    exportar_para_excel(planilhas, caminho_excel)
    sincronizar_postgres(planilhas)
    return caminho_excel


if __name__ == "__main__":
    caminho = raspar_books_to_scrape()
    print(f"Arquivo gerado: {caminho}")



