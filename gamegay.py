from ursina import *
from ursina.shaders import lit_with_shadows_shader, fresnel_shader, triplanar_shader
import random
import math

# =====================================================
# ІНІЦІАЛІЗАЦІЯ ВІКНА
# =====================================================
app = Ursina()
window.title = 'Ultimate 3D Runner — Enhanced'
window.borderless = False
window.exit_button.visible = False
window.fps_counter.enabled = True
window.color = color.hsv(210, 0.4, 0.3)   # Темно-синій фон

# =====================================================
# ГЛОБАЛЬНІ ЗМІННІ
# =====================================================
speed = 15
initial_speed = 15
score = 0
coins = 0
game_over = False
lanes = [-2.5, 0, 2.5]
current_lane = 1
obstacles = []
coin_list = []
decorations = []
particles = []
dust_particles = []
spawn_timer = 0
spawn_interval = 1.2
coin_spawn_timer = 0
difficulty_timer = 0
dust_timer = 0

# =====================================================
# ПОСТ-ПРОЦЕСИНГ (Bloom + SSAO) — покращує всю картинку
# =====================================================
try:
    from ursina.shaders import ssao
    # Вмикаємо SSAO для м'яких тіней у закутках
    # (якщо не спрацює — пропускаємо)
except Exception as e:
    print(f"SSAO skipped: {e}")

try:
    from ursina import bloom
    bloom.settings.intensity = 0.3
    bloom.settings.threshold = 0.7
except Exception as e:
    print(f"Bloom skipped: {e}")

# =====================================================
# ОСВІТЛЕННЯ (покращене)
# =====================================================
# Основне сонце — тепле
sun = DirectionalLight()
sun.look_at(Vec3(1, -1.5, -1))
sun.color = color.hsv(40, 0.25, 1.0)
sun._node.node().setShadowCaster(True, 2048, 2048)   # великі тіні

# Заповнююче світло (fill light) — холодне з протилежного боку
fill_light = DirectionalLight()
fill_light.look_at(Vec3(-1, -0.5, 1))
fill_light.color = color.hsv(220, 0.3, 0.4)

# Ambient — м'який
ambient = AmbientLight(color=color.hsv(220, 0.15, 0.45))

# Небо — градієнт (процедурний захід)
sky = Sky(
    texture='sky_sunset',
    color=color.hsv(20, 0.3, 0.9)
)

# Атмосферний туман
scene.fog_color = color.hsv(20, 0.25, 0.75)
scene.fog_density = 0.012

# =====================================================
# ДОРОГА (покращена)
# =====================================================
road_segments = []
SEGMENT_LENGTH = 20
NUM_SEGMENTS = 6

for i in range(NUM_SEGMENTS):
    # Основна дорога — темніший асфальт
    seg = Entity(
        model='cube',
        color=color.hsv(0, 0, 0.22),
        scale=(8, 0.3, SEGMENT_LENGTH),
        position=(0, -0.15, i * SEGMENT_LENGTH),
        shader=lit_with_shadows_shader,
        texture='white_cube'
    )
    road_segments.append(seg)

    # Пунктирні розділові лінії (замість суцільних)
    for x in (-1.25, 1.25):
        for dz in range(-9, 10, 4):   # пунктир кожні 4 одиниці
            Entity(
                parent=seg,
                model='cube',
                color=color.hsv(50, 0.8, 1.0),   # яскраво-жовті
                scale=(0.15, 0.32, 1.5),
                position=(x, 0.01, dz),
                unlit=True
            )

# Бордюри — з текстурою
curbs = []
for i in range(NUM_SEGMENTS):
    for side in (-1, 1):
        curb = Entity(
            model='cube',
            color=color.hsv(30, 0.3, 0.45),
            scale=(0.5, 0.5, SEGMENT_LENGTH),
            position=(side * 4.25, 0.1, i * SEGMENT_LENGTH),
            shader=lit_with_shadows_shader
        )
        curbs.append(curb)

# Трава по боках дороги
grass_segments = []
for i in range(NUM_SEGMENTS):
    for side in (-1, 1):
        grass = Entity(
            model='cube',
            color=color.hsv(110, 0.55, 0.35),
            scale=(15, 0.1, SEGMENT_LENGTH),
            position=(side * 12, -0.2, i * SEGMENT_LENGTH),
            shader=lit_with_shadows_shader
        )
        grass_segments.append(grass)

