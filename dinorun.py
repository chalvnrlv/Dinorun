import pygame
import sys
import random
import socket
import logging
import json
import os
import time

# Konfigurasi
logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s:%(name)s:%(message)s')
os.environ['GAME_SERVER'] = 'localhost'

# Inisialisasi Pygame dan konstanta
pygame.init()
WIDTH, HEIGHT = 1000, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Dino Runner - Multiplayer")
clock = pygame.time.Clock()
FPS = 30
WHITE, BLACK, GREEN, BROWN, GRAY, BLUE, ORANGE, RED, GOLD = ((255,255,255), (0,0,0), (34,139,34), (139,69,19), (128,128,128), (135,206,235), (255,165,0), (255,0,0), (255, 215, 0))
GROUND_HEIGHT = HEIGHT - 100
GRAVITY, JUMP_STRENGTH, OBSTACLE_SPEED, SPAWN_RATE = 0.8, -15, 8, 120

class ClientInterface:
    def __init__(self):
        server_host = os.getenv('GAME_SERVER', 'localhost')
        self.server_address = (server_host, 55555)
        self.player_id = None

    def register(self):
        response = self.send_command("register")
        if response and response.get('status') == 'OK':
            self.player_id = response.get('player_id')
            return self.player_id
        return None

    def get_game_state(self): return self.send_command(f"get_game_state {self.player_id}")
    def update_player_state(self, x, y, is_jumping, is_ducking, score): self.send_command(f"update_player {self.player_id} {x} {y} {is_jumping} {is_ducking} {score}")
    def set_ready(self): return self.send_command(f"set_ready {self.player_id}")
    def send_game_over(self, score): return self.send_command(f"game_over {self.player_id} {score}")

    def send_command(self, command_str=""):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2.0)
        try:
            sock.connect(self.server_address)
            sock.sendall((command_str + '\n').encode())
            data_received = ""
            while True:
                data = sock.recv(4096)
                if data:
                    data_received += data.decode('utf-8', errors='ignore')
                    if "\r\n\r\n" in data_received: break
                else: break
            json_part = data_received.split("\r\n\r\n")[0]
            if json_part: return json.loads(json_part.strip())
            return None
        except Exception: return None
        finally: sock.close()

class Obstacle:
    def __init__(self, obstacle_type, x, y):
        self.type, self.x, self.y, self.width, self.height, self.speed = obstacle_type, x, y, 40 if obstacle_type == 'rock' else 60, 40 if obstacle_type == 'rock' else 30, OBSTACLE_SPEED
    def update(self): self.x -= self.speed
    def draw(self, surface):
        color, border_color = (GRAY, BLACK) if self.type == 'rock' else (BROWN, BLACK)
        pygame.draw.rect(surface, color, (self.x, self.y, self.width, self.height))
        pygame.draw.rect(surface, border_color, (self.x, self.y, self.width, self.height), 2)
    def get_rect(self): return pygame.Rect(self.x, self.y, self.width, self.height)

