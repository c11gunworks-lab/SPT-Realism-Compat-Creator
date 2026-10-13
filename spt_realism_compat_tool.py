# spt_realism_compat_tool.py
import sys, os, json, re, math
from glob import iglob
from collections import defaultdict, OrderedDict
import importlib, inspect, traceback
import uuid
import itertools
import io

from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QLabel, QPushButton,
    QFileDialog, QLineEdit, QFormLayout, QComboBox, QSpinBox, QDoubleSpinBox, QCheckBox,
    QScrollArea, QMessageBox, QAbstractItemView, QTreeWidget, QTreeWidgetItem,
    QSizePolicy, QTabWidget, QDialog, QDialogButtonBox, QListWidgetItem, QGroupBox
)

from PyQt5.QtCore import Qt, QSettings, pyqtSignal, QEvent
from PyQt5.QtGui import QPalette, QColor
from PyQt5.QtWidgets import QInputDialog

FORMULAS_MOD_NAME = "formulas"
formulas_mod = None

# --- REGEX & PARSERS ---
COMPACT_ID_RE = re.compile(r"(?m)^\s*([0-9a-fA-F]{24})\s+(?:clone\s+\S+\s+)?enable\b")
GUID24_RE = re.compile(r"^[0-9a-fA-F]{24}$") 
UUID_RE    = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$")
BASE_HIDE_KEYS = {
    "Width", "Height", "BackgroundColor", "RagfairType", "ExamineTime",
    "StackMaxSize",  "Prefab", "PrefabPath", "AnimationVariantsNumber",
    "RepairCost", "RepairSpeed"
}

def is_guid_like(s: str) -> bool:
    if not isinstance(s, str) or len(s) < 8: return False
    return bool(GUID24_RE.match(s) or UUID_RE.match(s))

NAME_KEYS = {"name", "_name", "shortName"}
# Known locations of the vanilla item DB across SPT versions (relative to spt_path).
# items.json is a dict keyed by 24-char tpl id, each value carrying a "_props" dict.
BASE_ITEMS_CANDIDATES = [
    os.path.join("SPT_Data", "Server", "database", "templates", "items.json"),   # SPT 3.x
    os.path.join("SPT_Data", "Server", "database", "items.json"),                # fallback
]


def _load_base_items_db(spt_path: str) -> dict:
    """Load and index the vanilla item DB by tpl id. Returns {} if not found."""
    if not spt_path:
        return {}
    for rel in BASE_ITEMS_CANDIDATES:
        path = os.path.join(spt_path, rel)
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                # items.json is already {tpl_id: {"_props": {...}, ...}}
                if isinstance(data, dict):
                    return data
            except Exception as e:
                print(f"[compat] failed to read base item DB at {path}: {e}")
    print(f"[compat] WARNING: base item DB not found under {spt_path}; "
          f"cloned stats cannot be resolved and sparse mods will read 0 for inherited props.")
    return {}

def first_non_guid_string(value: str) -> str:
    if isinstance(value, str) and value.strip() and not is_guid_like(value.strip()): return value.strip()
    return ""

def deep_find_name(obj) -> str:
    if isinstance(obj, dict):
        locales = obj.get("locales") or obj.get("_locales")
        if isinstance(locales, dict):
            for lang in locales.values():
                if isinstance(lang, dict):
                    for key in ("name", "shortName"):
                        n = first_non_guid_string(lang.get(key, ""))
                        if n: return n
        for key in ("Name", "shortName", "_name", "displayName", "title"):
            n = first_non_guid_string(obj.get(key, ""))
            if n: return n
        for k, v in obj.items():
            if isinstance(v, (dict, list)):
                n = deep_find_name(v)
                if n: return n
            else:
                if k in NAME_KEYS:
                    n = first_non_guid_string(v)
                    if n: return n
    elif isinstance(obj, list):
        for v in obj:
            n = deep_find_name(v)
            if n: return n
    return ""

def get_display_name(rec):
    locales = rec.get("locales") or rec.get("_locales")
    if isinstance(locales, dict):
        en = locales.get("en")
        if isinstance(en, dict):
            for key in ("name", "shortName"):
                n = first_non_guid_string(en.get(key, ""))
                if n: return n

    for key in ("Name", "shortName", "_name", "displayName", "title"):
        n = first_non_guid_string(rec.get(key, ""))
        if n: return n

    for key in ("itemTplToClone","itemtpltoclone","clone","tpl","_tpl","_guid","id","_id"):
        v = rec.get(key)
        if isinstance(v, str) and v.strip() and not is_guid_like(v.strip()):
            return v.strip()

    n = deep_find_name(rec)
    if n: return n

    for key in ("itemTplToClone","itemtpltoclone","clone","tpl","_tpl","_guid","id","_id"):
        v = rec.get(key)
        if isinstance(v, str) and v.strip(): return v.strip()

    return "Unknown"

def _kv_scan(tokens: list[str], start_idx: int, stop_tokens: set[str], assign_to: dict):
    i = start_idx
    def _coerce(s: str):
        if s.lower() in ("true","false"): return s.lower() == "true"
        if re.fullmatch(r"-?\d+", s):
            try: return int(s)
            except: pass
        if re.fullmatch(r"-?\d+\.\d+", s):
            try: return float(s)
            except: pass
        return s

    while i < len(tokens)-1:
        k = tokens[i]
        if k in stop_tokens: break
        v = tokens[i+1]
        if v in stop_tokens or re.fullmatch(r"[A-Za-z_][\w\.\-]*", v) and tokens[i+2:i+3] and tokens[i+2] in stop_tokens:
            break
        assign_to[k] = _coerce(v)
        i += 2
    return i

def parse_compact_items_json(path: str):
    try: raw = open(path, "r", encoding="utf-8", errors="ignore").read()
    except Exception: return[]

    stripped = raw.lstrip()
    if stripped.startswith("{") or stripped.startswith("["): return []

    starts =[m.start(1) for m in COMPACT_ID_RE.finditer(raw)]
    if not starts: return[]
    starts.append(len(raw))

    def _coerce(s: str):
        sl = s.lower()
        if sl in ("true", "false"): return sl == "true"
        if re.fullmatch(r"-?\d+", s):
            try: return int(s)
            except: pass
        if re.fullmatch(r"-?\d+\.\d+", s):
            try: return float(s)
            except: pass
        if len(s) >= 2 and s[0] == s[-1] == '"': return s[1:-1]
        return s

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

    records =[]

    for i in range(len(starts)-1):
        chunk = raw[starts[i]:starts[i+1]]
        tokens = re.findall(r'[A-Za-z_][\w\.\-]*|\\_[A-Za-z][\w\.\-]*|[0-9a-fA-F]{24}|-?\d+\.\d+|-?\d+|".*?"', chunk)
        if not tokens: continue

        def clean(tok: str) -> str: return tok[1:] if tok.startswith("\\") else tok

        m_id = re.match(r"\s*([0-9a-fA-F]{24})", chunk)
        newId = m_id.group(1) if m_id else None

        m_clone = re.search(r"(?m)^\s*[0-9a-fA-F]{24}\s+clone\s+(\S+)\s+enable\b", chunk)
        itemTplToClone = m_clone.group(1) if m_clone else None

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

        rec = {
            "_file": path,
            "_guid": newId or inner_id or f"{os.path.basename(path)}:{i}",
            "newId": newId or inner_id,
            "itemTplToClone": itemTplToClone,
            "overrideProperties": {},
            "locales": {}
        }
        if inner_parent: rec["parent"] = inner_parent
        m_prefab = re.search(r"(?i)\bPrefab\s+path\s+([^\s]+)", chunk)
        if m_prefab:
            prefab_path = m_prefab.group(1).strip().strip('"')
            rec["overrideProperties"].setdefault("Prefab", {})["path"] = prefab_path
            rec["overrideProperties"]["PrefabPath"] = prefab_path

        m_parent = re.search(r"(?i)\bhandbook\s+ParentId\s+([0-9a-fA-F]{24})", chunk)
        if m_parent and "parent" not in rec: rec["parent"] = m_parent.group(1)

        m_price = re.search(r"(?i)\bhandbook\b.*?\bPrice\s+(\d+)", chunk, flags=re.S)
        if m_price: rec["overrideProperties"]["Price"] = int(m_price.group(1))

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
                    if key in ("handbook","items","_props","slots","grids","_type","_id","_parent","_proto"): break
                    k += 1
                break
        if name_val:
            rec["Name"] = name_val
            rec["locales"].setdefault("en", {})["name"] = name_val
        if short_val:
            rec["shortName"] = short_val
            rec["locales"].setdefault("en", {})["shortName"] = short_val

        override = {}
        for j, t in enumerate(tokens):
            if clean(t) in ("_props","_Props","props"):
                stop = {"Slots","Grids","Prefab","PrefabPath","handbook","locales", "_type","_proto","_name","_id","_parent","_mergeSlotWithChildren","item"}
                _kv_scan(tokens, j+1, stop, override)

        for j in range(len(tokens)-1):
            k_raw = clean(tokens[j]); v_raw = tokens[j+1]
            k_low = k_raw.lower()
            if k_low in INTERESTING_KEYS_LOWER:
                rec["overrideProperties"][CANON[k_low]] = _coerce(v_raw)

        for k, v in override.items():
            if isinstance(v, (int,float,bool,str)):
                rec["overrideProperties"].setdefault(k, v)

        is_weapon = bool(re.search(r'(?i)\bisweapon\s+true\b', chunk))
        rec["$type"] = "RealismMod.Gun, RealismMod" if is_weapon else "RealismMod.WeaponMod, RealismMod"

        records.append((rec["_guid"], rec))

    return records

def safe_load_formulas():
    global formulas_mod
    try:
        if FORMULAS_MOD_NAME in sys.modules:
            formulas_mod = importlib.reload(sys.modules[FORMULAS_MOD_NAME])
        else:
            formulas_mod = importlib.import_module(FORMULAS_MOD_NAME)
        # Reload restores the generated function, so re-patch every load.
        _install_scale_safe_override()
        return True, ""
    except Exception:
        return False, traceback.format_exc()

def _install_scale_safe_override():
    """Neutralise the cross-scale explicit-override leak in formulas.py.

    The generated code does, for example:
        explicit_val = explicit_override_value(base_data, ['RecoilForceBack','HorizontalRecoil'])
        pred = 0.40*pred + 0.60*float(explicit_val)
    RecoilForceBack is the VANILLA prop (316 on an HK416A5) while Realism's
    HorizontalRecoil is 140 -- so 60% of the prediction was anchored to a
    number on the wrong scale, which is why results came out roughly double.

    formulas.py also hard-codes a _props fallback for DurabilityBurnRatio,
    HeatFactorGun, CoolFactorGun and friends; all of those are rescaled by
    Realism too. Only genuinely 1:1 fields stay honoured.
    """
    if not formulas_mod: return False
    orig = getattr(formulas_mod, "explicit_override_value", None)
    if not callable(orig) or getattr(orig, "_scale_safe", False): return False

    def scale_safe_explicit_override(base_data, keys):
        ks = [keys] if isinstance(keys, str) else list(keys or ())
        safe = [k for k in ks if k in EFT_SCALE_SAFE_FIELDS]
        if not safe:
            return None          # every candidate was cross-scale -> no anchor
        return orig(base_data, safe)

    scale_safe_explicit_override._scale_safe = True
    scale_safe_explicit_override._original = orig
    formulas_mod.explicit_override_value = scale_safe_explicit_override
    return True

def resolve_formula_func(category: str):
    if not category: return None

    # Built-in ammo categories work with or without a generated formulas.py.
    if category in BUILTIN_AMMO_FORMULAS:
        return BUILTIN_AMMO_FORMULAS[category]

    if not formulas_mod: return None

    def _direct(cat):
        if hasattr(formulas_mod, "get_formula_func"):
            try:
                f = formulas_mod.get_formula_func(cat)
                if f: return f
            except Exception: pass
        for map_name in ("gun_formula_map", "mod_formula_map", "gear_formula_map", 'ammo_formula_map'):
            m = getattr(formulas_mod, map_name, None)
            if isinstance(m, dict) and cat in m: return m[cat]
        return None

    f = _direct(category)
    if f: return f

    # formulas.py's own alias table, then ours.
    ca = getattr(formulas_mod, "CATEGORY_ALIASES", {}) or {}
    for alias in (ca.get(category), RUNTIME_CATEGORY_ALIASES.get(category)):
        if alias:
            f = _direct(alias)
            if f: return f
    return None

def call_formula(func, item_entry: dict, base: dict, template: dict, context: dict) -> dict:
    try:
        sig = inspect.signature(func)
        argc = len(sig.parameters)
        if argc <= 2: return func(item_entry, base)
        elif argc == 3: return func(item_entry, base, template)
        else: return func(item_entry, base, template, context)
    except Exception as e:
        return item_entry

APP_ID = "SPT-Realism-Compat-Tool"
CONFIG_FILE = "spt_compat_tool.ini"

KNOWN_IGNORE_DIRS = { 'bundles','CustomAssortSchemes','CustomBotLoadouts','CustomLootspawnService',
                      'CustomWeaponPresets','images','src','res','locales','quests','traders',
                      '.git','.github','node_modules','dist','build','__pycache__'}

DEFAULT_EXCLUDE_DIR_CONTAINS =["spt-realism", ".git", "__pycache__"]
JSON_EXT = (".json",)
JS_EXT = (".js",)

# ---------------------------------------------------------------------------
# Hard-banned fields.
# These are never shown, never addable, never computed, and are stripped from
# anything on its way to disk. Add a key here and it disappears tool-wide.
# ---------------------------------------------------------------------------
BANNED_FIELDS = {"ConflictingItems", "LoyaltyLevel"}
BANNED_FIELDS_LOWER = {k.lower() for k in BANNED_FIELDS}

def is_banned(key) -> bool:
    return isinstance(key, str) and key.lower() in BANNED_FIELDS_LOWER

def strip_banned(d: dict) -> dict:
    """Return a copy of d with every banned key removed."""
    if not isinstance(d, dict): return d
    return {k: v for k, v in d.items() if not is_banned(k)}

def strip_banned_inplace(d: dict) -> dict:
    if isinstance(d, dict):
        for k in [k for k in d.keys() if is_banned(k)]:
            d.pop(k, None)
    return d

# ---------------------------------------------------------------------------
# Numeric precision.
# Realism happily reads 3 d.p.; the sub-0.01 fields need 4 or they round to 0.
# ---------------------------------------------------------------------------
DEFAULT_DECIMALS = 3
MAX_DECIMALS = 6

HIGH_PRECISION_FIELDS = {
    "BaseMalfunctionChance", "ModMalfunctionChance",
    "HipAccuracyRestorationDelay", "HipAccuracyRestorationSpeed",
    "HipInnaccuracyGain", "OffsetRotation",
}

# Fields whose useful range is roughly 0.0-2.0 -> small nudges when stepping.
SMALL_RANGE_FIELDS = {
    "RecoilDamping", "RecoilHandDamping", "RecoilIntensity", "VisualMulti",
    "DurabilityBurnRatio", "DurabilityBurnModificator",
    "HeatFactor", "CoolFactor", "HeatFactorGun", "CoolFactorGun",
    "CoolFactorGunMods", "HeatFactorByShot",
    "BaseChamberSpeedMulti", "BaseReloadSpeedMulti", "ReloadSpeedMulti",
    "SpallReduction", "BaseTorque",
}

# Always integers, even if a formula hands back a float.
INT_FIELDS = {
    "AutoROF", "SemiROF", "BasePriceModifier", "Price",
    "ShotgunDispersion", "Damage", "PenetrationPower",
}

# Numeric fields that must get a float editor even when the current value
# happens to be an int (0 -> QSpinBox would make 0.0025 untypeable).
FLOAT_FIELD_RE = re.compile(
    r"(Recoil|Ergonom|Accuracy|Disper|Velocity|Weight|Loudness|Flash|Convergence|"
    r"Malfunction|Heat|Cool|Durability|Chamber|Speed|Penalty|Comfort|Angle|"
    r"Torque|Stability|Handling|Impact|Spall|Multi|Intensity|Damping|dB)", re.I
)

def _decimal_places(val) -> int:
    try:
        s = repr(float(val))
    except (TypeError, ValueError):
        return 0
    if "e" in s or "E" in s: return MAX_DECIMALS
    if "." not in s: return 0
    return len(s.split(".", 1)[1].rstrip("0"))

def decimals_for(key: str, val=None) -> int:
    """How many decimal places this field is allowed to carry."""
    dec = 4 if key in HIGH_PRECISION_FIELDS else DEFAULT_DECIMALS
    # Never silently truncate a value that arrived with more precision.
    if isinstance(val, float):
        dec = max(dec, min(_decimal_places(val), MAX_DECIMALS))
    return dec

def step_for(key: str, dec: int) -> float:
    # Arrow keys should move in the field's natural increment. Typing a finer
    # value by hand still works -- the step only governs the up/down buttons.
    if key in ROUND_WHOLE_FIELDS: return 1.0
    if key in ROUND_HALF_FIELDS: return 0.5
    if dec >= 4: return 0.001
    if key in SMALL_RANGE_FIELDS: return 0.05
    return 0.5

def is_float_field(key: str) -> bool:
    if key in INT_FIELDS or key in KNOWN_BOOLS: return False
    return key in HIGH_PRECISION_FIELDS or key in SMALL_RANGE_FIELDS or bool(FLOAT_FIELD_RE.search(key or ""))

# ---------------------------------------------------------------------------
# Rounding rules.
# These snap a freshly *calculated* value only. Once a value is in the form you
# can type any precision you like and it will be exported exactly as typed --
# the snap never runs again on your manual edits.
# ---------------------------------------------------------------------------
ROUND_MODE = "half_up"   # "half_up" = .5 rounds away from zero | "ceil" = always up

ROUND_WHOLE_FIELDS = {
    "Accuracy", "WeapAccuracy", "Handling", "AimSpeed",
}

ROUND_HALF_FIELDS = {
    "Ergonomics", "Dispersion", "HorizontalRecoil", "VerticalRecoil", "Recoil",
}

def _snap(x: float, step: float) -> float:
    if step <= 0: return x
    q = x / step
    if ROUND_MODE == "ceil":
        n = math.ceil(q - 1e-9)
    else:
        n = math.floor(abs(q) + 0.5) * (1 if q >= 0 else -1)
    return round(n * step, 6)

def snap_value(key: str, val):
    """Apply this field's rounding rule to a calculated value."""
    if isinstance(val, bool) or not isinstance(val, (int, float)): return val
    if key in ROUND_WHOLE_FIELDS: return int(_snap(float(val), 1.0))
    if key in ROUND_HALF_FIELDS:  return _snap(float(val), 0.5)
    return val

def snap_compat(d: dict) -> dict:
    if not isinstance(d, dict): return d
    return {k: snap_value(k, v) for k, v in d.items()}

# ---------------------------------------------------------------------------
# Better/worse direction for the value colour coding.
# Blue        = identical to the cloned item
# Light green = a little better    Green = clearly better
# Yellow      = a little worse     Red   = clearly worse
# Grey        = no baseline, or a field with no meaningful "better"
# ---------------------------------------------------------------------------
SLIGHT_THRESHOLD = 0.10   # <=10% relative change counts as "a little"

HIGHER_IS_BETTER = {
    "Ergonomics", "Accuracy", "WeapAccuracy", "Velocity", "Convergence",
    "AimStability", "AimSpeed", "Handling",
    "CoolFactor", "CoolFactorGun", "CoolFactorGunMods",
    "BaseChamberCheckSpeed", "BaseChamberSpeedMulti", "MinChamberSpeed",
    "MaxChamberSpeed", "BaseReloadSpeedMulti", "ReloadSpeedMulti", "BaseFixSpeed",
    "RecoilDamping", "RecoilHandDamping",
    "Damage", "PenetrationPower", "ArmorLevel",
    # Flash accumulates into TotalMuzzleFlash / TotalGas, both of which the
    # UI labels as REDUCTION -- so a bigger number is less flash, not more.
    "Flash", "AimStability", "Handling",
    "ReloadSpeed", "ChamberSpeed", "FixSpeed", "MaxReloadSpeed", "MinReloadSpeed",
    "MeleeDamage", "MeleePen", "RadProtection", "GasProtection",
    "Durability", "InitialSpeed", "BallisticCoeficient", "ammoAccr",
}

LOWER_IS_BETTER = {
    "VerticalRecoil", "HorizontalRecoil", "CameraRecoil", "Recoil",
    "Dispersion", "ModShotDispersion", "ShotgunDispersion", "CenterOfImpact",
    "Weight", "Loudness", "RecoilIntensity", "VisualMulti", "BluntThroughput",
    "SpallReduction", "Comfort", "FragmentationChance", "RicochetChance",
    "BaseMalfunctionChance", "ModMalfunctionChance",
    "HeatFactor", "HeatFactorGun", "HeatFactorByShot",
    "DurabilityBurnRatio", "DurabilityBurnModificator",
    "HipInnaccuracyGain", "HipAccuracyRestorationDelay",
    "speedPenaltyPercent", "mousePenalty", "weaponErgonomicPenalty", "dB", "Price",
}

COLOR_BETTER        = "#3FBF4F"   # clearly better
COLOR_BETTER_SLIGHT = "#A5D6A7"   # a little better
COLOR_EQUAL         = "#4C8DFF"   # identical
COLOR_WORSE_SLIGHT  = "#D7C04A"   # a little worse
COLOR_WORSE         = "#E05555"   # clearly worse
COLOR_NONE          = "#8A8F98"   # no baseline / no direction

# Compat field -> the base-game _props key(s) it actually writes to.
# Taken from ItemStatHandler in json-handler.ts (weapPusherHelper / modPusherHelper /
# gearPusherHelper / ammoPusherHelper), so these are verified, not guesses.
COMPARE_ALIASES = {
    # --- guns (weapPusherHelper) ---
    "VerticalRecoil":      ("RecoilForceUp",),
    "HorizontalRecoil":    ("RecoilForceBack",),
    "Dispersion":          ("RecolDispersion", "RecoilDispersion"),   # sic: EFT's own typo
    "CameraRecoil":        ("RecoilCamera",),
    "Convergence":         ("RecoilReturnSpeedHandRotation",),
    "RecoilDamping":       ("RecoilDampingHandRotation",),
    "RecoilHandDamping":   ("RecoilReturnPathDampingHandRotation",),
    "OffsetRotation":      ("RecoilReturnPathOffsetHandRotation",),
    "RecoilIntensity":     ("RecoilCategoryMultiplierHandRotation",),
    "AutoROF":             ("bFirerate",),
    "SemiROF":             ("SingleFireRate",),   # server writes SemiROF * 1.1
    "ShotgunDispersion":   ("ShotgunDispersion", "shotgunDispersion"),
    "Ergonomics":          ("Ergonomics",),
    "Weight":              ("Weight",),
    "Velocity":            ("Velocity",),
    "RecoilAngle":         ("RecoilAngle",),
    "CenterOfImpact":      ("CenterOfImpact",),
    "BaseMalfunctionChance": ("BaseMalfunctionChance",),
    "HeatFactorGun":       ("HeatFactorGun",),
    "HeatFactorByShot":    ("HeatFactorByShot",),
    "CoolFactorGun":       ("CoolFactorGun",),
    "CoolFactorGunMods":   ("CoolFactorGunMods",),
    "DurabilityBurnRatio": ("DurabilityBurnRatio",),
    "AllowOverheat":       ("AllowOverheat",),
    "HipAccuracyRestorationDelay": ("HipAccuracyRestorationDelay",),
    "HipAccuracyRestorationSpeed": ("HipAccuracyRestorationSpeed",),
    "HipInnaccuracyGain":  ("HipInnaccuracyGain",),
    # --- weapon mods (modPusherHelper) ---
    "Accuracy":            ("Accuracy",),
    "HeatFactor":          ("HeatFactor",),
    "CoolFactor":          ("CoolFactor",),
    "ModMalfunctionChance": ("MalfunctionChance",),
    "MalfunctionChance":   ("MalfunctionChance",),
    "DurabilityBurnModificator": ("DurabilityBurnModificator",),
    "Loudness":            ("Loudness",),
    "BlocksFolding":       ("BlocksFolding",),
    "HasShoulderContact":  ("HasShoulderContact",),
    # --- gear (gearPusherHelper) ---
    "ArmorClass":          ("armorClass",),
    "ArmorLevel":          ("armorClass",),
    "Durability":          ("Durability", "MaxDurability"),
    "BluntThroughput":     ("BluntThroughput",),
    "ArmorMaterial":       ("ArmorMaterial",),
    "speedPenaltyPercent": ("speedPenaltyPercent",),
    "mousePenalty":        ("mousePenalty",),
    "weaponErgonomicPenalty": ("weaponErgonomicPenalty",),
    # --- ammo (ammoPusherHelper) ---
    "Damage":              ("Damage",),
    "PenetrationPower":    ("PenetrationPower",),
    "InitialSpeed":        ("InitialSpeed",),
    "BulletMassGram":      ("BulletMassGram",),
    "BulletDiameterMilimeters": ("BulletDiameterMilimeters",),
    "BallisticCoeficient": ("BallisticCoeficient",),
    "ammoAccr":            ("ammoAccr",),
}

# Fields that are plain base-game _props on the cloned item. Predicting these
# with ML is wrong -- the vanilla value is the correct answer and the clone
# already carries it. See the DurabilityBurnRatio note in the README comment.
# Realism keeps its own SCALE for most stats -- a vanilla EFT prop is not the
# same number as the Realism field of the same name. Nothing is copied verbatim
# any more; the fix is to stop feeding cross-scale values into the prediction
# (see scale_safe_explicit_override below), so the formula actually calculates.
REALISM_PASSTHROUGH = set()

# Fields where the EFT prop really IS 1:1 with the Realism field, so using the
# base item's value as an explicit override is legitimate. Everything else is
# rescaled by Realism and must never be pulled from _props/overrideProperties.
#   HK416A5:  RecoilForceUp 103 -> VerticalRecoil 80
#             RecoilForceBack 316 -> HorizontalRecoil 140
#             DurabilityBurnRatio 1.15 -> 0.18
#             HeatFactorGun 1.0 -> 0.2
EFT_SCALE_SAFE_FIELDS = {
    "Weight", "bFirerate", "AutoROF", "SingleFireRate", "SemiROF",
    # ammoPusherHelper writes these straight through, so they share a scale
    "Damage", "PenetrationPower", "InitialSpeed", "BulletMassGram",
    "BulletDiameterMilimeters", "BallisticCoeficient", "ammoAccr",
    "ArmorDamage", "FragmentationChance", "RicochetChance",
    "speedPenaltyPercent", "mousePenalty", "weaponErgonomicPenalty",
}

ZERO_ON_GUNS = {"Velocity", "WeapAccuracy"}

def compare_color(key: str, new_val, old_val) -> str:
    """Colour a computed value relative to its cloned baseline."""
    if old_val is None: return COLOR_NONE
    if isinstance(new_val, bool) or isinstance(old_val, bool):
        return COLOR_EQUAL if bool(new_val) == bool(old_val) else COLOR_NONE
    try:
        n = float(new_val); o = float(old_val)
    except (TypeError, ValueError):
        return COLOR_EQUAL if str(new_val) == str(old_val) else COLOR_NONE

    tol = 10 ** (-decimals_for(key)) / 2.0
    if abs(n - o) <= tol: return COLOR_EQUAL

    if key in HIGHER_IS_BETTER: better = n > o
    elif key in LOWER_IS_BETTER: better = n < o
    else: return COLOR_NONE

    denom = max(abs(o), abs(n), 1e-9)
    slight = (abs(n - o) / denom) <= SLIGHT_THRESHOLD

    if better: return COLOR_BETTER_SLIGHT if slight else COLOR_BETTER
    return COLOR_WORSE_SLIGHT if slight else COLOR_WORSE

# ---------------------------------------------------------------------------
# Field tooltips.
# Format: (one-line summary, effect of a HIGHER value, effect of a LOWER value)
# Entries listed in TOOLTIP_UNVERIFIED get a "verify" marker appended -- those
# are my best reading of Realism's behaviour rather than something I've
# confirmed against the mod source. Correct them freely; it's just a dict.
# ---------------------------------------------------------------------------
TOOLTIP_UNVERIFIED = {
    # Still unconfirmed: these are read client-side by the RealismMod C#
    # classes rather than pushed into server _props by json-handler.ts, so
    # the TS source doesn't pin their meaning down.
    # Empty: every field below has been traced to its consumer in the
    # RealismMod C# source or the server-side TypeScript.
}

