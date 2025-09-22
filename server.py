# server.py
import socket
import subprocess
import threading
import os
import platform
import json
import argparse
import shutil
import psutil
import logging
import time

class RemoteCommandServer:
    def __init__(self, host='127.0.0.1', port=9999, auth_token: str | None = None):
        self.host = host
        self.port = port
        self.server_socket = None
        self.running = False
        self.clients = []
        self.auth_token = auth_token or os.environ.get('RCE_TOKEN')
        
        # Define the allowed commands and their handlers
        self.commands = {
            'sysinfo': self.get_system_info,
            'listdir': self.list_directory,
            'diskspace': self.get_disk_space,
            'processlist': self.get_process_list,
            'meminfo': self.get_memory_info,
            'netinfo': self.get_network_info,
            'fileinfo': self.get_file_info,
            'uptime': self.get_uptime,
            'hostname': self.get_hostname,
            'echo': self.echo_message,
            'ping': self.ping_host,
            'findfile': self.find_file
        }
        
    def start(self):
        """Start the server and listen for connections"""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            self.running = True
            self._setup_logging()
            logging.info(json.dumps({
                'event': 'server_started',
                'host': self.host,
                'port': self.port,
                'system': platform.system(),
                'version': platform.version(),
                'cwd': os.getcwd(),
                'commands': list(self.commands.keys()),
                'auth_enabled': bool(self.auth_token)
            }))
            
            # Start accepting client connections
            self.accept_connections()
            
        except Exception as e:
            print(f"[-] Error starting server: {e}")
            self.stop()
            
    def accept_connections(self):
        """Accept incoming client connections"""
        while self.running:
            try:
                client_socket, client_address = self.server_socket.accept()
                client_handler = threading.Thread(
                    target=self.handle_client,
                    args=(client_socket, client_address)
                )
                client_handler.daemon = True
                client_handler.start()
                self.clients.append((client_socket, client_address, client_handler))
                logging.info(json.dumps({'event': 'client_connected', 'ip': client_address[0], 'port': client_address[1]}))
            except Exception as e:
                if self.running:
                    logging.error(json.dumps({'event': 'accept_error', 'error': str(e)}))
                break
    
    def handle_client(self, client_socket, client_address):
        """Handle communication with a connected client"""
        try:
            while self.running:
                # Receive command from client
                data = client_socket.recv(4096)
                if not data:
                    break
                
                # Parse the received command
                try:
                    command_data = json.loads(data.decode('utf-8'))
                    command = command_data.get('command', '')
                    args = command_data.get('args', {})
                    token = command_data.get('token')
                    
                    if command == 'exit':
                        break
                    
                    # Authentication check if enabled
                    if self.auth_token is not None:
                        if token != self.auth_token:
                            response = {'status': 'error', 'error': 'Unauthorized'}
                            client_socket.sendall(json.dumps(response).encode('utf-8'))
                            continue
                    
                    # Check if command is in predefined list
                    if command in self.commands:
                        handler = self.commands[command]
                        response = handler(args)
                    else:
                        response = {'status': 'error', 'error': f"Unknown command: {command}"}
                    
                    # Send response back to client
                    client_socket.sendall(json.dumps(response).encode('utf-8'))
                    
                except json.JSONDecodeError:
                    response = {'status': 'error', 'error': 'Invalid command format'}
                    client_socket.sendall(json.dumps(response).encode('utf-8'))
                    
        except Exception as e:
            logging.error(json.dumps({'event': 'handle_client_error', 'ip': client_address[0], 'port': client_address[1], 'error': str(e)}))
        finally:
            client_socket.close()
            logging.info(json.dumps({'event': 'client_disconnected', 'ip': client_address[0], 'port': client_address[1]}))
            self.clients = [c for c in self.clients if c[0] != client_socket]
    
    # Predefined command handlers
    def get_system_info(self, args):
        """Get system information"""
        result = {
            'system': platform.system(),
            'node': platform.node(),
            'release': platform.release(),
            'version': platform.version(),
            'machine': platform.machine(),
            'processor': platform.processor(),
            'cpu_count': os.cpu_count(),
            'cwd': os.getcwd()
        }
        return {'status': 'success', 'result': result}
    
    def list_directory(self, args):
        """List contents of a directory"""
        try:
            path = args.get('path', '.')
            files = os.listdir(path)
            
            file_info = []
            for file in files:
                full_path = os.path.join(path, file)
                stats = os.stat(full_path)
                info = {
                    'name': file,
                    'size': stats.st_size,
                    'modified': stats.st_mtime,
                    'is_dir': os.path.isdir(full_path)
                }
                file_info.append(info)
                
            return {'status': 'success', 'result': file_info}
        except Exception as e:
            return {'status': 'error', 'error': str(e)}
    
    def get_disk_space(self, args):
        """Get disk space information"""
        try:
            path = args.get('path', '.')
            usage = shutil.disk_usage(path)
            result = {
                'total': usage.total,
                'used': usage.used,
                'free': usage.free,
                'percent_used': (usage.used / usage.total) * 100
            }
            return {'status': 'success', 'result': result}
        except Exception as e:
            return {'status': 'error', 'error': str(e)}
    
    def get_process_list(self, args):
        """Get list of running processes"""
        try:
            limit = args.get('limit', 10)
            processes = []
            
            for proc in psutil.process_iter(['pid', 'name', 'username', 'memory_percent', 'cpu_percent', 'create_time']):
                try:
                    pinfo = proc.info
                    processes.append(pinfo)
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
            
            # Sort by memory usage and limit results
            processes = sorted(processes, key=lambda p: p.get('memory_percent', 0), reverse=True)[:limit]
            
            return {'status': 'success', 'result': processes}
        except Exception as e:
            return {'status': 'error', 'error': str(e)}
    
    def get_memory_info(self, args):
        """Get memory usage information"""
        try:
            vm = psutil.virtual_memory()
            sm = psutil.swap_memory()
            
            result = {
                'total': vm.total,
                'available': vm.available,
                'used': vm.used,
                'percent': vm.percent,
                'swap_total': sm.total,
                'swap_used': sm.used,
                'swap_percent': sm.percent
            }
            
            return {'status': 'success', 'result': result}
        except Exception as e:
            return {'status': 'error', 'error': str(e)}
    
    def get_network_info(self, args):
        """Get network interfaces information"""
        try:
            interfaces = psutil.net_if_addrs()
            stats = psutil.net_if_stats()
            io_counters = psutil.net_io_counters(pernic=True)
            
            result = {}
            for interface, addresses in interfaces.items():
                addrs = []
                for addr in addresses:
                    addr_info = {
                        'family': str(addr.family),
                        'address': addr.address,
                        'netmask': addr.netmask,
                        'broadcast': addr.broadcast
                    }
                    addrs.append(addr_info)
                
                interface_info = {
                    'addresses': addrs,
                    'is_up': stats.get(interface, None).isup if interface in stats else None
                }
                
                if interface in io_counters:
                    interface_info['bytes_sent'] = io_counters[interface].bytes_sent
                    interface_info['bytes_recv'] = io_counters[interface].bytes_recv
                
                result[interface] = interface_info
            
            return {'status': 'success', 'result': result}
        except Exception as e:
            return {'status': 'error', 'error': str(e)}
    
    def get_file_info(self, args):
        """Get information about a specific file"""
        try:
            path = args.get('path')
            if not path:
                return {'status': 'error', 'error': 'No path specified'}
                
            if not os.path.exists(path):
                return {'status': 'error', 'error': 'File not found'}
                
            stats = os.stat(path)
            
            result = {
                'name': os.path.basename(path),
                'path': os.path.abspath(path),
                'size': stats.st_size,
                'created': stats.st_ctime,
                'modified': stats.st_mtime,
                'accessed': stats.st_atime,
                'is_dir': os.path.isdir(path),
                'is_file': os.path.isfile(path),
                'is_symlink': os.path.islink(path)
            }
            
            return {'status': 'success', 'result': result}
        except Exception as e:
            return {'status': 'error', 'error': str(e)}
    
    def get_uptime(self, args):
        """Get system uptime"""
        try:
            uptime_seconds = psutil.boot_time()
            result = {
                'boot_time': uptime_seconds,
                'uptime_seconds': time.time() - uptime_seconds
            }
            return {'status': 'success', 'result': result}
        except Exception as e:
            return {'status': 'error', 'error': str(e)}
    
    def get_hostname(self, args):
        """Get the system hostname"""
        try:
            result = {
                'hostname': socket.gethostname(),
                'fqdn': socket.getfqdn()
            }
            return {'status': 'success', 'result': result}
        except Exception as e:
            return {'status': 'error', 'error': str(e)}
    
    def echo_message(self, args):
        """Echo a message back to the client"""
        message = args.get('message', '')
        return {'status': 'success', 'result': message}
    
    def ping_host(self, args):
        """Ping a remote host"""
        try:
            host = args.get('host')
            if not host:
                return {'status': 'error', 'error': 'No host specified'}
                
            count = args.get('count', 4)
            # Build argument list and use shell=False
            if platform.system().lower() == 'windows':
                cmd = ['ping', '-n', str(count), host]
            else:
                cmd = ['ping', '-c', str(count), host]
            result = subprocess.run(cmd, capture_output=True, text=True, shell=False)
            stdout, stderr = result.stdout, result.stderr
            
            return {
                'status': 'success' if result.returncode == 0 else 'error',
                'result': stdout,
                'error': stderr
            }
        except Exception as e:
            return {'status': 'error', 'error': str(e)}
    
    def find_file(self, args):
        """Find files matching a pattern"""
        try:
            pattern = args.get('pattern')
            path = args.get('path', '.')
            
            if not pattern:
                return {'status': 'error', 'error': 'No pattern specified'}
                
            matches = []
            for root, dirs, files in os.walk(path):
                for name in files + dirs:
                    if pattern.lower() in name.lower():
                        full_path = os.path.join(root, name)
                        matches.append({
                            'path': full_path,
                            'is_dir': os.path.isdir(full_path)
                        })
                        
                        # Limit results to avoid overwhelming response
                        if len(matches) >= 100:
                            break
                
                if len(matches) >= 100:
                    break
            
            return {'status': 'success', 'result': matches, 'count': len(matches)}
        except Exception as e:
            return {'status': 'error', 'error': str(e)}
    
    def stop(self):
        """Stop the server and close all connections"""
        self.running = False
        
        # Close client connections
        for client_socket, _, _ in self.clients:
            try:
                client_socket.close()
            except:
                pass
        
        # Close server socket
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
        logging.info(json.dumps({'event': 'server_stopped'}))

    def _setup_logging(self):
        # Configure structured logging (JSON per line)
        logging.basicConfig(level=logging.INFO, format='%(message)s')

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Remote Command Execution Server with Predefined Commands")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind the server to")
    parser.add_argument("--port", type=int, default=9999, help="Port to bind the server to")
    parser.add_argument("--token", default=os.environ.get('RCE_TOKEN'), help="Auth token (or set RCE_TOKEN env var)")
    args = parser.parse_args()

    # Check for psutil package
    try:
        import psutil  # noqa: F401 (already imported at top, kept for safety if refactored)
    except ImportError:
        print("[-] Warning: psutil package not found. Some commands will not work.")
        print("[-] Install it with: pip install psutil")

    server = RemoteCommandServer(args.host, args.port, auth_token=args.token)

    try:
        server.start()
    except KeyboardInterrupt:
        logging.info(json.dumps({'event': 'keyboard_interrupt'}))
    finally:
        server.stop()