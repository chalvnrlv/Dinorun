import socket
import time
import sys
import logging
from concurrent.futures import ThreadPoolExecutor
from dinorun_http import HttpServer
import threading

# Konfigurasi logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Membuat instance HttpServer secara global
httpserver = HttpServer()
httpserver.start_time = time.time()
# Inisialisasi request_count jika belum ada di dalam class
if not hasattr(httpserver, 'request_count'):
    httpserver.request_count = 0

def ProcessTheClient(connection, address):
    """Menangani koneksi klien di dalam thread pool"""
    client_info = f"{address[0]}:{address[1]}"
    logger.info(f"New connection from {client_info}")

    try:
        connection.settimeout(5.0)  # Timeout 5 detik untuk koneksi yang tidak aktif
        rcv = ""

        while True:
            try:
                data = connection.recv(1024)
                if data:
                    d = data.decode('utf-8', errors='ignore')
                    rcv += d

                    # Memeriksa akhir dari permintaan (diakhiri dengan newline)
                    if rcv.endswith('\r\n') or rcv.endswith('\n'):
                        request = rcv.strip()
                        logger.debug(f"Request from {client_info}: {request}")

                        # Menambah counter permintaan
                        httpserver.request_count += 1

                        # Memproses permintaan
                        hasil = httpserver.proses(request)

                        # Mengirim respons, sudah ditambahkan terminator untuk klien
                        if isinstance(hasil, bytes):
                            response = hasil + b"\r\n\r\n"
                        else:
                            response = str(hasil).encode() + b"\r\n\r\n"

                        connection.sendall(response)
                        logger.debug(f"Response sent to {client_info}")
                        
                        # Keluar dari loop setelah satu siklus request-response
                        break
                else:
                    # Tidak ada data lagi, klien menutup koneksi
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

    except Exception as e:
        logger.error(f"Unexpected error with client {client_info}: {e}")

    finally:
        try:
            connection.close()
            logger.debug(f"Connection closed for {client_info}")
        except:
            pass

def print_stats():
    """Mencetak statistik server secara berkala"""
    while True:
        time.sleep(30)
        try:
            stats = httpserver.get_stats()
            # Memastikan semua key ada sebelum dicetak
            uptime = stats.get('uptime', 0)
            active_players = stats.get('active_players', 0)
            total_requests = stats.get('total_requests', httpserver.request_count)
            logger.info(f"Server Stats - Active Players: {active_players}, "
                        f"Total Requests: {total_requests}, "
                        f"Uptime: {uptime:.1f}s")
        except Exception as e:
            logger.error(f"Error printing stats: {e}")


def Server():
    """Fungsi utama server menggunakan ThreadPoolExecutor"""
    HOST = '0.0.0.0'
    PORT = 55555
    MAX_WORKERS = 50

    logger.info(f"Starting Dino Game Server on {HOST}:{PORT}")
    logger.info(f"Max concurrent connections: {MAX_WORKERS}")

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        server_socket.bind((HOST, PORT))
        server_socket.listen(10)
        logger.info(f"Server listening on {HOST}:{PORT}")

        # Jalankan thread untuk statistik
        stats_thread = threading.Thread(target=print_stats, daemon=True)
        stats_thread.start()

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            while True:
                try:
                    connection, client_address = server_socket.accept()
                    executor.submit(ProcessTheClient, connection, client_address)
                except KeyboardInterrupt:
                    logger.info("Server shutdown requested")
                    break
                except Exception as e:
                    logger.error(f"Error accepting connection: {e}")

    except Exception as e:
        logger.error(f"Server error: {e}")

    finally:
        try:
            server_socket.close()
            logger.info("Server socket closed")
        except:
            pass

def main():
    """Main entry point"""
    try:
        Server()
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Fatal server error: {e}")
    finally:
        logger.info("Server shutdown complete")

if __name__ == "__main__":
    main()