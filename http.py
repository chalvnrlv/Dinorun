import json
import time
import logging

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

    def reset_game(self):
        self.logger.info("WINNER DECLARED. Resetting server for a new session.")
        self.players = {}
        self.game_state = { 'game_started': False, 'winner': None, 'game_over_time': None }

    def proses(self, request_string):
        self.request_count += 1
        try:
            request_string = request_string.strip()
            parts = request_string.split(' ')
            command = parts[0]
            
            if command == 'register': return self.register_new_player()
            elif command == 'game_over' and len(parts) >= 3: return self.set_player_game_over(parts[1], int(parts[2]))
            elif command == 'set_ready' and len(parts) >= 2: return self.set_player_ready(parts[1])
            elif command == 'update_player' and len(parts) >= 7:
                player_id, x, y, is_jumping, is_ducking, score = parts[1], float(parts[2]), float(parts[3]), parts[4]=='true', parts[5]=='true', int(parts[6])
                return self.update_player(player_id, x, y, is_jumping, is_ducking, score)
            elif command == 'get_game_state' and len(parts) >= 2: return self.get_game_state(parts[1])
            else: return self.create_response({'status': 'ERROR', 'message': 'Unknown command'})
        except Exception as e:
            self.logger.error(f"Error processing request: {e}")
            return self.create_response({'status': 'ERROR', 'message': str(e)})

    def register_new_player(self):
        next_id = 1
        while str(next_id) in self.players: next_id += 1
        player_id = str(next_id)
        self.players[player_id] = { 'state': 'waiting', 'score': 0, 'last_seen': time.time() }
        self.logger.info(f"New player registered with ID: {player_id}")
        return self.create_response({'status': 'OK', 'player_id': player_id})

    def set_player_game_over(self, player_id, final_score):
        if player_id in self.players and self.players[player_id].get('state') == 'playing':
            self.players[player_id]['state'] = 'game_over'
            self.players[player_id]['score'] = final_score
            self.logger.info(f"Player {player_id} is GAME OVER with final score {final_score}.")
            
            # Periksa apakah semua pemain yang bermain sudah game over
            if not any(p.get('state') == 'playing' for p in self.players.values()):
                self.logger.info("All players are game over. Determining winner.")
                winner = max(self.players.values(), key=lambda p: p.get('score', 0))
                winner_id = next(pid for pid, p in self.players.items() if p == winner)
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
                for p_id in self.players: self.players[p_id]['state'] = 'playing'
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
        # [FIX] Perbarui last_seen di sini agar pemain di lobby tidak timeout
        if player_id in self.players:
            self.players[player_id]['last_seen'] = current_time
        
        # Reset game setelah 10 detik menampilkan pemenang
        if self.game_state.get('game_over_time') and current_time - self.game_state['game_over_time'] > 10:
            self.reset_game()
            # Langsung kirim state kosong setelah reset
            return self.create_response({'status': 'OK', 'game_started': False, 'all_players': {}})
        
        return self.create_response({
            'status': 'OK',
            'game_started': self.game_state['game_started'],
            'winner': self.game_state.get('winner'),
            'all_players': self.players,
        })
    
    def get_stats(self):
        """[FIX] Fungsi untuk statistik server ditambahkan kembali."""
        return {
            'active_players': len(self.players),
            'total_requests': self.request_count,
            'uptime': time.time() - self.start_time
        }
    
    def create_response(self, data):
        return json.dumps(data).encode('utf-8')