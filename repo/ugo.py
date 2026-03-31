"""
Grid-Based Puzzle Game
----------------------
A clean, object-oriented Pygame-CE puzzle game.
Easily expandable with enemies, boxes, and new tile types.
"""

import sys
import pygame

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
TILE_SIZE    = 64          # pixels per grid cell
FPS          = 60
WINDOW_TITLE = "Grid Puzzle"

# Colours
COL_BG          = (18,  18,  30)   # dark navy background
COL_WALL        = (60,  63,  80)   # muted slate wall
COL_WALL_BORDER = (80,  84, 105)   # lighter wall edge
COL_GOAL        = (80, 200, 120)   # green goal tile
COL_GOAL_INNER  = (50, 160,  90)
COL_GRID        = (35,  35,  55)   # faint grid lines
COL_PLAYER_FB   = (80, 140, 230)   # fallback player square (blue)
COL_HUD_BG      = (10,  10,  20, 180)
COL_HUD_TEXT    = (220, 220, 240)

# ---------------------------------------------------------------------------
# Level definitions
# ---------------------------------------------------------------------------
# Legend:
#   '#' – wall          '.' – empty floor
#   'P' – player start  'G' – goal tile
#
# Add more levels to LEVELS; the game advances through them in order.

LEVELS = [
    ["#####", 
     "#P.G#", 
     "#####"],

    ["######", 
     "#P..G#", 
     "######"],

    ["#######", 
     "#P...G#", 
     "#######"],

    ["#######", 
     "#P...#", 
     "#..#.G#", 
     "#######"],

    ["#########", 
     "#P..#..G#", 
     "#.#.#.#.#", 
     "#.......#", 
     "#########"],

    ["#######", 
     "#P....#", 
     "#.###.#", 
     "#...G.#", 
     "#######"],

    ["#########", 
     "#P#.....#", 
     "#.#.###.#", 
     "#.....G.#", 
     "#########"],

    ["#####", 
     "#P..#", 
     "#.#.#", 
     "#..G#", 
     "#####"],

    ["#######", 
     "#P. . #", 
     "# .#. #", 
     "# ..G.#", 
     "#######"],

    ["#########", 
     "#P....G.#", 
     "#########"],

    ["#######", 
     "#P#G..#", 
     "#.#.###", 
     "#.....#", 
     "#######"],

    ["#########", 
     "#P......#", 
     "#######.#", 
     "#G......#", 
     "#########"],

    ["###########", 
     "#P.......G#", 
     "###########"],

    ["#######", 
     "#P....#", 
     "#.###.#", 
     "#.#G#.#", 
     "#.#.#.#", 
     "#...#.#", 
     "#######"],

    ["#########", 
     "#P#...#.#", 
     "#.#.#.#.#", 
     "#.#.#.#.#", 
     "#...#G#.#", 
     "#########"],

    ["#######", 
     "#P#...#", 
     "#.#.#.#", 
     "#.#.#.#", 
     "#.#.#.#", 
     "#...G.#", 
     "#######"],

    ["#########", 
     "#P......#", 
     "#.#####.#", 
     "#.#G....#", 
     "#.#####.#", 
     "#.......#", 
     "#########"],

    ["#######", 
     "#P#..G#", 
     "#.#.###", 
     "#.#...#", 
     "#.###.#", 
     "#.....#", 
     "#######"],

    ["#########", 
     "#P#.....#", 
     "#.#####.#", 
     "#.....#.#", 
     "#.###.#.#", 
     "#G#...#.#", 
     "#########"],

    ["###########", 
     "#P........#", 
     "#########.#", 
     "#G........#", 
     "###########"],

    ["###########", 
     "#P#.......#", 
     "#.#.#####.#", 
     "#.#.#G#.#.#", 
     "#.#.#.#.#.#", 
     "#.......#.#", 
     "###########"],

    ["#########", 
     "#P....#.#", 
     "#.###.#.#", 
     "#...#.#.#", 
     "###.#.#.#", 
     "#G..#...#", 
     "#########"],

    ["#############", 
     "#P..........#", 
     "#.#########.#", 
     "#.#.......#.#", 
     "#.#.#####.#.#", 
     "#.#.#G..#.#.#", 
     "#.###.###.#.#", 
     "#.........#.#", 
     "#############"],

    ["#######", 
     "#P..#.#", 
     "#.#.#.#", 
     "#.#.#.#", 
     "#.#.#.#", 
     "#.#..G#", 
     "#######"],

    ["#########", 
     "#P#.....#", 
     "#.#.###.#", 
     "#.#.#G..#", 
     "#.#.###.#", 
     "#.......#", 
     "#########"],

    ["###########", 
     "#P#.......#", 
     "#.#.#####.#", 
     "#.#.....#.#", 
     "#####.#...#", 
     "#G......#.#", 
     "###########"],

    ["#######", 
     "#P....#", 
     "#####.#", 
     "#G....#", 
     "#######"],

    ["#########", 
     "#P......#", 
     "#.#####.#", 
     "#.#...#.#", 
     "#.#G#.#.#", 
     "#.###.#.#", 
     "#.......#", 
     "#########"],

    ["###########", 
     "#P#.......#", 
     "#.#.#####.#", 
     "#.#.#...#.#", 
     "#.#.#G#.#.#", 
     "#.#.###.#.#", 
     "#.......#.#", 
     "###########"],

    ["#######", 
     "#P#...#", 
     "#.#.#.#", 
     "#.#G#.#", 
     "#.###.#", 
     "#.....#", 
     "#######"],

    ["#########", 
     "#P......#", 
     "#.#####.#", 
     "#.....#.#", 
     "#.###.#.#", 
     "#...#G#.#", 
     "#########"],

    ["###########", 
     "#P.......G#", 
     "###########"],

    ["#######", 
     "#P....#", 
     "#.#.#.#", 
     "##.#..#", 
     "#.###.#", 
     "#G....#", 
     "#######"],

    ["#########", 
     "#P#...#.#", 
     "#.#.#.#.#", 
     "#.#.#.#.#", 
     "#...#G#.#", 
     "#########"],

    ["###########", 
     "#P........#", 
     "#########.#", 
     "#G........#", 
     "###########"],

    ["#############", 
     "#P..........#", 
     "###########.#", 
     "#...........#", 
     "#.###########", 
     "#..........G#", 
     "#############"],

    ["###############", 
     "#P#...........#", 
     "#.#.#########.#", 
     "#.#.#.......#.#", 
     "#.#.#.#####.#.#", 
     "#.#...#G....#.#", 
     "#.#.#.#####.#.#", 
     "#.#.#.......#.#", 
     "#.#.#########.#", 
     "#.............#", 
     "###############"],

    ["#########", 
     "#P#...#.#", 
     "#.#.#.#.#", 
     "#.#.#.#.#", 
     "#.#.#.#.#", 
     "#.#.#.#.#", 
     "#.#.#.#.#", 
     "#...#G#.#", 
     "#########"],

    ["###########", 
     "#P#.......#", 
     "#.#.#####.#", 
     "#.#.#...#.#", 
     "#.#.#.#.#.#", 
     "#.#.#.#.#.#", 
     "#.#.#.#.#.#", 
     "#.....#G#.#", 
     "###########"],

    ["#############", 
     "#P..........#", 
     "#.#########.#", 
     "#.........#.#", 
     "#.#######.#.#", 
     "#.#.......#.#", 
     "#.#.#.#.#.#.#", 
     "#.#.#G#.#.#.#", 
     "#.#.###.#.#.#", 
     "#.#.....#.#.#", 
     "#.#######.#.#", 
     "#.........#.#", 
     "#############"],

    ["#######", 
     "#P....#", 
     "#.###.#", 
     "#.#G#.#", 
     "#.#.#.#", 
     "#.#.#.#", 
     "#.#.#.#", 
     "#.#.#.#", 
     "#...#.#", 
     "#######"],

    ["#########", 
     "#P......#", 
     "#.#####.#", 
     "#.#.....#", 
     "#.#.###.#", 
     "#.#.#G..#", 
     "#.#.###.#", 
     "#.#.....#", 
     "#.#####.#", 
     "#.......#", 
     "#########"],

    ["###########", 
     "#P........#", 
     "#########.#", 
     "#.........#", 
     "#.#########", 
     "#.........#", 
     "#########.#", 
     "#.........#", 
     "#.#########", 
     "#........G#", 
     "###########"],

    ["#############", 
     "#P#.......#.#", 
     "#.#.#####.#.#", 
     "#.#.#.....#.#", 
     "#.#.#.#.#.#.#", 
     "#.#.#.G.#.#.#", 
     "#.#.#.#.#.#.#", 
     "#.#.#...#.#.#", 
     "#.#.#####.#.#", 
     "#.........#.#", 
     "#############"],

    ["#######", 
     "#P..#.#", 
     "#.#.#.#", 
     "#.#.#.#", 
     "#.#.#.#", 
     "#.#.#.#", 
     "#.#.#.#", 
     "#.#.#.#", 
     "#.#.#.#", 
     "#.#..G#", 
     "#######"],

    ["#########", 
     "#P#.....#", 
     "#.#.###.#", 
     "#.#.#.#.#", 
     "#.#.#.#.#", 
     "#.#.#.#.#", 
     "#.#.#.#.#", 
     "#.#.#.#.#", 
     "#.#..G#.#", 
     "#########"],

    ["###########", 
     "#P........#", 
     "#.#.#####.#", 
     "#.#.#...#.#", 
     "#.#.#.#.#.#", 
     "#.#.#.#.#.#", 
     "#.#.#.#.#.#", 
     "#.#.#.#.#.#", 
     "#.#...#G#.#", 
     "###########"],

    ["#############", 
     "#P#.......#.#", 
     "#.#.#####.#.#", 
     "#...#...#.#.#", 
     "#.#.#.#.#.#.#", 
     "#.#.#.#.#.#.#", 
     "#.#.#.#.#.#.#", 
     "#.#.#.#.#.#.#", 
     "#.#...#G#.#.#", 
     "#############"],

    ["###############", 
     "#P#...........#", 
     "#.#.#####.###.#", 
     "#.#.#.......#.#", 
     "#.#.#.#####.#.#", 
     "#.#.#.#.....#.#", 
     "#.#.#.#.#.#.#.#", 
     "#.#.#.#.G.#.#.#", 
     "#.#.#.#.#.#.#.#", 
     "#.#.#.#...#.#.#", 
     "#.#.#.#####.#.#", 
     "#.#.........#.#", 
     "#.#.#########.#", 
     "#.............#", 
     "###############"],

    ["#####################", 
     "#P..................#", 
     "#.#################.#", 
     "#.#.................#", 
     "#.#.#####.#######.#.#", 
     "#.#.#...........#.#.#", 
     "#.#.#.###########.#.#", 
     "#.#.#.#.........#.#.#", 
     "#.#.#.#.#####.#.#.#.#", 
     "#.#.#.#.#.....#.#.#.#", 
     "#.#.#.#.#.G.#.#.#.#.#", 
     "#.#.#.#.#...#.#.#.#.#", 
     "#.#.#.#.#####.#.#.#.#", 
     "#.#.#.#.......#.#.#.#", 
     "#.#.#.#########.#.#.#", 
     "#.#.#...........#.#.#", 
     "#.#.#############.#.#", 
     "#.#...............#.#", 
     "#.#################.#", 
     "#...................#", 
     "#####################"]
]


