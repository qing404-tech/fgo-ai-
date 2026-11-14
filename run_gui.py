"""启动图形界面：python run_gui.py 或 pythonw run_gui.py

pythonw 没有控制台，stdout/stderr 为 None，异常会静默丢失；这里重定向到
logs/stdout.log、logs/stderr.log，方便排查（EXE 版同样适用）。
"""

import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
os.chdir(BASE_DIR)
sys.path.insert(0, str(BASE_DIR))


def _redirect_std_streams() -> None:
    if sys.stdout is not None and sys.stderr is not None:
        return
    try:
        log_dir = BASE_DIR / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        if sys.stderr is None:
            sys.stderr = open(
                log_dir / "stderr.log", "a", buffering=1, encoding="utf-8", errors="replace"
            )
        if sys.stdout is None:
            sys.stdout = open(
                log_dir / "stdout.log", "a", buffering=1, encoding="utf-8", errors="replace"
            )
    except OSError:
        pass  # 目录不可写就保持 None，至少不因此启动失败


_redirect_std_streams()

from fgo_auto.gui import main  # noqa: E402

if __name__ == "__main__":
    main()
