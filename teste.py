import os
import time
import json
import openai
import pyperclip
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service

# Configurar a chave de API da OpenAI
openai.api_key = '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'

diretorio_codigo = os.path.dirname(os.path.abspath(__file__))

def abrir_whatsapp_web(perfil):
    # Configurando opções do navegador Chrome
    opcoes = Options()
    opcoes.add_argument(f"user-data-dir={os.path.join(diretorio_codigo, perfil)}")
    opcoes.add_argument('--disable-infobars')
    opcoes.add_argument('--disable-extensions')

    # Iniciando o navegador Chrome com as opções configuradas e baixando o driver automaticamente
    driver_service = Service(ChromeDriverManager().install())
    navegador = webdriver.Chrome(service=driver_service, options=opcoes)

    # Abrindo o site do WhatsApp Web
    navegador.get('https://web.whatsapp.com/')

    esperar = WebDriverWait(navegador, 300)
    esperar.until(EC.presence_of_element_located((By.XPATH, "//span[@data-testid='default-user']")))
    time.sleep(20)
    return navegador

def fechar_whatsapp_web(navegador):
    time.sleep(5)
    navegador.quit()

def ler_ultimas_mensagens(navegador, qntd_mensagens):
    mensagens = []
    
    try:
        # Verifica se há mensagens suficientes para ler
        elementos_mensagens = navegador.find_elements(By.XPATH, "//div[contains(@class, 'message-in')]//span[@dir='ltr']")
        if len(elementos_mensagens) < qntd_mensagens:
            print(f"A quantidade de mensagens disponíveis ({len(elementos_mensagens)}) é menor do que a quantidade solicitada ({qntd_mensagens}).")
            return mensagens

        # Obtém as últimas mensagens
        elementos_mensagens = elementos_mensagens[-qntd_mensagens:]
        for elemento in elementos_mensagens:
            mensagem = elemento.text
            mensagens.append(mensagem)
    
    except NoSuchElementException:
        print("Erro ao ler as últimas mensagens.")
    return mensagens

def enviar_mensagem(navegador, mensagem):
    esperar = WebDriverWait(navegador, 600)
    caixa_de_entrada = esperar.until(EC.presence_of_element_located((By.XPATH, "//div[@title='Mensagem']//p[@class='selectable-text copyable-text iq0m558w']")))

    # Salvando o conteúdo atual da área de transferência
    conteudo_anterior = pyperclip.paste()

    # Copiando a mensagem para a área de transferência
    pyperclip.copy(mensagem)

    # Enviando a mensagem com emojis
    caixa_de_entrada.send_keys(Keys.CONTROL + "v")
    caixa_de_entrada.send_keys(Keys.ENTER, Keys.ESCAPE)

    # Restaurando o conteúdo anterior da área de transferência
    pyperclip.copy(conteudo_anterior)

def aguardando_mensagem(navegador):
    resultado = False

    while resultado == False:
        try:
            mensagem_pendente = navegador.find_element(By.XPATH, "//span[@data-testid='icon-unread-count']")
        except NoSuchElementException or StaleElementReferenceException:
            continue
        else:
            mensagem_pendente = navegador.find_element(By.XPATH, "//span[@data-testid='icon-unread-count']")
            time.sleep(1)
            try:
                qntd_mensagens = int(mensagem_pendente.text)
            except StaleElementReferenceException:
                continue
            else:
                try:
                    mensagem_pendente.click()
                except NoSuchElementException or StaleElementReferenceException:
                    continue
                else: 
                    resultado = True

    return qntd_mensagens, resultado

def obter_id(navegador):
    elemento = navegador.find_element(By.XPATH, "//div[@class='CzM4m']")

    id_completo = elemento.get_attribute('data-id')
    partes = id_completo.split('_')
    valor_numerico = None

    if len(partes) > 1:
        valor_numerico = partes[1]

    print(valor_numerico)

    return valor_numerico

def obter_resposta(prompt):
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "system", "content": prompt}],
        max_tokens=1000,
        temperature=0.2
    )

    return response.choices[0].message.content.strip()

