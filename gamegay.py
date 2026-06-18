from ursina import *
from ursina.shaders import lit_with_shadows_shader
import random
import math

# =====================================================
# ІНІЦІАЛІЗАЦІЯ ВІКНА
# =====================================================
app = Ursina()
window.title = 'Ultimate 3D Runner'
window.borderless = False
window.exit_button.visible = False
window.fps_counter.enabled = True

# =====================================================
# ГЛОБАЛЬНІ ЗМІННІ
# =====================================================
speed = 15
initial_speed = 15
score = 0
coins = 0
game_over = False
paused = False
in_menu = True                    # 🔴 НОВЕ: стан меню
in_controls = False               # 🔴 НОВЕ: стан екрану керування
lanes = [-2.5, 0, 2.5]
current_lane = 1
obstacles = []
coin_list = []
decorations = []
spawn_timer = 0
spawn_interval = 1.2
coin_spawn_timer = 0
difficulty_timer = 0

# =====================================================
# ЗВУКИ
# =====================================================
try:
    jump_sound = Audio('jump.mp3', loop=False, autoplay=False)
    jump_sound.volume = 0.5
except:
    jump_sound = None
    print("⚠️ jump.mp3 not found")

try:
    coin_sound = Audio('coin.mp3', loop=False, autoplay=False)
    coin_sound.volume = 0.6
except:
    coin_sound = None
    print("⚠️ coin.mp3 not found")

try:
    crash_sound = Audio('crush.mp3', loop=False, autoplay=False)
    crash_sound.volume = 0.7
except:
    crash_sound = None
    print("⚠️ crush.mp3 not found")

try:
    bg_music = Audio('back ground.mp3', loop=True, autoplay=True)
    bg_music.volume = 0.3
except:
    bg_music = None
    print("⚠️ back ground.mp3 not found")

# =====================================================
# ОСВІТЛЕННЯ ТА АТМОСФЕРА
# =====================================================
sun = DirectionalLight()
sun.look_at(Vec3(1, -1, -1))
sun.color = color.hsv(45, 0.3, 1.0)
ambient = AmbientLight(color=color.hsv(220, 0.2, 0.4))

try:
    sky = Sky(texture='sky_sunset')
except:
    sky = Sky(color=color.hsv(200, 0.4, 0.8))

scene.fog_color = color.hsv(200, 0.3, 0.7)
scene.fog_density = 0.015

# =====================================================
# МАТЕРІАЛИ
# =====================================================
player_shader = lit_with_shadows_shader
road_shader = lit_with_shadows_shader

# =====================================================
# ДОРОГА (сегментована)
# =====================================================
road_segments = []
SEGMENT_LENGTH = 20
NUM_SEGMENTS = 6

for i in range(NUM_SEGMENTS):
    seg = Entity(
        model='cube',
        color=color.hsv(0, 0, 0.25),
        scale=(8, 0.3, SEGMENT_LENGTH),
        position=(0, -0.15, i * SEGMENT_LENGTH),
        shader=road_shader,
        texture='white_cube'
    )
    road_segments.append(seg)

    for x in (-1.25, 1.25):
        Entity(
            parent=seg,
            model='cube',
            color=color.hsv(60, 0.3, 1.0),
            scale=(0.15, 0.32, 2),
            position=(x, 0.01, 0),
            unlit=True
        )

curbs = []
for i in range(NUM_SEGMENTS):
    for side in (-1, 1):
        curb = Entity(
            model='cube',
            color=color.hsv(30, 0.4, 0.4),
            scale=(0.5, 0.5, SEGMENT_LENGTH),
            position=(side * 4.25, 0.1, i * SEGMENT_LENGTH),
            shader=road_shader
        )
        curbs.append(curb)

# =====================================================
# ДЕКОРАЦІЇ
# =====================================================
def create_tree(x, z):
    tree = Entity(position=(x, 0, z))
    Entity(
        parent=tree,
        model='cube',
        color=color.brown,
        scale=(0.4, 2, 0.4),
        position=(0, 1, 0),
        shader=lit_with_shadows_shader
    )
    Entity(
        parent=tree,
        model='sphere',
        color=color.hsv(120, 0.7, 0.5),
        scale=(1.8, 1.8, 1.8),
        position=(0, 2.5, 0),
        shader=lit_with_shadows_shader
    )
    return tree

def create_building(x, z):
    height = random.uniform(3, 6)
    building = Entity(
        model='cube',
        color=color.hsv(random.randint(0, 360), 0.3, 0.5),
        scale=(2, height, 2),
        position=(x, height/2, z),
        shader=lit_with_shadows_shader
    )
    return building