# ---------------------------------------------------------------------------
# Helper – parse a level definition
# ---------------------------------------------------------------------------
def parse_level(level_map: list[str]) -> tuple[int, int]:
    """Return (cols, rows) for the widest row in level_map."""
    cols = max(len(row) for row in level_map)
    rows = len(level_map)
    return cols, rows


def find_start(level_map: list[str]) -> tuple[int, int]:
    """Return (col, row) grid position of the 'P' tile."""
    for r, row in enumerate(level_map):
        for c, ch in enumerate(row):
            if ch == "P":
                return c, r
    raise ValueError("No player start 'P' found in level map.")


# ---------------------------------------------------------------------------
# Tile
# ---------------------------------------------------------------------------
class Tile:
    """A single cell on the grid."""

    EMPTY = "."
    WALL  = "#"
    GOAL  = "G"
    START = "P"   # treated as EMPTY after player is placed

    def __init__(self, kind: str, col: int, row: int):
        self.kind = kind if kind != self.START else self.EMPTY
        self.col  = col
        self.row  = row
        self.rect = pygame.Rect(col * TILE_SIZE, row * TILE_SIZE,
                                TILE_SIZE, TILE_SIZE)

    def draw(self, surface: pygame.Surface) -> None:
        if self.kind == self.WALL:
            pygame.draw.rect(surface, COL_WALL, self.rect)
            pygame.draw.rect(surface, COL_WALL_BORDER, self.rect, 2)
        elif self.kind == self.GOAL:
            pygame.draw.rect(surface, COL_GOAL, self.rect)
            inner = self.rect.inflate(-14, -14)
            pygame.draw.rect(surface, COL_GOAL_INNER, inner, 3)
            # small star / diamond marker
            cx, cy = self.rect.center
            pts = [(cx, cy - 12), (cx + 10, cy),
                   (cx, cy + 12), (cx - 10, cy)]
            pygame.draw.polygon(surface, COL_GOAL, pts)
        # EMPTY tiles – just the background colour (drawn by Level)

    @property
    def walkable(self) -> bool:
        return self.kind != self.WALL