if __name__ == "__main__":
    perfil = '21992800257'
    navegador = abrir_whatsapp_web(perfil)

    while True:
        qntd_mensagens, mensagem_recebida = aguardando_mensagem(navegador)
        if mensagem_recebida:
            id = obter_id(navegador)
            if not os.path.exists(str(id)+".json"):
                # Arquivo não existe, criar um novo arquivo
                dados = {
                    "progresso": {
                        "estagio": "1",
                        "nome": "",
                        "vidas": "",
                        "idades": "",
                        "regiao": "",
                        "preferencia_hospital": "",
                        "plano_ativo": "",
                        "cnpj_ativo": ""
                    }
                }
                with open(str(id)+".json", 'w') as arquivo:
                    json.dump(dados, arquivo, indent=4, ensure_ascii=False)
                    print("Arquivo JSON criado com sucesso!")
                enviar_mensagem(navegador, "Olá! Tudo bem? Para iniciar seu atendimento, poderia me dizer qual é o seu nome?")
            else:
                print("O arquivo JSON já existe!")
                with open(str(id)+".json", 'r') as arquivo:
                    dados = json.load(arquivo)
                progresso = dados['progresso']['estagio']
                print(f"Progresso: {progresso}")
                ultimas_mensagens = ler_ultimas_mensagens(navegador, qntd_mensagens)
                print(f"Mensagens recebidas: {ultimas_mensagens}")
                if progresso == "1":
                    tentativas = 0
                    while tentativas < 5:
                        resposta = obter_resposta(f"""
                                                    Instruções:\n
                                                    1. Insira uma pergunta clara e específica no espaço \"Pergunta\".\n
                                                    2. Na seção \"Resposta\", forneça a resposta correspondente à pergunta de forma precisa e completa.\n
                                                    3. Ao receber a resposta, verifique se ela é coerente com a pergunta e se responde adequadamente a ela.\n
                                                    4. Se a resposta for coerente e responder à pergunta, responda \"SIM\".\n
                                                    5. Se a resposta não for coerente ou não responder à pergunta, responda \"NÃO\".\n
                                                    6. Interprete de lide com a possibilidade de erros de digitação ou abreviação\n\n
                                                    
                                                    Pergunta: \"Olá! Tudo bem? Para iniciar seu atendimento, poderia me dizer qual é o seu nome?\"\n
                                                    Resposta: \"{ultimas_mensagens}\".\n\n

                                                    Observação: Seja flexível na análise da coerência.  
                                                    """)
                        print(f"Resposta GPT: {resposta}")
                        tentativas += 1
                        if "sim" in resposta.lower().rstrip(".").rstrip("."):
                            resposta = obter_resposta(f"Eu enviei: Olá! Tudo bem? Para iniciar seu atendimento, poderia me dizer qual é o seu nome?\nCliente me respondeu com: {ultimas_mensagens}.\n\nPor favor, digite abaixo apenas o nome dele.")
                            print(f"Resposta GPT: {resposta}")
                            with open(str(id)+".json", 'r') as arquivo:
                                dados = json.load(arquivo)
                            dados['progresso']['estagio'] = "2"
                            dados['progresso']['nome'] = resposta
                            with open(str(id)+".json", 'w') as arquivo:
                                json.dump(dados, arquivo, indent=4, ensure_ascii=False)
                            enviar_mensagem(navegador, "Poderia me informar o número de pessoas para a cotação, por favor?")
                            time.sleep(1)
                            break
                        if tentativas == 5:
                            enviar_mensagem(navegador, "Não entendi sua resposta, poderia novamente me dizer qual é o seu nome, por favor?")
                            __name__
                elif progresso == "2":
                    tentativas = 0
                    while tentativas < 5:
                        resposta = obter_resposta(f"""
                                                    Instruções:\n
                                                    1. Insira uma pergunta clara e específica no espaço \"Pergunta\".\n
                                                    2. Na seção \"Resposta\", forneça a resposta correspondente à pergunta de forma precisa e completa.\n
                                                    3. Ao receber a resposta, verifique se ela é coerente com a pergunta e se responde adequadamente a ela.\n
                                                    4. Se a resposta for coerente e responder à pergunta, responda \"SIM\".\n
                                                    5. Se a resposta não for coerente ou não responder à pergunta, responda \"NÃO\".\n
                                                    6. Interprete de lide com a possibilidade de erros de digitação ou abreviação\n
                                                    7. A resposta pode ter a quantidade por extenso ou numérico, acompanhando por \"pessoas\", \"vidas\" ou outras palavras.\n\n
                                                  
                                                    Pergunta: \"Poderia me informar o número de pessoas para a cotação, por favor?\"\n
                                                    Resposta: \"{ultimas_mensagens}\".\n\n

                                                    Observação: Seja flexível na análise da coerência.  
                                                    """)                    
                        print(f"Resposta GPT: {resposta}")
                        tentativas += 1
                        if "sim" in resposta.lower().rstrip("."):
                            resposta = obter_resposta(f"Eu enviei: Poderia me informar o número de pessoas para a cotação, por favor?\nCliente me respondeu com: {ultimas_mensagens}.\n\nDigite abaixo somente o número de pessoas.")
                            print(f"Resposta GPT: {resposta}")
                            with open(str(id)+".json", 'r') as arquivo:
                                dados = json.load(arquivo)
                            dados['progresso']['estagio'] = "3"
                            dados['progresso']['vidas'] = resposta
                            with open(str(id)+".json", 'w') as arquivo:
                                json.dump(dados, arquivo, indent=4, ensure_ascii=False)
                            enviar_mensagem(navegador, "Por gentileza, poderia me informar a idade de cada pessoa?")
                            time.sleep(1)
                            break
                        if tentativas == 5:
                            enviar_mensagem(navegador, "Não entendi sua resposta, poderia novamente me dizer o número de pessoas para a cotação, por favor?")
                            __name__
                elif progresso == "3":
                    tentativas = 0
                    while tentativas < 5:
                        resposta = obter_resposta(f"""
                                                    Instruções:\n
                                                    1. Insira uma pergunta clara e específica no espaço \"Pergunta\".\n
                                                    2. Na seção \"Resposta\", forneça a resposta correspondente à pergunta de forma precisa e completa.\n
                                                    3. Ao receber a resposta, verifique se ela é coerente com a pergunta e se responde adequadamente a ela.\n
                                                    4. Se a resposta for coerente e responder à pergunta, responda \"SIM\".\n
                                                    5. Se a resposta não for coerente ou não responder à pergunta, responda \"NÃO\".\n
                                                    6. Interprete de lide com a possibilidade de erros de digitação ou abreviação.\n
                                                    7. A resposta pode ter as idades por extenso ou numérico, separadas por vírgula, espaços ou outras formas.\n\n
                                                   
                                                    Pergunta: \"Por gentileza, poderia me informar a idade de cada pessoa?\"\n
                                                    Resposta: \"{ultimas_mensagens}\".\n\n

                                                    Observação: Seja flexível na análise da coerência.  
                                                    """)      
                        print(f"Resposta GPT: {resposta}")
                        tentativas += 1
                        if "sim" in resposta.lower().rstrip("."):
                            resposta = obter_resposta(f"Eu enviei: Por gentileza, poderia me informar a idade de cada pessoa?\nCliente me respondeu com: {ultimas_mensagens}.\n\nDigite abaixo somente as idades informadas.")
                            print(f"Resposta GPT: {resposta}")
                            with open(str(id)+".json", 'r') as arquivo:
                                dados = json.load(arquivo)
                            dados['progresso']['estagio'] = "4"
                            dados['progresso']['idades'] = resposta
                            with open(str(id)+".json", 'w') as arquivo:
                                json.dump(dados, arquivo, indent=4, ensure_ascii=False)
                            enviar_mensagem(navegador, "Qual é o seu local de residência?")
                            time.sleep(1)
                            break
                        if tentativas == 5:
                            enviar_mensagem(navegador, "Não entendi sua resposta, poderia novamente me informar a idade de cada pessoa?")
                            __name__
                elif progresso == "4":
                    tentativas = 0
                    while tentativas < 5:
                        resposta = obter_resposta(f"""
                                                    Instruções:\n
                                                    1. Insira uma pergunta clara e específica no espaço \"Pergunta\".\n
                                                    2. Na seção \"Resposta\", forneça a resposta correspondente à pergunta de forma precisa e completa.\n
                                                    3. Ao receber a resposta, verifique se ela é coerente com a pergunta e se responde adequadamente a ela.\n
                                                    4. Se a resposta for coerente e responder à pergunta, responda \"SIM\".\n
                                                    5. Se a resposta não for coerente ou não responder à pergunta, responda \"NÃO\".\n
                                                    6. Interprete de lide com a possibilidade de erros de digitação ou abreviação\n\n
                                                    
                                                    Pergunta: \"Qual é o seu local de residência?\"\n
                                                    Resposta: \"{ultimas_mensagens}\".\n\n

                                                    Observação: Seja flexível na análise da coerência.  
                                                    """)      
                        print(f"Resposta GPT: {resposta}")
                        tentativas += 1
                        if "sim" in resposta.lower().rstrip("."):
                            resposta = obter_resposta(f"Eu enviei: Qual é o seu local de residência?\nCliente me respondeu com: {ultimas_mensagens}.\n\nDigite abaixo o local informado.")
                            print(f"Resposta GPT: {resposta}")
                            with open(str(id)+".json", 'r') as arquivo:
                                dados = json.load(arquivo)
                            dados['progresso']['estagio'] = "5"
                            dados['progresso']['regiao'] = resposta
                            with open(str(id)+".json", 'w') as arquivo:
                                json.dump(dados, arquivo, indent=4, ensure_ascii=False)
                            enviar_mensagem(navegador, "Você possui alguma preferência por um hospital específico ou uma rede de hospitais em particular?")
                            time.sleep(1)
                            break
                        if tentativas == 5:
                            enviar_mensagem(navegador, "Não entendi sua resposta, poderia novamente me dizer qual é o seu local de residência, por favor?")
                            __name__
                elif progresso == "5":
                    tentativas = 0
                    while tentativas < 5:
                        resposta = obter_resposta(f"""
                                                    Instruções:\n
                                                    1. Insira uma pergunta clara e específica no espaço \"Pergunta\".\n
                                                    2. Na seção \"Resposta\", forneça a resposta correspondente à pergunta de forma precisa e completa.\n
                                                    3. Ao receber a resposta, verifique se ela é coerente com a pergunta e se responde adequadamente a ela.\n
                                                    4. Se a resposta for coerente e responder à pergunta, responda \"SIM\".\n
                                                    5. Se a resposta não for coerente ou não responder à pergunta, responda \"NÃO\".\n
                                                    6. Interprete de lide com a possibilidade de erros de digitação ou abreviação\n\n
                                                    
                                                    Pergunta: \"Você possui alguma preferência por um hospital específico ou uma rede de hospitais em particular?\"\n
                                                    Resposta: \"{ultimas_mensagens}\".\n\n

                                                    Observação: Seja flexível na análise da coerência, o cliente pode informar tanto o nome de um hospital especifico ou nome de uma rede de hospitais. Aceite \"NÃO\" como resposta válida.  
                                                    """)      
                        print(f"Resposta GPT: {resposta}")
                        tentativas += 1
                        if "sim" in resposta.lower().rstrip("."):
                            resposta = obter_resposta(f"Eu enviei: Você possui alguma preferência por um hospital específico ou uma rede de hospitais em particular?\nCliente me respondeu com: {ultimas_mensagens}.\n\nSe o cliente informou que tem preferência por hospital ou alguma rede? Digite abaixo apenas o nome da preferência do cliente, caso ele tenha respondido que não tem preferência, Digite somente \"Não\"")
                            print(f"Resposta GPT: {resposta}")
                            with open(str(id)+".json", 'r') as arquivo:
                                dados = json.load(arquivo)
                            dados['progresso']['estagio'] = "6"
                            dados['progresso']['preferencia_hospital'] = resposta
                            with open(str(id)+".json", 'w') as arquivo:
                                json.dump(dados, arquivo, indent=4, ensure_ascii=False)
                            enviar_mensagem(navegador, "Atualmente, você possui algum plano de saúde? Se sim, por favor, informe qual plano você possui atualmente.")
                            time.sleep(1)
                            break
                        if tentativas == 5:
                            enviar_mensagem(navegador, "Não entendi sua resposta, poderia novamente me se você possui alguma preferência por um hospital específico ou uma rede de hospitais em particular, por favor?")
                            __name__
                elif progresso == "6":
                    tentativas = 0
                    while tentativas < 5:
                        resposta = obter_resposta(f"""
                                                    Instruções:\n
                                                    1. Insira uma pergunta clara e específica no espaço \"Pergunta\".\n
                                                    2. Na seção \"Resposta\", forneça a resposta correspondente à pergunta de forma precisa e completa.\n
                                                    3. Ao receber a resposta, verifique se ela é coerente com a pergunta e se responde adequadamente a ela.\n
                                                    4. Se a resposta for coerente e responder à pergunta, responda \"SIM\".\n
                                                    5. Se a resposta não for coerente ou não responder à pergunta, responda \"NÃO\".\n
                                                    6. Interprete de lide com a possibilidade de erros de digitação ou abreviação\n\n
                                                    
                                                    Pergunta: \"Atualmente, você possui algum plano de saúde? Se sim, por favor, informe qual plano você possui atualmente.\"\n
                                                    Resposta: \"{ultimas_mensagens}\".\n\n

                                                    Observação: Seja flexível na análise da coerência. Aceite como coerente \"NÃO\" ou qualquer forma de negar que tenha plano atualmente.   
                                                    """)      
                        print(f"Resposta GPT: {resposta}")
                        tentativas += 1
                        if "sim" in resposta.lower().rstrip("."):
                            resposta = obter_resposta(f"Eu enviei: Atualmente, você possui algum plano de saúde? Se sim, por favor, informe qual plano você possui atualmente.\nCliente me respondeu com: {ultimas_mensagens}.\n\nDigite abaixo apenas o nome do plano informado pelo cliente, seja seco, não quero nem uma palavra a mais.")
                            print(f"Resposta GPT: {resposta}")
                            with open(str(id)+".json", 'r') as arquivo:
                                dados = json.load(arquivo)
                            dados['progresso']['estagio'] = "7"
                            dados['progresso']['plano_ativo'] = resposta
                            with open(str(id)+".json", 'w') as arquivo:
                                json.dump(dados, arquivo, indent=4, ensure_ascii=False)
                            enviar_mensagem(navegador, "Você possui CNPJ ativo?")
                            time.sleep(1)
                            break
                        if tentativas == 5:
                            enviar_mensagem(navegador, "Não entendi sua resposta, poderia novamente me dizer se você possui algum plano de saúde? Se sim, por favor, informe qual plano você possui atualmente.")
                            __name__
                elif progresso == "7":
                    tentativas = 0
                    while tentativas < 5:
                        resposta = obter_resposta(f"""
                                                    Instruções:\n
                                                    1. Insira uma pergunta clara e específica no espaço \"Pergunta\".\n
                                                    2. Na seção \"Resposta\", forneça a resposta correspondente à pergunta de forma precisa e completa.\n
                                                    3. Ao receber a resposta, verifique se ela é coerente com a pergunta e se responde adequadamente a ela.\n
                                                    4. Se a resposta for coerente e responder à pergunta, responda \"SIM\".\n
                                                    5. Se a resposta não for coerente ou não responder à pergunta, responda \"NÃO\".\n
                                                    6. Interprete de lide com a possibilidade de erros de digitação ou abreviação\n\n
                                                    
                                                    Pergunta: \"Você possui CNPJ ativo?\"\n
                                                    Resposta: \"{ultimas_mensagens}\".\n\n

                                                    Observação: Seja flexível na análise da coerência. Aceite \"NÃO\" como resposta válida.  
                                                    """)      
                        print(f"Resposta GPT: {resposta}")
                        tentativas += 1
                        if "sim" in resposta.lower().rstrip("."):
                            resposta = obter_resposta(f"Eu enviei: Você possui CNPJ ativo?\nCliente me respondeu com: {ultimas_mensagens}.\n\nSe o cliente informou que tem CNPJ, responda \"Sim\", caso contrário responda \"Não\"")
                            print(f"Resposta GPT: {resposta}")
                            with open(str(id)+".json", 'r') as arquivo:
                                dados = json.load(arquivo)
                            dados['progresso']['estagio'] = "8"
                            dados['progresso']['cnpj_ativo'] = resposta
                            with open(str(id)+".json", 'w') as arquivo:
                                json.dump(dados, arquivo, indent=4, ensure_ascii=False)
                            enviar_mensagem(navegador, "Agradeço por responder às perguntas! Em breve, um especialista da Ully Seguros e Saúde entrará em contato para fornecer mais informações e uma cotação personalizada.")
                            break
                        if tentativas == 5:
                            enviar_mensagem(navegador, "Não entendi sua resposta, poderia novamente me se você possui CNPJ ativo, por favor?")
                            __name__