for i in range(30):
    z = i * 8
    if random.random() > 0.3:
        decorations.append(create_tree(random.uniform(-7, -6), z + random.uniform(-2, 2)))
    else:
        decorations.append(create_building(random.uniform(-8, -6), z))
    if random.random() > 0.3:
        decorations.append(create_tree(random.uniform(6, 7), z + random.uniform(-2, 2)))
    else:
        decorations.append(create_building(random.uniform(6, 8), z))

# =====================================================
# ГРАВЕЦЬ
# =====================================================
player = Entity(
    model='cube',
    color=color.hsv(210, 0.9, 0.7),
    scale=(0.8, 1.2, 0.8),
    position=(0, 0.6, 0),
    shader=lit_with_shadows_shader
)

Entity(
    parent=player,
    model='cube',
    color=color.white,
    scale=(0.6, 0.25, 0.1),
    position=(0, 0.2, 0.41)
)
Entity(
    parent=player,
    model='cube',
    color=color.black,
    scale=(0.15, 0.15, 0.12),
    position=(-0.15, 0.2, 0.45)
)
Entity(
    parent=player,
    model='cube',
    color=color.black,
    scale=(0.15, 0.15, 0.12),
    position=(0.15, 0.2, 0.45)
)

player_shadow = Entity(
    model='circle',
    color=color.hsv(0, 0, 0, 0.4),
    scale=(1.2, 1, 1.2),
    position=(0, 0.02, 0),
    rotation_x=90,
    unlit=True
)

# =====================================================
# КАМЕРА
# =====================================================
camera.position = (0, 5.5, -10)
camera.rotation_x = 20
camera.fov = 75

# =====================================================
# 🎯 ГОЛОВНЕ МЕНЮ (НОВЕ)
# =====================================================
menu_elements = []

# Темний напівпрозорий фон меню
menu_bg = Entity(
    parent=camera.ui,
    model='quad',
    color=color.rgba(0, 0, 0, 180),
    scale=(1, 1),
    z=-1
)
menu_elements.append(menu_bg)

# Заголовок гри
title_text = Text(
    text='ULTIMATE 3D RUNNER',
    position=(0, 0.3),
    origin=(0, 0),
    scale=4,
    color=color.cyan
)
menu_elements.append(title_text)

# Підзаголовок
subtitle_text = Text(
    text='— Neon Streets Edition —',
    position=(0, 0.18),
    origin=(0, 0),
    scale=1.5,
    color=color.hsv(50, 0.8, 1.0)
)
menu_elements.append(subtitle_text)

# Функція створення кнопки меню
def create_menu_button(text, y_pos, on_click):
    btn = Button(
        text=text,
        color=color.hsv(210, 0.7, 0.4),
        highlight_color=color.hsv(210, 0.9, 0.7),
        pressed_color=color.hsv(210, 0.9, 0.9),
        hover_color=color.hsv(210, 0.8, 0.6),
        scale=(0.35, 0.08),
        position=(0, y_pos),
        parent=camera.ui
    )
    btn.on_click = on_click
    menu_elements.append(btn)
    return btn

# Функції для кнопок
def start_game():
    global in_menu
    in_menu = False
    hide_menu()
    print("🎮 Game started!")

def show_controls():
    global in_controls
    in_controls = True
    hide_menu()
    show_controls_screen()

def quit_game():
    print("👋 Quitting game...")
    application.quit()

def back_to_menu():
    global in_controls, in_menu
    in_controls = False
    in_menu = True
    hide_controls_screen()
    show_menu()

# Створення кнопок
btn_start = create_menu_button('▶  START GAME', 0.02, start_game)
btn_controls = create_menu_button('🎮  CONTROLS', -0.1, show_controls)
btn_quit = create_menu_button('✖  QUIT', -0.22, quit_game)

# =====================================================
# 📖 ЕКРАН КЕРУВАННЯ (НОВЕ)
# =====================================================
controls_elements = []

