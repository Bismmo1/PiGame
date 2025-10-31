import pygame
import math
import os
import map_data
import random

# --- CONFIGURATION ---
SCREEN_WIDTH = 640
SCREEN_HEIGHT = 480
TILE_SIZE = 32
FPS = 60
WHITE = (255, 255, 255)
RED = (255, 0, 0)
BACKGROUND_COLOR = (0, 0, 0) # Back to dark to contrast sprites

# MOVEMENT CONFIGURATION
WALK_SPEED = 2.0
SPRINT_SPEED = 4.0

# CAMERA CONFIGURATION
CAMERA_X = SCREEN_WIDTH // 2
CAMERA_Y = SCREEN_HEIGHT // 2

# DEFINE THE ABSOLUTE PATH TO YOUR SPRITES FOLDER
ASSET_FOLDER = r'C:\Users\graz\Pictures\Game\Player\temp\Basic'

# TILE ASSET NAMES
TILE_ASSETS = {
    map_data.GRASS: 'grass.png',
    map_data.WALL: 'wall.png',
    map_data.STAIRS: 'stairs.png',
    map_data.DOOR: 'door.png',
    map_data.SPAWN: 'spawn.png',
}

# --- ASSET LOADING HELPER ---
def load_sprite(filename):
    """Loads, scales, and converts a sprite image."""
    path = os.path.join(ASSET_FOLDER, filename)
    try:
        image = pygame.image.load(path).convert_alpha()
        image = pygame.transform.scale(image, (TILE_SIZE, TILE_SIZE))
        return image
    except pygame.error as e:
        print(f"Error loading image at path: {path}")
        print(f"Pygame error: {e}")
        missing_sprite = pygame.Surface([TILE_SIZE, TILE_SIZE])
        missing_sprite.fill(RED)
        return missing_sprite

# --- NEW: INPUT MANAGER CLASS ---
class InputManager:
    """Handles keyboard input and translates it into generic game actions."""
    def __init__(self):
        # Maps Pygame keys to generic game actions
        self.key_map = {
            pygame.K_UP:    'up',
            pygame.K_w:     'up',
            pygame.K_DOWN:  'down',
            pygame.K_s:     'down',
            pygame.K_LEFT:  'left',
            pygame.K_a:     'left',
            pygame.K_RIGHT: 'right',
            pygame.K_d:     'right',
            pygame.K_LSHIFT:'sprint',
            pygame.K_RSHIFT:'sprint',
            pygame.K_SPACE: 'action_a', # A Button
            pygame.K_y:     'action_y'  # Y Button
        }
        # This dictionary will hold the current state of all actions
        self.action_state = {
            'up': False, 'down': False, 'left': False, 'right': False,
            'sprint': False, 'action_a': False, 'action_y': False
        }

    def update(self):
        """Reads the keyboard state and updates the action_state dictionary."""
        keys = pygame.key.get_pressed()
        
        # Reset and then update the state based on currently pressed keys
        for action in self.action_state:
            self.action_state[action] = False
            
        for key, action in self.key_map.items():
            if keys[key]:
                self.action_state[action] = True

    def is_pressed(self, action):
        """Checks if a specific game action is currently active."""
        return self.action_state.get(action, False)

# --- MAP SYSTEM CLASS ---
class Map():
    def __init__(self, map_name):
        self.map_array = map_data.MAP_COLLECTION[map_name]
        self.height = len(self.map_array)
        self.width = len(self.map_array[0])
        self.tile_sprites = self.load_map_tiles()

    def load_map_tiles(self):
        """Pre-loads and scales all tile sprites required for the map."""
        sprites = {}
        for code, filename in TILE_ASSETS.items():
            sprites[code] = load_sprite(filename)
        return sprites

    def draw(self, screen, camera_offset_x, camera_offset_y):
        """Renders only the visible tiles to the screen, offset by the camera."""
        cols_visible = SCREEN_WIDTH // TILE_SIZE + 1
        rows_visible = SCREEN_HEIGHT // TILE_SIZE + 1
        
        start_row = max(0, math.floor(-camera_offset_y / TILE_SIZE))
        start_col = max(0, math.floor(-camera_offset_x / TILE_SIZE))

        end_row = min(self.height, start_row + rows_visible)
        end_col = min(self.width, start_col + cols_visible)
        
        for row_index in range(start_row, end_row):
            for col_index in range(start_col, end_col):
                tile_code = self.map_array[row_index][col_index]
                x = col_index * TILE_SIZE + camera_offset_x
                y = row_index * TILE_SIZE + camera_offset_y
                
                tile_image = self.tile_sprites.get(tile_code)
                if tile_image:
                    screen.blit(tile_image, (x, y))

# --- PLAYER SPAWN UTILITY ---
def get_random_spawn_point(map_instance):
    """Scans the map array for all SPAWN tiles and returns a random (x, y) pixel coordinate."""
    spawn_points = []
    for row_index, row in enumerate(map_instance.map_array):
        for col_index, tile_code in enumerate(row):
            if tile_code == map_data.SPAWN:
                x = col_index * TILE_SIZE
                y = row_index * TILE_SIZE
                spawn_points.append((x, y))

    if not spawn_points:
        print("Warning: No SPAWN tiles found. Starting at (0, 0) in world coordinates.")
        return (0, 0)
        
    return random.choice(spawn_points)

