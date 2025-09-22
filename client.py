# client.py
import socket
import json
import argparse
import os
import sys
import textwrap
import datetime

# Try to import readline for Unix systems, otherwise use a fallback for Windows
try:
    import readline  # For command history on Unix
except ImportError:
    # On Windows, readline is not available
    pass

class RemoteCommandClient:
    def __init__(self,host='127.0.0.1', port=9999, token=None):
        self.host = host
        self.port = port
        self.token = token or os.environ.get('RCE_TOKEN')
        self.socket = None
        self.connected = False
        
        # Define the available commands and their descriptions
        self.commands = {
            'help': 'Show this help message',
            'exit': 'Exit the shell and disconnect',
            'sysinfo': 'Get system information from the remote machine',
            'listdir': 'List contents of a directory (args: path)',
            'diskspace': 'Get disk space information (args: path)',
            'processlist': 'List running processes (args: limit)',
            'meminfo': 'Get memory usage information',
            'netinfo': 'Get network interfaces information',
            'fileinfo': 'Get information about a specific file (args: path)',
            'uptime': 'Get system uptime',
            'hostname': 'Get the system hostname',
            'echo': 'Echo a message back (args: message)',
            'ping': 'Ping a remote host (args: host, count)',
            'findfile': 'Find files matching a pattern (args: pattern, path)'
        }
        
    def connect(self):
        """Connect to the remote command server"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            self.connected = True
            print(f"[+] Connected to {self.host}:{self.port}")
            return True
        except Exception as e:
            print(f"[-] Failed to connect: {e}")
            return False
            
    def disconnect(self):
        """Disconnect from the server"""
        if self.connected and self.socket:
            try:
                self.send_command('exit')
                self.socket.close()
            except:
                pass
            self.connected = False
            print("[+] Disconnected from server")
            
    def send_command(self, command, args=None):
        """Send a command to the server and return the response"""
        if not self.connected:
            print("[-] Not connected to any server")
            return None
            
        try:
            # Prepare command data
            command_data = {'command': command}
            if args:
                command_data['args'] = args
            if self.token:
                command_data['token'] = self.token
                
            serialized_data = json.dumps(command_data).encode('utf-8')
            
            # Send command
            self.socket.sendall(serialized_data)
            
            # Receive response
            response_data = self.socket.recv(16384)
            if not response_data:
                print("[-] Connection closed by server")
                self.connected = False
                return None
                
            # Parse response
            response = json.loads(response_data.decode('utf-8'))
            return response
            
        except Exception as e:
            print(f"[-] Error sending command: {e}")
            self.connected = False
            return None
            
    def start_shell(self):
        """Start an interactive shell with the server"""
        if not self.connected:
            print("[-] Not connected to any server")
            return
            
        print("[+] Starting remote shell. Type 'help' for available commands, 'exit' to disconnect.")
        
        try:
            while self.connected:
                command_line = input(f"{self.host}> ").strip()
                
                if not command_line:
                    continue
                    
                # Parse command and arguments
                parts = command_line.split(' ', 1)
                command = parts[0].lower()
                args_str = parts[1] if len(parts) > 1 else ''
                
                if command == 'exit':
                    self.disconnect()
                    break
                    
                if command == 'help':
                    self.show_help()
                    continue
                    
                # Parse command-specific arguments
                args = {}
                if command == 'listdir' or command == 'diskspace' or command == 'fileinfo':
                    if args_str:
                        args['path'] = args_str
                elif command == 'processlist':
                    if args_str and args_str.isdigit():
                        args['limit'] = int(args_str)
                elif command == 'echo':
                    args['message'] = args_str
                elif command == 'ping':
                    ping_args = args_str.split(' ')
                    if ping_args:
                        args['host'] = ping_args[0]
                        if len(ping_args) > 1 and ping_args[1].isdigit():
                            args['count'] = int(ping_args[1])
                elif command == 'findfile':
                    find_args = args_str.split(' ', 1)
                    if find_args:
                        args['pattern'] = find_args[0]
                        if len(find_args) > 1:
                            args['path'] = find_args[1]
                
                # Send command to server
                response = self.send_command(command, args)
                if response:
                    self.display_response(command, response, args)
                    
        except KeyboardInterrupt:
            print("\n[!] Shell terminated by user")
        finally:
            self.disconnect()
            
    def show_help(self):
        """Show available commands"""
        print("\nAvailable commands:")
        for cmd, desc in self.commands.items():
            print(f"  {cmd.ljust(12)} - {desc}")
        print()
        
    def display_response(self, command, response, args=None):
        """Display the response from the server"""
        if response.get('status') == 'error':
            print(f"[-] Error: {response.get('error', 'Unknown error')}")
            return
            
        result = response.get('result')
        
        if command == 'sysinfo':
            print("\n=== System Information ===")
            for key, value in result.items():
                print(f"{key.capitalize()}: {value}")
            print("========================\n")
            
        elif command == 'listdir':
            path = args.get('path', '.') if args else '.'
            print(f"\n=== Directory Listing: {path} ===")
            print(f"{'Type':<8} {'Size':<10} {'Modified':<22} {'Name'}")
            print("-" * 70)
            
            for item in result:
                item_type = "DIR" if item['is_dir'] else "FILE"
                size = item['size'] if not item['is_dir'] else "-"
                modified = datetime.datetime.fromtimestamp(item['modified']).strftime('%Y-%m-%d %H:%M:%S')
                print(f"{item_type:<8} {size:<10} {modified:<22} {item['name']}")
            print("=" * 70)
            print(f"Total: {len(result)} items\n")
            
        elif command == 'diskspace':
            print("\n=== Disk Space Information ===")
            print(f"Total: {self.format_size(result['total'])}")
            print(f"Used:  {self.format_size(result['used'])} ({result['percent_used']:.1f}%)")
            print(f"Free:  {self.format_size(result['free'])}")
            print("============================\n")
            
        elif command == 'processlist':
            print("\n=== Process List ===")
            print(f"{'PID':<7} {'User':<15} {'Memory %':<10} {'CPU %':<8} {'Created':<22} {'Name'}")
            print("-" * 80)
            
            for proc in result:
                created = datetime.datetime.fromtimestamp(proc.get('create_time', 0)).strftime('%Y-%m-%d %H:%M:%S') if proc.get('create_time') else "-"
                print(f"{proc.get('pid', '-'):<7} {proc.get('username', '-'):<15} {proc.get('memory_percent', 0):<10.1f} {proc.get('cpu_percent', 0):<8.1f} {created:<22} {proc.get('name', '-')}")
            print("=" * 80 + "\n")
            
        elif command == 'meminfo':
            print("\n=== Memory Information ===")
            print(f"Physical Memory:")
            print(f"  Total:     {self.format_size(result['total'])}")
            print(f"  Available: {self.format_size(result['available'])}")
            print(f"  Used:      {self.format_size(result['used'])} ({result['percent']}%)")
            print(f"Swap Memory:")
            print(f"  Total:     {self.format_size(result['swap_total'])}")
            print(f"  Used:      {self.format_size(result['swap_used'])} ({result['swap_percent']}%)")
            print("=========================\n")
            
        elif command == 'netinfo':
            print("\n=== Network Interfaces ===")
            for interface, info in result.items():
                print(f"Interface: {interface}")
                print(f"  Status: {'UP' if info.get('is_up') else 'DOWN'}")
                
                if 'bytes_sent' in info:
                    print(f"  Bytes Sent: {self.format_size(info['bytes_sent'])}")
                    print(f"  Bytes Received: {self.format_size(info['bytes_recv'])}")
                    
                print("  Addresses:")
                for addr in info.get('addresses', []):
                    print(f"    {addr.get('family')} - {addr.get('address')}")
                    if addr.get('netmask'):
                        print(f"      Netmask: {addr.get('netmask')}")
                    if addr.get('broadcast'):
                        print(f"      Broadcast: {addr.get('broadcast')}")
                print()
            print("=========================\n")
            
        elif command == 'fileinfo':
            print("\n=== File Information ===")
            print(f"Name: {result.get('name')}")
            print(f"Path: {result.get('path')}")
            print(f"Type: {'Directory' if result.get('is_dir') else 'File'}")
            print(f"Size: {self.format_size(result.get('size'))}")
            print(f"Created: {datetime.datetime.fromtimestamp(result.get('created')).strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"Modified: {datetime.datetime.fromtimestamp(result.get('modified')).strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"Accessed: {datetime.datetime.fromtimestamp(result.get('accessed')).strftime('%Y-%m-%d %H:%M:%S')}")
            print("=========================\n")
            
        elif command == 'uptime':
            uptime_seconds = result.get('uptime_seconds', 0)
            days, remainder = divmod(uptime_seconds, 86400)
            hours, remainder = divmod(remainder, 3600)
            minutes, seconds = divmod(remainder, 60)
            
            boot_time = datetime.datetime.fromtimestamp(result.get('boot_time', 0)).strftime('%Y-%m-%d %H:%M:%S')
            
            print("\n=== System Uptime ===")
            print(f"Boot Time: {boot_time}")
            print(f"Uptime: {int(days)} days, {int(hours)} hours, {int(minutes)} minutes, {int(seconds)} seconds")
            print("=====================\n")
            
        elif command == 'hostname':
            print("\n=== Hostname Information ===")
            print(f"Hostname: {result.get('hostname')}")
            print(f"FQDN: {result.get('fqdn')}")
            print("===========================\n")
            
        elif command == 'echo':
            print(f"\nServer echo: {result}\n")
            
        elif command == 'ping':
            print("\n=== Ping Results ===")
            print(result)
            print("===================\n")
            
        elif command == 'findfile':
            print(f"\n=== Find Results ===")
            print(f"Found {response.get('count', 0)} matches:")
            for item in result:
                item_type = "[DIR]" if item.get('is_dir') else "[FILE]"
                print(f"{item_type} {item.get('path')}")
            print("===================\n")
            
        else:
            print(f"\nResult: {result}\n")
            
    def format_size(self, size):
        """Format byte size to human-readable form"""
        if size is None:
            return "-"
            
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024 or unit == 'TB':
                return f"{size:.2f} {unit}"
            size /= 1024

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Remote Command Execution Client")
    parser.add_argument("host", nargs='?', default='127.0.0.1', help="Target host to connect to")
    parser.add_argument("--port", type=int, default=9999, help="Target port to connect to")
    parser.add_argument("--token", default=os.environ.get('RCE_TOKEN'), help="Auth token (or set RCE_TOKEN env var)")
    args = parser.parse_args()
    
    client = RemoteCommandClient(args.host, args.port, token=args.token)
    
    if client.connect():
        try:
            client.start_shell()
        except Exception as e:
            print(f"[-] Error in shell: {e}")
        finally:
            client.disconnect()