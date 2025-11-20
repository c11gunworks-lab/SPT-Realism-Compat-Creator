# spt_realism_compat_tool.py
import sys, os, json, re
from glob import iglob
from collections import defaultdict
import importlib, inspect, traceback
import uuid
import itertools
import io


from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QLabel, QPushButton,
    QFileDialog, QLineEdit, QFormLayout, QComboBox, QSpinBox, QDoubleSpinBox, QCheckBox,
    QScrollArea, QMessageBox, QAbstractItemView, QTreeWidget, QTreeWidgetItem,
    QSizePolicy, QTabWidget
)

from PyQt5.QtCore import Qt, QSettings
from PyQt5.QtGui import QPalette, QColor
from PyQt5.QtWidgets import QInputDialog
FORMULAS_MOD_NAME = "formulas"
formulas_mod = None




COMPACT_ID_RE = re.compile(r"(?m)^\s*([0-9a-fA-F]{24})\s+(?:clone\s+\S+\s+)?enable\b")
GUID24_RE = re.compile(r"^[0-9a-fA-F]{24}$")     # Mongo-like
UUID_RE    = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$")

def is_guid_like(s: str) -> bool:
    if not isinstance(s, str) or len(s) < 8:
        return False
    return bool(GUID24_RE.match(s) or UUID_RE.match(s))

NAME_KEYS = {"name", "_name", "shortName"}

def first_non_guid_string(value: str) -> str:
    if isinstance(value, str) and value.strip() and not is_guid_like(value.strip()):
        return value.strip()
    return ""

def deep_find_name(obj) -> str:
    """
    Recursively search for the first meaningful (non-GUID) name-like string:
      - locales.*.name / locales.*.shortName
      - 'name', '_name', 'shortName' anywhere
    """
    if isinstance(obj, dict):
        # locales.* first
        locales = obj.get("locales") or obj.get("_locales")
        if isinstance(locales, dict):
            for lang in locales.values():
                if isinstance(lang, dict):
                    for key in ("name", "shortName"):
                        n = first_non_guid_string(lang.get(key, ""))
                        if n:
                            return n
        # then direct known keys
        for key in ("Name", "shortName", "_name", "displayName", "title"):
            n = first_non_guid_string(obj.get(key, ""))
            if n:
                return n
        # then recursive for generic name keys
        for k, v in obj.items():
            if isinstance(v, (dict, list)):
                n = deep_find_name(v)
                if n:
                    return n
            else:
                if k in NAME_KEYS:
                    n = first_non_guid_string(v)
                    if n:
                        return n
    elif isinstance(obj, list):
        for v in obj:
            n = deep_find_name(v)
            if n:
                return n
    return ""

def get_display_name(rec):
    """
    Returns a human-friendly name. If the initial candidates look like GUIDs,
    drill down through the JSON to find name/_name/locales.*.name.
    """
    # Fast-path: standard locales
    locales = rec.get("locales") or rec.get("_locales")
    if isinstance(locales, dict):
        en = locales.get("en")
        if isinstance(en, dict):
            for key in ("name", "shortName"):
                n = first_non_guid_string(en.get(key, ""))
                if n:
                    return n

    # Simple direct fields
    for key in ("Name", "shortName", "_name", "displayName", "title"):
        n = first_non_guid_string(rec.get(key, ""))
        if n:
            return n

    # If what we have is GUID-ish, try deep search
    for key in ("itemTplToClone","itemtpltoclone","clone","tpl","_tpl","_guid","id","_id"):
        v = rec.get(key)
        if isinstance(v, str) and v.strip() and not is_guid_like(v.strip()):
            # this is already a non-guid string (rare); use it
            return v.strip()

    # Deep recursive search for any name field
    n = deep_find_name(rec)
    if n:
        return n

    # Fallback to IDs
    for key in ("itemTplToClone","itemtpltoclone","clone","tpl","_tpl","_guid","id","_id"):
        v = rec.get(key)
        if isinstance(v, str) and v.strip():
            return v.strip()

    return "Unknown"



def _kv_scan(tokens: list[str], start_idx: int, stop_tokens: set[str], assign_to: dict):
    """
    Cheap key/value scanner over flat token streams:
    Collect pairs like 'Weight 0.45 Ergonomics 10 Recoil -5' until we hit a stop token.
    Numbers -> float/int; 'true/false' -> bool; otherwise str.
    """
    i = start_idx
    def _coerce(s: str):
        if s.lower() in ("true","false"):
            return s.lower() == "true"
        if re.fullmatch(r"-?\d+", s):
            try: return int(s)
            except: pass
        if re.fullmatch(r"-?\d+\.\d+", s):
            try: return float(s)
            except: pass
        return s

    while i < len(tokens)-1:
        k = tokens[i]
        if k in stop_tokens:
            break
        v = tokens[i+1]
        # guard: if next token is a 'section' marker, stop
        if v in stop_tokens or re.fullmatch(r"[A-Za-z_][\w\.\-]*", v) and tokens[i+2:i+3] and tokens[i+2] in stop_tokens:
            break
        assign_to[k] = _coerce(v)
        i += 2
    return i

def parse_compact_items_json(path: str):
    """
    Fallback reader for 'compact' items.json (space-delimited tokens).
    Returns list[(guid, record_dict)] compatible with the rest of the tool.
    """
    try:
        raw = open(path, "r", encoding="utf-8", errors="ignore").read()
    except Exception:
        return []

    stripped = raw.lstrip()
    if stripped.startswith("{") or stripped.startswith("["):
        return []

    # ---- Entry boundaries (GUID [clone ..] enable) ----
    starts = [m.start(1) for m in COMPACT_ID_RE.finditer(raw)]
    if not starts:
        return []
    starts.append(len(raw))

    def _coerce(s: str):
        sl = s.lower()
        if sl in ("true", "false"):
            return sl == "true"
        if re.fullmatch(r"-?\d+", s):
            try: return int(s)
            except: pass
        if re.fullmatch(r"-?\d+\.\d+", s):
            try: return float(s)
            except: pass
        if len(s) >= 2 and s[0] == s[-1] == '"':
            return s[1:-1]
        return s

    # keys we can sweep for, if present
    INTERESTING_KEYS_LOWER = {
        "weight", "ergonomics", "recoil", "recoilforceup", "recoilforceback",
        "basemalfunctionchance", "damage", "penetrationpower",
        "mousepenalty", "speedpenaltypercent", "weaponergonomicpenalty",
        "velocity", "loudness",
    }
    CANON = {
        "weight":"Weight", "ergonomics":"Ergonomics", "recoil":"Recoil",
        "recoilforceup":"RecoilForceUp", "recoilforceback":"RecoilForceBack",
        "basemalfunctionchance":"BaseMalfunctionChance",
        "damage":"Damage", "penetrationpower":"PenetrationPower",
        "mousepenalty":"mousePenalty", "speedpenaltypercent":"speedPenaltyPercent",
        "weaponergonomicpenalty":"weaponErgonomicPenalty",
        "velocity":"Velocity", "loudness":"Loudness",
    }

    records = []

    for i in range(len(starts)-1):
        chunk = raw[starts[i]:starts[i+1]]

        # Tokenize for structure, but we’ll use regex for Prefab/Price to handle commas
        tokens = re.findall(
            r'[A-Za-z_][\w\.\-]*|\\_[A-Za-z][\w\.\-]*|[0-9a-fA-F]{24}|-?\d+\.\d+|-?\d+|".*?"',
            chunk
        )
        if not tokens:
            continue

        def clean(tok: str) -> str:
            return tok[1:] if tok.startswith("\\") else tok

        # newId (first GUID in this chunk)
        m_id = re.match(r"\s*([0-9a-fA-F]{24})", chunk)
        newId = m_id.group(1) if m_id else None

        # clone <tpl> (optional)
        m_clone = re.search(r"(?m)^\s*[0-9a-fA-F]{24}\s+clone\s+(\S+)\s+enable\b", chunk)
        itemTplToClone = m_clone.group(1) if m_clone else None

        # scan inner item block for _id/_parent (rarely present in this variant)
        inner_id, inner_parent = None, None
        for j in range(len(tokens)):
            if clean(tokens[j]).lower() == "item":
                k = j + 1
                end = min(j + 120, len(tokens) - 1)
                while k < end:
                    key = clean(tokens[k])
                    if key in ("_id","id") and k+1 < len(tokens) and re.fullmatch(r"[0-9a-fA-F]{24}", tokens[k+1]):
                        inner_id = tokens[k+1]
                    elif key in ("_parent","parent","parentId","Parent") and k+1 < len(tokens) and re.fullmatch(r"[0-9a-fA-F]{24}", tokens[k+1]):
                        inner_parent = tokens[k+1]
                    k += 1
                break

        # Build record shell
        rec = {
            "_file": path,
            "_guid": newId or inner_id or f"{os.path.basename(path)}:{i}",
            "newId": newId or inner_id,
            "itemTplToClone": itemTplToClone,
            "overrideProperties": {},
            "locales": {}
        }
        if inner_parent:
            rec["parent"] = inner_parent
        # ---- Prefab path (regex so commas are preserved) ----
        m_prefab = re.search(r"(?i)\bPrefab\s+path\s+([^\s]+)", chunk)
        if m_prefab:
            prefab_path = m_prefab.group(1).strip().strip('"')
            # dict + flattened string (so Base panel shows it)
            rec["overrideProperties"].setdefault("Prefab", {})["path"] = prefab_path
            rec["overrideProperties"]["PrefabPath"] = prefab_path

        # ---- Handbook: ParentId + Price ----
        # ParentId (if you want it at top-level for matching)
        m_parent = re.search(r"(?i)\bhandbook\s+ParentId\s+([0-9a-fA-F]{24})", chunk)
        if m_parent and "parent" not in rec:
            rec["parent"] = m_parent.group(1)

        # Price as a scalar (so Base panel shows it)
        m_price = re.search(r"(?i)\bhandbook\b.*?\bPrice\s+(\d+)", chunk, flags=re.S)
        if m_price:
            rec["overrideProperties"]["Price"] = int(m_price.group(1))

        # ---- locales without language code (Name / Shortname / Description) ----
        # pattern appears as: locales Name <...> Shortname <...> Description <...>
        # we take the next tokens after each key
        name_val = short_val = None
        for j in range(len(tokens)-1):
            if clean(tokens[j]).lower() == "locales":
                k = j + 1
                end = min(j + 140, len(tokens)-1)
                while k < end:
                    key = clean(tokens[k]).lower()
                    if key == "name" and k+1 < len(tokens):
                        name_val = tokens[k+1].strip('"'); k += 2; continue
                    if key in ("shortname","short_name") and k+1 < len(tokens):
                        short_val = tokens[k+1].strip('"'); k += 2; continue
                    if key in ("handbook","items","_props","slots","grids","_type","_id","_parent","_proto"):
                        break
                    k += 1
                break
        if name_val:
            rec["Name"] = name_val
            rec["locales"].setdefault("en", {})["name"] = name_val
        if short_val:
            rec["shortName"] = short_val
            rec["locales"].setdefault("en", {})["shortName"] = short_val

        # ---- _props islands (if any) + global sweep for interesting scalars ----
        # (These entries are mostly retextures so this usually yields nothing,
        # but it's harmless and keeps compatibility with other mods.)
        override = {}
        for j, t in enumerate(tokens):
            if clean(t) in ("_props","_Props","props"):
                stop = {"Slots","Grids","Prefab","PrefabPath","handbook","locales",
                        "_type","_proto","_name","_id","_parent","_mergeSlotWithChildren","item"}
                _kv_scan(tokens, j+1, stop, override)

        # token sweep for known scalar keys
        for j in range(len(tokens)-1):
            k_raw = clean(tokens[j]); v_raw = tokens[j+1]
            k_low = k_raw.lower()
            if k_low in INTERESTING_KEYS_LOWER:
                rec["overrideProperties"][CANON[k_low]] = _coerce(v_raw)

        # copy scalars from override (skip nested dicts)
        for k, v in override.items():
            if isinstance(v, (int,float,bool,str)):
                rec["overrideProperties"].setdefault(k, v)

        # ---- Heuristic $type (UI hint only)
        is_weapon = bool(re.search(r'(?i)\bisweapon\s+true\b', chunk))
        rec["$type"] = "Gun" if is_weapon else "WeaponMod"

        records.append((rec["_guid"], rec))

    return records


def safe_load_formulas():
    """
    Import or reload formulas.py. Returns (ok: bool, error_text: str).
    """
    global formulas_mod
    try:
        if FORMULAS_MOD_NAME in sys.modules:
            formulas_mod = importlib.reload(sys.modules[FORMULAS_MOD_NAME])
        else:
            formulas_mod = importlib.import_module(FORMULAS_MOD_NAME)
        return True, ""
    except Exception:
        return False, traceback.format_exc()

def resolve_category(base: dict) -> str:
    """
    Choose the most appropriate category string for this item, using
    the record itself and formulas.PARENT_CLASSES/CATEGORY_ALIASES when available.
    """
    cat = (base.get("$type") or base.get("parentClass") or base.get("ParentClass") or base.get("parent") or "")
    if not cat and formulas_mod and hasattr(formulas_mod, "PARENT_CLASSES"):
        pid = base.get("parent") or base.get("Parent") or base.get("parentId")
        if pid:
            cat = formulas_mod.PARENT_CLASSES.get(pid, "")
    # normalize alias
    if formulas_mod and hasattr(formulas_mod, "CATEGORY_ALIASES"):
        cat = formulas_mod.CATEGORY_ALIASES.get(cat, cat)
    return cat or ""

def resolve_formula_func(category: str):
    """
    Ask formulas.py for the callable (preferred), then fall back to maps.
    """
    if not formulas_mod:
        return None
    # Preferred exported API
    if hasattr(formulas_mod, "get_formula_func"):
        try:
            f = formulas_mod.get_formula_func(category)
            if f:
                return f
        except Exception:
            pass
    # Fallback: scan known maps if present
    for map_name in ("gun_formula_map", "mod_formula_map", "gear_formula_map"):
        m = getattr(formulas_mod, map_name, None)
        if isinstance(m, dict) and category in m:
            return m[category]
    # Try alias
    alias = getattr(formulas_mod, "CATEGORY_ALIASES", {}).get(category)
    if alias:
        return resolve_formula_func(alias)
    return None

def call_formula(func, item_entry: dict, base: dict, template: dict, context: dict) -> dict:
    """
    Call a formula function with flexible signatures:
      (item_entry, base)
      (item_entry, base, template)
      (item_entry, base, template, context)
    """
    try:
        sig = inspect.signature(func)
        argc = len(sig.parameters)
        if argc <= 2:
            return func(item_entry, base)
        elif argc == 3:
            return func(item_entry, base, template)
        else:
            return func(item_entry, base, template, context)
    except Exception as e:
        # bubble up; caller will show error nicely

        try:
            from formulas import get_formula_func
        except ImportError:
            def get_formula_func(_cat):
                return None

APP_ID = "Nate/SPT-Realism-Compat-Tool"
CONFIG_FILE = "spt_compat_tool.ini"

KNOWN_IGNORE_DIRS = { 'bundles','CustomAssortSchemes','CustomBotLoadouts','CustomLootspawnService',
                      'CustomWeaponPresets','images','src','res','locales','quests','traders',
                      '.git','.github','node_modules','dist','build','__pycache__'}

# Path substrings to skip (case-insensitive)
DEFAULT_EXCLUDE_DIR_CONTAINS = [
    "spt-realism",     # prevent duplicates in list; still available for 'realism stats' panel via separate load
    ".git",
    "__pycache__"
]



JSON_EXT = (".json",)
# JS support
JS_EXT = (".js",)
# Which basegame fields to suppress in the Base Game stats block (case-sensitive exact keys)
BASE_HIDE_KEYS = {
    # noise / UI / shop metadata you usually don’t want in a stat preview:
    "Width", "Height", "BackgroundColor", "RagfairType", "ExamineTime",
    "StackMaxSize",  "Prefab", "PrefabPath", "AnimationVariantsNumber",
    "RepairCost", "RepairSpeed"
}

