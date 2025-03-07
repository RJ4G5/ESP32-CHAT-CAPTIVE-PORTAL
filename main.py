import network
import socket
import time
import gc
import uasyncio as asyncio
import json
import urandom

# Configurações
AP_SSID = 'ESP32-CHAT'
AP_PASSWORD = '12345678'
AP_IP = '192.168.4.1'
MAX_CONNECTIONS = 5  # Limite máximo de conexões WebSocket simultâneas

# HTML da página de chat
CHAT_HTML = """

<!DOCTYPE html>
<html>
<head>
    <title>ESP32 Chat</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body{font-family:Arial;max-width:600px;margin:0 auto;padding:20px}
        #chat{height:300px;overflow-y:scroll;border:1px solid #ccc;padding:10px;margin-bottom:10px}
        #messageInput{width:70%;padding:10px}
        #sendButton{width:25%;padding:10px}
        .message{margin-bottom:8px;padding:8px;border-radius:4px}
        .mine{background-color:#e1f5fe;text-align:right}
        .others{background-color:#f1f1f1}
        .system{background-color:#fffde7;text-align:center;font-style:italic}
        .user-count{text-align:right;font-size:.9em;color:#666;margin-bottom:10px}
    </style>
</head>
<body>
    <h2>ESP32 Chat</h2>
    <div class="user-count"><span id="userCount">1</span> usuários online</div>
    <div id="chat"></div>
    <div>
        <input type="text" id="messageInput" placeholder="Digite sua mensagem">
        <button id="sendButton">Enviar</button>
    </div>

<script>
// Variáveis globais compactadas
const el={chat:document.getElementById('chat'),input:document.getElementById('messageInput'),
btn:document.getElementById('sendButton'),count:document.getElementById('userCount')};
let history=[], lastId=0, syncDone=false, syncReq=false;

// Detectar dispositivo e criar username
function getDevice(){
    const ua=navigator.userAgent;
    if(/iPhone/.test(ua)) return 'iPhone';
    if(/iPad/.test(ua)) return 'iPad';
    if(/Android/.test(ua)){
        const m=ua.match(/Android.*?; (.*?) Build/);
        return m && m[1] ? m[1].trim() : 'Android';
    }
    if(/Windows/.test(ua)) return 'Windows';
    if(/Mac/.test(ua)) return 'Mac';
    if(/Linux/.test(ua)) return 'Linux';
    return 'Unknown';
}

// Gerar ID e nome
const rnd=Math.floor(Math.random()*10000);
const device=getDevice();
const username=device+'_'+rnd;
const clientId=Date.now()+Math.floor(Math.random()*1000);

// Obter data/hora
function getTime(){
    const d=new Date();
    return `${String(d.getDate()).padStart(2,'0')}/${String(d.getMonth()+1).padStart(2,'0')}/${d.getFullYear()} ${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}`;
}

// WebSocket
const ws=new WebSocket('ws://'+window.location.hostname+':81/ws');

// Conectar
ws.onopen=function(){
    addMsg("Conectado ao chat!", "system");
    
    // Identificar
    ws.send(JSON.stringify({
        type:'identify',
        username:username,
        clientId:clientId
    }));
    
    // Pedir histórico após delay
    setTimeout(()=>{
        if(!syncReq) requestSync();
    }, 1000);
};

// Solicitar histórico
function requestSync(){
    syncReq=true;
    ws.send(JSON.stringify({
        type:'syncRequest',
        username:username,
        clientId:clientId
    }));
}

// Receber mensagens
ws.onmessage=function(e){
    try{
        const data=JSON.parse(e.data);
        
        // Tipo de mensagem
        if(data.type==='message'){
            // Verificar duplicação
            const exists=history.some(m=>m.id===data.id && m.usuario===data.sender);
            
            if(!exists){
                addMsg(data.sender+": "+data.content, data.senderId===clientId?"mine":"others");
                
                // Guardar no histórico
                history.push({
                    id:data.id || ++lastId,
                    data:data.timestamp || getTime(),
                    usuario:data.sender,
                    mensagem:data.content
                });
            }
        }
        else if(data.type==='connect'){
            // Notificação de conexão
            addMsg(`${data.username || 'Novo usuário'} se conectou`, "system");
        }
        else if(data.type==='userCount'){
            // Atualizar contador
            el.count.textContent=data.count;
        }
        else if(data.type==='syncRequest' && !data.targetClientId){
            // Pedido de sincronização - responder com probabilidade de 30%
            if(Math.random()<0.3 && history.length>0){
                ws.send(JSON.stringify({
                    type:'syncResponse',
                    targetClientId:data.clientId,
                    history:history,
                    sender:username,
                    senderId:clientId
                }));
            }
        }
        else if(data.type==='syncResponse' && data.targetClientId===clientId){
            // Recebendo histórico
            if(!syncDone && data.history && data.history.length>0){
                // Limpar chat se vazio
                if(history.length===0) el.chat.innerHTML='';
                
                // Processar histórico
                data.history.forEach(msg=>{
                    const exists=history.some(m=>m.id===msg.id && m.usuario===msg.usuario);
                    
                    if(!exists){
                        const type=msg.usuario===username?"mine":"others";
                        addMsg(`${msg.usuario}: ${msg.mensagem}`, type);
                        
                        if(msg.id>lastId) lastId=msg.id;
                        history.push(msg);
                    }
                });
                
                // Ordenar por data
                history.sort((a,b)=>{
                    return new Date(a.data.replace(/(\d{2})\/(\d{2})\/(\d{4})/, '$3-$2-$1')) - 
                           new Date(b.data.replace(/(\d{2})\/(\d{2})\/(\d{4})/, '$3-$2-$1'));
                });
                
                syncDone=true;
                addMsg("Histórico sincronizado!", "system");
            }
        }
    }catch(e){
        addMsg(e.data, "system");
    }
};

// Desconectar
ws.onclose=function(){
    addMsg("Desconectado do servidor!", "system");
};

// Adicionar mensagem
function addMsg(msg, type){
    const div=document.createElement('div');
    div.textContent=msg;
    div.className='message '+type;
    el.chat.appendChild(div);
    el.chat.scrollTop=el.chat.scrollHeight;
}

// Enviar mensagem
function sendMessage(){
    const msg=el.input.value.trim();
    if(msg){
        // Gerar ID e timestamp
        const msgId=++lastId;
        const time=getTime();
        
        // Enviar
        ws.send(JSON.stringify({
            type:'message',
            sender:username,
            content:msg,
            senderId:clientId,
            id:msgId,
            timestamp:time
        }));
        
        // Mostrar localmente
        addMsg(username+": "+msg, "mine");
        
        // Guardar no histórico
        history.push({
            id:msgId,
            data:time,
            usuario:username,
            mensagem:msg
        });
        
        // Limpar input
        el.input.value='';
    }
}

// Listeners
el.btn.onclick=sendMessage;
el.input.addEventListener('keypress',function(e){
    if(e.key==='Enter') sendMessage();
});
</script>
</body>
</html>
"""