# ---------------------------------------------------------------------------
# Level
# ---------------------------------------------------------------------------
class Level:
    """Holds the tile grid for one level."""

    def __init__(self, level_map: list[str]):
        self.map   = level_map
        self.cols, self.rows = parse_level(level_map)
        self.tiles: list[list[Tile]] = []
        self._build_grid()

    def _build_grid(self) -> None:
        self.tiles = []
        for r, row_str in enumerate(self.map):
            tile_row: list[Tile] = []
            for c in range(self.cols):
                ch = row_str[c] if c < len(row_str) else Tile.EMPTY
                tile_row.append(Tile(ch, c, r))
            self.tiles.append(tile_row)

    def get_tile(self, col: int, row: int) -> Tile | None:
        """Return the Tile at (col, row), or None if out of bounds."""
        if 0 <= row < self.rows and 0 <= col < self.cols:
            return self.tiles[row][col]
        return None

    def pixel_size(self) -> tuple[int, int]:
        return self.cols * TILE_SIZE, self.rows * TILE_SIZE

    def draw(self, surface: pygame.Surface) -> None:
        # Background
        surface.fill(COL_BG)
        # Tiles
        for row in self.tiles:
            for tile in row:
                tile.draw(surface)
        # Grid overlay
        w, h = self.pixel_size()
        for x in range(0, w + 1, TILE_SIZE):
            pygame.draw.line(surface, COL_GRID, (x, 0), (x, h))
        for y in range(0, h + 1, TILE_SIZE):
            pygame.draw.line(surface, COL_GRID, (0, y), (w, y))


