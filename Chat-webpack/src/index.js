//import './styles.css';
require('./styles.css');

class ChatController {
    // Configurações constantes
    static SCROLL_CONFIG = {
        STEP: 40,           // Pixels por passo de rolagem
        INTERVAL: 50,       // Intervalo em ms para rolagem contínua
        INDICATOR_MIN: 12   // Altura mínima do indicador em %
    };

      // Elementos DOM organizados
    static DOM_ELEMENTS = {
        chatContainer: 'msger-chat',
        scrollUpButton: 'scroll-up',
        scrollDownButton: 'scroll-down',
        scrollIndicator: 'scroll-position',
        chatInput: 'chat-input-text',
        sendButton: 'sendButton',
        userCountDisplay: 'userCount',
        userNameDisplay: 'user_name',
        profileImage: '.chat-header-perfil .msg-img'
    };

    // Usuários predefinidos
    static PREDEFINED_USERS = [
        { name: "Cupuaçu", avatar: "bot01-avatar", id: 1 },
        { name: "Jabuticaba", avatar: "bot02-avatar", id: 2 },
        { name: "Açaí", avatar: "bot03-avatar", id: 3 },
        { name: "Bacuri", avatar: "bot04-avatar", id: 4 },
        { name: "Uxi", avatar: "bot05-avatar", id: 5 },
        { name: "Sistema", id: 6 },
        { name: "Servidor", id: 7 }
    ];

    constructor() {
        this.elements = this.initializeElements();
        this.webSocket = null;
        this.currentUser = null;
        this.messageHistory = [];
        this.lastMessageId = 0;
        this.scrollState = {
            isActive: false,
            timer: null
        };

        this.initializeChat();
    }

    // Inicialização dos elementos DOM
    initializeElements() {
        const elements = {};
        for (const [key, id] of Object.entries(ChatController.DOM_ELEMENTS)) {
            elements[key] = id.startsWith('.')
                ? document.querySelector(id)
                : document.getElementById(id);
        }

        if (Object.values(elements).some(el => !el)) {
            console.error("Alguns elementos DOM não foram encontrados");
        }
        return elements;
    }

    // Configuração inicial do chat
    initializeChat() {
        this.setupScrollEvents();
        this.scrollToBottom();
        this.webSocket = this.createWebSocketConnection();

        if (this.webSocket) {
            this.setupInputEvents();
        }
    }

    // Configuração dos eventos de rolagem
    setupScrollEvents() {
        const { chatContainer, scrollUpButton, scrollDownButton } = this.elements;

        this.updateScrollIndicator();
        chatContainer.addEventListener('scroll', () => this.updateScrollIndicator());

        const scrollEvents = [
            { element: scrollUpButton, direction: -1 },
            { element: scrollDownButton, direction: 1 }
        ];

        scrollEvents.forEach(({ element, direction }) => {
            this.addScrollEventListeners(element, () => this.scrollChat(direction));
        });
    }

    // Adiciona eventos de rolagem para mouse e touch
    addScrollEventListeners(element, scrollFunction) {
        const startScrolling = (e) => {
            e.preventDefault();
            if (this.scrollState.isActive) return;

            this.scrollState.isActive = true;
            scrollFunction();

            this.scrollState.timer = setInterval(scrollFunction, ChatController.SCROLL_CONFIG.INTERVAL);
        };

        const stopScrolling = () => {
            if (this.scrollState.timer) {
                clearInterval(this.scrollState.timer);
                this.scrollState.timer = null;
            }
            this.scrollState.isActive = false;
        };

        element.addEventListener('mousedown', startScrolling);
        element.addEventListener('touchstart', startScrolling);
        element.addEventListener('mouseup', stopScrolling);
        element.addEventListener('touchend', stopScrolling);
        element.addEventListener('touchcancel', stopScrolling);
        element.addEventListener('click', scrollFunction);
    }

    // Função de rolagem do chat
    scrollChat(direction) {
        this.elements.chatContainer.scrollTop += direction * ChatController.SCROLL_CONFIG.STEP;
    }

    // Atualiza o indicador de posição da rolagem
    updateScrollIndicator() {
        const { chatContainer, scrollIndicator } = this.elements;
        const scrollableHeight = chatContainer.scrollHeight - chatContainer.clientHeight;
        const scrollPercentage = (chatContainer.scrollTop / scrollableHeight) * 100;
        const indicatorHeight = Math.min(
            Math.max(scrollPercentage, ChatController.SCROLL_CONFIG.INDICATOR_MIN),
            100
        );

        scrollIndicator.style.bottom = `${100 - indicatorHeight}%`;
    }

