import network
import socket
import time
import gc
import uasyncio as asyncio
import json
import urandom
import os




# Configurações
AP_SSID = 'ESP32-CHAT'
AP_PASSWORD = '12345678'
AP_IP = '192.168.4.1'
MAX_CONNECTIONS = 5  # Limite máximo de conexões WebSocket simultâneas
FRAGMENT_SIZE = 5 * 1024  # 5KB para cada fragmento



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

async def split_base64_content(filename, output_dir, fragment_size=FRAGMENT_SIZE):
    """
    Lê um arquivo e divide em fragmentos menores para otimizar o uso de memória.
    
    Args:
        filename (str): Nome do arquivo a ser processado
        output_dir (str): Diretório onde os fragmentos serão salvos
        fragment_size (int): Tamanho de cada fragmento em bytes
    
    Returns:
        int: Número de fragmentos criados, ou 0 em caso de erro
    """
    try:
        # Criar diretório de saída se não existir
        try:
            os.stat(output_dir)
        except OSError:
            os.mkdir(output_dir)
        
        # Limpar o diretório de saída
        try:
            files = os.listdir(output_dir)
            for file in files:
                os.remove(f"{output_dir}/{file}")
                gc.collect()  # Liberar memória após cada remoção
        except OSError:
            pass
        
        # Abrir o arquivo e determinar seu tamanho
        file_size = os.stat(filename)[6]  # Índice 6 é o tamanho do arquivo
        
        # Calcular o número total de fragmentos
        num_fragments = (file_size + fragment_size - 1) // fragment_size
        
        print(f"Dividindo arquivo de {file_size} bytes em {num_fragments} fragmentos de {fragment_size} bytes")
        
        # Processar o arquivo em fragmentos
        with open(filename, 'rb') as input_file:
            for i in range(num_fragments):
                # Liberar memória antes de cada fragmento
                gc.collect()
                await asyncio.sleep(0.1)
                
                # Abrir o arquivo de fragmento
                fragment_path = f"{output_dir}/fragment_{i}"
                with open(fragment_path, 'wb') as out_file:
                    # Determinar quanto ler para este fragmento
                    bytes_to_read = min(fragment_size, file_size - (i * fragment_size))
                    
                    # Ler e escrever em pequenos blocos
                    chunk_size = 256  # Processar 256 bytes por vez
                    bytes_read = 0
                    
                    while bytes_read < bytes_to_read:
                        # Calcular tamanho do próximo chunk
                        current_chunk_size = min(chunk_size, bytes_to_read - bytes_read)
                        
                        # Ler e escrever o chunk
                        chunk = input_file.read(current_chunk_size)
                        out_file.write(chunk)
                        
                        # Atualizar contadores
                        bytes_read += len(chunk)
                        
                        # Liberar memória e permitir outras tarefas
                        await asyncio.sleep(0.02)
                
                # Mostrar progresso e liberar memória
                if i % 5 == 0:
                    print(f"Processado fragmento {i}/{num_fragments}")
                    gc.collect()
        
        # Criando arquivo index.txt com informações dos fragmentos
        if num_fragments > 0:
            with open(f'{output_dir}/index.txt', 'w') as f:
                f.write(f"fragments: {num_fragments}\n")
                f.write(f"filename: {filename}\n")
                f.write(f"filesize: {file_size}\n")
        
        print(f"Arquivo dividido em {num_fragments} fragmentos")
        return num_fragments
    
    except Exception as e:
        print(f"Erro ao processar arquivo {filename}: {e}")
        return 0

