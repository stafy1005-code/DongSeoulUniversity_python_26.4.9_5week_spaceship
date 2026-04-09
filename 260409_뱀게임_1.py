import math
import random
import sys
from collections import deque

import pygame

# =========================
# 기본 설정
# =========================
CELL_SIZE = 15                 # 맵은 2배, 대신 셀을 줄여 화면에 맞춤
GRID_WIDTH = 60                # 가로 2배
GRID_HEIGHT = 40               # 세로 2배

TOP_UI_HEIGHT = 56
BOTTOM_UI_HEIGHT = 70

PLAY_WIDTH = CELL_SIZE * GRID_WIDTH
PLAY_HEIGHT = CELL_SIZE * GRID_HEIGHT

SCREEN_WIDTH = PLAY_WIDTH
SCREEN_HEIGHT = TOP_UI_HEIGHT + PLAY_HEIGHT + BOTTOM_UI_HEIGHT

FPS = 60

APPLE_COUNT = 18
BOT_COUNT = 6

PLAYER_BASE_INTERVAL = 0.11
PLAYER_FAST_INTERVAL = 0.032
PLAYER_DRAINED_INTERVAL = 0.22
PLAYER_ACCEL_TIME = 0.85

BOT_FAST_INTERVAL = 0.095
BOT_SINGLE_STEP_INTERVAL = 0.24   # 방전 상태에서 한 칸씩 느리게

STAMINA_MAX = 100.0
STAMINA_RECOVER_PER_SEC = 48.0    # 기존보다 2배 빠르게 회복
STAMINA_DRAIN_PER_SEC = 12.0      # 기존보다 3배 느리게 감소

# 방향
UP = (0, -1)
DOWN = (0, 1)
LEFT = (-1, 0)
RIGHT = (1, 0)
DIRECTIONS = [UP, DOWN, LEFT, RIGHT]

DIR_KEY_MAP = {
    pygame.K_UP: UP,
    pygame.K_DOWN: DOWN,
    pygame.K_LEFT: LEFT,
    pygame.K_RIGHT: RIGHT,
}

# 색상
WHITE = (245, 245, 245)
BLACK = (18, 18, 18)
UI_DARK = (22, 27, 31)
UI_LIGHT = (235, 238, 240)
GRAY = (176, 183, 189)
YELLOW = (255, 210, 85)

PLAYER_HEAD = (76, 230, 145)
PLAYER_BODY_A = (54, 194, 118)
PLAYER_BODY_B = (31, 133, 83)

BOT_PALETTES = [
    ((255, 146, 84), (222, 113, 48), (171, 76, 30)),
    ((98, 178, 255), (64, 139, 222), (38, 96, 176)),
    ((211, 116, 255), (171, 75, 220), (120, 44, 170)),
    ((255, 107, 138), (214, 70, 101), (158, 44, 69)),
    ((255, 210, 94), (225, 170, 48), (166, 121, 28)),
    ((107, 233, 207), (56, 194, 164), (31, 140, 118)),
]

APPLE_RED = (205, 48, 48)
APPLE_RED_DARK = (150, 30, 30)
APPLE_HIGHLIGHT = (255, 185, 185)
LEAF_GREEN = (68, 165, 82)
STEM_BROWN = (110, 72, 42)

BAR_BG = (60, 66, 72)
BAR_FILL = (255, 194, 74)
BAR_FRAME = (240, 240, 240)

GAME_OVER_OVERLAY = (0, 0, 0, 145)
SHADOW_COLOR = (0, 0, 0, 55)


class Snake:
    def __init__(self, name, body, direction, head_color, body_a, body_b, is_bot=False):
        self.name = name
        self.body = body[:]
        self.direction = direction
        self.head_color = head_color
        self.body_color_a = body_a
        self.body_color_b = body_b
        self.is_bot = is_bot
        self.alive = True

        self.move_timer = 0.0
        self.hold_time = 0.0
        self.held_dir = None
        self.next_dir = direction

        self.max_stamina = STAMINA_MAX
        self.stamina = STAMINA_MAX
        self.recharge_mode = False

        self.hold_step_count = 0

    @property
    def head(self):
        return self.body[0]

    @property
    def tail(self):
        return self.body[-1]


