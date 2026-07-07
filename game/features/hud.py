"""HUD機能(担当:
"""

from __future__ import annotations

from typing import Any

from game.core import Feature, FPSGame


class Hud(Feature):


    name = "HUD"

    def setup(self, game: FPSGame) -> None:
        self.kills = 0
        self.log_text = ""
        self.log_timer = 0.0
        game.on("enemy_defeated", self.on_enemy_defeated)

    def on_enemy_defeated(self, data: dict[str, Any]) -> None:
        self.kills += 1
        self.log_text = "+100"
        self.log_timer = 2.0

    def update(self, game: FPSGame, dt: float) -> None:
            if self.log_timer > 0:
                self.log_timer -= dt

    def draw_hud(self, game: FPSGame, screen: Any) -> None:
        
        hp = game.player.health
        
        if hp <= 25:
            if int(game.time * 4) % 2 == 0:
                game.draw_bar(20, 44, game.player.health, game.player.max_health, color=(255, 0, 0), label="HP") # 赤いHPバーを描く
                pass
        elif hp <= 50:
                game.draw_bar(20, 44, game.player.health, game.player.max_health, color=(255, 255, 0), label="HP") # 黄色いHPバーを描く
                pass
        else:
                game.draw_bar(20, 44, game.player.health, game.player.max_health, color=(0, 255, 0), label="HP")# 通常色のHPバーを描く
                pass        
        
        # game.draw_bar(20, 44, game.player.health, game.player.max_health, color=(230, 70, 60), label="HP")
        game.draw_bar(20, 96, game.player.ammo, game.player.max_ammo, color=(80, 160, 255), label="弾薬")
        game.draw_text(f"スコア {game.score}", 20, 122, size=22)
        game.draw_text(f"撃破数 {self.kills}", 20, 150, size=22)
        
        if self.log_timer > 0:
            game.draw_text(self.log_text, 20, 180, size=22, color=(255, 255, 100)) # self.log_text を画面に表示する
            pass        
        
        game.draw_text(
            "WASD移動 / Shiftダッシュ / マウス視点 / 左クリック射撃 / ESC終了",
            20,
            game.height - 36,
            size=18,
            color=(160, 168, 180),
        )
