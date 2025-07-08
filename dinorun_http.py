import json
import time
import logging
import os
import sys
from datetime import datetime
from glob import glob

class HttpServer:
    def __init__(self):
        self.players = {}
        self.game_state = {
            'game_started': False,
            'winner': None,
            'game_over_time': None
        }
        self.start_time = time.time()
        self.request_count = 0
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)

        self.sessions = {}
        self.types = {}
        self.types['.pdf'] = 'application/pdf'
        self.types['.jpg'] = 'image/jpeg'
        self.types['.txt'] = 'text/plain'
        self.types['.html'] = 'text/html'


    def response(self, kode=404, message='Not Found', messagebody=bytes(), headers={}):
        tanggal = datetime.now().strftime('%c')
        resp = [
            f"HTTP/1.0 {kode} {message}\r\n",
            f"Date: {tanggal}\r\n",
            "Connection: close\r\n",
            "Server: myserver/1.0\r\n",
            f"Content-Length: {len(messagebody)}\r\n"
        ]
        for kk, vv in headers.items():
            resp.append(f"{kk}: {vv}\r\n")
        resp.append("\r\n")

        response_headers = "".join(resp)
        if not isinstance(messagebody, bytes):
            messagebody = messagebody.encode()
        return response_headers.encode() + messagebody

    def http_get(self, object_address, headers):
        thedir = './'
        if object_address == '/':
            return self.response(200, 'OK', 'Ini Adalah web Server percobaan', {})
        if object_address == '/video':
            return self.response(302, 'Found', '', {'location': 'https://youtu.be/katoxpnTf04'})
        if object_address == '/santai':
            return self.response(200, 'OK', 'santai saja', {})

        object_address = object_address.lstrip('/')
        # Validasi path untuk keamanan
        if '..' in object_address or not os.path.exists(thedir + object_address) or os.path.isdir(thedir + object_address):
             return self.response(404, 'Not Found', '', {})

        try:
            with open(os.path.join(thedir, object_address), 'rb') as fp:
                isi = fp.read()
            
            fext = os.path.splitext(object_address)[1]
            content_type = self.types.get(fext, 'application/octet-stream')
            
            headers = {'Content-type': content_type}
            return self.response(200, 'OK', isi, headers)
        except Exception as e:
            self.logger.error(f"Error reading file {object_address}: {e}")
            return self.response(500, 'Internal Server Error', '', {})


    def http_post(self, object_address, headers):
        return self.response(200, 'OK', "POST request processed", {})

    # --- (Logika Game) ---
    def reset_game(self):
        self.logger.info("WINNER DECLARED. Resetting server for a new session.")
        self.players = {}
        self.game_state = {'game_started': False, 'winner': None, 'game_over_time': None}

    def register_new_player(self):
        next_id = 1
        while str(next_id) in self.players:
            next_id += 1
        player_id = str(next_id)
        self.players[player_id] = {'state': 'waiting', 'score': 0, 'last_seen': time.time()}
        self.logger.info(f"New player registered with ID: {player_id}")
        return self.create_response({'status': 'OK', 'player_id': player_id})

    def set_player_game_over(self, player_id, final_score):
        if player_id in self.players and self.players[player_id].get('state') == 'playing':
            self.players[player_id]['state'] = 'game_over'
            self.players[player_id]['score'] = final_score
            self.logger.info(f"Player {player_id} is GAME OVER with final score {final_score}.")
            
            playing_players = [p for p in self.players.values() if p.get('state') == 'playing']
            if not playing_players:
                self.logger.info("All players are game over. Determining winner.")
                winner = max(self.players.values(), key=lambda p: p.get('score', 0))
                winner_id = next((pid for pid, p in self.players.items() if p == winner), None)
                if winner_id:
                    self.game_state['winner'] = {'id': winner_id, 'score': winner['score']}
                    self.game_state['game_over_time'] = time.time()
                    self.logger.info(f"Winner is Player {winner_id} with score {winner['score']}.")
        return self.create_response({'status': 'OK'})

    def set_player_ready(self, player_id):
        if player_id in self.players:
            self.players[player_id]['state'] = 'ready'
            all_players = list(self.players.values())
            if len(all_players) >= 2 and all(p.get('state') == 'ready' for p in all_players):
                self.game_state['game_started'] = True
                for p_id in self.players:
                    self.players[p_id]['state'] = 'playing'
                self.logger.info("Game is starting!")
        return self.create_response({'status': 'OK'})

    def update_player(self, player_id, x, y, is_jumping, is_ducking, score):
        if player_id in self.players:
            self.players[player_id].update({
                'x': x, 'y': y, 'is_jumping': is_jumping, 'is_ducking': is_ducking,
                'score': score, 'last_seen': time.time()
            })
        return self.create_response({'status': 'OK'})

    def get_game_state(self, player_id):
        current_time = time.time()
        if player_id in self.players:
            self.players[player_id]['last_seen'] = current_time

        if self.game_state.get('game_over_time') and current_time - self.game_state['game_over_time'] > 10:
            self.reset_game()
            return self.create_response({'status': 'OK', 'game_started': False, 'all_players': {}})

        initial_player_count = len(self.players)
        active_players = {pid: pdata for pid, pdata in self.players.items() if current_time - pdata.get('last_seen', 0) < 15}
        
        if len(active_players) != initial_player_count:
            self.logger.info(f"Clearing {initial_player_count - len(active_players)} inactive player(s).")
            self.players = active_players
            if not self.game_state['game_started'] and len(self.players) >= 2:
                if all(p.get('state') == 'ready' for p in self.players.values()):
                    self.game_state['game_started'] = True
                    for p_id in self.players:
                        self.players[p_id]['state'] = 'playing'
                    self.logger.info("An inactive player was removed, and now all remaining players are ready. Starting game!")

        return self.create_response({
            'status': 'OK',
            'game_started': self.game_state['game_started'],
            'winner': self.game_state.get('winner'),
            'all_players': self.players,
        })

    def get_stats(self):
        return {
            'active_players': len(self.players),
            'total_requests': self.request_count,
            'uptime': time.time() - self.start_time
        }

    def create_response(self, data):
        return json.dumps(data).encode('utf-8')

    # --- Metode proses() yang sudah terintegrasi ---
    def proses(self, data):
        self.request_count += 1
        
        # Cek apakah ini request HTTP atau command game
        # Request HTTP standar memiliki format "METHOD /path HTTP/version"
        if "HTTP/" in data.split("\r\n")[0]:
            requests = data.split("\r\n")
            baris = requests[0]
            all_headers = {h.split(': ')[0]: h.split(': ')[1] for h in requests[1:] if ': ' in h}
            j = baris.split(" ")
            try:
                method = j[0].upper().strip()
                object_address = j[1].strip()
                if method == 'GET':
                    return self.http_get(object_address, all_headers)
                elif method == 'POST':
                    return self.http_post(object_address, all_headers)
                else:
                    return self.response(400, 'Bad Request', '', {})
            except IndexError:
                return self.response(400, 'Bad Request', '', {})
        else:
            # Jika bukan, anggap sebagai command game
            try:
                request_string = data.strip()
                parts = request_string.split(' ')
                command = parts[0]
                
                if command == 'register':
                    return self.register_new_player()
                elif command == 'game_over' and len(parts) >= 3:
                    return self.set_player_game_over(parts[1], int(parts[2]))
                elif command == 'set_ready' and len(parts) >= 2:
                    return self.set_player_ready(parts[1])
                elif command == 'update_player' and len(parts) >= 7:
                    player_id, x, y, is_jumping, is_ducking, score = parts[1], float(parts[2]), float(parts[3]), parts[4].lower() == 'true', parts[5].lower() == 'true', int(parts[6])
                    return self.update_player(player_id, x, y, is_jumping, is_ducking, score)
                elif command == 'get_game_state' and len(parts) >= 2:
                    return self.get_game_state(parts[1])
                else:
                    return self.create_response({'status': 'ERROR', 'message': 'Unknown command'})
            except Exception as e:
                self.logger.error(f"Error processing game command: {request_string} -> {e}")
                return self.create_response({'status': 'ERROR', 'message': str(e)})