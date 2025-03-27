### Chat Móvel via Captive Portal com ESP32 MicroPython

#### O início da jornada

Tudo começou com uma ideia simples e um ESP32. Enquanto explorava os exemplos da IDE do Arduino, percebi que era possível criar um captive portal e carregar uma página local. Foi aí que pensei:

Por que não criar um chat? Um sistema fora da internet onde qualquer pessoa pudesse se comunicar, como em um condomínio ou escola, sem precisar expor sua identidade.

#### Colocando o plano em prática

Para dar vida a essa ideia, eu precisava de um servidor HTTP e um servidor WebSocket para realizar experimentos. No entanto, as limitações do ESP32 logo se tornaram um obstáculo. Tentei de tudo: bibliotecas, ajuda de colegas, fóruns, códigos disponíveis no GitHub... Nada parecia atender às necessidades do projeto. Até mesmo LLMs, como o ChatGPT, afirmavam que era inviável implementar a ideia no ESP32 devido às suas restrições de hardware. Confesso que fiquei desanimado, quase aceitando que era impossível.

Com o tempo, amadureci e percebi que, tudo é possível nas limitações atribuidas. Foi então que me deparei com uma LLM chamada Claude.ai. Diferente das outras, ela demonstrava uma abordagem mais eficaz na construção de códigos. Isso reacendeu minha esperança.

#### A solução

Utilizando o Claude.ai, consegui criar um servidor HTTP combinado com um WebSocket otimizado para o ESP32. Finalmente, funcionou! Depois de tanto tempo, essa LLM me forneceu o material bruto necessário para avançar. Embora eu não tenha construído o servidor do zero, adaptei-o para atender exatamente às minhas necessidades.

### Especificações de Hardware do ESP32 usado (ESP32-WROOM-32)
- **Processador:** Dual-core 32bits até 240 MHz
-  **Memória RAM:** 520 KB de SRAM
- **MemóriaInterna (Flash):**  4 MB (32 Mbit)
-  **Wi-Fi:** 802.11 b/g/n (2.4 GHz), com suporte a taxas de até 150 Mbp

### A estrada até aqui
Foram realizados vários testes, a ponto de já começar a acreditar que não seria possível, mas eu tinha que testar todas as possibilidades para afirmar que não seria possível. Várias otimizações foram testadas para chegar ao que estou colocando neste repositório.

#### Nos testes, foram observadas as seguintes questões:

- Há perda de dados em respostas HTTP maiores que 5 KB.
- A memória é mais limitada do que 520 KB de RAM, tendo uma memória livre de 140 KB `gc.mem_free()` antes de iniciar a aplicação.
- Todo arquivo deve ser lido e processado em partes de bytes para não haver estouro de memória.
- O ESP32 suporta até 5 conexões estáveis WebSocket


Esses pontos foram os responsaveis pelas otimizações para que no final a aplicação funcione.

Então, para tudo funcionar, primeiro a função `split_html_content(filename, output_dir, fragment_size=FRAGMENT_SIZE)` fragmenta o chat.html em pedaços de 5 KB e depois inicia o servidor com a página loader.html como página principal. O loader.html é o responsável por carregar cada fragmento e montá-lo no lado do cliente. Todo arquivo é lido e enviado em partes de 256 e 512 bytes para evitar estouro de memória. Podem ver mais em:
- [Documentação chat.html](https://github.com/RJ4G5/ESP32-CHAT-CAPTIVE-PORTAL/blob/main/Documenta%C3%A7%C3%A3o/chat.html.md)
- [Documentação main.py](https://github.com/RJ4G5/ESP32-CHAT-CAPTIVE-PORTAL/blob/main/Documenta%C3%A7%C3%A3o/main.py.md)

### Requisitos de produção

- Foi utilizao a IDE Thonny 
- MicroPython v1.24.1 on 2024-11-29; Generic ESP32 module with ESP32
- Bibliotecas externas `uwebsocket.py` e `uasyncio`

Para instalar as bibliotecas, você pode colar o seguinte codigo no shell do Thonny:
```python
import network

# Configurar modo estação
sta_if = network.WLAN(network.STA_IF)
sta_if.active(True)
sta_if.connect('NOME_DA_REDE', 'SENHA')

# Verificar conexão
sta_if.isconnected()

import mip
mip.install("uwebsockets")
mip.install("uasyncio")

```

Na pasta Arquivos-micropython do repositório, estão todos os arquivos já prontos para upload no ESP32. Utilizei o Webpack para que o HTML fique bem comprimido. Você pode usar o Thonny IDE ou Ampy para subir os arquivos para o esp32.

#### Fazendo o upload dos arquivos no esp32(micropython) no windows com Ampy

- Abra o terminal (CMD) na pasta Arquivos-MicroPython que está neste repositório
- Instale o ampy `pip install adafruit-ampy` pelo terminal
- Depois você tem que identificar a porta COM que seu ESP está conectado; no meu caso, é a porta COM5
- No terminal você pode fazer put de cada arquivo por vez `ampy --port COM5 put main.py` ou usar um loop para agilizar `for %f in (*.py *.html) do ampy --port COM5 put %f`, a demora é de acordo com o tamanho
- E por fim, só dar um reset pelo ampy, se não funcionar dê um reset pelo botão do ESP32

Recomendo o uso do Thonny IDE caso não esteja familiarizado com o MicroPython; com ele, você pode fazer tudo que precisa, até mesmo instalar o firmware mais recente.