# -------------------------
# HELPERS BELOW THIS LINE
# -------------------------
def get_settings():
    settings = QSettings(CONFIG_FILE, QSettings.IniFormat)
    return settings



def ask_for_folder(title):
    dlg = QFileDialog()
    dlg.setFileMode(QFileDialog.Directory)
    dlg.setOption(QFileDialog.ShowDirsOnly, True)
    dlg.setWindowTitle(title)
    if dlg.exec_():
        return dlg.selectedFiles()[0]
    return ""
def get_mod_name_from_path(path: str, spt_root: str) -> str:
    """
    Return the top-level mod folder name for a given file path,
    e.g., <SPT>/user/mods/<MOD_NAME>/...  -> "<MOD_NAME>"
    If not under mods, label as "(External)".
    """
    mods_root = os.path.join(spt_root, "user", "mods")
    try:
        rel = os.path.relpath(path, mods_root)
    except ValueError:
        return "(External)"
    parts = rel.split(os.sep)
    if parts and parts[0] not in ("..", ".", ""):
        return parts[0]
    return "(External)"

def is_choccy_mod_path(path: str, spt_root: str) -> bool:
    """
    Return True if 'path' is under a mod folder whose name contains 'choccy'
    (case-insensitive). Helps whitelist /src/ JS for those mods.
    """
    mod_name = get_mod_name_from_path(path, spt_root)
    return isinstance(mod_name, str) and ("choccy" in mod_name.lower())

def load_exclude_patterns(settings: QSettings):
    """
    Read user-defined exclude substrings from settings and merge with defaults.
    Settings key: 'exclude_patterns' (comma or semicolon separated).
    """
    user = (settings.value("exclude_patterns", "") or "").strip()
    toks = [t.strip().lower() for t in re.split(r"[;,]", user) if t.strip()]
    # dedupe while preserving order: user first, then defaults
    seen = set()
    out = []
    for t in itertools.chain(toks, DEFAULT_EXCLUDE_DIR_CONTAINS):
        if t and t not in seen:
            out.append(t); seen.add(t)
    return out


def load_example_schema(schema_path: str) -> dict:
    """
    Parse example.json that has comment lines and placeholder values.
    Strategy:
      - Find every `"$itemID": { ... }` block by brace-balance
      - Inside, find the `$type` value; map to bucket: WeaponMod/Gun/Gear/Ammo
      - Collect top-level keys in that block as the allowed set for that bucket
    Returns:
      { "WeaponMod": {keys...}, "Gun": {...}, "Gear": {...}, "Ammo": {...} }
    """
    if not os.path.isfile(schema_path):
        return {}

    txt = open(schema_path, "r", encoding="utf-8", errors="ignore").read()

    # Remove single-line // comments (tolerant)
    txt = re.sub(r"//.*?$", "", txt, flags=re.M)

    buckets = {"WeaponMod": set(), "Gun": set(), "Gear": set(), "Ammo": set()}

    # Scan all " \"$itemID\": { ... } " blocks
    for m in re.finditer(r'"\$itemID"\s*:\s*\{', txt):
        start = m.end() - 1  # at the '{'
        # brace-balance to capture this object's body
        depth, i = 0, start
        while i < len(txt):
            if txt[i] == "{":
                depth += 1
            elif txt[i] == "}":
                depth -= 1
                if depth == 0:
                    block = txt[start:i+1]
                    break
            i += 1
        else:
            continue  # unbalanced, skip

        # Get $type value (as text)
        mtype = re.search(r'"\$type"\s*:\s*"([^"]+)"', block)
        if not mtype:
            continue
        raw_type = mtype.group(1).lower()
        if "weaponmod" in raw_type:
            bucket = "WeaponMod"
        elif "gun" in raw_type:
            bucket = "Gun"
        elif "gear" in raw_type:
            bucket = "Gear"
        elif "ammo" in raw_type:
            bucket = "Ammo"
        else:
            continue

        # Collect top-level keys (quoted) within this block
        for km in re.finditer(r'"([^"]+)"\s*:', block):
            key = km.group(1).strip()
            # Only top-level: cheap heuristic—ignore nested obvious containers by skipping duplicates;
            # the whole block is top-level in the schema template, so keep everything.
            buckets[bucket].add(key)

    return buckets


def classify_realism_type(value: str) -> str:
    """
    Map a $type like 'RealismMod.WeaponMod, RealismMod' or 'WeaponMod'
    into canonical bucket: 'WeaponMod', 'Gun', 'Ammo', 'Gear' (or '').
    """
    if not isinstance(value, str):
        return ""
    v = value.lower()
    if "weaponmod" in v:
        return "WeaponMod"
    if "gun" in v:
        return "Gun"
    if "ammo" in v:
        return "Ammo"
    if "gear" in v:
        return "Gear"
    return ""
def guess_type_bucket(compat: dict, base: dict, template: dict | None) -> str:
    # Prefer explicit compat $type
    ctype = classify_realism_type(compat.get("$type", ""))
    if ctype:
        return ctype

    # Heuristics while formula is incomplete:
    # - WeaponMod: presence of ModType on compat or base
    if isinstance(compat.get("ModType"), str) or isinstance(base.get("ModType"), str):
        return "WeaponMod"

    # - Gun: if compat declares WeapType/OperationType
    if isinstance(compat.get("WeapType"), str) or isinstance(compat.get("OperationType"), str):
        return "Gun"

    # - If template has a $type that names one of the realism classes
    if isinstance(template, dict):
        t = classify_realism_type(template.get("$type", ""))
        if t:
            return t

    return ""

# --- Stat extraction (module-level) ---
STAT_KEYS = [
    "Weight", "Ergonomics",
    "RecoilVertical", "RecoilForceUp", "RecoilForceBack",
    "BaseMalfunctionChance",
    "Damage", "PenetrationPower",
    "mousePenalty", "speedPenaltyPercent", "weaponErgonomicPenalty",
]

def extract_stats(rec: dict) -> dict:
    """
    For Realism templates, return ALL top-level numeric or string stats.
    (Skip arrays and nested dicts for display.)
    """
    if not isinstance(rec, dict):
        return {}
    out = {}
    for k, v in rec.items():
        # Skip metadata fields if you want (e.g., $type, ItemID, Name)
        if k in ("$type", "ItemID", "Name", "_file"):
            continue
        # Show numbers and strings, skip lists/dicts
        if isinstance(v, (int, float, str)):
            out[k] = v
        if isinstance(v, list) and v:
            out[k] = ", ".join(str(x) for x in v)
    return out

# -------------------------
# Dark palette
# -------------------------
def set_dark_palette(app):
    p = QPalette()
    p.setColor(QPalette.Window, QColor(30, 30, 30))
    p.setColor(QPalette.WindowText, Qt.white)
    p.setColor(QPalette.Base, QColor(25, 25, 25))
    p.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
    p.setColor(QPalette.ToolTipBase, Qt.white)
    p.setColor(QPalette.ToolTipText, Qt.white)
    p.setColor(QPalette.Text, Qt.white)
    p.setColor(QPalette.Button, QColor(53, 53, 53))
    p.setColor(QPalette.ButtonText, Qt.white)
    p.setColor(QPalette.BrightText, Qt.red)
    p.setColor(QPalette.Link, QColor(42, 130, 218))
    p.setColor(QPalette.Highlight, QColor(42, 130, 218))
    p.setColor(QPalette.HighlightedText, Qt.black)
    app.setPalette(p)

# -------------------------
# IO / Scanning
# -------------------------
def iter_json_files(root, exclude_contains=None):
    """
    Yield *.json files under root, skipping directories/files whose path
    contains any token from `exclude_contains` (case-insensitive).
    If not provided, fall back to DEFAULT_EXCLUDE_DIR_CONTAINS.
    """
    if exclude_contains is None:
        exclude_contains = DEFAULT_EXCLUDE_DIR_CONTAINS

    for dirpath, dirnames, filenames in os.walk(root):
        # drop dirs by exact name
        dirnames[:] = [d for d in dirnames if d not in KNOWN_IGNORE_DIRS]
        # drop dirs that contain any banned substring (case-insensitive)
        dirnames[:] = [d for d in dirnames if not any(bad in d.lower() for bad in exclude_contains)]

        # skip entire branch if path already includes an excluded token
        lower_dirpath = dirpath.lower()
        if any(bad in lower_dirpath for bad in exclude_contains):
            continue

        for f in filenames:
            if f.endswith(JSON_EXT):
                fp = os.path.join(dirpath, f)
                if any(bad in fp.lower() for bad in exclude_contains):
                    continue
                yield fp
def safe_json_load(path):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return None

def iter_massivesoft_js_files(spt_path: str):
    """
    Yield *.js files ONLY from:
        <SPT>/user/mods/Massivesoft-Guns/src/scripts/
    Ignores the global 'src' blacklist for this one mod.
    Returns nothing if the mod or the scripts folder doesn't exist.
    """
    mods_root = os.path.join(spt_path, "user", "mods")
    if not os.path.isdir(mods_root):
        return
    # Resolve the Massivesoft folder in a case-insensitive way
    massive_dir = None
    try:
        for d in os.listdir(mods_root):
            if d.lower() == "massivesoft-guns":
                massive_dir = os.path.join(mods_root, d)
                break
    except Exception:
        return
    if not (massive_dir and os.path.isdir(massive_dir)):
        return

    base = os.path.join(massive_dir, "src", "scripts")
    if not os.path.isdir(base):
        return

    for dirpath, dirnames, filenames in os.walk(base):
        for f in filenames:
            if f.endswith(JS_EXT):
                yield os.path.join(dirpath, f)

def unwrap_records(obj, path):
    """
    Normalize JSONs:
      - envelope: { "<id>": {...} }
      - list: [ {...}, {...} ]
      - object: {...}
    Returns list of (id, record_dict)
    """
    out = []
    if isinstance(obj, dict) and obj and all(isinstance(v, dict) for v in obj.values()):
        for k, v in obj.items():
            rec = dict(v)
            rec["_guid"] = k
            rec["_file"] = path
            out.append((k, rec))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            if isinstance(v, dict):
                rec = dict(v)
                rec["_guid"] = v.get("id") or v.get("_id") or f"{os.path.basename(path)}:{i}"
                rec["_file"] = path
                out.append((rec["_guid"], rec))
    elif isinstance(obj, dict):
        rec = dict(obj)
        rec["_guid"] = obj.get("id") or obj.get("_id") or os.path.basename(path)
        rec["_file"] = path
        out.append((rec["_guid"], rec))
    return out
def get_base_props_dict(rec: dict) -> dict:
    """
    Return the best-available _props dict for a record, supporting JSON styles:
      - top-level _props
      - item._props
      - items._props
    """
    if not isinstance(rec, dict):
        return {}
    p = rec.get("_props")
    if isinstance(p, dict):
        return p
    for k in ("item", "items"):
        it = rec.get(k)
        if isinstance(it, dict):
            p = it.get("_props")
            if isinstance(p, dict):
                return p
    return {}


def normalize_json_style_record(rec: dict):
    """
    Mutate `rec` in-place so downstream UI always sees a consistent shape:
      - Promote item/_props -> rec["_props"]
      - Flatten handbook: set rec["parent"] and surface Price into overrideProperties
      - Flatten Prefab path: overrideProperties.Prefab.path + overrideProperties.PrefabPath
      - Normalize Name/ShortName on top-level from locales or _props
    """
    if not isinstance(rec, dict):
        return

    # 1) Promote nested _props
    base_props = get_base_props_dict(rec)
    if base_props and "_props" not in rec:
        rec["_props"] = base_props  # promote for display / formulas

    # 2) Prefab path flatten (string for Base panel)
    try:
        pf = base_props.get("Prefab", {})
        if isinstance(pf, dict):
            ppath = pf.get("path")
            if isinstance(ppath, str) and ppath.strip():
                rec.setdefault("overrideProperties", {}).setdefault("Prefab", {})["path"] = ppath
                rec["overrideProperties"].setdefault("PrefabPath", ppath)
    except Exception:
        pass

    # 3) Handbook → parent + price (accept GUID or text)
    hb = rec.get("handbook") or rec.get("Handbook")
    if isinstance(hb, dict):
        pid = (hb.get("ParentId") or hb.get("parentId") or
               hb.get("Parent")   or hb.get("parent"))
        if isinstance(pid, str) and pid.strip():
            rec["parent"] = pid.strip()
        price = hb.get("Price")
        if isinstance(price, (int, float)):
            rec.setdefault("overrideProperties", {})["Price"] = int(price)

    # 4) Normalize Name / ShortName to top-level
    # Priority: locales.en -> locales.any -> _props.Name/ShortName
    def _from_locales(lc: dict) -> tuple[str, str]:
        if not isinstance(lc, dict):
            return "", ""
        # prefer en
        en = lc.get("en")
        if isinstance(en, dict):
            return (str(en.get("Name") or en.get("name") or "") or "",
                    str(en.get("ShortName") or en.get("shortName") or "") or "")
        # else first any language
        for lang in lc.values():
            if isinstance(lang, dict):
                n = str(lang.get("Name") or lang.get("name") or "") or ""
                s = str(lang.get("ShortName") or lang.get("shortName") or "") or ""
                if n or s:
                    return n, s
        return "", ""

    n, s = _from_locales(rec.get("locales") or rec.get("_locales") or {})
    if not n:
        n = str(base_props.get("Name") or base_props.get("name") or rec.get("_name") or "")
    if not s:
        s = str(base_props.get("ShortName") or base_props.get("shortName") or "")

    if n:
        rec["Name"] = n
    if s:
        rec["shortName"] = s

    # 5) $type hint (optional)
    if isinstance(rec.get("isweapon"), bool):
        rec["$type"] = "Gun" if rec["isweapon"] else "WeaponMod"


def iter_js_files(root, exclude_contains=None, spt_root: str = ""):
    """
    Yield *.js files under root, skipping by exclude_contains.
    Special-case: if the path is inside a 'choccy' mod, DO NOT drop 'src' from dirnames.
    """
    if exclude_contains is None:
        exclude_contains = DEFAULT_EXCLUDE_DIR_CONTAINS

    for dirpath, dirnames, filenames in os.walk(root):
        # drop dirs by exact name, BUT keep 'src' for choccy mods
        if is_choccy_mod_path(dirpath, spt_root):
            dirnames[:] = [d for d in dirnames if d not in KNOWN_IGNORE_DIRS or d.lower() == "src"]
        else:
            dirnames[:] = [d for d in dirnames if d not in KNOWN_IGNORE_DIRS]

        # drop dirs that contain any banned substring (case-insensitive)
        dirnames[:] = [d for d in dirnames if not any(bad in d.lower() for bad in exclude_contains)]

        # skip entire branch if path already includes an excluded token
        lower_dirpath = dirpath.lower()
        if any(bad in lower_dirpath for bad in exclude_contains):
            continue

        for f in filenames:
            if f.endswith(JS_EXT):
                fp = os.path.join(dirpath, f)
                if any(bad in fp.lower() for bad in exclude_contains):
                    continue
                yield fp