def show_controls_screen():
    # Фон
    bg = Entity(
        parent=camera.ui,
        model='quad',
        color=color.rgba(0, 0, 0, 200),
        scale=(1, 1),
        z=-1
    )
    controls_elements.append(bg)

    # Заголовок
    title = Text(
        text='CONTROLS',
        position=(0, 0.35),
        origin=(0, 0),
        scale=3,
        color=color.cyan
    )
    controls_elements.append(title)

    # Інструкції
    instructions = Text(
        text='A / ←       — Move Left\n'
             'D / →       — Move Right\n'
             'SPACE       — Jump\n'
             'R           — Restart\n\n'
             'Avoid red obstacles!\n'
             'Jump over purple ones!\n'
             'Collect coins for points!',
        position=(0, 0.1),
        origin=(0, 0),
        scale=1.8,
        color=color.white
    )
    controls_elements.append(instructions)

    # Кнопка назад
    btn_back = Button(
        text='←  BACK',
        color=color.hsv(0, 0.7, 0.5),
        highlight_color=color.hsv(0, 0.9, 0.7),
        scale=(0.25, 0.08),
        position=(0, -0.3),
        parent=camera.ui
    )
    btn_back.on_click = back_to_menu
    controls_elements.append(btn_back)

def hide_controls_screen():
    for el in controls_elements:
        destroy(el)
    controls_elements.clear()

# =====================================================
# ФУНКЦІЇ ДЛЯ МЕНЮ
# =====================================================
def show_menu():
    for el in menu_elements:
        el.enabled = True

def hide_menu():
    for el in menu_elements:
        el.enabled = False

# =====================================================
# UI — HUD (прихований спочатку)
# =====================================================
score_text = Text(
    text='SCORE: 0',
    position=(-0.85, 0.45),
    scale=1.8,
    color=color.white,
    background=color.rgba(0, 0, 0, 120),
    enabled=False   # 🔴 Приховано до початку гри
)
coins_text = Text(
    text='COINS: 0',
    position=(-0.85, 0.35),
    scale=1.8,
    color=color.yellow,
    background=color.rgba(0, 0, 0, 120),
    enabled=False
)
speed_text = Text(
    text='SPEED: 15',
    position=(0.7, 0.45),
    scale=1.8,
    color=color.cyan,
    background=color.rgba(0, 0, 0, 120),
    enabled=False
)

# =====================================================
# ЧАСТИНКИ
# =====================================================
particles = []

def spawn_particles(position, col, count=20):
    for _ in range(count):
        p = Entity(
            model='cube',
            color=col,
            scale=0.2,
            position=position,
            unlit=True
        )
        p.velocity = Vec3(
            random.uniform(-3, 3),
            random.uniform(2, 6),
            random.uniform(-3, 3)
        )
        p.lifetime = 1.0
        particles.append(p)

def update_particles(dt):
    for p in particles[:]:
        p.lifetime -= dt
        if p.lifetime <= 0:
            particles.remove(p)
            destroy(p)
            continue
        p.position += p.velocity * dt
        p.velocity.y -= 9.8 * dt
        p.scale *= 0.97

# =====================================================
# КЕРУВАННЯ
# =====================================================
def input(key):
    global current_lane, game_over, in_menu, in_controls

    # 🔴 Ігноруємо всі клавіші в меню
    if in_menu or in_controls:
        return

    if game_over:
        if key == 'r':
            restart()
        elif key == 'escape':
            show_menu()
            hide_game_over()
            global in_menu
            in_menu = True
        return

    if key in ('left arrow', 'a'):
        if current_lane > 0:
            current_lane -= 1
            player.animate_x(lanes[current_lane], duration=0.15, curve=curve.out_quad)
            player.animate_rotation_y(-15, duration=0.08)
            invoke(player.animate_rotation_y, 0, duration=0.15, delay=0.08)

    elif key in ('right arrow', 'd'):
        if current_lane < 2:
            current_lane += 1
            player.animate_x(lanes[current_lane], duration=0.15, curve=curve.out_quad)
            player.animate_rotation_y(15, duration=0.08)
            invoke(player.animate_rotation_y, 0, duration=0.15, delay=0.08)

    elif key == 'space':
        jump()

    elif key == 'escape':
        # Пауза — повернення в меню
        pause_to_menu()

def jump():
    if player.y <= 0.65:
        player.animate_y(2.8, duration=0.35, curve=curve.out_quad)
        invoke(player.animate_y, 0.6, duration=0.35,
               delay=0.35, curve=curve.in_quad)
        if jump_sound:
            jump_sound.play()

# =====================================================
# 🆕 ФУНКЦІЇ ДЛЯ ПОВЕРНЕННЯ В МЕНЮ
# =====================================================
def pause_to_menu():
    global in_menu, game_over
    in_menu = True
    game_over = False
    reset_game_state()
    show_menu()
    hide_hud()
    print("⏸️ Paused — back to menu")

def hide_game_over():
    for ui in game_over_ui:
        destroy(ui)
    game_over_ui.clear()

def hide_hud():
    score_text.enabled = False
    coins_text.enabled = False
    speed_text.enabled = False