class SnakeGame:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("정지형 뱀게임 - 확장 맵 + 봇 AI")
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.clock = pygame.time.Clock()

        self.font_small = pygame.font.SysFont("malgungothic", 18)
        self.font_medium = pygame.font.SysFont("malgungothic", 24, bold=True)
        self.font_large = pygame.font.SysFont("malgungothic", 42, bold=True)

        self.play_background = self.make_natural_background()
        self.reset()

    # =========================
    # 초기화
    # =========================
    def reset(self):
        self.game_over = False
        self.player_score = 0

        self.snakes = []

        # 플레이어
        px = GRID_WIDTH // 2
        py = GRID_HEIGHT // 2
        player_body = [(px, py), (px - 1, py), (px - 2, py), (px - 3, py)]
        self.player = Snake(
            "PLAYER", player_body, RIGHT,
            PLAYER_HEAD, PLAYER_BODY_A, PLAYER_BODY_B, is_bot=False
        )
        self.snakes.append(self.player)

        occupied = set(player_body)

        # 봇 생성
        for i in range(BOT_COUNT):
            body, direction = self.spawn_snake_body(occupied, length=4)
            palette = BOT_PALETTES[i % len(BOT_PALETTES)]
            bot = Snake(
                f"BOT_{i+1}", body, direction,
                palette[0], palette[1], palette[2], is_bot=True
            )
            self.snakes.append(bot)
            occupied.update(body)

        self.apples = []
        while len(self.apples) < APPLE_COUNT:
            self.apples.append(self.spawn_apple())

    def spawn_snake_body(self, occupied, length=4):
        attempts = 0
        while True:
            attempts += 1
            direction = random.choice(DIRECTIONS)
            dx, dy = direction

            head_x = random.randint(3, GRID_WIDTH - 4)
            head_y = random.randint(3, GRID_HEIGHT - 4)

            body = []
            valid = True
            for i in range(length):
                bx = head_x - dx * i
                by = head_y - dy * i
                cell = (bx, by)
                if not (0 <= bx < GRID_WIDTH and 0 <= by < GRID_HEIGHT):
                    valid = False
                    break
                if cell in occupied:
                    valid = False
                    break
                body.append(cell)

            if valid:
                return body, direction

            if attempts > 2000:
                raise RuntimeError("봇 생성 공간이 부족합니다.")

    def spawn_apple(self):
        occupied = set()
        for snake in self.snakes:
            if snake.alive:
                occupied.update(snake.body)
        occupied.update(self.apples)

        while True:
            pos = (
                random.randint(0, GRID_WIDTH - 1),
                random.randint(0, GRID_HEIGHT - 1)
            )
            if pos not in occupied:
                return pos

    # =========================
    # 배경
    # =========================
    def make_natural_background(self):
        base = pygame.Surface((PLAY_WIDTH, PLAY_HEIGHT))
        base.fill((71, 107, 63))

        overlay = pygame.Surface((PLAY_WIDTH, PLAY_HEIGHT), pygame.SRCALPHA)

        for _ in range(70):
            w = random.randint(120, 340)
            h = random.randint(80, 220)
            x = random.randint(-50, PLAY_WIDTH - 30)
            y = random.randint(-40, PLAY_HEIGHT - 30)
            color = random.choice([
                (58, 95, 50, 42),
                (88, 125, 76, 36),
                (102, 136, 86, 28),
                (92, 82, 55, 22),
                (45, 78, 42, 34),
            ])
            pygame.draw.ellipse(overlay, color, (x, y, w, h))

        for _ in range(10):
            points = []
            base_y = random.randint(40, PLAY_HEIGHT - 40)
            amp = random.randint(18, 40)
            phase = random.uniform(0, math.pi * 2)
            for x in range(-50, PLAY_WIDTH + 50, 24):
                y = base_y + int(math.sin(x * 0.015 + phase) * amp)
                points.append((x, y))
            pygame.draw.lines(
                overlay,
                random.choice([
                    (35, 74, 35, 35),
                    (115, 102, 67, 22),
                    (51, 86, 44, 28),
                ]),
                False,
                points,
                random.randint(14, 28)
            )

        for _ in range(14):
            x = random.randint(0, PLAY_WIDTH)
            y = random.randint(0, PLAY_HEIGHT)
            r = random.randint(70, 170)
            pygame.draw.circle(overlay, (255, 255, 220, 8), (x, y), r)

        base.blit(overlay, (0, 0))
        return base

    # =========================
    # 입력
    # =========================
    def handle_keydown(self, key):
        if key == pygame.K_r:
            self.reset()
            return

        if key in DIR_KEY_MAP and not self.game_over and self.player.alive:
            new_dir = DIR_KEY_MAP[key]
            if self.is_reverse_direction(self.player.direction, new_dir) and len(self.player.body) > 1:
                return

            self.player.held_dir = new_dir
            self.player.direction = new_dir
            self.player.hold_time = 0.0
            self.player.move_timer = 0.0
            self.player.hold_step_count = 0

            # 첫 입력은 무료 1칸 이동
            moved = self.process_single_immediate_player_step()
            if moved:
                self.player.hold_step_count = 1

    def handle_keyup(self, key):
        if key in DIR_KEY_MAP:
            released = DIR_KEY_MAP[key]
            if self.player.held_dir == released:
                self.player.held_dir = None
                self.player.hold_time = 0.0
                self.player.move_timer = 0.0
                self.player.hold_step_count = 0

    def process_single_immediate_player_step(self):
        if not self.player.alive or self.game_over:
            return False

        old_head = self.player.head
        self.resolve_step([self.player], {self.player: self.player.direction})
        return self.player.alive and self.player.head != old_head

    # =========================
    # 업데이트
    # =========================
    def update(self, dt):
        if self.game_over:
            return

        movers = []
        planned_dirs = {}

        # =========================
        # 플레이어
        # =========================
        if self.player.alive and self.player.held_dir is not None:
            self.player.hold_time += dt
            self.player.move_timer += dt
        else:
            self.player.hold_time = 0.0
            self.player.move_timer = 0.0
            self.player.hold_step_count = 0
            if self.player.alive:
                self.recover_stamina(self.player, dt)

        if self.player.alive and self.player.held_dir is not None:
            if self.player.stamina <= 0:
                # 방전 시 느린 연속 이동
                player_interval = PLAYER_DRAINED_INTERVAL
            else:
                accel_ratio = min(self.player.hold_time / PLAYER_ACCEL_TIME, 1.0)
                stamina_ratio = self.player.stamina / self.player.max_stamina
                usable_accel = accel_ratio * stamina_ratio
                player_interval = (
                    PLAYER_BASE_INTERVAL
                    - (PLAYER_BASE_INTERVAL - PLAYER_FAST_INTERVAL) * usable_accel
                )

            if self.player.move_timer >= player_interval:
                self.player.move_timer -= player_interval
                movers.append(self.player)
                planned_dirs[self.player] = self.player.held_dir

                # 2칸째 이상의 연속 이동부터만 에너지 감소
                if self.player.stamina > 0 and self.player.hold_step_count >= 1:
                    self.drain_stamina(self.player, STAMINA_DRAIN_PER_SEC * player_interval)

                self.player.hold_step_count += 1

        # =========================
        # 봇
        # =========================
        for snake in self.snakes:
            if not snake.alive or not snake.is_bot:
                continue

            snake.move_timer += dt

            if snake.recharge_mode:
                # 방전 후 회복 모드: 한 칸씩만 느리게 이동
                self.recover_stamina(snake, dt)
                bot_interval = BOT_SINGLE_STEP_INTERVAL

                if snake.stamina >= snake.max_stamina:
                    snake.stamina = snake.max_stamina
                    snake.recharge_mode = False
            else:
                # 가속 사용 모드
                bot_interval = BOT_FAST_INTERVAL

                if snake.stamina > 0:
                    self.drain_stamina(snake, STAMINA_DRAIN_PER_SEC * dt)
                    if snake.stamina <= 0:
                        snake.stamina = 0
                        snake.recharge_mode = True
                        bot_interval = BOT_SINGLE_STEP_INTERVAL
                else:
                    snake.stamina = 0
                    snake.recharge_mode = True
                    bot_interval = BOT_SINGLE_STEP_INTERVAL

            if snake.move_timer >= bot_interval:
                snake.move_timer -= bot_interval
                bot_dir = self.choose_bot_direction(snake)
                if bot_dir is not None:
                    movers.append(snake)
                    planned_dirs[snake] = bot_dir

        if movers:
            self.resolve_step(movers, planned_dirs)

        if not self.player.alive:
            self.game_over = True

        while len(self.apples) < APPLE_COUNT:
            self.apples.append(self.spawn_apple())

    # =========================
    # AI
    # =========================
    def choose_bot_direction(self, bot):
        if not bot.alive:
            return None

        occupied_after_tail_vacate = self.build_occupied_map_for_next_step(bot)
        enemy_head_danger = self.build_enemy_head_danger(bot)

        candidate_info = []
        head = bot.head

        for d in DIRECTIONS:
            if self.is_reverse_direction(bot.direction, d) and len(bot.body) > 1:
                continue

            nxt = (head[0] + d[0], head[1] + d[1])

            # 1순위: 즉사 회피
            if not (0 <= nxt[0] < GRID_WIDTH and 0 <= nxt[1] < GRID_HEIGHT):
                continue
            if nxt in occupied_after_tail_vacate:
                continue

            danger_score = 0
            if nxt in enemy_head_danger:
                danger_score += 1000

            # 2순위: 가장 가까운 사과까지의 거리
            dist = self.distance_to_nearest_apple(nxt, bot, first_step=nxt)
            if dist is None:
                dist = 10**9

            # 공간 넓이
            flood = self.flood_fill_space(nxt, bot, limit=180)

            # 근처 빈칸 수
            local_open = 0
            for nd in DIRECTIONS:
                nn = (nxt[0] + nd[0], nxt[1] + nd[1])
                if 0 <= nn[0] < GRID_WIDTH and 0 <= nn[1] < GRID_HEIGHT and nn not in occupied_after_tail_vacate:
                    local_open += 1

            score_tuple = (
                danger_score,   # 낮을수록 좋음
                dist,           # 낮을수록 좋음
                -flood,         # 높을수록 좋음
                -local_open     # 높을수록 좋음
            )
            candidate_info.append((score_tuple, d))

        if candidate_info:
            candidate_info.sort(key=lambda x: x[0])
            return candidate_info[0][1]

        return bot.direction

    def build_occupied_map_for_next_step(self, perspective_snake):
        occupied = set()

        for snake in self.snakes:
            if not snake.alive:
                continue
            occupied.update(snake.body)

        occupied.discard(perspective_snake.head)
        occupied.discard(perspective_snake.tail)
        return occupied

    def build_enemy_head_danger(self, perspective_snake):
        danger = set()
        for snake in self.snakes:
            if not snake.alive or snake is perspective_snake:
                continue
            hx, hy = snake.head
            danger.add((hx, hy))
            for d in DIRECTIONS:
                danger.add((hx + d[0], hy + d[1]))
        return danger

    def distance_to_nearest_apple(self, start, perspective_snake, first_step=None):
        apples = set(self.apples)
        if start in apples:
            return 0

        blocked = self.build_occupied_map_for_pathfinding(perspective_snake, first_step)
        if start in blocked:
            return None

        q = deque([(start, 0)])
        visited = {start}

        while q:
            pos, dist = q.popleft()
            for d in DIRECTIONS:
                nxt = (pos[0] + d[0], pos[1] + d[1])
                if nxt in visited:
                    continue
                if not (0 <= nxt[0] < GRID_WIDTH and 0 <= nxt[1] < GRID_HEIGHT):
                    continue
                if nxt in blocked:
                    continue
                if nxt in apples:
                    return dist + 1
                visited.add(nxt)
                q.append((nxt, dist + 1))
        return None

    def build_occupied_map_for_pathfinding(self, perspective_snake, first_step=None):
        blocked = set()
        for snake in self.snakes:
            if not snake.alive:
                continue
            blocked.update(snake.body)

        blocked.discard(perspective_snake.head)
        blocked.discard(perspective_snake.tail)

        if first_step is not None:
            blocked.discard(first_step)

        return blocked

    def flood_fill_space(self, start, perspective_snake, limit=180):
        blocked = self.build_occupied_map_for_pathfinding(perspective_snake, first_step=start)
        if start in blocked:
            return 0

        q = deque([start])
        visited = {start}

        while q and len(visited) < limit:
            pos = q.popleft()
            for d in DIRECTIONS:
                nxt = (pos[0] + d[0], pos[1] + d[1])
                if nxt in visited:
                    continue
                if not (0 <= nxt[0] < GRID_WIDTH and 0 <= nxt[1] < GRID_HEIGHT):
                    continue
                if nxt in blocked:
                    continue
                visited.add(nxt)
                q.append(nxt)
        return len(visited)

    # =========================
    # 이동 / 충돌
    # =========================
    def resolve_step(self, movers, planned_dirs):
        movers = [s for s in movers if s.alive and s in planned_dirs]
        if not movers:
            return

        next_heads = {}
        will_eat = {}

        for snake in movers:
            direction = planned_dirs[snake]
            hx, hy = snake.head
            nx = hx + direction[0]
            ny = hy + direction[1]
            next_heads[snake] = (nx, ny)
            will_eat[snake] = (nx, ny) in self.apples

        dead = set()

        # 벽 충돌
        for snake, nxt in next_heads.items():
            if not (0 <= nxt[0] < GRID_WIDTH and 0 <= nxt[1] < GRID_HEIGHT):
                dead.add(snake)

        # 전체 점유맵
        occupied = set()
        for snake in self.snakes:
            if not snake.alive:
                continue
            occupied.update(snake.body)

        # 먹지 않는 이동 뱀 꼬리는 비워짐
        vacated_tails = set()
        for snake in movers:
            if snake in dead:
                continue
            if not will_eat[snake]:
                vacated_tails.add(snake.tail)

        occupied_after_vacate = occupied - vacated_tails

        for snake in movers:
            occupied_after_vacate.discard(snake.head)

        # 몸통 / 정지 머리 충돌
        for snake, nxt in next_heads.items():
            if snake in dead:
                continue
            if nxt in occupied_after_vacate:
                dead.add(snake)

        # 같은 칸으로 머리 충돌
        cell_to_snakes = {}
        for snake, nxt in next_heads.items():
            if snake in dead:
                continue
            cell_to_snakes.setdefault(nxt, []).append(snake)

        for _, snakes_here in cell_to_snakes.items():
            if len(snakes_here) >= 2:
                dead.update(snakes_here)

        # 머리 교차 충돌
        for a in movers:
            if a in dead:
                continue
            for b in movers:
                if a is b or b in dead:
                    continue
                if next_heads[a] == b.head and next_heads[b] == a.head:
                    dead.add(a)
                    dead.add(b)

        # 사망 처리
        for snake in dead:
            snake.alive = False

        # 생존자 이동
        eaten_apples = []
        for snake in movers:
            if not snake.alive:
                continue

            snake.direction = planned_dirs[snake]
            new_head = next_heads[snake]
            snake.body.insert(0, new_head)

            if will_eat[snake]:
                if new_head in self.apples:
                    eaten_apples.append(new_head)
                if snake is self.player:
                    self.player_score += 10
            else:
                snake.body.pop()

        for apple in eaten_apples:
            if apple in self.apples:
                self.apples.remove(apple)

        while len(self.apples) < APPLE_COUNT:
            self.apples.append(self.spawn_apple())

    def is_reverse_direction(self, old_dir, new_dir):
        return old_dir[0] == -new_dir[0] and old_dir[1] == -new_dir[1]

    def cell_to_center(self, pos):
        x, y = pos
        return (
            x * CELL_SIZE + CELL_SIZE // 2,
            TOP_UI_HEIGHT + y * CELL_SIZE + CELL_SIZE // 2
        )
        
    def recover_stamina(self, snake, dt):
        snake.stamina += STAMINA_RECOVER_PER_SEC * dt
        if snake.stamina > snake.max_stamina:
            snake.stamina = snake.max_stamina

    def drain_stamina(self, snake, amount):
        snake.stamina -= amount
        if snake.stamina < 0:
            snake.stamina = 0

    # =========================
    # 그리기
    # =========================
    def draw_playfield(self):
        self.screen.blit(self.play_background, (0, TOP_UI_HEIGHT))
        pygame.draw.rect(
            self.screen,
            (18, 24, 18),
            (0, TOP_UI_HEIGHT, PLAY_WIDTH, PLAY_HEIGHT),
            4
        )

    def draw_apples(self):
        for ax, ay in self.apples:
            cx = ax * CELL_SIZE + CELL_SIZE // 2
            cy = TOP_UI_HEIGHT + ay * CELL_SIZE + CELL_SIZE // 2

            shadow_surf = pygame.Surface((CELL_SIZE + 10, CELL_SIZE + 10), pygame.SRCALPHA)
            pygame.draw.ellipse(shadow_surf, (0, 0, 0, 45), (3, 6, CELL_SIZE - 1, CELL_SIZE - 6))
            self.screen.blit(shadow_surf, (cx - CELL_SIZE // 2 - 2, cy - CELL_SIZE // 2 + 2))

            radius = max(4, CELL_SIZE // 2 - 2)
            pygame.draw.circle(self.screen, APPLE_RED_DARK, (cx, cy + 1), radius)
            pygame.draw.circle(self.screen, APPLE_RED, (cx, cy), radius - 1)
            pygame.draw.circle(self.screen, APPLE_HIGHLIGHT, (cx - 2, cy - 3), max(2, radius // 4))
            pygame.draw.line(self.screen, STEM_BROWN, (cx, cy - 5), (cx + 1, cy - 10), 2)

            leaf_rect = pygame.Rect(0, 0, 8, 5)
            leaf_rect.center = (cx + 5, cy - 8)
            pygame.draw.ellipse(self.screen, LEAF_GREEN, leaf_rect)

    def draw_snake(self, snake):
        if not snake.alive or not snake.body:
            return

        centers = [self.cell_to_center(pos) for pos in snake.body]
        radii = []

        head_radius = max(5, int(CELL_SIZE * 0.48))
        tail_radius = max(3, int(CELL_SIZE * 0.22))
        count = max(1, len(centers) - 1)

        for i in range(len(centers)):
            t = i / count
            r = int(head_radius * (1 - t) + tail_radius * t)
            radii.append(max(3, r))

        shadow = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        for i in range(len(centers) - 1):
            p1 = (centers[i][0] + 1, centers[i][1] + 3)
            p2 = (centers[i + 1][0] + 1, centers[i + 1][1] + 3)
            width = max(2, radii[i] * 2)
            pygame.draw.line(shadow, SHADOW_COLOR, p1, p2, width)
        for i, c in enumerate(centers):
            pygame.draw.circle(shadow, SHADOW_COLOR, (c[0] + 1, c[1] + 3), radii[i])
        self.screen.blit(shadow, (0, 0))

        for i in range(len(centers) - 1, 0, -1):
            t = i / max(1, len(centers) - 1)
            color = (
                int(snake.body_color_a[0] * (1 - t) + snake.body_color_b[0] * t),
                int(snake.body_color_a[1] * (1 - t) + snake.body_color_b[1] * t),
                int(snake.body_color_a[2] * (1 - t) + snake.body_color_b[2] * t),
            )
            pygame.draw.line(self.screen, color, centers[i - 1], centers[i], max(2, radii[i - 1] * 2))

        for i in range(len(centers) - 1, 0, -1):
            t = i / max(1, len(centers) - 1)
            color = (
                int(snake.body_color_a[0] * (1 - t) + snake.body_color_b[0] * t),
                int(snake.body_color_a[1] * (1 - t) + snake.body_color_b[1] * t),
                int(snake.body_color_a[2] * (1 - t) + snake.body_color_b[2] * t),
            )
            pygame.draw.circle(self.screen, color, centers[i], radii[i])

        head_center = centers[0]
        head_radius = radii[0] + 1
        pygame.draw.circle(self.screen, snake.head_color, head_center, head_radius)

        dx, dy = snake.direction
        forward = pygame.Vector2(dx, dy)
        if forward.length() == 0:
            forward = pygame.Vector2(1, 0)
        forward = forward.normalize()
        side = pygame.Vector2(-forward.y, forward.x)

        eye_offset_front = forward * (head_radius * 0.35)
        eye_offset_side = side * (head_radius * 0.40)

        left_eye = pygame.Vector2(head_center) + eye_offset_front + eye_offset_side
        right_eye = pygame.Vector2(head_center) + eye_offset_front - eye_offset_side

        eye_r = max(2, int(head_radius * 0.24))
        pupil_r = max(1, int(eye_r * 0.5))

        pygame.draw.circle(self.screen, WHITE, (int(left_eye.x), int(left_eye.y)), eye_r)
        pygame.draw.circle(self.screen, WHITE, (int(right_eye.x), int(right_eye.y)), eye_r)

        pupil_offset = forward * (eye_r * 0.45)
        left_pupil = left_eye + pupil_offset
        right_pupil = right_eye + pupil_offset

        pygame.draw.circle(self.screen, BLACK, (int(left_pupil.x), int(left_pupil.y)), pupil_r)
        pygame.draw.circle(self.screen, BLACK, (int(right_pupil.x), int(right_pupil.y)), pupil_r)

    def draw_top_ui(self):
        pygame.draw.rect(self.screen, UI_DARK, (0, 0, SCREEN_WIDTH, TOP_UI_HEIGHT))

        score_text = self.font_medium.render(f"점수: {self.player_score}", True, UI_LIGHT)
        self.screen.blit(score_text, (12, 13))

        alive_bots = sum(1 for s in self.snakes if s.is_bot and s.alive)
        info_text = self.font_small.render(
            f"맵: {GRID_WIDTH}x{GRID_HEIGHT} | 봇 생존: {alive_bots}/{BOT_COUNT} | 방향키 홀드 = 가속",
            True, GRAY
        )
        info_rect = info_text.get_rect(midright=(SCREEN_WIDTH - 12, TOP_UI_HEIGHT // 2))
        self.screen.blit(info_text, info_rect)

    def draw_bottom_ui(self):
        pygame.draw.rect(
            self.screen,
            UI_DARK,
            (0, TOP_UI_HEIGHT + PLAY_HEIGHT, SCREEN_WIDTH, BOTTOM_UI_HEIGHT)
        )

        label = self.font_small.render("가속 에너지", True, UI_LIGHT)
        self.screen.blit(label, (12, TOP_UI_HEIGHT + PLAY_HEIGHT + 7))

        bar_x = 12
        bar_y = TOP_UI_HEIGHT + PLAY_HEIGHT + 32
        bar_w = SCREEN_WIDTH - 24
        bar_h = 22

        pygame.draw.rect(self.screen, BAR_BG, (bar_x, bar_y, bar_w, bar_h), border_radius=10)

        fill_ratio = self.player.stamina / self.player.max_stamina
        fill_w = int(bar_w * fill_ratio)
        if fill_w > 0:
            pygame.draw.rect(self.screen, BAR_FILL, (bar_x, bar_y, fill_w, bar_h), border_radius=10)

        pygame.draw.rect(self.screen, BAR_FRAME, (bar_x, bar_y, bar_w, bar_h), 2, border_radius=10)

        value_text = self.font_small.render(
            f"{int(self.player.stamina)} / {int(self.player.max_stamina)}",
            True,
            UI_LIGHT
        )
        value_rect = value_text.get_rect(midright=(SCREEN_WIDTH - 14, TOP_UI_HEIGHT + PLAY_HEIGHT + 17))
        self.screen.blit(value_text, value_rect)

    def draw_game_over(self):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill(GAME_OVER_OVERLAY)
        self.screen.blit(overlay, (0, 0))

        title = self.font_large.render("GAME OVER", True, YELLOW)
        score_text = self.font_medium.render(f"최종 점수: {self.player_score}", True, WHITE)
        retry_text = self.font_medium.render("R 키를 누르면 다시 시작", True, WHITE)

        self.screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 40)))
        self.screen.blit(score_text, score_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 10)))
        self.screen.blit(retry_text, retry_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 56)))

    def draw(self):
        self.screen.fill(BLACK)
        self.draw_playfield()
        self.draw_apples()

        for snake in self.snakes:
            self.draw_snake(snake)

        self.draw_top_ui()
        self.draw_bottom_ui()

        if self.game_over:
            self.draw_game_over()

        pygame.display.flip()

    # =========================
    # 실행
    # =========================
    def run(self):
        while True:
            dt = self.clock.tick(FPS) / 1000.0

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        pygame.quit()
                        sys.exit()
                    self.handle_keydown(event.key)

                elif event.type == pygame.KEYUP:
                    self.handle_keyup(event.key)

            self.update(dt)
            self.draw()


if __name__ == "__main__":
    SnakeGame().run()