import configparser
from pathlib import Path

_ini = configparser.ConfigParser()
_ini.read(Path(__file__).parent / "config.ini", encoding="utf-8")

DATABASE_URL         = _ini["database"]["url"]

LINUX_PATH_PREFIX    = _ini["path"]["linux_prefix"]
WINDOWS_MOUNT_LETTER = _ini["path"]["windows_drive"]

BHVR_TABLE = _ini["tables"]["bhvr_table"]
DST_TABLE  = _ini["tables"]["dst_table"]
EVENT_COL  = _ini["tables"]["event_col"]

BHVR_EVENTS   = [e.strip() for e in _ini["events"]["bhvr"].split(",")]
DST_EVENTS    = [e.strip() for e in _ini["events"]["dst"].split(",")]
ALL_EVENTS    = BHVR_EVENTS + DST_EVENTS
BHVR_EVNT_KND = _ini.get("events", "bhvr_evnt_knd", fallback="BHAR")
DST_EVNT_KND  = _ini.get("events", "dst_evnt_knd",  fallback="CALAMITY")

API_BASE_URL = _ini["api"]["base_url"]