FIELD_TOOLTIPS = {
    # --- identity / tags -------------------------------------------------
    "$type": ("Which Realism class this entry is parsed as. Decides which stat block the mod reads.",
              "", ""),
    "ItemID": ("The 24-character template ID of the item this compat entry applies to.", "", ""),
    "Name": ("Display name. Cosmetic only — used for your own bookkeeping and log messages.", "", ""),
    "ModType": ("Tag telling Realism what kind of attachment this is, which enables special-case handling "
                "(suppressor gas effects, bipod deploy, stock adapters, calibre conversions). Blank is valid "
                "and means 'no special handling'.", "", ""),
    "WeapType": ("Action/layout tag for guns (DI, bullpup, short_AK). Drives layout-specific recoil handling.", "", ""),
    "OperationType": ("How the action cycles (buffer, tubefed, magForward, p90). Drives reload and cycling behaviour.", "", ""),
    "TemplateType": ("Which gear template block Realism should apply (e.g. 'gear').", "", ""),

    # --- recoil ----------------------------------------------------------
    "VerticalRecoil": ("Percent change to upward recoil impulse — the muzzle climb you fight between shots.",
                       "more muzzle climb, harder to keep on target",
                       "flatter recoil, easier follow-up shots"),
    "HorizontalRecoil": ("Percent change to side-to-side recoil impulse.",
                         "more lateral wander, sprays get wider",
                         "steadier, more predictable side-to-side"),
    "Recoil": ("Overall recoil percent change where a single combined figure is used.",
               "more recoil overall", "less recoil overall"),
    "CameraRecoil": ("Percent change to how much the camera/view is kicked, separate from where rounds land. "
                     "This is the visual disturbance, not the mechanical accuracy.",
                     "more view kick, harder to track targets",
                     "calmer sight picture"),
    "RecoilAngle": ("Direction in degrees that the recoil impulse is applied. 90 is straight up; lower angles "
                    "push the muzzle back and to one side.",
                    "impulse rotates toward vertical", "impulse rotates toward horizontal"),
    "RecoilDamping": ("Written to RecoilDampingHandRotation: how quickly the recoil impulse decays "
                      "after each shot.",
                      "recoil settles faster", "recoil keeps pushing for longer"),
    "RecoilHandDamping": ("Written to RecoilReturnPathDampingHandRotation: damping on the return path "
                          "the hands travel back along after recoil.",
                          "hands settle back faster", "hands keep moving for longer"),
    "RecoilIntensity": ("Written to RecoilCategoryMultiplierHandRotation: a category-wide multiplier on "
                        "the hand-rotation recoil component.",
                        "stronger recoil", "weaker recoil"),
    "VisualMulti": ("Becomes CurrentVisualRecoilMulti and scales TargetVisualRecoil in DoVisualRecoil. "
                    "Purely cosmetic -- it does not move where rounds land. Default 1.",
                    "punchier looking recoil", "flatter, calmer looking recoil"),
    "Convergence": ("Written to RecoilReturnSpeedHandRotation: how fast the weapon returns to the "
                    "original point of aim. Shown in the UI as 'FLATNESS'. Note the tradeoff -- a "
                    "a positive Convergence is ALSO applied to vertical recoil via "
                    "ConvVRecoilConversion, which is -1f -- so it subtracts from vertical recoil. "
                    "Convergence helps twice over.",
                    "faster return to point of aim AND less vertical recoil",
                    "the muzzle drifts further off between shots"),

    # --- accuracy --------------------------------------------------------
    "Accuracy": ("Percent change to the weapon's mechanical accuracy (group size at range).",
                 "tighter groups", "looser groups"),
    "WeapAccuracy": ("The weapon's base mechanical accuracy as a percentage modifier.",
                     "tighter inherent grouping", "looser inherent grouping"),
    "Dispersion": ("Percent change to how far shots scatter off point of aim during sustained fire. This is the "
                   "spread that builds up as you keep firing, distinct from base accuracy.",
                   "shots wander further during bursts", "bursts stay tighter"),
    "ModShotDispersion": ("Buckshot spread contribution, summed across mods. The delta is sum / base, "
                          "then applied as ShotgunDispersionBase * (1 + delta). Shown as "
                          "'BUCKSHOT SPREAD'. Only meaningful on shotgun mods, so the tool "
                          "leaves it out of calculated compats -- add it by hand when you need it.",
                          "wider pattern", "tighter pattern"),
    "ShotgunDispersion": ("Pellet spread for shotguns. Integer value.",
                          "wider pattern", "tighter pattern"),
    "CenterOfImpact": ("Base shot deviation -- the cone the weapon shoots into before any player-induced "
                       "error. Weapon mods default to 0.05 server-side if the field is absent.",
                       "larger cone, less inherently accurate", "smaller cone, more inherently accurate"),
    "HipAccuracyRestorationDelay": ("Seconds before hip-fire accuracy starts recovering after firing.",
                                    "stays inaccurate longer after shooting",
                                    "starts recovering sooner"),
    "HipAccuracyRestorationSpeed": ("How fast hip-fire accuracy recovers once it starts.",
                                    "recovers faster", "recovers slower"),
    "HipInnaccuracyGain": ("How much hip-fire inaccuracy accumulates per shot.",
                           "hip fire degrades faster while shooting",
                           "hip fire holds together better"),

    # --- handling --------------------------------------------------------
    "Ergonomics": ("Flat change to ergonomics. Feeds ADS speed, sway, stamina drain and weapon handling generally.",
                   "easier to handle overall", "more sluggish, more sway, faster stamina drain"),
    "Handling": ("Percent contribution, summed across all mods, then applied as "
                 "1 - (total / 100) clamped to 0.25-2. So +25 across the build gives a 0.75x handling "
                 "modifier.",
                 "snappier handling", "more sluggish"),
    "AimSpeed": ("Percent change to how fast the weapon comes up into aimed fire.",
                 "faster ADS", "slower ADS"),
    "AimStability": ("Percent contribution, summed across all mods, then applied as "
                     "1 - (total / 100) clamped to 0.25-2. Shown in the UI as 'STABILITY'.",
                     "steadier hold", "more sway while aimed"),
    "Weight": ("Mass in kilograms. Weight feeds ergonomics, stamina drain, recoil behaviour and movement speed, "
               "so it quietly affects several other stats.",
               "heavier: worse ergo and stamina, sometimes less felt recoil",
               "lighter: better ergo and stamina, sometimes more felt recoil"),
    "BaseTorque": ("A signed DISTANCE, not a quality score: the moment arm fed into "
                   "TorqueCalc(distance, weight, weapClass) to work out weapon balance. Mod positions use "
                   "values like -15 to +10. Negative is rearward (butt-heavy), positive is forward "
                   "(muzzle-heavy). Neither end is simply 'better'.",
                   "", ""),
    "OffsetRotation": ("Written to RecoilReturnPathOffsetHandRotation: how far off the original point of "
                       "aim the return path settles, i.e. the drift left behind after each shot.",
                       "settles further from where you were aiming", "returns closer to point of aim"),

    # --- reliability and heat -------------------------------------------
    "BaseMalfunctionChance": ("The weapon's base probability of a malfunction per shot. Values live in the "
                              "0.0001-0.5 band, so small numbers matter here. Legacy guard on the server: "
                              "any value >= 0.1 is silently multiplied by 0.01.",
                              "jams, misfeeds and misfires happen more often",
                              "more reliable"),
    "ModMalfunctionChance": ("This part's additive change to malfunction probability. Same tiny scale as the base "
                             "value — 0.005 is a meaningful change.",
                             "makes the weapon less reliable", "makes the weapon more reliable"),
    "AllowFeed": ("Whether feed failures can occur with this part fitted.", "", ""),
    "AllowJam": ("Whether jams can occur with this part fitted.", "", ""),
    "AllowMisfire": ("Whether misfires can occur with this part fitted.", "", ""),
    "AllowSlide": ("Whether slide/bolt malfunctions can occur with this part fitted.", "", ""),
    "AllowOverheat": ("Whether this weapon can overheat at all.", "", ""),
    "HeatFactor": ("Multiplier on how fast this part adds heat when firing.",
                   "heats up faster", "heats up slower"),
    "HeatFactorGun": ("Multiplier on the weapon's overall heat accumulation. A plain base-game prop, read "
                      "from the cloned item rather than predicted. Realism multiplies it by 1.125 at load "
                      "time when trader repair changes are on.",
                      "heats up faster", "heats up slower"),
    "HeatFactorByShot": ("Heat added per individual shot.",
                         "each round adds more heat", "each round adds less heat"),
    "CoolFactor": ("Multiplier on how fast this part sheds heat.",
                   "cools faster", "cools slower"),
    "CoolFactorGun": ("Multiplier on the weapon's own cooling rate. A plain base-game prop, read from the "
                      "cloned item. Realism doubles it at load time when trader repair changes are on.",
                      "cools faster", "cools slower"),
    "CoolFactorGunMods": ("Multiplier on cooling contributed by attached mods.",
                          "mods help it cool faster", "mods help it cool less"),
    "DurabilityBurnRatio": ("How fast the weapon loses durability while firing. A plain base-game prop -- "
                            "the AKM ships 0.18. The tool now reads this straight off the cloned item "
                            "instead of predicting it.",
                            "wears out faster", "wears out slower"),
    "DurabilityBurnModificator": ("Multiplier on durability consumption. Mods multiply together into "
                                  "TotalModDuraBurn, so 1.0 is neutral and the default when absent.",
                                  "accelerates wear", "reduces wear"),

    # --- ballistics / signature -----------------------------------------
    "Velocity": ("Percent change to muzzle velocity. Feeds downrange energy, penetration retention and drop.",
                 "faster round, flatter trajectory, better retained penetration",
                 "slower round, more drop"),
    "Loudness": ("Summed across mods, then applied as ((total / 80) + 1) * the caliber loudness factor. "
                 "Bullpups and P90-pattern guns take a further 1.18x.",
                 "audible from further away", "quieter, shorter detection radius"),
    "Flash": ("Muzzle flash / gas REDUCTION, not flash amount. On muzzle combos, flash hiders and "
              "barrels it accumulates into TotalMuzzleFlash; on everything else it feeds TotalGas "
              "(the VISUAL GAS attribute) instead. The UI labels it 'MUZZLE FLASH REDUCTION'.",
              "less flash / less gas obscuring your sight picture",
              "more flash and gas"),
    "dB": ("Sound level figure used for gear (headsets) and suppression maths.",
           "louder", "quieter"),
    "Damage": ("Per-projectile damage for ammunition.", "hits harder", "hits softer"),
    "PenetrationPower": ("Ammunition penetration value, checked against armour class.",
                         "defeats better armour", "stopped by lighter armour"),
    "BasePriceModifier": ("Multiplier applied to the item's base trader/flea price.",
                          "more expensive", "cheaper"),
    "Price": ("Flat price figure for the item.", "more expensive", "cheaper"),

    # --- rate of fire / cycling -----------------------------------------
    "AutoROF": ("On a gun: full-auto cyclic rate in RPM, copied from bFirerate. On a mod: an RPM delta "
                "added to the weapon's rate. The client floors the final figure at 400 RPM.",
                "faster cyclic rate", "slower cyclic rate"),
    "SemiROF": ("On a gun: semi-auto rate in RPM. On a mod: an RPM delta. The server writes "
                "SingleFireRate = SemiROF * 1.1, and the client floors the final figure at 300 RPM.",
                "faster semi-auto cap", "slower semi-auto cap"),
    "IsManuallyOperated": ("Whether the action must be worked by hand between shots (pump, bolt, lever).", "", ""),
    "CanCycleSubs": ("Whether the weapon reliably cycles subsonic ammunition with this part fitted.", "", ""),
    "NoFiremodeOnBoltcatch": ("Whether the fire selector is blocked while the bolt is locked back.", "", ""),

    # --- speeds ----------------------------------------------------------
    "BaseChamberCheckSpeed": ("How fast the chamber-check animation plays.",
                              "faster press-check", "slower press-check"),
    "BaseChamberSpeedMulti": ("Multiplier on chambering speed.", "faster chambering", "slower chambering"),
    "MinChamberSpeed": ("Lower bound on chambering speed.", "faster floor", "slower floor"),
    "MaxChamberSpeed": ("Upper bound on chambering speed.", "faster ceiling", "slower ceiling"),
    "BaseReloadSpeedMulti": ("Multiplier on reload speed.", "faster reloads", "slower reloads"),
    "ReloadSpeedMulti": ("Multiplier on reload speed for this gear/part.", "faster reloads", "slower reloads"),
    "BaseFixSpeed": ("Malfunction-clearing speed. StatCalc computes "
                     "clamp(BaseFixSpeed * ergoWeightMulti * chamberSpeedMod, MinChamberSpeed, "
                     "MaxChamberSpeed) -- note it is bounded by the CHAMBER speed limits, not reload ones.",
                     "clears jams faster", "clears jams slower"),

    # --- ADS / contact ---------------------------------------------------
    "AllowADS": ("Whether aiming down sights is permitted with this item equipped.", "", ""),
    "WeaponAllowADS": ("Whether this weapon can be aimed down sights at all.", "", ""),
    "StockAllowADS": ("Whether ADS is allowed with this stock fitted — the flag folded stocks use.", "", ""),
    "HasShoulderContact": ("Whether the part actually provides a shoulder weld. Big recoil implications: a folded "
                           "or missing stock loses this.", "", ""),
    "BlockFolding": ("Whether this part stops the stock from folding.", "", ""),
    "BlocksFolding": ("Whether this part stops the stock from folding.", "", ""),

    # --- gear ------------------------------------------------------------
    "ArmorClass": ("Client-side STRING label on the Gear class (e.g. 'ESAPI', 'GOST 5'), default "
                   "'unclassified'. This is not the numeric armour level -- use ArmorLevel for that.",
                   "", ""),
    "MaskToUse": ("Which face-mask overlay/effect this headgear uses.", "", ""),
    "CanSpall": ("Whether rounds stopped by this armour can produce spall.", "", ""),
    "SpallReduction": ("Despite the name this is the fraction of spall that GETS THROUGH -- "
                       "CalculatSpalling multiplies spall damage directly by it. The UI inverts it and "
                       "shows (1 - value) * 100 as 'SPALLING REDUCTION', so a raw 0.3 displays as 70%.",
                       "more spall reaches the wearer", "better spall protection"),
    "BlocksMouth": ("Whether the item covers the mouth, which affects breathing and stamina recovery.", "", ""),
    "Comfort": ("A multiplier, default 1. GearPatches displays it as -1 * (value - 1) * 100, so a value "
                "above 1 shows as a negative percentage and is a penalty. Below 1 is a bonus.",
                "less comfortable, larger penalties", "more comfortable, smaller penalties"),
    "speedPenaltyPercent": ("Movement speed penalty from wearing this. Normally negative.",
                            "less speed lost", "more speed lost"),
    "mousePenalty": ("Turn/aim speed penalty from wearing this. Normally negative.",
                     "less turn speed lost", "more turn speed lost"),
    "weaponErgonomicPenalty": ("Ergonomics penalty applied to the held weapon. Normally negative.",
                               "less ergo lost", "more ergo lost"),

    # --- added from the C# classes and pusher helpers -------------------
    "ArmorLevel": ("Server-side numeric armour class, written into _props.armorClass by gearPusherHelper. "
                   "This is the one that decides what the plate actually stops.",
                   "stops heavier threats", "stops less"),
    "Durability": ("Armour durability. Written to both Durability and MaxDurability server-side.",
                   "takes more hits before degrading", "degrades sooner"),
    "BluntThroughput": ("Fraction of blunt damage that passes through the armour. The UI inverts it and "
                        "shows 'AVG. BLUNT DAMAGE REDUCTION'.",
                        "more blunt damage reaches you", "better blunt protection"),
    "ArmorMaterial": ("Material enum driving destructibility and spall behaviour. Realism sets "
                      "Destructibility to Glass 0.45, ArmoredSteel 0.375, Aramid 0.33, Ceramic 0.3, "
                      "UHMWPE 0.255, Combined 0.225, Aluminium 0.2, Titan 0.15. ArmoredSteel and Titan "
                      "count as metal and take extra spall as durability drops.", "", ""),
    "IsGasMask": ("Marks the item as a gas mask. Combined with MaskToUse it forces FaceShieldComponent, "
                  "armorClass 1, 25 max durability, and adds a gas filter slot when hazard zones are on.",
                  "", ""),
    "GasProtection": ("Fraction of gas exposure blocked. Displayed as a percentage.",
                      "better gas protection", "less protection"),
    "RadProtection": ("Fraction of radiation exposure blocked. Displayed as a percentage.",
                      "better radiation protection", "less protection"),
    "ReloadSpeed": ("Weapon-mod reload speed contribution, summed across mods into SDReloadSpeedModifier.",
                    "faster reloads", "slower reloads"),
    "ChamberSpeed": ("Weapon-mod chambering speed contribution, summed into SDChamberSpeedModifier.",
                     "faster chambering", "slower chambering"),
    "FixSpeed": ("Weapon-mod malfunction-clearing contribution. Note the source marks SDFixSpeedModifier "
                 "as unused, replaced by chamber speed.",
                 "clears jams faster", "clears jams slower"),
    "MeleeDamage": ("Melee damage, read off muzzle devices (bayonets).", "hits harder", "hits softer"),
    "MeleePen": ("Melee penetration, read off muzzle devices (bayonets).",
                 "defeats more armour", "defeats less"),
    "MaxReloadSpeed": ("Upper bound on the weapon's reload speed multiplier.", "faster ceiling", "slower ceiling"),
    "MinReloadSpeed": ("Lower bound on the weapon's reload speed multiplier.", "faster floor", "slower floor"),
    "EnableBSGVisRecoil": ("Whether BSG's stock visual recoil is left enabled for this weapon.", "", ""),
    "ReduceBSGVisRecoil": ("Whether BSG's visual recoil is damped down for this weapon.", "", ""),
    "InitialSpeed": ("Muzzle velocity in m/s. Drives kinetic energy directly: "
                     "KE = (0.5 * BulletMassGram * InitialSpeed^2) / 1000, which feeds armour "
                     "penetration and spalling. Velocity is squared here, so it matters more than mass.",
                     "faster round, flatter trajectory, more energy on target", "slower, more drop"),
    "BallisticCoeficient": ("How well the round holds velocity downrange. Spelled with one 'f' -- that is "
                            "the base-game field name. Realism's range is roughly 0.009-0.02 for buckshot "
                            "pellets and 0.1-0.55 for rifle rounds.",
                            "retains velocity better at range", "sheds velocity faster"),
    "BulletMassGram": ("Projectile mass in grams. The other half of "
                       "KE = (0.5 * BulletMassGram * InitialSpeed^2) / 1000. Buckshot pellets are ~0.4-1.9g "
                       "since the value is per projectile, not per shell.",
                       "heavier projectile, more energy", "lighter projectile"),
    "BulletDiameterMilimeters": ("Projectile diameter in mm. Base-game spelling, one 'l' in 'Milimeters'.",
                                 "larger calibre", "smaller calibre"),
    "ProjectileCount": ("Projectiles per shot. Note Realism sets Damage as the PER-PELLET figure: its own "
                        "buckshot entries compute Damage = total / ProjectileCount.",
                        "more pellets", "fewer pellets"),
    "PenetrationPowerDiviation": ("Random spread applied around PenetrationPower shot to shot.",
                                  "less consistent penetration", "more consistent penetration"),
    "FragmentationChance": ("Chance the round fragments. In CalculatSpalling it is scaled by "
                            "ArmorDamage / InitialSpeed and raises spall damage as (chance + 1).",
                            "fragments more often, more spall behind armour", "fragments less"),
    "RicochetChance": ("Chance the round deflects. Also scaled by ArmorDamage / InitialSpeed and raises "
                       "spall damage as (chance + 1).",
                       "deflects more often", "deflects less"),
    "ammoAccr": ("Ammunition accuracy modifier, signed. Realism's own values run about -130 (buckshot) "
                 "to +90 (match rifle ammo); 0 is neutral.",
                 "tighter groups", "looser groups"),
}

def tooltip_for(key: str) -> str:
    entry = FIELD_TOOLTIPS.get(key)
    if not entry:
        return f"<b>{key}</b><br><i>No description recorded yet for this field.</i>"

    summary, up, down = entry
    html = f"<b>{key}</b><br>{summary}"
    if up or down:
        html += "<br><br>"
        if up:   html += f"<span style='color:#9ad0a0'>▲ higher:</span> {up}<br>"
        if down: html += f"<span style='color:#e0a0a0'>▼ lower:</span> {down}"

    direction = ("Higher is better." if key in HIGHER_IS_BETTER
                 else "Lower is better." if key in LOWER_IS_BETTER
                 else "No inherent better/worse direction.")
    html += f"<br><br><span style='color:#9aa0a6'>{direction}</span>"

    if key in ROUND_WHOLE_FIELDS:
        html += "<br><span style='color:#9aa0a6'>Calculated values snap to a whole number.</span>"
    elif key in ROUND_HALF_FIELDS:
        html += "<br><span style='color:#9aa0a6'>Calculated values snap to the nearest 0.5.</span>"

    if key in TOOLTIP_UNVERIFIED:
        html += "<br><span style='color:#d7a04a'>⚠ Description unverified — check against mod source.</span>"
    return html

# ---------------------------------------------------------------------------
# Category resolution helpers.
#
# The handbook walk returns *handbook* category names ("Pistols", "Muzzle"),
# but the formula maps are keyed on *class* names ("Pistol", "MuzzleBrakes").
# formulas.py only aliases a handful of these, so the gaps are patched here at
# runtime -- that way pistols resolve without regenerating formulas.py.
# ---------------------------------------------------------------------------
RUNTIME_CATEGORY_ALIASES = {
    "Pistols": "Pistol",
    "Pistol": "Pistols",
    "Muzzle": "MuzzleBrakes",
    "FlashHiders": "MuzzleBrakes",
    "MuzzleAdapters": "MuzzleBrakes",
    "BoltActionRifles": "SniperRifles",
    "ArmorPlates": "ArmorVests",
    "ArmorMasks": "Headwear",
    "TacticalRigs": "ArmorVests",
    "GrenadeLaunchers": "Launchers",
    "Launcher": "Launchers",
    "Rounds": "Ammo",
    "AmmoBoxes": "Ammo",
    "Barrels": "Barrel",
    "Handguards": "Handguard",
    "Receiver": "ReceiversSlides",
    "ReceiversSlides": "Receiver",
    "IronSights": "Sights",
    "Optics": "Sights",
    "Collimators": "Sights",
    "AssaultScopes": "Sights",
    "CompactCollimators": "Sights",
    "StocksChassis": "Stock",
    "Stocks": "Stock",
    "ForeGrips": "Foregrip",
    "PistolGrips": "PistolGrip",
    "ChargingHandles": "ChargingHandle",
    "GasBlocks": "Gasblock",
    "Visors": "Visor",
    "Headsets": "Headset",
}

# _props.weapClass is the most reliable signal for what a gun actually is --
# far better than walking a handbook tree the mod author may have set loosely.
WEAPCLASS_TO_CATEGORY = {
    "pistol": "Pistol",
    "revolver": "Pistol",
    "smg": "SMGs",
    "assaultrifle": "AssaultRifles",
    "assaultcarbine": "AssaultCarbines",
    "machinegun": "MachineGuns",
    "shotgun": "Shotguns",
    "sniperrifle": "SniperRifles",
    "marksmanrifle": "MarksmanRifles",
    "grenadelauncher": "GrenadeLaunchers",
    "speciallweapon": "SpecialWeapons",
    "specialweapon": "SpecialWeapons",
}

MUZZLE_FAMILY = {"Muzzle", "MuzzleBrakes", "Compensators", "MuzzleCombos",
                 "Suppressors", "FlashHiders", "MuzzleAdapters"}


def muzzle_subcategory(rec: dict) -> str:
    """Split a muzzle device into the four sub-classes the emitter trains on.

    The handbook walk only ever returns the umbrella category "Muzzle", so
    without this every muzzle device resolved to MuzzleBrakes -- a suppressor
    was being scored against the brake model. This mirrors the Muzzle split in
    emit_form_test.main() exactly so the tool asks for the model the item was
    actually trained under. Returns "" when the item is not a muzzle device.
    """
    if not isinstance(rec, dict):
        return ""

    name = " ".join(
        str(rec.get(k, "") or "")
        for k in ("_preset_hint", "Name", "_name", "shortName")
    ).lower()

    mod_type = ""
    for src in (rec.get("overrideProperties"), rec.get("_props"), rec):
        if isinstance(src, dict):
            v = src.get("muzzleModType") or src.get("MuzzleModType")
            if isinstance(v, str) and v.strip():
                mod_type = v.strip().lower()
                break

    if not mod_type and not name:
        return ""

    if mod_type in ("silencer", "pms") or "suppressor" in name or "silencer" in name:
        return "Suppressors"
    if mod_type == "adapter" or "adapter" in name or "thread" in name:
        return "MuzzleAdapters"
    if mod_type == "flashhider" or "flash" in name or "hider" in name:
        return "FlashHiders"
    # muzzleModType separates these three and they are not interchangeable:
    # a compensator makes flash worse (+4.82 mean) while a brake barely moves it
    # (-1.63), and a brake is twice the camera-recoil reduction of a combo.
    if mod_type == "conpensator":          # BSG's spelling
        return "Compensators"
    if mod_type == "muzzlecombo":
        return "MuzzleCombos"
    if mod_type == "brake" or "brake" in name or "compensator" in name:
        return "MuzzleBrakes"
    return ""


def weapclass_category(rec: dict) -> str:
    """Map an item's _props.weapClass to a formula category, if it has one."""
    if not isinstance(rec, dict): return ""
    for src in (rec.get("_props"), rec.get("overrideProperties"), rec):
        if isinstance(src, dict):
            wc = src.get("weapClass") or src.get("WeapClass")
            if isinstance(wc, str) and wc.strip():
                return WEAPCLASS_TO_CATEGORY.get(wc.strip().lower().replace(" ", ""), "")
    return ""

# ---------------------------------------------------------------------------
# What the game can actually READ back.
#
# There is ONE json, and the server owns it. ItemStatHandler.processTemplateJson
# loads db/templates/user_templates and does two things with each entry:
#   1. runs it through the relevant pusher helper, writing values into _props
#   2. when called with isForClientDataRequest, stores the entry VERBATIM into
#      rawTemplateData, which is what /RealismMod/GetTemplateData serves to the
#      client for deserialising into the C# classes in TemplateStats.cs
#
# So a field is valid if EITHER of those consumes it -- both arrive via the
# server. The only thing that matters for export correctness is whether a field
# has a consumer at all. The APPLIED_BY split below is kept purely as reference
# for working out sensible values; it is not a validity distinction.
# ---------------------------------------------------------------------------
_APPLIED_BY_PLUGIN = {
    "Gun": {
        "WeapType", "BaseTorque", "HasShoulderContact", "BaseReloadSpeedMulti",
        "OperationType", "WeapAccuracy", "RecoilDamping", "RecoilHandDamping",
        "WeaponAllowADS", "BaseChamberSpeedMulti", "MaxChamberSpeed",
        "MinChamberSpeed", "IsManuallyOperated", "MaxReloadSpeed",
        "MinReloadSpeed", "BaseChamberCheckSpeed", "BaseFixSpeed",
        "VisualMulti", "EnableBSGVisRecoil", "ReduceBSGVisRecoil",
    },
    "WeaponMod": {
        "ModType", "VerticalRecoil", "HorizontalRecoil", "Dispersion",
        "CameraRecoil", "AutoROF", "SemiROF", "ModMalfunctionChance",
        "ReloadSpeed", "AimSpeed", "ChamberSpeed", "Convergence",
        "CanCycleSubs", "RecoilAngle", "StockAllowADS", "FixSpeed",
        "ModShotDispersion", "MeleeDamage", "MeleePen", "Flash",
        "AimStability", "Handling",
    },
    "Gear": {
        "AllowADS", "ArmorClass", "CanSpall", "SpallReduction",
        "ReloadSpeedMulti", "BlocksMouth", "IsGasMask", "RadProtection",
        "GasProtection", "MaskToUse", "dB", "Comfort",
    },
    "Ammo": set(),   # the C# Ammo class carries no stats of its own
}

_APPLIED_BY_PROPS = {
    "Gun": {
        "BaseMalfunctionChance", "HeatFactorGun", "HeatFactorByShot",
        "CoolFactorGun", "CoolFactorGunMods", "DurabilityBurnRatio",
        "AllowOverheat", "Velocity", "Ergonomics", "VerticalRecoil",
        "HorizontalRecoil", "Dispersion", "CameraRecoil", "RecoilAngle",
        "CenterOfImpact", "HipAccuracyRestorationDelay",
        "HipAccuracyRestorationSpeed", "HipInnaccuracyGain",
        "ShotgunDispersion", "Weight", "AutoROF", "SemiROF",
        "DoubleActionAccuracyPenalty", "Convergence", "RecoilDamping",
        "RecoilHandDamping", "OffsetRotation", "RecoilIntensity",
        "RecoilCenter", "CanQueueSecondShot", "BurstShotsCount",
        "weapFireType", "MasteryCategory",
    },
    "WeaponMod": {
        "Ergonomics", "Accuracy", "CenterOfImpact", "HeatFactor", "CoolFactor",
        "MalfunctionChance", "DurabilityBurnModificator", "BlocksFolding",
        "Weight", "ShotgunDispersion", "Loudness", "HasShoulderContact",
        "Velocity",
        # Magazine timing. These were missing from both applied-by tables, so
        # field_status() reported them as having no consumer and the editor
        # flagged them with a red warning. They are set on all 224 magazines in
        # Realism's own MagazineTemplates.json and the server does read them.
        "CheckTimeModifier", "LoadUnloadModifier",
    },
    "Gear": {
        "speedPenaltyPercent", "mousePenalty", "weaponErgonomicPenalty",
        "ArmorLevel", "Durability", "BluntThroughput", "ArmorMaterial",
        "Weight",
    },
    "Ammo": {
        "PenetrationPower", "Weight", "InitialSpeed", "BulletMassGram",
        "BulletDiameterMilimeters", "ammoAccr", "DurabilityBurnModificator",
        "HeatFactor", "Damage", "BallisticCoeficient",
    },
}

