"""武器機能(担当:
"""

from __future__ import annotations

import math
from typing import Any

from game.core import Feature, FPSGame




class Weapons(Feature):

    name = "武器"

    def setup(self, game: FPSGame) -> None:
        self.muzzle_timer = 0.0
        self.cooldown = 0.0 
        self.reloading = False     
        self.reload_time = 1.2     
        self.recoil = 0
        self.weapons = {
            "pistol": {
                "cooldown": 0.35,
                "damage": 2,
                "pellets": 1,
                "spread": 0.0,
                "max_ammo": 12,
                "reload_time": 1.2,
            },
            "rifle": {
                "cooldown": 0.12,
                "damage": 1,
                "pellets": 1,
                "spread": 0.02,
                "max_ammo": 30,
                "reload_time": 1.6,
            },
            "shotgun": {
                "cooldown": 0.8,
                "damage": 1,
                "pellets": 6,
                "spread": 0.08,
                "max_ammo": 6,
                "reload_time": 2.0,
            },
        }
        self.current_weapon = "pistol"
        game.player.max_ammo = self.weapons["pistol"]["max_ammo"]
        game.player.ammo = game.player.max_ammo

    def shoot(self, game: FPSGame) -> None:
        if self.reloading:
            return
        if self.cooldown > 0:
            return
        if game.player.ammo <= 0:
            game.emit("empty_click", {})
            return
        weapon = self.weapons[self.current_weapon]
        for _ in range(weapon["pellets"]):
            game.fire_bullet(
                damage=weapon["damage"],
                spread=weapon["spread"]
        )
        game.player.ammo -= 1
        self.muzzle_timer = 0.07
        self.cooldown = weapon["cooldown"]
        self.recoil += 10
        game.flash((255, 230, 120), 0.08)

    def update(self, game: FPSGame, dt: float) -> None:
        if self.cooldown > 0:
            self.cooldown -= dt
            if self.cooldown < 0:
                self.cooldown = 0
        self.muzzle_timer = max(0.0, self.muzzle_timer - dt)
        self.recoil *= 0.85
        if game.pygame.mouse.get_pressed()[0]:
                self.shoot(game)

    def on_mouse_down(self, game: FPSGame, button: int) -> None:
        if button != 1: 
            return
        self.shoot(game)

    def start_reload(self, game: FPSGame) -> None:
        if self.reloading:
            return
        weapon = self.weapons[self.current_weapon]
        if game.player.ammo == weapon["max_ammo"]:
            return
        self.reload_time = weapon["reload_time"]
        self.reloading = True
        game.after(self.reload_time, lambda: self.finish_reload(game))

    def finish_reload(self, game: FPSGame) -> None:
        weapon = self.weapons[self.current_weapon]
        game.player.max_ammo = weapon["max_ammo"]
        game.player.ammo = weapon["max_ammo"]
        self.reloading = False

    def on_key_down(self, game: FPSGame, key: str) -> None:
        if key == "1":
            self.current_weapon = "pistol"
        elif key == "2":
            self.current_weapon = "rifle"
        elif key == "3":
            self.current_weapon = "shotgun"
        else:
            if key == "r":
                self.start_reload(game)
                return
            return
        weapon = self.weapons[self.current_weapon]
        game.player.max_ammo = weapon["max_ammo"]
        game.player.ammo = weapon["max_ammo"]
        self.reload_time = weapon["reload_time"]

    def draw_hud(self, game: FPSGame, screen: Any) -> None:

        draw = game.pygame.draw
        cx = game.width // 2
        sway_x = int(math.sin(game.time * 1.7) * 4)
        sway_y = int(math .cos(game.time * 3.4) * 3)
        kick = int(self.muzzle_timer * 260)
        gx = cx + sway_x
        base_gun_y = game.height - 128 + sway_y + kick
        gy = base_gun_y + self.recoil


        draw.polygon(screen, (52, 46, 44), [(gx - 88, gy + 132), (gx - 30, gy + 66), (gx + 30, gy + 66), (gx + 88, gy + 132)])
        draw.rect(screen, (74, 62, 54), (gx - 34, gy + 62, 68, 70), border_radius=8)
        draw.rect(screen, (58, 48, 42), (gx - 34, gy + 62, 68, 12), border_radius=6) 
        # フレームとスライド
        draw.rect(screen, (52, 54, 60), (gx - 30, gy - 6, 60, 78), border_radius=6)
        draw.rect(screen, (108, 112, 120), (gx - 24, gy - 18, 48, 62), border_radius=4)
        draw.rect(screen, (76, 80, 88), (gx - 24, gy - 18, 48, 14), border_radius=4) 
        draw.rect(screen, (30, 32, 36), (gx + 4, gy - 8, 16, 8), border_radius=2)  
        # 銃身と銃口
        draw.rect(screen, (38, 40, 46), (gx - 10, gy - 34, 20, 22), border_radius=3)
        draw.rect(screen, (14, 14, 16), (gx - 6, gy - 31, 12, 9), border_radius=2) 
        # フロントサイトと黄色のアクセント
        draw.rect(screen, (230, 190, 70), (gx - 3, gy - 43, 6, 8))
        draw.rect(screen, (230, 190, 70), (gx - 24, gy + 32, 48, 5))

        if self.muzzle_timer > 0.0:
            flash_y = gy - 40
            draw.polygon(screen, (255, 236, 120), [(gx, flash_y - 48), (gx - 27, flash_y), (gx + 27, flash_y)])
            draw.polygon(screen, (255, 150, 40), [(gx, flash_y - 25), (gx - 14, flash_y), (gx + 14, flash_y)])
            draw.circle(screen, (255, 246, 200), (gx, flash_y - 9), 7)
        if self.current_weapon == "pistol":
            pass
        elif self.current_weapon == "rifle":
            draw.rect(screen, (52,54,60), (gx-25, gy-35, 50, 120), border_radius=6)
            draw.rect(screen, (38,40,46), (gx-8, gy-80, 16, 50), border_radius=3)
        elif self.current_weapon == "shotgun":
            draw.rect(screen, (60,55,45), (gx-35, gy+20, 70, 110), border_radius=8)
            draw.rect(screen, (40,35,30), (gx-12, gy-70, 24, 70), border_radius=4)
                
        