# ---------------------------------------------------------------------------
# Player
# ---------------------------------------------------------------------------
class Player:
    """The player object; moves cell-by-cell."""

    def __init__(self, col: int, row: int, image: pygame.Surface | None):
        self.col   = col
        self.row   = row
        self.image = image   # None → use fallback square

    # -- Movement -----------------------------------------------------------
    def try_move(self, dcol: int, drow: int, level: "Level") -> bool:
        """
        Attempt to move by (dcol, drow).
        Returns True if the move succeeded.
        Extend here later for box-pushing, ice sliding, etc.
        """
        nc, nr = self.col + dcol, self.row + drow
        tile = level.get_tile(nc, nr)
        if tile is None or not tile.walkable:
            return False
        self.col, self.row = nc, nr
        return True

    def reset(self, col: int, row: int) -> None:
        self.col, self.row = col, row

    def on_goal(self, level: "Level") -> bool:
        tile = level.get_tile(self.col, self.row)
        return tile is not None and tile.kind == Tile.GOAL

    def draw(self, surface: pygame.Surface) -> None:
        rect = pygame.Rect(self.col * TILE_SIZE, self.row * TILE_SIZE,
                           TILE_SIZE, TILE_SIZE)
        if self.image:
            surface.blit(self.image, rect.topleft)
        else:
            # Fallback: blue rounded square with subtle shadow
            shadow = rect.move(3, 3)
            pygame.draw.rect(surface, (20, 40, 80), shadow, border_radius=10)
            pygame.draw.rect(surface, COL_PLAYER_FB, rect, border_radius=10)
            pygame.draw.rect(surface, (140, 190, 255), rect, 2,
                             border_radius=10)