# Identity / routing keys that are always legitimate.
STRUCTURAL_FIELDS = {"$type", "ItemID", "Name", "TemplateID"}

# Present throughout Realism's own shipped templates but with no consumer in
# either the C# classes or the pusher helpers. Harmless, just inert.
INERT_KNOWN_FIELDS = {"TemplateType", "Price", "BasePriceModifier", "LoyaltyLevel"}

# ---------------------------------------------------------------------------
# Ammunition model.
#
# Fitted against the "item" section of the base-game ammo dump -- Realism's own
# hand-authored values, 138 single-projectile rounds across 21 calibres.
# Buckshot is excluded: multi-pellet loads follow different rules.
#
#   Damage      = a + b * momentum            (momentum = mass_g * v / 1000)
#   Penetration = a + b * v + c * sectional_density
#   BC          = a + b * sectional_density   (sectional_density = kg / cm^2)
#
# Momentum beats kinetic energy for damage (r=0.92 vs 0.85) in Realism's data.
# Coefficients are split by bullet construction because that is what the raw
# numbers demand: HP/SP has the steepest damage slope, AP the highest
# penetration intercept.
#
# Fit quality (R^2 / mean absolute error):
#   Damage  AP 0.74/12.6   FMJ 0.90/12.6   HP-SP 0.62/18.4
#   Pen     AP 0.55/7.9    FMJ 0.66/8.6    HP-SP 0.61/4.6
#   BC      0.75
#
# These are a defensible STARTING POINT, not an oracle. Expect roughly +/-13
# damage and +/-8 penetration against a hand-tuned equivalent. Always compare
# against the reference rounds shown for the calibre before accepting.
# ---------------------------------------------------------------------------
AMMO_MODEL = {"diameter": {".300": 7.82,".338 Lapua Magnum": 8.6,".357 Magnum": 9.07,".366 TKM": 9.5,".45 ACP": 11.5,".50 AE": 12.7,"12.7x108mm": 12.98,"12.7x55mm": 12.7,"4.6x30mm": 4.6,"5.45x39mm": 5.6,"5.56x45mm": 5.7,"5.7x28mm": 5.7,"6.8x51mm": 7.0,"7.62x25mm": 7.85,"7.62x39mm": 7.9,"7.62x51mm": 7.82,"7.62x54mm R": 7.92,"9x18mm": 9.27,"9x19mm": 9.02,"9x21mm": 9.02,"9x39mm": 9.25},"damage": {"AP": [28.86745803342013,9.83858401564454],"FMJ": [40.1663287955971,8.594406232562443],"HP/SP": [36.924744500702595,13.375508426201268]},"pen": {"AP": [15.683393237408747,0.04191452408200236,1431.3711595701404],"FMJ": [3.444501642213391,0.04848814713158353,1062.6937044453557],"HP/SP": [7.01577287268861,0.029247630836270355,1233.9066497329497]},"bc": [-0.04219436464769867,17.468792989794494],"reference": {".300": [["Blackout BCP FMJ",9.5,516.0,79.0,53.0,0.334],["Blackout AP",8.3,680.0,74.0,59.0,0.334],["Blackout V-Max",7.13,645.0,115.0,49.0,0.334],["Whisper",14.0,300.0,62.0,39.0,0.334],["Blackout M62 Tracer",9.2,556.0,76.0,55.0,0.334],["Blackout CBJ",9.3,725.0,70.0,62.0,0.334]],".338 Lapua Magnum": [["FMJ",16.2,877.0,180.0,85.0,0.48],["AP",15.5,900.0,150.0,115.0,0.477],["TAC-X",18.5,846.0,217.0,75.0,0.476],["UCW",16.2,860.0,195.0,70.0,0.48]],".357 Magnum": [["FMJ",10.15,385,90.0,46.0,0.163],["HP",10.3,481,135.0,38.0,0.124],["JHP",10.3,425,125.0,43.0,0.155],["SP",10.2,455,110.0,40.0,0.189]],".366 TKM": [["FMJ",13.0,580.0,110.0,54.0,0.202],["EKO",6.5,770.0,105.0,58.0,0.135],["Geksa",15.5,550.0,122.0,51.0,0.241],["AP-M",15.6,567.0,100.0,60.0,0.373]],".45 ACP": [["Match FMJ",14.9,290.0,58.0,30.0,0.131],["RIP",10.5,292.0,65.0,25.0,0.131],["AP",13.8,365.0,56.0,51.0,0.197],["Lasermatch FMJ",14.9,254.0,48.0,24.0,0.161],["Hydra-Shok",14.9,274.0,75.0,21.0,0.114]],".50 AE": [["FMJ",19.4,440,120.0,40.0,0.131],["JHP",19.4,440,150.0,30.0,0.122],["Copper Solid",25.9,460,100.0,49.0,0.163],["Hawk JSP",26.4,465,130.0,35.0,0.166]],"12.7x108mm": [["B-32",48.3,818.0,350.0,85.0,0.623],["BZT-44M",48.3,818.0,350.0,85.0,0.623]],"12.7x55mm": [["PS12",32.9,300.0,135.0,57.0,0.426],["PS12A",7.0,870.0,150.0,53.0,0.091],["PS12B",17.95,570.0,125.0,64.0,0.151]],"4.6x30mm": [["FMJ SX",2.6,620.0,41.0,44.0,0.228],["Action SX",2.0,690.0,55.0,38.0,0.175],["AP SX",2.0,680.0,39.0,52.0,0.14],["Subsonic SX",5.0,290.0,34.0,51.0,0.437],["JSP SX",2.0,579.0,47.0,41.0,0.175]],"5.45x39mm": [["BP gs",3.7,910.0,66.0,69.0,0.252],["BS gs",4.1,840.0,64.0,75.0,0.254],["BT gs",3.1,905.0,67.0,67.0,0.209],["FMJ",3.9,905.0,77.0,55.0,0.266],["HP",3.56,905.0,110.0,52.0,0.246],["PP gs",3.62,880.0,66.0,65.0,0.254],["PRS gs",3.85,910.0,64.0,44.0,0.266],["PS gs",3.43,880.0,71.0,58.0,0.235],["SP",3.6,895.0,95.0,54.0,0.246],["T gs",3.23,883.0,72.0,54.0,0.223],["US gs",5.1,340.0,45.0,30.0,0.355],["PPBS gs Igolnik",4.1,850.0,62.0,84.0,0.283],["7N40",3.64,830.0,65.0,70.0,0.252]],"5.56x45mm": [["M855",4.0,902.0,63.0,69.0,0.233],["M855A1",4.0,942.0,79.0,75.0,0.233],["M856",4.14,891.0,68.0,55.0,0.241],["M856A1",3.63,945.0,72.0,63.0,0.269],["M995",3.37,980.0,65.0,83.0,0.196],["MK 255 Mod 0 (RRLP)",4.0,880.0,73.0,48.0,0.335],["FMJ",3.56,993.0,74.0,58.0,0.252],["HP",3.56,976.0,110.0,51.0,0.209],["Warmageddon",3.56,983.0,125.0,56.0,0.335],["MK 318 Mod 0 (SOST)",4.0,927.0,94.0,64.0,0.269],["SSA AP",4.54,1013.0,61.0,90.0,0.196]],"5.7x28mm": [["SS190",2.0,716.0,39.0,53.0,0.233],["L191",2.0,716.0,44.0,50.0,0.233],["SB193",3.56,305.0,35.0,52.0,0.233],["SS198LF",1.75,792.0,45.0,41.0,0.233],["SS197SR",2.59,594.0,60.0,30.0,0.233],["R37.F",2.4,729.0,50.0,48.0,0.075],["R37.X",2.4,724.0,53.0,46.0,0.075]],"6.8x51mm": [["SIG Hybrid",8.75,884.0,140.0,75.0,0.55],["SIG FMJ",8.75,792.0,120.0,65.0,0.4]],"7.62x25mm": [["TT AKBS",5.5,425.0,68.0,32.0,0.127],["TT FMJ43",7.2,427.0,72.0,27.0,0.055],["TT LRN",6.35,385.0,60.0,38.0,0.146],["TT LRNPC",7.2,375.0,56.0,41.0,0.119],["TT P gl",5.5,430.0,52.0,36.0,0.127],["TT Pst gzh",5.46,430.0,50.0,50.0,0.126],["TT PT gzh",5.39,415.0,55.0,30.0,0.124]],"7.62x39mm": [["PS gzh",7.9,725.0,86.0,60.0,0.28],["BP gzh",7.9,740.0,80.0,70.0,0.28],["T-45M1 gzh",7.6,725.0,90.0,54.0,0.227],["US gzh",12.6,300.0,60.0,45.0,0.379],["HP",8.0,754.0,128.0,52.0,0.278],["MAI AP",7.2,875.0,70.0,80.0,0.28],["PP gzh",7.9,732.0,83.0,63.0,0.28],["FMJ",7.9,775.0,95.0,55.0,0.28],["SP",7.9,770.0,120.0,54.0,0.28]],"7.62x51mm": [["M80",9.2,860.0,122.0,61.0,0.335],["M61",9.75,854.0,115.0,80.0,0.346],["M62 Tracer",9.52,856.0,125.0,60.0,0.326],["BCP FMJ",11.34,800.0,126.0,55.0,0.402],["TCW SP",10.8,808.0,137.0,52.0,0.383],["Ultra Nosler",10.6,822.0,155.0,53.0,0.375],["M993",8.2,915.0,110.0,94.0,0.291],["M80A1",8.42,914.0,130.0,84.0,0.335]],"7.62x54mm R": [["SNB gzh",9.8,830.0,125.0,85.0,0.342],["LPS gzh",9.6,828.0,120.0,68.0,0.334],["PS gzh",9.8,823.0,118.0,72.0,0.342],["T-46M gzh",9.4,800.0,122.0,59.0,0.289],["BT gzh",9.2,824.0,116.0,74.0,0.331],["BS gs",12.2,820.0,112.0,88.0,0.425],["FMJ",9.6,785.0,125.0,58.0,0.334],["SP BT",9.6,790.0,140.0,57.0,0.334],["HP BT",9.6,807.0,155.0,55.0,0.334]],"9x18mm": [["PM BZhT gzh",5.7,325.0,46.0,38.0,0.067],["PM P gzh",6.1,302.0,37.0,17.0,0.101],["PM PBM gzh",3.55,480.0,45.0,43.0,0.061],["PMM PstM gzh",5.7,420.0,60.0,50.0,0.096],["PM PPe gzh",7.8,297.0,60.0,15.0,0.092],["PM PPT gzh",7.8,301.0,37.0,18.0,0.104],["PM PRS gs",6.1,301.0,36.0,7.0,0.101],["PM PS gs PPO",6.3,330.0,51.0,20.0,0.104],["PM PSO gzh",6.0,315.0,38.0,19.0,0.099],["PM Pst gzh",6.0,298.0,39.0,28.0,0.097],["PM PSV",7.5,280.0,47.0,15.0,0.124],["PM RG028 gzh",6.0,325.0,50.0,34.0,0.106],["PM SP7 gzh",6.0,420.0,65.0,19.0,0.069],["PM SP8 gzh",5.0,250.0,50.0,12.0,0.083]],"9x19mm": [["Pst gzh",5.2,460.0,48.0,52.0,0.068],["PSO gzh",7.46,340.0,45.0,23.0,0.131],["Luger CCI",5.18,457.0,65.0,25.0,0.131],["RIP",5.96,385.0,63.0,34.0,0.075],["Green Tracer",6.0,365.0,44.0,21.0,0.105],["AP 6.3",5.18,450.0,52.0,59.0,0.121],["PBP gzh",4.1,550.0,45.0,64.0,0.051],["QuakeMaker",11.99,304.0,68.0,20.0,0.15],["FMJ M882",7.26,385.0,55.0,39.0,0.068]],"9x21mm": [["PS gzh",6.7,420.0,55.0,52.0,0.084],["P gzh",7.5,400.0,60.0,44.0,0.138],["PE gzh",6.7,415.0,70.0,39.0,0.117],["BT gzh",7.3,400.0,52.0,56.0,0.084],["7N42 Zubilo",6.7,400.0,58.0,60.0,0.156],["7U4",6.7,300.0,50.0,47.0,0.117]],"9x39mm": [["SP-5 gs",16.8,308.0,80.0,50.0,0.353],["SP-6 gs",15.6,315.0,73.0,62.0,0.414],["SPP gs",16.0,295.0,70.0,64.0,0.189],["BP gs",15.6,310.0,68.0,66.0,0.395],["PAB-9 gs",17.3,310.0,65.0,58.0,0.395],["FMJ",15.5,330.0,85.0,40.0,0.343]]}}

# --------------------------------------------------------------------------
# BARREL_MODEL -- fitted from Realism BarrelTemplates.json (178 barrels)
# joined to items_master.json for length and calibre.
#
#   std_mm      barrel length at which Realism writes Velocity = 0, i.e. the
#               reference length the mod treats as "standard" for the calibre
#   vel_per_mm  Velocity units gained per mm of barrel past std_mm
#   heat/cool/burn  [slope, intercept] against (length / std_mm); omitted
#               where the relationship did not clear R2 >= 0.25, in which
#               case the pooled fallback below is used
#
# NOTE ON CoolFactor: in both the base game and Realism, a SHORTER barrel
# gets a HIGHER CoolFactor (base-game slope -0.302, R2 0.64; Realism -0.174).
# The field behaves as a multiplier on cooling TIME, not a cooling rate --
# higher is slower cooling, i.e. worse. Realism CoolFactor correlates 0.83
# with the base-game value on the same barrel.
# --------------------------------------------------------------------------
BARREL_MODEL = {
    "9x19mm": {"std_mm": 281.4, "vel_per_mm": 0.0736, "heat": [-0.2082, 1.1823], "cool": [-0.1755, 1.2092], "n": 34},
    "12g": {"std_mm": 633.9, "vel_per_mm": 0.0473, "heat": [-0.2317, 1.0954], "cool": [-0.2222, 1.1255], "n": 33},
    "7.62x51mm": {"std_mm": 524.7, "vel_per_mm": 0.0559, "heat": [-0.2352, 1.1246], "cool": [-0.1817, 1.1108], "n": 30},
    "5.56x45mm": {"std_mm": 439.8, "vel_per_mm": 0.1005, "heat": [-0.2128, 1.1901], "cool": [-0.1393, 1.1282], "burn": [-0.3641, 1.315], "n": 22},
    ".45 ACP": {"std_mm": 212.9, "vel_per_mm": 0.0975, "heat": [-0.2284, 1.2339], "cool": [-0.302, 1.3262], "n": 12},
    "7.62x54mm R": {"std_mm": 596.1, "vel_per_mm": 0.0871, "n": 9},
    "7.62x39mm": {"std_mm": 482.0, "vel_per_mm": 0.0578, "heat": [-0.137, 1.0874], "cool": [-0.1953, 1.1701], "burn": [-0.4648, 1.4576], "n": 8},
    ".338 Lapua Magnum": {"std_mm": 642.5, "vel_per_mm": 0.0776, "burn": [-0.353, 1.3691], "n": 5},
    ".50 AE": {"std_mm": 153.4, "vel_per_mm": 0.2267, "n": 4},
    "5.7x28mm": {"std_mm": 277.1, "vel_per_mm": 0.0786, "heat": [-0.2019, 1.1984], "cool": [-0.2194, 1.2679], "n": 4},
    ".300": {"std_mm": 244.2, "vel_per_mm": 0.0825, "heat": [-0.0611, 1.0915], "cool": [-0.0928, 1.1387], "burn": [-0.2021, 1.1905], "n": 4},
    "7.62x25mm": {"std_mm": 116.0, "vel_per_mm": 0.0523, "heat": [-0.1137, 1.2337], "cool": [-0.1137, 1.2937], "n": 4},
}

# Used when a calibre has no fitted relationship of its own.
BARREL_POOLED = {"heat": [-0.18, 1.13], "cool": [-0.174, 1.157], "burn": [-0.099, 1.083]}


# Profile multipliers applied on top of the length model. Barrel contour is not
# in the game data at all, so these encode the physical reasoning rather than a
# fit:
#   more steel -> more thermal mass -> slower to heat, and (in EFT's sense) a
#                 LOWER CoolFactor, since CoolFactor is cooling TIME
#   fluting    -> removes mass but adds surface area, so it heats a little
#                 faster while shedding heat much better
# heat/cool/burn are multipliers on the length-model output.
BARREL_PROFILES = {
    "pencil":       {"heat": 1.12, "cool": 1.10, "burn": 1.08, "note": "thin and light, heats fast"},
    "standard":     {"heat": 1.00, "cool": 1.00, "burn": 1.00, "note": "government / factory contour"},
    "match":        {"heat": 0.96, "cool": 0.98, "burn": 0.95, "note": "tighter bore, a little more mass"},
    "heavy":        {"heat": 0.82, "cool": 0.95, "burn": 0.90, "note": "major thermal mass, slow to heat"},
    "bull":         {"heat": 0.74, "cool": 0.93, "burn": 0.86, "note": "maximum mass, minimum whip"},
    "fluted":       {"heat": 1.05, "cool": 0.80, "burn": 1.00, "note": "less mass, much more surface area"},
    "heavy fluted": {"heat": 0.88, "cool": 0.78, "burn": 0.90, "note": "heavy contour with flutes cut"},
}
BARREL_PROFILE_ORDER = ["pencil", "standard", "match", "heavy", "bull",
                        "fluted", "heavy fluted"]

_BARREL_PROFILE_HINTS = [
    ("heavy_fluted", "heavy fluted"), ("heavy fluted", "heavy fluted"),
    ("fluted", "fluted"), ("heavy", "heavy"), ("bull", "bull"),
    ("national_match", "match"), ("match", "match"), ("pencil", "pencil"),
    ("lightweight", "pencil"), ("std", "standard"),
]


def barrel_length_mm(name: str):
    """Barrel length from the item name; mm first, then inches."""
    src = name or ""
    m = re.search(r"(\d{2,4})\s*mm", src, re.I)
    if m:
        v = float(m.group(1))
        if 50.0 <= v <= 1200.0:
            return v
    m = re.search(r"(\d{1,2}(?:\.\d+)?)\s*(?:inch|in\b|\")", src, re.I)
    if m:
        v = float(m.group(1)) * 25.4
        if 50.0 <= v <= 1200.0:
            return v
    return None


def barrel_profile_hint(name: str) -> str:
    n = (name or "").lower()
    for frag, prof in _BARREL_PROFILE_HINTS:
        if frag in n:
            return prof
    return "standard"


def calc_barrel_stats(calibre: str, length_mm: float, profile: str = "standard") -> dict:
    """Realism barrel stats from calibre + length + contour.

    Velocity is exact rather than fitted noise: Realism's Velocity is a straight
    line in barrel length within a calibre (R2 0.79-0.99 across the twelve
    calibres with enough barrels), so it is reproduced as
    slope * (length - standard_length), rounded to the integer the mod writes.

    HeatFactor / CoolFactor / DurabilityBurnModificator use the same
    relative-length model, then take the contour multiplier.

    Weight is deliberately NOT produced -- it is copied 1:1 from the base mod.
    """
    m = BARREL_MODEL.get(calibre)
    if not m or not length_mm:
        return {}
    prof = BARREL_PROFILES.get(profile, BARREL_PROFILES["standard"])
    std = m["std_mm"]
    ratio = (length_mm / std) if std else 1.0

    def _rel(key):
        sl, ic = m.get(key, BARREL_POOLED[key])
        return sl * ratio + ic

    return {
        "Velocity": int(round(m["vel_per_mm"] * (length_mm - std))),
        "HeatFactor": round(max(0.1, _rel("heat") * prof["heat"]), 3),
        "CoolFactor": round(max(0.1, _rel("cool") * prof["cool"]), 3),
        "DurabilityBurnModificator": round(max(0.1, _rel("burn") * prof["burn"]), 3),
    }


def barrel_reference(calibre: str):
    """Standard length and velocity slope for the calibre, for the readout."""
    m = BARREL_MODEL.get(calibre)
    if not m:
        return None
    return {"std_mm": m["std_mm"], "std_in": round(m["std_mm"] / 25.4, 1),
            "vel_per_mm": m["vel_per_mm"], "n": m["n"]}


# ---------------------------------------------------------------------------
# Stock model.
#
# The three booleans are overwhelmingly one value in Realism's own 244 stocks,
# and where they are not, ModType says so:
#   HasShoulderContact  True  184 / False 60. Every ModType that is a stock
#                       proper (Stock/StockR/StockN/buffer_stock) is almost
#                       always True; the False cases are adapters and buffers
#                       (buffer 10/10 False, buffer_adapter 13/15, stock_adapter
#                       7/10). So: default True, and copy the clone's ModType
#                       when it says adapter/buffer.
#   BlocksFolding       False 231 / True 13  (95% -- edge case, default False)
#   StockAllowADS       False 235 / True   9  (96% -- edge case, default False)
#
# The archetype nudges below come from the same file, grouping by name:
#                        light    precision
#   AimSpeed             +2.33      -0.94
#   Ergonomics           +1.44      +6.88
#   HorizontalRecoil     -0.90      -6.14
#   Dispersion           -0.42      -5.86
#   CameraRecoil         +1.96      -4.90
# i.e. a skeleton/wire/PDW stock gets on target faster but damps almost nothing,
# and a marksman/precision stock is the reverse -- which is what they do.
# ---------------------------------------------------------------------------
STOCK_NO_SHOULDER_MODTYPES = {
    "buffer", "buffer_adapter", "stock_adapter", "hydraulic_buffer", "stockf",
}

STOCK_ARCHETYPES = {
    "light":     {"AimSpeed": 2.3, "Ergonomics": 1.4, "VerticalRecoil": -2.0,
                  "HorizontalRecoil": -0.9, "Dispersion": -0.4, "CameraRecoil": 2.0,
                  "Accuracy": 1.0,
                  "note": "skeleton / wire / PDW -- fast to shoulder, damps little"},
    "standard":  {"AimSpeed": 1.1, "Ergonomics": 6.8, "VerticalRecoil": -2.3,
                  "HorizontalRecoil": -6.5, "Dispersion": -3.2, "CameraRecoil": -3.8,
                  "Accuracy": 2.3, "note": "ordinary fixed or collapsible stock"},
    "precision": {"AimSpeed": -0.9, "Ergonomics": 6.9, "VerticalRecoil": -2.6,
                  "HorizontalRecoil": -6.1, "Dispersion": -5.9, "CameraRecoil": -4.9,
                  "Accuracy": 2.2,
                  "note": "marksman / chassis -- slow to swing, damps hard"},
    "adapter":   {"AimSpeed": 0.0, "Ergonomics": 0.0, "VerticalRecoil": 0.0,
                  "HorizontalRecoil": 0.0, "Dispersion": 0.0, "CameraRecoil": 0.0,
                  "Accuracy": 0.0, "note": "buffer tube or adapter -- no contact"},
}
STOCK_ARCHETYPE_ORDER = ["light", "standard", "precision", "adapter"]

_STOCK_LIGHT_HINTS = ("skeleton", "wire", "minimalist", "pdw", "brace", "stubby",
                      "light", "tube", "collaps")
_STOCK_PRECISION_HINTS = ("marksman", "precision", "match", "sniper", "target",
                          "chassis", "prs", "cheek", "a5", "adjustable")
_STOCK_ADAPTER_HINTS = ("adapter", "buffer")


def stock_archetype_hint(name: str, mod_type: str = "") -> str:
    mt = (mod_type or "").strip().lower()
    if mt in STOCK_NO_SHOULDER_MODTYPES:
        return "adapter"
    n = (name or "").lower()
    if any(k in n for k in _STOCK_ADAPTER_HINTS) and not any(
            k in n for k in ("stock_adapter_stock",)):
        return "adapter"
    if any(k in n for k in _STOCK_PRECISION_HINTS):
        return "precision"
    if any(k in n for k in _STOCK_LIGHT_HINTS):
        return "light"
    return "standard"


def calc_stock_stats(name: str, archetype: str = "", mod_type: str = "",
                     clone_mod_type: str = "") -> dict:
    """Realism stock stats from archetype plus the three boolean defaults.

    ModType is taken from the Realism clone when it has one, because that is
    what decides whether the item is a stock at all or a buffer/adapter.
    """
    mt = (clone_mod_type or mod_type or "").strip()
    arch = archetype or stock_archetype_hint(name, mt)
    prof = STOCK_ARCHETYPES.get(arch, STOCK_ARCHETYPES["standard"])

    out = {k: v for k, v in prof.items() if k != "note"}
    out["HasShoulderContact"] = (arch != "adapter"
                                 and mt.lower() not in STOCK_NO_SHOULDER_MODTYPES)
    out["BlocksFolding"] = False     # 231/244 -- edge case, set by hand
    out["StockAllowADS"] = False     # 235/244 -- edge case, set by hand
    if mt:
        out["ModType"] = mt
    return out


# --------------------------------------------------------------------------
# Magazine model -- fitted from Realism MagazineTemplates.json (213 mags)
# joined to items_master.json for capacity and ExtraSizeDown.
#
# Capacity on its own explains nothing (r = +0.000 against ReloadSpeed).
# What actually orders these values is the physical SIZE CLASS, which the
# game already stores as ExtraSizeDown -- how far the magazine hangs below
# the receiver:
#     0 = flush-fit / short      91 mags
#     1 = standard double-stack 111 mags
#     2 = extended               11 mags
# Group means are monotonic across every target:
#     ReloadSpeed        -0.66  -1.99  -4.91
#     CheckTimeModifier  -5.56  -1.49 +11.82
#     LoadUnloadModifier -3.94  +2.88  +4.55
#     Ergonomics         -0.13  -0.88  -5.32
# Capacity then matters WITHIN a size class (r = -0.545 for ReloadSpeed
# among standard mags), so each class carries its own log-capacity slope.
#
# MalfunctionChance is the exception: it tracks absolute capacity directly,
# 25x from the smallest band to the largest --
#     cap  0-15  0.029 | 16-25  0.112 | 26-40  0.276 | 41-60  0.710 | 61+  0.733
# which is the real-world result that big and drum magazines are the
# unreliable ones.
# --------------------------------------------------------------------------
MAG_SIZE_CLASSES = {
    0: {"name": "flush", "ref_capacity": 10, "n": 81,
        "ReloadSpeed": [-0.355, 0.266], "CheckTimeModifier": [-3.051, 2.058], "LoadUnloadModifier": [6.915, -19.437], "Ergonomics": [-0.05, -0.016]},
    1: {"name": "standard", "ref_capacity": 30, "n": 96,
        "ReloadSpeed": [0.089, -0.655], "CheckTimeModifier": [0.333, -5.839], "LoadUnloadModifier": [6.845, -24.19], "Ergonomics": [-0.318, 0.796]},
    2: {"name": "extended", "ref_capacity": 40, "n": 8,
        "ReloadSpeed": [5.813, -24.77], "CheckTimeModifier": [7.997, -16.072], "LoadUnloadModifier": [1.226, -1.88], "Ergonomics": [0.509, -3.883]},
}

# MalfunctionChance by absolute capacity: [max_capacity, value].
MAG_MALF_BANDS = [
    [15, 0.029],   # n=75
    [25, 0.112],   # n=46
    [40, 0.276],   # n=57
    [60, 0.71],   # n=15
    [999, 0.733],   # n=19
]

# Extras that the size class does not capture.
MAG_FEATURE_MODIFIERS = {
    # 9 drums, mean MalfunctionChance 1.146 against 0.225 overall
    "drum":     {"MalfunctionChance": 0.95, "ReloadSpeed": -3.0, "Ergonomics": -4.0},
    # windowed / cutout bodies: CheckTimeModifier -35.0 against -2.2
    "windowed": {"CheckTimeModifier": -32.8},
    "shot_tube": {"LoadUnloadModifier": 0.0, "ReloadSpeed": 0.0},
}


MAG_SIZE_ORDER = ["flush", "standard", "extended"]
_MAG_SIZE_BY_NAME = {v["name"]: k for k, v in MAG_SIZE_CLASSES.items()}

