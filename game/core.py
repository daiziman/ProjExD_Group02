"""
"""

from __future__ import annotations

import math
import random
from collections.abc import Sequence

from minipy3dr import Mesh, Vector3
from minipy3dr.fps import Feature, FPSConfig, FPSGame, GameObject, Player  # noqa: F401

from game.config import CONFIG, GRAVITY, JUMP_VELOCITY

Color = tuple[int, int, int]


def shade(color: Color, factor: float) -> Color:
    return (
        max(0, min(255, int(color[0] * factor))),
        max(0, min(255, int(color[1] * factor))),
        max(0, min(255, int(color[2] * factor))),
    )


class Game(FPSGame):

    def __init__(self, map_data: list[str], features: Sequence[Feature] = (), title: str = "FPS") -> None:
        super().__init__(map_data=map_data, features=features, title=title, config=CONFIG)
        self._hit_marker = 0.0
        self.on("target_hit", self._on_any_target_hit)

        self._jump_offset = 0.0 
        self._jump_velocity = 0.0
        self._grounded = True
        self._lean = 0.0
        self._lean_dx = 0.0
        self._lean_dz = 0.
        self._spawn_barrels()
        self._spawn_covers()
        self._decorate_world()
        self._schedule_lamp_flicker()

    def _on_any_target_hit(self, data: dict) -> None:
        """どこかのターゲットに弾が当たったら照準を一瞬光らせる。"""
        self._hit_marker = 0.18

    def update_player_extra(self, dt: float) -> None:
        """毎フレーム、基本の移動処理の後に呼ばれる: ジャンプとリーンを処理する。"""
        self._update_jump(dt)
        self._update_lean(dt)

    def _update_jump(self, dt: float) -> None:
        """Spaceで跳ぶ。空中では重力で落ちていき、着地すると再び跳べる。"""
        app = self.app
        if app.key("space") and self._grounded:
            self._jump_velocity = JUMP_VELOCITY
            self._grounded = False
        self._jump_velocity -= GRAVITY * dt
        self._jump_offset += self._jump_velocity * dt
        if self._jump_offset <= 0.0:  # 着地
            self._jump_offset = 0.0
            self._jump_velocity = 0.0
            self._grounded = True
        pos = app.camera.position
        app.camera.position = Vector3(pos.x, pos.y + self._jump_offset, pos.z)

    def _update_lean(self, dt: float) -> None:
        """Q/Eで体を左右に傾け壁から覗き込む。"""
        app = self.app
        target = (1.0 if app.key("e") else 0.0) - (1.0 if app.key("q") else 0.0)
        self._lean += (target - self._lean) * min(1.0, dt * 9.0)

        fx, fz = self.player.forward
        rx, rz = -fz, fx  # 右方向ベクトル
        lean_dx = rx * self._lean * 0.45
        lean_dz = rz * self._lean * 0.45
        dx = lean_dx - self._lean_dx
        dz = lean_dz - self._lean_dz
        pos = app.camera.position
        if not self.blocked(pos.x + dx, pos.z + dz, 0.2):  # 壁にめり込まない
            app.camera.position = Vector3(pos.x + dx, pos.y, pos.z + dz)
            self._lean_dx = lean_dx
            self._lean_dz = lean_dz
        # rotation.z を yaw より内側(Rx  Ry  Rz)で適用するため　左右になるため　無r

    def blocked(
        self,
        x: float,
        z: float,
        radius: float | None = None,
        ignore: GameObject | None = None,
    ) -> bool:
        """壁と障害物の当たり判定。ただしジャンプで足が障害物の高さを越えていれば通す。
        エンジン側が2Dの判定しかないのでたかさっをこうり
        """
        if radius is None:
            radius = self.config.player_radius
        # 壁は高さに関係なく通れない
        for ox in (-radius, radius):
            for oz in (-radius, radius):
                if self.is_wall(x + ox, z + oz):
                    return True
        feet = getattr(self, "_jump_offset", 0.0)
        for obstacle in self._obstacles:
            if obstacle is ignore or not obstacle.alive:
                continue
            if math.hypot(obstacle.x - x, obstacle.z - z) < obstacle.radius + radius:
                clear_height = obstacle.data.get("clear_height", 1.6)
                if ignore is None and feet >= clear_height:
                    continue  
                return True
        return False

    def build_wall(self, row: int, col: int, x: float, z: float) -> None:
        """壁1マスぶん: 標準の壁に、下端の巾木と上端の飾り帯を足す。"""
        super().build_wall(row, col, x, z)
        cfg = self.config
        flip = (row + col) % 2
        self.app.cube(  # 巾木(壁の下端の黒い帯)
            position=(x, cfg.floor_y + 0.08, z),
            scale=(cfg.tile * 1.02, 0.16, cfg.tile * 1.02),
            color=cfg.wall_trim_color,
            ambient=0.38,
        )
        self.app.cube(  # 壁の上端の飾り帯(2色を交互に)
            position=(x, cfg.floor_y + cfg.wall_height - 0.2, z),
            scale=(cfg.tile * 1.02, 0.1, cfg.tile * 1.02),
            color=cfg.wall_top_colors[flip],
            ambient=0.5,
        )

    def build_floor_and_ceiling(self, row: int, col: int, x: float, z: float) -> None:
        super().build_floor_and_ceiling(row, col, x, z)
        cfg = self.config
        if row % 3 == 1 and col % 3 == 1:
            self.app.cube(  # ランプの台座
                position=(x, cfg.ceiling_y - 0.03, z),
                scale=(0.68, 0.06, 0.68),
                color=(58, 56, 52),
                ambient=0.4,
            )
            glow = self.app.cube(  # 光る面
                position=(x, cfg.ceiling_y - 0.08, z),
                scale=(0.52, 0.06, 0.52),
                color=cfg.lamp_color,
                ambient=0.95,
            )
            if not hasattr(self, "_lamps"):
                self._lamps: list[Mesh] = []
            self._lamps.append(glow)
    def spawn_character(
        self,
        x: float,
        z: float,
        color: Color = (172, 42, 40),
        head_color: Color | None = None,
        eye_color: Color = (255, 218, 72),
        scale: float = 1.0,
        style: str = "grunt",
        name: str = "",
    ) -> GameObject:

        if head_color is None:
            head_color = shade(color, 1.3)

        # スタイルごとの体格差
        big = style in ("brute", "boss")
        s = scale * {"brute": 1.25, "boss": 1.55}.get(style, 1.0)
        wide = 1.15 if big else 1.0
        parts: list[tuple[Mesh, Vector3, Vector3]] = []

        def part(
            local: tuple[float, float, float],
            size: tuple[float, float, float],
            part_color: Color,
            ambient: float = 0.3,
            tilt: tuple[float, float, float] = (0.0, 0.0, 0.0),
        ) -> None:
            """体のパーツを1個追加する(localは足元中心からの相対位置)。"""
            mesh = self.app.cube(
                position=(0, 0, 0),
                scale=(size[0] * s, size[1] * s, size[2] * s),
                color=part_color,
                ambient=ambient,
            )
            parts.append((mesh, Vector3(local[0] * s, local[1] * s, local[2] * s), Vector3(*tilt)))

        dark = shade(color, 0.55)
        dim = shade(color, 0.8)
        face_dark = (32, 27, 32)
        bone = (226, 209, 178)

        # --- 砲台型は人型と構造が違うので先に組んで返す ---
        if style == "turret":
            part((0.0, 0.14, 0.0), (0.66, 0.28, 0.66), dark, ambient=0.34)  # 台座
            part((0.0, 0.42, 0.0), (0.3, 0.3, 0.3), dim)  # 支柱
            part((0.0, 0.78, 0.0), (0.5, 0.34, 0.5), color, ambient=0.32)  # 砲頭
            part((0.0, 0.98, 0.0), (0.36, 0.08, 0.36), dark, ambient=0.4)  # 上蓋
            part((-0.17, 0.78, 0.2), (0.09, 0.09, 0.34), dark, ambient=0.4)  # 砲身(左)
            part((0.17, 0.78, 0.2), (0.09, 0.09, 0.34), dark, ambient=0.4)  # 砲身(右)
            part((0.0, 0.84, 0.26), (0.14, 0.1, 0.05), eye_color, ambient=0.95)  # センサー
            return GameObject(self, parts, x, z, radius=0.34 * s, name=name)

        # --- 人型の共通パーツ: 脚・胴体・胸当て ---
        part((-0.16 * wide, 0.17, 0.0), (0.18, 0.34, 0.2), dark, ambient=0.28)
        part((0.16 * wide, 0.17, 0.0), (0.18, 0.34, 0.2), dark, ambient=0.28)
        part((0.0, 0.64, 0.0), (0.66 * wide, 0.6, 0.46), color)
        part((0.0, 0.7, 0.21), (0.4 * wide, 0.32, 0.08), dim, ambient=0.38)

        # --- 肩・腕・こぶし ---
        shoulder = 0.3 if big else 0.18
        part((-0.42 * wide, 0.88, 0.0), (0.24, shoulder, 0.3), dark)
        part((0.42 * wide, 0.88, 0.0), (0.24, shoulder, 0.3), dark)
        part((-0.44 * wide, 0.5, 0.04), (0.13, 0.42, 0.16), dim, tilt=(0.0, 0.0, 0.1))
        part((0.44 * wide, 0.5, 0.04), (0.13, 0.42, 0.16), dim, tilt=(0.0, 0.0, -0.1))
        part((-0.46 * wide, 0.26, 0.1), (0.15, 0.13, 0.15), shade(color, 1.45), ambient=0.4)
        part((0.46 * wide, 0.26, 0.1), (0.15, 0.13, 0.15), shade(color, 1.45), ambient=0.4)

        # --- 頭・眉・目・口(前がプラスZ側) ---
        part((0.0, 1.16, 0.0), (0.46, 0.4, 0.44), head_color, ambient=0.32)
        part((0.0, 1.28, 0.2), (0.4, 0.07, 0.07), face_dark, ambient=0.5)  # 眉(悪役顔にする)
        part((-0.11, 1.19, 0.23), (0.1, 0.08, 0.04), eye_color, ambient=0.95)
        part((0.11, 1.19, 0.23), (0.1, 0.08, 0.04), eye_color, ambient=0.95)
        part((0.0, 1.03, 0.23), (0.22, 0.05, 0.04), face_dark, ambient=0.5)  # 口

        # --- スタイル別の追加パーツ ---
        if style == "imp":
            part((-0.17, 1.42, 0.0), (0.09, 0.22, 0.09), bone, ambient=0.5, tilt=(0.0, 0.0, 0.35))  # 角
            part((0.17, 1.42, 0.0), (0.09, 0.22, 0.09), bone, ambient=0.5, tilt=(0.0, 0.0, -0.35))
            part((0.0, 0.98, -0.26), (0.1, 0.24, 0.1), bone, ambient=0.45, tilt=(0.5, 0.0, 0.0))  # 背中のトゲ
            part((0.0, 0.74, -0.28), (0.1, 0.22, 0.1), bone, ambient=0.45, tilt=(0.6, 0.0, 0.0))
        elif style == "boss":
            part((-0.2, 1.46, 0.0), (0.12, 0.3, 0.12), bone, ambient=0.55, tilt=(0.0, 0.0, 0.4))  # 大きな角
            part((0.2, 1.46, 0.0), (0.12, 0.3, 0.12), bone, ambient=0.55, tilt=(0.0, 0.0, -0.4))
            part((0.0, 1.5, 0.0), (0.1, 0.22, 0.1), bone, ambient=0.55)  # 中央のトサカ
            part((0.0, 0.72, 0.25), (0.16, 0.16, 0.06), eye_color, ambient=0.95)  # 光る胸のコア

        radius = 0.44 * s if big else 0.36 * s
        return GameObject(self, parts, x, z, radius=radius, name=name)

    def spawn_pickup(
        self,
        x: float,
        z: float,
        color: Color = (74, 220, 92),
        size: float = 0.42,
        name: str = "",
    ) -> GameObject:

        s = size
        bright = shade(color, 1.55)
        dark = shade(color, 0.45)
        parts: list[tuple[Mesh, Vector3, Vector3]] = []

        def part(
            local: tuple[float, float, float],
            dims: tuple[float, float, float],
            part_color: Color,
            ambient: float = 0.5,
            tilt: tuple[float, float, float] = (0.0, 0.0, 0.0),
        ) -> None:
            mesh = self.app.cube(position=(0, 0, 0), scale=dims, color=part_color, ambient=ambient)
            parts.append((mesh, Vector3(*local), Vector3(*tilt)))

        part((0.0, -0.28, 0.0), (s * 1.7, 0.03, s * 1.7), color, ambient=0.85)  # 床の光る目印
        part((0.0, 0.0, 0.0), (s, s * 0.62, s), color, ambient=0.55)  # クレート本体
        part((0.0, 0.29 * s, 0.0), (s * 1.1, 0.1 * s, s * 1.1), dark, ambient=0.45)  # 上のフレーム
        part((0.0, -0.29 * s, 0.0), (s * 1.1, 0.1 * s, s * 1.1), dark, ambient=0.45)  # 下のフレーム
        part((0.0, 0.62 * s, 0.0), (0.4 * s, 0.4 * s, 0.4 * s), bright, ambient=0.95, tilt=(0.0, 0.785, 0.0))  # 結晶

        return GameObject(self, parts, x, z, y=0.3, radius=s / 2.0, name=name)
    def _spawn_barrels(self) -> None:
        """マップのBの位置に樽を置く。

        樽は障害物(通れない)かつ撃てるターゲットで、撃つと爆発して
        周囲のターゲットとプレイヤーにダメージを与える。近くの樽にも
        誘爆する。爆発時には "explosion" イベントが発信されるので、
        音担当・演出担当はそれを購読すればよい。
        """
        for x, z in self.find_cells("B"):
            barrel = self._make_barrel(x, z)
            self.add_obstacle(barrel)
            self.add_target(barrel, on_hit=self._on_barrel_hit, radius=0.5, height=1.1)

    def _make_barrel(self, x: float, z: float) -> GameObject:
        """ドラム缶風の樽モデルを組み立てる。"""
        body_color = (38, 132, 82)
        band_color = (230, 66, 52)
        parts: list[tuple[Mesh, Vector3, Vector3]] = []

        def part(
            local: tuple[float, float, float],
            dims: tuple[float, float, float],
            part_color: Color,
            ambient: float = 0.36,
        ) -> None:
            mesh = self.app.cube(position=(0, 0, 0), scale=dims, color=part_color, ambient=ambient)
            parts.append((mesh, Vector3(*local), Vector3()))

        part((0.0, 0.46, 0.0), (0.56, 0.92, 0.56), body_color)  # 本体
        part((0.0, 0.68, 0.0), (0.62, 0.14, 0.62), band_color, ambient=0.45)  # 上の帯
        part((0.0, 0.28, 0.0), (0.62, 0.14, 0.62), band_color, ambient=0.45)  # 下の帯
        part((0.0, 0.93, 0.0), (0.44, 0.06, 0.44), shade(body_color, 0.5), ambient=0.4)  # フタ
        part((0.0, 0.5, 0.29), (0.2, 0.2, 0.03), (255, 214, 90), ambient=0.8)  # 危険マーク

        barrel = GameObject(self, parts, x, z, radius=0.34, name="barrel")
        barrel.data["exploded"] = False
        barrel.data["clear_height"] = 1.1  
        return barrel

    def _on_barrel_hit(self, barrel: GameObject, damage: int) -> None:
        """樽に弾(または他の樽の爆発)が当たったときの処理。"""
        if barrel.data.get("exploded"):
            return
        barrel.data["exploded"] = True
        barrel.remove()  # 先に消してから爆発(自分自身への誘爆を防ぐ)
        self.explode(barrel.x, barrel.z, radius=2.6, damage=3, player_damage=30)
        self.app.cube(  # 床に焦げ跡を残す
            position=(barrel.x, self.config.floor_y + 0.011, barrel.z),
            scale=(1.4, 0.01, 1.4),
            color=(24, 22, 22),
            ambient=0.25,
        )
    def _spawn_covers(self) -> None:
        """マップのCの位置に遮蔽用コンテナを置く。

        コンテナは通れない障害物で、弾も高さ1.05までは防ぐ。
        プレイヤーの目線(約1.25)からは頭がわずかに出るので、
        リーン(代表者の追加アクション)との相性がよい。
        """
        for x, z in self.find_cells("C"):
            cover = self._make_container(x, z)
            cover.data["block_height"] = 1.05  # 弾を防ぐ高さ
            cover.data["clear_height"] = 0.7  # 
            self.add_obstacle(cover)

    def _make_container(self, x: float, z: float) -> GameObject:
        """軍用コンテナ風の遮蔽物モデルを組み立てる。"""
        body_color = (78, 92, 112)
        strap_color = (235, 186, 74)
        parts: list[tuple[Mesh, Vector3, Vector3]] = []

        def part(
            local: tuple[float, float, float],
            dims: tuple[float, float, float],
            part_color: Color,
            ambient: float = 0.42,
        ) -> None:
            mesh = self.app.cube(position=(0, 0, 0), scale=dims, color=part_color, ambient=ambient)
            parts.append((mesh, Vector3(*local), Vector3()))

        part((0.0, 0.34, 0.0), (0.98, 0.68, 0.98), body_color)  # 本体
        part((0.0, 0.71, 0.0), (1.04, 0.07, 1.04), shade(body_color, 0.6))  # フタの縁
        part((-0.25, 0.36, 0.0), (0.07, 0.74, 1.0), strap_color, ambient=0.55)  # 帯(左)
        part((0.25, 0.36, 0.0), (0.07, 0.74, 1.0), strap_color, ambient=0.55)  # 帯(右)
        part((0.16, 0.9, -0.12), (0.5, 0.32, 0.5), shade(body_color, 0.85))  # 上の小箱
        part((0.16, 1.08, -0.12), (0.54, 0.05, 0.54), shade(body_color, 0.55))  # 小箱のフタ

        return GameObject(self, parts, x, z, radius=0.52, name="container")

    def _decorate_world(self) -> None:
        """行き止まりにガレキ、天井にパイプを通して基地の廃墟らしさを出す。"""
        cfg = self.config
        for row in range(self.map_h):
            for col in range(self.map_w):
                if self.map[row][col] != ".":
                    continue
                x, z = self.cell_to_world(row, col)

                # 天井パイプ: 4行おきに横一直線に走らせる
                if row % 4 == 2:
                    self.app.cube(
                        position=(x, cfg.ceiling_y - 0.14, z),
                        scale=(cfg.tile, 0.09, 0.09),
                        color=(70, 74, 82),
                        ambient=0.35,
                    )

                # 行き止まり(3方向が壁)のマスにはガレキを散らす
                wall_count = sum(
                    1
                    for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1))
                    if self.is_wall(*self.cell_to_world(row + dr, col + dc))
                )
                if wall_count >= 3:
                    seed = row * 31 + col  
                    for i in range(3):
                        angle = (seed * 2.39 + i * 1.7) % 6.28
                        offset_x = math.cos(seed + i * 2.1) * 0.45
                        offset_z = math.sin(seed * 1.3 + i) * 0.45
                        size = 0.16 + ((seed + i) % 3) * 0.07
                        self.app.cube(
                            position=(x + offset_x, cfg.floor_y + size / 2, z + offset_z),
                            rotation=(0.0, angle, 0.0),
                            scale=(size, size, size),
                            color=(66, 62, 58) if i % 2 else (84, 78, 70),
                            ambient=0.4,
                        )

    def _schedule_lamp_flicker(self) -> None:
        """数秒おきにどこかの天井ランプをチカッとさせる(電源が不安定な演出)。"""
        self.after(random.uniform(2.5, 6.0), self._flicker_random_lamp)

    def _flicker_random_lamp(self) -> None:
        """ランプを1つ選んで短く消灯し、次の明滅を予約する。"""
        lamps = getattr(self, "_lamps", [])
        if lamps:
            lamp = random.choice(lamps)
            lamp.visible = False
            self.after(0.07, lambda: setattr(lamp, "visible", True))
            if random.random() < 0.4:  # たまに二度点滅する
                self.after(0.18, lambda: setattr(lamp, "visible", False))
                self.after(0.26, lambda: setattr(lamp, "visible", True))
        self._schedule_lamp_flicker()

    def draw_overlay_extra(self) -> None:
        """コア全体の画面演出: 開始時のミッション表示と瀕死時の警告。"""
        if self.state != "playing":
            return

        # 開始から数秒間、ミッションを表示する
        if self.time < 4.0:
            self.draw_text(
                "MISSION: 敵をぶったおす💛",
                self.width // 2,
                80,
                size=26,
                center=True,
                bold=True,
            )
            self.draw_text(
                "(赤い帯の樽は撃つと爆発する)",
                self.width // 2,
                112,
                size=18,
                color=(200, 205, 215),
                center=True,
            )

        # HPが低いときは画面の縁を赤く明滅させる
        if self.player.health <= 25:
            pg = self.pygame
            pulse = 0.5 + 0.5 * math.sin(self.time * 6.0)
            alpha = 30 + int(70 * pulse)
            surface = pg.Surface((self.width, self.height), pg.SRCALPHA)
            edge = 26
            for rect in (
                (0, 0, self.width, edge),
                (0, self.height - edge, self.width, edge),
                (0, 0, edge, self.height),
                (self.width - edge, 0, edge, self.height),
            ):
                pg.draw.rect(surface, (200, 30, 30, alpha), rect)
            self.app.screen.blit(surface, (0, 0))


    def draw_crosshair(self) -> None:
        """照準: 十字+中央ドット。命中の瞬間はオレンジに光ってXが出る。"""
        draw = self.pygame.draw
        cx, cy = self.width // 2, self.height // 2

        self._hit_marker = max(0.0, self._hit_marker - self.app.delta)
        hit = self._hit_marker > 0.0
        color = (255, 150, 60) if hit else (238, 235, 210)

        for (x0, y0, x1, y1) in (
            (cx - 14, cy, cx - 6, cy),
            (cx + 6, cy, cx + 14, cy),
            (cx, cy - 14, cx, cy - 6),
            (cx, cy + 6, cx, cy + 14),
        ):
            draw.line(self.app.screen, color, (x0, y0), (x1, y1), 2)
        draw.circle(self.app.screen, color, (cx, cy), 2)

        if hit:  # ヒットマーカー(照準の四隅に小さなX)
            for sx in (-1, 1):
                for sy in (-1, 1):
                    draw.line(
                        self.app.screen,
                        (255, 235, 180),
                        (cx + sx * 8, cy + sy * 8),
                        (cx + sx * 16, cy + sy * 16),
                        2,
                    )

    def draw_end_screen(self) -> None:
        """勝敗画面: 半透明パネルの上にタイトル・スコア・生存時間を表示。"""
        pg = self.pygame
        cx, cy = self.width // 2, self.height // 2

        panel = pg.Surface((self.width, 190), pg.SRCALPHA)
        panel.fill((10, 10, 14, 200))
        pg.draw.rect(panel, (255, 255, 255, 40), (0, 0, self.width, 190), width=2)
        self.app.screen.blit(panel, (0, cy - 95))

        if self.state == "win":
            title_color = (255, 228, 90)
        else:
            title_color = (230, 48, 40)
        self.draw_text(self._end_title, cx, cy - 45, size=52, color=title_color, center=True, bold=True)
        minutes, seconds = divmod(int(self.time), 60)
        self.draw_text(
            f"スコア {self.score}   生存時間 {minutes}:{seconds:02d}",
            cx,
            cy + 15,
            size=26,
            center=True,
        )
        self.draw_text("ESCキー 終了", cx, cy + 58, size=20, color=(180, 186, 196), center=True)
