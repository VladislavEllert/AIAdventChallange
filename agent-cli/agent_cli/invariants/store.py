from pathlib import Path
import yaml
import agent_cli.config as cfg

DEFAULT_FILE = "default.yaml"


def _path(filename: str = DEFAULT_FILE) -> Path:
    return Path(cfg.INVARIANTS_DIR) / filename


def load_invariants(filename: str = DEFAULT_FILE) -> list[str]:
    p = _path(filename)
    if not p.exists():
        return []
    data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    return data.get("invariants", [])


def save_invariants(invariants: list[str], filename: str = DEFAULT_FILE) -> None:
    p = _path(filename)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        yaml.dump({"invariants": invariants}, allow_unicode=True, default_flow_style=False),
        encoding="utf-8",
    )


def add_invariant(text: str, filename: str = DEFAULT_FILE) -> None:
    invs = load_invariants(filename)
    if text not in invs:
        invs.append(text)
        save_invariants(invs, filename)