class Dinosaur:
    def __init__(self, player_id, client_interface, x=100, is_remote=False):
        self.id, self.client, self.x, self.is_remote = player_id, client_interface, x, is_remote
        self.y, self.width, self.height, self.score = GROUND_HEIGHT - 60, 50, 60, 0
        self.vel_y, self.is_jumping, self.is_ducking, self.color = 0, False, False, GREEN if not is_remote else ORANGE
    def jump(self):
        if not self.is_jumping and not self.is_ducking: self.is_jumping, self.vel_y = True, JUMP_STRENGTH
    def duck(self, is_ducking):
        if not self.is_jumping:
            if is_ducking and not self.is_ducking: self.is_ducking, self.height, self.y = True, 30, GROUND_HEIGHT - 30
            elif not is_ducking and self.is_ducking: self.is_ducking, self.height, self.y = False, 60, GROUND_HEIGHT - 60
    def update(self, keys_pressed=None):
        if not self.is_remote and keys_pressed:
            if (keys_pressed[pygame.K_SPACE] or keys_pressed[pygame.K_UP]): self.jump()
            self.duck(keys_pressed[pygame.K_DOWN])
        if self.is_jumping:
            self.vel_y += GRAVITY; self.y += self.vel_y
            if self.y >= GROUND_HEIGHT - self.height: self.y, self.is_jumping, self.vel_y = GROUND_HEIGHT - self.height, False, 0
        if not self.is_remote: self.score += 1; self.client.update_player_state(self.x, self.y, self.is_jumping, self.is_ducking, self.score)
    def set_state_from_server(self, server_data):
        self.x, self.y, self.score = server_data.get('x', self.x), server_data.get('y', self.y), server_data.get('score', self.score)
        self.duck(server_data.get('is_ducking', False)); self.is_jumping = server_data.get('is_jumping', False)
    def draw(self, surface, is_game_over=False):
        color = self.color if not is_game_over else GRAY
        pygame.draw.rect(surface, color, (self.x, self.y, self.width, self.height))
        pygame.draw.rect(surface, BLACK, (self.x, self.y, self.width, self.height), 2)
        font = pygame.font.Font(None, 24); text = font.render(f"P{self.id} ({self.score})", True, BLACK)
        surface.blit(text, (self.x + 5, self.y - 25))
    def get_rect(self): return pygame.Rect(self.x, self.y, self.width, self.height)