# --------- Mass_* JS reader (no evaluation) ---------
def parse_mass_js_file_records(path: str):
    """
    Parse a Mass_* style .js file that contains:
      const IDDL = { KEY: "MongoID", ... };
      this.data = { keyName: { itemTplToClone: IDDL.X, newId: IDDL.Y, overrideProperties:{...}, locales:{...} }, ... };

    Returns: list of (id_key, record_dict)
             - id_key becomes _guid (your tooling expects a per-record id)
             - record_dict carries fields similar to JSON items so the rest of your tool can reuse them
    """
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            js_text = f.read()
    except Exception:
        return []

    def _brace_balanced_slice(src: str, start_open_idx: int) -> str:
        depth = 0
        i = start_open_idx
        while i < len(src):
            ch = src[i]
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    return src[start_open_idx:i+1]
            i += 1
        raise ValueError("Unbalanced braces while parsing JS object")

    def _find_block_after(anchor_pat: str) -> str | None:
        m = re.search(anchor_pat, js_text)
        if not m:
            return None
        brace = js_text.find('{', m.end())
        if brace == -1:
            return None
        return _brace_balanced_slice(js_text, brace)

    # 1) Build IDDL mapping
    iddl_map = {}
    iddl_block = _find_block_after(r"const\s+IDDL\s*=")
    if iddl_block:
        for k, v in re.findall(r'(\w+)\s*:\s*"([^"]+)"', iddl_block):
            iddl_map[k] = v

    # 2) Find this.data = { ... }
    data_block = _find_block_after(r"this\.data\s*=")
    if not data_block:
        return []

    inner = data_block[1:-1]  # strip outer braces
    records = []

    i = 0
    while i < len(inner):
        # skip whitespace/commas
        while i < len(inner) and inner[i] in " \r\n\t,":
            i += 1
        if i >= len(inner): break

        # read key (top-level entry name)
        ks = i
        while i < len(inner) and re.match(r"[\w$]", inner[i]):
            i += 1
        key = inner[ks:i].strip()
        # find the object body
        colon = inner.find(':', i)
        if colon == -1: break
        brace = inner.find('{', colon)
        if brace == -1: break
        body = _brace_balanced_slice(inner, brace)
        i = brace + len(body)

        # helpers to extract values
        def _resolve_id(expr: str) -> str | None:
            expr = expr.strip()
            m = re.search(r'IDDL\.(\w+)', expr)
            if m:
                return iddl_map.get(m.group(1), f"IDDL.{m.group(1)}")
            m2 = re.search(r'"([^"]+)"', expr)
            return m2.group(1) if m2 else None

        def _extract_field(b: str, field: str) -> str | None:
            m = re.search(rf"\b{re.escape(field)}\s*:\s*([^,\n\r]+)", b)
            return m.group(1).strip() if m else None

        def _extract_subobj(b: str, field: str) -> str:
            m = re.search(rf"{re.escape(field)}\s*:\s*\{{", b)
            if not m: return ""
            return _brace_balanced_slice(b, m.end()-1)

        def _extract_number(ov: str, fld: str):
            m = re.search(rf"\b{re.escape(fld)}\s*:\s*([-]?\d+(?:\.\d+)?)\b", ov)
            return float(m.group(1)) if m else None

        def _extract_prefab_path(ov: str):
            m = re.search(r'Prefab\s*:\s*\{[^}]*\bpath\s*:\s*"([^"]+)"', ov, flags=re.S)
            return m.group(1) if m else None

        def _extract_en_locale(b: str):
            # returns {"name":..., "shortName":...} where found
            loc = {}
            m = re.search(r'locales\s*:\s*\{[^}]*"en"\s*:\s*\{(.*?)\}', body, flags=re.S)
            if m:
                section = m.group(1)
                n = re.search(r'"name"\s*:\s*"([^"]+)"', section)
                s = re.search(r'"shortName"\s*:\s*"([^"]+)"', section)
                if n: loc["name"] = n.group(1)
                if s: loc["shortName"] = s.group(1)
            return loc

        tpl_expr = _extract_field(body, "itemTplToClone")
        new_expr = _extract_field(body, "newId")
        itemTplToClone = _resolve_id(tpl_expr) if tpl_expr else None
        newId = _resolve_id(new_expr) if new_expr else None

        ov = _extract_subobj(body, "overrideProperties")
        weight = _extract_number(ov, "Weight")
        ergo   = _extract_number(ov, "Ergonomics")
        recoil = _extract_number(ov, "Recoil")
        prefab = _extract_prefab_path(ov)
        enloc  = _extract_en_locale(body)

        # synthesize a “mod item” record that looks like JSON inputs your tool already handles
        rec = {
            "_file": path,
            "_guid": newId or f"{os.path.basename(path)}:{key}",  # stable id for UI
            "itemTplToClone": itemTplToClone,
            "newId": newId,
            "overrideProperties": {},
            "locales": {"en": enloc} if enloc else {}
        }

        if prefab:
            rec["overrideProperties"]["Prefab"] = {"path": prefab}
        if weight is not None:
            rec["overrideProperties"]["Weight"] = weight
        if ergo is not None:
            rec["overrideProperties"]["Ergonomics"] = ergo
        if recoil is not None:
            rec["overrideProperties"]["Recoil"] = recoil

        # (Optional) hint for UI only
        if key.lower().startswith("weapon"):
            rec["$type"] = "Weapon"
        else:
            rec["$type"] = "WeaponMod"

        records.append((rec["_guid"], rec))

    return records
def parse_choccy_js_file_records(path: str):
    """
    Parse a 'choccy' mod JS file under /src (compiled TS style).
    Detects 24-hex enums like:
        EnumName["KEY"] = "24hexguid";
    Finds:
      - const VAR = { itemTplToClone, newId, overrideProperties:{...}, locales:{...}, parentId|handbookParentId, ... }
      - customitem.createItemFromClone(VAR)

    Returns: list of (guid, record_dict)
    """
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            js = f.read()
    except Exception:
        return []

    # --- Build ALL enum maps that assign 24-hex values ---
    # Pattern captures: EnumName["KEY"] = "24hex"
    enum_maps: dict[str, dict[str, str]] = {}
    for m in re.finditer(r'([A-Za-z_]\w*)\s*\[\s*"([^"]+)"\s*\]\s*=\s*"([0-9a-fA-F]{24})"', js):
        enum_name, key, gid = m.group(1), m.group(2), m.group(3)
        enum_maps.setdefault(enum_name, {})[key] = gid

    # --- Helper: brace-balanced slice ---
    def _brace_balanced_slice(src: str, start_open_idx: int) -> str:
        depth = 0
        i = start_open_idx
        while i < len(src):
            ch = src[i]
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    return src[start_open_idx:i+1]
            i += 1
        raise ValueError("Unbalanced braces while parsing JS object")

    # --- Collect const VAR = { ... } objects ---
    var_to_obj = {}
    for m in re.finditer(r'\bconst\s+([A-Za-z_]\w*)\s*=\s*\{', js):
        var = m.group(1)
        try:
            body = _brace_balanced_slice(js, m.end() - 1)  # includes outer braces
        except Exception:
            continue
        var_to_obj[var] = body

    # --- Which ones get created? ---
    created = set()
    for m in re.finditer(r'createItemFromClone\(\s*([A-Za-z_]\w*)\s*\)', js):
        created.add(m.group(1))

    # --- Extract helpers ---
    def _resolve_id(expr: str) -> str | None:
        """
        Resolve:
          - "24hex"
          - EnumName["KEY"]
          - (prefixes.)EnumName.KEY   e.g., exports_1.EnumName.KEY, ItemTpl_1.ItemTpl.KEY
        """
        if not expr:
            return None
        expr = expr.strip()

        # 1) literal GUID in quotes
        m = re.search(r'"([0-9a-fA-F]{24})"', expr)
        if m:
            return m.group(1)

        # 2) bracket enum use: EnumName["KEY"]
        m = re.search(r'([A-Za-z_]\w*)\s*\[\s*"([^"]+)"\s*\]', expr)
        if m:
            enum_name, key = m.group(1), m.group(2)
            mp = enum_maps.get(enum_name)
            if mp and key in mp:
                return mp[key]

        # 3) dotted enum use with any qualifier chain: (something.)EnumName.KEY
        #    Capture the last two identifiers as EnumName.KEY, ignoring prefixes.
        #    Examples: exports.WeapID.WEAP_RAFFICA, exports_1.WeaponIds.KSG12, ItemTpl_1.ItemTpl.SHOTGUN_...
        parts = [p for p in re.split(r'[^A-Za-z0-9_\.]', expr) if p]
        # Search each dot-segment candidate for EnumName.KEY
        for token in parts:
            if '.' not in token:
                continue
            segs = token.split('.')
            # Walk pairs from the end: (..., EnumName, KEY)
            for i in range(len(segs) - 1):
                enum_name = segs[i]
                key_name  = segs[i+1]
                # Accept only if enum exists and key maps to GUID
                mp = enum_maps.get(enum_name)
                if mp and key_name in mp:
                    return mp[key_name]

        return None

    def _extract_field(obj_text: str, field: str) -> str | None:
        # tolerate: field: <expr> (expr may be string literal, EnumName.KEY, number, etc.)
        m = re.search(rf'\b{re.escape(field)}\s*:\s*([^,\n\r]+)', obj_text)
        return m.group(1).strip() if m else None

    def _extract_number(obj_text: str, field: str):
        m = re.search(rf'\b{re.escape(field)}\s*:\s*([-]?\d+(?:\.\d+)?)\b', obj_text)
        return float(m.group(1)) if m else None

    def _extract_bool(obj_text: str, field: str):
        m = re.search(rf'\b{re.escape(field)}\s*:\s*(true|false)\b', obj_text)
        if not m: return None
        return m.group(1) == "true"

    def _extract_prefab_path(obj_text: str) -> str | None:
        m_ov = re.search(r'\boverrideProperties\s*:\s*\{', obj_text)
        if not m_ov:
            return None
        try:
            ov = _brace_balanced_slice(obj_text, m_ov.end() - 1)
        except Exception:
            return None
        m = re.search(r'Prefab\s*:\s*\{[^}]*\bpath\s*:\s*"([^"]+)"', ov, flags=re.S)
        return m.group(1) if m else None

    def _extract_locales_en(obj_text: str) -> dict:
        loc = {}
        m = re.search(r'locales\s*:\s*\{', obj_text)
        if not m:
            return loc
        try:
            locales_obj = _brace_balanced_slice(obj_text, m.end() - 1)
        except Exception:
            return loc
        m_en = re.search(r'"en"\s*:\s*\{', locales_obj)
        if not m_en:
            return loc
        try:
            en_obj = _brace_balanced_slice(locales_obj, m_en.end() - 1)
        except Exception:
            return loc
        def grab(k: str) -> str:
            m = re.search(rf'\b{k}\s*:\s*"([^"]+)"', en_obj)
            return m.group(1) if m else ""
        loc["name"] = grab("name")
        loc["shortName"] = grab("shortName")
        loc["description"] = grab("description")
        return loc

    def _extract_override_scalars(obj_text: str) -> dict:
        out = {}
        m_ov = re.search(r'\boverrideProperties\s*:\s*\{', obj_text)
        if not m_ov:
            return out
        try:
            ov = _brace_balanced_slice(obj_text, m_ov.end() - 1)
        except Exception:
            return out
        for fld in ("Weight","Ergonomics","Recoil","RecoilForceUp","RecoilForceBack",
                    "Velocity","Loudness","BaseMalfunctionChance"):
            m = re.search(rf'\b{fld}\s*:\s*([-]?\d+(?:\.\d+)?)\b', ov)
            if m:
                val = float(m.group(1))
                out[fld] = int(val) if val.is_integer() else val
        for fld in ("ExaminedByDefault","NoFiremodeOnBoltcatch","IsAnimated","CompactHandling",
                    "AllowFeed","AllowJam","AllowMisfire","AllowSlide","AllowOverheat"):
            b = _extract_bool(ov, fld)
            if b is not None:
                out[fld] = b
        return out

    records = []
    for var in created:
        obj = var_to_obj.get(var)
        if not obj:
            continue

        itemTpl_expr = _extract_field(obj, "itemTplToClone")
        newId_expr   = _extract_field(obj, "newId")
        parent_expr  = (_extract_field(obj, "parentId") or
                        _extract_field(obj, "handbookParentId"))

        itemTplToClone = _resolve_id(itemTpl_expr or "")
        newId          = _resolve_id(newId_expr or "")
        parent_id      = _resolve_id(parent_expr or "")

        # (extra) Literal fallback for parent if resolver missed it
        if not parent_id and parent_expr:
            m = re.search(r'"([0-9a-fA-F]{24})"', parent_expr)
            if m:
                parent_id = m.group(1)

        en = _extract_locales_en(obj)
        pref_path = _extract_prefab_path(obj)
        ov_scalars = _extract_override_scalars(obj)

        rec = {
            "_file": path,
            "_guid": newId or f"{os.path.basename(path)}:{var}",  # prefer resolved GUID
            "newId": newId,
            "itemTplToClone": itemTplToClone,
            "overrideProperties": {},
            "locales": {}
        }
        if parent_id:
            rec["parent"] = parent_id

        if pref_path:
            rec["overrideProperties"].setdefault("Prefab", {})["path"] = pref_path
            rec["overrideProperties"]["PrefabPath"] = pref_path

        for k, v in ov_scalars.items():
            rec["overrideProperties"][k] = v

        if en:
            if en.get("name"):
                rec["Name"] = en["name"]
                rec["locales"].setdefault("en", {})["name"] = en["name"]
            if en.get("shortName"):
                rec["shortName"] = en["shortName"]
                rec["locales"].setdefault("en", {})["shortName"] = en["shortName"]

        # Gun hint if likely a weapon
        is_gun = bool(re.search(r'\bweapFireType\s*:\s*\[', obj) or
                      re.search(r'\bbFirerate\s*:', obj) or
                      re.search(r'\bRecoilForceUp\s*:', obj) or
                      re.search(r'\bammoCaliber\s*:', obj))
        rec["$type"] = "Gun" if is_gun else "WeaponMod"

        records.append((rec["_guid"], rec))

    return records

def map_parent_to_formula_category(parent: str) -> str:
    """
    Convert a handbook parent (GUID or text) into a formula category string
    using formulas.HANDBOOK_TO_FORMULA and PARENT_CLASSES/CATEGORY_ALIASES.
    Returns "" if nothing maps.
    """
    if not isinstance(parent, str) or not parent.strip():
        return ""
    p = parent.strip()

    # If GUID -> translate via PARENT_CLASSES to a textual class first
    if re.fullmatch(r"[0-9a-fA-F]{24}", p):
        if formulas_mod and hasattr(formulas_mod, "PARENT_CLASSES"):
            txt = formulas_mod.PARENT_CLASSES.get(p, "")
            p = txt or p  # if unknown, keep GUID (we'll try to map directly)

    # Normalize alias if available
    if formulas_mod and hasattr(formulas_mod, "CATEGORY_ALIASES"):
        p = formulas_mod.CATEGORY_ALIASES.get(p, p)

    # 1) Direct mapping via HANDBOOK_TO_FORMULA
    hbmap = getattr(formulas_mod, "HANDBOOK_TO_FORMULA", {})
    if isinstance(hbmap, dict):
        cat = hbmap.get(p)
        if isinstance(cat, str) and cat.strip():
            return cat.strip()

    # 2) Some teams place the same map under FORMULA_CATEGORY_MAP
    catmap = getattr(formulas_mod, "FORMULA_CATEGORY_MAP", {})
    if isinstance(catmap, dict):
        cat = catmap.get(p)
        if isinstance(cat, str) and cat.strip():
            return cat.strip()

    return ""

