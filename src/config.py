"""配置加载：JSON 配置 + extends 继承 + CLI 覆盖。"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[1]  # repo 根目录（src/config.py -> repo）
CONFIG_DIR = ROOT / "configs"


def load_config(name: str = "base.json", overrides: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """加载配置，支持一层 extends 继承。in: 配置文件名, 覆盖字典 -> out: 合并配置。"""
    path = CONFIG_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"配置不存在: {path}")
    cfg = json.loads(path.read_text(encoding="utf-8"))
    parent = cfg.pop("extends", None)
    if parent:
        base = load_config(parent)
        _deep_update(base, cfg)
        cfg = base
    if overrides:
        _deep_update(cfg, overrides)
    return cfg


def _deep_update(dst: Dict[str, Any], src: Dict[str, Any]) -> None:
    for k, v in src.items():
        if isinstance(v, dict) and isinstance(dst.get(k), dict):
            _deep_update(dst[k], v)
        else:
            dst[k] = v
