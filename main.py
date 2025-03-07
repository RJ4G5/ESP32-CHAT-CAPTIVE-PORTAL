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
            client.settimeout(2)  # Timeout de 2 segundos
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
                    # Enviar cabeçalho HTTP
                    client.send(b'HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n')
                    
                    # Ler e enviar o arquivo HTML em chunks
                    try:
                        with open('chat.html', 'r') as file:
                            while True:
                                chunk = file.read(2048)
                                if not chunk:
                                    break
                                client.send(chunk.encode())
                                await asyncio.sleep(0.01)  # Pequena pausa para processamento
                    except OSError as e:
                        print(f"Erro ao ler arquivo HTML: {e}")
                        # Se não conseguir ler o arquivo, envia uma mensagem de erro
                        client.send(b'Erro ao carregar o arquivo HTML')
            
            client.close()
        
        except OSError as e:
            if e.errno == 104:  # ECONNRESET
                print(f"Conexão redefinida de {addr}")
            elif e.errno == 11:  # EAGAIN
                print("Recurso temporariamente indisponível")
            else:
                print(f"Erro de conexão: {e}")
        finally:
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


