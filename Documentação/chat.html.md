# Documentação da classe ChatController

## Propósito Geral e Contexto de Uso

O `ChatController` é uma classe JavaScript projetada para gerenciar um sistema de chat em tempo real utilizando WebSocket para comunicação com um servidor. Seu propósito é permitir que usuários pré-definidos (com nomes inspirados em frutas) troquem mensagens em uma interface de chat com rolagem personalizada, indicadores visuais e sincronização de histórico. O código é ideal para aplicações web que requerem interação em tempo real.

- **OBS:** Este código implementa um sistema de rolagem com botões de "subir" e "descer", suportando tanto o pressionamento longo quanto o rápido, necessário devido à limitação de recursos do navegador no Captive Portal

---

## Estrutura Geral

O código é composto por:

- **Constantes estáticas**: Configurações de rolagem, elementos DOM e lista de usuários pré-definidos.
- **Métodos de inicialização**: Configuram o chat e a conexão WebSocket.
- **Gerenciamento de eventos**: Controlam rolagem, entrada de usuário e mensagens WebSocket.
- **Manipulação de mensagens**: Exibem e sincronizam mensagens no chat.

---

## Descrição Detalhada das Funções

### 1. `constructor()`

- **Propósito**: Inicializa a instância do `ChatController`.
- **Parâmetros**: Nenhum.
- **Retorno**: Nenhum (configura propriedades internas).
- **Papel**: Define os elementos DOM, cria o estado inicial (como histórico de mensagens e estado de rolagem) e chama `initializeChat()` para configurar o sistema.

### 2. `initializeElements()`

- **Propósito**: Localiza e armazena referências aos elementos DOM.
- **Parâmetros**: Nenhum.
- **Retorno**: Objeto com referências aos elementos DOM.
- **Papel**: Usa `ChatController.DOM_ELEMENTS` para buscar elementos pelo ID ou seletor CSS. Registra erro no console se algum elemento não for encontrado.

### 3. `initializeChat()`

- **Propósito**: Configura o chat no início.
- **Parâmetros**: Nenhum.
- **Retorno**: Nenhum.
- **Papel**: Configura eventos de rolagem, rola para o final do chat e inicia a conexão WebSocket.

### 4. `setupScrollEvents()`

- **Propósito**: Configura eventos de rolagem para botões de subir/descer.
- **Parâmetros**: Nenhum.
- **Retorno**: Nenhum.
- **Papel**: Atualiza o indicador de rolagem e associa eventos de clique e pressão contínua aos botões.

### 5. `addScrollEventListeners(element, scrollFunction)`

- **Propósito**: Adiciona eventos de rolagem (mouse e touch) a um elemento.
- **Parâmetros**:
  - `element`: Elemento DOM (botão de rolagem).
  - `scrollFunction`: Função a ser chamada para rolar.
- **Retorno**: Nenhum.
- **Papel**: Implementa rolagem contínua enquanto o botão é pressionado, parando ao soltar.

### 6. `scrollChat(direction)`

- **Propósito**: Move o chat na direção especificada.
- **Parâmetros**:
  - `direction`: Inteiro (`-1` para cima, `1` para baixo).
- **Retorno**: Nenhum.
- **Papel**: Ajusta a posição de rolagem do container em `STEP` pixels.

### 7. `updateScrollIndicator()`

- **Propósito**: Atualiza a posição visual do indicador de rolagem.
- **Parâmetros**: Nenhum.
- **Retorno**: Nenhum.
- **Papel**: Calcula a porcentagem de rolagem e ajusta o estilo do indicador.

### 8. `scrollToBottom()`

- **Propósito**: Rola o chat até o final.
- **Parâmetros**: Nenhum.
- **Retorno**: Nenhum.
- **Papel**: Usado para exibir mensagens novas automaticamente.

### 9. `createWebSocketConnection()`

- **Propósito**: Estabelece a conexão WebSocket com o servidor.
- **Parâmetros**: Nenhum.
- **Retorno**: Objeto WebSocket ou `null` (se falhar).
- **Papel**: Configura eventos de abertura, mensagem, fechamento e erro.

### 10. `setupInputEvents()`

- **Propósito**: Configura eventos para envio de mensagens.
- **Parâmetros**: Nenhum.
- **Retorno**: Nenhum.
- **Papel**: Associa o clique no botão de envio e a tecla Enter ao método `sendMessage()`.

### 11. `handleWebSocketOpen()`, `handleWebSocketClose(event)`, `handleWebSocketError(error)`

- **Propósito**: Manipulam eventos do WebSocket.
- **Parâmetros**:
  - `event` (close): Contém código de fechamento.
  - `error` (error): Objeto de erro.
- **Retorno**: Nenhum.
- **Papel**: Exibem mensagens de sistema e tentam reconectar após falha.

### 12. `handleWebSocketMessage(event)`

- **Propósito**: Processa mensagens recebidas do servidor.
- **Parâmetros**:
  - `event`: Evento WebSocket com dados JSON.
- **Retorno**: Nenhum.
- **Papel**: Analisa o tipo de mensagem (`message`, `identify`, etc.) e chama o manipulador correspondente.

### 13. `handleSyncRequest(data)`, `handleSyncResponse(data)`

- **Propósito**: Sincronizam o histórico de mensagens entre clientes.
- **Parâmetros**:
  - `data`: Objeto JSON com informações da solicitação/resposta.
