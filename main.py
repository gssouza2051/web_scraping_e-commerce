from selenium import webdriver

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import NoSuchElementException

import time
from pathlib import Path
from urllib.parse import urljoin

HEADLESS = False
TELA_MAXIMIZADA = True

options = webdriver.ChromeOptions()

if HEADLESS:
    options.add_argument("--headless=new")
if TELA_MAXIMIZADA:
    options.add_argument("--start-maximized")


driver = webdriver.Chrome(options=options)

# Navega até o Amazon
driver.get("https://www.amazon.com.br/")

# Espere inteligente
wait = WebDriverWait(driver, 20)

# Escreve na barra de pesquisa
pesquisa = wait.until(EC.presence_of_element_located((By.ID, "twotabsearchtextbox")))

#resposta_pesquisa = input('O que deseja pesquisar? ')
resposta_pesquisa = 'Monitor gamer'
pesquisa.clear()
pesquisa.send_keys(resposta_pesquisa)
pesquisa.send_keys(Keys.ENTER)

# Aguarda o carregamento da página
wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.s-main-slot")))

# Coletando produtos
dados = []

time.sleep(1)

cards = driver.find_elements(By.ID, "77c36b4a-d21f-4e9d-8dde-bae97bd46c82")
for card in cards:
    try:
        nome = card.find_element(By.CSS_SELECTOR, "h2 a span").text.strip()
        link_rel = card.find_element(By.CSS_SELECTOR, "h2 a").get_attribute("href")
    except NoSuchElementException:
        continue

    try:
        valor = card.find_element(By.CSS_SELECTOR, "span.a-price span.a-offscreen").text.strip()
    except NoSuchElementException:
        valor = None

    if not nome or not link_rel:
        continue

    link = urljoin("https://www.amazon.com.br", link_rel)
    dados.append({"nome": nome, "valor": valor, "link": link})

print(dados)

# Fechar o navegador
driver.quit()
print("Navegador fechado")
