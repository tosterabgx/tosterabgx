import curses
import random
import time
import copy

HEIGHT = 20
WIDTH = 10

FIGURES = [
    [[1, 1, 1, 1]],                # I
    [[1, 1], [1, 1]],             # O
    [[0, 1, 0], [1, 1, 1]],       # T
    [[1, 1, 0], [0, 1, 1]],       # S
    [[0, 1, 1], [1, 1, 0]],       # Z
    [[1, 0, 0], [1, 1, 1]],       # J
    [[0, 0, 1], [1, 1, 1]],       # L
]

def rotate(shape):
    return [list(row)[::-1] for row in zip(*shape)]

def check_collision(field, shape, offset):
    off_x, off_y = offset
    for y, row in enumerate(shape):
        for x, cell in enumerate(row):
            if cell:
                px = x + off_x
                py = y + off_y
                if px < 0 or px >= WIDTH or py >= HEIGHT or (py >= 0 and field[py][px]):
                    return True
    return False

def merge(field, shape, offset):
    off_x, off_y = offset
    for y, row in enumerate(shape):
        for x, cell in enumerate(row):
            if cell:
                field[y + off_y][x + off_x] = cell

def clear_lines(field):
    new_field = [row for row in field if any(cell == 0 for cell in row)]
    lines_cleared = HEIGHT - len(new_field)
    return [[0]*WIDTH for _ in range(lines_cleared)] + new_field, lines_cleared

def draw_border(win):
    for y in range(HEIGHT + 2):
        win.addstr(y, 0, "#")
        win.addstr(y, WIDTH + 1, "#")
    for x in range(WIDTH + 2):
        win.addstr(0, x, "#")
        win.addstr(HEIGHT + 1, x, "#")

def draw(win, field, shape, offset, score):
    win.erase()
    draw_border(win)
    for y in range(HEIGHT):
        line_chars = []
        for x in range(WIDTH):
            cell = field[y][x]
            sy = y - offset[1]
            sx = x - offset[0]
            shape_cell = 0
            if 0 <= sy < len(shape) and 0 <= sx < len(shape[0]):
                shape_cell = shape[sy][sx]
            if shape_cell or cell:
                line_chars.append("█")
            else:
                line_chars.append(" ")
        win.addstr(y + 1, 1, "".join(line_chars))
    win.addstr(1, WIDTH + 3, f"Score: {score}")
    win.noutrefresh()

def evaluate_field(field):
    aggregate_height = 0
    holes = 0
    bumpiness = 0

    heights = []
    for x in range(WIDTH):
        column_height = 0
        block_found = False
        column_holes = 0
        for y in range(HEIGHT):
            if field[y][x]:
                if not block_found:
                    column_height = HEIGHT - y
                    block_found = True
            else:
                if block_found:
                    column_holes += 1
        heights.append(column_height)
        holes += column_holes

    aggregate_height = sum(heights)
    for i in range(len(heights)-1):
        bumpiness += abs(heights[i] - heights[i+1])

    return aggregate_height, holes, bumpiness

def evaluate_position(field, shape, offset):
    field_copy = copy.deepcopy(field)
    merge(field_copy, shape, offset)
    field_copy, lines_cleared = clear_lines(field_copy)

    aggregate_height, holes, bumpiness = evaluate_field(field_copy)

    score = (-0.510066 * aggregate_height) + (0.760666 * lines_cleared) - (0.35663 * bumpiness) - (0.484483 * holes)
    return score, field_copy, lines_cleared

def generate_rotations(figure):
    rotations = []
    rotated = figure
    for _ in range(4):
        rotations.append(rotated)
        rotated = rotate(rotated)
    unique_rotations = []
    for r in rotations:
        if r not in unique_rotations:
            unique_rotations.append(r)
    return unique_rotations

def best_move_recursive(field, figures, depth=0, max_depth=6):
    if depth == max_depth or not figures:
        aggregate_height, holes, bumpiness = evaluate_field(field)
        return (-0.510066 * aggregate_height) - (0.484483 * holes) - (0.35663 * bumpiness), None, None, None

    current_figure = figures[0]
    next_figures = figures[1:]

    best_score = -float('inf')
    best_shape = None
    best_x = None
    best_y = None

    rotations = generate_rotations(current_figure)

    for shape in rotations:
        shape_width = len(shape[0])
        for x in range(-shape_width + 1, WIDTH):
            y = 0
            while not check_collision(field, shape, (x, y)):
                y += 1
            y -= 1
            if y < 0:
                continue

            score_after, field_after, lines = evaluate_position(field, shape, (x, y))

            future_score, _, _, _ = best_move_recursive(field_after, next_figures, depth+1, max_depth)

            total_score = score_after + future_score

            if total_score > best_score:
                best_score = total_score
                best_shape = shape
                best_x = x
                best_y = y

    return best_score, best_shape, best_x, best_y

def main(stdscr):
    curses.curs_set(0)
    stdscr.nodelay(True)
    stdscr.timeout(0)  # максимально быстрый цикл

    field = [[0 for _ in range(WIDTH)] for _ in range(HEIGHT)]
    score = 0

    upcoming_figures = [random.choice(FIGURES) for _ in range(6)]

    current = upcoming_figures.pop(0)
    offset = [WIDTH // 2 - len(current[0]) // 2, 0]

    last_fall = time.time()
    fall_interval = 0.5

    target_score = 100_000

    while True:
        now = time.time()
        if now - last_fall > fall_interval:
            offset[1] += 1
            if check_collision(field, current, offset):
                offset[1] -= 1
                merge(field, current, offset)
                field, lines = clear_lines(field)
                score += lines * 100

                upcoming_figures.append(random.choice(FIGURES))

                if upcoming_figures:
                    current = upcoming_figures.pop(0)
                else:
                    current = random.choice(FIGURES)

                next_five = upcoming_figures[:5]
                search_figures = [current] + next_five
                _, best_shape, best_x, best_y = best_move_recursive(field, search_figures, depth=0, max_depth=len(search_figures))

                if best_shape is None:
                    stdscr.addstr(HEIGHT // 2, WIDTH // 2 - 4, "GAME OVER")
                    stdscr.refresh()
                    time.sleep(3)
                    break

                current = best_shape
                offset = [best_x, best_y]

                if check_collision(field, current, offset):
                    stdscr.addstr(HEIGHT // 2, WIDTH // 2 - 4, "GAME OVER")
                    stdscr.refresh()
                    time.sleep(3)
                    break

            last_fall = now

        draw(stdscr, field, current, offset, score)
        curses.doupdate()

        if score >= target_score:
            stdscr.addstr(HEIGHT // 2, WIDTH // 2 - 3, "YOU WIN!")
            stdscr.refresh()
            time.sleep(3)
            break

if __name__ == "__main__":
    curses.wrapper(main)