# --- PLAYER CLASS ---
class Player(pygame.sprite.Sprite):
    def __init__(self, x, y, current_map):
        super().__init__()
        
        self.world_x = x
        self.world_y = y
        self.screen_x = 0
        self.screen_y = 0
        self.current_map = current_map
        
        self.walk_speed = WALK_SPEED
        self.sprint_speed = SPRINT_SPEED
        self.current_speed = self.walk_speed

        self.sprites = {
            'up': load_sprite('arrowUp.png'),
            'down': load_sprite('arrowDown.png'),
            'left': load_sprite('arrowLeft.png'),
            'right': load_sprite('arrowRight.png'),
        }
        
        self.current_direction = 'down'
        self.image = self.sprites[self.current_direction]
        self.rect = self.image.get_rect(topleft=(self.world_x, self.world_y))

        self.change_x = 0
        self.change_y = 0

    def _check_collision(self, next_x, next_y):
        """Checks if a position (in pixels) collides with a WALL tile."""
        tile_x1 = int(next_x // TILE_SIZE)
        tile_y1 = int(next_y // TILE_SIZE)
        tile_x2 = int((next_x + self.rect.width - 1) // TILE_SIZE)
        tile_y2 = int((next_y + self.rect.height - 1) // TILE_SIZE)

        map_array = self.current_map.map_array
        
        for tx, ty in [(tile_x1, tile_y1), (tile_x1, tile_y2), (tile_x2, tile_y1), (tile_x2, tile_y2)]:
            if 0 <= ty < self.current_map.height and 0 <= tx < self.current_map.width:
                tile_code = map_array[ty][tx]
                if tile_code == map_data.WALL:
                    return True
        return False

    def handle_input(self, input_manager):
        """Reads from the InputManager to set speed and movement vectors."""
        if input_manager.is_pressed('sprint'):
            self.current_speed = self.sprint_speed
        else:
            self.current_speed = self.walk_speed
            
        self.change_x = 0
        self.change_y = 0

        if input_manager.is_pressed('left'):
            self.change_x = -self.current_speed
            self.current_direction = 'left'
        if input_manager.is_pressed('right'):
            self.change_x = self.current_speed
            self.current_direction = 'right'
        if input_manager.is_pressed('up'):
            self.change_y = -self.current_speed
            self.current_direction = 'up'
        if input_manager.is_pressed('down'):
            self.change_y = self.current_speed
            self.current_direction = 'down'
            
        self.image = self.sprites[self.current_direction]
        
        if input_manager.is_pressed('action_a'):
            print("Action Button (A) Pressed!")
        if input_manager.is_pressed('action_y'):
            print("Use Button (Y) Pressed!")

    def update(self):
        """Calculates position changes, applies diagonal correction and collision."""
        mag_sq = self.change_x**2 + self.change_y**2
        dx, dy = 0, 0
        
        if mag_sq > 0:
            if self.change_x != 0 and self.change_y != 0:
                scaling_factor = self.current_speed / math.sqrt(mag_sq)
                dx = self.change_x * scaling_factor
                dy = self.change_y * scaling_factor
            else:
                dx = self.change_x
                dy = self.change_y

            if not self._check_collision(self.world_x + dx, self.world_y):
                self.world_x += dx
            
            if not self._check_collision(self.world_x, self.world_y + dy):
                self.world_y += dy

        map_max_x = self.current_map.width * TILE_SIZE - self.rect.width
        map_max_y = self.current_map.height * TILE_SIZE - self.rect.height
        
        self.world_x = max(0, min(self.world_x, map_max_x))
        self.world_y = max(0, min(self.world_y, map_max_y))

# --- MAIN GAME LOOP ---
def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Top-Down Game Prototype")
    clock = pygame.time.Clock()

    # --- SETUP GAME OBJECTS ---
    input_manager = InputManager() # Create the input handler
    current_map = Map("map1")
    start_x, start_y = get_random_spawn_point(current_map)
    player = Player(start_x, start_y, current_map)
    
    all_sprites = pygame.sprite.Group(player)

    map_width_pixels = current_map.width * TILE_SIZE
    map_height_pixels = current_map.height * TILE_SIZE

    # --- GAME LOOP ---
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        # --- UPDATE ---
        input_manager.update() # Read keyboard state
        player.handle_input(input_manager) # Pass actions to player
        player.update() # Update player logic

        # --- CAMERA ---
        camera_offset_x = CAMERA_X - player.world_x
        camera_offset_y = CAMERA_Y - player.world_y
        
        # Clamp Camera X
        if map_width_pixels < SCREEN_WIDTH:
            camera_offset_x = (SCREEN_WIDTH - map_width_pixels) // 2
        else:
            camera_offset_x = min(0, max(camera_offset_x, SCREEN_WIDTH - map_width_pixels))

        # Clamp Camera Y
        if map_height_pixels < SCREEN_HEIGHT:
            camera_offset_y = (SCREEN_HEIGHT - map_height_pixels) // 2
        else:
            camera_offset_y = min(0, max(camera_offset_y, SCREEN_HEIGHT - map_height_pixels))

        player.rect.topleft = (player.world_x + camera_offset_x, player.world_y + camera_offset_y)

        # --- DRAWING ---
        screen.fill(BACKGROUND_COLOR)
        current_map.draw(screen, camera_offset_x, camera_offset_y)
        all_sprites.draw(screen)

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()

if __name__ == "__main__":
    main()