def show_hud():
    score_text.enabled = True
    coins_text.enabled = True
    speed_text.enabled = True

def reset_game_state():
    global speed, score, coins, current_lane
    global spawn_timer, coin_spawn_timer, difficulty_timer, spawn_interval

    for obs in obstacles:
        destroy(obs)
    obstacles.clear()

    for coin in coin_list:
        destroy(coin)
    coin_list.clear()

    for p in particles:
        destroy(p)
    particles.clear()

    speed = initial_speed
    score = 0
    coins = 0
    current_lane = 1
    spawn_timer = 0
    coin_spawn_timer = 0
    difficulty_timer = 0
    spawn_interval = 1.2
    player.position = (0, 0.6, 0)
    player.rotation = (0, 0, 0)

    score_text.text = 'SCORE: 0'
    coins_text.text = 'COINS: 0'
    speed_text.text = f'SPEED: {int(speed)}'

# =====================================================
# СПАВН ПЕРЕШКОД
# =====================================================
def spawn_obstacle():
    global game_over
    if game_over or in_menu:
        return

    lane = random.choice(lanes)
    obstacle_type = random.choice(['low', 'low', 'high'])

    if obstacle_type == 'low':
        obs = Entity(
            model='cube',
            color=color.hsv(0, 0.9, 0.6),
            scale=(1.2, 1.2, 1.2),
            position=(lane, 0.6, 60),
            shader=lit_with_shadows_shader
        )
        obs.type = 'low'
    else:
        obs = Entity(
            model='cube',
            color=color.hsv(300, 0.9, 0.6),
            scale=(1.2, 2.5, 1.2),
            position=(lane, 1.25, 60),
            shader=lit_with_shadows_shader
        )
        obs.type = 'high'

    obs.rotation_speed = random.uniform(30, 90)
    obstacles.append(obs)

# =====================================================
# СПАВН МОНЕТОК
# =====================================================
def spawn_coin():
    global game_over
    if game_over or in_menu:
        return

    lane = random.choice(lanes)
    coin = Entity(
        model='sphere',
        color=color.hsv(50, 0.9, 1.0),
        scale=(0.6, 0.6, 0.2),
        position=(lane, 1.0, 60),
        shader=lit_with_shadows_shader,
        double_sided=True
    )
    coin.rotation_speed = 180
    coin_list.append(coin)

# =====================================================
# ІГРОВИЙ ЦИКЛ
# =====================================================
def update():
    global speed, score, coins, game_over, spawn_timer, coin_spawn_timer, difficulty_timer, spawn_interval

    # 🔴 Не оновлюємо гру якщо в меню
    if in_menu or game_over:
        return

    dt = time.dt
    update_particles(dt)

    difficulty_timer += dt
    if difficulty_timer >= 1.0:
        speed += 0.5
        difficulty_timer = 0

    for seg in road_segments:
        seg.z -= speed * dt
        if seg.z < -SEGMENT_LENGTH:
            seg.z += SEGMENT_LENGTH * NUM_SEGMENTS

    for curb in curbs:
        curb.z -= speed * dt
        if curb.z < -SEGMENT_LENGTH:
            curb.z += SEGMENT_LENGTH * NUM_SEGMENTS

    for dec in decorations:
        dec.z -= speed * dt
        if dec.z < -10:
            dec.z += 240

    player.rotation_z = math.sin(time.time() * 8) * 2

    player_shadow.x = player.x
    player_shadow.z = player.z
    shadow_scale = max(0.3, 1.2 - (player.y - 0.6) * 0.3)
    player_shadow.scale_x = shadow_scale
    player_shadow.scale_z = shadow_scale

    spawn_timer += dt
    coin_spawn_timer += dt

    if spawn_timer >= spawn_interval:
        spawn_obstacle()
        spawn_timer = 0
        spawn_interval = max(0.45, 1.2 - (speed - initial_speed) * 0.03)

    if coin_spawn_timer >= 1.8:
        spawn_coin()
        coin_spawn_timer = 0

    for obs in obstacles[:]:
        obs.z -= speed * dt
        obs.rotation_y += obs.rotation_speed * dt

        dz = abs(obs.z - player.z)
        dx = abs(obs.x - player.x)

        if dz < 0.9 and dx < 0.9:
            if obs.type == 'low':
                if abs(obs.y - player.y) < 1.0:
                    trigger_game_over(obs.position)
                    return
            else:
                if player.y < 1.8:
                    trigger_game_over(obs.position)
                    return

        if obs.z < -5:
            obstacles.remove(obs)
            destroy(obs)

    for coin in coin_list[:]:
        coin.z -= speed * dt
        coin.rotation_y += coin.rotation_speed * dt

        dz = abs(coin.z - player.z)
        dx = abs(coin.x - player.x)
        dy = abs(coin.y - player.y)

        if dz < 0.8 and dx < 0.8 and dy < 1.2:
            coins += 1
            score += 50
            spawn_particles(coin.position, color.yellow, 15)
            if coin_sound:
                coin_sound.play()
            coin_list.remove(coin)
            destroy(coin)
            continue

        if coin.z < -5:
            coin_list.remove(coin)
            destroy(coin)

    score += dt * speed * 0.5
    score_text.text = f'SCORE: {int(score)}'
    coins_text.text = f'COINS: {coins}'
    speed_text.text = f'SPEED: {int(speed)}'

