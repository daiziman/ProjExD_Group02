from minipy3dr.fps import FPSConfig

CONFIG = FPSConfig(
    # 画面
    screen_size=(960, 600),
    render_scale=0.6,
    fov=78.0,
    walk_speed=4.2,
    sprint_speed=6.0,  # Shift押下時の速度
    mouse_look=True,  # トラックパッド環境ならFalse
    use_qe_turn=False,  # Q/Eをリーンに使うので旋回からは外す(旋回は矢印キーのみ)
    max_health=100,
    start_ammo=40,
    # 見 た目のテーマ
    floor_colors=((42, 42, 44), (52, 48, 43)),
    wall_colors=((96, 82, 76), (126, 108, 90)),
    lamp_color=(255, 214, 120),
)
JUMP_VELOCITY = 5.2  # 跳ぶ初速
GRAVITY = 13.0  # 重力加速度