# =====================================================
# ДЕКОРАЦІЇ (розширені — дерева, будівлі, ліхтарі)
# =====================================================
def create_tree(x, z):
    tree = Entity(position=(x, 0, z))
    Entity(
        parent=tree,
        model='cube',
        color=color.hsv(25, 0.7, 0.35),
        scale=(0.4, 2.2, 0.4),
        position=(0, 1.1, 0),
        shader=lit_with_shadows_shader
    )
    # Крона — трохи витягнута
    Entity(
        parent=tree,
        model='sphere',
        color=color.hsv(110, 0.65, 0.45),
        scale=(2.0, 2.4, 2.0),
        position=(0, 2.8, 0),
        shader=lit_with_shadows_shader
    )
    return tree

def create_building(x, z):
    height = random.uniform(4, 8)
    hue = random.randint(0, 360)
    building = Entity(
        model='cube',
        color=color.hsv(hue, 0.25, 0.55),
        scale=(2.5, height, 2.5),
        position=(x, height/2, z),
        shader=lit_with_shadows_shader
    )
    # Вікна (жовті квадратики)
    for wy in range(1, int(height), 2):
        for wx in (-0.7, 0.7):
            Entity(
                parent=building,
                model='cube',
                color=color.hsv(50, 0.7, 1.0),
                scale=(0.4, 0.4, 0.05),
                position=(wx, wy - height/2, 1.28),
                unlit=True
            )
    return building

def create_lamp(x, z):
    """Ліхтар освітлення"""
    lamp = Entity(position=(x, 0, z))
    # Стовп
    Entity(
        parent=lamp,
        model='cube',
        color=color.hsv(0, 0, 0.2),
        scale=(0.15, 3.5, 0.15),
        position=(0, 1.75, 0),
        shader=lit_with_shadows_shader
    )
    # Ліхтар (світиться!)
    bulb = Entity(
        parent=lamp,
        model='sphere',
        color=color.hsv(45, 0.6, 1.0),
        scale=(0.5, 0.5, 0.5),
        position=(0, 3.6, 0),
        unlit=True
    )
    # Точкове світло від ліхтаря
    light = PointLight(
        parent=lamp,
        position=(0, 3.5, 0),
        color=color.hsv(45, 0.5, 0.8),
        attenuation=Vec3(1, 0.1, 0.02)
    )
    return lamp

# Генеруємо декорації
for i in range(30):
    z = i * 8
    # Ліва сторона
    r = random.random()
    if r > 0.5:
        decorations.append(create_tree(random.uniform(-7, -6), z + random.uniform(-2, 2)))
    elif r > 0.2:
        decorations.append(create_building(random.uniform(-9, -6.5), z))
    else:
        decorations.append(create_lamp(-5.2, z))
    # Права сторона
    r = random.random()
    if r > 0.5:
        decorations.append(create_tree(random.uniform(6, 7), z + random.uniform(-2, 2)))
    elif r > 0.2:
        decorations.append(create_building(random.uniform(6.5, 9), z))
    else:
        decorations.append(create_lamp(5.2, z))

# =====================================================
# ГРАВЕЦЬ (покращений — з rim-light)
# =====================================================
player = Entity(
    model='cube',
    color=color.hsv(210, 0.9, 0.75),
    scale=(0.8, 1.2, 0.8),
    position=(0, 0.6, 0),
    shader=fresnel_shader   # rim-light по контуру!
)
player.shader = fresnel_shader

# Очі
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

# Тінь під гравцем
player_shadow = Entity(
    model='circle',
    color=color.hsv(0, 0, 0, 0.5),
    scale=(1.2, 1, 1.2),
    position=(0, 0.02, 0),
    rotation_x=90,
    unlit=True
)

# Світло від гравця (ледь помітне)
player_light = PointLight(
    parent=player,
    position=(0, 0.5, 0),
    color=color.hsv(210, 0.7, 0.6),
    attenuation=Vec3(1, 0.3, 0.05)
)

# =====================================================
# КАМЕРА
# =====================================================
camera.position = (0, 5.5, -10)
camera.rotation_x = 20
camera.fov = 75