# HTML da página de limite excedido
LIMIT_EXCEEDED_HTML = """<!DOCTYPE html>
<html>
<head>
    <title>Limite de Conexões</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: Arial; max-width: 600px; margin: 0 auto; padding: 20px; text-align: center; }
        .container { margin-top: 50px; }
        h1 { color: #d32f2f; }
        p { font-size: 18px; line-height: 1.6; }
        .retry-btn { 
            display: inline-block; 
            margin-top: 20px; 
            padding: 10px 20px; 
            background-color: #2196f3; 
            color: white; 
            text-decoration: none; 
            border-radius: 4px; 
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Limite de Conexões Atingido</h1>
        <p>O servidor ESP32 atingiu o número máximo de conexões simultâneas permitidas (%d).</p>
        <p>Por favor, tente novamente mais tarde quando houver disponibilidade.</p>
        <a href="/" class="retry-btn">Tentar Novamente</a>
    </div>
</body>
</html>
""" % MAX_CONNECTIONS

class DNSServer:
    def __init__(self, ip):
        self.ip = ip
        self.socket = None
        self.running = True
    
    def start(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setblocking(False)
        self.socket.bind(('0.0.0.0', 53))
        print('DNS Server iniciado')
    
    async def process_request(self):
        try:
            data, addr = self.socket.recvfrom(1024)
            if data:
                # Extraindo ID da query DNS
                request_id = data[0:2]
                
                # Construindo resposta - redirecionando para o IP do ESP
                response = (
                    request_id +  # Transaction ID
                    b'\x81\x80'   # Flags (Standard response, No error)
                    + data[4:6]   # Questions
                    + b'\x00\x01'  # Answer RRs
                    + b'\x00\x00'  # Authority RRs
                    + b'\x00\x00'  # Additional RRs
                    + data[12:]    # Original domain question
                )
                
                # Adicionando answer - sempre apontando para o IP do ESP
                response += (
                    b'\xc0\x0c'                 # Pointer to domain name
                    + b'\x00\x01'               # Type A (Host address)
                    + b'\x00\x01'               # Class IN
                    + b'\x00\x00\x00\x3c'       # TTL (60 seconds)
                    + b'\x00\x04'               # Data length (4 bytes for IPv4)
                    + bytes(map(int, self.ip.split('.')))  # IP address in bytes
                )
                
                self.socket.sendto(response, addr)
        except Exception as e:
            if not isinstance(e, OSError) or e.args[0] != 11:  # EAGAIN/EWOULDBLOCK
                print(f"Erro DNS: {e}")

    async def run(self):
        self.start()
        while self.running:
            await self.process_request()
            await asyncio.sleep(0.01)

class WebServer:
    def __init__(self, port=80, websocket_server=None):
        self.port = port
        self.socket = None
        self.websocket_server = websocket_server
    
    def start(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(('0.0.0.0', self.port))
        self.socket.listen(5)
        self.socket.setblocking(False)
        print(f'Servidor HTTP iniciado na porta {self.port}')
    
    # Modificação para enviar HTML grande em partes
    async def handle_http_request(self, client, addr):
        try:
            client.setblocking(False)
            data = b''
            
            # Timeout para receber todos os dados
            start_time = time.time()
            while True:
                try:
                    chunk = client.recv(1024)
                    if not chunk:
                        break
                    data += chunk
                    if b'\r\n\r\n' in data:
                        break
                except OSError as e:
                    if e.args[0] == 11:  # EAGAIN/EWOULDBLOCK
                        if time.time() - start_time > 1:  # 1 segundo de timeout
                            break
                        await asyncio.sleep(0.01)
                    else:
                        break
            
            if not data:
                client.close()
                return
            
            # Analisar requisição
            request = data.decode()
            request_lines = request.split('\r\n')
            method, path, _ = request_lines[0].split(' ')
            
            # Verificar se atingiu o limite de conexões para o WebSocket
            if self.websocket_server and len(self.websocket_server.clients) >= MAX_CONNECTIONS:
                # Se estiver no limite, forneça a página de limite excedido
                client.send(b'HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n')
                client.send(LIMIT_EXCEEDED_HTML.encode())
            else:
                # Caso contrário, processe normalmente
                if 'generate_204' in path or 'connecttest.txt' in path or 'redirect' in path:
                    # Requisições específicas para detecção de captive portal
                    client.send(b'HTTP/1.1 302 Found\r\nLocation: http://' + AP_IP.encode() + b'\r\n\r\n')
                else:
                    # Página principal - enviando em partes
                    client.send(b'HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n')
                    
                    # Dividir o HTML em pedaços de 2048 bytes e enviar cada um
                    html_bytes = CHAT_HTML.encode()
                    chunk_size = 2048
                    
                    for i in range(0, len(html_bytes), chunk_size):
                        chunk = html_bytes[i:i + chunk_size]
                        client.send(chunk)
                        await asyncio.sleep(0.01)  # Pequena pausa para processamento
            
            client.close()
        
        except Exception as e:
            print(f"Erro HTTP: {e}")
            try:
                client.close()
            except:
                pass
    
    async def run(self):
        self.start()
        while True:
            try:
                client, addr = self.socket.accept()
                asyncio.create_task(self.handle_http_request(client, addr))
            except OSError as e:
                if e.args[0] != 11:  # EAGAIN/EWOULDBLOCK
                    print(f"Erro aceitando conexão: {e}")
                await asyncio.sleep(0.01)

class WebSocketServer:
    def __init__(self, port=81):
        self.port = port
        self.socket = None
        self.clients = []
    
    def start(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(('0.0.0.0', self.port))
        self.socket.listen(5)
        self.socket.setblocking(False)
        print(f'Servidor WebSocket iniciado na porta {self.port}')
    
    def parse_headers(self, data):
        headers = {}
        lines = data.split(b'\r\n')
        for line in lines:
            if b': ' in line:
                key, value = line.split(b': ', 1)
                headers[key.decode().lower()] = value.decode()
        return headers
    
    def generate_websocket_key(self, key):
        import ubinascii
        import uhashlib
        
        GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
        
        key = key + GUID
        key_hash = uhashlib.sha1(key.encode())
        key_hash_bytes = key_hash.digest()
        return ubinascii.b2a_base64(key_hash_bytes).decode().strip()
    
    def broadcast_user_count(self):
        """Enviar para todos os clientes o número atual de usuários conectados"""
        count_message = json.dumps({
            "type": "userCount",
            "count": len(self.clients)
        }).encode()
        
        for client in self.clients:
            self.send_message(client, count_message)
    
    async def handle_websocket(self, client, addr):
        try:
            # Verificar limite de conexões
            if len(self.clients) >= MAX_CONNECTIONS:
                print("Limite de conexões WebSocket atingido. Recusando nova conexão.")
                client.close()
                return
                
            client.setblocking(False)
            data = b''
            
            # Receber handshake
            while True:
                try:
                    chunk = client.recv(1024)
                    if not chunk:
                        client.close()
                        return
                    data += chunk
                    if b'\r\n\r\n' in data:
                        break
                except OSError as e:
                    if e.args[0] == 11:  # EAGAIN/EWOULDBLOCK
                        await asyncio.sleep(0.01)
                    else:
                        client.close()
                        return
            
            # Processar handshake
            headers = self.parse_headers(data)
            
            if 'sec-websocket-key' not in headers:
                client.close()
                return
            
            # Responder com handshake WebSocket
            key = headers['sec-websocket-key']
            accept_key = self.generate_websocket_key(key)
            
            response = (
                b'HTTP/1.1 101 Switching Protocols\r\n'
                b'Upgrade: websocket\r\n'
                b'Connection: Upgrade\r\n'
                b'Sec-WebSocket-Accept: ' + accept_key.encode() + b'\r\n\r\n'
            )
            
            client.send(response)
            
            # Adicionar cliente à lista
            self.clients.append(client)
            
            # Atualizar contador de usuários para todos
            self.broadcast_user_count()
            
            # Enviar mensagem de boas-vindas
            welcome_msg = '{"type":"message","sender":"Sistema","content":"Bem-vindo ao chat!"}'
            self.send_message(client, welcome_msg.encode())
            
            # Processar mensagens
            buffer = b''
            while True:
                try:
                    data = client.recv(1024)
                    if not data:
                        break
                    
                    buffer += data
                    message = self.decode_websocket_frame(buffer)
                    
                    if message:
                        buffer = b''
                        # Broadcast para todos os clientes
                        for c in self.clients:
                            if c != client:  # Não reenvie para o próprio remetente
                                self.send_message(c, message)
                
                except OSError as e:
                    if e.args[0] == 11:  # EAGAIN/EWOULDBLOCK
                        await asyncio.sleep(0.01)
                    else:
                        break
        
        except Exception as e:
            print(f"Erro WebSocket: {e}")
        
        finally:
            if client in self.clients:
                self.clients.remove(client)
                # Atualizar contador de usuários quando alguém sai
                self.broadcast_user_count()
                
            try:
                client.close()
            except:
                pass
    
    def decode_websocket_frame(self, data):
        if len(data) < 6:
            return None
        
        # Primeiros 2 bytes contêm informações de controle
        b1, b2 = data[0], data[1]
        
        # Verificar FIN e opcode
        fin = b1 & 0x80
        opcode = b1 & 0x0F
        
        if opcode == 8:  # Close frame
            return None
        
        # Verificar se é mascarado (deve ser para mensagens do cliente)
        mask = b2 & 0x80
        if not mask:
            return None
        
        # Tamanho da payload
        payload_len = b2 & 0x7F
        
        # Determinar onde começa a máscara e os dados
        mask_offset = 2
        if payload_len == 126:
            mask_offset = 4
        elif payload_len == 127:
            mask_offset = 10
        
        # Verificar se temos dados suficientes
        if len(data) < mask_offset + 4:
            return None
        
        # Obter a máscara
        mask_key = data[mask_offset:mask_offset+4]
        
        # Calcular onde começa a payload
        data_offset = mask_offset + 4
        
        # Verificar se temos toda a payload
        if payload_len == 126:
            payload_len = (data[2] << 8) | data[3]
        elif payload_len == 127:
            payload_len = 0
            for i in range(8):
                payload_len = (payload_len << 8) | data[2+i]
        
        if len(data) < data_offset + payload_len:
            return None
        
        # Desmascarar a payload
        payload = bytearray(payload_len)
        for i in range(payload_len):
            payload[i] = data[data_offset + i] ^ mask_key[i % 4]
        
        return payload
    
    def send_message(self, client, message):
        try:
            # Criar cabeçalho para frame WebSocket
            header = bytearray()
            
            # FIN bit + opcode text
            header.append(0x81)  
            
            msg_len = len(message)
            
            # Tamanho da payload
            if msg_len < 126:
                header.append(msg_len)
            elif msg_len < 65536:
                header.append(126)
                header.append((msg_len >> 8) & 0xFF)
                header.append(msg_len & 0xFF)
            else:
                header.append(127)
                for i in range(7, -1, -1):
                    header.append((msg_len >> (i * 8)) & 0xFF)
            
            # Enviar frame completo
            client.send(header + message)
            
        except Exception as e:
            print(f"Erro ao enviar mensagem: {e}")
            if client in self.clients:
                self.clients.remove(client)
                # Atualizar contador de usuários quando há erro de envio
                self.broadcast_user_count()
                try:
                    client.close()
                except:
                    pass
    
    async def run(self):
        self.start()
        while True:
            try:
                client, addr = self.socket.accept()
                # Verificação de limite movida para dentro do handler
                asyncio.create_task(self.handle_websocket(client, addr))
            except OSError as e:
                if e.args[0] != 11:  # EAGAIN/EWOULDBLOCK
                    print(f"Erro aceitando conexão: {e}")
                await asyncio.sleep(0.01)

async def setup_network():
    # Configurar ponto de acesso
    ap = network.WLAN(network.AP_IF)
    ap.active(True)
    ap.config(essid=AP_SSID, password=AP_PASSWORD)
    ap.config(authmode=3)  # WPA2
    
    # Configurar endereço IP estático
    ap.ifconfig((AP_IP, '255.255.255.0', AP_IP, AP_IP))
    
    print(f'Ponto de Acesso criado: {AP_SSID}')
    print(f'IP: {AP_IP}')
    print(f'Limite de conexões: {MAX_CONNECTIONS}')
    
    return ap

async def main():
    # Limpar memória
    gc.collect()
    
    # Configurar rede
    ap = await setup_network()
    
    # Iniciar servidores
    dns_server = DNSServer(AP_IP)
    websocket_server = WebSocketServer(81)
    web_server = WebServer(80, websocket_server)  # Passando referência do WebSocket server
    
    # Executar servidores em tarefas paralelas
    await asyncio.gather(
        dns_server.run(),
        web_server.run(),
        websocket_server.run()
    )

# Iniciar o programa
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"Erro principal: {e}")
        # Reiniciar em caso de erro grave
        import machine
        time.sleep(5)
        machine.reset()