# =====================================================
# GAME OVER
# =====================================================
game_over_ui = []

def trigger_game_over(position):
    global game_over
    game_over = True

    spawn_particles(position, color.red, 40)
    spawn_particles(player.position, color.orange, 30)

    if crash_sound:
        crash_sound.play()

    if bg_music:
        bg_music.stop()

    original_pos = camera.position
    camera.animate('position', original_pos + Vec3(0.5, 0.5, 0), duration=0.05)
    invoke(camera.animate, 'position', original_pos - Vec3(0.5, 0.5, 0),
           duration=0.05, delay=0.05)
    invoke(camera.animate, 'position', original_pos,
           duration=0.05, delay=0.1)

    panel = Entity(
        parent=camera.ui,
        model='quad',
        color=color.rgba(0, 0, 0, 190),
        scale=(1, 1),
        z=-1
    )
    game_over_ui.append(panel)

    title = Text(
        text='GAME OVER',
        position=(0, 0.2),
        origin=(0, 0),
        scale=3.5,
        color=color.red
    )
    game_over_ui.append(title)

    stats = Text(
        text=f'Score: {int(score)}\nCoins: {coins}\nSpeed: {int(speed)}',
        position=(0, 0.0),
        origin=(0, 0),
        scale=2,
        color=color.white
    )
    game_over_ui.append(stats)

    # 🔴 Додано кнопку "Menu"
    btn_menu = Button(
        text='🏠  MAIN MENU',
        color=color.hsv(210, 0.7, 0.4),
        highlight_color=color.hsv(210, 0.9, 0.7),
        scale=(0.3, 0.07),
        position=(0, -0.15),
        parent=camera.ui
    )
    btn_menu.on_click = go_to_menu_from_gameover
    game_over_ui.append(btn_menu)

    hint = Text(
        text='[ R ] Restart   |   [ ESC ] Menu',
        position=(0, -0.28),
        origin=(0, 0),
        scale=1.5,
        color=color.cyan
    )
    game_over_ui.append(hint)

def go_to_menu_from_gameover():
    global in_menu
    in_menu = True
    hide_game_over()
    reset_game_state()
    show_menu()
    hide_hud()
    if bg_music:
        bg_music.play()
    print("🏠 Back to main menu")

# =====================================================
# ПЕРЕЗАПУСК
# =====================================================
def restart():
    global speed, score, coins, game_over, current_lane
    global spawn_timer, coin_spawn_timer, difficulty_timer, spawn_interval

    for obs in obstacles:
        destroy(obs)
    obstacles.clear()

    for coin in coin_list:
        destroy(coin)
    coin_list.clear()

    for p in particles:
        destroy(p)
    particles.clear()

    for ui in game_over_ui:
        destroy(ui)
    game_over_ui.clear()

    speed = initial_speed
    score = 0
    coins = 0
    current_lane = 1
    spawn_timer = 0
    coin_spawn_timer = 0
    difficulty_timer = 0
    spawn_interval = 1.2
    player.position = (0, 0.6, 0)
    player.rotation = (0, 0, 0)
    game_over = False

    score_text.text = 'SCORE: 0'
    coins_text.text = 'COINS: 0'
    speed_text.text = f'SPEED: {int(speed)}'

    if bg_music:
        bg_music.play()

    print("🔄 Game restarted!")

# =====================================================
# 🎯 ОНОВЛЕНА ФУНКЦІЯ СТАРТУ ГРИ
# =====================================================
def start_game():
    global in_menu
    in_menu = False
    hide_menu()
    show_hud()
    print("🎮 Game started!")

# =====================================================
# СТАРТ
# =====================================================
print("=" * 50)
print("ULTIMATE 3D RUNNER — WITH MAIN MENU")
print("=" * 50)
print("Main menu will appear on startup")
print("Press START to begin playing")
print("=" * 50)

app.run()