# ModTypes Realism actually uses on magazines.
MAG_MOD_TYPES = ["", "long_mag", "shotTube"]

_MAG_WINDOW_HINTS = ("window", "cutout", "clear", "translucent", "viewport")
_MAG_DRUM_HINTS = ("drum", "helical", "beta", "x-15", "snail")


def magazine_capacity(name: str, props: dict = None) -> int:
    """Capacity from _props.Cartridges, falling back to a count in the name."""
    if isinstance(props, dict):
        carts = props.get("Cartridges") or []
        if carts and isinstance(carts[0], dict):
            c = carts[0].get("_max_count")
            if isinstance(c, int) and c > 0:
                return c
    m = re.search(r"(\d{1,3})\s*(?:rnd|round|rd)\b", (name or ""), re.I)
    if m:
        v = int(m.group(1))
        if 1 <= v <= 200:
            return v
    return 0


def magazine_size_class(props: dict = None, name: str = "") -> str:
    """flush / standard / extended, from ExtraSizeDown.

    ExtraSizeDown is how far the magazine hangs below the receiver, which is
    exactly the physical distinction that orders Realism's values.
    """
    esd = None
    if isinstance(props, dict):
        v = props.get("ExtraSizeDown")
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            esd = int(v)
    if esd is None:
        return "standard"
    return MAG_SIZE_CLASSES.get(min(max(esd, 0), 2), MAG_SIZE_CLASSES[1])["name"]


def magazine_is_windowed(name: str) -> bool:
    n = (name or "").lower()
    return any(k in n for k in _MAG_WINDOW_HINTS)


def magazine_is_drum(name: str, capacity: int = 0) -> bool:
    n = (name or "").lower()
    return any(k in n for k in _MAG_DRUM_HINTS) or capacity >= 60


def calc_magazine_stats(capacity: int, size_class: str = "standard",
                        drum: bool = False, windowed: bool = False,
                        mod_type: str = "", is_family_default: bool = False) -> dict:
    """Realism magazine stats from size class + capacity + body features.

    The baseline is a zero across the board: that is the weapon's own default
    magazine, and everything here is a delta away from it. Pass
    is_family_default=True for the weapon's standard magazine and you get zeros.

    HONEST HEALTH WARNING. Measured against Realism's own 213 magazines this
    model beats writing a plain zero only on ReloadSpeed (3.16 vs 3.30) and
    Ergonomics (0.76 vs 0.79), and it is clearly WORSE than the ML formula on
    CheckTimeModifier (8.3 vs 2.6) and LoadUnloadModifier (9.1 vs 0.4). The
    group structure is real -- the size-class means are cleanly monotonic and
    the malfunction bands span 25x -- but within a class the spread is dominated
    by per-weapon authoring choices that no physical quantity predicts.

    So treat this as a STARTING POINT for a magazine that has no template yet,
    not as a replacement for the fitted formulas. The size class and malfunction
    band are the parts worth trusting.
    """
    if not capacity:
        return {}
    if is_family_default and not drum and not windowed and size_class == "standard":
        # The weapon's own default magazine is the zero point by definition.
        out = {k: 0.0 for k in ("ReloadSpeed", "CheckTimeModifier",
                                "LoadUnloadModifier", "Ergonomics",
                                "MalfunctionChance")}
        if mod_type:
            out["ModType"] = mod_type
        return out
    idx = _MAG_SIZE_BY_NAME.get(size_class, 1)
    cls = MAG_SIZE_CLASSES[idx]
    lc = math.log(max(capacity, 1))

    out = {}
    for tgt in ("ReloadSpeed", "CheckTimeModifier", "LoadUnloadModifier", "Ergonomics"):
        slope, icept = cls[tgt]
        out[tgt] = slope * lc + icept

    malf = MAG_MALF_BANDS[-1][1]
    for cap_max, val in MAG_MALF_BANDS:
        if capacity <= cap_max:
            malf = val
            break
    out["MalfunctionChance"] = malf

    if drum:
        for k, v in MAG_FEATURE_MODIFIERS["drum"].items():
            out[k] = out.get(k, 0.0) + v
    if windowed:
        for k, v in MAG_FEATURE_MODIFIERS["windowed"].items():
            out[k] = out.get(k, 0.0) + v

    out = {k: round(v, 2) for k, v in out.items()}
    if mod_type:
        out["ModType"] = mod_type
    return out


# ---------------------------------------------------------------------------
# Charging handle model.
#
# ChamberSpeed on a charging handle is a PERCENTAGE increase over the weapon's
# base chambering speed, so the milspec handle a rifle ships with is 0 by
# definition and everything else is measured against it. Crucially the scale is
# absolute, not family-relative: an SR-25 KAC std handle is +26 and a SIG Spear
# std is +30, because those designs are simply better than an AR-15 T-handle,
# which is the 0 point.
#
# Fitted across Realism's 35 charging handles the tiers are near-perfectly
# separated, with no milspec handle carrying a non-zero value:
#     legacy    n= 2  median  -5.0   range [-5, -5]
#     milspec   n=11  median   0.0   range [ 0,  0]
#     extended  n= 8  median  22.5   range [18, 27]
#     ambi      n=14  median  32.8   range [24, 38]
#
# Tier median MAE 1.81, against 18.47 for writing a plain 0 and 11.37 for the
# fitted ML formula -- the taxonomy beats the regression by 6x here.
# ---------------------------------------------------------------------------
CHARGING_HANDLE_TIERS = {
    "legacy":   {"ChamberSpeed": -5.0,
                 "note": "awkward reciprocating design (MP5, P90) -- slower than baseline"},
    "milspec":  {"ChamberSpeed": 0.0,
                 "note": "the handle the weapon ships with -- the 0 point"},
    "extended": {"ChamberSpeed": 22.5,
                 "note": "extended or tactical latch, still single-sided"},
    "ambi":     {"ChamberSpeed": 32.8,
                 "note": "ambidextrous / oversized / gas-buster -- fastest to run"},
}
CHARGING_HANDLE_TIER_ORDER = ["legacy", "milspec", "extended", "ambi"]

_CH_TIER_HINTS = [
    ("ambi", ("ambi", "raptor", "grip_n_rip", "avalanche", "geissele_ach",
              "geissele_sch", "double_latch", "masp", "mod2", "knurled",
              "zenit_rp1", "css", "cmmg_mid", "spear")),
    ("extended", ("extended", "tactical_latch", "badger", "handler", "a3_handle",
                  "single_latch", "kac_charging_handle", "mcx")),
    ("legacy", ("mp5_hk_mp5_std", "p90_fn_p90_std")),
]


def charging_handle_tier(name: str) -> str:
    n = (name or "").lower()
    for tier, keys in _CH_TIER_HINTS:
        if any(k in n for k in keys):
            return tier
    return "milspec"


def calc_charging_handle_stats(name: str = "", tier: str = "") -> dict:
    """ChamberSpeed for a charging handle, as a percentage over the base handle."""
    t = tier or charging_handle_tier(name)
    prof = CHARGING_HANDLE_TIERS.get(t, CHARGING_HANDLE_TIERS["milspec"])
    return {"ChamberSpeed": prof["ChamberSpeed"]}


AMMO_CONSTRUCTION = ["FMJ", "AP", "HP/SP"]

def sectional_density(mass_g: float, diameter_mm: float) -> float:
    """kg per cm^2 of frontal area."""
    if not diameter_mm: return 0.0
    area_cm2 = math.pi * (diameter_mm / 2.0 / 10.0) ** 2
    return (mass_g / 1000.0) / area_cm2 if area_cm2 else 0.0

def calc_ammo_stats(calibre: str, construction: str, mass_g: float, velocity: float,
                    diameter_mm: float = None) -> dict:
    """Derive ammo stats from physical inputs. Returns {} if inputs are unusable."""
    if not mass_g or not velocity: return {}
    if diameter_mm is None:
        diameter_mm = AMMO_MODEL["diameter"].get(calibre, 0.0)
    if not diameter_mm: return {}

    k = construction if construction in AMMO_MODEL["damage"] else "FMJ"
    momentum = mass_g * velocity / 1000.0
    sd = sectional_density(mass_g, diameter_mm)

    da, db = AMMO_MODEL["damage"][k]
    pa, pb, pc = AMMO_MODEL["pen"][k]
    ba, bb = AMMO_MODEL["bc"]

    return {
        "Damage": max(1.0, da + db * momentum),
        "PenetrationPower": max(0.0, pa + pb * velocity + pc * sd),
        "BallisticCoeficient": max(0.009, ba + bb * sd),
        "BulletMassGram": float(mass_g),
        "BulletDiameterMilimeters": float(diameter_mm),
        "InitialSpeed": float(velocity),
    }

def ammo_reference(calibre: str):
    """Realism's own rounds for this calibre: [name, mass, v, dmg, pen, bc]."""
    return AMMO_MODEL["reference"].get(calibre, [])


# Valid fields that should NOT be auto-populated by a formula. They apply to a
# small, specific set of items, so a predicted value on everything else is just
# noise. Still selectable from "+ Add Field" when you actually need them.
ADD_ONLY_FIELDS = {
    "WeaponMod": {"ModShotDispersion"},   # buckshot spread -- shotgun mods only
}

def add_only_for(bucket: str) -> set:
    return ADD_ONLY_FIELDS.get(bucket, set())


# Fields that are valid for a specific mod category but are not guaranteed to be
# produced by a formula (the emitter drops a target when its fit scores worse
# than writing nothing, and Realism itself only sets many of these on some
# items). Without this, "+ Add Field" could not offer Velocity on a barrel even
# though barrels are the main thing that changes muzzle velocity.
CATEGORY_ADD_FIELDS = {
    "Barrel": {
        "Velocity", "Loudness", "CenterOfImpact", "Convergence", "Dispersion",
        "VerticalRecoil", "HorizontalRecoil", "CameraRecoil", "RecoilAngle",
        "Ergonomics", "Accuracy", "ModMalfunctionChance", "DurabilityBurnModificator",
        "HeatFactor", "CoolFactor", "Weight", "AutoROF", "SemiROF", "Flash",
        "AimSpeed", "ChamberSpeed", "HasShoulderContact",
    },
    "Suppressors": {
        "Loudness", "Flash", "Velocity", "Dispersion", "Convergence",
        "VerticalRecoil", "HorizontalRecoil", "CameraRecoil", "RecoilAngle",
        "Ergonomics", "Accuracy", "ModMalfunctionChance", "DurabilityBurnModificator",
        "HeatFactor", "CoolFactor", "Weight", "AutoROF", "SemiROF", "CanCycleSubs",
    },
    "MuzzleBrakes": {
        "Loudness", "Flash", "Velocity", "Dispersion", "Convergence",
        "VerticalRecoil", "HorizontalRecoil", "CameraRecoil", "RecoilAngle",
        "Ergonomics", "Accuracy", "ModMalfunctionChance", "DurabilityBurnModificator",
        "HeatFactor", "CoolFactor", "Weight",
    },
    "Stock": {
        "VerticalRecoil", "HorizontalRecoil", "CameraRecoil", "Dispersion",
        "RecoilAngle", "Ergonomics", "Accuracy", "AimSpeed", "Weight",
        "BlocksFolding", "StockAllowADS", "HasShoulderContact",
    },
    "Handguard": {
        "VerticalRecoil", "HorizontalRecoil", "Dispersion", "Ergonomics",
        "Accuracy", "AimSpeed", "ChamberSpeed", "HeatFactor", "CoolFactor", "Weight",
    },
    "Gasblock": {
        "VerticalRecoil", "HorizontalRecoil", "Dispersion", "AutoROF", "SemiROF",
        "Ergonomics", "Accuracy", "Convergence", "Flash", "ModMalfunctionChance",
        "DurabilityBurnModificator", "HeatFactor", "CoolFactor", "Weight",
    },
    "Receiver": {
        "Accuracy", "Ergonomics", "ModMalfunctionChance", "DurabilityBurnModificator",
        "HeatFactor", "CoolFactor", "Weight", "Dispersion", "VerticalRecoil",
    },
    "Magazines": {
        "Ergonomics", "ReloadSpeed", "MalfunctionChance", "CheckTimeModifier",
        "LoadUnloadModifier", "Weight", "ModType",
    },
    "Sights": {"Ergonomics", "Accuracy", "AimSpeed", "Weight"},
    "PistolGrip": {
        "Ergonomics", "Accuracy", "Dispersion", "VerticalRecoil",
        "HorizontalRecoil", "AimSpeed", "Weight",
    },
    "Foregrip": {
        "Ergonomics", "Accuracy", "Dispersion", "VerticalRecoil",
        "HorizontalRecoil", "AimSpeed", "Weight",
    },
}
# Aliases so the alternate class spellings resolve to the same set.
for _a, _b in (("Barrels", "Barrel"), ("Stocks", "Stock"),
               ("StocksChassis", "Stock"), ("Handguards", "Handguard"),
               ("FlashHiders", "MuzzleBrakes"), ("MuzzleAdapters", "MuzzleBrakes"),
               ("Compensators", "MuzzleBrakes"), ("MuzzleCombos", "MuzzleBrakes"),
               ("Muzzle", "MuzzleBrakes"), ("Magazine", "Magazines")):
    CATEGORY_ADD_FIELDS.setdefault(_a, CATEGORY_ADD_FIELDS[_b])


def category_add_fields(category: str) -> set:
    return set(CATEGORY_ADD_FIELDS.get((category or "").strip(), set()))

def strip_add_only(d: dict, bucket: str) -> dict:
    """Drop auto-populated values for fields that should be opt-in."""
    if not isinstance(d, dict): return d
    drop = add_only_for(bucket)
    return {k: v for k, v in d.items() if k not in drop} if drop else d

def readable_fields(bucket: str) -> set:
    """Everything the server will do something with, by either route."""
    return (_APPLIED_BY_PLUGIN.get(bucket, set())
            | _APPLIED_BY_PROPS.get(bucket, set())
            | STRUCTURAL_FIELDS)

def field_status(bucket: str, key: str) -> str:
    """'ok', 'structural', 'inert' or 'unknown' -- the only validity question."""
    if key in STRUCTURAL_FIELDS: return "structural"
    if key in readable_fields(bucket): return "ok"
    if key in INERT_KNOWN_FIELDS: return "inert"
    return "unknown"

def field_applied_by(bucket: str, key: str) -> str:
    """Reference only: where the value ends up once the server has it."""
    a = key in _APPLIED_BY_PLUGIN.get(bucket, set())
    b = key in _APPLIED_BY_PROPS.get(bucket, set())
    if a and b: return "forwarded to the plugin and written into _props"
    if a: return "forwarded to the RealismMod plugin"
    if b: return "written into the item's _props"
    return ""

def unreadable_fields(compat: dict, bucket: str) -> list:
    """Keys that would be exported but never read back by the game."""
    if not isinstance(compat, dict): return []
    return sorted(k for k in compat
                  if not str(k).startswith("_")
                  and field_status(bucket, k) == "unknown")

# Real value ranges taken verbatim from the base-game ammo dump
# (ammo_v2.json "info"). All 19 fields, not the 8 that were listed before --
# the missing ones meant a bad ProjectileCount or FragmentationChance sailed
# through export validation unremarked. These sanity-check an export; they do
# NOT clamp your input, since a custom cartridge may legitimately sit outside
# whatever the base game happens to span.
AMMO_VALUE_RANGES = {
    "PenetrationPower": (0, 115),
    "ArmorDamage": (0, 95),
    "ProjectileCount": (1, 20),
    "Damage": (1, 350),
    "InitialSpeed": (80, 1013),
    "BallisticCoeficient": (0.009, 1),
    "RicochetChance": (0, 1),
    "FragmentationChance": (0, 0.6),
    "BulletMassGram": (0, 80),
    "HeavyBleedingDelta": (0, 1),
    "LightBleedingDelta": (0, 1),
    "ammoAccr": (-130, 100),
    "ammoHear": (0, 1),
    "ammoRec": (-25, 115),
    "MalfMisfireChance": (0, 1.4),
    "MisfireChance": (0, 0.01),
    "MalfFeedChance": (0, 0.01),
    "DurabilityBurnModificator": (1, 6),
    "HeatFactor": (1, 2.975),
}

def out_of_range_fields(compat: dict, bucket: str) -> list:
    if bucket != "Ammo" or not isinstance(compat, dict): return []
    out = []
    for k, (lo, hi) in AMMO_VALUE_RANGES.items():
        v = compat.get(k)
        if isinstance(v, (int, float)) and not isinstance(v, bool) and not (lo <= v <= hi):
            out.append(f"{k}={v} (dump spans {lo}-{hi})")
    return out


# ---------------------------------------------------------------------------
# Ammunition calculator.
#
# Derived from the hand-written "item" block of ammo_v2.json (186 cartridges).
# Two axes, because that is what the data actually supports:
#
#   calibre/casing  -> baseline profile (median of that calibre's FMJ loads)
#   construction    -> multipliers off that baseline
#
# then bullet mass and muzzle velocity scale the physics-driven fields via the
# kinetic-energy ratio against the baseline load, using the same KE expression
# BallisticController uses:  KE = 0.5 * mass_g * velocity^2 / 1000
#
# Variance explained by calibre x construction on the source data:
#   Damage 0.96 | BallisticCoeficient 0.94 | HeatFactor 0.91
#   PenetrationPower 0.90 | DurabilityBurnModificator 0.70
#   ammoRec 0.56 | ammoAccr 0.49
# The last two are weak -- they are largely taste, not physics. The calculator
# emits them as the calibre baseline and they are worth setting by hand.
# ---------------------------------------------------------------------------
AMMO_CALIBRE_PROFILES = {
    '.300': dict(dia=7.82, mass=9.4, vel=580.5, pen=51.0, dmg=74.5, bc=0.334, burn=1.35, heat=1.07, rec=4.0, accr=5.0, n=4),
    '.338 Lapua Magnum': dict(dia=8.58, mass=16.2, vel=860.0, pen=75.0, dmg=195.0, bc=0.48, burn=1.25, heat=1.0, rec=5.0, accr=12.0, n=3),
    '.357 Magnum': dict(dia=9.07, mass=10.225, vel=405.0, pen=44.5, dmg=107.5, bc=0.159, burn=1.25, heat=1.15, rec=12.5, accr=0.0, n=2),
    '.366 TKM': dict(dia=9.55, mass=13.0, vel=580.0, pen=54.0, dmg=110.0, bc=0.202, burn=1.0, heat=1.0, rec=0.0, accr=0.0, n=3),
    '.45 ACP': dict(dia=11.48, mass=14.9, vel=274.0, pen=24.0, dmg=58.0, bc=0.131, burn=1.5, heat=1.12, rec=0.0, accr=0.0, n=3),
    '.50 AE': dict(dia=12.7, mass=19.4, vel=440, pen=40.0, dmg=120.0, bc=0.131, burn=1.5, heat=1.25, rec=10.0, accr=0.0, n=3),
    '12.7x108mm': dict(dia=12.98, mass=48.3, vel=818.0, pen=85.0, dmg=350.0, bc=0.623, burn=1.0, heat=1.0, rec=0.0, accr=0.0, n=1),
    '12.7x55mm': dict(dia=12.95, mass=17.95, vel=570.0, pen=57.0, dmg=135.0, bc=0.151, burn=1.35, heat=1.0, rec=0.0, accr=-10.0, n=3),
    '12/70': dict(dia=18.5, mass=21.25, vel=402.5, pen=20.0, dmg=142.0, bc=0.1105, burn=1.7, heat=1.295, rec=12.0, accr=-30.0, n=6),
    '12/70 shot': dict(dia=18.5, mass=1.4, vel=357.5, pen=12.5, dmg=180.0, bc=0.0175, burn=1.2, heat=1.0, rec=-6.0, accr=-30.0, n=4),
    '12/70 single': dict(dia=18.5, mass=0.605, vel=357.5, pen=2.5, dmg=4.75, bc=0.0235, burn=1.0, heat=2.0958, rec=0.0, accr=-5.0, n=4),
    '20/70': dict(dia=15.6, mass=19.4, vel=445.5, pen=32.5, dmg=153.0, bc=0.032, burn=1.775, heat=1.27, rec=16.0, accr=15.0, n=4),
    '20/70 shot': dict(dia=15.6, mass=1.26, vel=410.0, pen=12.0, dmg=144.0, bc=0.034, burn=1.1, heat=1.0, rec=-10.0, accr=-10.0, n=5),
    '20/70 single': dict(dia=15.6, mass=2, vel=410, pen=3, dmg=2.75, bc=0.034, burn=1.3, heat=1.9295, rec=0, accr=0, n=5),
    '23x75mm': dict(dia=23.0, mass=50.0, vel=250.0, pen=30.0, dmg=165.5, bc=0.1485, burn=3.0, heat=1.29, rec=15.0, accr=0.0, n=2),
    '23x75mm shot': dict(dia=23.0, mass=3.38, vel=270, pen=22.0, dmg=240.0, bc=0.02, burn=1.0, heat=1.0, rec=0.0, accr=0.0, n=3),
    '23x75mm single': dict(dia=23.0, mass=3.38, vel=270, pen=10, dmg=9.75, bc=0.022, burn=1, heat=2.8, rec=0, accr=0, n=3),
    '4.40x46mm shot': dict(dia=4.4, mass=24.0, vel=269.0, pen=30.0, dmg=15.0, bc=0.013, burn=1, heat=1, rec=0, accr=90.0, n=1),
    '4.40x46mm single': dict(dia=4.4, mass=0.09, vel=269, pen=5, dmg=10.6667, bc=0.013, burn=1, heat=1, rec=0, accr=100, n=1),
    '4.6x30mm': dict(dia=4.65, mass=2.3, vel=655.0, pen=41.0, dmg=48.0, bc=0.2015, burn=1.05, heat=1.1, rec=2.5, accr=2.5, n=2),
    '5.45x39mm': dict(dia=5.6, mass=3.63, vel=881.5, pen=56.5, dmg=68.5, bc=0.253, burn=1.175, heat=1.05, rec=2.5, accr=12.5, n=6),
    '5.56x45mm': dict(dia=5.7, mass=4.0, vel=934.5, pen=60.5, dmg=73.5, bc=0.2605, burn=1.3, heat=1.055, rec=5.5, accr=0.5, n=8),
    '5.7x28mm': dict(dia=5.7, mass=2.4, vel=716.0, pen=48.0, dmg=45.0, bc=0.233, burn=1.2, heat=1.02, rec=5.0, accr=-6.0, n=7),
    '6.8x51mm': dict(dia=7.0, mass=8.75, vel=838.0, pen=70.0, dmg=130.0, bc=0.475, burn=3.0, heat=1.1, rec=5.0, accr=10.0, n=2),
    '7.62x25mm': dict(dia=7.85, mass=6.35, vel=427.0, pen=38.0, dmg=56.0, bc=0.126, burn=1.5, heat=1.0, rec=10.0, accr=0.0, n=5),
    '7.62x39mm': dict(dia=7.92, mass=7.9, vel=732.0, pen=60.0, dmg=86.0, bc=0.28, burn=1.4, heat=1.03, rec=8.0, accr=5.0, n=3),
    '7.62x51mm': dict(dia=7.82, mass=9.9, vel=841.0, pen=58.0, dmg=128.0, bc=0.355, burn=1.85, heat=1.1, rec=8.0, accr=-2.5, n=4),
    '7.62x54mm R': dict(dia=7.92, mass=9.6, vel=823.0, pen=68.0, dmg=120.0, bc=0.334, burn=1.5, heat=1.08, rec=8.0, accr=7.0, n=3),
    '9x18mm': dict(dia=9.27, mass=6.0, vel=315.0, pen=20.0, dmg=46.0, bc=0.099, burn=1.18, heat=1.08, rec=8.0, accr=-5.0, n=11),
    '9x19mm': dict(dia=9.02, mass=6.23, vel=421.0, pen=32.0, dmg=51.5, bc=0.0995, burn=1.7, heat=1.11, rec=10.0, accr=0.0, n=4),
    '9x21mm': dict(dia=9.02, mass=6.7, vel=400.0, pen=47.0, dmg=58.0, bc=0.117, burn=1.35, heat=1.05, rec=5.0, accr=0.0, n=5),
    '9x39mm': dict(dia=9.25, mass=16.0, vel=310.0, pen=58.0, dmg=70.0, bc=0.343, burn=2.5, heat=1.04, rec=9.0, accr=18.0, n=3),
}

# Multipliers against the calibre's FMJ baseline, medians from the source data.
AMMO_CONSTRUCTION = {
    "FMJ / Ball":  dict(pen=1.00, dmg=1.00, bc=1.00, burn=1.00, heat=1.00),
    "AP / Steel core": dict(pen=1.33, dmg=0.82, bc=1.05, burn=1.46, heat=1.11),
    "HP / SP (expanding)": dict(pen=0.92, dmg=1.18, bc=0.90, burn=1.28, heat=1.02),
    "Tracer":      dict(pen=0.97, dmg=0.98, bc=0.97, burn=0.90, heat=0.97),
    "Subsonic":    dict(pen=0.69, dmg=1.05, bc=1.00, burn=1.01, heat=0.96),
}

def ammo_kinetic_energy(mass_g: float, velocity_ms: float) -> float:
    """The exact expression BallisticController uses for armour interactions."""
    try:
        return 0.5 * float(mass_g) * float(velocity_ms) ** 2 / 1000.0
    except (TypeError, ValueError):
        return 0.0

def calculate_ammo(calibre: str, construction: str = "FMJ / Ball",
                   mass_g: float = None, velocity_ms: float = None,
                   diameter_mm: float = None) -> dict:
    """Predict a Realism ammo stat block. Returns {} for an unknown calibre."""
    prof = AMMO_CALIBRE_PROFILES.get(calibre)
    if not prof: return {}
    mult = AMMO_CONSTRUCTION.get(construction, AMMO_CONSTRUCTION["FMJ / Ball"])

    mass = float(mass_g) if mass_g else prof["mass"]
    vel = float(velocity_ms) if velocity_ms else prof["vel"]
    dia = float(diameter_mm) if diameter_mm else prof["dia"]

    ke = ammo_kinetic_energy(mass, vel)
    ke_base = ammo_kinetic_energy(prof["mass"], prof["vel"])
    ke_ratio = (ke / ke_base) if ke_base > 0 else 1.0

    # Penetration scales with sqrt(KE) and sectional density; damage tracks KE
    # more directly. Both are damped so an unusual load nudges rather than
    # dominates the calibre's hand-tuned baseline.
    sd = mass / (dia * dia) if dia else 0.0
    sd_base = prof["mass"] / (prof["dia"] ** 2) if prof["dia"] else 0.0
    sd_ratio = (sd / sd_base) if sd_base > 0 else 1.0

    pen = prof["pen"] * mult["pen"] * (max(ke_ratio, 0.01) ** 0.5) * (sd_ratio ** 0.25)
    dmg = prof["dmg"] * mult["dmg"] * (max(ke_ratio, 0.01) ** 0.7)
    bc = prof["bc"] * mult["bc"] * (sd_ratio ** 0.8)

    return {
        "PenetrationPower": round(min(max(pen, 0.0), 115.0), 1),
        "Damage": round(min(max(dmg, 1.0), 350.0), 1),
        "InitialSpeed": round(vel, 1),
        "BallisticCoeficient": round(min(max(bc, 0.009), 1.0), 3),
        "BulletMassGram": round(mass, 2),
        "BulletDiameterMilimeters": round(dia, 2),
        "DurabilityBurnModificator": round(prof["burn"] * mult["burn"], 2),
        "HeatFactor": round(prof["heat"] * mult["heat"], 2),
        "ammoAccr": round(prof["accr"], 1),
    }

# ---------------------------------------------------------------------------
# Ammo as a first-class formula category.
#
# formulas.py ships an EMPTY ammo_formula_map, so every ammo compat used to
# fall through to _fallback_merge and "Ammo" never appeared in the category
# dropdown. These built-ins fill that gap without needing a regenerated
# formulas.py; they use the same (item_entry, base_data, template, context)
# signature as the emitted functions so everything downstream is unchanged.
# ---------------------------------------------------------------------------
# EFT's Caliber prop spellings -> the calibre keys in AMMO_CALIBRE_PROFILES.
AMMO_CALIBER_ALIASES = {
    "Caliber556x45NATO": "5.56x45mm", "Caliber762x39": "7.62x39mm",
    "Caliber762x51": "7.62x51mm", "Caliber762x54R": "7.62x54mm R",
    "Caliber545x39": "5.45x39mm", "Caliber9x19PARA": "9x19mm",
    "Caliber9x18PM": "9x18mm", "Caliber9x18PMM": "9x18mm",
    "Caliber9x21": "9x21mm", "Caliber9x39": "9x39mm",
    "Caliber762x25TT": "7.62x25mm", "Caliber1143x23ACP": ".45 ACP",
    "Caliber57x28": "5.7x28mm", "Caliber46x30": "4.6x30mm",
    "Caliber86x70": ".338 Lapua Magnum", "Caliber127x55": "12.7x55mm",
    "Caliber127x108": "12.7x108mm", "Caliber366TKM": ".366 TKM",
    "Caliber12g": "12/70", "Caliber20g": "20/70", "Caliber23x75": "23x75mm",
    "Caliber40x46": "4.40x46mm single", "Caliber50AE": ".50 AE",
    "Caliber357": ".357 Magnum", "Caliber300Blackout": ".300",
    "Caliber300BLK": ".300", "Caliber68x51": "6.8x51mm",
}