# -------------------------
# Template index
# -------------------------
class CompatTemplateIndex:
    """
    Holds compat-template-like objects; we treat any record as a potential template
    if it exposes fields we can use to bind to a base item:
      - ItemID or id/ItemId as "target"
      - parent or parentClass/$type as category
    """
    def __init__(self):
        self.by_target = defaultdict(list)   # target_id -> [template_record, ...]
        self.all_templates = []              # every template-like record
        self.by_parent = defaultdict(list)   # parentClass/$type -> [template_record, ...]
        self.by_parent_id = defaultdict(list)   #  strict parent ID map


    def add(self, rec):
        # Identify likely target id
        target = (rec.get("ItemID") or rec.get("ItemId") or rec.get("id") or rec.get("_guid"))
        parent = (rec.get("parentClass") or rec.get("ParentClass") or rec.get("$type") or rec.get("parent"))
        is_template_like = bool(target) or bool(parent)
        if not is_template_like:
            return
        self.all_templates.append(rec)
        if target:
            self.by_target[str(target)].append(rec)
        if parent:
            self.by_parent[str(parent)].append(rec)
        pid = rec.get("parent") or rec.get("Parent") or rec.get("parentId")
        if pid:
            self.by_parent_id[str(pid)].append(rec)


    def match_by_item(self, item):
        # Gather possible “clone/tpl” values from the base item
        candidate_ids = []
        for key in ("itemTplToClone","itemtpltoclone","clone","tpl","_tpl","id","_id","_guid"):
            v = item.get(key)
            if v:
                candidate_ids.append(str(v))
        candidate_ids = list(dict.fromkeys(candidate_ids))  # dedupe, preserve order
        matches = []
        for cid in candidate_ids:
            matches.extend(self.by_target.get(cid, []))

        item_parent_id = item.get("parent") or item.get("Parent") or item.get("parentId")
        if not matches and item_parent_id:
            matches.extend(self.by_parent_id.get(str(item_parent_id), []))

        # If still none, try parent class / $type / generic "parent" bucket
        if not matches:
            parent = (item.get("parentClass") or item.get("ParentClass") or item.get("$type") or item.get("parent"))
            if parent:
                matches.extend(self.by_parent.get(str(parent), []))

        # Deduplicate while preserving order
        seen, uniq = set(), []
        for m in matches:
            mid = id(m)
            if mid not in seen:
                seen.add(mid)
                uniq.append(m)

        return uniq, candidate_ids

def normalize_json_style_record(rec: dict):
    """
    Mutate `rec` in-place so your UI always sees a consistent shape.

    - Promote item/_props → rec["_props"]
    - Flatten handbook: set rec["parent"] and surface Price into overrideProperties
    - Flatten Prefab path: overrideProperties.Prefab.path + overrideProperties.PrefabPath
    - Keep locales as-is (get_display_name already uses it)
    """
    if not isinstance(rec, dict):
        return

    # 1) Promote nested _props (supports 'item' or 'items')
    base_props = get_base_props_dict(rec)
    if base_props and "_props" not in rec:
        rec["_props"] = base_props  # promote for downstream code

    # 2) Flatten Prefab path if present in _props
    try:
        pf = base_props.get("Prefab", {})
        if isinstance(pf, dict):
            ppath = pf.get("path")
            if isinstance(ppath, str) and ppath.strip():
                rec.setdefault("overrideProperties", {}).setdefault("Prefab", {})["path"] = ppath
                rec["overrideProperties"].setdefault("PrefabPath", ppath)
    except Exception:
        pass

    # 3) Flatten handbook -> parent + price
    hb = rec.get("handbook") or rec.get("Handbook")
    if isinstance(hb, dict):
        pid = (hb.get("ParentId") or hb.get("parentId") or
               hb.get("Parent")   or hb.get("parent"))
        if isinstance(pid, str) and pid.strip():
            # Let mod's handbook parent take precedence
            rec["parent"] = pid.strip()
        price = hb.get("Price")
        if isinstance(price, (int, float)):
            rec.setdefault("overrideProperties", {})["Price"] = int(price)

    # 4) $type hint for UI (optional)
    if "isweapon" in rec and isinstance(rec["isweapon"], bool):
        rec["$type"] = "Gun" if rec["isweapon"] else "WeaponMod"
# -------------------------
# Build full index from SPT path
# -------------------------


class SPTIndex:
    def __init__(self, spt_path, compat_root=None, exclude_contains=None):
        self.spt_path = spt_path
        self.compat_root = compat_root
        self.exclude_contains = (exclude_contains or DEFAULT_EXCLUDE_DIR_CONTAINS)
        self.items = []                           # displayable (filtered) records
        self.items_by_mod = defaultdict(list)
        self.name_map = {}                        # id/guid -> resolved name
        self.template_index = CompatTemplateIndex()
        # --- Counters for console logging ---
        self.count_json_files = 0
        self.count_json_records = 0
        self.count_js_files = 0
        self.count_js_records = 0
        self.count_mass_js_files = 0
        self.count_mass_js_records = 0


    def scan(self):
        """Scan only <SPT>/user/mods and (optionally) a compat_root folder."""
        def record_is_displayable(rec: dict) -> bool:
            # treat a record as display-worthy if it carries _props or overrideProperties,
            # possibly one level deep; case-insensitive on the key name.
            if not isinstance(rec, dict):
                return False
            for k in rec.keys():
                kl = k.lower()
                if kl == "_props" or kl == "overrideproperties":
                    return True
            for v in rec.values():
                if isinstance(v, dict):
                    for k2 in v.keys():
                        kl2 = k2.lower()
                        if kl2 == "_props" or kl2 == "overrideproperties":
                            return True
            return False

        self.items.clear()
        self.items_by_mod.clear()
        self.name_map.clear()
        # reset counters
        self.count_json_files = 0
        self.count_json_records = 0
        self.count_js_files = 0
        self.count_js_records = 0
        self.count_mass_js_files = 0
        self.count_mass_js_records = 0

        # keep template_index; we are going to re-fill it
        self.template_index = CompatTemplateIndex()

        scan_roots = [os.path.join(self.spt_path, "user", "mods")]
        if self.compat_root and os.path.isdir(self.compat_root):
            scan_roots.append(self.compat_root)

        for root in scan_roots:
            if not os.path.isdir(root):
                continue

            
            for path in iter_json_files(root, self.exclude_contains):
                if any(bad in path.lower() for bad in self.exclude_contains):
                    continue

                obj = safe_json_load(path)

                # A) If json.load() failed, try the compact items.json format
                if obj is None:
                    compact_records = parse_compact_items_json(path)
                    if compact_records:
                        self.count_json_files += 1  # still a file we parsed
                        mod_name = get_mod_name_from_path(path, self.spt_path)
                        for rid, rec in compact_records:
                            self.count_json_records += 1
                            rec["_mod"] = mod_name
                            nm = get_display_name(rec)
                            self.name_map[str(rid)] = nm

                            # same displayability predicate
                            def record_is_displayable(loc_rec: dict) -> bool:
                                if not isinstance(loc_rec, dict):
                                    return False
                                if any(k.lower() in ("_props", "overrideproperties") for k in loc_rec.keys()):
                                    return True
                                for v in loc_rec.values():
                                    if isinstance(v, dict) and any(
                                        k2.lower() in ("_props", "overrideproperties") for k2 in v.keys()
                                    ):
                                        return True
                                return False

                            if record_is_displayable(rec):
                                self.items.append(rec)
                                self.items_by_mod[mod_name].append(rec)

                            self.template_index.add(rec)

                        # handled as compact; go to next file
                        continue

                    # Neither valid JSON nor compact format -> skip file
                    continue

                # B) Normal JSON handling (obj is dict/list)
                self.count_json_files += 1
                mod_name = get_mod_name_from_path(path, self.spt_path)

                for rid, rec in unwrap_records(obj, path):
                    # normalize JSON-style records so _props/handbook/locales are usable
                    normalize_json_style_record(rec)

                    self.count_json_records += 1
                    rec["_mod"] = mod_name

                    nm = get_display_name(rec)
                    self.name_map[str(rid)] = nm

                    if record_is_displayable(rec):
                        self.items.append(rec)
                        self.items_by_mod[mod_name].append(rec)

                    self.template_index.add(rec)


            
            # ----------  JS scan (Mass_* style) ----------
            
            for path in iter_js_files(root, self.exclude_contains, spt_root=self.spt_path):
                if any(bad in path.lower() for bad in self.exclude_contains):
                    continue

                
                
                p_norm = path.replace("\\", "/").lower()

                # guard: ignore /src/scripts unless Massivesoft or Choccy 
                if "/src/" in p_norm:
                    mod_name_generic = get_mod_name_from_path(path, self.spt_path)
                    if ("massivesoft-guns" not in mod_name_generic.lower()) and ("choccy" not in mod_name_generic.lower()):
                        # Not a whitelisted mod; skip JS under /src/
                        continue


                self.count_js_files += 1

                mod_name = get_mod_name_from_path(path, self.spt_path)
                try:
                    js_records = parse_mass_js_file_records(path)
                except Exception:
                    js_records = []

                # If nothing matched Massivesoft shape, try choccy shape
                if not js_records:
                    try:
                        js_records = parse_choccy_js_file_records(path)
                    except Exception:
                        js_records = []

                self.count_js_records += len(js_records)
                for rid, rec in js_records:
                    rec["_mod"] = mod_name
                    nm = get_display_name(rec)
                    self.name_map[str(rid)] = nm

                    # Use the same (correct) display predicate as JSON path
                    def record_is_displayable(loc_rec: dict) -> bool:
                        if not isinstance(loc_rec, dict):
                            return False
                        if any(k.lower() in ("_props", "overrideproperties") for k in loc_rec.keys()):
                            return True
                        for v in loc_rec.values():
                            if isinstance(v, dict) and any(k2.lower() in ("_props", "overrideproperties") for k2 in v.keys()):
                                return True
                        return False

                    if record_is_displayable(rec):
                        self.items.append(rec)
                        self.items_by_mod[mod_name].append(rec)

                    self.template_index.add(rec)

            # ---------- Massivesoft-only JS scan (src/scripts only) ----------
            # NOTE: this must be at the SAME indentation level as the generic js loop above,
            #       i.e. still inside "for root in scan_roots:" but NOT nested inside that js loop.
            for path in iter_massivesoft_js_files(self.spt_path):
                self.count_mass_js_files += 1
                mod_name = "Massivesoft-Guns"
                try:
                    js_records = parse_mass_js_file_records(path)
                except Exception:
                    js_records = []

                # If nothing matched Massivesoft shape, try choccy shape
                if not js_records:
                    try:
                        js_records = parse_choccy_js_file_records(path)
                    except Exception:
                        js_records = []

                self.count_mass_js_records += len(js_records)
                for rid, rec in js_records:
                    rec["_mod"] = mod_name
                    nm = get_display_name(rec)
                    self.name_map[str(rid)] = nm

                    # FIXED: proper, case-insensitive check
                    def record_is_displayable(loc_rec: dict) -> bool:
                        if not isinstance(loc_rec, dict):
                            return False
                        if any(k.lower() in ("_props", "overrideproperties") for k in loc_rec.keys()):
                            return True
                        for v in loc_rec.values():
                            if isinstance(v, dict) and any(k2.lower() in ("_props", "overrideproperties") for k2 in v.keys()):
                                return True
                        return False

                    if record_is_displayable(rec):
                        self.items.append(rec)
                        self.items_by_mod[mod_name].append(rec)

                    self.template_index.add(rec)

                # ------ Summary logging ------
        print(
            "Indexed: "
            f"{self.count_json_files} JSON file(s), {self.count_json_records} record(s); "
            f"{self.count_js_files} generic JS file(s), {self.count_js_records} record(s); "
            f"{self.count_mass_js_files} Massivesoft JS file(s), {self.count_mass_js_records} record(s)."
        )
        print(
            f"Visible items in tree: {len(self.items)} across {len(self.items_by_mod)} mod(s); "
            f"Templates indexed: {len(self.template_index.all_templates)}"
        )





    def display_name_for(self, rec):
        nm = get_display_name(rec)
        if nm and nm != "Unknown":
            return nm
        # Try any known IDs we cached
        for k in ("id", "_id", "_guid", "tpl", "_tpl", "itemTplToClone", "itemtpltoclone"):
            v = rec.get(k)
            if v and str(v) in self.name_map:
                return self.name_map[str(v)]
        return nm




