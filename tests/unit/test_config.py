from pathlib import Path
import pytest
from private_dictate.config import Config, load, save, DEFAULT_CONFIG_TOML


def test_defaults_roundtrip(tmp_path: Path):
    path = tmp_path / "config.toml"
    path.write_text(DEFAULT_CONFIG_TOML)
    cfg = load(path)
    assert cfg.hotkey.binding == "ctrl+shift+d"
    assert cfg.hotkey.mode == "hold"
    assert cfg.model.size == "small"
    assert cfg.transcription.max_seconds == 180
    assert cfg.history.limit == 100


def test_missing_file_writes_default_and_loads(tmp_path: Path):
    path = tmp_path / "config.toml"
    cfg = load(path)
    assert path.exists()
    assert cfg.hotkey.binding == "ctrl+shift+d"
    # Round-trip preserves content
    assert DEFAULT_CONFIG_TOML in path.read_text()


def test_bad_field_falls_back_to_default(tmp_path: Path, caplog):
    path = tmp_path / "config.toml"
    path.write_text("""
[hotkey]
binding = "ctrl+shift+d"
mode = "invalid_mode"
""")
    cfg = load(path)
    assert cfg.hotkey.mode == "hold"  # default
    assert any("invalid" in rec.message.lower() for rec in caplog.records)


def test_save_atomic_temp_plus_rename(tmp_path: Path):
    path = tmp_path / "config.toml"
    cfg = load(path)  # writes default
    cfg.hotkey.binding = "F9"
    save(cfg, path)
    assert "F9" in path.read_text()
    # no leftover temp file
    assert list(tmp_path.iterdir()) == [path]


@pytest.mark.parametrize("compute_type", ["int8", "float16", "int8_float16", "float32", "int8_float32"])
def test_compute_type_accepts_cpu_and_no_cudnn_variants(tmp_path: Path, compute_type):
    path = tmp_path / "config.toml"
    path.write_text(f"""
[model]
compute_type = "{compute_type}"
""")
    cfg = load(path)
    assert cfg.model.compute_type == compute_type


def test_invalid_toml_falls_back_and_logs(tmp_path: Path, caplog):
    path = tmp_path / "config.toml"
    path.write_text("this is not = = valid toml [")
    cfg = load(path)
    assert cfg.hotkey.binding == "ctrl+shift+d"
    assert any("parse" in rec.message.lower() or "toml" in rec.message.lower() for rec in caplog.records)