def ammo_calibre_for_base(base: dict) -> str:
    """Best-guess calibre profile key for a base item."""
    if not isinstance(base, dict): return ""
    props = get_base_props_dict(base) or {}
    for src in (props, base):
        cal = src.get("Caliber") or src.get("ammoCaliber") or src.get("caliber")
        if isinstance(cal, str) and cal.strip():
            cal = cal.strip()
            if cal in AMMO_CALIBER_ALIASES: return AMMO_CALIBER_ALIASES[cal]
            if cal in AMMO_CALIBRE_PROFILES: return cal
    return ""

AMMO_CATEGORY = "Ammo"

def apply_ammo_formulas(item_entry, base_data=None, template=None, context=None):
    """The single Ammo formula. Which calibre profile to use comes from the
    ML Preset Override dropdown, handed in via context['calibre']."""
    entry = dict(item_entry or {})
    ctx = context if isinstance(context, dict) else {}
    props = get_base_props_dict(base_data or {}) or {}

    calibre = ctx.get("calibre") or ammo_calibre_for_base(base_data or {})
    if calibre not in AMMO_CALIBRE_PROFILES:
        return entry   # no profile picked yet -- leave the entry untouched

    def pick(*names):
        for src in (ctx, entry, props):
            for n in names:
                v = src.get(n)
                if isinstance(v, (int, float)) and not isinstance(v, bool) and v:
                    return float(v)
        return None

    calc = calculate_ammo(
        calibre,
        ctx.get("construction") or entry.get("_construction") or "FMJ / Ball",
        mass_g=pick("BulletMassGram", "bulletMassGram"),
        velocity_ms=pick("InitialSpeed", "initialSpeed"),
        diameter_mm=pick("BulletDiameterMilimeters", "bulletDiameterMilimeters"),
    )
    # Never clobber a value the author already set by hand.
    for k, v in calc.items():
        if entry.get(k) in (None, 0, 0.0, ""):
            entry[k] = v
        else:
            entry.setdefault(k, v)
    return entry

BUILTIN_AMMO_FORMULAS = {AMMO_CATEGORY: apply_ammo_formulas}

def ammo_formula_categories() -> list:
    return [AMMO_CATEGORY]

KNOWN_BOOLS = {
    "AllowADS", "StockAllowADS", "HasShoulderContact", "WeaponAllowADS", 
    "AllowOverheat", "IsManuallyOperated", "CanCycleSubs", 
    "ExaminedByDefault", "NoFiremodeOnBoltcatch", "IsAnimated", 
    "CompactHandling", "AllowFeed", "AllowJam", "AllowMisfire", 
    "AllowSlide", "BlockFolding", "BlocksFolding", "CanSpall", "BlocksMouth",
    "IsGasMask", "EnableBSGVisRecoil", "ReduceBSGVisRecoil"
}

CANONICAL_ORDER = {
    # Field lists reconciled against the actual consumers:
    #   client-side  -> the C# classes in TemplateStats.cs (Gun/WeaponMod/Gear/Ammo)
    #   server-side  -> ItemStatHandler's pusher helpers in json-handler.ts
    # A field only does something if it appears in one of those two places.
    "Ammo":[
        # The C# Ammo class is empty -- every ammo field is server-side,
        # written into _props by ammoPusherHelper.
        "$type", "ItemID", "Name", "Damage", "PenetrationPower",
        "InitialSpeed", "BallisticCoeficient", "BulletMassGram",
        "BulletDiameterMilimeters", "ammoAccr", "HeatFactor",
        "DurabilityBurnModificator", "Weight"
    ],
    "Gear":[
        "$type", "ItemID", "Name", "TemplateType",
        # client-side (Gear class)
        "ArmorClass", "MaskToUse", "AllowADS", "CanSpall", "SpallReduction",
        "BlocksMouth", "IsGasMask", "RadProtection", "GasProtection",
        "ReloadSpeedMulti", "Comfort", "dB",
        # server-side (gearPusherHelper)
        "ArmorLevel", "Durability", "BluntThroughput", "ArmorMaterial",
        "speedPenaltyPercent", "mousePenalty", "weaponErgonomicPenalty",
        "Weight", "Price"
    ],
    "WeaponMod":[
        "$type", "ItemID", "Name", "ModType",
        # client-side (WeaponMod class)
        "VerticalRecoil", "HorizontalRecoil", "Dispersion", "CameraRecoil",
        "AutoROF", "SemiROF", "ModMalfunctionChance", "ReloadSpeed", "AimSpeed",
        "ChamberSpeed", "Convergence", "CanCycleSubs", "RecoilAngle",
        "StockAllowADS", "FixSpeed", "ModShotDispersion", "MeleeDamage",
        "MeleePen", "Flash", "AimStability", "Handling",
        # server-side (modPusherHelper)
        "Ergonomics", "Accuracy", "CenterOfImpact", "HeatFactor", "CoolFactor",
        "DurabilityBurnModificator", "BlocksFolding", "Weight",
        "ShotgunDispersion", "Loudness", "HasShoulderContact", "Velocity"
    ],
    "Gun":[
        "$type", "ItemID", "Name",
        # client-side (Gun class)
        "WeapType", "OperationType", "BaseTorque", "HasShoulderContact",
        "WeapAccuracy", "RecoilDamping", "RecoilHandDamping", "WeaponAllowADS",
        "BaseReloadSpeedMulti", "MaxReloadSpeed", "MinReloadSpeed",
        "BaseChamberSpeedMulti", "MaxChamberSpeed", "MinChamberSpeed",
        "BaseChamberCheckSpeed", "BaseFixSpeed", "IsManuallyOperated",
        "VisualMulti", "EnableBSGVisRecoil", "ReduceBSGVisRecoil",
        # server-side (weapPusherHelper)
        "Ergonomics", "VerticalRecoil", "HorizontalRecoil", "Dispersion",
        "CameraRecoil", "RecoilAngle", "Convergence", "CenterOfImpact",
        "BaseMalfunctionChance", "HeatFactorGun", "HeatFactorByShot",
        "CoolFactorGun", "CoolFactorGunMods", "AllowOverheat",
        "DurabilityBurnRatio", "HipAccuracyRestorationDelay",
        "HipAccuracyRestorationSpeed", "HipInnaccuracyGain",
        "ShotgunDispersion", "Velocity", "Weight", "AutoROF", "SemiROF",
        "OffsetRotation", "RecoilIntensity"
    ]
}

def get_settings():
    return QSettings(CONFIG_FILE, QSettings.IniFormat)

def ask_for_folder(title):
    dlg = QFileDialog()
    dlg.setFileMode(QFileDialog.Directory)
    dlg.setOption(QFileDialog.ShowDirsOnly, True)
    dlg.setWindowTitle(title)
    if dlg.exec_(): return dlg.selectedFiles()[0]
    return ""

def get_mod_name_from_path(path: str, spt_root: str) -> str:
    mods_root = os.path.join(spt_root, "user", "mods")
    try: rel = os.path.relpath(path, mods_root)
    except ValueError: return "(External)"
    parts = rel.split(os.sep)
    if parts and parts[0] not in ("..", ".", ""): return parts[0]
    return "(External)"

def is_choccy_mod_path(path: str, spt_root: str) -> bool:
    mod_name = get_mod_name_from_path(path, spt_root)
    return isinstance(mod_name, str) and 'choccy' in mod_name.lower()

def load_exclude_patterns(settings: QSettings):
    user = (settings.value("exclude_patterns", "") or "").strip()
    toks =[t.strip().lower() for t in re.split(r"[;,]", user) if t.strip()]
    seen = set()
    out =[]
    for t in itertools.chain(toks, DEFAULT_EXCLUDE_DIR_CONTAINS):
        if t and t not in seen: out.append(t); seen.add(t)
    return out


def classify_realism_type(value: str) -> str:
    if not isinstance(value, str): return ""
    v = value.lower()
    if "weaponmod" in v: return "WeaponMod"
    if "gun" in v: return "Gun"
    if "ammo" in v: return "Ammo"
    if "gear" in v: return "Gear"
    return ""

def guess_type_bucket(compat: dict, base: dict, template: dict | None) -> str:
    ctype = classify_realism_type(compat.get("$type", ""))
    if ctype: return ctype

    base_props = base.get("_props", base) if isinstance(base, dict) else {}

    if isinstance(compat.get("WeapType"), str) or isinstance(compat.get("OperationType"), str) or "weapFireType" in base_props:
        return "Gun"
        
    if any(k in compat for k in["ArmorClass", "Comfort", "BlocksMouth", "TemplateType", "SpallReduction", "dB"]) or \
       any(k in base_props for k in["ArmorClass", "Comfort", "BlocksMouth", "TemplateType", "SpallReduction", "dB", "armorClass"]):
        return "Gear"

    if any(k in compat for k in["Damage", "PenetrationPower", "BasePriceModifier"]) or \
       "ammoType" in base_props or "Damage" in base_props:
        return "Ammo"

    if isinstance(compat.get("ModType"), str) or isinstance(base.get("ModType"), str) or "muzzleModType" in base_props:
        return "WeaponMod"

    if isinstance(template, dict):
        t = classify_realism_type(template.get("$type", ""))
        if t: return t

    return ""

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

def iter_js_files(root, exclude_contains=None, spt_root: str = ""):
    if exclude_contains is None: exclude_contains = DEFAULT_EXCLUDE_DIR_CONTAINS
    for dirpath, dirnames, filenames in os.walk(root):
        filtered =[]
        for d in dirnames:
            dl = d.lower()
            full = os.path.join(dirpath, d)
            if d in KNOWN_IGNORE_DIRS:
                if dl == 'src' and is_choccy_mod_path(full, spt_root):
                    filtered.append(d)
                continue
            if any(bad in dl for bad in exclude_contains):
                continue
            filtered.append(d)
        dirnames[:] = filtered
        if any(bad in dirpath.lower() for bad in exclude_contains):
            continue
        for f in filenames:
            if f.endswith(JS_EXT):
                yield os.path.join(dirpath, f)

def iter_massivesoft_js_files(root, exclude_contains=None, spt_root: str = ""):
    for path in iter_js_files(root, exclude_contains, spt_root):
        p = path.lower().replace('\\', '/')
        if '/src/' in p and ('massive' in p or 'massivesoft' in p):
            yield path

def iter_json_files(root, exclude_contains=None):
    if exclude_contains is None: exclude_contains = DEFAULT_EXCLUDE_DIR_CONTAINS
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] =[d for d in dirnames if d not in KNOWN_IGNORE_DIRS]
        dirnames[:] =[d for d in dirnames if not any(bad in d.lower() for bad in exclude_contains)]
        if any(bad in dirpath.lower() for bad in exclude_contains): continue
        for f in filenames:
            if f.endswith(JSON_EXT):
                fp = os.path.join(dirpath, f)
                if any(bad in fp.lower() for bad in exclude_contains): continue
                yield fp

def safe_json_load(path):
    try:
        with open(path, "r", encoding="utf-8") as fh: return json.load(fh)
    except Exception: return None

def _parse_js_chunk(chunk: str, path: str, idx: int):
    rec = {'_file': path, '_guid': f'{os.path.basename(path)}:{idx}', 'overrideProperties': {}, 'locales': {}}
    for key in ('_id','id','newId'):
        m = re.search(rf'["\']{key}["\']\s*:\s*["\']([^"\']+)["\']', chunk)
        if m:
            rec['_guid'] = m.group(1)
            rec['newId'] = m.group(1)
            break
    for key in ('itemTplToClone','clone','tpl','_tpl'):
        m = re.search(rf'["\']{key}["\']\s*:\s*["\']([^"\']+)["\']', chunk)
        if m:
            rec['itemTplToClone'] = m.group(1)
            break
    for key in ('Name','name','shortName'):
        m = re.search(rf'["\']{key}["\']\s*:\s*["\']([^"\']+)["\']', chunk)
        if m:
            if key.lower() == 'shortname':
                rec['shortName'] = m.group(1)
            else:
                rec['Name'] = m.group(1)
    if 'Name' in rec:
        rec['locales'].setdefault('en', {})['name'] = rec['Name']
    if 'shortName' in rec:
        rec['locales'].setdefault('en', {})['shortName'] = rec['shortName']
    for key in ('Weight','Ergonomics','RecoilForceUp','RecoilForceBack','BaseMalfunctionChance','Damage','PenetrationPower','Velocity','Loudness','CenterOfImpact'):
        m = re.search(rf'["\']{key}["\']\s*:\s*(-?\d+(?:\.\d+)?)', chunk)
        if m:
            rec['overrideProperties'][key] = float(m.group(1))
    return rec if rec.get('newId') or rec.get('itemTplToClone') else None

def _js_object_chunks(raw: str):
    chunks =[]
    for m in re.finditer(r'\{', raw):
        depth = 0
        start = m.start()
        for i in range(start, len(raw)):
            c = raw[i]
            if c == '{': depth += 1
            elif c == '}':
                depth -= 1
                if depth == 0:
                    chunk = raw[start:i+1]
                    if '_id' in chunk or 'itemTplToClone' in chunk or 'clone' in chunk:
                        chunks.append(chunk)
                    break
    return chunks

def parse_mass_js_file_records(path: str):
    try:
        raw = open(path, "r", encoding="utf-8", errors="ignore").read()
    except Exception:
        return []
    out =[]
    for i, chunk in enumerate(_js_object_chunks(raw)):
        rec = _parse_js_chunk(chunk, path, i)
        if rec:
            out.append((rec.get('_guid') or f'{os.path.basename(path)}:{i}', rec))
    return out

def parse_choccy_js_file_records(path: str):
    return parse_mass_js_file_records(path)

def unwrap_records(obj, path):
    out =[]
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
    if not isinstance(rec, dict): return {}
    p = rec.get("_props")
    if isinstance(p, dict): return p
    for k in ("item", "items"):
        it = rec.get(k)
        if isinstance(it, dict):
            p = it.get("_props")
            if isinstance(p, dict): return p
    return {}

def normalize_json_style_record(rec: dict):
    if not isinstance(rec, dict): return
    base_props = get_base_props_dict(rec)
    if base_props and "_props" not in rec: rec["_props"] = base_props 

    try:
        pf = base_props.get("Prefab", {})
        if isinstance(pf, dict):
            ppath = pf.get("path")
            if isinstance(ppath, str) and ppath.strip():
                rec.setdefault("overrideProperties", {}).setdefault("Prefab", {})["path"] = ppath
                rec["overrideProperties"].setdefault("PrefabPath", ppath)
    except Exception: pass

    hb = rec.get("handbook") or rec.get("Handbook")
    if isinstance(hb, dict):
        pid = (hb.get("ParentId") or hb.get("parentId") or hb.get("Parent") or hb.get("parent"))
        if isinstance(pid, str) and pid.strip():
            # Keep this as the HANDBOOK parent. Writing it into rec["parent"]
            # overwrote the item's real class parent, which is what broke
            # category detection for pistols (and anything else whose mod
            # author picked a handbook node the parent table doesn't know).
            rec.setdefault("handbookParentId", pid.strip())
            rec.setdefault("parent", pid.strip())
        price = hb.get("Price")
        if isinstance(price, (int, float)):
            rec.setdefault("overrideProperties", {})["Price"] = int(price)

    def _from_locales(lc: dict) -> tuple[str, str]:
        if not isinstance(lc, dict): return "", ""
        en = lc.get("en")
        if isinstance(en, dict):
            return (str(en.get("Name") or en.get("name") or "") or "",
                    str(en.get("ShortName") or en.get("shortName") or "") or "")
        for lang in lc.values():
            if isinstance(lang, dict):
                n = str(lang.get("Name") or lang.get("name") or "") or ""
                s = str(lang.get("ShortName") or lang.get("shortName") or "") or ""
                if n or s: return n, s
        return "", ""

    n, s = _from_locales(rec.get("locales") or rec.get("_locales") or {})
    if not n: n = str(base_props.get("Name") or base_props.get("name") or rec.get("_name") or "")
    if not s: s = str(base_props.get("ShortName") or base_props.get("shortName") or "")

    if n: rec["Name"] = n
    if s: rec["shortName"] = s
    if isinstance(rec.get("isweapon"), bool):
        rec["$type"] = "RealismMod.Gun, RealismMod" if rec["isweapon"] else "RealismMod.WeaponMod, RealismMod"

def reorder_fields(record: dict) -> dict:
    if not isinstance(record, dict): return record

    # Final gate: banned fields never reach an exported file.
    record = strip_banned(record)

    type_str = record.get("$type", "")
    bucket = classify_realism_type(type_str)
    if bucket == "Weapon": bucket = "Gun"
    
    order_list = CANONICAL_ORDER.get(bucket,[])
    if not order_list: return record

    ordered = OrderedDict()
    
    if "$type" in record:
        ordered["$type"] = record["$type"]

    for key in order_list:
        if key == "$type": continue
        if key in record:
            ordered[key] = record[key]
            
    for key, val in record.items():
        if key not in ordered:
            ordered[key] = val
            
    return dict(ordered)

class CompatTemplateIndex:
    def __init__(self):
        self.by_target = defaultdict(list)
        self.all_templates =[]
        self.by_parent = defaultdict(list)
        self.by_parent_id = defaultdict(list)

    def add(self, rec):
        target = (rec.get("ItemID") or rec.get("ItemId") or rec.get("id") or rec.get("_guid"))
        parent = (rec.get("parentClass") or rec.get("ParentClass") or rec.get("$type") or rec.get("parent"))
        if not (target or parent): return
        self.all_templates.append(rec)
        if target: self.by_target[str(target)].append(rec)
        if parent: self.by_parent[str(parent)].append(rec)
        pid = rec.get("parent") or rec.get("Parent") or rec.get("parentId")
        if pid: self.by_parent_id[str(pid)].append(rec)

    def match_by_item(self, item):
        candidate_ids =[]
        for key in ("itemTplToClone","itemtpltoclone","clone","tpl","_tpl","id","_id","_guid","newId"):
            v = item.get(key)
            if v: candidate_ids.append(str(v))
        candidate_ids = list(dict.fromkeys(candidate_ids))
        matches =[]
        for cid in candidate_ids:
            matches.extend(self.by_target.get(cid,[]))

        item_parent_id = item.get("parent") or item.get("Parent") or item.get("parentId")
        if not matches and item_parent_id:
            matches.extend(self.by_parent_id.get(str(item_parent_id),[]))

        if not matches:
            parent = (item.get("parentClass") or item.get("ParentClass") or item.get("$type") or item.get("parent"))
            if parent: matches.extend(self.by_parent.get(str(parent),[]))

        seen, uniq = set(),[]
        for m in matches:
            mid = id(m)
            if mid not in seen:
                seen.add(mid)
                uniq.append(m)

        return uniq, candidate_ids

class SPTIndex:
    def __init__(self, spt_path, compat_root=None, exclude_contains=None):
        self.spt_path = spt_path
        self.compat_root = compat_root
        self.exclude_contains = (exclude_contains or DEFAULT_EXCLUDE_DIR_CONTAINS)
        self.items =[]
        self.items_by_mod = defaultdict(list)
        self.name_map = {}
        self.template_index = CompatTemplateIndex()
        self.scan_stats = {}

    def scan(self):
        def record_is_displayable(rec: dict) -> bool:
            if not isinstance(rec, dict): return False
            for k in rec.keys():
                if k.lower() in ("_props", "overrideproperties"): return True
            for v in rec.values():
                if isinstance(v, dict):
                    for k2 in v.keys():
                        if k2.lower() in ("_props", "overrideproperties"): return True
            return False

        self.items.clear()
        self.items_by_mod.clear()
        self.name_map.clear()
        self.template_index = CompatTemplateIndex()
        
        stats = defaultdict(int)

        scan_roots =[os.path.join(self.spt_path, "user", "mods")]
        if self.compat_root and os.path.isdir(self.compat_root):
            scan_roots.append(self.compat_root)

        for root in scan_roots:
            if not os.path.isdir(root): continue

            for path in iter_json_files(root, self.exclude_contains):
                stats['json_files'] += 1
                if any(bad in path.lower() for bad in self.exclude_contains): continue
                obj = safe_json_load(path)

                if obj is None:
                    compact_records = parse_compact_items_json(path)
                    if compact_records:
                        stats['compact_records'] += len(compact_records)
                        mod_name = get_mod_name_from_path(path, self.spt_path)
                        for rid, rec in compact_records:
                            rec["_mod"] = mod_name
                            nm = get_display_name(rec)
                            self.name_map[str(rid)] = nm
                            if record_is_displayable(rec):
                                self.items.append(rec)
                                self.items_by_mod[mod_name].append(rec)
                            self.template_index.add(rec)
                    continue

                unwrapped = unwrap_records(obj, path)
                stats['json_records'] += len(unwrapped)
                mod_name = get_mod_name_from_path(path, self.spt_path)
                for rid, rec in unwrapped:
                    normalize_json_style_record(rec)
                    strip_banned_inplace(rec)
                    rec["_mod"] = mod_name
                    nm = get_display_name(rec)
                    self.name_map[str(rid)] = nm
                    if record_is_displayable(rec):
                        self.items.append(rec)
                        self.items_by_mod[mod_name].append(rec)
                    self.template_index.add(rec)

            for path in iter_js_files(root, self.exclude_contains, self.spt_path):
                stats['js_files'] += 1
                parsed = parse_choccy_js_file_records(path) if is_choccy_mod_path(path, self.spt_path) else parse_mass_js_file_records(path)
                if parsed:
                    stats['js_records'] += len(parsed)
                    mod_name = get_mod_name_from_path(path, self.spt_path)
                    for rid, rec in parsed:
                        normalize_json_style_record(rec)
                        rec["_mod"] = mod_name
                        nm = get_display_name(rec)
                        self.name_map[str(rid)] = nm
                        if record_is_displayable(rec):
                            self.items.append(rec)
                            self.items_by_mod[mod_name].append(rec)
                        self.template_index.add(rec)

            for path in iter_massivesoft_js_files(root, self.exclude_contains, self.spt_path):
                stats['massivesoft_js_files'] += 1

        self.scan_stats = dict(stats)
        print(f"Indexed: json_files={stats['json_files']} json_records={stats['json_records']} compact_records={stats['compact_records']} js_files={stats['js_files']} js_records={stats['js_records']} massivesoft_js_files={stats['massivesoft_js_files']}")
        print(f"Visible items in tree: {len(self.items)}")

    def display_name_for(self, rec):
        nm = get_display_name(rec)
        if nm and nm != "Unknown": return nm
        for k in ("id", "_id", "_guid", "tpl", "_tpl", "itemTplToClone", "itemtpltoclone", "newId"):
            v = rec.get(k)
            if v and str(v) in self.name_map: return self.name_map[str(v)]
        return nm

