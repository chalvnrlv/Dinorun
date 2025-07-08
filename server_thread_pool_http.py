import socket
import time
import sys
import logging
from concurrent.futures import ThreadPoolExecutor
from dinorun_http import HttpServer  # Mengimpor kelas gabungan yang baru
import threading

# Konfigurasi logging dari server dinorun
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Instance global dari HttpServer
httpserver = HttpServer()

def ProcessTheClient(connection, address):
    """Menangani koneksi dari satu klien."""
    rcv = ""
    client_info = f"{address[0]}:{address[1]}"
    logger.info(f"New connection from {client_info}")
    
    try:
        connection.settimeout(10.0) # Timeout untuk koneksi
        
        # Loop untuk menerima data hingga command lengkap
        while True:
            try:
                data = connection.recv(1024)
                if data:
                    d = data.decode('utf-8', errors='ignore')
                    rcv += d
                    
                    # --- THIS IS THE CORRECTED LINE ---
                    # Command game diakhiri dengan '\n', request HTTP dengan '\r\n'
                    if rcv.endswith('\n') or '\r\n\r\n' in rcv:
                        request = rcv.strip()
                        logger.debug(f"Request from {client_info}: {request}")
                        
                        # Proses request menggunakan instance httpserver
                        hasil = httpserver.proses(request)
                        
                        # Kirim balasan
                        if isinstance(hasil, bytes):
                            # Jika balasan BUKAN response HTTP, tambahkan terminator
                            if not hasil.startswith(b"HTTP/"):
                                hasil += b"\r\n\r\n"
                        else:
                            # Fallback jika hasil bukan bytes
                            hasil = str(hasil).encode() + b"\r\n\r\n"

                        connection.sendall(hasil)
                        logger.debug(f"Response sent to {client_info}")
                        
                        # Keluar dari loop setelah satu siklus request-response
                        # Klien dinorun membuka koneksi baru untuk setiap command
                        break 
                else:
                    # Klien menutup koneksi
                    break
            except socket.timeout:
                logger.warning(f"Timeout for client {client_info}")
                break
            except ConnectionResetError:
                logger.warning(f"Connection reset by client {client_info}")
                break
            except Exception as e:
                logger.error(f"Error handling client {client_info}: {e}")
                break
    finally:
        connection.close()
        logger.debug(f"Connection closed for {client_info}")

def Server():
    """Fungsi utama server."""
    HOST = '0.0.0.0'
    PORT = 55555      # Port dari game dinorun
    MAX_WORKERS = 50  # Jumlah worker dari game dinorun

    my_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    my_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        my_socket.bind((HOST, PORT))
        my_socket.listen(10)
        logger.info(f"DinoRun Game Server listening on {HOST}:{PORT}")

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            while True:
                try:
                    connection, client_address = my_socket.accept()
                    executor.submit(ProcessTheClient, connection, client_address)
                except KeyboardInterrupt:
                    logger.info("Server shutdown requested")
                    break
                except Exception as e:
                    logger.error(f"Error accepting connection: {e}")
    except Exception as e:
        logger.error(f"Server failed to start: {e}")
    finally:
        my_socket.close()
        logger.info("Server socket closed")

if __name__ == "__main__":
    try:
        Server()
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    finally:
        logger.info("Server shutdown complete")