# =====================================================
# UI — HUD
# =====================================================
score_text = Text(
    text='SCORE: 0',
    position=(-0.85, 0.45),
    scale=1.8,
    color=color.white,
    background=color.rgba(0, 0, 0, 140)
)
coins_text = Text(
    text='COINS: 0',
    position=(-0.85, 0.35),
    scale=1.8,
    color=color.yellow,
    background=color.rgba(0, 0, 0, 140)
)
speed_text = Text(
    text='SPEED: 15',
    position=(0.7, 0.45),
    scale=1.8,
    color=color.cyan,
    background=color.rgba(0, 0, 0, 140)
)

# =====================================================
# ЧАСТИНКИ (вибухи)
# =====================================================
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

def spawn_dust():
    """Пил з-під ніг гравця"""
    if player.y > 0.7:   # тільки коли на землі
        return
    for _ in range(2):
        p = Entity(
            model='sphere',
            color=color.hsv(30, 0.2, 0.7, 0.6),
            scale=0.15,
            position=(player.x + random.uniform(-0.3, 0.3),
                      0.1,
                      player.z - 0.5),
            unlit=True
        )
        p.velocity = Vec3(
            random.uniform(-0.5, 0.5),
            random.uniform(0.3, 0.8),
            random.uniform(-1.5, -0.5)
        )
        p.lifetime = 0.6
        dust_particles.append(p)

def update_particles(dt):
    for lst in (particles, dust_particles):
        for p in lst[:]:
            p.lifetime -= dt
            if p.lifetime <= 0:
                lst.remove(p)
                destroy(p)
                continue
            p.position += p.velocity * dt
            p.velocity.y -= 9.8 * dt
            p.scale *= 0.96

# =====================================================
# КЕРУВАННЯ
# =====================================================
def input(key):
    global current_lane, game_over

    if game_over:
        if key == 'r':
            restart()
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

def jump():
    if player.y <= 0.65:
        player.animate_y(2.8, duration=0.35, curve=curve.out_quad)
        invoke(player.animate_y, 0.6, duration=0.35,
               delay=0.35, curve=curve.in_quad)

# =====================================================
# СПАВН ПЕРЕШКОД (зі свіченням)
# =====================================================
def spawn_obstacle():
    global game_over
    if game_over:
        return

    lane = random.choice(lanes)
    obstacle_type = random.choice(['low', 'low', 'high'])

    if obstacle_type == 'low':
        obs = Entity(
            model='cube',
            color=color.hsv(0, 0.85, 0.7),
            scale=(1.2, 1.2, 1.2),
            position=(lane, 0.6, 60),
            shader=lit_with_shadows_shader
        )
        obs.type = 'low'
    else:
        obs = Entity(
            model='cube',
            color=color.hsv(290, 0.85, 0.7),
            scale=(1.2, 2.5, 1.2),
            position=(lane, 1.25, 60),
            shader=lit_with_shadows_shader
        )
        obs.type = 'high'

    # Внутрішнє свічення (emissive-ефект через point light)
    obs.light = PointLight(
        parent=obs,
        color=obs.color,
        attenuation=Vec3(1, 0.2, 0.05)
    )
    obs.rotation_speed = random.uniform(40, 100)
    obstacles.append(obs)

# =====================================================
# СПАВН МОНЕТОК (покращений)
# =====================================================
def spawn_coin():
    global game_over
    if game_over:
        return

    lane = random.choice(lanes)
    coin = Entity(
        model='sphere',
        color=color.hsv(50, 0.9, 1.0),
        scale=(0.5, 0.5, 0.15),
        position=(lane, 1.2, 60),
        shader=lit_with_shadows_shader,
        double_sided=True
    )
    # Золотий блиск
    coin.light = PointLight(
        parent=coin,
        color=color.hsv(50, 0.8, 0.9),
        attenuation=Vec3(1, 0.3, 0.08)
    )
    coin.rotation_speed = 200
    coin.bob_offset = random.uniform(0, math.pi * 2)   # для "плавання"
    coin_list.append(coin)