- **Retorno**: Nenhum.
- **Papel**: Gerenciam a troca de histórico entre clientes para manter consistência.

### 14. `handleNewMessage(data)`

- **Propósito**: Processa uma nova mensagem recebida.
- **Parâmetros**:
  - `data`: Objeto JSON com conteúdo, remetente, etc.
- **Retorno**: Nenhum.
- **Papel**: Adiciona a mensagem ao chat e ao histórico, evitando duplicatas.

### 15. `handleClientIdentification(data)`

- **Propósito**: Identifica o cliente atual.
- **Parâmetros**:
  - `data`: Objeto JSON com ID do cliente.
- **Retorno**: Nenhum.
- **Papel**: Define o usuário atual e solicita sincronização do histórico.

### 16. `addMessage(content, type, userId, timestamp)`

- **Propósito**: Adiciona uma mensagem ao chat.
- **Parâmetros**:
  - `content`: Texto da mensagem.
  - `type`: Tipo (`left-msg`, `right-msg`, `system`).
  - `userId`: ID do usuário (opcional).
  - `timestamp`: Data/hora (opcional).
- **Retorno**: Nenhum.
- **Papel**: Cria o elemento DOM da mensagem e rola para o final.

### 17. `sendMessage()`

- **Propósito**: Envia uma mensagem ao servidor.
- **Parâmetros**: Nenhum.
- **Retorno**: Nenhum.
- **Papel**: Constrói e envia o objeto JSON da mensagem, adicionando-a localmente.

### 18. `getFormattedTime()`

- **Propósito**: Gera uma string de data/hora formatada.
- **Parâmetros**: Nenhum.
- **Retorno**: String no formato `DD/MM/YYYY HH:MM`.
- **Papel**: Usada para timestamps de mensagens.

### 19. `getUserById(id)`

- **Propósito**: Busca um usuário por ID.
- **Parâmetros**:
  - `id`: Inteiro representando o ID do usuário.
- **Retorno**: Objeto usuário ou `undefined`.
- **Papel**: Recupera informações de usuários pré-definidos.

### 20. `requestHistorySync()`

- **Propósito**: Solicita sincronização do histórico.
- **Parâmetros**: Nenhum.
- **Retorno**: Nenhum.
- **Papel**: O novo usuário solicita o histórico de mensagens para todos os usuários, e o método `handleSyncRequest(data)` processa o histórico recebido.

---

## Comunicação via WebSocket

### Funcionamento Geral

O WebSocket conecta-se ao endereço `ws://192.168.4.1:81/ws`, endereço local do ESP32. A comunicação é bidirecional e baseada em mensagens JSON com tipos específicos:

- `message`: Nova mensagem de um usuário.
- `identify`: Identificação de um novo cliente.
- `idClient`: Atribuição de ID ao cliente atual.
- `userCount`: Atualização do número de usuários.
- `syncRequest`/`syncResponse`: Sincronização de histórico.

### Uso de Broadcast

O servidor usa um broadcast para enviar mensagens a todos os clientes conectados. Por exemplo:

- Quando um cliente envia uma mensagem via `sendMessage()`, o servidor a retransmite a todos, menos o remetente.
- Eventos como `userDesconect` também são transmitidos a todos os clientes.

---

## Limitação de Usuários a 5

### Implementação

A limitação reflete a um número máximo de conexões simultâneas estáveis que o ESP32 surporta, por isso uma lista estática `PREDEFINED_USERS`, que contém 5 usuários com avatares (`Cupuaçu`, `Jabuticaba`, `Açaí`, `Bacuri`, `Uxi`). O servidor associa cada conexão a um desses IDs, que é o indice do `self.clients = ListaFixa(5)`, limitando o número de usuários únicos a 5.

### Implicações

- **Captive Portal**: Funcionalidades do navegador restritas por motivos de segurança.
- **Tamanho**: Quanto maior for o chat.html, maior será a quantidade de fragmentos de 5kb, o que acaba limitando o uso de frameworks como Vue ou aumentando a complexidade do chat.

---

### Código HTML Exemplo

```html
<!DOCTYPE html>
<html lang="pt-BR">
  <head>
    <title>ESP32 Chat</title>
    <meta
      name="viewport"
      content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no"
    />
    <meta charset="UTF-8" />
  </head>

  <body>
    <div class="root">
      <div class="chat-body">
        <div class="chat-header">
          <div class="chat-header-perfil">
            <div class="msg-img" style="width: 33px;height: 33px;"></div>
            <div class="perfil-user">
              <span> Conectado como <strong id="user_name">---</strong> </span>
              <span>
                <userCount id="userCount">--</userCount> usuários online
              </span>
            </div>
          </div>
        </div>
        <div class="control-buttons">
          <button class="btn-control" id="scroll-up">Subir</button>
          <div class="scroll-indicator-container">
            <div class="msger-chat" id="msger-chat"></div>

            <div class="scroll-indicator">
              <div id="scroll-position" class="scroll-position"></div>
            </div>
          </div>

          <button class="btn-control" id="scroll-down">Descer</button>
        </div>

        <div class="chat-input">
          <div class="chat-input-text">
            <textarea
              id="chat-input-text"
              placeholder="O que está acontecendo?"
            ></textarea>
            <button id="sendButton">Enviar</button>
          </div>
        </div>
      </div>
    </div>
  </body>
</html>
```
