from pathlib import Path
import os

user_data_tm2020_base_path = Path(os.environ.get("GBX_PY_USER_DATA_TM2020", "C:/Users/schad/Documents/Trackmania/"))
user_data_mp4_base_path = Path(os.environ.get("GBX_PY_USER_DATA_MP4", "C:/Users/schad/Documents/Maniaplanet/"))
openplanet_tm2020_extract_base = Path(os.environ.get("GBX_PY_OP_TM2020_EXTRACT", "C:/Users/schad/OpenplanetNext/Extract/"))
openplanet_mp4_extract_base = Path(os.environ.get("GBX_PY_OP_MP4_EXTRACT", "C:/Users/schad/Openplanet4/Extract/"))

def get_ud_tm2020_path(relative_ud_file: str | Path) -> Path:
    return user_data_tm2020_base_path / Path(relative_ud_file)

def get_ud_mp4_path(relative_ud_file: str | Path) -> Path:
    return user_data_mp4_base_path / Path(relative_ud_file)

def get_extract_tm2020_path(relative_extract_file: str | Path) -> Path:
    return openplanet_tm2020_extract_base / Path(relative_extract_file)

def get_extract_mp4_path(relative_extract_file: str | Path) -> Path:
    return openplanet_mp4_extract_base / Path(relative_extract_file)

def get_author_name() -> str:
    return os.environ("GBX_PY_AUTHOR_NAME", "schadocalex")

hex_window_width_px = int(os.environ.get("GBX_PY_HEX_WINDOW_WIDTH", "538"))
