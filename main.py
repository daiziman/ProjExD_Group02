"""ゲームのエントリポイント。 なるべく増やさないこと あくまでエントリーポイント

実行方法:

    python main.py
"""

import os
from game.core import Game
from game.features import FEATURES
from game.level import MAP

os.chdir(os.path.dirname(os.path.abspath(__file__)))
def main() -> None:
    game = Game(
        map_data=MAP,
        features=FEATURES,
        title="ProjExD Group02",
    )
    game.run()
if __name__ == "__main__":
    main()