    // Rola para o final do chat
    scrollToBottom() {
        const { chatContainer } = this.elements;
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }

    // Cria conexão WebSocket
    createWebSocketConnection() {
        try {
            const ws = new WebSocket(`ws://192.168.4.1:81/ws`);

            ws.onopen = () => this.handleWebSocketOpen();
            ws.onmessage = (event) => this.handleWebSocketMessage(event);
            ws.onclose = (event) => this.handleWebSocketClose(event);
            ws.onerror = (error) => this.handleWebSocketError(error);

            return ws;
        } catch (error) {
            this.addSystemMessage("Falha ao conectar. Tente novamente mais tarde.");
            console.error("Erro ao criar WebSocket:", error);
            return null;
        }
    }

    // Configura eventos de entrada
    setupInputEvents() {
        const { sendButton, chatInput } = this.elements;

        sendButton.onclick = () => this.sendMessage();
        chatInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') this.sendMessage();
        });
    }

    // Método que estava ausente
    handleWebSocketOpen() {
        this.addSystemMessage("Conectado ao servidor!");
    }

    handleWebSocketClose(event) {
        this.addSystemMessage(`Desconectado do servidor (código: ${event.code})!`);
        setTimeout(() => {
            this.addSystemMessage("Tentando reconectar...");
            this.initializeChat();
        }, 5000);
    }

    handleWebSocketError(error) {
        this.addSystemMessage("Erro de conexão");
        console.error("Erro de WebSocket:", error);
    }

    // Manipula mensagem WebSocket recebida
    handleWebSocketMessage(event) {
        try {
            const data = JSON.parse(event.data);

            switch (data.type) {
                case 'message':
                    this.handleNewMessage(data);
                    break;
                case 'identify':
                    this.addSystemMessage(`${data.username || 'Novo usuário'} se conectou`);
                    break;
                case 'idClient':
                    this.handleClientIdentification(data);
                    break;
                case 'userCount':
                    this.elements.userCountDisplay.textContent = data.count;
                    break;
                case 'userDesconect':
                    this.handleUserDisconnect(data);
                    break;
                case 'syncRequest':
                    this.handleSyncRequest(data);
                    break;
                case 'syncResponse':
                    this.handleSyncResponse(data);
                    break;
            }
        } catch (error) {
            this.addSystemMessage("Erro ao processar mensagem");
            console.error("Erro ao processar mensagem WebSocket:", error);
        }
    }

    // Método que estava ausente
    handleSyncRequest(data) {
        if (!data.targetClientId && this.isWebSocketOpen()) {
            if (this.messageHistory.length > data.messageCount) {
                this.webSocket.send(JSON.stringify({
                    type: 'syncResponse',
                    targetClientId: data.clientId,
                    history: this.messageHistory,
                    sender: this.currentUser.name,
                    senderId: this.currentUser.id
                }));
            }
        }
    }

    // Método que estava ausente
    handleSyncResponse(data) {
        console.log(data);
        if (data.targetClientId === this.currentUser.id && data.history?.length > 0) {
            if (this.messageHistory.length === 0) {
                this.elements.chatContainer.innerHTML = '';
            }

            data.history.forEach(msg => {
                const exists = this.messageHistory.some(m =>
                    m.id === msg.id && m.userId === msg.usuarioId
                );
                if (!exists) {
                    const type = msg.userId === this.currentUser.id ? "right-msg" : "left-msg";
                    this.addMessage(msg.content, type, msg.userId, msg.timestamp);
                    if (msg.id > this.lastMessageId) this.lastMessageId = msg.id;
                    this.messageHistory.push({
                        id: msg.id,
                        timestamp: msg.timestamp,
                        userId: msg.userId,
                        content: msg.content
                    });
                }
            });

            this.addSystemMessage("Histórico sincronizado!");
        }
    }

    handleUserDisconnect(data) {
        const user = this.getUserById(parseInt(data.content));
        this.addSystemMessage(`${user.name} desconectou`);
    }

    // Manipula nova mensagem
    handleNewMessage(data) {
        const exists = this.messageHistory.some(m =>
            m.id === data.id && m.userId === data.senderId
        );

        if (!exists) {          
            const messageType = data.senderId === this.currentUser.id ? "right-msg" : "left-msg";
            this.addMessage(data.content, messageType, data.senderId, data.timestamp);
            this.messageHistory.push({
                id: data.id || ++this.lastMessageId,
                timestamp: data.timestamp || this.getFormattedTime(),
                userId: data.senderId,
                content: data.content
            });
        }
    }

    // Manipula identificação do cliente
    handleClientIdentification(data) {
        this.currentUser = this.getUserById(parseInt(data.content));
        this.elements.userNameDisplay.textContent = this.currentUser.name;
        this.elements.profileImage.classList.add(this.currentUser.avatar);

        this.addSystemMessage(`Você está conectado como ${this.currentUser.name}`);

        this.webSocket.send(JSON.stringify({
            type: 'identify',
            username: this.currentUser.name,
            clientId: this.currentUser.id
        }));

        setTimeout(() => this.requestHistorySync(), 1000);
    }

    // Adiciona mensagem ao chat
    addMessage(content, type, userId, timestamp) {
        const messageElement = document.createElement('div');
        messageElement.className = `msg ${type === 'system' ? 'center-msg' : type}`;

        const bubbleElement = document.createElement('div');
        bubbleElement.className = 'msg-bubble';

        const infoElement = document.createElement('div');
        infoElement.className = 'msg-info';

        const textElement = document.createElement('div');
        textElement.className = 'msg-text';
        textElement.textContent = content;

        if (userId) {

            const user = this.getUserById(userId);
            const avatarElement = document.createElement('div');
            avatarElement.className = `msg-img ${user.avatar}`;
            messageElement.appendChild(avatarElement);

            const nameElement = document.createElement('div');
            nameElement.className = 'msg-info-name';
            nameElement.textContent = user.name;
            infoElement.appendChild(nameElement);
        }

        if (timestamp) {
            const timeElement = document.createElement('div');
            timeElement.className = 'msg-info-time';
            timeElement.textContent = timestamp;
            infoElement.appendChild(timeElement);
        }

        if (type === 'system') {
            const nameElement = document.createElement('div');
            nameElement.className = 'msg-info-name';
            nameElement.textContent = 'Sistema';
            infoElement.appendChild(nameElement);
        }

        bubbleElement.appendChild(infoElement);
        bubbleElement.appendChild(textElement);
        messageElement.appendChild(bubbleElement);

        this.elements.chatContainer.appendChild(messageElement);
        this.scrollToBottom();
    }

    // Adiciona mensagem do sistema
    addSystemMessage(content) {
        this.addMessage(content, 'system');
    }

    // Envia mensagem
    sendMessage() {
        const content = this.elements.chatInput.value.trim();
        if (!content || !this.isWebSocketOpen()) return;

        const messageId = ++this.lastMessageId;
        const timestamp = this.getFormattedTime();

        this.webSocket.send(JSON.stringify({
            type: 'message',
            sender: this.currentUser.name,
            content,
            senderId: this.currentUser.id,
            id: messageId,
            timestamp
        }));

        this.addMessage(content, "right-msg", this.currentUser.id, timestamp);
        this.messageHistory.push({
            id: messageId,
            timestamp,
            userId: this.currentUser.id,
            content
        });

        this.elements.chatInput.value = '';
    }

    // Obtém horário formatado
    getFormattedTime() {
        const date = new Date();
        return `${date.getDate().toString().padStart(2, '0')}/` +
            `${(date.getMonth() + 1).toString().padStart(2, '0')}/` +
            `${date.getFullYear()} ` +
            `${date.getHours().toString().padStart(2, '0')}:` +
            `${date.getMinutes().toString().padStart(2, '0')}`;
    }

    // Obtém usuário por ID
    getUserById(id) {
        return ChatController.PREDEFINED_USERS.find(user => user.id === id);
    }

    // Verifica se WebSocket está aberto
    isWebSocketOpen() {
        return this.webSocket && this.webSocket.readyState === WebSocket.OPEN;
    }

    // Solicita sincronização do histórico
    requestHistorySync() {
        if (this.isWebSocketOpen()) {
            this.webSocket.send(JSON.stringify({
                type: 'syncRequest',
                username: this.currentUser.name,
                clientId: this.currentUser.id,
                messageCount: this.messageHistory.length
            }));
        }
    }
}
new ChatController()