# =====================================================
# ІГРОВИЙ ЦИКЛ
# =====================================================
def update():
    global speed, score, coins, game_over, spawn_timer, coin_spawn_timer
    global difficulty_timer, spawn_interval, dust_timer

    if game_over:
        return

    dt = time.dt
    update_particles(dt)

    # Складність
    difficulty_timer += dt
    if difficulty_timer >= 1.0:
        speed += 0.5
        difficulty_timer = 0

    # Рух дороги
    for seg in road_segments:
        seg.z -= speed * dt
        if seg.z < -SEGMENT_LENGTH:
            seg.z += SEGMENT_LENGTH * NUM_SEGMENTS

    for curb in curbs:
        curb.z -= speed * dt
        if curb.z < -SEGMENT_LENGTH:
            curb.z += SEGMENT_LENGTH * NUM_SEGMENTS

    for grass in grass_segments:
        grass.z -= speed * dt
        if grass.z < -SEGMENT_LENGTH:
            grass.z += SEGMENT_LENGTH * NUM_SEGMENTS

    # Рух декорацій
    for dec in decorations:
        dec.z -= speed * dt
        if dec.z < -10:
            dec.z += 240

    # Анімація гравця
    player.rotation_z = math.sin(time.time() * 8) * 2

    # Тінь під гравцем
    player_shadow.x = player.x
    player_shadow.z = player.z
    shadow_scale = max(0.3, 1.2 - (player.y - 0.6) * 0.3)
    player_shadow.scale_x = shadow_scale
    player_shadow.scale_z = shadow_scale

    # Пил з-під ніг
    dust_timer += dt
    if dust_timer >= 0.08:
        spawn_dust()
        dust_timer = 0

    # Спавн
    spawn_timer += dt
    coin_spawn_timer += dt

    if spawn_timer >= spawn_interval:
        spawn_obstacle()
        spawn_timer = 0
        spawn_interval = max(0.45, 1.2 - (speed - initial_speed) * 0.03)

    if coin_spawn_timer >= 1.5:
        spawn_coin()
        coin_spawn_timer = 0

    # Перешкоди
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

    # Монетки (з "плаванням" вгору-вниз)
    for coin in coin_list[:]:
        coin.z -= speed * dt
        coin.rotation_y += coin.rotation_speed * dt
        # Легке плавання
        coin.y = 1.2 + math.sin(time.time() * 3 + coin.bob_offset) * 0.15

        dz = abs(coin.z - player.z)
        dx = abs(coin.x - player.x)
        dy = abs(coin.y - player.y)

        if dz < 0.8 and dx < 0.8 and dy < 1.2:
            coins += 1
            score += 50
            spawn_particles(coin.position, color.yellow, 15)
            coin_list.remove(coin)
            destroy(coin)
            continue

        if coin.z < -5:
            coin_list.remove(coin)
            destroy(coin)

    # Рахунок
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

    spawn_particles(position, color.red, 50)
    spawn_particles(player.position, color.orange, 40)
    spawn_particles(player.position, color.yellow, 20)

    # Тряска камери
    original_pos = camera.position
    camera.animate('position', original_pos + Vec3(0.5, 0.5, 0), duration=0.05)
    invoke(camera.animate, 'position', original_pos - Vec3(0.5, 0.5, 0),
           duration=0.05, delay=0.05)
    invoke(camera.animate, 'position', original_pos,
           duration=0.05, delay=0.1)

    # UI
    panel = Entity(
        parent=camera.ui,
        model='quad',
        color=color.rgba(0, 0, 0, 200),
        scale=(1, 1),
        z=-1
    )
    game_over_ui.append(panel)

    title = Text(
        text='GAME OVER',
        position=(0, 0.15),
        origin=(0, 0),
        scale=3.5,
        color=color.red
    )
    game_over_ui.append(title)

    stats = Text(
        text=f'Score: {int(score)}\nCoins: {coins}\nSpeed: {int(speed)}',
        position=(0, -0.05),
        origin=(0, 0),
        scale=2,
        color=color.white
    )
    game_over_ui.append(stats)

    hint = Text(
        text='Press [ R ] to restart',
        position=(0, -0.3),
        origin=(0, 0),
        scale=1.8,
        color=color.cyan
    )
    game_over_ui.append(hint)

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

    for p in particles + dust_particles:
        destroy(p)
    particles.clear()
    dust_particles.clear()

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

    print("Game restarted!")

# =====================================================
# СТАРТ
# =====================================================
print("=" * 50)
print("ULTIMATE 3D RUNNER — ENHANCED")
print("=" * 50)
print("A / Left  — move left")
print("D / Right — move right")
print("SPACE     — jump")
print("R         — restart")
print("=" * 50)

app.run()