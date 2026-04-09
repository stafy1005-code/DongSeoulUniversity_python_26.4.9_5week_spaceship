import math
import random
import sys
import pygame

# =========================
# 기본 설정
# =========================
WIDTH, HEIGHT = 1000, 700
FPS = 60

BG_COLOR = (18, 18, 24)
GRID_COLOR = (30, 30, 38)
SNAKE_HEAD_COLOR = (60, 220, 120)
SNAKE_BODY_COLOR = (40, 180, 95)
FOOD_COLOR = (255, 80, 80)
TEXT_COLOR = (240, 240, 240)

INITIAL_SPEED = 4.0
MAX_SPEED = 7.0
TURN_SPEED = 0.16
SEGMENT_SPACING = 14
INITIAL_LENGTH = 18
GROW_AMOUNT = 5
FOOD_RADIUS = 9
HEAD_RADIUS = 14
BODY_RADIUS = 11

# =========================
# 유틸
# =========================
def clamp(value, min_value, max_value):
    return max(min_value, min(value, max_value))

def distance(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])

def angle_lerp(current, target, amount):
    diff = (target - current + math.pi) % (2 * math.pi) - math.pi
    return current + diff * amount

def draw_text(surface, text, size, x, y, color=TEXT_COLOR, center=False):
    font = pygame.font.SysFont("malgungothic", size)
    img = font.render(text, True, color)
    rect = img.get_rect()
    if center:
        rect.center = (x, y)
    else:
        rect.topleft = (x, y)
    surface.blit(img, rect)

# =========================
# 먹이
# =========================
class Food:
    def __init__(self):
        self.respawn([])

    def respawn(self, snake_body):
        while True:
            self.x = random.randint(40, WIDTH - 40)
            self.y = random.randint(40, HEIGHT - 40)

            ok = True
            for pos in snake_body:
                if distance((self.x, self.y), pos) < 40:
                    ok = False
                    break

            if ok:
                break

    def draw(self, surface):
        pygame.draw.circle(surface, FOOD_COLOR, (int(self.x), int(self.y)), FOOD_RADIUS)
        pygame.draw.circle(surface, (255, 180, 180), (int(self.x - 3), int(self.y - 3)), 3)

# =========================
# 뱀
# =========================
class Snake:
    def __init__(self):
        self.reset()

    def reset(self):
        self.head_x = WIDTH // 2
        self.head_y = HEIGHT // 2
        self.angle = 0
        self.speed = INITIAL_SPEED
        self.score = 0
        self.alive = True

        self.body = []
        for i in range(INITIAL_LENGTH):
            self.body.append((self.head_x - i * SEGMENT_SPACING, self.head_y))

    def update(self, mouse_pos):
        if not self.alive:
            return

        mx, my = mouse_pos

        # 마우스 방향 계산
        target_angle = math.atan2(my - self.head_y, mx - self.head_x)
        self.angle = angle_lerp(self.angle, target_angle, TURN_SPEED)

        # 이동
        self.head_x += math.cos(self.angle) * self.speed
        self.head_y += math.sin(self.angle) * self.speed

        # 몸통 갱신
        self.body.insert(0, (self.head_x, self.head_y))
        while len(self.body) > INITIAL_LENGTH + self.score * GROW_AMOUNT:
            self.body.pop()

        # 속도 증가
        self.speed = min(MAX_SPEED, INITIAL_SPEED + self.score * 0.12)

        # 벽 충돌
        if (
            self.head_x < HEAD_RADIUS
            or self.head_x > WIDTH - HEAD_RADIUS
            or self.head_y < HEAD_RADIUS
            or self.head_y > HEIGHT - HEAD_RADIUS
        ):
            self.alive = False

        # 자기 몸 충돌
        # 머리 바로 뒤는 제외하고 검사
        for segment in self.body[10:]:
            if distance((self.head_x, self.head_y), segment) < BODY_RADIUS:
                self.alive = False
                break

    def eat_food(self, food):
        if distance((self.head_x, self.head_y), (food.x, food.y)) < HEAD_RADIUS + FOOD_RADIUS:
            self.score += 1
            food.respawn(self.body)

    def draw(self, surface):
        # 몸통
        for i in range(len(self.body) - 1, 0, -1):
            x, y = self.body[i]
            radius = max(6, BODY_RADIUS - i // 25)
            pygame.draw.circle(surface, SNAKE_BODY_COLOR, (int(x), int(y)), radius)

        # 머리
        pygame.draw.circle(surface, SNAKE_HEAD_COLOR, (int(self.head_x), int(self.head_y)), HEAD_RADIUS)

        # 눈
        eye_offset_x = math.cos(self.angle + math.pi / 2) * 5
        eye_offset_y = math.sin(self.angle + math.pi / 2) * 5
        forward_x = math.cos(self.angle) * 5
        forward_y = math.sin(self.angle) * 5

        left_eye = (
            int(self.head_x + forward_x + eye_offset_x),
            int(self.head_y + forward_y + eye_offset_y),
        )
        right_eye = (
            int(self.head_x + forward_x - eye_offset_x),
            int(self.head_y + forward_y - eye_offset_y),
        )

        pygame.draw.circle(surface, (255, 255, 255), left_eye, 4)
        pygame.draw.circle(surface, (255, 255, 255), right_eye, 4)
        pygame.draw.circle(surface, (20, 20, 20), left_eye, 2)
        pygame.draw.circle(surface, (20, 20, 20), right_eye, 2)

# =========================
# 배경 그리드
# =========================
def draw_grid(surface):
    for x in range(0, WIDTH, 40):
        pygame.draw.line(surface, GRID_COLOR, (x, 0), (x, HEIGHT))
    for y in range(0, HEIGHT, 40):
        pygame.draw.line(surface, GRID_COLOR, (0, y), (WIDTH, y))

# =========================
# 메인
# =========================
def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("마우스로 이동하는 뱀게임")
    clock = pygame.time.Clock()

    snake = Snake()
    food = Food()

    running = True
    while running:
        clock.tick(FPS)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r and not snake.alive:
                    snake.reset()
                    food.respawn(snake.body)

        mouse_pos = pygame.mouse.get_pos()

        if snake.alive:
            snake.update(mouse_pos)
            snake.eat_food(food)

        # 그리기
        screen.fill(BG_COLOR)
        draw_grid(screen)
        food.draw(screen)
        snake.draw(screen)

        draw_text(screen, f"점수: {snake.score}", 28, 20, 20)
        draw_text(screen, "마우스를 따라 이동 / 벽 또는 몸에 닿으면 게임 오버", 22, 20, 55)

        if not snake.alive:
            draw_text(screen, "게임 오버", 52, WIDTH // 2, HEIGHT // 2 - 20, center=True)
            draw_text(screen, "R 키를 누르면 다시 시작", 28, WIDTH // 2, HEIGHT // 2 + 30, center=True)

        pygame.display.flip()

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()