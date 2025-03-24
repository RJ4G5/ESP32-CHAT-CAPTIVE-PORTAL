

# Especificações do código para ESP32

Este documento explica o funcionamento do código para a optimização do servidor no ESP32. projetado para rodar em um ESP32, um microcontrolador com recursos limitados de memória e processamento. O código implementa um ponto de acesso Wi-Fi, um servidor DNS, um servidor HTTP e um servidor WebSocket para criar um sistema de chat local. O design foi otimizado para gerenciar memória de forma eficiente suportando até 5 conexões simultâneas

## 1. Função `main()`

A função `main()` é a principal do programa. Ela realiza as seguintes tarefas:
```python
async def main():
    # Limpar memória
    gc.collect()
    await split_html_content('chat.html', 'fragments', FRAGMENT_SIZE)
    # Configurar rede
    ap = await setup_network()
    
    # Iniciar servidores
    dns_server = DNSServer(AP_IP)
    websocket_server = WebSocketServer(81)
    web_server = WebServer(80, websocket_server)
    
    # Executar servidores em tarefas paralelas
    await asyncio.gather(
        dns_server.run(),
        web_server.run(),
        websocket_server.run()
    )
  ```

1. **Libera a memória** utilizando `gc.collect()`.
2. **Divide o arquivo `chat.html` em fragmentos menores** com `split_html_content()` para otimizar o uso de memória. (maximo 5kb por fragmento para facilitar o carregamento em pedaços, evitando o uso excessivo de RAM)
3. **Configura o ponto de acesso Wi-Fi**, definindo um SSID e senha.
4. **Inicializa os servidores**:
   - `DNSServer`: Redireciona todo o tráfego DNS para o ESP32.
   - `WebSocketServer`: Gerencia conexões WebSocket.
   - `WebServer`: Fornece serviços HTTP, incluindo uma página de aviso caso o limite de conexões seja atingido.
5. **Executa os servidores de forma assíncrona** com `asyncio.gather()`, maximizando o uso do processador single-core do ESP32.

### Por que assim:
O uso de asyncio permite lidar com múltiplas conexões sem bloqueio, essencial para um dispositivo com um único núcleo.
A fragmentação inicial do HTML e a limpeza de memória são estratégias para evitar estouro de RAM, comum em dispositivos como o ESP32

---

## 2. Classe `DNSServer`

Implementa um servidor DNS simples para capturar todas as consultas e redirecioná-las ao ESP32.

- **`start()`**: Configura um socket UDP para escutar na porta 53 (DNS).
- **`process_request()`**: Lê uma requisição DNS e retorna um IP fixo (o do ESP32).
- **`run()`**: Mantém o servidor rodando, processando requisições continuamente.

> **Motivo da Implementação**: Isso permite que dispositivos conectados ao ESP32 sempre resolvam qualquer domínio para o IP local, simulando um portal cativo.


---

## 3. Classe `WebServer`

Este é o servidor HTTP que lida com requisições GET e POST.

- **`start()`**: Inicia um servidor HTTP na porta 80.
- **`handle_http_request(client, addr)`**:
  - Recebe dados em pedaços de 512 bytes para economizar memória. 
    ```python 
    chunk = client.recv(512) 
    ```
  - Responde a GETs com arquivos como loader.html ou fragmentos.
  - Envia uma página de erro se o limite de conexões WebSocket for atingido.
      ```python 
     if hasattr(self, 'websocket_server') and self.websocket_server and len(self.websocket_server.clients) >= MAX_CONNECTIONS:
                # Enviar página de limite excedido
                client.send(b'HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n')
                client.send(LIMIT_EXCEEDED_HTML.encode())
    ```
  - Processa as requisições HTTP.
  - Implementa um mecanismo de timeout para conexões lentas.
  - Envia respostas fragmentadas para evitar o consumo excessivo de RAM.
    ```python 
      # Ler e enviar o arquivo em chunks pequenos
      buffer_size = 512  # Reduzido para 512 bytes
      while True:
          chunk = file.read(buffer_size)
          if not chunk:
              break
          client.send(chunk.encode())
          await asyncio.sleep(0.01)
          gc.collect()  # Liberar memória após cada envio
    ```
  
- **`run()`**: Aceita conexões de clientes e cria uma nova tarefa para processá-las.

> **Motivo da Implementação**: A fragmentação e as otimizações ajudam a evitar o estouro de memória no ESP32.

---

## 4. Classe `WebSocketServer`

Gerencia conexões WebSocket para comunicação em tempo real.

- **`start()`**: Configura um servidor WebSocket na porta 81.
- **`handle_websocket(client, addr)`**:
  - Realiza o handshake WebSocket.
  - Adiciona o cliente a uma lista gerenciada pela classe `ListaFixa`.
  - Gerencia a troca de mensagens entre clientes.
- **`decode_websocket_frame(data)`**: Decodifica mensagens WebSocket.
- **`send_message(client, message)`**: Envia mensagens para clientes conectados.
- **`broadcast_user_count()`**: Envia para todos os clientes o número atual de usuários conectados.

> **Motivo da Implementação**: Garante um chat em tempo real com mínimo impacto na memória do ESP32.

---

## 5. Classe `ListaFixa`

Implementa uma lista de tamanho fixo para gerenciar até 5 clientes WebSocket.

- **`add(elemento)`**: Adiciona um cliente na primeira posição disponível.
- **`remove(elemento)`**: Remove um cliente e libera espaço.
- **`getIndice(elemento)`**: Retorna o índice de um cliente.
- **`getLength()`**: Retorna o número de conexões ativas.

> **Motivo da Implementação**: Observando na documentação do chat.html, as identificações dos usuários são definidas previamente em um array chamado "PREDEFINED_USERS", onde o ID de cada usuário corresponde ao índice dessa lista fixa no servidor. Quando um usuário se desconecta, ele é removido da lista, liberando o índice para que um novo usuário possa se conectar. Dessa forma, os índices podem ser reutilizados como IDs sem gerar duplicidades

---

## 6. Função `split_html_content(filename, output_dir, fragment_size)`

Essa função é responsavel por dividir um arquivo em fragmentos de 5kb para otimizar a memória. 5kb é um tamanho ideal para evitar perda de dados nas requisições http com base nas observações durante os testes.
 - Cria um index.txt com metadados (número de fragmentos, tamanho original)
 - Lê o arquivo em blocos de 256 bytes e grava fragmentos de 5KB. 


> **Motivo da Implementação**: Evita sobrecarga ao carregar arquivos grandes na RAM do ESP32, com isso a pagina loader.html que é <= 5kb, consegue carregar paginas grandes como chat.html.

---

## 7. Função `setup_network()`

Configura o ESP32 como um ponto de acesso Wi-Fi.

> **Motivo da Implementação**: Permite conexões diretas ao ESP32 sem necessidade de roteador.

---

## Conclusão

O código foi projetado para atender as limitações de memória do ESP32, utilizando fragmentação de arquivos, listas de conexão otimizadas e gerenciamento eficiente de sockets. Com essa arquitetura, é possível fornecer serviços de comunicação em tempo real sem comprometer a estabilidade do dispositivo.