class BaseGameDB:
    def __init__(self, spt_path, exclude_contains):
        self.spt_path = spt_path
        self.exclude_contains = exclude_contains
        self.by_id = {}

    def scan(self):
        # Load items_master.json from the script's directory
        script_dir = os.path.dirname(os.path.abspath(__file__))
        master_path = os.path.join(script_dir, "items_master.json")
        if not os.path.isfile(master_path):
            print(f"items_master.json not found at {master_path}")
            return
        try:
            import json
            with open(master_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Assume data is a dict of {id: record} or a list of records
            if isinstance(data, dict):
                for k, rec in data.items():
                    self.by_id[k] = rec
            elif isinstance(data, list):
                for rec in data:
                    for key in ("id", "_id", "_guid", "tpl", "_tpl"):
                        v = rec.get(key)
                        if isinstance(v, str) and v.strip():
                            self.by_id.setdefault(v.strip(), rec)
            print(f"Loaded {len(self.by_id)} base items from items_master.json")
        except Exception as e:
            print(f"Failed to load items_master.json: {e}")

class RealismDB:
    """
    Loads Realism-modified stats from any mod path containing 'spt-realism'
    (case-insensitive). These are NOT shown in the left tree; lookups only.
    """
    def __init__(self, spt_path):
        self.spt_path = spt_path
        self.by_id = {}

    def scan(self):
        mods_root = os.path.join(self.spt_path, "user", "mods")
        if not os.path.isdir(mods_root):
            return
        for mod in os.listdir(mods_root):
            if "spt-realism" not in mod.lower():
                continue
            base = os.path.join(mods_root, mod)
            # Important: don't use the user excludes here; we WANT realism stats
            for path in iter_json_files(base, []):
                obj = safe_json_load(path)
                if obj is None:
                    continue
                for rid, rec in unwrap_records(obj, path):
                    for key in ("ItemID", "id", "_id", "_guid", "tpl", "_tpl"):
                        v = rec.get(key)
                        if isinstance(v, str) and v.strip():
                            self.by_id.setdefault(v.strip(), rec)


class UserTemplatesDB:
    r"""
    Loads user-created compats from:
      <SPT>/user/mods/SPT-Realism/db/templates/user_templates
    Each file is expected to be an envelope: { "<ItemID>": { ... compat ... }, ... }
    """
    def __init__(self, spt_path):

        self.spt_path = spt_path
        self.by_id = {}           # ItemID -> compat dict
        self.by_file = defaultdict(list)  # file -> [compat ...]
        self.loaded_files = []

    def scan(self):
        base = os.path.join(self.spt_path, "user", "mods", "SPT-Realism", "db", "templates", "user_templates")
        self.by_id.clear(); self.by_file.clear(); self.loaded_files.clear()
        if not os.path.isdir(base):
            return

        for path in iter_json_files(base, exclude_contains=[]):
            obj = safe_json_load(path)
            if not isinstance(obj, dict):
                continue
            self.loaded_files.append(path)
            for item_id, compat in obj.items():
                if not isinstance(compat, dict):
                    continue
                c = dict(compat)
                c["_file"] = path
                c["_guid"] = item_id
                c["ItemID"] = c.get("ItemID") or item_id
                # make name visible in editors
                if "Name" not in c:
                    c["Name"] = c.get("shortName") or c.get("ShortName") or item_id
                self.by_id[item_id] = c
                self.by_file[path].append(c)

# -------------------------
# UI pieces
# -------------------------
class CompatForm(QWidget):
    """Editable form that renders a dict with smart widgets, with schema-driven add-field support."""
    MODTYPE_OPTIONS = [
        "", "bipod", "short_barrel", "booster", "762x39", "300", "556", "366TKM", "308", "277",
        "sight", "mount", "shotTube", "foregrip_adapter", "shot_pump_grip_adapt", "counterWeight",
        "muzzle_supp_adapter", "sig_taper_brake", "barrel_2slot",
        "grip_stock_adapter", "buffer_adapter", "stock_adapter",
        "hydraulic_buffer", "buffer", "buffer_stock", "Stock", "StockR", "StockN", "StockF"
    ]
    WEAPTYPE_OPTIONS = ["", "DI", "bullpup", "short_AK"]
    OPERATION_OPTIONS = ["", "buffer", "magForward", "tubefed", "tubefed-m", "p90"]

    def __init__(self, compat_dict, editable=True, schema_for_type=None):
        super().__init__()
        self.compat_dict = compat_dict or {}
        self.fields = {}
        self.schema_for_type = schema_for_type or set()
        self._ctype = classify_realism_type(self.compat_dict.get("$type", ""))

        # Layout with an optional schema-based adder on top
        outer = QVBoxLayout(self)
        
        # --- Main form FIRST (so self._form always exists before add-row) ---
        form = QFormLayout()
        for k, v in sorted(self.compat_dict.items(), key=lambda kv: kv[0].lower()):
            if k.startswith("_"):  # hide internal
                continue
            w = self._widget_for(k, v)
            self.fields[k] = w
            form.addRow(QLabel(k), w)
        outer.addLayout(form)
        self._form = form


        # --- Add Field row: ALWAYS show a dropdown with allowed keys ---
        
        self.add_row = None
        if editable:
            self.add_row = QHBoxLayout()
            self.add_row.addWidget(QLabel("+ Add Field:"))

            self.cb_add = QComboBox()
            self.add_row.addWidget(self.cb_add)
            self.cb_add.activated.connect(lambda _: self._on_add_field())

            self.btn_add = QPushButton("Add")
            self.btn_add.clicked.connect(self._on_add_field)
            self.add_row.addWidget(self.btn_add)

            # keep the full allowed catalog and build initial list of missing keys
            self._all_allowed = sorted(set(self.schema_for_type))
            self._refresh_add_dropdown()

            outer.addLayout(self.add_row)



        
    def _on_add_field_generic(self):
        key = (self.tb_add_key.text() or "").strip()
        if not key:
            QMessageBox.information(self, "Missing", "Enter a field name.")
            return
        if key in self.compat_dict:
            QMessageBox.information(self, "Exists", f"Field '{key}' already exists.")
            return

        # Heuristic default
        default = ""
        if re.search(r"(Allow|Has|Can|Is)[A-Z_]", key):
            default = "False"
        if re.search(r"(Speed|Velocity|Recoil|Angle|Dispersion|Accuracy|Heat|Cool|Weight|Ergonomics|"
                    r"Convergence|Torque|Chance|Intensity|Penalty|Modifier|Loudness|Handling|Stability)",
                    key, re.I):
            default = "0"

        self.compat_dict[key] = default
        w = self._widget_for(key, default)
        self.fields[key] = w
        self._form.addRow(QLabel(key), w)
        self.tb_add_key.clear()


    # Smart field widgets
    # --- in class CompatForm(QWidget) ---

    def _widget_for(self, key, val):
        # --- Make ModType ALWAYS a dropdown, regardless of when it's added ---
        if key.lower() == "modtype":
            # Prefer WeaponMod-specific list if we can infer it; otherwise still a dropdown
            # Re-detect bucket from current dict instead of relying only on stale self._ctype
            bucket_now = classify_realism_type(self.compat_dict.get("$type", "")) or self._ctype
            cb = QComboBox()
            if bucket_now == "WeaponMod":
                cb.addItems(self.MODTYPE_OPTIONS)
            else:
                # Generic set remains available when type is unknown/non-WeaponMod
                cb.addItems([
                    "", "barrel", "muzzle", "muzzle_supp_adapter", "handguard", "stock",
                    "grip", "scope", "mount", "magazine", "laser", "flashlight",
                    "bipod", "pistol_grip", "buttpad", "buffer_tube"
                ])
            idx = cb.findText(str(val))
            if idx >= 0:
                cb.setCurrentIndex(idx)
            return cb

        # Special dropdowns gated by $type
        if key == "WeapType" and self._ctype == "Gun":
            cb = QComboBox(); cb.addItems(self.WEAPTYPE_OPTIONS)
            idx = cb.findText(str(val))
            if idx >= 0: cb.setCurrentIndex(idx)
            return cb

        if key == "OperationType" and self._ctype == "Gun":
            cb = QComboBox(); cb.addItems(self.OPERATION_OPTIONS)
            idx = cb.findText(str(val))
            if idx >= 0: cb.setCurrentIndex(idx)
            return cb

        # Generic renderers
        if isinstance(val, bool):
            box = QComboBox()
            box.addItems(["True", "False"])
            box.setCurrentIndex(0 if val else 1)
            return box

        if isinstance(val, int):
            sp = QSpinBox()
            sp.setRange(-1_000_000, 1_000_000)
            sp.setSingleStep(1)
            sp.setValue(val)
            return sp

        if isinstance(val, float):
            dsp = QDoubleSpinBox()
            dsp.setDecimals(6)
            dsp.setRange(-1_000_000.0, 1_000_000.0)
            dsp.setSingleStep(0.1)
            dsp.setValue(val)
            return dsp

        # Keep existing fallback behavior for other string fields
        return QLineEdit(str(val))


    def _missing_allowed_keys(self):
        """Return the allowed keys not yet present in the compat dict."""
        have = set(k for k in self.compat_dict.keys() if not k.startswith("_"))
        # Only offer keys we don't already have
        return [k for k in self._all_allowed if k not in have]

    def _refresh_add_dropdown(self):
        """Repopulate the dropdown and enable/disable Add button accordingly."""
        if not hasattr(self, "cb_add"):
            return
        missing = self._missing_allowed_keys()
        self.cb_add.blockSignals(True)
        self.cb_add.clear()
        self.cb_add.addItems(missing)
        if missing:
            self.cb_add.setCurrentIndex(0)
        self.cb_add.blockSignals(False)
        # disable Add button if nothing left to add
        if hasattr(self, "btn_add"):
            self.btn_add.setEnabled(bool(missing))


    # --- in class CompatForm(QWidget) ---

    def _on_add_field(self):
        key = self.cb_add.currentText().strip() if hasattr(self, "cb_add") else ""
        if not key:
            return
        if key in self.compat_dict:
            QMessageBox.information(self, "Exists", f"Field '{key}' already exists.")
            self._refresh_add_dropdown()
            return

        # Heuristic default: numbers -> "0", booleans -> "False", else ""
        default = ""
        if re.search(r"(Allow|Has|Can|Is)[A-Z_]", key):
            default = "False"
        if re.search(
            r"(Speed|Velocity|Recoil|Angle|Dispersion|Accuracy|Heat|Cool|Weight|Ergonomics|"
            r"Convergence|Torque|Chance|Intensity|Penalty|Modifier|Loudness|Handling|Stability)",
            key, re.I
        ):
            default = "0"

        # Insert into backing dict
        self.compat_dict[key] = default

        # If user just added $type, recompute type bucket immediately
        if key == "$type":
            self._ctype = classify_realism_type(self.compat_dict.get("$type", ""))

        # Add a proper editor row to the form
        w = self._widget_for(key, default)
        self.fields[key] = w
        self._form.addRow(QLabel(key), w)

        # (Optional) If $type changed and ModType already exists, upgrade that widget
        if key == "$type" and "ModType" in self.fields:
            self._refresh_widget_for("ModType")

        # Focus the new control for feedback
        try:
            if hasattr(w, "setFocus"):
                w.setFocus()
        except Exception:
            pass

        # Rebuild the dropdown list of missing keys
        self._refresh_add_dropdown()


    def _refresh_widget_for(self, key: str):
        """
        Rebuild JUST one field's widget (e.g. 'ModType') based on the current state,
        preserving its current value and replacing the row in the form.
        """
        if key not in self.fields:
            return

        old_widget = self.fields[key]

        # Read existing value from the current widget
        if isinstance(old_widget, (QSpinBox, QDoubleSpinBox)):
            current_val = old_widget.value()
        elif isinstance(old_widget, QComboBox):
            current_val = old_widget.currentText()
        else:
            current_val = old_widget.text()

        # Build a new widget with correct logic (e.g., now that _ctype is updated)
        new_widget = self._widget_for(key, current_val)

        # Locate the row index where the old widget lives
        row_idx = None
        for i in range(self._form.rowCount()):
            # column 1 is the field widget
            if self._form.itemAt(i, QFormLayout.FieldRole) is not None:
                item = self._form.itemAt(i, QFormLayout.FieldRole)
                if item is not None and item.widget() is old_widget:
                    row_idx = i
                    break

        # Replace in the form layout
        if row_idx is not None:
            # Remove old widget from layout
            self._form.removeRow(row_idx)
            # Re-add the row with same label text and new widget
            label_text = key
            self._form.insertRow(row_idx, QLabel(label_text), new_widget)

        # Update internal map
        self.fields[key] = new_widget

    def value(self):
        out = {}
        for k, w in self.fields.items():
            if isinstance(w, QSpinBox) or isinstance(w, QDoubleSpinBox):
                out[k] = w.value()
            elif isinstance(w, QComboBox):
                t = w.currentText()
                out[k] = True if t == "True" else False if t == "False" else t
            else:
                txt = w.text()
                if re.fullmatch(r"-?\d+", txt): out[k] = int(txt)
                elif re.fullmatch(r"-?\d+(\.\d+)?", txt): out[k] = float(txt)
                elif txt in ("True","False"): out[k] = (txt == "True")
                else: out[k] = txt
        return out

# -------------------------
# Main Window
# -------------------------
class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SPT Realism Compat Tool (Dark)")
        self.resize(1300, 780)
        self.settings = get_settings()
        self.exclude_contains = load_exclude_patterns(self.settings)
        self.spt_path = self.ensure_spt_path()
        self.compat_root = self.settings.value("compat_root", "")
        # If no compat root remembered, we will try to auto-detect later

        self.index = SPTIndex(self.spt_path, self.compat_root if self.compat_root else None, self.exclude_contains)
        self.index.scan()
        
        # Base game DB (for vanilla stats)
        self.base_db = BaseGameDB(self.spt_path, self.exclude_contains)
        self.base_db.scan()

        # Realism db (lookup only; still excluded from left tree)
        self.realism_db = RealismDB(self.spt_path)
        self.realism_db.scan()

        # User templates DB
        self.user_templates = UserTemplatesDB(self.spt_path)
        self.user_templates.scan()
        
        # Inject RealismDB records as template candidates if not already present
        for rec in self.realism_db.by_id.values():
            self.index.template_index.add(rec)
        
        #  load example.json schema for +Add Field dropdowns
        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.example_schema = load_example_schema(os.path.join(script_dir, "example.json"))



        ok, err = safe_load_formulas()
        if not ok:
            QMessageBox.warning(self, "Formulas load error", f"Could not load formulas.py:\n\n{err}")

    
        # If template index is too empty, prompt once for compat root
        if len(self.index.template_index.all_templates) < 10:
            guessed = self.guess_compat_root(self.spt_path)
            if guessed and guessed != self.compat_root:
                self.compat_root = guessed
                self.settings.setValue("compat_root", self.compat_root)
                self.index = SPTIndex(self.spt_path, self.compat_root)
                self.index.scan()
            elif not self.compat_root:
                cr = ask_for_folder("Select your Realism compat templates root (optional)")
                if cr:
                    self.compat_root = cr
                    self.settings.setValue("compat_root", self.compat_root)
                    self.index = SPTIndex(self.spt_path, self.compat_root)
                    self.index.scan()

        self.selected_records = []
        self.compat_forms = []

        self.init_ui()
        self.populate_items_tree()
        self.populate_user_templates_tree()

    def _base_tpl_and_record(self, base: dict):
        """Return (tpl, basegame_record) for this item."""
        tpl = None
        for key in ("itemTplToClone","itemtpltoclone","clone","tpl","_tpl"):
            v = base.get(key)
            if isinstance(v, str) and v.strip():
                tpl = v.strip()
                break
        rec = self.base_db.by_id.get(tpl) if tpl else None
        return tpl, rec

    def _handbook_parent_name(self, base: dict) -> str:
        def norm(cat: str) -> str:
            if not isinstance(cat, str) or not cat.strip():
                return ""
            if formulas_mod and hasattr(formulas_mod, "CATEGORY_ALIASES"):
                return formulas_mod.CATEGORY_ALIASES.get(cat, cat)
            return cat

        # 1) Prefer handbook parent from the record (text or GUID)
        pid = base.get("parent") or base.get("Parent") or base.get("parentId")
        if isinstance(pid, str) and pid.strip():
            if re.fullmatch(r"[0-9a-fA-F]{24}", pid):
                if formulas_mod and hasattr(formulas_mod, "PARENT_CLASSES"):
                    raw = formulas_mod.PARENT_CLASSES.get(pid, "")
                    if isinstance(raw, str) and raw.strip():
                        return norm(raw)
            else:
                return norm(pid)

        # 2) Fallback: basegame parent from cloned template
        tpl, vanilla = self._base_tpl_and_record(base)
        if isinstance(vanilla, dict):
            vpid = vanilla.get("_parent") or vanilla.get("parent") or vanilla.get("Parent") or vanilla.get("parentId")
            if isinstance(vpid, str) and vpid.strip():
                if re.fullmatch(r"[0-9a-fA-F]{24}", vpid):
                    if formulas_mod and hasattr(formulas_mod, "PARENT_CLASSES"):
                        raw = formulas_mod.PARENT_CLASSES.get(vpid, "")
                        if isinstance(raw, str) and raw.strip():
                            return norm(raw)
                else:
                    return norm(vpid)

        # 3) Last-hints
        for key in ("parentClass", "ParentClass", "$type"):
            val = base.get(key)
            if isinstance(val, str) and val.strip():
                return norm(val)

        return "Unknown"
    
    def _ensure_identity_fields(self, base: dict, compat: dict, template: dict = None) -> dict:
        """
        Make sure compat has $type, ItemID, Name in the canonical shapes.
        - $type -> "RealismMod.<Bucket>, RealismMod" where <Bucket> ∈ {WeaponMod, Gun, Gear, Ammo}
        - ItemID -> base.newId/_guid/id/_id (stringified)
        - Name   -> display name of base (fallback: ItemID)
        """
        if not isinstance(compat, dict):
            return compat or {}

        # ---- ItemID
        iid = compat.get("ItemID")
        if not isinstance(iid, str) or not iid.strip():
            iid = str(
                base.get("newId")
                or base.get("_guid")
                or base.get("id")
                or base.get("_id")
                or "compat"
            )
            compat["ItemID"] = iid

        # ---- Name
        nm = compat.get("Name")
        if not isinstance(nm, str) or not nm.strip():
            # Prefer the index's name resolver; fallback to on-the-fly
            nm = self.index.display_name_for(base) if base else ""
            if not nm:
                nm = get_display_name(base) if base else ""
            compat["Name"] = nm or iid

        # ---- $type
        t = compat.get("$type")
        if not isinstance(t, str) or not t.strip():
            bucket = guess_type_bucket(compat, base or {}, template)
            if not bucket:
                # heuristics if formula result didn't hint a bucket
                bucket = "WeaponMod" if isinstance(compat.get("ModType"), str) else ""
            if bucket:
                compat["$type"] = f"RealismMod.{bucket}, RealismMod"

        return compat

    def render_realism_panel(self, base):
        """
        Render Realism header + stats in the middle-right pane.
        Shows Name, ItemID, $type; omits _guid (redundant).
        """
        self.realism_header.setText(self._mk_header("Realism stats of cloned item"))

        rec, key_used = self._find_realism_record_for_base(base)
        if not isinstance(rec, dict):
            self.realism_sub.setText("<i>No realism record found for this item.</i>")
            self.realism_stats.setText("")
            return

        r_name = rec.get("Name") or rec.get("shortName") or rec.get("name") or ""
        r_id   = rec.get("ItemID") or rec.get("ItemId") or rec.get("ID") or rec.get("id") or rec.get("_guid") or key_used or ""
        r_type = rec.get("$type") or ""

        self.realism_sub.setText(self._mk_stacked_header([
            ("Name", r_name),
            ("ItemID", str(r_id)),
            ("$type", str(r_type) if r_type else "")
        ]))

        stats = self._extract_realism_stats(rec) or {}
        self.realism_stats.setText(self._pretty_stats("", stats) if stats else "<i>No stats found</i>")

    def _pick_formula_category(self, base: dict, template: dict | None) -> str:
        """
        Category selection order:
        1) Map handbook parent (GUID or text) via formulas.HANDBOOK_TO_FORMULA
        2) Explicit ModType on template/base
        3) Basegame handbook category (normalized)
        4) $type hint
        5) Fallback to parentClass/$type on base
        """
        def norm(cat: str) -> str:
            if not isinstance(cat, str):
                return ""
            cat = cat.strip()
            if formulas_mod and hasattr(formulas_mod, "CATEGORY_ALIASES"):
                return formulas_mod.CATEGORY_ALIASES.get(cat, cat)
            return cat

        # 1) Handbook mapping first (authoritative)
        pid = base.get("parent") or base.get("Parent") or base.get("parentId")
        if isinstance(pid, str) and pid.strip():
            mapped = map_parent_to_formula_category(pid)
            if mapped:
                return norm(mapped)

        # 2) Explicit ModType
        for src in (template, base):
            if isinstance(src, dict):
                mt = src.get("ModType")
                if isinstance(mt, str) and mt.strip():
                    return norm(mt)

        # 3) Basegame handbook category (normalized)
        handbook = self._handbook_parent_name(base)
        if handbook and handbook != "Unknown":
            return norm(handbook)

        # 4) $type hint
        for src in (template, base):
            if isinstance(src, dict):
                t = src.get("$type") or ""
                if isinstance(t, str) and "WeaponMod" in t:
                    return norm("WeaponMod")

        # 5) parentClass/$type on base
        for key in ("parentClass", "ParentClass", "$type", "parent"):
            val = base.get(key)
            if isinstance(val, str) and val.strip():
                return norm(val)

        return ""
    
    def _find_realism_record_for_base(self, base: dict):
        """
        Locate the Realism record by trying, in order:
        - base clone/tpl fields
        - base id/_id/_guid
        - any ids present on the chosen template
        Returns (record_or_None, key_used_or_None)
        """
        candidates = []
        for key in ("itemTplToClone","itemtpltoclone","clone","tpl","_tpl",
                    "id","_id","_guid"):
            v = base.get(key)
            if isinstance(v, str) and v.strip():
                candidates.append(v.strip())

        t = getattr(self, "_current_template", None)
        if isinstance(t, dict):
            for key in ("ItemID","ItemId","ID","id","_id","_guid","tpl","_tpl"):
                v = t.get(key)
                if isinstance(v, str) and v.strip():
                    candidates.append(v.strip())

        seen, uniq = set(), []
        for c in candidates:
            if c not in seen:
                uniq.append(c); seen.add(c)

        for c in uniq:
            rec = self.realism_db.by_id.get(c)
            if isinstance(rec, dict):
                return rec, c
        return None, None

    def render_realism_inline(self, base):
        """
        Render Realism header + stats directly under Base panel.
        Shows Name, ItemID, $type; omits _guid (redundant).
        """
        # optional thin divider
        self.realism_inline_header.setText(
            "<hr style='margin:8px 0'>" + self._mk_header("Realism stats (by clone/tpl)")
        )

        rec, key_used = self._find_realism_record_for_base(base)
        if not isinstance(rec, dict):
            self.realism_inline_sub.setText("<i>No realism record found for this item.</i>")
            self.realism_inline_stats.setText("")
            return

        r_name = rec.get("Name") or rec.get("shortName") or rec.get("name") or ""
        r_id   = rec.get("ItemID") or rec.get("ItemId") or rec.get("ID") or rec.get("id") or rec.get("_guid") or key_used or ""
        r_type = rec.get("$type") or ""

        self.realism_inline_sub.setText(self._mk_stacked_header([
            ("Name", r_name),
            ("ItemID", str(r_id)),
            ("$type", str(r_type) if r_type else "")
        ]))

        stats = self._extract_realism_stats(rec) or {}
        self.realism_inline_stats.setText(
            self._pretty_stats("", stats) if stats else "<i>No stats found</i>"
        )

    def ensure_spt_path(self):
        """
        Retrieve (or prompt for) the SPT install path and persist it in settings.
        This matches the original behavior used elsewhere in the window.
        """
        spt = self.settings.value("spt_path", "")
        if not spt or not os.path.isdir(spt):
            spt = ask_for_folder("Select your SPT install folder")
            if not spt:
                QMessageBox.critical(self, "Required", "SPT install folder is required.")
                sys.exit(1)
        self.settings.setValue("spt_path", spt)
        return spt

    def _mk_header(self, text: str) -> str:
        """Large, bold, centered section header."""
        return (
            "<div style='font-size:18px;font-weight:700;"
            "margin:4px 0 6px 0;text-align:center'>"
            f"{text}</div>"
        )

    def _mk_stacked_header(self, pieces: list) -> str:
        """
        pieces: list of (label, value) pairs; empty values skipped.
        Each pair is rendered on its own line.
        """
        lines = []
        for label, value in pieces:
            if value:
                lines.append(f"<b>{label}</b>: {value}")
        return "<div style='margin:4px 0;text-align:left'>" + "<br>".join(lines) + "</div>"

    def _resolve_parent_category_name(self, base: dict, template: dict | None) -> str:
        """
        Show the *basegame handbook* parent (normalized), not the Realism $type.
        """
        return self._handbook_parent_name(base)
    
    def is_reskin_compat(self, rec):
        # Accepts a dict; returns True if it matches the reskin/clone pattern
        if not isinstance(rec, dict):
            return False
        keys = set(rec.keys())
        # Accept both possible TemplateID field names
        template_keys = [k for k in keys if k.lower().startswith("templateid")]
        expected_keys = {"$type", "ItemID", "Name"}
        if len(keys) == 4 and expected_keys.issubset(keys) and template_keys:
            return True
        return False

    def init_ui(self):
        # ROOT: horizontal layout (tabs left, shared editor right)
        root = QHBoxLayout(self)

        # ----- LEFT: Tabs -----
        self.tabs = QTabWidget(self)
        root.addWidget(self.tabs, 3)

        self.tabs.currentChanged.connect(self._on_tab_changed)

        # ====== Tab 1: Mod Items (left column only) ======
        tab1 = QWidget()
        left1 = QVBoxLayout(tab1)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Search items by name/type/id…")
        self.search.textChanged.connect(self.populate_items_tree)
        left1.addWidget(self.search)

        self.item_tree = QTreeWidget()
        self.item_tree.setHeaderLabels(["Item"])
        self.item_tree.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.item_tree.itemSelectionChanged.connect(self.on_item_selected)
        left1.addWidget(self.item_tree)

        btn_row = QHBoxLayout()
        self.btn_batch = QPushButton("Batch Export Selected")
        self.btn_batch.clicked.connect(self.batch_export)
        btn_row.addWidget(self.btn_batch)
        self.btn_change_paths = QPushButton("Paths…")
        self.btn_change_paths.clicked.connect(self.change_paths)
        btn_row.addWidget(self.btn_change_paths)
        left1.addLayout(btn_row)

        self.tabs.addTab(tab1, "Mod Items")

        # ====== Tab 2: User Templates (left column only) ======
        tab2 = QWidget()
        left2 = QVBoxLayout(tab2)

        self.search_ut = QLineEdit()
        self.search_ut.setPlaceholderText("Search user templates by name/ItemID…")
        self.search_ut.textChanged.connect(self.populate_user_templates_tree)
        left2.addWidget(self.search_ut)

        self.user_template_tree = QTreeWidget()
        self.user_template_tree.setHeaderLabels(["User Template"])
        self.user_template_tree.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.user_template_tree.itemSelectionChanged.connect(self.on_user_template_selected)
        left2.addWidget(self.user_template_tree)

        self.tabs.addTab(tab2, "User Templates")

        # ----- RIGHT: Shared editor (center-left Base, center-right Realism, far-right Compat) -----
        midright = QHBoxLayout()

        # ========= CENTER-LEFT: Base/Merged =========
        base_panel = QVBoxLayout()
        self.base_header = QLabel(self._mk_header("Base Game (merged view)"))
        self.base_header.setTextFormat(Qt.RichText)
        self.base_header.setWordWrap(True)
        base_panel.addWidget(self.base_header)

        self.base_sub = QLabel("—")
        self.base_sub.setTextFormat(Qt.RichText)
        self.base_sub.setAlignment(Qt.AlignLeft)
        self.base_header.setWordWrap(True)
        base_panel.addWidget(self.base_sub)

        self.base_stats = QLabel("—")
        self.base_stats.setWordWrap(True)
        self.base_stats.setTextFormat(Qt.RichText)
        self.base_stats.setAlignment(Qt.AlignLeft)
        self.base_stats.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        base_panel.addWidget(self.base_stats, 1)

        base_scroll = QScrollArea(); base_scroll.setWidgetResizable(True)
        base_container = QWidget(); base_container.setLayout(base_panel)
        base_container.setMinimumWidth(420)
        base_scroll.setWidget(base_container)

        # ========= CENTER-RIGHT: Realism =========
        realism_panel = QVBoxLayout()
        self.realism_header = QLabel(self._mk_header("Realism stats (by clone/tpl)"))
        self.realism_header.setTextFormat(Qt.RichText)
        self.realism_header.setWordWrap(True)
        realism_panel.addWidget(self.realism_header)

        self.realism_sub = QLabel("—")
        self.realism_sub.setTextFormat(Qt.RichText)
        self.realism_sub.setAlignment(Qt.AlignLeft)
        self.realism_sub.setWordWrap(True)
        realism_panel.addWidget(self.realism_sub)

        self.realism_stats = QLabel("—")
        self.realism_stats.setWordWrap(True)
        self.realism_stats.setTextFormat(Qt.RichText)
        self.realism_stats.setAlignment(Qt.AlignLeft)
        self.realism_stats.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        realism_panel.addWidget(self.realism_stats, 1)

        realism_scroll = QScrollArea(); realism_scroll.setWidgetResizable(True)
        realism_container = QWidget(); realism_container.setLayout(realism_panel)
        realism_container.setMinimumWidth(420)
        realism_scroll.setWidget(realism_container)

        # ========= FAR-RIGHT: Formula & Compat =========
        right = QVBoxLayout()

        self.template_details = QLabel()
        self.template_details.setWordWrap(True)
        self.template_details.setTextFormat(Qt.RichText)
        right.addWidget(self.template_details)

        self.lbl_parent_cat = QLabel("<b>Parent</b>: —")
        self.lbl_parent_cat.setTextFormat(Qt.RichText)
        right.addWidget(self.lbl_parent_cat)

        self.lbl_type = QLabel("<b>$type</b>: —")
        self.lbl_type.setTextFormat(Qt.RichText)
        right.addWidget(self.lbl_type)

        row_cat = QHBoxLayout()
        row_cat.addWidget(QLabel("Formula Category:"))
        self.cb_category = QComboBox()
        self.cb_category.setEditable(True)
        row_cat.addWidget(self.cb_category)
        self.btn_reload_formulas = QPushButton("Reload formulas.py")
        self.btn_reload_formulas.clicked.connect(self.reload_formulas)
        row_cat.addWidget(self.btn_reload_formulas)
        right.addLayout(row_cat)

        self.lbl_compat = QLabel("<b>Compat (Editable)</b>")
        self.lbl_compat.setTextFormat(Qt.RichText)
        right.addWidget(self.lbl_compat)

        self.lbl_compat_hint = QLabel("—")
        self.lbl_compat_hint.setTextFormat(Qt.RichText)
        self.lbl_compat_hint.setAlignment(Qt.AlignLeft)
        right.addWidget(self.lbl_compat_hint)

        self.compat_area = QScrollArea()
        self.compat_area.setWidgetResizable(True)
        right.addWidget(self.compat_area, 2)

        export_row = QHBoxLayout()
        self.btn_compute = QPushButton("Recompute from Formula")
        self.btn_compute.clicked.connect(self.recompute_current)
        export_row.addWidget(self.btn_compute)
        self.btn_export_one = QPushButton("Export This")
        self.btn_export_one.clicked.connect(self.export_current)
        export_row.addWidget(self.btn_export_one)
        right.addLayout(export_row)

        right_scroll = QScrollArea(); right_scroll.setWidgetResizable(True)
        right_container = QWidget(); right_container.setLayout(right)
        right_scroll.setWidget(right_container)

        # Assemble shared editor
        midright.addWidget(base_scroll, 3)
        midright.addWidget(realism_scroll, 3)
        midright.addWidget(right_scroll, 5)

        # Add shared editor to root (right column)
        # Note: add as a QWidget so stretch works nicely
        editor_wrap = QWidget(); editor_wrap.setLayout(midright)
        root.addWidget(editor_wrap, 8)
        
        self.base_header.setWordWrap(True)
        self.base_sub.setWordWrap(True)
        self.base_stats.setWordWrap(True)

        self.realism_header.setWordWrap(True)
        self.realism_sub.setWordWrap(True)
        self.realism_stats.setWordWrap(True)

        self.template_details.setWordWrap(True)
        self.lbl_parent_cat.setWordWrap(True)
        self.lbl_type.setWordWrap(True)
        self.lbl_compat.setWordWrap(True)
        self.lbl_compat_hint.setWordWrap(True)


        # After building tabs and editor:
        self._on_tab_changed(self.tabs.currentIndex())


    def on_user_template_selected(self):
        sel_items = self.user_template_tree.selectedItems()
        if not sel_items:
            return
        tmpl = sel_items[0].data(0, Qt.UserRole)
        if not isinstance(tmpl, dict):
            return

        # Try to find a base mod item by ItemID / guid match
        base = None
        iid = str(tmpl.get("ItemID") or tmpl.get("_guid") or "")
        if iid:
            for rec in self.index.items:
                for key in ("newId","_guid","id","_id"):
                    if str(rec.get(key) or "") == iid:
                        base = rec; break
                if base: break

        # Render: template displayed as 'template', compat editor seeded from template
        self._current_template = tmpl
        self.lbl_parent_cat.setText(f"<b>Parent</b>: {tmpl.get('parent') or '—'}")
        self.lbl_type.setText(f"<b>$type</b>: {tmpl.get('$type') or '—'}")

        # category combobox like in render_base()
        detected = self._pick_formula_category(base or {}, tmpl)
        self.cb_category.blockSignals(True)
        self.cb_category.clear()
        self.cb_category.addItem("— select category —")
        cats = set()
        if formulas_mod:
            for map_name in ("gun_formula_map","mod_formula_map","gear_formula_map"):
                m = getattr(formulas_mod, map_name, None)
                if isinstance(m, dict):
                    cats.update(k for k in m.keys() if isinstance(k, str))
        if detected and callable(resolve_formula_func(detected)):
            self.cb_category.addItem(detected)
            self.cb_category.setCurrentText(detected)
        for c in sorted(cats):
            if c != detected:
                self.cb_category.addItem(c)
        if not (detected and callable(resolve_formula_func(detected))):
            self.cb_category.setCurrentIndex(0)
        self.cb_category.blockSignals(False)

        # panels
        if base:
            self.render_basegame_stats(base)     # base stats center-left
            self.render_realism_panel(base)      # realism center-right
        else:
            # clear or minimal
            self.base_header.setText(self._mk_header("No matching base item"))
            self.base_sub.setText("—"); self.base_stats.setText("—")
            self.realism_header.setText(self._mk_header("Realism stats")); self.realism_sub.setText("—"); self.realism_stats.setText("—")

        # Right editor: show the template itself as compat (editable)
        # Build allowed set (bucket or union)
        ctype = guess_type_bucket(tmpl, base or {}, tmpl)
        allowed = set()
        if isinstance(self.example_schema, dict) and self.example_schema:
            if ctype and self.example_schema.get(ctype):
                allowed = set(self.example_schema.get(ctype))
            else:
                for v in self.example_schema.values():
                    if isinstance(v, (set, list, tuple)): allowed.update(v)
        if not allowed:
            allowed = {
                "$type","ItemID","Name","ModType","WeapType","OperationType","Weight","Ergonomics",
                "Recoil","RecoilForceUp","RecoilForceBack","RecoilAngle","BaseMalfunctionChance",
                "Damage","PenetrationPower","Velocity","Loudness",
                "mousePenalty","speedPenaltyPercent","weaponErgonomicPenalty"
            }

        form = CompatForm(tmpl, editable=True, schema_for_type=allowed)
        self.compat_area.setWidget(form)
        self.compat_forms = [form]

    def _on_tab_changed(self, idx: int):
        """
        When switching tabs, clear the editor if User Templates tab is active with no selection.
        Tab 0 = Mod Items, Tab 1 = User Templates.
        """
        # Only act on the User Templates tab
        if idx == 1:
            # If no template selected yet, clear the editor panes
            if not getattr(self, "user_template_tree", None) or not self.user_template_tree.selectedItems():
                # Header & hints on the right
                self.template_details.setText("<i>Select a user template…</i>")
                self.lbl_parent_cat.setText("<b>Parent</b>: —")
                self.lbl_type.setText("<b>$type</b>: —")

                # Center-left (Base)
                self.base_header.setText(self._mk_header("Base Game (merged view)"))
                self.base_sub.setText("—")
                self.base_stats.setText("—")

                # Center-right (Realism)
                self.realism_header.setText(self._mk_header("Realism stats (by clone/tpl)"))
                self.realism_sub.setText("—")
                self.realism_stats.setText("—")

                # Far-right (Compat editor area)
                self.compat_area.setWidget(QWidget())

    def reload_formulas(self):
        """
        Reload formulas.py and refresh the current preview so category maps and
        functions take immediate effect without restarting the app.
        """
        ok, err = safe_load_formulas()
        if not ok:
            QMessageBox.critical(self, "Reload failed", err)
            return

        # Rebuild the visible list (names/categories can influence labels/filters)
        self.populate_items_tree()

        # If an item is currently selected, re-render it
        sel_items = self.item_tree.selectedItems()
        if sel_items:
            rec = sel_items[0].data(0, Qt.UserRole)
            if isinstance(rec, dict):
                self.render_base(rec)

        QMessageBox.information(self, "Formulas reloaded", "formulas.py reloaded successfully.")




    def guess_compat_root(self, spt_path):
        # Try to find a mod folder that likely contains compat-like JSONs
        user_mods = os.path.join(spt_path, "user", "mods")
        candidates = []
        if os.path.isdir(user_mods):
            for d in os.listdir(user_mods):
                p = os.path.join(user_mods, d)
                if not os.path.isdir(p): continue
                # Heuristic: look for "compat" or "realism" in structure
                for sub in ("db", "database", ""):
                    test = os.path.join(p, sub)
                    if not os.path.isdir(test): continue
                    # If there are many JSONs here, consider it
                    count = sum(1 for _ in iter_json_files(test))
                    if count > 100:  # a real data source
                        candidates.append(test)
        # Prefer ones with 'realism' in path
        candidates.sort(key=lambda x: (("realism" not in x.lower()), -sum(1 for _ in iter_json_files(x))))
        return candidates[0] if candidates else ""


    


    def change_paths(self):
        spt = ask_for_folder("Select your SPT install folder")
        if spt:
            self.settings.setValue("spt_path", spt)

        compat = ask_for_folder("Select your Realism compat templates root (optional)")
        if compat:
            self.settings.setValue("compat_root", compat)

        # Edit exclude patterns (comma or semicolon separated)
        current = self.settings.value("exclude_patterns", "")
        new_patterns, ok = QInputDialog.getText(self, "Exclude Folders/Paths",
                                                "Comma- or semicolon-separated substrings to exclude\n(e.g. spt-realism,.git,__pycache__):",
                                                text=current)
        if ok:
            self.settings.setValue("exclude_patterns", new_patterns)

        # Reload
        self.spt_path = self.settings.value("spt_path", self.spt_path)
        self.compat_root = self.settings.value("compat_root", self.compat_root)
        self.exclude_contains = load_exclude_patterns(self.settings)
        self.index = SPTIndex(self.spt_path, self.compat_root, self.exclude_contains)
        self.index.scan()
        print("Indexed items:", len(self.index.items))
        print("Mods with items:", len(self.index.items_by_mod))
        print("Templates:", len(self.index.template_index.all_templates))

        # refresh tree
        self.populate_items_tree()


    def _pretty_stats(self, title, stats_dict):
        if not stats_dict:
            return f"<i>No stats found</i>"
        lines = [f"<b>{k}</b>: {stats_dict[k]}" for k in stats_dict]
        return "<br>".join(lines)
    

    def _extract_basegame_stats(self, rec: dict) -> dict:
        """
        Extract Base Game or Mod-merged stats for display.
        We now build a 'props_view' where overrideProperties overlays _props,
        so MOD values are visible and not shadowed by vanilla.
        """
        if not isinstance(rec, dict):
            return {}
        out = {}

        # Start with vanilla props; overlay mod overrides for the display view
        props_view = {}
        base_props = rec.get("_props", {})
        if isinstance(base_props, dict):
            props_view.update(base_props)

        ov = rec.get("overrideProperties", {})
        if isinstance(ov, dict):
            # Only copy simple scalars into the view (skip large/nested blobs)
            for k, v in ov.items():
                if isinstance(v, (int, float, bool, str)):
                    props_view[k] = v

        # 1) Use props_view first (already has mod overrides on top)
        for k, v in props_view.items():
            if k in BASE_HIDE_KEYS:
                continue
            if isinstance(v, (int, float, bool, str)):
                out[k] = v
        # 2) Preserve a few useful top-level overrides (if not present already)
        for k in ("Weight", "Ergonomics", "RecoilForceUp", "RecoilForceBack", "RecoilAngle",
                "DeviationMax", "CenterOfImpact", "Velocity", "Damage", "PenetrationPower"):
            if k in rec and k not in out and isinstance(rec[k], (int, float, bool, str)):
                out[k] = rec[k]

        # Aliases/convenience
        if "RecoilForceUp" in out and "RecoilVertical" not in out:
            out["RecoilVertical"] = out["RecoilForceUp"]

        return out


    def _extract_realism_stats(self, rec: dict) -> dict:
        """
        For Realism templates (in templates_data), show ALL simple fields at the top level.
        Skip $type, IDs, file metadata, and large containers; pretty-print short lists.
        """
        if not isinstance(rec, dict):
            return {}
        out = {}
        skip = {"$type", "ItemID", "ItemId", "ID", "id", "_id", "_guid", "_file", "Name"}

        for k, v in rec.items():
            if k in skip:
                continue
            if isinstance(v, (int, float, bool, str)):
                out[k] = v
            elif isinstance(v, list):
                # display short lists inline; skip very long ones
                if len(v) <= 12:
                    out[k] = ", ".join(str(x) for x in v)
            # dicts/nested not shown to keep it compact

        return out
    
    def render_basegame_stats(self, base):
        """
        Show mod stats built from _props (promoted from item/_props) overlayed with overrideProperties.
        """
        # Header
        item_name = self.index.display_name_for(base)
        mod_name  = base.get("_mod", "") or "(External)"
        guid      = str(base.get("_guid") or base.get("id") or base.get("_id") or "")
        self.base_header.setText(self._mk_header(f"{mod_name} — Mod stats"))
        self.base_sub.setText(self._mk_stacked_header([
            ("Item", item_name),
            ("_guid", guid),
            ("ItemTplToClone", base.get("itemTplToClone") or base.get("clone") or "")
        ]))

        # Build a display view: start with base _props, then overlay simple scalars from overrideProperties
        props_view = {}
        base_props = get_base_props_dict(base)  # ← supports top-level _props or item/_props
        if isinstance(base_props, dict):
            props_view.update(base_props)

        ov = base.get("overrideProperties", {})
        if isinstance(ov, dict):
            for k, v in ov.items():
                if isinstance(v, (int, float, bool, str)):
                    props_view[k] = v

        # Now pretty-print simple scalars, skipping noise keys
        out = {}
        for k, v in props_view.items():
            if k in BASE_HIDE_KEYS:
                continue
            if isinstance(v, (int, float, bool, str)):
                out[k] = v

        # If nested Prefab existed but the flattener didn't run (edge cases), echo it
        if isinstance(ov, dict):
            pref = ov.get("Prefab")
            if isinstance(pref, dict) and "path" in pref and "PrefabPath" not in ov:
                out.setdefault("PrefabPath", pref["path"])

        self.base_stats.setText(self._pretty_stats("", out) if out else "<i>No mod stats found</i>")



    def _pretty_kv(self, rec, keys):
        lines = []
        for k in keys:
            if k in rec:
                lines.append(f"<b>{k}</b>: {rec[k]}")
        return "<br>".join(lines) if lines else "—"

    def populate_items_tree(self):
        self.item_tree.clear()
        if not hasattr(self, "search"):
            return

        # set of ItemIDs that exist in user templates
        ut_ids = set(self.user_templates.by_id.keys()) if hasattr(self, "user_templates") else set()
        q = (self.search.text() or "").lower().strip()

        for mod_name in sorted(self.index.items_by_mod.keys(), key=lambda s: s.lower()):
            records = self.index.items_by_mod[mod_name]
            filtered = []
            for rec in records:
                name = self.index.display_name_for(rec)
                typ  = (rec.get("$type") or rec.get("parentClass") or rec.get("parent") or "").strip()
                idv  = rec.get("newId") or rec.get("_guid") or rec.get("id") or rec.get("_id") or ""
                label = f"{name} [{typ}]" if typ else name
                if not q or q in label.lower() or (idv and q in str(idv).lower()) or q in mod_name.lower():
                    filtered.append(rec)

            if not filtered:
                continue
            mod_item = QTreeWidgetItem([f"{mod_name}  ({len(filtered)}/{len(records)})"])
            mod_item.setExpanded(False)
            self.item_tree.addTopLevelItem(mod_item)

            for rec in sorted(filtered, key=lambda r: self.index.display_name_for(r).lower()):
                name = self.index.display_name_for(rec)
                child = QTreeWidgetItem([name])
                child.setData(0, Qt.UserRole, rec)

                # COLOR: green if user template exists for ItemID/newId/_guid; yellow otherwise
                iid = str(rec.get("newId") or rec.get("_guid") or rec.get("id") or rec.get("_id") or "")
                if iid and iid in ut_ids:
                    child.setBackground(0, QColor(30, 90, 30))   # deep green
                    child.setForeground(0, QColor(230, 255, 230))
                else:
                    child.setBackground(0, QColor(110, 110, 30)) # yellow-ish
                    child.setForeground(0, QColor(255, 255, 230))

                mod_item.addChild(child)

        if q:
            self.item_tree.expandAll()
        else:
            self.item_tree.collapseAll()


    def recompute_current(self):
        # If user templates tab is active, recompute using that template and the resolved base
        if hasattr(self, "tabs") and self.tabs.currentIndex() == 1:
            w = self.compat_forms[0] if self.compat_forms else None
            tmpl = w.value() if w else None
            if not isinstance(tmpl, dict):
                QMessageBox.information(self, "Recompute", "Select a user template first.")
                return
            # Find base by ItemID
            base = None
            iid = str(tmpl.get("ItemID") or tmpl.get("_guid") or "")
            if iid:
                for rec in self.index.items:
                    if str(rec.get("newId") or rec.get("_guid") or rec.get("id") or rec.get("_id") or "") == iid:
                        base = rec; break
            # Compute via formula category picker
            detected = self._pick_formula_category(base or {}, tmpl)
            func = resolve_formula_func(detected) if detected else None
            if not callable(func):
                QMessageBox.information(self, "Recompute", "Pick a valid formula category first.")
                return
            effective_base = self._build_effective_base_for_formula(base or {})
            newc = call_formula(func, {}, effective_base, tmpl, {
                "spt_path": self.spt_path, "compat_root": self.compat_root, "index": self.index,
            })
            if isinstance(newc, dict):
                # replace editor with recomputed dict, preserving identity keys
                newc.setdefault("ItemID", tmpl.get("ItemID"))
                newc.setdefault("Name", tmpl.get("Name"))
                ctype = guess_type_bucket(newc, base or {}, tmpl)
                allowed = set()
                if isinstance(self.example_schema, dict) and self.example_schema:
                    if ctype and self.example_schema.get(ctype):
                        allowed = set(self.example_schema.get(ctype))
                    else:
                        for v in self.example_schema.values():
                            if isinstance(v, (set, list, tuple)): allowed.update(v)
                form = CompatForm(newc, editable=True, schema_for_type=allowed)
                self.compat_area.setWidget(form)
                self.compat_forms = [form]
            return

        # default: Mod Items tab (unchanged)
        if not self.selected_records:
            QMessageBox.information(self, "Recompute", "Select an item first.")
            return
        base = self.selected_records[0]
        template = getattr(self, "_current_template", None)
        self.render_compat(base, template)

    def on_item_selected(self):
        sel_items = self.item_tree.selectedItems()
        self.selected_records = []
        for it in sel_items:
            rec = it.data(0, Qt.UserRole)  # only children carry a dict
            if isinstance(rec, dict):
                self.selected_records.append(rec)
        if not self.selected_records:
            return
        self.render_base(self.selected_records[0])


    def render_base(self, base):
        base_name = self.index.display_name_for(base)
        base_typ  = (base.get("$type") or base.get("parentClass") or base.get("parent") or "")
        base_mod  = base.get("_mod", "")
        header = f"<b>Item</b> — {base_name}  <span style='color:#9aa0a6'>[{base_typ}]</span>"
        if base_mod:
            header += f"  <span style='color:#6aa84f'>({base_mod})</span>"
        
        
                # --- Find template matches ---
        matches, candidates = self.index.template_index.match_by_item(base)

        # Pick best template (prefer exact target id match)
        best_idx = 0
        cand_set = set(candidates)
        for i, t in enumerate(matches):
            tgt = str(
                t.get("_guid") or t.get("id") or t.get("_id") or
                t.get("ItemID") or t.get("ItemId") or ""
            )
            if tgt in cand_set:
                best_idx = i
                break

        sel_template = matches[best_idx] if matches else None

        # ----  if no template match, fall back to the Realism record ----
        if not isinstance(sel_template, dict):
            realism_rec, _ = self._find_realism_record_for_base(base)
            if isinstance(realism_rec, dict):
                sel_template = realism_rec

        self._current_template = sel_template  # remember selection

        # Update the two small lines above the category
        handbook_parent = self._resolve_parent_category_name(base, sel_template)
        self.lbl_parent_cat.setText(f"<b>Parent</b>: {handbook_parent}")

        type_text = ""
        if isinstance(sel_template, dict):
            type_text = sel_template.get("$type") or ""
        if not type_text:
            # secondary fallback: $type from base
            type_text = base.get("$type") or ""
        self.lbl_type.setText(f"<b>$type</b>: {type_text}")

        # Now seed the category combobox using the correct detection (with real fallback)
        
        detected = self._pick_formula_category(base, sel_template)

        self.cb_category.blockSignals(True)
        self.cb_category.clear()
        self.cb_category.addItem("— select category —")  # placeholder at index 0

        # Known categories from formulas.py (union of keys)
        cats = set()
        if formulas_mod:
            for map_name in ("gun_formula_map","mod_formula_map","gear_formula_map"):
                m = getattr(formulas_mod, map_name, None)
                if isinstance(m, dict):
                    cats.update(k for k in m.keys() if isinstance(k, str))

        # Put detected first if it has a callable formula
        if detected:
            f = resolve_formula_func(detected)
            if callable(f):
                self.cb_category.addItem(detected)

        # Then the rest (without duplicating 'detected')
        for c in sorted(cats):
            if c != detected:
                self.cb_category.addItem(c)

        # Select detected if callable; otherwise leave placeholder selected
        if detected and callable(resolve_formula_func(detected)):
            self.cb_category.setCurrentText(detected)
        else:
            self.cb_category.setCurrentIndex(0)

        self.cb_category.blockSignals(False)



        # Drive the panels
        self.render_template(sel_template)
        self.render_compat(base, sel_template)
        self.render_basegame_stats(base)
        self.render_realism_panel(base)

    def render_template(self, template):
        # Keep the details pane minimal; the two header labels above already show Parent and $type
        if not template:
            self.template_details.setText("<i>No template found for this item.</i>")
            return
        ttype = template.get("$type") or ""
        # optional: show the template's name only (avoid dumping lots of fields)
        tname = template.get("Name") or template.get("shortName") or ""
        self.template_details.setText(
            (f"<b>Template</b>: {tname}" if tname else "<b>Template</b>: (selected)")
        )
    def _merge_dicts(self, a: dict, b: dict, drop_keys=None):
            """
            Deep-merge dicts where values from b override a.
            - drop_keys: optional set of keys to remove from the result.
            - We DO NOT strip underscore keys here (we need '_props'!).
            """
            drop_keys = drop_keys or set()
            out = {} if a is None else dict(a)
            for k, v in (b or {}).items():
                if k in drop_keys:
                    continue
                if isinstance(out.get(k), dict) and isinstance(v, dict):
                    out[k] = self._merge_dicts(out[k], v, drop_keys)
                else:
                    out[k] = v
            # prune
            for k in list(out.keys()):
                if k in drop_keys:
                    out.pop(k, None)
            return out
    def populate_user_templates_tree(self):
        self.user_template_tree.clear()
        q = (self.search_ut.text() or "").lower().strip()

        # Nothing loaded? Show an empty top-level and return gracefully.
        if not getattr(self.user_templates, "by_file", None):
            top = QTreeWidgetItem(["user_templates"])
            self.user_template_tree.addTopLevelItem(top)
            self.user_template_tree.expandAll()
            return

        # Group under the true 'user_templates' anchor found in each absolute file path.
        folders: dict[str, dict[str, list]] = {}
        loose_files: dict[str, list] = {}

        for abs_path, recs in self.user_templates.by_file.items():
            norm = abs_path.replace("\\", "/")
            parts = norm.split("/")
            lower = [p.lower() for p in parts]
            try:
                anchor_idx = lower.index("user_templates")
                rel_parts = parts[anchor_idx + 1:]  # path segments AFTER 'user_templates'
            except ValueError:
                # If we can't find the anchor, treat as a loose file name fallback
                rel_parts = [os.path.basename(abs_path)]

            # Sanitize out any empty / dot segments that could have slipped in
            rel_parts = [p for p in rel_parts if p not in ("", ".", "..")]

            if not rel_parts:
                # Unexpected; fall back to file name
                file_name = os.path.basename(abs_path)
                loose_files.setdefault(file_name, []).extend(recs)
            elif len(rel_parts) == 1:
                # Loose JSON directly under user_templates/
                file_name = rel_parts[0]
                loose_files.setdefault(file_name, []).extend(recs)
            else:
                # Folder under user_templates/ → then JSON file
                folder = rel_parts[0]
                file_name = rel_parts[-1]
                folders.setdefault(folder, {}).setdefault(file_name, []).extend(recs)

        # --- Build the tree ---
        top = QTreeWidgetItem(["user_templates"])
        self.user_template_tree.addTopLevelItem(top)

        # 1) Folders under user_templates
        for folder in sorted(folders.keys(), key=lambda s: s.lower()):
            folder_node = QTreeWidgetItem([folder])
            top.addChild(folder_node)

            for file_name in sorted(folders[folder].keys(), key=lambda s: s.lower()):
                recs = folders[folder][file_name]
                # filter by search
                filtered = []
                for rec in recs:
                    name = rec.get("Name") or ""
                    iid  = rec.get("ItemID") or rec.get("_guid") or ""
                    label = f"{name} [{iid}]"
                    if not q or q in label.lower() or q in file_name.lower() or q in folder.lower():
                        filtered.append(rec)
                if not filtered:
                    continue

                file_node = QTreeWidgetItem([f"{file_name} ({len(filtered)})"])
                folder_node.addChild(file_node)

                for rec in sorted(filtered, key=lambda r: (r.get("Name") or "").lower()):
                    leaf = QTreeWidgetItem([rec.get("Name") or rec.get("ItemID") or "(template)"])
                    leaf.setData(0, Qt.UserRole, rec)
                    if self.is_reskin_compat(rec):
                        leaf.setBackground(0, QColor(120, 30, 30))  # deep red background
                        leaf.setForeground(0, QColor(255, 220, 220))  # light red text
                    file_node.addChild(leaf)

        # 2) Loose JSONs directly under user_templates
        for file_name in sorted(loose_files.keys(), key=lambda s: s.lower()):
            recs = loose_files[file_name]
            filtered = []
            for rec in recs:
                name = rec.get("Name") or ""
                iid  = rec.get("ItemID") or rec.get("_guid") or ""
                label = f"{name} [{iid}]"
                if not q or q in label.lower() or q in file_name.lower():
                    filtered.append(rec)
            if not filtered:
                continue

            file_node = QTreeWidgetItem([f"{file_name} ({len(filtered)})"])
            top.addChild(file_node)

            for rec in sorted(filtered, key=lambda r: (r.get("Name") or "").lower()):
                    leaf = QTreeWidgetItem([rec.get("Name") or rec.get("ItemID") or "(template)"])
                    leaf.setData(0, Qt.UserRole, rec)
                    if self.is_reskin_compat(rec):
                        leaf.setBackground(0, QColor(120, 30, 30))  # deep red background
                        leaf.setForeground(0, QColor(255, 220, 220))  # light red text
                    file_node.addChild(leaf)

        # Default collapsed (less clutter). Change to expandAll() if you prefer.
        self.user_template_tree.collapseAll()
        top.setExpanded(True)  # keep the top node open

    def _build_effective_base_for_formula(self, mod_item: dict) -> dict:
        """
        Provide the mod item to formulas with _props present and
        overrideProperties overlaid for convenience. No basegame merge.
        """
        merged = dict(mod_item or {})

        # Prefer normalized/promoted _props (supports JSON styles)
        base_props = get_base_props_dict(merged)

        # Overlay overrideProperties into _props so formulas can read a single place.
        ov = merged.get("overrideProperties", {})
        if isinstance(ov, dict):
            cur = dict(base_props) if isinstance(base_props, dict) else {}
            merged["_props"] = self._merge_dicts(cur, ov)

        # If no ov, still ensure _props exists when base_props does
        elif isinstance(base_props, dict):
            merged["_props"] = dict(base_props)

        return merged


    def compute_compat(self, base, template):
        category = self.cb_category.currentText().strip() if hasattr(self, "cb_category") else resolve_category(base)
        func = resolve_formula_func(category) if category else None
        
    #  fallback to basegame handbook category (via items_master.json)
        if not callable(func):
            hb_cat = self._handbook_parent_name(base)  # normalized with CATEGORY_ALIASES when available
            if hb_cat and hb_cat != category:
                alt = resolve_formula_func(hb_cat)
                if callable(alt):
                    category = hb_cat
                    func = alt
                    # reflect this fallback in the UI without firing signals
                    if hasattr(self, "cb_category"):
                        self.cb_category.blockSignals(True)
                        self.cb_category.setCurrentText(hb_cat)
                        self.cb_category.blockSignals(False)

        context = {
            "spt_path": self.spt_path,
            "compat_root": self.compat_root,
            "index": self.index,
        }
        if callable(func):
            try:
                effective_base = self._build_effective_base_for_formula(base)
                out = call_formula(func, {}, effective_base, template, context)
                if not isinstance(out, dict):
                    out = {"_formula_error": "Formula did not return a dict."}
                # >>> Ensure identity fields even for formula results <<<
                return self._ensure_identity_fields(base or {}, out, template)
            except Exception as e:
                minimal = self._fallback_merge(base, template)
                minimal["_formula_error"] = f"{type(e).__name__}: {e}"
                # >>> Ensure identity on fallback too (harmless if already present) <<<
                return self._ensure_identity_fields(base or {}, minimal, template)

        # No formula
        out = self._fallback_merge(base, template)
        return self._ensure_identity_fields(base or {}, out, template)

    def _fallback_merge(self, base, template):
        """
        Strict fallback: do NOT merge basegame/mod raw keys into compat.
        Produce only a minimal shell so the user can finish via UI.
        """
        out = {}

        # $type from template or base (if present)
        ttype = None
        if isinstance(template, dict):
            ttype = template.get("$type")
        if not ttype:
            ttype = base.get("$type")
        if ttype:
            out["$type"] = ttype

        # Identity
        out["ItemID"] = base.get("newId") or base.get("_guid") or base.get("id") or "compat"
        out["Name"]   = get_display_name(base)

        # If it's a WeaponMod, add minimal required fields you usually need:
        bucket = classify_realism_type(out.get("$type", ""))
        if bucket == "WeaponMod":
            out.setdefault("ModType", "")
            # Pull Weight from overrideProperties if present (scalar only)
            ov = base.get("overrideProperties", {})
            if isinstance(ov, dict):
                w = ov.get("Weight")
                if isinstance(w, (int, float)):
                    out["Weight"] = w

        return out


    def render_compat(self, base, template):
        compat = self.compute_compat(base, template)
        
        ctype = guess_type_bucket(compat, base, template)

    # ---- build an allowed set that always exists ----
        # Prefer bucket-specific keys from example.json; otherwise use the union across all buckets.
        def _schema_union(ex_schema: dict) -> set:
            if not isinstance(ex_schema, dict) or not ex_schema:
                return set()
            out = set()
            for v in ex_schema.values():
                if isinstance(v, (set, list, tuple)):
                    out.update(v)
            return out

        DEFAULT_ALLOWED = {
            # sensible base set if example.json is missing/empty
            "$type", "ItemID", "Name",
            "ModType", "WeapType", "OperationType",
            "Weight", "Ergonomics",
            "Recoil", "RecoilForceUp", "RecoilForceBack", "RecoilAngle",
            "BaseMalfunctionChance",
            "Damage", "PenetrationPower",
            "Velocity", "Loudness",
            "mousePenalty", "speedPenaltyPercent", "weaponErgonomicPenalty"
        }

        allowed = set()
        if isinstance(self.example_schema, dict) and self.example_schema:
            if ctype and self.example_schema.get(ctype):
                allowed = set(self.example_schema.get(ctype, set()))
            else:
                allowed = _schema_union(self.example_schema)
        if not allowed:
            allowed = set(DEFAULT_ALLOWED)

        # (Optional) normalize a few common aliases that may appear in example.json
        alias_norm = {
            "shortName": "ShortName",
            "short_name": "ShortName",
            "parentId": "parent",
            "ParentId": "parent",
        }
        allowed = {alias_norm.get(k, k) for k in allowed}


        # ---- create the form with the always-available allowed set ----
        form = CompatForm(compat, editable=True, schema_for_type=allowed)
        self.compat_area.setWidget(form)
        self.compat_forms = [form]



        # -- UI hint --
        have = set(k for k in compat.keys() if not k.startswith("_"))
        missing = sorted(allowed - have)
        type_text = compat.get("$type") or "(unknown)"
        pieces = [
            ("Detected $type", type_text),
            ("Type bucket", ctype or "(not classified)"),
            ("Addable fields", f"{len(missing)}")
        ]
        if ctype == "WeaponMod":
            pieces.append(("Special", "ModType options available (blank allowed)"))
        elif ctype == "Gun":
            pieces.append(("Special", "WeapType & OperationType options (blank allowed)"))
        self.lbl_compat_hint.setText(self._mk_stacked_header(pieces))
        has_func = callable(resolve_formula_func(self.cb_category.currentText().strip()))
        pieces = [
            ("Detected $type", type_text),
            ("Type bucket", ctype or "(not classified)"),
            ("Formula", "found" if has_func else "not found — pick one"),
            ("Addable fields", f"{len(missing)}" if missing else "unconstrained"),
]




    
    def batch_export(self):
        """
        Batch export for all items selected in the left list.
        For each item:
        - auto-match a template (prefers exact candidate id match)
        - compute compat (via formulas if available; else fallback)
        - write { <key>: compat } to a file in the chosen folder
        """
        sel = getattr(self, "selected_records", []) or []
        if not sel:
            QMessageBox.information(self, "Batch Export", "Select items in the list first.")
            return

        out_dir = QFileDialog.getExistingDirectory(self, "Select export folder")
        if not out_dir:
            return

        exported = 0
        for base in sel:
            # Find best template match(es) for this base
            matches, candidates = self.index.template_index.match_by_item(base)
            t = None
            # Prefer an exact candidate target match
            cand_set = set(candidates)
            for cand in matches:
                tgt = str(cand.get("ItemID") or cand.get("ItemId") or cand.get("id") or cand.get("_guid") or "")
                if tgt in cand_set:
                    t = cand
                    break
            if not t and matches:
                t = matches[0]

            # Compute compat (uses formulas.py if wired; else simple merge)
            compat = self.compute_compat(base, t)
            compat = self._ensure_identity_fields(base or {}, compat, t)

            key = str(compat.get("ItemID"))  # guaranteed
            name = self.index.display_name_for(base).replace("/", "_")
            fname = os.path.join(out_dir, f"{key}_{name}_compat.json")
            with open(fname, "w", encoding="utf-8") as f:
                json.dump({key: compat}, f, indent=2, ensure_ascii=False)
            exported += 1

        QMessageBox.information(self, "Batch Export", f"Exported {exported} file(s) to {out_dir}")



    def export_current(self):
        if not self.compat_forms:
            return
        compat = self.compat_forms[0].value()
        # Try to locate a base record for better Name/$type inference
        base = None
        iid_for_lookup = str(compat.get("ItemID") or compat.get("_guid") or "")
        if iid_for_lookup:
            for rec in self.index.items:
                if str(rec.get("newId") or rec.get("_guid") or rec.get("id") or rec.get("_id") or "") == iid_for_lookup:
                    base = rec
                    break
        compat = self._ensure_identity_fields(base or {}, compat)
        fname, _ = QFileDialog.getSaveFileName(self, "Export Compat JSON", "", "JSON Files (*.json)")
        if not fname: return
        key = str(compat.get("ItemID"))  # must exist now
        with open(fname, "w", encoding="utf-8") as f:
            json.dump({key: compat}, f, indent=2, ensure_ascii=False)
        QMessageBox.information(self, "Exported", f"Exported to {fname}")


# -------------------------
def apply_dark_stylesheet(app):
    """
    Force consistent dark backgrounds and readable text for common widgets.
    This complements the dark QPalette and fixes white-on-white controls.
    """
    app.setStyleSheet("""
    QWidget {
        color: #EAEAEA;
        background-color: #1E1F22;
    }
    QLabel {
        color: #EAEAEA;
    }
    QLineEdit, QPlainTextEdit, QTextEdit,
    QSpinBox, QDoubleSpinBox, QComboBox,
    QListWidget, QTreeWidget, QTableWidget,
    QTableView, QTreeView, QAbstractItemView,
    QDateTimeEdit, QDateEdit, QTimeEdit {
        background-color: #2B2D31;
        color: #EAEAEA;
        border: 1px solid #3A3D41;
        selection-background-color: #3A71C1;
        selection-color: #FFFFFF;
    }
    QComboBox QAbstractItemView {
        background-color: #2B2D31;
        color: #EAEAEA;
        selection-background-color: #3A71C1;
    }
    QScrollArea, QScrollArea * {
        background-color: #1E1F22;
        color: #EAEAEA;
    }
    QPushButton {
        background-color: #3A3D41;
        color: #EAEAEA;
        border: 1px solid #4A4D51;
        padding: 6px 10px;
    }
    QPushButton:hover {
        background-color: #4A4D51;
    }
    QHeaderView::section {
        background-color: #2B2D31;
        color: #EAEAEA;
        border: 1px solid #3A3D41;
        padding: 4px;
    }
    QScrollBar:vertical, QScrollBar:horizontal {
        background: #2B2D31;
    }
    QToolTip {
        background-color: #2B2D31;
        color: #EAEAEA;
        border: 1px solid #3A3D41;
    }
    QTabWidget::pane {
        border: 1px solid #3A3D41;
    }
    QTabBar::tab {
        background: #2B2D31;
        color: #EAEAEA;
        padding: 6px 12px;
        border: 1px solid #3A3D41;
        border-bottom: none;
    }
    QTabBar::tab:selected {
        background: #3A3D41;
}

    """)
def main():
    app = QApplication(sys.argv)
    set_dark_palette(app)
    apply_dark_stylesheet(app)
    w = MainWindow()
    w.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()