# ---------------------------------------------------------------------------
# HUD
# ---------------------------------------------------------------------------
class HUD:
    """Draws level number and key hints."""

    def __init__(self, font: pygame.font.Font):
        self.font = font

    def draw(self, surface: pygame.Surface, level_index: int,
             total_levels: int) -> None:
        lines = [
            f"Level {level_index + 1} / {total_levels}",
            "Arrows: move   R: restart",
        ]
        padding = 8
        line_h  = self.font.get_height() + 4
        panel_w = 260
        panel_h = len(lines) * line_h + padding * 2

        # Semi-transparent panel
        panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        panel.fill(COL_HUD_BG)
        surface.blit(panel, (8, 8))

        for i, text in enumerate(lines):
            img = self.font.render(text, True, COL_HUD_TEXT)
            surface.blit(img, (8 + padding, 8 + padding + i * line_h))


# ---------------------------------------------------------------------------
# Game
# ---------------------------------------------------------------------------
class Game:
    """Top-level game controller."""

    def __init__(self):
        pygame.init()

        self.clock       = pygame.time.Clock()
        self.level_index = 0
        self.font        = pygame.font.SysFont("consolas", 16)
        self.hud         = HUD(self.font)

        # Load levels
        self.levels = [Level(lm) for lm in LEVELS]

        # Determine window size from the first (largest?) level
        self.screen = pygame.display.set_mode(self.current_level.pixel_size())

        # Load player sprite (fallback if missing)
        player_image = self._load_image("player.png",
                                        (TILE_SIZE, TILE_SIZE))

        # Place player
        sx, sy = find_start(LEVELS[self.level_index])
        self.player = Player(sx, sy, player_image)

        self.running = True

    # -- Asset helpers -------------------------------------------------------
    @staticmethod
    def _load_image(path: str,
                    size: tuple[int, int]) -> pygame.Surface | None:
        try:
            img = pygame.image.load(path).convert_alpha()
            return pygame.transform.scale(img, size)
        except FileNotFoundError:
            print(f"[INFO] '{path}' not found – using fallback graphic.")
            return None

    # -- Level management ---------------------------------------------------
    @property
    def current_level(self) -> Level:
        return self.levels[self.level_index]

    def _start_level(self, index: int) -> None:
        self.level_index = index % len(self.levels)
        
        # --- ДОБАВЬ ЭТИ ДВЕ СТРОЧКИ ---
        new_size = self.current_level.pixel_size()
        self.screen = pygame.display.set_mode(new_size) 
        # ------------------------------
        
        sx, sy = find_start(LEVELS[self.level_index])
        self.player.reset(sx, sy)

    def _restart_level(self) -> None:
        self._start_level(self.level_index)

    def _next_level(self) -> None:
        print(f"Level {self.level_index + 1} complete!")
        self._start_level(self.level_index + 1)

    # -- Event handling -----------------------------------------------------
    def _handle_events(self) -> None:
        MOVE_MAP = {
            pygame.K_UP:    ( 0, -1),
            pygame.K_DOWN:  ( 0,  1),
            pygame.K_LEFT:  (-1,  0),
            pygame.K_RIGHT: ( 1,  0),
        }
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False

                elif event.key == pygame.K_r:
                    self._restart_level()

                elif event.key in MOVE_MAP:
                    dc, dr = MOVE_MAP[event.key]
                    self.player.try_move(dc, dr, self.current_level)
                    # Check win condition after movement
                    if self.player.on_goal(self.current_level):
                        self._next_level()

    # -- Main loop ----------------------------------------------------------
    def run(self) -> None:
        while self.running:
            self._handle_events()

            # Draw
            self.current_level.draw(self.screen)
            self.player.draw(self.screen)
            self.hud.draw(self.screen, self.level_index, len(self.levels))

            pygame.display.flip()
            self.clock.tick(FPS)

        pygame.quit()
        sys.exit()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    Game().run()