async def process_form_data(data, boundary):
    """
    Processa dados do formulário de forma eficiente em memória.
    
    Args:
        data (bytes): Dados brutos do formulário
        boundary (bytes): Boundary do formulário multipart
    
    Returns:
        dict: Dicionário com os campos do formulário
    """
    form_data = {}
    
    # Verificar se temos boundary
    if not boundary:
        return form_data
    
    # Dividir em partes principais
    parts = data.split(b'--' + boundary)
    
    # Processar cada parte
    for part in parts:
        # Liberar memória
        gc.collect()
        
        # Ignorar partes vazias ou boundary final
        if not part or part.strip() == b'--' or part.strip() == b'--\r\n':
            continue
        
        # Extrair nome do campo e valor
        if b'Content-Disposition: form-data;' in part:
            # Extrair nome do campo
            name_start = part.find(b'name="') + 6
            name_end = part.find(b'"', name_start)
            
            if name_start > 5 and name_end > name_start:
                field_name = part[name_start:name_end].decode()
                
                # Extrair conteúdo do campo
                content_start = part.find(b'\r\n\r\n') + 4
                if content_start > 3:
                    content_end = len(part)
                    if part.endswith(b'\r\n'):
                        content_end -= 2
                    
                    # Para campo de conteúdo, processar em pedaços menores
                    if field_name == 'content':
                        field_value = part[content_start:content_end].decode()
                    else:
                        # Para outros campos, decodificar normalmente
                        try:
                            field_value = part[content_start:content_end].decode()
                        except UnicodeDecodeError:
                            # Manter como bytes se não for decodificável
                            field_value = part[content_start:content_end]
                    
                    form_data[field_name] = field_value
    
    return form_data



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
        """
        Trata uma requisição HTTP.
        
        Args:
            client (socket): Socket do cliente
            addr (tuple): Endereço do cliente
        """
        try:
            # Configurar socket
            client.settimeout(5)
            client.setblocking(False)
            data = b''
            
            # Timeout para receber dados
            start_time = time.time()
            
            # Parâmetros para processamento de requisições
            headers_received = False
            
            while True:
                try:
                    # Verificar e liberar memória antes de receber dados
                    gc.collect()
                    
                    chunk = client.recv(512)  # Receber 512 bytes por vez
                    if not chunk:
                        break
                    
                    data += chunk
                    
                    # Verificar se já recebemos os cabeçalhos completos
                    if b'\r\n\r\n' in data and not headers_received:
                        headers_received = True
                        
                    # Verificar se estamos recebendo muito dados
                    if len(data) > 100000:  # 100KB de limite
                        # Enviar resposta de erro
                        error_response = "<html><body><h1>Erro</h1><p>Requisição muito grande</p></body></html>"
                        client.send(b'HTTP/1.1 413 Request Entity Too Large\r\nContent-Type: text/html\r\n\r\n')
                        client.send(error_response.encode())
                        break
                    
                    # Parar se já temos os cabeçalhos
                    if headers_received:
                        break
                        
                except OSError as e:
                    if e.args[0] == 11:  # EAGAIN/EWOULDBLOCK
                        if time.time() - start_time > 15:  # 15 segundos de timeout
                            break
                        await asyncio.sleep(0.01)
                    else:
                        break
                
                # Liberar memória periodicamente
                if len(data) % 5000 == 0:
                    gc.collect()
            
            # Verificar se recebemos dados
            if not data:
                client.close()
                return
            
            # Liberar memória antes de processar
            gc.collect()
            
            # Analisar requisição
            request_line = data.split(b'\r\n')[0].decode()
            method, path, _ = request_line.split(' ')
            
            # Verificar limite de conexões para WebSocket
            if hasattr(self, 'websocket_server') and self.websocket_server and len(self.websocket_server.clients) >= MAX_CONNECTIONS:
                # Enviar página de limite excedido
                client.send(b'HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n')
                client.send(LIMIT_EXCEEDED_HTML.encode())
            else:
                # Processar requisições GET
                if method == 'GET':
                    file_path = None
                    
                    # Determinar o arquivo a ser servido
                    if path == '/' or path == '/index.html':
                        file_path = 'loader.html'
                    elif path == '/uploader':
                        file_path = 'uploader.html'
                    elif path.startswith('/fragments/'):
                        # Servir fragmentos HTML
                        file_name = path.split('/')[-1]
                        file_path = 'fragments/' + file_name
                    elif path == '/generate_204' or path == '/connecttest.txt' or path == '/redirect':
                        # Requisições para detecção de captive portal
                        client.send(b'HTTP/1.1 302 Found\r\nLocation: http://' + AP_IP.encode() + b'\r\n\r\n')
                        client.close()
                        return
                    
                    if file_path:
                        try:
                            with open(file_path, 'r') as file:
                                # Determinar o tipo de conteúdo
                                content_type = 'text/html'
                                if file_path.endswith('.css'):
                                    content_type = 'text/css'
                                elif file_path.endswith('.js'):
                                    content_type = 'application/javascript'
                                
                                # Enviar cabeçalho HTTP
                                client.send(f'HTTP/1.1 200 OK\r\nContent-Type: {content_type}\r\n\r\n'.encode())
                                
                                # Ler e enviar o arquivo em chunks pequenos
                                buffer_size = 512  # Reduzido para 512 bytes
                                while True:
                                    chunk = file.read(buffer_size)
                                    if not chunk:
                                        break
                                    client.send(chunk.encode())
                                    await asyncio.sleep(0.01)
                                    gc.collect()  # Liberar memória após cada envio
                        except OSError as e:
                            print(f"Erro ao ler arquivo {file_path}: {e}")
                            error_msg = f'<html><body><h1>Erro 404</h1><p>Arquivo não encontrado: {file_path}</p></body></html>'
                            client.send(b'HTTP/1.1 404 Not Found\r\nContent-Type: text/html\r\n\r\n')
                            client.send(error_msg.encode())
                    else:
                        # Arquivo não encontrado
                        error_msg = f'<html><body><h1>Erro 404</h1><p>Página não encontrada: {path}</p></body></html>'
                        client.send(b'HTTP/1.1 404 Not Found\r\nContent-Type: text/html\r\n\r\n')
                        client.send(error_msg.encode())
                
                # Processar outros métodos POST (sem upload)
                elif method == 'POST':
                    # Resposta genérica para POST quando não é upload
                    response = "<html><body><h1>Solicitação POST recebida</h1><p>Esta solicitação foi processada.</p></body></html>"
                    client.send(b'HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n')
                    client.send(response.encode())
            
            client.close()
        
        except OSError as e:
            print(f"Erro de conexão: {e}")
        except Exception as e:
            print(f"Erro geral: {e}")
            print(f"Memória livre: {gc.mem_free() if hasattr(gc, 'mem_free') else 'N/A'}")
        finally:
            try:
                client.close()
            except:
                pass
            # Liberar memória ao finalizar
            gc.collect()
        
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
    await split_base64_content('chat.html', 'fragments', FRAGMENT_SIZE)
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