class Game:
    def __init__(self):
        self.client = ClientInterface()
        self.local_player, self.remote_players, self.obstacles = None, {}, []
        self.spawn_timer, self.is_ready = 0, False

    def initialize_connection(self):
        print("Connecting to server...")
        player_id = self.client.register()
        if player_id:
            print(f"Successfully connected! You are Player {player_id}.")
            self.local_player = Dinosaur(player_id, self.client, 100)
            return True
        print("Failed to connect to the server. Exiting."); return False

    def run(self):
        if not self.initialize_connection(): pygame.quit(); sys.exit()
        if self.lobby_loop(): self.game_loop()
        print("Thank you for playing!"); pygame.quit(); sys.exit()

    def lobby_loop(self):
        self.client.update_player_state(self.local_player.x, self.local_player.y, False, False, 0)
        while True:
            server_state = self.client.get_game_state()
            if not server_state: print("Connection lost. Exiting."); return False
            if server_state.get('game_started', False): return True
            for event in pygame.event.get():
                if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE): return False
                if event.type == pygame.KEYDOWN and event.key == pygame.K_r and not self.is_ready:
                    self.client.set_ready(); self.is_ready = True
            self.draw_lobby_screen(server_state.get('all_players', {}))
            pygame.display.flip(); clock.tick(10)
    
    def game_loop(self):
        running, local_game_over, sent_game_over = True, False, False
        while running:
            server_state = self.client.get_game_state()
            if not server_state or self.local_player.id not in server_state.get('all_players', {}):
                print("Game over or disconnected by server."); time.sleep(5); running = False; continue

            for event in pygame.event.get():
                if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE): running = False
            
            if not local_game_over:
                self.local_player.update(pygame.key.get_pressed())
                self.spawn_obstacle(); self.update_obstacles()
                if self.check_collisions(): local_game_over = True
            
            if local_game_over and not sent_game_over:
                self.client.send_game_over(self.local_player.score); sent_game_over = True

            self.update_remote_players(server_state)
            self.draw_game_elements(local_game_over, server_state)
            pygame.display.flip(); clock.tick(FPS)
    
    def draw_game_elements(self, local_game_over, server_state):
        self.draw_background(screen)
        for o in self.obstacles: o.draw(screen)
        self.local_player.draw(screen, local_game_over)
        for pid, player in self.remote_players.items():
            player_state = server_state.get('all_players', {}).get(pid, {}).get('state')
            player.draw(screen, player_state == 'game_over')
        self.draw_ui(screen)
        if server_state.get('winner'): self.draw_winner_screen(server_state['winner'])
        elif local_game_over:
            font = pygame.font.Font(None, 72); text = font.render("GAME OVER", True, BLACK)
            screen.blit(text, (WIDTH//2 - text.get_width()//2, HEIGHT//2 - text.get_height()//2))

    def draw_winner_screen(self, winner_info):
        font_big, font_med = pygame.font.Font(None, 80), pygame.font.Font(None, 50)
        winner_text = font_big.render(f"WINNER: PLAYER {winner_info['id']}", True, GOLD)
        score_text = font_med.render(f"Score: {winner_info['score']}", True, WHITE)
        screen.blit(winner_text, (WIDTH//2 - winner_text.get_width()//2, HEIGHT//2 - 60))
        screen.blit(score_text, (WIDTH//2 - score_text.get_width()//2, HEIGHT//2 + 20))

    def draw_lobby_screen(self, players_data):
        screen.fill(BLUE)
        font_title, font_info, font_player = pygame.font.Font(None, 72), pygame.font.Font(None, 36), pygame.font.Font(None, 32)
        title_text = font_title.render("Waiting for Players...", True, BLACK)
        screen.blit(title_text, (WIDTH//2 - title_text.get_width()//2, 50))
        ready_text = font_info.render("Press 'R' to Ready Up!" if not self.is_ready else "You are Ready!", True, WHITE)
        screen.blit(ready_text, (WIDTH//2 - ready_text.get_width()//2, 150))
        y_offset = 250
        for pid, pdata in sorted(players_data.items()):
            state, color = ("READY", GREEN) if pdata.get('state') == 'ready' else ("WAITING", RED)
            player_text = font_player.render(f"Player {pid}: {state}", True, color)
            screen.blit(player_text, (WIDTH//2 - player_text.get_width()//2, y_offset)); y_offset += 40

    def spawn_obstacle(self):
        if self.spawn_timer <= 0:
            obstacle_type = random.choice(['rock', 'pterodactyl']); y = GROUND_HEIGHT - 40 if obstacle_type == 'rock' else GROUND_HEIGHT - 70
            self.obstacles.append(Obstacle(obstacle_type, WIDTH, y))
            self.spawn_timer = random.randint(max(30, 120 - self.local_player.score // 10), SPAWN_RATE)
        else: self.spawn_timer -= 1
    def update_obstacles(self):
        for o in self.obstacles[:]: o.update();
        if o.x + o.width < 0: self.obstacles.remove(o)
    def check_collisions(self): return any(self.local_player.get_rect().colliderect(o.get_rect()) for o in self.obstacles)
    def update_remote_players(self, server_state):
        if 'all_players' not in server_state: return
        server_players = dict(server_state['all_players'])
        if self.local_player.id in server_players: del server_players[self.local_player.id]
        current_pids, server_pids = set(self.remote_players.keys()), set(server_players.keys())
        for pid in current_pids - server_pids: del self.remote_players[pid]
        for pid, pdata in server_players.items():
            if pid not in self.remote_players: self.remote_players[pid] = Dinosaur(pid, self.client, 100, True)
            self.remote_players[pid].set_state_from_server(pdata)
    def draw_background(self, surface):
        surface.fill(BLUE); pygame.draw.rect(surface, GREEN, (0, GROUND_HEIGHT, WIDTH, HEIGHT - GROUND_HEIGHT)); pygame.draw.line(surface, BLACK, (0, GROUND_HEIGHT), (WIDTH, GROUND_HEIGHT), 3)
    def draw_ui(self, surface):
        font = pygame.font.Font(None, 36); score_text = font.render(f"Score: {self.local_player.score}", True, BLACK)
        surface.blit(score_text, (10, 10))

if __name__ == "__main__":
    game = Game()
    game.run()