class BaseGameDB:
    def __init__(self, spt_path, exclude_contains):
        self.spt_path = spt_path
        self.exclude_contains = exclude_contains
        self.by_id = {}

    def scan(self):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        master_path = os.path.join(script_dir, "items_master.json")
        if not os.path.isfile(master_path): return
        try:
            with open(master_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                for k, rec in data.items(): self.by_id[k] = rec
            elif isinstance(data, list):
                for rec in data:
                    for key in ("id", "_id", "_guid", "tpl", "_tpl"):
                        v = rec.get(key)
                        if isinstance(v, str) and v.strip():
                            self.by_id.setdefault(v.strip(), rec)
        except Exception: pass

class RealismDB:
    def __init__(self, spt_path):
        self.spt_path = spt_path
        self.by_id = {}

    def scan(self):
        mods_root = os.path.join(self.spt_path, "user", "mods")
        if not os.path.isdir(mods_root): return
        for mod in os.listdir(mods_root):
            if "spt-realism" not in mod.lower(): continue
            base = os.path.join(mods_root, mod)
            for path in iter_json_files(base,[]):
                obj = safe_json_load(path)
                if obj is None: continue
                for rid, rec in unwrap_records(obj, path):
                    for key in ("ItemID", "id", "_id", "_guid", "tpl", "_tpl"):
                        v = rec.get(key)
                        if isinstance(v, str) and v.strip():
                            self.by_id.setdefault(v.strip(), rec)

class UserTemplatesDB:
    def __init__(self, spt_path):
        self.spt_path = spt_path
        self.by_id = {}
        self.by_file = defaultdict(list)
        self.loaded_files =[]

    def scan(self):
        base = os.path.join(self.spt_path, "user", "mods", "SPT-Realism", "db", "templates", "user_templates")
        self.by_id.clear(); self.by_file.clear(); self.loaded_files.clear()
        if not os.path.isdir(base): return

        for path in iter_json_files(base, exclude_contains=[]):
            obj = safe_json_load(path)
            if not isinstance(obj, dict): continue
            self.loaded_files.append(path)
            for item_id, compat in obj.items():
                if not isinstance(compat, dict): continue
                c = strip_banned(dict(compat))
                c["_file"] = path
                c["_guid"] = item_id
                c["ItemID"] = c.get("ItemID") or item_id
                if "Name" not in c:
                    c["Name"] = c.get("shortName") or c.get("ShortName") or item_id
                self.by_id[item_id] = c
                self.by_file[path].append(c)

# -------------------------
# UI pieces
# -------------------------
class CompatForm(QWidget):
    MODTYPE_OPTIONS =[
        "", "bipod", "short_barrel", "booster", "762x39", "300", "556", "366TKM", "308", "277",
        "sight", "mount", "shotTube", "foregrip_adapter", "shot_pump_grip_adapt", "counterWeight",
        "muzzle_supp_adapter", "sig_taper_brake", "barrel_2slot",
        "grip_stock_adapter", "buffer_adapter", "stock_adapter",
        "hydraulic_buffer", "buffer", "buffer_stock", "Stock", "StockR", "StockN", "StockF",
        # Used on 19 magazines in Realism's own MagazineTemplates.json but
        # missing from this list, so the dropdown could not represent them.
        "long_mag"
    ]
    WEAPTYPE_OPTIONS =["", "DI", "bullpup", "short_AK"]
    OPERATION_OPTIONS =["", "buffer", "magForward", "tubefed", "tubefed-m", "p90"]
    
    ARMOR_MATERIAL_OPTIONS =["", "Glass", "Aramid", "Ceramic", "Combined",
                             "UHMWPE", "Aluminium", "Titan", "ArmoredSteel"]

    # Every ArmorClass string used across Realism's shipped gear templates.
    ARMOR_CLASS_OPTIONS =["", "Unclassified",
        "GOST 1", "GOST 2", "GOST 2A", "GOST 3", "GOST 3A", "GOST 4",
        "GOST 5", "GOST 5A", "GOST 6A",
        "NIJ II", "NIJ IIA", "NIJ IIIA", "Abbr. NIJ IIIA", "NIJ III",
        "NIJ III+", "NIJ IV", "NIJ RF3 07",
        "ESAPI", "ESAPI (Rev. G)", "ESAPI (Rev. J)", "XSAPI", "MK4A Plates",
        "PM 5", "PM 8", "PM 10",
        "Gentex PRS-1011", "MIL-PRF-32432 (GL)", "BS EN 166:2002 Class 2B",
        "16gr V50 \u2265 905 m/s", "17gr V0 \u2265 731 m/s",
        "124gr 9mm FMJ V0 \u2265 427 m/s", "7.62x39 MSC @ 732 m/s"]
    MASK_OPTIONS =["", "atomic"]
    
    TYPE_OPTIONS =[
        "RealismMod.WeaponMod, RealismMod",
        "RealismMod.Gun, RealismMod",
        "RealismMod.Gear, RealismMod",
        "RealismMod.Ammo, RealismMod"
    ]

    PROTECTED_KEYS = {"$type", "ItemID", "Name", "_id", "id", "_guid"}

    # Emitted with the hovered field name, or "" when the cursor leaves a row.
    hoverKeyChanged = pyqtSignal(str)

    def __init__(self, compat_dict, editable=True, schema_for_type=None,
                 category=""):
        super().__init__()
        self.compat_dict = strip_banned(compat_dict or {})
        self.fields = {}
        self.labels = {}
        self.rows = {}
        self.clone_buttons = {}
        self._baseline = {}
        self.bucket = classify_realism_type(self.compat_dict.get("$type", "")) or "WeaponMod"
        self.schema_for_type = {k for k in (schema_for_type or set()) if not is_banned(k)}
        self.category = category or ""
        self._ctype = classify_realism_type(self.compat_dict.get("$type", ""))

        outer = QVBoxLayout(self)
        self._form = QFormLayout()
        self._form.setVerticalSpacing(4) 
        
        keys = list(self.compat_dict.keys())
        priority =["$type", "ItemID", "Name", "TemplateType", "ArmorClass", "ModType", "WeapType", "OperationType"]
        keys.sort(key=lambda k: (0 if k in priority else 1, priority.index(k) if k in priority else k.lower()))

        for k in keys:
            if k.startswith("_") or is_banned(k): continue
            v = self.compat_dict[k]
            self._add_row_to_layout(k, v)
            
        outer.addLayout(self._form)

        self.add_row = None
        if editable:
            self.add_row = QHBoxLayout()
            self.add_row.addWidget(QLabel("<b>+ Add Field:</b>"))
            
            self.cb_add = QComboBox()
            self.add_row.addWidget(self.cb_add, 1)
            
            self.btn_add = QPushButton("Add")
            self.btn_add.setFixedWidth(60)
            self.btn_add.clicked.connect(self._on_add_field)
            self.add_row.addWidget(self.btn_add)
            
            self._all_allowed = sorted(set(self.schema_for_type))
            self._refresh_add_dropdown()
            
            outer.addLayout(self.add_row)

    def _add_row_to_layout(self, key, val):
        if is_banned(key): return

        editor_widget = self._widget_for(key, val)
        self.fields[key] = editor_widget

        label = QLabel(key)
        self.labels[key] = label

        tip = tooltip_for(key)
        status = field_status(self.bucket, key)
        if status == "unknown":
            label.setText("\u26a0 " + key)
            tip += ("<br><br><span style='color:#e05555'>\u26a0 Nothing consumes this field on a "
                    f"{self.bucket}. It will export, but the server does nothing with it.</span>")
        elif status == "inert":
            label.setText("\u26a0 " + key)
            tip += ("<br><br><span style='color:#d7a04a'>\u26a0 Ships in Realism's own templates but "
                    "has no consumer \u2014 inert.</span>")
        else:
            applied = field_applied_by(self.bucket, key)
            if applied:
                tip += f"<br><span style='color:#6a9a6a'>Server {applied}.</span>"
        label.setToolTip(tip)
        editor_widget.setToolTip(tip)

        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        layout.addWidget(editor_widget, 1)

        if key not in self.PROTECTED_KEYS:
            btn_clone = QPushButton("=")
            btn_clone.setFixedSize(24, 24)
            btn_clone.setStyleSheet(
                "QPushButton { color: #4C8DFF; font-weight: bold; border: 1px solid #33456b; } "
                "QPushButton:hover { background-color: #22314a; } "
                "QPushButton:disabled { color: #555; border: 1px solid #333; }")
            btn_clone.clicked.connect(lambda _, k=key: self._set_to_baseline(k))
            layout.addWidget(btn_clone)
            self.clone_buttons[key] = btn_clone

            btn_del = QPushButton("X")
            btn_del.setFixedSize(24, 24)
            btn_del.setStyleSheet("QPushButton { color: #ff5555; font-weight: bold; border: 1px solid #553333; } QPushButton:hover { background-color: #442222; }")
            btn_del.setToolTip(f"Remove field '{key}'")
            btn_del.clicked.connect(lambda _, k=key: self._on_remove_field(k))
            layout.addWidget(btn_del)

        # Hover tracking: the label and the row container both report the key so
        # the comparison panels can highlight the matching stat.
        for w in (container, label):
            w.setAttribute(Qt.WA_Hover, True)
            w.setProperty("_compat_key", key)
            w.installEventFilter(self)
        container.setToolTip(tip)

        self.rows[key] = container
        self._form.addRow(label, container)

        # Live recolour as the value is edited.
        if isinstance(editor_widget, (QDoubleSpinBox, QSpinBox)):
            editor_widget.valueChanged.connect(lambda _v, k=key: self._recolor_key(k))
        elif isinstance(editor_widget, QComboBox):
            editor_widget.currentTextChanged.connect(lambda _v, k=key: self._recolor_key(k))
        elif isinstance(editor_widget, QLineEdit):
            editor_widget.textChanged.connect(lambda _v, k=key: self._recolor_key(k))

        self._recolor_key(key)

    def eventFilter(self, obj, event):
        et = event.type()
        if et in (QEvent.Enter, QEvent.HoverEnter):
            key = obj.property("_compat_key")
            if key: self.hoverKeyChanged.emit(str(key))
        elif et in (QEvent.Leave, QEvent.HoverLeave):
            key = obj.property("_compat_key")
            if key: self.hoverKeyChanged.emit("")
        return super().eventFilter(obj, event)

    def _set_field_value(self, key, val):
        w = self.fields.get(key)
        if w is None or val is None: return False
        if isinstance(w, QDoubleSpinBox):
            try: w.setValue(round(float(val), decimals_for(key, float(val))))
            except (TypeError, ValueError): return False
        elif isinstance(w, QSpinBox):
            try: w.setValue(int(round(float(val))))
            except (TypeError, ValueError): return False
        elif isinstance(w, QComboBox):
            if w.itemText(0) == "False" and w.itemText(1) == "True":
                w.setCurrentIndex(1 if str(val).lower() in ("true", "1", "1.0") else 0)
            else:
                idx = w.findText(str(val))
                if idx >= 0: w.setCurrentIndex(idx)
                elif w.isEditable(): w.setCurrentText(str(val))
                else: return False
        elif isinstance(w, QLineEdit):
            w.setText(str(val))
        else:
            return False
        return True

    def _set_to_baseline(self, key):
        """Copy the cloned item's value for this field into the editor."""
        val = self._baseline_value(key)
        if val is None: return
        self._set_field_value(key, val)
        self._recolor_key(key)

    def _refresh_clone_buttons(self):
        for key, btn in self.clone_buttons.items():
            val = self._baseline_value(key)
            btn.setEnabled(val is not None)
            if val is None:
                btn.setToolTip(f"No cloned value available for '{key}'")
            else:
                btn.setToolTip(f"Set '{key}' to the cloned item's value ({val})")

    # ---- comparison colouring -------------------------------------------
    def set_comparison_baseline(self, baseline: dict):
        """baseline = the cloned item's stats, used to colour every field."""
        self._baseline = dict(baseline or {})
        for key in list(self.fields.keys()):
            self._recolor_key(key)
        self._refresh_clone_buttons()

    def _baseline_value(self, key):
        if not self._baseline: return None
        if key in self._baseline: return self._baseline[key]
        for alias in COMPARE_ALIASES.get(key, ()):
            if alias in self._baseline: return self._baseline[alias]
        lower = {str(k).lower(): v for k, v in self._baseline.items()}
        return lower.get(str(key).lower())

    def _current_value(self, key):
        w = self.fields.get(key)
        if w is None: return None
        if isinstance(w, QDoubleSpinBox): return round(w.value(), decimals_for(key))
        if isinstance(w, QSpinBox): return w.value()
        if isinstance(w, QComboBox):
            if w.itemText(0) == "False" and w.itemText(1) == "True":
                return w.currentIndex() == 1
            return w.currentText()
        if isinstance(w, QLineEdit): return w.text()
        return None

    def _recolor_key(self, key):
        w = self.fields.get(key)
        lbl = self.labels.get(key)
        if w is None: return
        if key in self.PROTECTED_KEYS:
            color = COLOR_NONE
        else:
            color = compare_color(key, self._current_value(key), self._baseline_value(key))

        w.setStyleSheet(f"border: 1px solid {color};")
        if lbl is not None:
            weight = "bold" if color in (COLOR_BETTER, COLOR_WORSE) else "normal"
            lbl.setStyleSheet(f"color: {color}; font-weight: {weight};")

    def _on_remove_field(self, key):
        if key in self.compat_dict: del self.compat_dict[key]
        if key in self.fields: del self.fields[key]
        self.labels.pop(key, None)
        self.rows.pop(key, None)
        self.clone_buttons.pop(key, None)

        for i in range(self._form.rowCount()):
            item = self._form.itemAt(i, QFormLayout.LabelRole)
            if item and item.widget():
                lbl = item.widget()
                if isinstance(lbl, QLabel) and lbl.text() == key:
                    self._form.removeRow(i)
                    break
        self._refresh_add_dropdown()

    def _widget_for(self, key, val):
        if key == "$type":
            cb = QComboBox()
            cb.addItems(self.TYPE_OPTIONS)
            
            if not val or val not in self.TYPE_OPTIONS:
                bucket = classify_realism_type(str(val))
                if not bucket: bucket = "WeaponMod"
                val = f"RealismMod.{bucket}, RealismMod"
                
            idx = cb.findText(str(val))
            if idx >= 0: cb.setCurrentIndex(idx)
            return cb

        if key.lower() == "modtype":
            cb = QComboBox()
            cb.addItems(self.MODTYPE_OPTIONS)
            idx = cb.findText(str(val))
            if idx >= 0: cb.setCurrentIndex(idx)
            else: cb.setEditText(str(val))
            return cb

        if key == "WeapType":
            cb = QComboBox(); cb.addItems(self.WEAPTYPE_OPTIONS)
            idx = cb.findText(str(val))
            if idx >= 0: cb.setCurrentIndex(idx)
            return cb

        if key == "OperationType":
            cb = QComboBox(); cb.addItems(self.OPERATION_OPTIONS)
            idx = cb.findText(str(val))
            if idx >= 0: cb.setCurrentIndex(idx)
            return cb
            
        if key == "ArmorClass":
            cb = QComboBox()
            cb.setEditable(True)
            cb.addItems(self.ARMOR_CLASS_OPTIONS)
            cb.setCurrentText(str(val) if val else "")
            return cb
            
        if key == "ArmorMaterial":
            cb = QComboBox()
            cb.setEditable(True)
            cb.addItems(self.ARMOR_MATERIAL_OPTIONS)
            cb.setCurrentText(str(val) if val else "")
            return cb

        if key == "MaskToUse":
            cb = QComboBox()
            cb.setEditable(True)
            cb.addItems(self.MASK_OPTIONS)
            cb.setCurrentText(str(val) if val else "")
            return cb

        if key in KNOWN_BOOLS or isinstance(val, bool):
            box = QComboBox()
            box.addItems(["False", "True"])
            is_true = str(val).lower() == "true" or val == 1 or val == 1.0
            box.setCurrentIndex(1 if is_true else 0)
            return box

        if isinstance(val, (int, float)) and not isinstance(val, bool):
            # An int-looking 0 on a float field must still get a float editor,
            # otherwise values like 0.0025 can never be typed in.
            if isinstance(val, int) and key not in INT_FIELDS and not is_float_field(key):
                sp = QSpinBox()
                sp.setRange(-1_000_000, 1_000_000)
                sp.setValue(val)
                return sp
            if key in INT_FIELDS:
                sp = QSpinBox()
                sp.setRange(-1_000_000, 1_000_000)
                sp.setValue(int(round(float(val))))
                return sp

            dec = decimals_for(key, float(val))
            dsp = QDoubleSpinBox()
            dsp.setDecimals(dec)
            dsp.setRange(-1_000_000.0, 1_000_000.0)
            dsp.setSingleStep(step_for(key, dec))
            dsp.setValue(round(float(val), dec))
            return dsp

        return QLineEdit(str(val))

    def _on_add_field(self):
        key = self.cb_add.currentText().strip() if hasattr(self, "cb_add") else ""
        if not key or key in self.fields or is_banned(key): return
        
        default = ""
        if key in KNOWN_BOOLS or re.search(r"(Allow|Has|Can|Is|Blocks)[A-Z_]", key): default = False 
        elif re.search(r"(Speed|Velocity|Recoil|Angle|Dispersion|Accuracy|Heat|Cool|Weight|Ergonomics|Reduction|dB|Level|Price|Penalty|Damage|Power)", key, re.I): default = 0.0
        elif key == "TemplateType": default = "gear"
            
        self.compat_dict[key] = default
        if key == "$type": self._ctype = classify_realism_type(self.compat_dict.get("$type", ""))
        
        self._add_row_to_layout(key, default)
        self._refresh_add_dropdown()

    def _refresh_add_dropdown(self):
        if not hasattr(self, "cb_add"): return
        have = set(self.fields.keys())
        missing =[k for k in self._all_allowed if k not in have]
        
        for extra in["ArmorClass", "TemplateType", "CanSpall", "SpallReduction", "BlocksMouth", "MaskToUse", "dB", "Price", "Comfort", "ChamberSpeed", "Damage", "PenetrationPower", "HeatFactor", "CoolFactor", "BaseChamberCheckSpeed", "BaseChamberSpeedMulti", "MinChamberSpeed", "MaxChamberSpeed"]:
            if extra not in have and extra not in missing:
                missing.append(extra)

        for extra in sorted(add_only_for(self.bucket)):
            if extra not in have and extra not in missing:
                missing.append(extra)

        # Category-specific fields (barrels get Velocity, suppressors get
        # Loudness/CanCycleSubs, ...). These are dropped from the formula output
        # when the fit is not good enough to justify writing them, but they are
        # still legitimate fields the author may want to set by hand.
        for extra in sorted(category_add_fields(self.category)):
            if extra not in have and extra not in missing:
                missing.append(extra)

        missing = [k for k in missing if not is_banned(k)]

        self.cb_add.clear()
        self.cb_add.addItems(sorted(missing))
        if hasattr(self, "btn_add"): self.btn_add.setEnabled(bool(missing))

    def value(self):
        out = {}
        for k, w in self.fields.items():
            if is_banned(k): continue
            if isinstance(w, QDoubleSpinBox): out[k] = round(w.value(), decimals_for(k, w.value()))
            elif isinstance(w, QSpinBox): out[k] = w.value()
            elif isinstance(w, QComboBox):
                if w.itemText(0) == "False" and w.itemText(1) == "True": out[k] = (w.currentIndex() == 1)
                else: out[k] = w.currentText()
            else:
                txt = w.text()
                if k in KNOWN_BOOLS: out[k] = (txt.lower() == "true")
                elif re.fullmatch(r"-?\d+", txt): out[k] = int(txt)
                elif re.fullmatch(r"-?\d+(\.\d+)?", txt): out[k] = round(float(txt), decimals_for(k, float(txt)))
                else: out[k] = txt
        return out

class CloneTargetDialog(QDialog):
    """Pick any number of mod items that should receive a copy of the stats
    currently sitting in the compat form. Each target keeps its own ItemID and
    Name; everything else is copied verbatim."""

    def __init__(self, parent, entries, source_label=""):
        """entries: list of (record, item_id, display_name, mod_name)"""
        super().__init__(parent)
        self.setWindowTitle("Clone stats to other items")
        self.resize(680, 620)
        self._entries = entries

        lay = QVBoxLayout(self)

        if source_label:
            hdr = QLabel(f"Copying the stats from <b>{source_label}</b> to the items you tick below.<br>"
                         "<span style='color:#9aa0a6'>Each clone keeps its own ItemID and Name.</span>")
            hdr.setTextFormat(Qt.RichText)
            hdr.setWordWrap(True)
            lay.addWidget(hdr)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Filter by name, ItemID or mod…")
        self.search.textChanged.connect(self._apply_filter)
        lay.addWidget(self.search)

        self.list = QListWidget()
        self.list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        for rec, iid, name, mod in entries:
            it = QListWidgetItem(f"{name}   [{iid}]   ({mod})")
            it.setFlags(it.flags() | Qt.ItemIsUserCheckable)
            it.setCheckState(Qt.Unchecked)
            it.setData(Qt.UserRole, rec)
            it.setData(Qt.UserRole + 1, iid)
            it.setData(Qt.UserRole + 2, name)
            self.list.addItem(it)
        self.list.itemDoubleClicked.connect(self._toggle_item)
        lay.addWidget(self.list, 1)

        row = QHBoxLayout()
        b_all = QPushButton("Check All Visible")
        b_all.clicked.connect(lambda: self._set_visible(Qt.Checked))
        row.addWidget(b_all)

        b_none = QPushButton("Uncheck All Visible")
        b_none.clicked.connect(lambda: self._set_visible(Qt.Unchecked))
        row.addWidget(b_none)

        b_sel = QPushButton("Check Highlighted")
        b_sel.clicked.connect(self._check_selected)
        row.addWidget(b_sel)

        b_clear = QPushButton("Uncheck Everything")
        b_clear.clicked.connect(self._clear_all)
        row.addWidget(b_clear)
        lay.addLayout(row)

        self.lbl_count = QLabel("0 selected")
        lay.addWidget(self.lbl_count)
        self.list.itemChanged.connect(lambda _i: self._update_count())

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        lay.addWidget(buttons)

    def _toggle_item(self, item):
        item.setCheckState(Qt.Unchecked if item.checkState() == Qt.Checked else Qt.Checked)

    def _apply_filter(self, text):
        q = (text or "").lower().strip()
        for i in range(self.list.count()):
            it = self.list.item(i)
            it.setHidden(bool(q) and q not in it.text().lower())

    def _set_visible(self, state):
        for i in range(self.list.count()):
            it = self.list.item(i)
            if not it.isHidden(): it.setCheckState(state)

    def _check_selected(self):
        for it in self.list.selectedItems():
            it.setCheckState(Qt.Checked)

    def _clear_all(self):
        for i in range(self.list.count()):
            self.list.item(i).setCheckState(Qt.Unchecked)

    def _update_count(self):
        self.lbl_count.setText(f"{len(self.chosen())} selected")

    def chosen(self):
        """Returns [(record, item_id, display_name), ...] for every ticked row."""
        out = []
        for i in range(self.list.count()):
            it = self.list.item(i)
            if it.checkState() == Qt.Checked:
                out.append((it.data(Qt.UserRole),
                            it.data(Qt.UserRole + 1),
                            it.data(Qt.UserRole + 2)))
        return out


class MainWindow(QWidget):
    
    CALIBERS =[
        "9x18 PM", "9x19", "9x21", "7.62x25", ".45 ACP", "4.6x30", "5.7x28", ".357 Magnum", ".44 Magnum", "9x33R",
        "5.45x39", "5.56x45", "7.62x39", ".300 Blackout", "7.62x51", "7.62x54R", ".338 Lapua", ".277 Fury", "9x39", ".366 TKM", "12.7x55",
        "12g", "20g", "23x75"
    ]
    
    MUZZLE_PRESETS =["Select Formula Profile..."]
    for cal in CALIBERS:
        MUZZLE_PRESETS.extend([f"{cal} sound suppressor", f"{cal} muzzle brake", f"{cal} flash hider", f"{cal} thread adapter"])
        
    BARREL_PRESETS =["Select Formula Profile..."]
    for cal in CALIBERS:
        BARREL_PRESETS.extend([
            f"{cal} 5 inch barrel", f"{cal} 10.5 inch barrel", 
            f"{cal} 14.5 inch barrel", f"{cal} 16 inch barrel", 
            f"{cal} 20 inch barrel", f"{cal} 24 inch barrel"
        ])
        
    STOCK_PRESETS =["Select Formula Profile...", "heavy stock", "light stock", "heavy buffer tube", "light buffer tube", "standard stock"]
    HANDGUARD_PRESETS =["Select Formula Profile...", "short handguard", "long handguard", "heavy handguard", "light handguard", "short heavy handguard", "long light handguard"]
    SIGHT_PRESETS =["Select Formula Profile...", "compact collimator sight", "collimator sight", "assault scope sight", "optic sight"]
    AMMO_PRESETS =["Select Formula Profile..."] + sorted(AMMO_CALIBRE_PROFILES)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("SPT Realism Compat Tool (Dark)")
        self.resize(1300, 780)
        self.settings = get_settings()
        self.exclude_contains = load_exclude_patterns(self.settings)
        self.spt_path = self.ensure_spt_path()
        self.compat_root = self.settings.value("compat_root", "")

        self.index = SPTIndex(self.spt_path, self.compat_root if self.compat_root else None, self.exclude_contains)
        self.index.scan()
        
        self.base_db = BaseGameDB(self.spt_path, self.exclude_contains)
        self.base_db.scan()

        self.realism_db = RealismDB(self.spt_path)
        self.realism_db.scan()

        self.user_templates = UserTemplatesDB(self.spt_path)
        self.user_templates.scan()
        
        for rec in self.realism_db.by_id.values():
            self.index.template_index.add(rec)
        
        script_dir = os.path.dirname(os.path.abspath(__file__))
        
        self.export_queue =[]

        ok, err = safe_load_formulas()
        if not ok: QMessageBox.warning(self, "Formulas load error", f"Could not load formulas.py:\n\n{err}")

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

        self.selected_records =[]
        self.compat_forms =[]
        self._hover_key = None
        self._realism_stats_data = {}
        self._basegame_stats_data = {}

        self.init_ui()
        self.populate_items_tree()
        self.populate_user_templates_tree()
        self._refresh_queue_view()

    def _base_tpl_and_record(self, base: dict):
        tpl = None
        for key in ("itemTplToClone","itemtpltoclone","clone","tpl","_tpl"):
            v = base.get(key)
            if isinstance(v, str) and v.strip():
                tpl = v.strip()
                break
        rec = self.base_db.by_id.get(tpl) if tpl else None
        return tpl, rec
    def _base_items(self) -> dict:
        """Lazily-loaded, cached vanilla item DB (by tpl id)."""
        db = getattr(self, "_base_items_db", None)
        if db is None:
            db = _load_base_items_db(getattr(self, "spt_path", ""))
            self._base_items_db = db
        return db


    def _clone_base_props(self, mod_item: dict) -> dict:
        """Return the _props of the item referenced by itemTplToClone, walking clone chains
        (a mod may clone another modded item that itself clones a vanilla item)."""
        if not isinstance(mod_item, dict):
            return {}
        db = self._base_items()
        seen = set()
        tpl = (mod_item.get("itemTplToClone") or mod_item.get("itemtpltoclone")
            or mod_item.get("clone") or mod_item.get("tpl") or mod_item.get("_tpl"))
        for _ in range(10):  # bounded clone-chain walk
            if not tpl or tpl in seen:
                break
            seen.add(tpl)
            # 1) vanilla DB
            entry = db.get(tpl)
            if isinstance(entry, dict) and isinstance(entry.get("_props"), dict):
                return dict(entry["_props"])
            # 2) another modded item in the scanned index (clone-of-a-clone)
            modded = None
            if hasattr(self, "index"):
                for rec in getattr(self.index, "items", []):
                    for k in ("_guid", "id", "_id", "newId"):
                        if rec.get(k) == tpl:
                            modded = rec
                            break
                    if modded:
                        break
            if isinstance(modded, dict):
                bp = modded.get("_props")
                if isinstance(bp, dict) and bp:
                    return dict(bp)
                tpl = (modded.get("itemTplToClone") or modded.get("clone")
                    or modded.get("tpl") or modded.get("_tpl"))
                continue
            break
        return {}
    def _ensure_identity_fields(self, base: dict, compat: dict, template: dict = None) -> dict:
        if not isinstance(compat, dict): return compat or {}

        # Every computed/edited compat funnels through here on its way to the
        # form or to disk, so this is the reliable place to drop banned fields.
        strip_banned_inplace(compat)

        # 1. Force ItemID: Always use the target mod item's ID
        base_id = str((base or {}).get("newId") or (base or {}).get("_guid") or (base or {}).get("id") or (base or {}).get("_id") or "")
        
        if base_id:
            compat["ItemID"] = base_id
        else:
            iid = compat.get("ItemID")
            if not isinstance(iid, str) or not iid.strip():
                compat["ItemID"] = "compat"

        # 2. Force Name: Don't accidentally inherit the vanilla item's name
        base_name = self.index.display_name_for(base) if base else ""
        if not base_name and base: 
            base_name = get_display_name(base)
            
        nm = compat.get("Name")
        if template and nm == template.get("Name") and base_name:
            compat["Name"] = base_name
        elif not isinstance(nm, str) or not nm.strip():
            compat["Name"] = base_name or compat.get("ItemID")

        # 3. Handle Types
        t = compat.get("$type")
        bucket = guess_type_bucket(compat, base or {}, template)
        
        if not isinstance(t, str) or not t.strip() or ", RealismMod" not in t:
            if not bucket and hasattr(self, "cb_category"):
                cat = self.cb_category.currentText().strip()
                if cat in["AssaultRifles", "Pistol", "SMGs", "Shotguns", "SniperRifles", "MarksmanRifles", "AssaultCarbines", "MachineGuns", "BoltActionRifles"]: bucket = "Gun"
                elif cat in["Armor", "ArmorVests", "ArmorPlates", "ArmorMasks", "Headset", "Headwear", "Vest", "Visor", "Backpack", "Backpacks", "GearComponents", "GearMods"]: bucket = "Gear"
                elif cat in["Ammo", "Rounds", "AmmoBoxes"]: bucket = "Ammo"
                elif cat and cat != "— select category —" and cat != "Unknown": bucket = "WeaponMod"
            if not bucket: bucket = "WeaponMod"
            compat["$type"] = f"RealismMod.{bucket}, RealismMod"

        if bucket == "WeaponMod" and "ModType" not in compat:
            compat["ModType"] = ""
        if bucket == "Gun":
            if "WeapType" not in compat: compat["WeapType"] = ""
            if "OperationType" not in compat: compat["OperationType"] = ""

        return compat

    def _record_id(self, rec) -> str:
        if not isinstance(rec, dict): return ""
        return str(rec.get("newId") or rec.get("_guid") or rec.get("id") or rec.get("_id") or "")

    def _find_base_by_id(self, item_id: str):
        if not item_id: return None
        for rec in self.index.items:
            if self._record_id(rec) == str(item_id):
                return rec
        return None

    def _push_queue(self, compat: dict, base: dict):
        """Add/replace one queue entry, keyed on ItemID."""
        compat = self._ensure_identity_fields(base or {}, compat, None)
        compat = reorder_fields(compat)
        item_id = str(compat.get("ItemID"))
        self.export_queue = [x for x in getattr(self, "export_queue", [])
                             if str(x[0].get("ItemID")) != item_id]
        self.export_queue.append((compat, base))
        return compat

    def _current_compat_and_base(self):
        """The compat currently in the editor, plus the mod record it belongs to."""
        if not self.compat_forms: return None, None
        compat = self.compat_forms[0].value()
        iid = str(compat.get("ItemID") or compat.get("_guid") or "")
        return compat, self._find_base_by_id(iid)

    def queue_current_compat(self):
        compat, base = self._current_compat_and_base()
        if compat is None: return
        compat = self._push_queue(compat, base)
        self._refresh_queue_view()
        QMessageBox.information(self, "Queued",
                                f"Queued compat: {compat.get('Name')} [{compat.get('ItemID')}]")

    def queue_current_with_clones(self):
        """Queue the current compat, then queue identical copies against any
        number of other items — same stats, their own ItemID and Name."""
        compat, base = self._current_compat_and_base()
        if compat is None:
            QMessageBox.information(self, "Clone", "Build a compat first.")
            return

        source = self._push_queue(dict(compat), base)
        source_id = str(source.get("ItemID"))

        entries = []
        for rec in self.index.items:
            iid = self._record_id(rec)
            if not iid or iid == source_id: continue
            entries.append((rec, iid, self.index.display_name_for(rec), rec.get("_mod", "") or "(External)"))
        entries.sort(key=lambda e: (e[3].lower(), e[2].lower()))

        if not entries:
            QMessageBox.information(self, "Clone", "No other mod items available to clone onto.")
            self._refresh_queue_view()
            return

        dlg = CloneTargetDialog(self, entries, source_label=f"{source.get('Name')} [{source_id}]")
        if dlg.exec_() != QDialog.Accepted:
            self._refresh_queue_view()
            return

        targets = dlg.chosen()
        made = 0
        for rec, iid, name in targets:
            clone = dict(source)
            # Identity is per-item; every other stat is carried over untouched.
            clone["ItemID"] = iid
            clone["Name"] = name or iid
            for k in ("_file", "_guid", "_mod"):
                clone.pop(k, None)
            self._push_queue(clone, rec)
            made += 1

        self._refresh_queue_view()
        QMessageBox.information(
            self, "Cloned",
            f"Queued {source.get('Name')} plus {made} clone{'s' if made != 1 else ''}.\n"
            f"Queue now holds {len(self.export_queue)} item(s)."
        )

    def _refresh_queue_view(self):
        if not hasattr(self, "queue_list"): return
        self.queue_list.clear()
        for compat, _base in getattr(self, "export_queue", []):
            it = QListWidgetItem(f"{compat.get('Name')}   [{compat.get('ItemID')}]")
            self.queue_list.addItem(it)
        if hasattr(self, "queue_box"):
            self.queue_box.setTitle(f"Export Queue ({len(getattr(self, 'export_queue', []))})")

    def _remove_selected_from_queue(self):
        rows = sorted((self.queue_list.row(i) for i in self.queue_list.selectedItems()), reverse=True)
        for r in rows:
            if 0 <= r < len(self.export_queue):
                self.export_queue.pop(r)
        self._refresh_queue_view()

    def _clear_queue(self):
        if not getattr(self, "export_queue", []): return
        if QMessageBox.question(self, "Clear queue", "Discard everything in the export queue?",
                                QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            self.export_queue.clear()
            self._refresh_queue_view()

    def _check_exportable(self, entries) -> bool:
        """Warn about fields the game can't read before anything hits disk.
        entries: list of (compat, bucket)."""
        dead, ranges = {}, []
        for compat, bucket in entries:
            for k in unreadable_fields(compat, bucket):
                dead.setdefault(k, set()).add(bucket)
            ranges += out_of_range_fields(compat, bucket)

        if not dead and not ranges:
            return True

        msg = ""
        if dead:
            lines = "".join(f"<li><b>{k}</b> — on {', '.join(sorted(v))}</li>"
                            for k, v in sorted(dead.items()))
            msg += ("<b>The server has no consumer for these fields:</b>"
                    f"<ul>{lines}</ul>")
        if ranges:
            msg += ("<b>Outside the range seen in the ammo dump</b> "
                    "<span style='color:#9aa0a6'>(advisory only \u2014 that dump predates "
                    ".50 BMG and .22 LR, so the extremes are not authoritative)</span>:<ul>"
                    + "".join(f"<li>{r}</li>" for r in sorted(set(ranges))) + "</ul>")
        msg += "<br>Export anyway?"

        box = QMessageBox(self)
        box.setWindowTitle("Export check")
        box.setTextFormat(Qt.RichText)
        box.setText(msg)
        box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        box.setDefaultButton(QMessageBox.Yes)
        return box.exec_() == QMessageBox.Yes

    def export_all_queued(self):
        q = getattr(self, "export_queue",[])
        if not q: return
        fname, _ = QFileDialog.getSaveFileName(self, "Export All", "", "JSON Files (*.json)")
        if not fname: return

        out_dict = {}
        for compat, base in q:
            compat = self._ensure_identity_fields(base or {}, compat)
            compat = reorder_fields(compat) 
            key = str(compat.get("ItemID"))
            out_dict[key] = compat

        if not self._check_exportable(
                [(c, guess_type_bucket(c, {}, None)) for c in out_dict.values()]):
            return

        with open(fname, "w", encoding="utf-8") as f:
            json.dump(out_dict, f, indent=4, ensure_ascii=False)
        QMessageBox.information(self, "Exported", f"Exported {len(out_dict)} items.")
        self.export_queue.clear()
        self._refresh_queue_view()

    def _handbook_parent_name(self, base: dict) -> str:
        def norm(cat: str) -> str:
            if not isinstance(cat, str) or not cat.strip(): return ""
            cat = cat.strip()
            if formulas_mod and hasattr(formulas_mod, "CATEGORY_ALIASES"):
                return formulas_mod.CATEGORY_ALIASES.get(cat, cat)
            return cat

        # weapClass is authoritative for guns and sidesteps the handbook tree
        # entirely, so try it before anything else.
        wc = weapclass_category(base)
        if not wc:
            _, cloned = self._base_tpl_and_record(base)
            wc = weapclass_category(cloned or {})
        if wc: return wc

        # Collect every candidate the chain offers, then prefer one that
        # actually has a formula behind it rather than returning the first hit.
        found = []

        def offer(raw):
            n = norm(raw)
            if n and n not in found: found.append(n)

        current = base
        for _ in range(12):
            if not isinstance(current, dict): break

            if formulas_mod and hasattr(formulas_mod, "PARENT_CLASSES"):
                pc = formulas_mod.PARENT_CLASSES
                for hb_key in ("handbookParentId",):
                    v = current.get(hb_key)
                    if isinstance(v, str) and v.strip(): offer(pc.get(v.strip(), ""))

                hb = current.get("handbook") or current.get("Handbook")
                if isinstance(hb, dict):
                    hpid = hb.get("ParentId") or hb.get("parentId")
                    if isinstance(hpid, str) and hpid.strip(): offer(pc.get(hpid.strip(), ""))

            pid = (current.get("_parent") or current.get("parent")
                   or current.get("Parent") or current.get("parentId"))

            if not pid:
                tpl = (current.get("itemTplToClone") or current.get("clone")
                       or current.get("tpl") or current.get("_tpl"))
                if tpl:
                    current = self.base_db.by_id.get(tpl)
                    continue
                break

            if isinstance(pid, str) and re.fullmatch(r"[0-9a-fA-F]{24}", pid):
                if formulas_mod and hasattr(formulas_mod, "PARENT_CLASSES"):
                    offer(formulas_mod.PARENT_CLASSES.get(pid, ""))
                nxt = self.base_db.by_id.get(pid)
                if nxt is None:
                    # Handbook node IDs aren't in the item DB, so the walk dead-ends
                    # here. Fall back to the item this one was cloned from.
                    tpl = (current.get("itemTplToClone") or current.get("clone")
                           or current.get("tpl") or current.get("_tpl"))
                    nxt = self.base_db.by_id.get(tpl) if tpl else None
                current = nxt
                if current is None: break
                continue
            else:
                offer(pid)
                break

        for cand in found:
            if resolve_formula_func(cand): return cand

        for key in ("parentClass", "ParentClass", "$type"):
            val = base.get(key)
            if isinstance(val, str) and val.strip():
                n = norm(val)
                if resolve_formula_func(n): return n
                if n and not found: found.append(n)

        return found[0] if found else "Unknown"

    def render_realism_panel(self, base):
        self.realism_header.setText(self._mk_header("Realism stats of cloned item"))
        rec, key_used = self._find_realism_record_for_base(base)
        if not isinstance(rec, dict):
            self._realism_stats_data = {}
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
        self._realism_stats_data = stats
        self.realism_stats.setText(
            self._pretty_stats("", stats, highlight=getattr(self, "_hover_key", None))
            if stats else "<i>No stats found</i>"
        )

    def _resolve_parent_category_name(self, base: dict, template: dict | None) -> str:
        return self._handbook_parent_name(base)

    def _pick_formula_category(self, base: dict, template: dict | None) -> str:
        def norm(cat: str) -> str:
            if not isinstance(cat, str): return ""
            cat = cat.strip()
            if formulas_mod and hasattr(formulas_mod, "CATEGORY_ALIASES"):
                aliased = formulas_mod.CATEGORY_ALIASES.get(cat)
                if aliased: return aliased
            if not resolve_formula_func(cat):
                alt = RUNTIME_CATEGORY_ALIASES.get(cat)
                if alt and resolve_formula_func(alt): return alt
            return cat

        # Ammo routes to a calibre-specific built-in rather than a class name.
        if guess_type_bucket(template or {}, base, template) == "Ammo":
            return AMMO_CATEGORY

        hb = self._handbook_parent_name(base)

        # Muzzle devices: the handbook only says "Muzzle", but the emitter trains
        # Suppressors / MuzzleBrakes / FlashHiders / MuzzleAdapters separately.
        # Resolve the specific one and use it when it has a model; otherwise fall
        # through and let CATEGORY_ALIASES route it to MuzzleBrakes as before.
        if hb in MUZZLE_FAMILY or muzzle_subcategory(base):
            sub_cat = muzzle_subcategory(base)
            if not sub_cat:
                _, cloned = self._base_tpl_and_record(base)
                sub_cat = muzzle_subcategory(cloned or {})
            if sub_cat and resolve_formula_func(sub_cat):
                return sub_cat

        if hb and hb != "Unknown" and resolve_formula_func(norm(hb)): return norm(hb)

        wc = weapclass_category(base)
        if not wc:
            _, cloned = self._base_tpl_and_record(base)
            wc = weapclass_category(cloned or {})
        if wc and resolve_formula_func(wc): return wc

        pid = base.get("parent") or base.get("Parent") or base.get("parentId") or base.get("_parent")
        if pid == "5b5f701386f774093f2ecf0f": return "ArmorPlates"
        if pid == "5a341c4b86f77401e2507e28": return "ArmorMasks"

        for src in (template, base):
            if isinstance(src, dict):
                mt = src.get("ModType")
                if isinstance(mt, str) and mt.strip() and resolve_formula_func(norm(mt)): return norm(mt)

        for key in ("parentClass", "ParentClass", "$type", "parent"):
            val = base.get(key)
            if isinstance(val, str) and val.strip() and resolve_formula_func(norm(val)): return norm(val)

        return ""
    
    def _find_realism_record_for_base(self, base: dict):
        candidates =[]
        for key in ("itemTplToClone","itemtpltoclone","clone","tpl","_tpl","id","_id","_guid"):
            v = base.get(key)
            if isinstance(v, str) and v.strip(): candidates.append(v.strip())

        t = getattr(self, "_current_template", None)
        if isinstance(t, dict):
            for key in ("ItemID","ItemId","ID","id","_id","_guid","tpl","_tpl"):
                v = t.get(key)
                if isinstance(v, str) and v.strip(): candidates.append(v.strip())

        seen, uniq = set(),[]
        for c in candidates:
            if c not in seen:
                uniq.append(c); seen.add(c)

        for c in uniq:
            rec = self.realism_db.by_id.get(c)
            if isinstance(rec, dict): return rec, c
        return None, None

    def render_realism_inline(self, base):
        self.realism_inline_header.setText("<hr style='margin:8px 0'>" + self._mk_header("Realism stats (by clone/tpl)"))
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
        self.realism_inline_stats.setText(self._pretty_stats("", stats) if stats else "<i>No stats found</i>")

    def ensure_spt_path(self):
        spt = self.settings.value("spt_path", "")
        if not spt or not os.path.isdir(spt):
            spt = ask_for_folder("Select your SPT install folder")
            if not spt:
                QMessageBox.critical(self, "Required", "SPT install folder is required.")
                sys.exit(1)
        self.settings.setValue("spt_path", spt)
        return spt

    def _mk_header(self, text: str) -> str:
        return f"<div style='font-size:18px;font-weight:700;margin:4px 0 6px 0;text-align:center'>{text}</div>"

    def _mk_stacked_header(self, pieces: list) -> str:
        lines =[]
        for label, value in pieces:
            if value: lines.append(f"<b>{label}</b>: {value}")
        return "<div style='margin:4px 0;text-align:left'>" + "<br>".join(lines) + "</div>"
    
    def is_reskin_compat(self, rec):
        if not isinstance(rec, dict): return False
        keys = set(rec.keys())
        template_keys =[k for k in keys if k.lower().startswith("templateid")]
        expected_keys = {"$type", "ItemID", "Name"}
        if len(keys) == 4 and expected_keys.issubset(keys) and template_keys: return True
        return False

    def init_ui(self):
        root = QHBoxLayout(self)

        self.tabs = QTabWidget(self)
        root.addWidget(self.tabs, 3)
        self.tabs.currentChanged.connect(self._on_tab_changed)

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

        midright = QHBoxLayout()

        base_panel = QVBoxLayout()
        self.base_header = QLabel(self._mk_header("Base Game (merged view)"))
        self.base_header.setTextFormat(Qt.RichText)
        self.base_header.setWordWrap(True)
        base_panel.addWidget(self.base_header)

        self.base_sub = QLabel("—")
        self.base_sub.setTextFormat(Qt.RichText)
        self.base_sub.setAlignment(Qt.AlignLeft)
        base_panel.addWidget(self.base_sub)

        self.base_stats = QLabel("—")
        self.base_stats.setWordWrap(True)
        self.base_stats.setTextFormat(Qt.RichText)
        self.base_stats.setAlignment(Qt.AlignLeft)
        self.base_stats.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        base_panel.addWidget(self.base_stats, 1)

        base_scroll = QScrollArea(); base_scroll.setWidgetResizable(True)
        base_container = QWidget(); base_container.setLayout(base_panel)
        base_container.setMinimumWidth(320)
        base_scroll.setWidget(base_container)

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
        realism_container.setMinimumWidth(320)
        realism_scroll.setWidget(realism_container)

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
        self.cb_category.currentTextChanged.connect(self._on_category_dropdown_changed)
        row_cat.addWidget(self.cb_category)
        
        self.btn_reload_formulas = QPushButton("Reload formulas.py")
        self.btn_reload_formulas.clicked.connect(self.reload_formulas)
        row_cat.addWidget(self.btn_reload_formulas)
        right.addLayout(row_cat)

        self.row_preset = QHBoxLayout()
        self.lbl_preset = QLabel("ML Preset Override:")
        self.cb_preset = QComboBox()
        self.cb_preset.setEditable(True)
        self.cb_preset.addItems(self.BARREL_PRESETS)
        self.cb_preset.currentTextChanged.connect(self._on_preset_changed)
        self.row_preset.addWidget(self.lbl_preset)
        self.row_preset.addWidget(self.cb_preset)
        right.addLayout(self.row_preset)

        # --- ammo calculator inputs (only shown for "Ammo: ..." categories) ---
        self.grp_ammo = QGroupBox("Ammo Calculator")
        ammo_lay = QVBoxLayout(self.grp_ammo)

        r1 = QHBoxLayout()
        r1.addWidget(QLabel("Construction:"))
        self.cb_construction = QComboBox()
        self.cb_construction.addItems(list(AMMO_CONSTRUCTION.keys()))
        self.cb_construction.setToolTip(
            "Multipliers off the calibre's FMJ baseline, derived from Realism's own ammo data.\n"
            "AP raises penetration and durability burn; subsonic drops penetration sharply.")
        r1.addWidget(self.cb_construction, 1)
        ammo_lay.addLayout(r1)

        r2 = QHBoxLayout()
        self.sp_bullet_mass = QDoubleSpinBox()
        self.sp_bullet_mass.setDecimals(2); self.sp_bullet_mass.setRange(0.0, 200.0)
        self.sp_bullet_mass.setSingleStep(0.1); self.sp_bullet_mass.setSuffix(" g")
        self.sp_bullet_mass.setToolTip("Projectile mass. Feeds KE = 0.5 * mass * velocity^2 / 1000.\n"
                                       "0 = use the calibre's baseline load.")
        r2.addWidget(QLabel("Bullet mass:")); r2.addWidget(self.sp_bullet_mass, 1)

        self.sp_velocity = QDoubleSpinBox()
        self.sp_velocity.setDecimals(1); self.sp_velocity.setRange(0.0, 2000.0)
        self.sp_velocity.setSingleStep(5.0); self.sp_velocity.setSuffix(" m/s")
        self.sp_velocity.setToolTip("Muzzle velocity. Squared in the KE term, so it dominates.\n"
                                    "0 = use the calibre's baseline load.")
        r2.addWidget(QLabel("Velocity:")); r2.addWidget(self.sp_velocity, 1)

        self.sp_diameter = QDoubleSpinBox()
        self.sp_diameter.setDecimals(2); self.sp_diameter.setRange(0.0, 40.0)
        self.sp_diameter.setSingleStep(0.1); self.sp_diameter.setSuffix(" mm")
        self.sp_diameter.setToolTip("Projectile diameter, for sectional density.\n"
                                    "0 = use the calibre's standard bore.")
        r2.addWidget(QLabel("Diameter:")); r2.addWidget(self.sp_diameter, 1)
        ammo_lay.addLayout(r2)

        r3 = QHBoxLayout()
        self.lbl_ammo_ke = QLabel("—")
        self.lbl_ammo_ke.setStyleSheet("color:#9aa0a6")
        r3.addWidget(self.lbl_ammo_ke, 1)
        self.btn_ammo_calc = QPushButton("Calculate Ammo Stats")
        self.btn_ammo_calc.setToolTip("Recompute the compat from these inputs.\n"
                                      "Fields you have already set by hand are left alone.")
        self.btn_ammo_calc.clicked.connect(self.recompute_current)
        r3.addWidget(self.btn_ammo_calc)
        ammo_lay.addLayout(r3)

        for w in (self.cb_construction,):
            w.currentTextChanged.connect(self._on_ammo_input_changed)
        for w in (self.sp_bullet_mass, self.sp_velocity, self.sp_diameter):
            w.valueChanged.connect(self._on_ammo_input_changed)

        right.addWidget(self.grp_ammo)
        self.grp_ammo.hide()

        self._toggle_presets_visibility()

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
        
        self.btn_export_one = QPushButton("Queue This")
        self.btn_export_one.clicked.connect(self.queue_current_compat)
        export_row.addWidget(self.btn_export_one)

        self.btn_queue_clone = QPushButton("Queue + Clone To…")
        self.btn_queue_clone.setToolTip(
            "Queue this compat, then copy the same stats onto any number of other\n"
            "items. Each clone keeps its own ItemID and Name."
        )
        self.btn_queue_clone.clicked.connect(self.queue_current_with_clones)
        export_row.addWidget(self.btn_queue_clone)

        self.btn_export_all = QPushButton("Export All Queued")
        self.btn_export_all.clicked.connect(self.export_all_queued)
        export_row.addWidget(self.btn_export_all)

        right.addLayout(export_row)

        self.queue_box = QGroupBox("Export Queue (0)")
        qlay = QVBoxLayout(self.queue_box)
        self.queue_list = QListWidget()
        self.queue_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.queue_list.setMaximumHeight(150)
        qlay.addWidget(self.queue_list)

        qrow = QHBoxLayout()
        self.btn_queue_remove = QPushButton("Remove Selected")
        self.btn_queue_remove.clicked.connect(self._remove_selected_from_queue)
        qrow.addWidget(self.btn_queue_remove)
        self.btn_queue_clear = QPushButton("Clear Queue")
        self.btn_queue_clear.clicked.connect(self._clear_queue)
        qrow.addWidget(self.btn_queue_clear)
        qlay.addLayout(qrow)

        right.addWidget(self.queue_box)

        legend = QLabel(
            f"<span style='color:{COLOR_BETTER}'>■ better</span> &nbsp; "
            f"<span style='color:{COLOR_BETTER_SLIGHT}'>■ slightly better</span> &nbsp; "
            f"<span style='color:{COLOR_EQUAL}'>■ equal</span> &nbsp; "
            f"<span style='color:{COLOR_WORSE_SLIGHT}'>■ slightly worse</span> &nbsp; "
            f"<span style='color:{COLOR_WORSE}'>■ worse</span> &nbsp; "
            f"<span style='color:{COLOR_NONE}'>■ no baseline</span><br>"
            f"<span style='color:#9aa0a6'>vs the cloned item; within "
            f"{int(SLIGHT_THRESHOLD*100)}% counts as slight. "
            "Hover a field for its description and to highlight it in the panels.</span>"
        )
        legend.setTextFormat(Qt.RichText)
        legend.setWordWrap(True)
        right.addWidget(legend)

        right_scroll = QScrollArea(); right_scroll.setWidgetResizable(True)
        right_container = QWidget(); right_container.setLayout(right)
        right_scroll.setWidget(right_container)

        midright.addWidget(base_scroll, 3)
        midright.addWidget(realism_scroll, 3)
        midright.addWidget(right_scroll, 5)

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

        self._on_tab_changed(self.tabs.currentIndex())

    def _toggle_presets_visibility(self):
        cat = self.cb_category.currentText()
        self.cb_preset.blockSignals(True)
        self.cb_preset.clear()
        
        if cat in["Barrel", "Barrels"]:
            self.cb_preset.addItems(self.BARREL_PRESETS)
            self.lbl_preset.show()
            self.cb_preset.show()
        elif cat in["Muzzle", "Suppressors", "MuzzleBrakes", "FlashHiders", "MuzzleAdapters"]:
            self.cb_preset.addItems(self.MUZZLE_PRESETS)
            self.lbl_preset.show()
            self.cb_preset.show()
        elif cat in["StocksChassis", "Stock", "Stocks"]:
            self.cb_preset.addItems(self.STOCK_PRESETS)
            self.lbl_preset.show()
            self.cb_preset.show()
        elif cat in["Handguard", "Handguards"]:
            self.cb_preset.addItems(self.HANDGUARD_PRESETS)
            self.lbl_preset.show()
            self.cb_preset.show()
        elif cat in["Sights", "IronSights", "Optics", "Collimators", "AssaultScopes", "CompactCollimators"]:
            self.cb_preset.addItems(self.SIGHT_PRESETS)
            self.lbl_preset.show()
            self.cb_preset.show()
        elif cat in["Ammo", "Rounds"]:
            self.cb_preset.addItems(self.AMMO_PRESETS)
            self.lbl_preset.show()
            self.cb_preset.show()
        else:
            self.cb_preset.addItems(["Select Formula Profile..."] + self.BARREL_PRESETS[1:20])
            self.lbl_preset.show()
            self.cb_preset.show()
            
        self.cb_preset.blockSignals(False)

    def _on_category_dropdown_changed(self, text):
        self._toggle_presets_visibility()
        self._toggle_ammo_panel()

    def _toggle_ammo_panel(self):
        if not hasattr(self, "grp_ammo"): return
        cat = self.cb_category.currentText().strip()
        is_ammo = cat in (AMMO_CATEGORY, "Rounds")
        self.grp_ammo.setVisible(is_ammo)
        if is_ammo:
            cal = self._selected_calibre()
            self.grp_ammo.setTitle(
                f"Ammo Calculator \u2014 {cal}" if cal
                else "Ammo Calculator \u2014 pick a calibre in ML Preset Override")
            self._update_ammo_readout()

    def _on_ammo_input_changed(self, *_):
        self._update_ammo_readout()

    def _update_ammo_readout(self):
        if not hasattr(self, "lbl_ammo_ke"): return
        cal = self._selected_calibre()
        if not cal:
            self.lbl_ammo_ke.setText(
                "Pick a calibre in ML Preset Override to calculate."); return
        prof = AMMO_CALIBRE_PROFILES.get(cal, {})
        m = self.sp_bullet_mass.value() or prof.get("mass", 0)
        v = self.sp_velocity.value() or prof.get("vel", 0)
        ke = ammo_kinetic_energy(m, v)
        base_ke = ammo_kinetic_energy(prof.get("mass", 0), prof.get("vel", 0))
        ratio = (ke / base_ke) if base_ke else 1.0
        self.lbl_ammo_ke.setText(
            f"{m:g} g @ {v:g} m/s \u2192 KE {ke:,.0f} J "
            f"({ratio:.2f}\u00d7 the {cal} baseline)")

    def _on_preset_changed(self, _text=""):
        # The calibre lives here for Ammo, so the panel has to follow it.
        self._toggle_ammo_panel()

    def _selected_calibre(self) -> str:
        """Calibre chosen in ML Preset Override, if it names a real profile."""
        if not hasattr(self, "cb_preset"): return ""
        txt = self.cb_preset.currentText().strip()
        return txt if txt in AMMO_CALIBRE_PROFILES else ""

    def _ammo_context(self) -> dict:
        """Calculator inputs handed to the ammo formula. 0 means 'use baseline'."""
        if not hasattr(self, "cb_construction"): return {}
        ctx = {"construction": self.cb_construction.currentText()}
        cal = self._selected_calibre()
        if cal: ctx["calibre"] = cal
        for key, w in (("BulletMassGram", self.sp_bullet_mass),
                       ("InitialSpeed", self.sp_velocity),
                       ("BulletDiameterMilimeters", self.sp_diameter)):
            if w.value(): ctx[key] = w.value()
        return ctx

    def _ammo_seed_value(self, base: dict, key: str):
        """Find an ammo physical property on the mod, in priority order.

        A custom round almost always declares its ballistics in
        overrideProperties rather than a full _props block, and may declare
        nothing at all and rely on the cloned base item. Reading only _props (the
        old behaviour) meant the calculator opened on zeros and silently fell
        back to the calibre baseline, so a 9.5 g subsonic load was costed as a
        standard 7.9 g one.
        """
        if not isinstance(base, dict):
            return None

        def _num(v):
            if isinstance(v, (int, float)) and not isinstance(v, bool) and v > 0:
                return float(v)
            return None

        # 1) the mod's own explicit override
        for holder in (base.get("overrideProperties"), base.get("_overrideProperties")):
            if isinstance(holder, dict):
                got = _num(holder.get(key))
                if got is not None:
                    return got
        # 2) the mod's own _props / top level
        got = _num((get_base_props_dict(base) or {}).get(key))
        if got is not None:
            return got
        got = _num(base.get(key))
        if got is not None:
            return got
        # 3) whatever it clones from
        try:
            _tpl, cloned = self._base_tpl_and_record(base)
        except Exception:
            cloned = None
        if isinstance(cloned, dict):
            for holder in (cloned.get("overrideProperties"),
                           get_base_props_dict(cloned) or {}, cloned):
                if isinstance(holder, dict):
                    got = _num(holder.get(key))
                    if got is not None:
                        return got
        return None

    def _seed_ammo_inputs(self, base: dict):
        """Prefill from the base item so the panel opens on real numbers."""
        if not hasattr(self, "sp_bullet_mass") or not isinstance(base, dict): return
        cal = ammo_calibre_for_base(base)
        if cal and hasattr(self, "cb_preset"):
            self.cb_preset.blockSignals(True)
            if self.cb_preset.findText(cal) < 0: self.cb_preset.addItem(cal)
            self.cb_preset.setCurrentText(cal)
            self.cb_preset.blockSignals(False)

        # Mass -> BulletMassGram, velocity -> InitialSpeed,
        # diameter -> BulletDiameterMilimeters, each resolved through
        # overrideProperties -> _props -> cloned base.
        for key, w in (("BulletMassGram", self.sp_bullet_mass),
                       ("InitialSpeed", self.sp_velocity),
                       ("BulletDiameterMilimeters", self.sp_diameter)):
            v = self._ammo_seed_value(base, key)
            w.blockSignals(True)
            w.setValue(float(v) if v is not None else 0.0)
            w.blockSignals(False)
        self._update_ammo_readout()

    def populate_items_tree(self):
        self.item_tree.clear()
        if not hasattr(self, "search"): return

        ut_ids = set(self.user_templates.by_id.keys()) if hasattr(self, "user_templates") else set()
        q = (self.search.text() or "").lower().strip()

        for mod_name in sorted(self.index.items_by_mod.keys(), key=lambda s: s.lower()):
            records = self.index.items_by_mod[mod_name]
            filtered =[]
            for rec in records:
                name = self.index.display_name_for(rec)
                typ  = (rec.get("$type") or rec.get("parentClass") or rec.get("parent") or "").strip()
                idv  = rec.get("newId") or rec.get("_guid") or rec.get("id") or rec.get("_id") or ""
                label = f"{name} [{typ}]" if typ else name
                if not q or q in label.lower() or (idv and q in str(idv).lower()) or q in mod_name.lower():
                    filtered.append(rec)

            if not filtered: continue
            mod_item = QTreeWidgetItem([f"{mod_name}  ({len(filtered)}/{len(records)})"])
            mod_item.setExpanded(False)
            self.item_tree.addTopLevelItem(mod_item)

            for rec in sorted(filtered, key=lambda r: self.index.display_name_for(r).lower()):
                name = self.index.display_name_for(rec)
                child = QTreeWidgetItem([name])
                child.setData(0, Qt.UserRole, rec)

                iid = str(rec.get("newId") or rec.get("_guid") or rec.get("id") or rec.get("_id") or "")
                if iid and iid in ut_ids:
                    child.setBackground(0, QColor(30, 90, 30))  
                    child.setForeground(0, QColor(230, 255, 230))
                else:
                    child.setBackground(0, QColor(110, 110, 30)) 
                    child.setForeground(0, QColor(255, 255, 230))

                mod_item.addChild(child)

        if q: self.item_tree.expandAll()
        else: self.item_tree.collapseAll()

    def populate_user_templates_tree(self):
        self.user_template_tree.clear()
        if not hasattr(self, "search_ut"): return

        q = (self.search_ut.text() or "").lower().strip()

        for filepath in sorted(self.user_templates.by_file.keys(), key=lambda s: s.lower()):
            records = self.user_templates.by_file[filepath]
            filtered =[]
            for rec in records:
                name = rec.get("Name") or rec.get("shortName") or "Unknown"
                iid = str(rec.get("ItemID") or rec.get("_guid") or "")
                
                label = f"{name}[{iid}]"
                if not q or q in label.lower() or q in os.path.basename(filepath).lower():
                    filtered.append(rec)

            if not filtered: continue
            
            file_basename = os.path.basename(filepath)
            file_item = QTreeWidgetItem([f"{file_basename}  ({len(filtered)}/{len(records)})"])
            file_item.setExpanded(False)
            self.user_template_tree.addTopLevelItem(file_item)

            for rec in sorted(filtered, key=lambda r: str(r.get("Name") or "").lower()):
                name = rec.get("Name") or rec.get("shortName") or "Unknown"
                
                child = QTreeWidgetItem([name])
                child.setData(0, Qt.UserRole, rec)

                child.setBackground(0, QColor(30, 60, 90))  
                child.setForeground(0, QColor(230, 240, 255))

                file_item.addChild(child)

        if q: self.user_template_tree.expandAll()
        else: self.user_template_tree.collapseAll()

    def on_user_template_selected(self):
        sel_items = self.user_template_tree.selectedItems()
        if not sel_items: return
        tmpl = sel_items[0].data(0, Qt.UserRole)
        if not isinstance(tmpl, dict): return

        base = None
        iid = str(tmpl.get("ItemID") or tmpl.get("_guid") or "")
        if iid:
            for rec in self.index.items:
                for key in ("newId","_guid","id","_id"):
                    if str(rec.get(key) or "") == iid:
                        base = rec; break
                if base: break

        self._current_template = tmpl
        self.lbl_parent_cat.setText(f"<b>Parent</b>: {tmpl.get('parent') or '—'}")
        self.lbl_type.setText(f"<b>$type</b>: {tmpl.get('$type') or '—'}")

        detected = self._pick_formula_category(base or {}, tmpl)
        self.cb_category.blockSignals(True)
        self.cb_category.clear()
        self.cb_category.addItem("— select category —")
        cats = set()
        if formulas_mod:
            for map_name in ("gun_formula_map","mod_formula_map",
                             "gear_formula_map","ammo_formula_map"):
                m = getattr(formulas_mod, map_name, None)
                if isinstance(m, dict):
                    cats.update(k for k in m.keys() if isinstance(k, str))
        # ammo_formula_map ships empty, so the built-ins are what actually
        # populate the Ammo side of the dropdown.
        cats.update(ammo_formula_categories())
        if detected and callable(resolve_formula_func(detected)):
            self.cb_category.addItem(detected)
            self.cb_category.setCurrentText(detected)
        for c in sorted(cats):
            if c != detected:
                self.cb_category.addItem(c)
        if not (detected and callable(resolve_formula_func(detected))):
            self.cb_category.setCurrentIndex(0)
        self.cb_category.blockSignals(False)
        self._toggle_ammo_panel()
        self._toggle_presets_visibility()

        if base:
            self.render_basegame_stats(base)     
            self.render_realism_panel(base)      
        else:
            self._basegame_stats_data = {}
            self._realism_stats_data = {}
            self.base_header.setText(self._mk_header("No matching base item"))
            self.base_sub.setText("—"); self.base_stats.setText("—")
            self.realism_header.setText(self._mk_header("Realism stats")); self.realism_sub.setText("—"); self.realism_stats.setText("—")

        ctype = guess_type_bucket(tmpl, base or {}, tmpl)
        allowed = set()
        if ctype == "Gun": allowed = set(CANONICAL_ORDER.get("Gun",[]))
        elif ctype == "Gear": allowed = set(CANONICAL_ORDER.get("Gear",[]))
        elif ctype == "Ammo": allowed = set(CANONICAL_ORDER.get("Ammo",[]))
        else: allowed = set(CANONICAL_ORDER.get("WeaponMod",[]))

        form = CompatForm(tmpl, editable=True, schema_for_type=allowed,
                          category=self.cb_category.currentText().strip())
        self._wire_form(form)

    def _on_tab_changed(self, idx: int):
        if idx == 1:
            if not getattr(self, "user_template_tree", None) or not self.user_template_tree.selectedItems():
                self.template_details.setText("<i>Select a user template…</i>")
                self.lbl_parent_cat.setText("<b>Parent</b>: —")
                self.lbl_type.setText("<b>$type</b>: —")
                self.base_header.setText(self._mk_header("Base Game (merged view)"))
                self.base_sub.setText("—")
                self.base_stats.setText("—")
                self.realism_header.setText(self._mk_header("Realism stats (by clone/tpl)"))
                self.realism_sub.setText("—")
                self.realism_stats.setText("—")
                self._basegame_stats_data = {}
                self._realism_stats_data = {}
                self._hover_key = None
                self.compat_forms = []
                self.compat_area.setWidget(QWidget())

    def reload_formulas(self):
        ok, err = safe_load_formulas()
        if not ok:
            QMessageBox.critical(self, "Reload failed", err)
            return

        self.populate_items_tree()
        sel_items = self.item_tree.selectedItems()
        if sel_items:
            rec = sel_items[0].data(0, Qt.UserRole)
            if isinstance(rec, dict):
                self.render_base(rec)
        QMessageBox.information(self, "Formulas reloaded", "formulas.py reloaded successfully.")

    def guess_compat_root(self, spt_path):
        user_mods = os.path.join(spt_path, "user", "mods")
        candidates =[]
        if os.path.isdir(user_mods):
            for d in os.listdir(user_mods):
                p = os.path.join(user_mods, d)
                if not os.path.isdir(p): continue
                for sub in ("db", "database", ""):
                    test = os.path.join(p, sub)
                    if not os.path.isdir(test): continue
                    count = sum(1 for _ in iter_json_files(test))
                    if count > 100: candidates.append(test)
        candidates.sort(key=lambda x: (("realism" not in x.lower()), -sum(1 for _ in iter_json_files(x))))
        return candidates[0] if candidates else ""

    def change_paths(self):
        spt = ask_for_folder("Select your SPT install folder")
        if spt: self.settings.setValue("spt_path", spt)

        compat = ask_for_folder("Select your Realism compat templates root (optional)")
        if compat: self.settings.setValue("compat_root", compat)

        current = self.settings.value("exclude_patterns", "")
        new_patterns, ok = QInputDialog.getText(self, "Exclude Folders/Paths",
                                                "Comma- or semicolon-separated substrings to exclude\n(e.g. spt-realism,.git,__pycache__):",
                                                text=current)
        if ok: self.settings.setValue("exclude_patterns", new_patterns)

        self.spt_path = self.settings.value("spt_path", self.spt_path)
        self.compat_root = self.settings.value("compat_root", self.compat_root)
        self.exclude_contains = load_exclude_patterns(self.settings)
        self.index = SPTIndex(self.spt_path, self.compat_root, self.exclude_contains)
        self.index.scan()
        self.populate_items_tree()

    def _pretty_stats(self, title, stats_dict, highlight=None):
        if not stats_dict: return f"<i>No stats found</i>"

        hl = set()
        if highlight:
            hl.add(str(highlight).lower())
            for alias in COMPARE_ALIASES.get(highlight, ()):
                hl.add(alias.lower())

        sorted_keys = sorted(stats_dict.keys(), key=lambda k: k.lower())

        lines = []
        for k in sorted_keys:
            row = f"<b>{k}</b>: {stats_dict[k]}"
            if k.lower() in hl:
                row = ("<span style='background-color:#3A71C1;color:#FFFFFF;"
                       "padding:1px 3px;border-radius:2px'>" + row + "</span>")
            lines.append(row)
        return "<br>".join(lines)

    def _on_compat_hover(self, key: str):
        """Highlight the hovered creation-side field in the comparison panels."""
        self._hover_key = key or None
        realism = getattr(self, "_realism_stats_data", {}) or {}
        basegame = getattr(self, "_basegame_stats_data", {}) or {}
        if realism:
            self.realism_stats.setText(self._pretty_stats("", realism, highlight=self._hover_key))
        if basegame:
            self.base_stats.setText(self._pretty_stats("", basegame, highlight=self._hover_key))

    def _apply_form_comparison(self):
        """Feed the cloned item's stats into the form so values colour themselves."""
        baseline = dict(getattr(self, "_realism_stats_data", {}) or {})
        # Fall back to the raw base-game props for anything realism doesn't define.
        for k, v in (getattr(self, "_basegame_stats_data", {}) or {}).items():
            baseline.setdefault(k, v)
        for form in (self.compat_forms or []):
            try:
                form.set_comparison_baseline(baseline)
            except Exception:
                pass

    def _wire_form(self, form):
        """Common hookup for a freshly created CompatForm."""
        try:
            form.hoverKeyChanged.connect(self._on_compat_hover)
        except Exception:
            pass
        self.compat_area.setWidget(form)
        self.compat_forms = [form]
        self._apply_form_comparison()
        return form

    def _extract_basegame_stats(self, rec: dict) -> dict:
        if not isinstance(rec, dict): return {}
        out = {}
        props_view = {}
        base_props = rec.get("_props", {})
        if isinstance(base_props, dict): props_view.update(base_props)

        ov = rec.get("overrideProperties", {})
        if isinstance(ov, dict):
            for k, v in ov.items():
                if isinstance(v, (int, float, bool, str)):
                    props_view[k] = v

        for k, v in props_view.items():
            if k in BASE_HIDE_KEYS or is_banned(k): continue
            if isinstance(v, (int, float, bool, str)): out[k] = v
            
        for k in ("Weight", "Ergonomics", "RecoilForceUp", "RecoilForceBack", "RecoilAngle",
                "DeviationMax", "CenterOfImpact", "Velocity", "Damage", "PenetrationPower"):
            if k in rec and k not in out and isinstance(rec[k], (int, float, bool, str)):
                out[k] = rec[k]

        if "RecoilForceUp" in out and "RecoilVertical" not in out:
            out["RecoilVertical"] = out["RecoilForceUp"]

        return out

    def _extract_realism_stats(self, rec: dict) -> dict:
        if not isinstance(rec, dict): return {}
        out = {}
        skip = {"$type", "ItemID", "ItemId", "ID", "id", "_id", "_guid", "_file", "Name"}
        for k, v in rec.items():
            if k in skip or is_banned(k): continue
            if isinstance(v, (int, float, bool, str)): out[k] = v
            elif isinstance(v, list):
                if len(v) <= 12: out[k] = ", ".join(str(x) for x in v)
        return out
    
    def render_basegame_stats(self, base):
        item_name = self.index.display_name_for(base)
        mod_name  = base.get("_mod", "") or "(External)"
        guid      = str(base.get("_guid") or base.get("id") or base.get("_id") or "")
        self.base_header.setText(self._mk_header(f"{mod_name} — Mod stats"))
        self.base_sub.setText(self._mk_stacked_header([
            ("Item", item_name),
            ("_guid", guid),
            ("ItemTplToClone", base.get("itemTplToClone") or base.get("clone") or "")
        ]))

        props_view = {}
        base_props = get_base_props_dict(base)  
        if isinstance(base_props, dict): props_view.update(base_props)

        ov = base.get("overrideProperties", {})
        if isinstance(ov, dict):
            for k, v in ov.items():
                if isinstance(v, (int, float, bool, str)):
                    props_view[k] = v

        out = {}
        for k, v in props_view.items():
            if k in BASE_HIDE_KEYS: continue
            if isinstance(v, (int, float, bool, str)): out[k] = v

        if isinstance(ov, dict):
            pref = ov.get("Prefab")
            if isinstance(pref, dict) and "path" in pref and "PrefabPath" not in ov:
                out.setdefault("PrefabPath", pref["path"])

        self._basegame_stats_data = out
        self.base_stats.setText(
            self._pretty_stats("", out, highlight=getattr(self, "_hover_key", None))
            if out else "<i>No mod stats found</i>"
        )

    def _apply_realism_passthrough(self, compat: dict, base: dict) -> dict:
        """Copy fields straight off the CLONED ITEM'S REALISM RECORD.

        These are values Realism overwrites wholesale, so the vanilla _props
        figure is the pre-Realism number and is simply wrong: a stock HK416A5
        ships DurabilityBurnRatio 1.15 in _props but Realism sets 0.18, and
        RecoilForceBack 316 against Realism's HorizontalRecoil 140.

        A recolour or backport that clones an existing weapon should inherit
        that weapon's Realism values verbatim. If no Realism record can be
        resolved for the clone source we leave the prediction alone rather
        than substituting a vanilla number.
        """
        if not isinstance(compat, dict) or not isinstance(base, dict): return compat

        rec, _key = self._find_realism_record_for_base(base)
        if not isinstance(rec, dict): return compat

        lower = {str(k).lower(): v for k, v in rec.items()}
        for key in REALISM_PASSTHROUGH:
            if key not in compat: continue
            v = rec.get(key, lower.get(key.lower()))
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                compat[key] = v
            elif isinstance(v, bool):
                compat[key] = v
        return compat

    RESCALED_BY_REALISM = ("DurabilityBurnRatio", "HeatFactorGun", "HeatFactorByShot",
                           "CoolFactorGun", "CoolFactorGunMods")

    def _fix_rescaled_fields(self, compat: dict, base: dict, bucket: str) -> dict:
        """Repair fields the generated formula copies straight out of _props.

        formulas.py still contains an emitted passthrough that reads these from
        the base item's props. Realism rescales all of them -- vanilla
        DurabilityBurnRatio 1.15 is Realism's 0.18, HeatFactorGun 1.0 is 0.2 --
        so a copied value is simply the wrong number. Where we can see the copy
        happening, substitute the median of that weapon class across Realism's
        own templates: a class-typical value, not a clone of one item.
        """
        if bucket != "Gun" or not isinstance(compat, dict): return compat
        props = get_base_props_dict(base) or {}
        ov = base.get("overrideProperties") if isinstance(base, dict) else None
        if isinstance(ov, dict):
            props = {**props, **{k: v for k, v in ov.items() if isinstance(v, (int, float))}}

        meds = self._realism_class_medians(base)
        for key in self.RESCALED_BY_REALISM:
            if key not in compat: continue
            vanilla = props.get(key)
            cur = compat.get(key)
            if not isinstance(vanilla, (int, float)) or isinstance(vanilla, bool): continue
            if not isinstance(cur, (int, float)) or isinstance(cur, bool): continue
            if abs(float(cur) - float(vanilla)) > 1e-6: continue   # genuinely predicted
            m = meds.get(key)
            if m is not None: compat[key] = m
        return compat

    def _realism_class_medians(self, base: dict) -> dict:
        """Median of each rescaled field across Realism guns of the same class."""
        cache = self.__dict__.get("_rclass_med_cache")
        if cache is None:
            cache = {}
            self.__dict__["_rclass_med_cache"] = cache
        cat = weapclass_category(base) or ""
        if not cat:
            _, cloned = self._base_tpl_and_record(base)
            cat = weapclass_category(cloned or {})
        if cat in cache: return cache[cat]

        vals = {k: [] for k in self.RESCALED_BY_REALISM}
        for rec in getattr(self.realism_db, "by_id", {}).values():
            if not isinstance(rec, dict): continue
            if "Gun" not in str(rec.get("$type", "")): continue
            b = self.base_db.by_id.get(str(rec.get("ItemID") or ""))
            if cat and b is not None and weapclass_category(b) != cat: continue
            for k in vals:
                v = rec.get(k)
                if isinstance(v, (int, float)) and not isinstance(v, bool): vals[k].append(float(v))
        import statistics as _st
        out = {k: round(_st.median(v), 3) for k, v in vals.items() if v}
        cache[cat] = out
        return out

    def _zero_gun_only_fields(self, compat: dict, bucket: str) -> dict:
        """Fields that only apply in narrow situations on a whole weapon.

        Velocity and WeapAccuracy are meaningful on attachments (a barrel
        really does change both) but on a gun they are situational, so a
        predicted value on every weapon is noise. Zero them for guns; leave
        attachments alone.
        """
        if bucket != "Gun" or not isinstance(compat, dict): return compat
        for key in ZERO_ON_GUNS:
            if key in compat: compat[key] = 0
        return compat

    def compute_compat(self, base, template):
        """Calculate a compat and apply the rounding rules. Snapping happens
        here and nowhere else, so anything you type by hand afterwards is
        exported exactly as entered."""
        out = self._compute_compat_raw(base, template)
        if isinstance(out, dict):
            _bucket = guess_type_bucket(out, base or {}, template)
            out = self._apply_realism_passthrough(out, base or {})
            out = self._fix_rescaled_fields(out, base or {}, _bucket)
            out = self._zero_gun_only_fields(out, _bucket)
            out = strip_add_only(out, guess_type_bucket(out, base or {}, template))
            out = snap_compat(out)
        return out

    def _compute_compat_raw(self, base, template):
        category = self.cb_category.currentText().strip() if hasattr(self, "cb_category") else self._pick_formula_category(base, template)
        
        if category == "— select category —":
            category = self._pick_formula_category(base, template)
            
        func = resolve_formula_func(category) if category else None
        
        if not callable(func):
            hb_cat = self._handbook_parent_name(base)  
            if hb_cat and hb_cat != category:
                alt = resolve_formula_func(hb_cat)
                if callable(alt):
                    category = hb_cat
                    func = alt
                    if hasattr(self, "cb_category"):
                        self.cb_category.blockSignals(True)
                        self.cb_category.setCurrentText(hb_cat)
                        self.cb_category.blockSignals(False)
        self._toggle_ammo_panel()

        context = {
            "spt_path": self.spt_path,
            "compat_root": self.compat_root,
            "index": self.index,
        }
        if category in (AMMO_CATEGORY, "Rounds"):
            context.update(self._ammo_context())
        
        clean_template = {}
        if template:
            ctype = guess_type_bucket(template, base or {}, template)
            allowed_keys = set(CANONICAL_ORDER.get(ctype if ctype in CANONICAL_ORDER else 'WeaponMod',[]))
            allowed_keys.update(['$type', 'ItemID', 'Name', 'ModType', 'WeapType', 'OperationType', 'TemplateType', 'ArmorClass', 'MaskToUse'])
            
            for k, v in template.items():
                if is_banned(k): continue
                if k in allowed_keys or k in KNOWN_BOOLS or str(k).startswith('_'):
                    clean_template[k] = v

        if callable(func):
            try:
                effective_base = self._build_effective_base_for_formula(base)
                
                if self.cb_preset.isVisible() and self.cb_preset.currentIndex() > 0:
                    effective_base["_preset_hint"] = self.cb_preset.currentText()
                    
                item_entry = dict(clean_template)
                out = call_formula(func, item_entry, effective_base, clean_template, context)
                
                if not isinstance(out, dict):
                    out = {"_formula_error": "Formula did not return a dict."}
                return self._ensure_identity_fields(base or {}, out, clean_template)
            except Exception as e:
                import traceback
                traceback.print_exc()
                minimal = self._fallback_merge(base, clean_template)
                minimal["_formula_error"] = f"{type(e).__name__}: {e}"
                return self._ensure_identity_fields(base or {}, minimal, clean_template)

        out = self._fallback_merge(base, clean_template)
        return self._ensure_identity_fields(base or {}, out, clean_template)

    def _fallback_merge(self, base, template):
        out = {}
        ttype = None
        if isinstance(template, dict): ttype = template.get("$type")
        if not ttype: ttype = base.get("$type")
        if ttype: out["$type"] = ttype

        out["ItemID"] = base.get("newId") or base.get("_guid") or base.get("id") or "compat"
        out["Name"]   = get_display_name(base)

        bucket = classify_realism_type(out.get("$type", ""))
        if bucket == "WeaponMod":
            out.setdefault("ModType", "")
            ov = base.get("overrideProperties", {})
            if isinstance(ov, dict):
                w = ov.get("Weight")
                if isinstance(w, (int, float)): out["Weight"] = w

        return out

    def render_compat(self, base, template):
        compat = self.compute_compat(base, template)
        ctype = guess_type_bucket(compat, base, template)

        allowed = set()
        if ctype == "Gun": allowed = set(CANONICAL_ORDER.get("Gun",[]))
        elif ctype == "Gear": allowed = set(CANONICAL_ORDER.get("Gear",[]))
        elif ctype == "Ammo": allowed = set(CANONICAL_ORDER.get("Ammo",[]))
        else: allowed = set(CANONICAL_ORDER.get("WeaponMod",[]))

        form = CompatForm(compat, editable=True, schema_for_type=allowed,
                          category=self.cb_category.currentText().strip())
        self._wire_form(form)

        have = set(k for k in compat.keys() if not k.startswith("_"))
        missing = sorted(allowed - have)
        type_text = compat.get("$type") or "(unknown)"
        
        pieces =[
            ("Detected $type", type_text),
            ("Type bucket", ctype or "(not classified)"),
            ("Addable fields", f"{len(missing)}")
        ]
        if ctype == "WeaponMod": pieces.append(("Special", "ModType options available (blank allowed)"))
        elif ctype == "Gun": pieces.append(("Special", "WeapType & OperationType options (blank allowed)"))
        elif ctype == "Gear": pieces.append(("Special", "Armor Class & Mask options added"))
        elif ctype == "Ammo": pieces.append(("Special", "Ammo template logic mapped"))
        
        self.lbl_compat_hint.setText(self._mk_stacked_header(pieces))
        
        has_func = callable(resolve_formula_func(self.cb_category.currentText().strip()))

    def recompute_current(self):
        if hasattr(self, "tabs") and self.tabs.currentIndex() == 1:
            w = self.compat_forms[0] if self.compat_forms else None
            tmpl = w.value() if w else None
            if not isinstance(tmpl, dict):
                QMessageBox.information(self, "Recompute", "Select a user template first.")
                return
            base = None
            iid = str(tmpl.get("ItemID") or tmpl.get("_guid") or "")
            if iid:
                for rec in self.index.items:
                    if str(rec.get("newId") or rec.get("_guid") or rec.get("id") or rec.get("_id") or "") == iid:
                        base = rec; break
                        
            detected = self.cb_category.currentText().strip() if hasattr(self, "cb_category") else self._pick_formula_category(base or {}, tmpl)
            
            func = resolve_formula_func(detected) if detected else None
            if not callable(func):
                QMessageBox.information(self, "Recompute", "Pick a valid formula category first.")
                return
            effective_base = self._build_effective_base_for_formula(base or {})
            
            if self.cb_preset.isVisible() and self.cb_preset.currentIndex() > 0:
                effective_base["_preset_hint"] = self.cb_preset.currentText()
                
            newc = call_formula(func, {}, effective_base, tmpl, {
                "spt_path": self.spt_path, "compat_root": self.compat_root, "index": self.index,
            })
            if isinstance(newc, dict):
                newc.setdefault("ItemID", tmpl.get("ItemID"))
                newc.setdefault("Name", tmpl.get("Name"))
                newc = self._ensure_identity_fields(base or {}, newc, tmpl)
                newc = self._apply_realism_passthrough(newc, base or {})
                newc = self._zero_gun_only_fields(newc, guess_type_bucket(newc, base or {}, tmpl))
                newc = strip_add_only(newc, guess_type_bucket(newc, base or {}, tmpl))
                newc = snap_compat(newc)
                
                ctype = guess_type_bucket(newc, base or {}, tmpl)
                allowed = set()
                if ctype == "Gun": allowed = set(CANONICAL_ORDER.get("Gun",[]))
                elif ctype == "Gear": allowed = set(CANONICAL_ORDER.get("Gear",[]))
                elif ctype == "Ammo": allowed = set(CANONICAL_ORDER.get("Ammo",[]))
                else: allowed = set(CANONICAL_ORDER.get("WeaponMod",[]))
                    
                form = CompatForm(newc, editable=True, schema_for_type=allowed,
                                  category=self.cb_category.currentText().strip())
                self._wire_form(form)
            return

        if not self.selected_records:
            QMessageBox.information(self, "Recompute", "Select an item first.")
            return
        base = self.selected_records[0]
        template = getattr(self, "_current_template", None)
        self.render_compat(base, template)

    def on_item_selected(self):
        sel_items = self.item_tree.selectedItems()
        self.selected_records =[]
        for it in sel_items:
            rec = it.data(0, Qt.UserRole)
            if isinstance(rec, dict):
                self.selected_records.append(rec)
        if not self.selected_records: return
        self.render_base(self.selected_records[0])

    def render_base(self, base):
        base_name = self.index.display_name_for(base)
        base_typ  = (base.get("$type") or base.get("parentClass") or base.get("parent") or "")
        base_mod  = base.get("_mod", "")
        header = f"<b>Item</b> — {base_name}  <span style='color:#9aa0a6'>[{base_typ}]</span>"
        if base_mod: header += f"  <span style='color:#6aa84f'>({base_mod})</span>"
        
        matches, candidates = self.index.template_index.match_by_item(base)

        best_idx = 0
        cand_set = set(candidates)
        for i, t in enumerate(matches):
            tgt = str(t.get("_guid") or t.get("id") or t.get("_id") or t.get("ItemID") or t.get("ItemId") or "")
            if tgt in cand_set:
                best_idx = i
                break

        sel_template = matches[best_idx] if matches else None

        if not isinstance(sel_template, dict):
            realism_rec, _ = self._find_realism_record_for_base(base)
            if isinstance(realism_rec, dict): sel_template = realism_rec

        self._current_template = sel_template 

        handbook_parent = self._resolve_parent_category_name(base, sel_template)
        self.lbl_parent_cat.setText(f"<b>Parent</b>: {handbook_parent}")

        type_text = ""
        if isinstance(sel_template, dict): type_text = sel_template.get("$type") or ""
        if not type_text: type_text = base.get("$type") or ""
        self.lbl_type.setText(f"<b>$type</b>: {type_text}")

        detected = self._pick_formula_category(base, sel_template)

        self.cb_category.blockSignals(True)
        self.cb_category.clear()
        self.cb_category.addItem("— select category —")

        cats = set()
        if formulas_mod:
            for map_name in ("gun_formula_map","mod_formula_map",
                             "gear_formula_map","ammo_formula_map"):
                m = getattr(formulas_mod, map_name, None)
                if isinstance(m, dict):
                    cats.update(k for k in m.keys() if isinstance(k, str))
        # ammo_formula_map ships empty, so the built-ins are what actually
        # populate the Ammo side of the dropdown.
        cats.update(ammo_formula_categories())

        if detected:
            f = resolve_formula_func(detected)
            if callable(f): self.cb_category.addItem(detected)

        for c in sorted(cats):
            if c != detected: self.cb_category.addItem(c)

        if detected and callable(resolve_formula_func(detected)): self.cb_category.setCurrentText(detected)
        else: self.cb_category.setCurrentIndex(0)

        self.cb_category.blockSignals(False)
        self._toggle_ammo_panel()
        self._toggle_presets_visibility()

        self.render_template(sel_template)
        # Panels first: the compat form colours itself against their values.
        self.render_basegame_stats(base)
        self.render_realism_panel(base)
        self._seed_ammo_inputs(base)
        self._toggle_ammo_panel()
        self.render_compat(base, sel_template)

    def render_template(self, template):
        if not template:
            self.template_details.setText("<i>No template found for this item.</i>")
            return
        ttype = template.get("$type") or ""
        tname = template.get("Name") or template.get("shortName") or ""
        self.template_details.setText((f"<b>Template</b>: {tname}" if tname else "<b>Template</b>: (selected)"))

    def _merge_dicts(self, a: dict, b: dict, drop_keys=None):
            drop_keys = drop_keys or set()
            out = {} if a is None else dict(a)
            for k, v in (b or {}).items():
                if k in drop_keys: continue
                if isinstance(out.get(k), dict) and isinstance(v, dict): out[k] = self._merge_dicts(out[k], v, drop_keys)
                else: out[k] = v
            for k in list(out.keys()):
                if k in drop_keys: out.pop(k, None)
            return out

    def _build_effective_base_for_formula(self, mod_item: dict) -> dict:
        merged = dict(mod_item or {})

        # 1) start from the item's own _props if present, else the CLONED base-game item's _props
        base_props = get_base_props_dict(merged)                 # existing helper
        if not base_props:
            base_props = self._clone_base_props(merged)          # <-- the fix: resolve the clone

        # 2) overlay overrideProperties (scalar overrides win; nested Slots/Grids/etc. ignored)
        ov = merged.get("overrideProperties", {})
        if isinstance(ov, dict):
            cur = dict(base_props) if isinstance(base_props, dict) else {}
            merged["_props"] = self._merge_dicts(cur, ov)        # existing helper
        elif isinstance(base_props, dict):
            merged["_props"] = dict(base_props)

        # 3) keep the display name at top level for engineer_features_from_item (caliber/length parse)
        if not merged.get("Name"):
            display = get_display_name(merged)
            if display and display != "Unknown":
                merged["Name"] = display

        # 4) muzzleModType visibility for muzzle-device classification
        if isinstance(ov, dict) and "muzzleModType" in ov:
            if isinstance(merged.get("_props"), dict):
                merged["_props"].setdefault("muzzleModType", ov["muzzleModType"])

        return merged


    def batch_export(self):
        sel = getattr(self, "selected_records", []) or[]
        if not sel: return
        out_dir = QFileDialog.getExistingDirectory(self, "Select export folder")
        if not out_dir: return

        pending = []
        for base in sel:
            matches, _c = self.index.template_index.match_by_item(base)
            t = matches[0] if matches else None
            c = reorder_fields(self._ensure_identity_fields(base or {}, self.compute_compat(base, t), t))
            pending.append((c, guess_type_bucket(c, base, t)))
        if not self._check_exportable(pending):
            return

        exported = 0
        for base in sel:
            matches, candidates = self.index.template_index.match_by_item(base)
            t = matches[0] if matches else None
            
            compat = self.compute_compat(base, t)
            compat = self._ensure_identity_fields(base or {}, compat, t)
            compat = reorder_fields(compat) 

            key = str(compat.get("ItemID"))
            name = self.index.display_name_for(base).replace("/", "_")
            fname = os.path.join(out_dir, f"{key}_{name}_compat.json")
            with open(fname, "w", encoding="utf-8") as f:
                json.dump({key: compat}, f, indent=4, ensure_ascii=False)
            exported += 1
        QMessageBox.information(self, "Batch Export", f"Exported {exported} files.")

def apply_dark_stylesheet(app):
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