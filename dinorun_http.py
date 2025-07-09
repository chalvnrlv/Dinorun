import json
import time
import logging
import os
from datetime import datetime

class HttpServer:
    def __init__(self):
        self.players = {}
        self.game_state = {'game_started': False, 'winner': None, 'game_over_time': None}
        self.start_time = time.time()
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)

    # --- FUNGSI LOGIKA GAME (Sebagian besar tidak berubah) ---
    def reset_game(self):
        self.players = {}
        self.game_state = {'game_started': False, 'winner': None, 'game_over_time': None}

    def register_new_player(self):
        next_id = 1
        while str(next_id) in self.players: next_id += 1
        player_id = str(next_id)
        self.players[player_id] = {'state': 'waiting', 'score': 0, 'last_seen': time.time()}
        return {'status': 'OK', 'player_id': player_id}

    def set_player_ready(self, player_id):
        if player_id in self.players:
            self.players[player_id]['state'] = 'ready'
            if len(self.players) >= 2 and all(p.get('state') == 'ready' for p in self.players.values()):
                self.game_state['game_started'] = True
                for p_id in self.players: self.players[p_id]['state'] = 'playing'
                self.logger.info("Game is starting!")
        return {'status': 'OK'}

    def update_player(self, data):
        player_id = data.get('player_id')
        if player_id in self.players:
            self.players[player_id].update({
                'x': data.get('x'), 'y': data.get('y'), 
                'is_jumping': data.get('is_jumping'), 'is_ducking': data.get('is_ducking'),
                'score': data.get('score'), 'last_seen': time.time()
            })
        return {'status': 'OK'}

    def set_player_game_over(self, data):
        player_id = data.get('player_id')
        if player_id in self.players and self.players[player_id].get('state') == 'playing':
            self.players[player_id]['state'] = 'game_over'
            self.players[player_id]['score'] = data.get('score')
            if not any(p.get('state') == 'playing' for p in self.players.values()):
                winner = max(self.players.values(), key=lambda p: p.get('score', 0))
                winner_id = next((pid for pid, p in self.players.items() if p == winner), None)
                if winner_id:
                    self.game_state['winner'] = {'id': winner_id, 'score': winner['score']}
                    self.game_state['game_over_time'] = time.time()
        return {'status': 'OK'}

    def get_game_state(self, player_id):
        current_time = time.time()
        if player_id in self.players: self.players[player_id]['last_seen'] = current_time
        if self.game_state.get('game_over_time') and current_time - self.game_state['game_over_time'] > 10:
            self.reset_game()
        active_players = {pid: p for pid, p in self.players.items() if current_time - p.get('last_seen', 0) < 15}
        self.players = active_players
        return {'game_started': self.game_state['game_started'], 'winner': self.game_state.get('winner'), 'all_players': self.players}

    # --- FUNGSI HTTP DARI PROGJAR5 ---
    def response(self, kode=200, message='OK', body=None, headers=None):
        if headers is None: headers = {}
        
        body_bytes = b''
        if body:
            body_bytes = json.dumps(body).encode('utf-8')
            headers['Content-Type'] = 'application/json'
        
        headers['Content-Length'] = str(len(body_bytes))
        
        tanggal = datetime.now().strftime('%c')
        header_str = f"HTTP/1.0 {kode} {message}\r\n"
        header_str += f"Date: {tanggal}\r\n"
        header_str += "Server: DinoRunServer/1.0\r\n"
        for k, v in headers.items():
            header_str += f"{k}: {v}\r\n"
        header_str += "\r\n"
        
        return header_str.encode('utf-8') + body_bytes

    # --- INI ADALAH BAGIAN UTAMA: API ROUTER ---
    def proses(self, data):
        try:
            lines = data.split('\r\n')
            request_line = lines[0]
            method, path, _ = request_line.split(' ')
            
            # Ekstrak body untuk POST request
            body_dict = {}
            if method == 'POST' and '\r\n\r\n' in data:
                body_str = data.split('\r\n\r\n', 1)[1]
                if body_str: body_dict = json.loads(body_str)

            # Routing berdasarkan path dan method
            if method == 'POST' and path == '/register':
                response_body = self.register_new_player()
                return self.response(200, 'OK', response_body)

            if method == 'POST' and path == '/ready':
                player_id = body_dict.get('player_id')
                response_body = self.set_player_ready(player_id)
                return self.response(200, 'OK', response_body)

            if method == 'POST' and path == '/update':
                response_body = self.update_player(body_dict)
                return self.response(200, 'OK', response_body)
                
            if method == 'POST' and path == '/gameover':
                response_body = self.set_player_game_over(body_dict)
                return self.response(200, 'OK', response_body)

            if method == 'GET' and path.startswith('/gamestate'):
                # Ekstrak player_id dari query parameter
                player_id = path.split('?player_id=')[1]
                response_body = self.get_game_state(player_id)
                return self.response(200, 'OK', response_body)

            # Jika tidak ada path yang cocok
            return self.response(404, 'Not Found', {'error': 'Endpoint not found'})

        except Exception as e:
            self.logger.error(f"Error processing request: {e}")
            return self.response(500, 'Internal Server Error', {'error': str(e)})