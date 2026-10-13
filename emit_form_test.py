#!/usr/bin/env python3
"""
Emit Realism formulas per parent type (autodiscovers many templates)
Tuned for strict target isolation, explicit subclasses, physics features, smart rounding.
Updated with stable linear feature extraction and Physical Preset Bypass for real-world tuning.
"""

import os
import re
import sys
import json
import math
import argparse
import warnings
import importlib
import importlib.util
import inspect
from typing import Dict, List, Any, Tuple, Optional, Set

import numpy as np
from sklearn.linear_model import (LinearRegression, Ridge, HuberRegressor,
                                  ElasticNet, LogisticRegression)

# ---------- Robust regexes ----------
HEX24_RE = re.compile(r'^[0-9A-Fa-f]{24}$')

# ---------- Parent classes & friendly names ----------
PARENT_CLASSES: Dict[str, str] = {
    "5b47574386f77428ca22b346": "Ammo", "5b47574386f77428ca22b33c": "AmmoBoxes",
    # The handbook id above only covers the handbook tree. Ammo boxes in the item
    # master hang off the 'AmmoBox' node, which was missing - so all 316 of them
    # walked past StackableItem to the root 'Item' node and were dropped.
    "543be5cb4bdc2deb348b4568": "AmmoBoxes",
    # Same story as AmmoBox: the 'Vest' node in the item master had no entry, so
    # every tactical rig walked to the root and was dropped from training.
    "5448e5284bdc2dcb718b4567": "TacticalRigs",
    # m1911 slide catches and friends hang off AuxiliaryMod -> FunctionalMod in the
    # item master; neither node had an entry, so they walked to the root.
    "5a74651486f7744e73386dd1": "FunctionalMods",
    "550aa4154bdc2dd8348b456b": "FunctionalMods",
    "5448e54d4bdc2dcc718b4568": "ArmorVests", "5b5f701386f774093f2ecf0f": "ArmorPlates",
    "5a341c4b86f77401e2507e28": "ArmorMasks", "5b5f78e986f77447ed5636b1": "AssaultCarbines",
    "5447b5fc4bdc2d87278b4567": "AssaultCarbines", "5b5f78fc86f77409407a7f90": "AssaultRifles",
    "5447b5f14bdc2d61278b4567": "AssaultRifles", "5448e53e4bdc2d60728b4567": "Backpacks",
    "5b5f6f6c86f774093f2ecf0b": "Backpacks", "555ef6e44bdc2de9068b457e": "Barrel",
    "5b5f75c686f774094242f19f": "Barrels", "5b5f71c186f77409407a7ec0": "Bipods",
    "55818afb4bdc2dde698b456d": "Bipods", "5b5f798886f77447ed5636b5": "BoltActionRifles",
    "55818a6f4bdc2db9688b456b": "ChargingHandle", "5b5f751486f77447ec5d770c": "ChargingHandles",
    "5b5f73ab86f774094242f195": "Flashlights", "5b5f71de86f774093f2ecf13": "ForeGrips",
    "55818af64bdc2d5b648b4570": "Foregrip", "5b5f71b386f774093f2ecf11": "FunctionalMods",
    "5b5f760586f774093e6cb509": "GasBlocks", "56ea9461d2720b67698b456f": "Gasblock",
    "5b47574386f77428ca22b33f": "Gear", "5b5f704686f77447ec5d76d7": "GearComponents",
    "5b5f750686f774093e6cb503": "GearMods", "57bef4c42459772e8d35a53b": "GearComponents",
    "5b5f79d186f774093f2ed3c2": "GrenadeLaunchers", "55818a104bdc2db9688b4569": "Handguard",
    "5b5f75e486f77447ec5d7712": "Handguards", "5645bcb74bdc2ded0b8b4578": "Headset",
    "5b5f6f3c86f774094242ef87": "Headsets", "5a341c4086f77401f2541505": "Headwear",
    "5b47574386f77428ca22b330": "Headwear", "55818b014bdc2ddc698b456b": "Launcher",
    "5b5f752e86f774093e6cb505": "Launchers", "55818b0e4bdc2dde698b456e": "LightLasers",
    "5b5f79a486f77409407a7f94": "MachineGuns", "5447bed64bdc2d97278b4568": "MachineGuns",
    "5b5f754a86f774094242f19b": "Magazines", "5448bc234bdc2d3c308b4569": "Magazines",
    "5b5f791486f774093f2ed3be": "MarksmanRifles", "5447b6194bdc2d67278b4567": "MarksmanRifles",
    "5b5f755f86f77447ec5d770e": "Mounts", "55818b224bdc2dde698b456f": "Mounts",
    "5447b5cf4bdc2d65278b4567": "Pistol", "5b5f761f86f774094242f1a1": "PistolGrips",
    "55818a684bdc2ddd698b456d": "PistolGrip", "5b5f792486f77447ed5636b3": "Pistols",
    "55818a304bdc2db5418b457d": "Receiver", "5b5f764186f77447ec5d7714": "ReceiversSlides",
    "5b47574386f77428ca22b33b": "Rounds", "5485a8684bdc2da71d8b4567": "Rounds",
    "5b5f794b86f77409407a7f92": "Shotguns", "5447b6094bdc2dc3278b4567": "Shotguns",
    "5b5f796a86f774093f2ed3c0": "SMGs", "5447b5e04bdc2d62278b4567": "SMGs",
    "5447b6254bdc2dc3278b4568": "SniperRifles", "55818a594bdc2db9688b456a": "Stock",
    "5b5f757486f774093e6cb507": "StocksChassis", "5b5f737886f774093e6cb4fb": "TacticalComboDevices",
    "5b5f6f8786f77447ed563642": "TacticalRigs", "5448e5724bdc2ddf718b4568": "Visor",
    "5b47574386f77428ca22b331": "Visors", "5b5f75b986f77447ec5d7710": "VitalParts",
    "5b5f71a686f77447ed5636ab": "WeaponPartsMods", "5b5f78dc86f77409407a7f8e": "Weapons",
    "55818b164bdc2ddc698b456c": "CombTactDevice",
    "5b5f746686f77447ec5d7708": "IronSights", "5b5f73ec86f774093e6cb4fd": "Sights",
    "5448fe7a4bdc2d6f028b456b": "Sights", "5b5f748386f774093e6cb501": "Sights",
    "5b5f742686f774093e6cb4ff": "Sights", "5b5f744786f774094242f197": "Sights",
    "5b5f740a86f77447ec5d7706": "Sights", "5448fe394bdc2d0d028b456c": "Muzzle",
    "5b5f72f786f77447ec5d7702": "Muzzle", "5b5f724186f77447ed5636ad": "Muzzle",
    "5b5f724c86f774093f2ecf15": "Muzzle", "5b5f731a86f774093e6cb4f9": "Muzzle",
}
CLASS_ID_SET: Set[str] = set(PARENT_CLASSES.keys())

GUN_CLASS_NAMES = {'AssaultCarbines','AssaultRifles','BoltActionRifles','GrenadeLaunchers','Launcher','Launchers','MachineGuns','MarksmanRifles','Pistol','Pistols','Shotguns','SMGs','SniperRifles','Weapons'}
GEAR_CLASS_NAMES = {'ArmorVests','ArmorPlates','ArmorMasks','Backpacks','Gear','GearComponents','GearMods','Headset','Headsets','Headwear','TacticalRigs','Visor','Visors'}
BOOL_FIELDS = {'AllowADS','StockAllowADS','HasShoulderContact','WeaponAllowADS','AllowOverheat','IsManuallyOperated','CanCycleSubs','CanSpall','BlocksMouth'}

# Strict per-class target allowlists derived from json_gen.ts
MOD_CLASS_ALLOWED_TARGETS: Dict[str, Set[str]] = {
    'Barrel':       {'verticalrecoil','horizontalrecoil','autorof','semirof','modmalfunctionchance',
                     'convergence','accuracy','centerofimpact','heatfactor','coolfactor',
                     'durabilityburnmodificator','velocity','ergonomics','weight','loudness','dispersion'},
    'Barrels':      {'verticalrecoil','horizontalrecoil','autorof','semirof','modmalfunctionchance',
                     'convergence','accuracy','centerofimpact','heatfactor','coolfactor',
                     'durabilityburnmodificator','velocity','ergonomics','weight','loudness','dispersion'},
    'Suppressors':  {'verticalrecoil','horizontalrecoil','dispersion','camerarecoil','autorof','semirof',
                     'modmalfunctionchance','cancyclesubs','accuracy','heatfactor','coolfactor',
                     'durabilityburnmodificator','velocity','recoilangle','ergonomics','weight',
                     'modshotdispersion','loudness','convergence','flash'},
    'MuzzleBrakesFactory': {'verticalrecoil','horizontalrecoil','dispersion','camerarecoil','autorof','semirof',
                     'modmalfunctionchance','cancyclesubs','accuracy','heatfactor','coolfactor',
                     'durabilityburnmodificator','velocity','recoilangle','ergonomics','weight',
                     'modshotdispersion','loudness','convergence','flash'},
    'Compensators': {'verticalrecoil','horizontalrecoil','dispersion','camerarecoil','autorof','semirof',
                     'modmalfunctionchance','cancyclesubs','accuracy','heatfactor','coolfactor',
                     'durabilityburnmodificator','velocity','recoilangle','ergonomics','weight',
                     'modshotdispersion','loudness','convergence','flash'},
    'MuzzleCombos': {'verticalrecoil','horizontalrecoil','dispersion','camerarecoil','autorof','semirof',
                     'modmalfunctionchance','cancyclesubs','accuracy','heatfactor','coolfactor',
                     'durabilityburnmodificator','velocity','recoilangle','ergonomics','weight',
                     'modshotdispersion','loudness','convergence','flash'},
    'MuzzleBrakes': {'verticalrecoil','horizontalrecoil','dispersion','camerarecoil','autorof','semirof',
                     'modmalfunctionchance','cancyclesubs','accuracy','heatfactor','coolfactor',
                     'durabilityburnmodificator','velocity','recoilangle','ergonomics','weight',
                     'modshotdispersion','loudness','convergence','flash'},
    'FlashHiders':  {'verticalrecoil','horizontalrecoil','dispersion','camerarecoil','autorof','semirof',
                     'modmalfunctionchance','cancyclesubs','accuracy','heatfactor','coolfactor',
                     'durabilityburnmodificator','velocity','recoilangle','ergonomics','weight',
                     'modshotdispersion','loudness','convergence','flash'},
    'MuzzleAdapters':{'verticalrecoil','horizontalrecoil','dispersion','camerarecoil','autorof','semirof',
                     'modmalfunctionchance','cancyclesubs','accuracy','heatfactor','coolfactor',
                     'durabilityburnmodificator','velocity','recoilangle','ergonomics','weight',
                     'modshotdispersion','loudness','convergence','flash'},
    'Mounts':       {'ergonomics','accuracy','weight'},
    'Receiver':     {'modmalfunctionchance','accuracy','heatfactor','coolfactor',
                     'durabilityburnmodificator','ergonomics','weight'},
    'ReceiversSlides':{'modmalfunctionchance','accuracy','heatfactor','coolfactor',
                     'durabilityburnmodificator','ergonomics','weight'},
    'Stock':        {'verticalrecoil','horizontalrecoil','dispersion','autorof','semirof',
                     'modmalfunctionchance','camerarecoil','aimspeed','ergonomics','accuracy',
                     'hasshouldercontact','blocksfolding','stockallowads','weight'},
    'StocksChassis':{'verticalrecoil','horizontalrecoil','dispersion','autorof','semirof',
                     'modmalfunctionchance','camerarecoil','aimspeed','ergonomics','accuracy',
                     'hasshouldercontact','blocksfolding','stockallowads','weight'},
    'ChargingHandle':  {'reloadspeed','fixspeed','ergonomics','weight','chamberspeed'},
    'ChargingHandles': {'reloadspeed','fixspeed','ergonomics','weight','chamberspeed'},
    'Sights':    {'aimspeed','accuracy','ergonomics','weight'},
    'IronSights':{'aimspeed','accuracy','ergonomics','weight'},
    'Magazines': {'reloadspeed','ergonomics','malfunctionchance','loadunloadmodifier',
                  'checktimemodifier','weight','verticalrecoil','horizontalrecoil'},
    'Foregrip':    {'verticalrecoil','horizontalrecoil','dispersion','aimspeed','ergonomics','accuracy','weight'},
    'ForeGrips':   {'verticalrecoil','horizontalrecoil','dispersion','aimspeed','ergonomics','accuracy','weight'},
    'PistolGrip':  {'verticalrecoil','horizontalrecoil','dispersion','aimspeed','ergonomics','accuracy','weight'},
    'PistolGrips': {'verticalrecoil','horizontalrecoil','dispersion','aimspeed','ergonomics','accuracy','weight'},
    'Gasblock':  {'verticalrecoil','horizontalrecoil','dispersion','autorof','semirof',
                  'modmalfunctionchance','cancyclesubs','accuracy','heatfactor','coolfactor',
                  'durabilityburnmodificator','ergonomics','weight','convergence','flash'},
    'GasBlocks': {'verticalrecoil','horizontalrecoil','dispersion','autorof','semirof',
                  'modmalfunctionchance','cancyclesubs','accuracy','heatfactor','coolfactor',
                  'durabilityburnmodificator','ergonomics','weight','convergence','flash'},
    # ChamberSpeed is deliberately absent. Only 7 of 196 handguards in Realism's
    # own template set carry a non-zero value, and every one of them is a
    # pump-action shotgun forend (KS-23, MR-133, Mossberg 590, Remington 870) --
    # where the handguard IS the pump, so it really does drive cycling. On a
    # rifle handguard it means nothing, and predicting it stamped a cycling
    # modifier onto all 196. It stays available from "+ Add Field" for the
    # handful of pump forends that need it.
    'Handguard':  {'verticalrecoil','horizontalrecoil','dispersion','aimspeed',
                   'ergonomics','accuracy','heatfactor','coolfactor','weight'},
    'Handguards': {'verticalrecoil','horizontalrecoil','dispersion','aimspeed',
                   'ergonomics','accuracy','heatfactor','coolfactor','weight'},
    'CombTactDevice':       {'ergonomics','weight'},
    'TacticalComboDevices': {'ergonomics','weight'},
    'Flashlights':          {'ergonomics','weight'},
    'LightLasers':          {'ergonomics','weight'},
    'Bipods': {'verticalrecoil','horizontalrecoil','autorof','semirof','modmalfunctionchance',
               'aimspeed','reloadspeed','ergonomics','accuracy','fixspeed',
               'heatfactor','coolfactor','durabilityburnmodificator','weight'},
}

GUN_ALLOWED_TARGETS: Set[str] = {
    'weapaccuracy', 'basetorque', 'recoildamping', 'recoilhanddamping', 'offsetrotation',
    'recoilintensity', 'hasshouldercontact', 'weaponallowads',
    'ergonomics', 'verticalrecoil', 'horizontalrecoil', 'dispersion', 'camerarecoil',
    'visualmulti', 'convergence', 'recoilangle', 'durabilityburnratio', 'basemalfunctionchance',
    'heatfactorgun', 'heatfactorbyshot', 'coolfactorgun', 'coolfactorgunmods',
    'centerofimpact', 'hipaccuracyrestorationdelay', 'hipaccuracyrestorationspeed',
    'hipinnaccuracygain', 'velocity', 'weight', 'autorof', 'semirof',
    'basereloadspeedmulti', 'basechamberspeedmulti', 'maxchamberspeed', 'minchamberspeed',
    'basechambercheckspeed', 'basefixspeed',
}

PRESET_KEYWORDS = {
    'BarrelLengthMM', 'CaliberNumeric', 'IsShort', 'IsLong', 'IsHeavy', 'IsLight',
    'IsSuppressor', 'IsBrake', 'IsAdapter', 'IsCombo', 'LogWeight', 'LogErgo',
    'IsShotgun', 'GaugeNumeric', 'IsPumpAction', 'IsSemiAutoShotgun', 'IsTubeFed',
    'ChokeTightness', 'IsMagnified', 'IsCollimator', 'IsDrum', 'CapacityGuess',
    'ArmorClassNumeric', 'LoudnessHint', 'FireRateRPM', 'SightingRange', 'GridCells',
    'DurabilityBurnMod', 'IsManuallyOperatedGun', 'WeaponFootprint',
}

# Fields that are physically impossible to be negative
# Set from --keep-weak-targets; see _beats_writing_nothing.
KEEP_WEAK_TARGETS = False

# Minimum samples per half before a class is allowed to split. Everything that
# guards quality here (the zero-gate recall contract, the null-model check) is
# measured in-sample, so a small half can pass both and still be wrong.
MIN_SPLIT_SAMPLES = 20

# Bore diameter in mm for every calibre id the game uses. Used to turn an exact
# ammoCaliber string into the numeric feature, instead of regexing a display name.
CALIBER_ID_TO_MM: Dict[str, float] = {
    'caliber12g': 18.5, 'caliber20g': 15.6, 'caliber23x75': 23.0,
    'caliber9x19para': 9.02, 'caliber9x18pm': 9.27, 'caliber9x21': 9.02,
    'caliber9x39': 9.25, 'caliber9x33r': 9.07, 'caliber1143x23acp': 11.5,
    'caliber762x51': 7.82, 'caliber762x54r': 7.92, 'caliber762x39': 7.9,
    'caliber762x35': 7.82, 'caliber762x25tt': 7.85, 'caliber556x45nato': 5.7,
    'caliber545x39': 5.6, 'caliber57x28': 5.7, 'caliber46x30': 4.6,
    'caliber127x33': 12.7, 'caliber127x55': 12.7, 'caliber86x70': 8.6,
    'caliber366tkm': 9.5, 'caliber68x51': 7.0, 'caliber1270x55': 12.7,
    'caliber40x46': 40.0, 'caliber40mmru': 40.0, 'caliber26x75': 26.0,
}

# item id -> bore mm, built by build_caliber_index() and emitted into formulas.py.
CALIBER_BY_ITEM_ID: Dict[str, float] = {}

# Handgun / PDW chamberings. A mod that fits one of these behaves nothing like
# the rifle equivalent: a 4" pistol barrel is at its design length while a 4"
# rifle barrel is a stub, and burn rate, heat and velocity all scale differently
# (5.56 loses 0.10 velocity/mm to barrel loss, .45 ACP is essentially flat past
# its 8" reference). Pooling them was dragging both fits toward the middle.
PISTOL_CALIBER_IDS = {
    'caliber9x19para', 'caliber9x18pm', 'caliber9x21', 'caliber1143x23acp',
    'caliber762x25tt', 'caliber57x28', 'caliber46x30', 'caliber127x33',
    'caliber9x33r',
}
PISTOL_CALIBER_ITEM_IDS: Set[str] = set()

# Mod classes worth splitting by host platform. Only where both halves are
# large enough to fit separately.
SPLIT_PISTOL_RIFLE = {'Barrel', 'Barrels', 'Suppressors', 'MuzzleBrakes',
                      'Compensators', 'MuzzleCombos',
                      'Handguard', 'Handguards', 'Magazines', 'PistolGrip'}

# ExtraSizeDown -- how far a magazine hangs below the receiver -- is what orders
# Realism's magazine values, far better than capacity does. Group means across
# the 213 magazines are monotonic on every target:
#     ExtraSizeDown   0 flush    1 standard   2 extended
#     ReloadSpeed        -0.66       -1.99        -4.91
#     CheckTimeModifier  -5.56       -1.49       +11.82
#     LoadUnloadModifier -3.94       +2.88        +4.55
#     Ergonomics         -0.13       -0.88        -5.32
# Capacity is near-useless on its own (r = +0.000 against ReloadSpeed) but does
# matter within a class (r = -0.545 among standard mags), so splitting on size
# lets the fit pick that up instead of averaging it away.
# ChamberSpeed on a charging handle is a percentage over the weapon's base
# handle, on an ABSOLUTE quality scale rather than a family-relative one: the
# milspec AR-15 T-handle is the 0 point, and an SR-25 KAC std handle is already
# +26 because the design is simply better. Across Realism's 35 handles the tiers
# separate cleanly (milspec n=11 all exactly 0; extended n=8 median 22.5; ambi
# n=14 median 32.8), and the tier median scores MAE 1.81 against 11.37 for the
# regression. Splitting lets the fit stop averaging a bimodal population.
CHARGING_HANDLE_TIER_HINTS = [
    ('Ambi', ('ambi', 'raptor', 'grip_n_rip', 'avalanche', 'geissele_ach',
              'geissele_sch', 'double_latch', 'masp', 'mod2', 'knurled',
              'zenit_rp1', 'css', 'cmmg_mid', 'spear')),
    ('Extended', ('extended', 'tactical_latch', 'badger', 'handler', 'a3_handle',
                  'single_latch', 'kac_charging_handle', 'mcx')),
]


def split_charging_handles(class_name: str, samples: List[Tuple[Dict, Dict]]):
    if not class_name.startswith('ChargingHandle'):
        return {}
    buckets: Dict[str, List[Tuple[Dict, Dict]]] = {}
    for m, rec in samples:
        nm = (rec.get('Name') or m.get('_name') or '').lower()
        tier = next((t for t, keys in CHARGING_HANDLE_TIER_HINTS
                     if any(k in nm for k in keys)), '')
        buckets.setdefault(f'{class_name}{tier}', []).append((m, rec))
    usable = {k: v for k, v in buckets.items() if len(v) >= 6}
    return usable if len(usable) > 1 else {}


# A free-floating handguard does not touch the barrel, so it does not disturb
# harmonics; a clamped one does. Realism reflects it -- mean Accuracy +5.96 over
# 48 free-float rails against +2.43 over 148 clamped, and 30/48 positive against
# 58/148. Pooling them is why Handguard Accuracy sat at 74% sign.
FREE_FLOAT_HINTS = ('mlok', 'm-lok', 'keymod', 'key_mod', 'free', 'ffs', 'quad',
                    'ris', 'rahg', 'urx', 'mrf', 'slr', 'geissele', 'mcmr',
                    'smr', 'hera', 'midwest', 'ff')


def split_handguards_by_mount(class_name: str, samples: List[Tuple[Dict, Dict]]):
    if not class_name.startswith('Handguard'):
        return {}
    ff, clamped = [], []
    for m, rec in samples:
        nm = (rec.get('Name') or m.get('_name') or '').lower()
        (ff if any(k in nm for k in FREE_FLOAT_HINTS) else clamped).append((m, rec))
    if len(ff) < MIN_SPLIT_SAMPLES or len(clamped) < MIN_SPLIT_SAMPLES:
        return {}
    return {f'{class_name}FreeFloat': ff, class_name: clamped}


def split_magazines_by_size(class_name: str, samples: List[Tuple[Dict, Dict]]):
    if not class_name.startswith('Magazines'):
        return {}
    buckets: Dict[str, List[Tuple[Dict, Dict]]] = {}
    for m, rec in samples:
        esd = m.get('_props', {}).get('ExtraSizeDown')
        esd = int(esd) if isinstance(esd, (int, float)) and not isinstance(esd, bool) else 1
        key = {0: 'Flush', 1: '', 2: 'Extended'}.get(min(max(esd, 0), 2), '')
        buckets.setdefault(f'{class_name}{key}', []).append((m, rec))
    usable = {k: v for k, v in buckets.items() if len(v) >= MIN_SPLIT_SAMPLES}
    return usable if len(usable) > 1 else {}

# Suppressor mounting, which decides whether the can can hurt accuracy at all.
# A rubber-wipe or muzzle-clamped design really does disturb the projectile and
# the barrel; a rigid QD or direct-thread mount on a modern can does not, and in
# the real world usually tightens groups slightly by adding muzzle mass. Realism
# authors both kinds in one file, so pooling them teaches the fit that
# suppressors cost accuracy on average, which is wrong for two thirds of them.
SUPPRESSOR_WIPE_HINTS = (
    'pbs-1', 'pbs1', 'pbs-4', 'pbs4', 'bramit', 'hexagon', 'rotor', 'tochmash',
    '9a91', 'val', 'vss', 'kbp', '6p9', 'dvl', 'buben', 'tundra',
    'tt_custom_noname', 'pab-9', 'fischer', 'fd917', 'alpha_dog', 'alpha_9',
    'noname', 'spectehnika',
)


def is_wipe_suppressor(name: str) -> bool:
    n = (name or '').lower()
    return any(k in n for k in SUPPRESSOR_WIPE_HINTS)


def split_suppressors_by_mount(class_name: str, samples: List[Tuple[Dict, Dict]]):
    """Split suppressors into wipe/legacy and rigid/modern halves."""
    if not class_name.startswith('Suppressors'):
        return {}
    wipe, rigid = [], []
    for m, rec in samples:
        nm = rec.get('Name') or m.get('_name') or ''
        (wipe if is_wipe_suppressor(nm) else rigid).append((m, rec))
    if len(wipe) < MIN_SPLIT_SAMPLES or len(rigid) < MIN_SPLIT_SAMPLES:
        return {}
    return {f'{class_name}Wipe': wipe, class_name: rigid}


def split_by_host_caliber(class_name: str, samples: List[Tuple[Dict, Dict]]):
    """Split a mod class into pistol-host and rifle-host halves.

    Returns {} when the class is not worth splitting or one half is too small
    to fit, in which case the caller trains the class whole as before.
    """
    if class_name not in SPLIT_PISTOL_RIFLE:
        return {}
    pistol, rifle = [], []
    for m, rec in samples:
        iid = str(m.get('_id', '') or '').lower()
        (pistol if iid in PISTOL_CALIBER_ITEM_IDS else rifle).append((m, rec))
    # A split halves the sample count, and the zero-gate contract plus the
    # null-model check are both measured in-sample -- at n < 20 a half can
    # satisfy both while still flattening most real values. SuppressorsPistolWipe
    # trained on 7 items and CompensatorsPistol on 9; both produced targets that
    # were wrong in sign more often than not.
    if len(pistol) < MIN_SPLIT_SAMPLES or len(rifle) < MIN_SPLIT_SAMPLES:
        return {}
    return {f'{class_name}Pistol': pistol, class_name: rifle}


def build_pistol_caliber_set(master_by_id: Dict[str, Dict[str, Any]]) -> Set[str]:
    """Item ids whose only resolvable host chambering is a handgun round."""
    from collections import defaultdict
    parents = defaultdict(set)
    for it in master_by_id.values():
        for slot in (it.get('_props', {}).get('Slots') or []):
            for filt in (slot.get('_props', {}).get('filters') or []):
                for child in (filt.get('Filter') or []):
                    parents[str(child).lower()].add(str(it.get('_id', '')).lower())

    def resolve(item_id, depth=0, seen=None):
        seen = seen or set()
        if item_id in seen or depth > 6:
            return set()
        seen.add(item_id)
        found = set()
        it = master_by_id.get(item_id)
        if it:
            cal = it.get('_props', {}).get('ammoCaliber')
            if isinstance(cal, str) and cal.strip():
                found.add(cal.strip().lower())
        for par in parents.get(item_id, ()):
            found |= resolve(par, depth + 1, seen)
        return found

    out = set()
    for iid in master_by_id:
        cals = resolve(iid)
        if cals and cals <= PISTOL_CALIBER_IDS:
            out.add(iid)
    return out


def build_caliber_index(master_by_id: Dict[str, Dict[str, Any]]) -> Dict[str, float]:
    """Resolve every mod to the calibre of the weapon it can be fitted to.

    The name-derived CaliberNumeric is unreliable on mods because model numbers
    look like calibres: barrel_ar15_260mm parses as 15.0mm, barrel_mr133_610mm as
    1.33mm. That was wrong on 63 of 165 barrels, feeding garbage into every
    formula that used the feature.

    A mod does not carry ammoCaliber itself, but the weapon it mounts on does -
    sometimes several slot levels up (barrel -> upper receiver -> weapon). Walking
    the slot-filter graph upwards to the nearest ancestor that declares
    ammoCaliber resolves all 165 barrels with no ambiguity.
    """
    from collections import defaultdict
    parents = defaultdict(set)
    for it in master_by_id.values():
        for slot in (it.get('_props', {}).get('Slots') or []):
            for filt in (slot.get('_props', {}).get('filters') or []):
                for child in (filt.get('Filter') or []):
                    parents[str(child).lower()].add(str(it.get('_id', '')).lower())

    cache: Dict[str, Optional[str]] = {}

    def resolve(item_id: str, depth: int = 0, seen=None) -> Set[str]:
        seen = seen or set()
        if item_id in seen or depth > 6:
            return set()
        seen.add(item_id)
        found = set()
        it = master_by_id.get(item_id)
        if it:
            cal = it.get('_props', {}).get('ammoCaliber')
            if isinstance(cal, str) and cal.strip():
                found.add(cal.strip().lower())
        for par in parents.get(item_id, ()):
            found |= resolve(par, depth + 1, seen)
        return found

    out: Dict[str, float] = {}
    for iid in master_by_id:
        cals = resolve(iid)
        mms = {CALIBER_ID_TO_MM[c] for c in cals if c in CALIBER_ID_TO_MM}
        if len(mms) == 1:                      # unambiguous only
            out[iid] = mms.pop()
    return out

HARD_FLOOR_ZERO: Set[str] = {
    'Weight', 'Dispersion', 'CenterOfImpact',
    'BaseMalfunctionChance', 'ModMalfunctionChance', 'DurabilityBurnRatio',
    'DurabilityBurnModificator', 'HeatFactor', 'CoolFactor', 'HeatFactorGun',
    'CoolFactorGun', 'CoolFactorGunMods', 'HeatFactorByShot', 'AutoROF', 'SemiROF',
    'BaseChamberSpeedMulti', 'BaseReloadSpeedMulti', 'MinChamberSpeed', 'MaxChamberSpeed',
    'RecoilDamping', 'RecoilHandDamping', 'HipAccuracyRestorationDelay',
    'HipAccuracyRestorationSpeed', 'HipInnaccuracyGain', 'SpallReduction',
    'VisualMulti', 'OffsetRotation', 'RecoilIntensity',
}

SHOTGUN_DISP_DEFAULTS: Dict[str, int] = {
    'Shotguns': 1,
    'Pistol': 10,
    'Pistols': 10,
}

EXCLUDED_TARGETS_DEFAULT = {
    # 'loyaltylevel' and 'conflictingitems' are hard-banned: they are never
    # predicted, never emitted, and never editable in the compat tool.
    'loyaltylevel', 'conflictingitems',
    # Buckshot-only: predicting it on every mod class was pure noise.
    'modshotdispersion',
    'basepricemodifier', 'ismanuallyoperated', 'allowoverheat',
    'templateid', 'templatetype', 'armorclass', 'masktouse', 'price',
    'shotgundispersion',
}

# Emitted-value precision. Realism reads 3 d.p. fine for ordinary stats, and the
# sub-0.01 fields (malfunction chance et al) need 4 to survive rounding at all.
BASE_PROP_PASSTHROUGH = {
    'DurabilityBurnRatio', 'HeatFactorGun', 'HeatFactorByShot',
    'CoolFactorGun', 'CoolFactorGunMods',
}

DEFAULT_EMIT_DECIMALS = 3
HIGH_PRECISION_TARGETS = {
    'BaseMalfunctionChance', 'ModMalfunctionChance',
    'HipAccuracyRestorationDelay', 'HipAccuracyRestorationSpeed',
    'HipInnaccuracyGain', 'OffsetRotation',
}

BARREL_LIKE_CLASSES = {'Barrel','Barrels','Muzzle','Suppressors','MuzzleBrakes','Compensators','MuzzleCombos','FlashHiders','MuzzleAdapters'}
CLASS_FORCE_FEATURES = {
    'Shotguns': {'IsShotgun','GaugeNumeric','IsPumpAction','IsSemiAutoShotgun','IsTubeFed','ChokeTightness','BarrelLengthMM','CaliberNumeric','FireRateRPM','IsManuallyOperatedGun'},
    'Barrel': {'BarrelLengthMM','CaliberNumeric','IsShort','IsLong','IsHeavy','IsLight'},
    'Barrels': {'BarrelLengthMM','CaliberNumeric','IsShort','IsLong','IsHeavy','IsLight'},
    'Muzzle': {'IsSuppressor','IsBrake','IsAdapter','IsCombo','LoudnessHint'},
    'Suppressors': {'IsSuppressor','LoudnessHint'},
    'MuzzleBrakes': {'IsBrake'},
    'FlashHiders': {'IsBrake'},
    'MuzzleAdapters': {'IsAdapter'},
    'StocksChassis': {'IsHeavy','IsLight','LogWeight'},
    'Stock': {'IsHeavy','IsLight','LogWeight'},
    'Handguard': {'IsShort','IsLong','IsHeavy','IsLight','LogWeight'},
    'Handguards': {'IsShort','IsLong','IsHeavy','IsLight','LogWeight'},
    'Sights': {'IsMagnified','IsCollimator','LogWeight','SightingRange'},
    'IronSights': {'IsMagnified','IsCollimator','LogWeight','SightingRange'},
    'Magazines': {'CapacityGuess','IsDrum','IsHeavy'},
    'Receiver': {'DurabilityBurnMod','LogWeight'},
    'ReceiversSlides': {'DurabilityBurnMod','LogWeight'},
    'ArmorPlates': {'ArmorClassNumeric','LogWeight'},
    'ArmorMasks': {'ArmorClassNumeric','LogWeight'},
    'ArmorVests': {'ArmorClassNumeric','LogWeight'},
    'Headwear': {'ArmorClassNumeric','LogWeight'},
    'Backpacks': {'GridCells','LogWeight'},
    'Headset': {'LoudnessHint','LogWeight'},
    'Headsets': {'LoudnessHint','LogWeight'},
}

CLASS_TARGET_ADJUSTMENTS = {
 'Shotguns': {
  'WeapAccuracy':['pred += (0.85 * ((BarrelLengthMM - 470.0) / 100.0))','pred += (5.0 * ChokeTightness)','pred += (-0.20 * ((GaugeNumeric - 12.0) / 8.0))','pred += (-0.75 * IsPumpAction)','pred += (0.45 * IsSemiAutoShotgun)'],
  'Velocity':['pred += (5.5 * ((BarrelLengthMM - 470.0) / 100.0))','pred += (-0.50 * ((GaugeNumeric - 12.0) / 8.0))','pred += (0.25 * ChokeTightness)'],
  'BaseMalfunctionChance':['pred += (-0.002 * IsPumpAction)','pred += (0.0015 * IsSemiAutoShotgun)'],
  'CameraRecoil':['pred += (0.06 * ((GaugeNumeric - 12.0) / 8.0))','pred += (0.04 * IsSemiAutoShotgun)'],
  'Convergence':['pred += (0.20 * ((BarrelLengthMM - 470.0) / 100.0))','pred += (0.15 * ChokeTightness)'],
 },
 'Barrel': {
  'Velocity':         ['pred += ((3.5 * ((BarrelLengthMM - 406.4) / 100.0))) if BarrelLengthMM else 0'],
  'Ergonomics':       ['pred += ((-5.0 * ((BarrelLengthMM - 406.4) / 100.0))) if BarrelLengthMM else 0'],
  'HorizontalRecoil': ['pred += ((-8.0 * ((BarrelLengthMM - 406.4) / 100.0))) if BarrelLengthMM else 0'],
  'VerticalRecoil':   ['pred += ((0.5 * ((BarrelLengthMM - 406.4) / 100.0))) if BarrelLengthMM else 0'],
  'Convergence':      ['pred += ((-0.3 * ((BarrelLengthMM - 406.4) / 100.0))) if BarrelLengthMM else 0'],
  'Loudness':         ['pred += ((-3.0 * ((BarrelLengthMM - 406.4) / 100.0))) if BarrelLengthMM else 0'],
 },
 'Barrels': {
  'Velocity':         ['pred += ((3.5 * ((BarrelLengthMM - 406.4) / 100.0))) if BarrelLengthMM else 0'],
  'Ergonomics':       ['pred += ((-5.0 * ((BarrelLengthMM - 406.4) / 100.0))) if BarrelLengthMM else 0'],
  'HorizontalRecoil': ['pred += ((-8.0 * ((BarrelLengthMM - 406.4) / 100.0))) if BarrelLengthMM else 0'],
  'VerticalRecoil':   ['pred += ((0.5 * ((BarrelLengthMM - 406.4) / 100.0))) if BarrelLengthMM else 0'],
  'Convergence':      ['pred += ((-0.3 * ((BarrelLengthMM - 406.4) / 100.0))) if BarrelLengthMM else 0'],
  'Loudness':         ['pred += ((-3.0 * ((BarrelLengthMM - 406.4) / 100.0))) if BarrelLengthMM else 0'],
 },
 # Ergonomics is 0 on all 88 suppressors in Realism's template and
 # CenterOfImpact is 0 on all 88 too, so neither gets a hand nudge -- the fit
 # reproduces the template. The Loudness/Flash/recoil offsets are gone as well:
 # they were flat subtractions applied on top of a fit that had already learned
 # the level, which is exactly what made Loudness bias equal its MAE on every
 # item. Only the physical weight of the can stays.
 'Suppressors': {'Weight':['pred += (0.08 * IsSuppressor)']},
 'SuppressorsWipe': {'Weight':['pred += (0.08 * IsSuppressor)']},
 'SuppressorsPistol': {'Weight':['pred += (0.08 * IsSuppressor)']},
 'SuppressorsPistolWipe': {'Weight':['pred += (0.08 * IsSuppressor)']},
 'MuzzleBrakes': {
  'Flash':         ['pred += (1.2 * IsBrake)', 'pred += ((3.0 * (CaliberNumeric - 7.62))) if CaliberNumeric else 0'],
  'Loudness':      ['pred += ((6.0 * (CaliberNumeric - 7.62))) if CaliberNumeric else 0'],
  'Convergence':   ['pred += ((4.0 * (CaliberNumeric - 7.62))) if CaliberNumeric else 0'],
  'CameraRecoil':  ['pred += ((-2.0 * (CaliberNumeric - 7.62))) if CaliberNumeric else 0'],
  'Ergonomics':    ['pred -= (0.6 * IsBrake)'],
  'VerticalRecoil':['pred -= (1.0 * IsBrake)'],
  'HorizontalRecoil':['pred -= (0.7 * IsBrake)'],
  'Weight':        ['pred += (0.03 * IsBrake)'],
 },
 'FlashHiders': {'Flash':['pred -= (3.0 * IsBrake)'],'Ergonomics':['pred -= (0.3 * IsBrake)'],'Weight':['pred += (0.02 * IsBrake)']},
 'MuzzleAdapters': {'Weight':['pred += (0.015 * IsAdapter)'],'Ergonomics':['pred -= (0.2 * IsAdapter)']},
 'StocksChassis': {'Ergonomics':['pred += (-0.6 * IsHeavy) + (0.6 * IsLight)'],'Weight':['pred += (0.12 * IsHeavy) - (0.08 * IsLight)'],'CameraRecoil':['pred += (-0.4 * IsHeavy) + (0.2 * IsLight)'],'HasShoulderContact':['pred += (0.5 * IsHeavy)']},
 'Stock': {'Ergonomics':['pred += (-0.6 * IsHeavy) + (0.6 * IsLight)'],'Weight':['pred += (0.12 * IsHeavy) - (0.08 * IsLight)'],'CameraRecoil':['pred += (-0.4 * IsHeavy) + (0.2 * IsLight)'],'HasShoulderContact':['pred += (0.5 * IsHeavy)']},
 'Handguard': {'Ergonomics':['pred += (0.5 * IsShort) - (0.5 * IsLong) - (0.3 * IsHeavy) + (0.3 * IsLight)'],'Weight':['pred += (0.05 * IsLong) + (0.06 * IsHeavy) - (0.04 * IsLight)'],'VerticalRecoil':['pred -= (0.3 * IsLong)'],'HorizontalRecoil':['pred -= (0.2 * IsLong)']},
 'Handguards': {'Ergonomics':['pred += (0.5 * IsShort) - (0.5 * IsLong) - (0.3 * IsHeavy) + (0.3 * IsLight)'],'Weight':['pred += (0.05 * IsLong) + (0.06 * IsHeavy) - (0.04 * IsLight)'],'VerticalRecoil':['pred -= (0.3 * IsLong)'],'HorizontalRecoil':['pred -= (0.2 * IsLong)']},
 'Sights': {'Ergonomics':['pred += (-0.8 * IsMagnified) + (0.4 * IsCollimator)'],'Weight':['pred += (0.05 * IsMagnified)'],'AimSpeed':['pred += (-0.25 * IsMagnified) + (0.15 * IsCollimator)']},
 'IronSights': {'Ergonomics':['pred += (0.25 * IsCollimator)'],'Weight':['pred += (0.01 * IsMagnified)'],'AimSpeed':['pred += (0.10 * IsCollimator)']},
 'Magazines': {'Weight':['pred += (0.0025 * CapacityGuess) + (0.10 * IsDrum)'],'Ergonomics':['pred -= (0.03 * CapacityGuess) - (0.8 * IsDrum)'],'Reload':['pred -= (0.0015 * CapacityGuess) - (0.05 * IsDrum)'],'LoadUnload':['pred -= (0.0020 * CapacityGuess) - (0.06 * IsDrum)']},
 'ArmorPlates': {'AllowADS':['pred -= (0.15 * ArmorClassNumeric)'],'ReloadSpeedMulti':['pred -= (0.03 * ArmorClassNumeric)'],'SpallReduction':['pred += (0.08 * ArmorClassNumeric)']},
 'ArmorMasks': {'AllowADS':['pred -= (0.1 * ArmorClassNumeric)'],'ReloadSpeedMulti':['pred -= (0.02 * ArmorClassNumeric)'],'SpallReduction':['pred += (0.06 * ArmorClassNumeric)'],'BlocksMouth':['pred += (0.5 * ArmorClassNumeric)']},
 'ArmorVests': {'Comfort':['pred -= (0.08 * ArmorClassNumeric)'],'speedPenaltyPercent':['pred += (0.6 * ArmorClassNumeric)'],'mousePenalty':['pred += (0.5 * ArmorClassNumeric)'],'weaponErgonomicPenalty':['pred += (0.45 * ArmorClassNumeric)']},
 'Headset': {'dB':['pred += (0.4 * LoudnessHint)']},
 'Headsets': {'dB':['pred += (0.4 * LoudnessHint)']},
 'Backpacks': {'speedPenaltyPercent':['pred += -(GridCells * 0.1)']},
}

EXPLICIT_SOURCE_MAP = {
    # NO vanilla-prop aliases here: RecoilForceUp/RecoilForceBack are on a
    # different scale to Realism's VerticalRecoil/HorizontalRecoil (HK416A5:
    # 103/316 vanilla vs 80/140 Realism), so blending them in doubled results.
    'VerticalRecoil':['VerticalRecoil'],
    'HorizontalRecoil':['HorizontalRecoil'],
    'Velocity':['Velocity'], 'Loudness':['Loudness'],
    'CenterOfImpact': ['CenterOfImpact'], 'BaseMalfunctionChance':['BaseMalfunctionChance'],
    'ModMalfunctionChance':['ModMalfunctionChance','BaseMalfunctionChance'],
    'HeatFactor':['HeatFactor'], 'CoolFactor': ['CoolFactor'],
    'HeatFactorGun':['HeatFactorGun'], 'CoolFactorGun':['CoolFactorGun'],
    'DurabilityBurnRatio':['DurabilityBurnRatio'],
    'Accuracy': ['Accuracy','WeapAccuracy'], 'WeapAccuracy': ['WeapAccuracy','Accuracy'],
    'Comfort': ['Comfort'],
    'speedPenaltyPercent':['speedPenaltyPercent'], 'mousePenalty':['mousePenalty'],
    'weaponErgonomicPenalty':['weaponErgonomicPenalty'], 'dB': ['dB'],
    'Damage': ['Damage'], 'PenetrationPower': ['PenetrationPower'], 'ArmorDamage': ['ArmorDamage'],
    'InitialSpeed': ['InitialSpeed', 'Velocity'], 'FragmentationChance':['FragmentationChance'],
    'RicochetChance': ['RicochetChance']
}

STRING_PRESERVE_KEYS = {'ArmorClass', 'TemplateType', 'ModType', 'WeapType'}

# --- HELPER FUNCTIONS ---

def parse_armor_class_string(s: str) -> float:
    if not isinstance(s, str): return 0.0
    s = s.lower()
    if 'iiia' in s or '3a' in s: return 1.5
    if 'iii+' in s or '3+' in s: return 4.0
    if 'iii' in s or '3' in s: return 3.0
    if 'iv' in s or '4' in s: return 5.0
    if 'ii' in s or '2' in s: return 2.0
    if 'v0' in s or 'v50' in s: return 2.0
    if 'gost 1' in s: return 1.0
    if 'gost 2' in s or 'pm 5' in s: return 2.0
    if 'gost 3' in s or 'pm 8' in s: return 3.0
    if 'gost 4' in s or 'pm 10' in s or 'esapi' in s or 'xsapi' in s: return 4.0
    if 'gost 5' in s: return 5.0
    if 'gost 6' in s: return 6.0
    if 'unclassified' in s: return 2.0
    return 0.0

def to_f(x, d=0.0):
    try: return float(x)
    except: return d

def sanitize_function_name(name: str) -> str:
    s = name.lower()
    s = re.sub(r'&\s*&', ' and ', s)
    s = re.sub(r'[^a-z0-9]+', '_', s)
    s = re.sub(r'_+', '_', s).strip('_')
    return s if s else 'class'

def _normalized_targets(names):
    return {str(n).strip().lower() for n in names if n is not None}

def _build_excluded_targets(args) -> set:
    return EXCLUDED_TARGETS_DEFAULT | _normalized_targets(args.exclude_target or[])

# Ammo does not follow the *Templates.json convention. ammo_v2.json carries the
# real cartridge data (an "info" block of per-field [min, max] bounds and an
# "item" block of 186 cartridges); ammoTemplates.json carries only names,
# LoyaltyLevel and BasePriceModifier - all banned targets - so scanning it
# produced 188 samples with nothing to learn from.
EXTRA_TEMPLATE_FILES = {'ammo_v2.json'}
SKIP_TEMPLATE_FILES = {'ammotemplates.json'}

# Populated by parse_compat_any from ammo_v2.json's "info" block: authoritative
# per-field value ranges from the base-game dump, used to widen prediction clips
# for ammo targets beyond whatever the training sample happened to span.
AMMO_INFO_BOUNDS: Dict[str, Tuple[float, float]] = {}


def find_templates(search_dir: str) -> List[str]:
    found =[]
    for root, _, files in os.walk(search_dir):
        for file in files:
            low = file.lower()
            if low in SKIP_TEMPLATE_FILES:
                continue
            if low.endswith("templates.json") or low in EXTRA_TEMPLATE_FILES:
                found.append(os.path.join(root, file))
    return list(dict.fromkeys(found))

def load_master(path: str) -> List[Dict[str, Any]]:
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    if isinstance(data, dict):
        for k in ('items', 'Items', 'data', 'Data'):
            if k in data:
                data = data[k]
                break

    if isinstance(data, dict):
        out =[]
        for k, v in data.items():
            if isinstance(v, dict):
                v['_id'] = v.get('_id', k)
                out.append(v)
        return out
    elif isinstance(data, list):
        return data
    return []

def build_master_id_map(items: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    return {it.get('_id').lower(): it for it in items if isinstance(it.get('_id'), str)}

def index_master(items: List[Dict[str, Any]], join_key: str) -> Dict[str, Dict[str, Any]]:
    return {it.get(join_key).lower(): it for it in items if isinstance(it.get(join_key), str)}

def parse_compat_any(path: Optional[str]) -> Dict[str, Dict[str, Any]]:
    if not path or not os.path.exists(path): return {}
    try:
        with open(path, 'r', encoding='utf-8') as f: data = json.load(f)
        out: Dict[str, Dict[str, Any]] = {}

        def add(iid, obj):
            if not iid: return
            rid = str(iid).lower()
            if isinstance(obj, dict):
                # Merge, don't replace: an item can be described across more than
                # one section of the same file (see the ammo shape below).
                rec = out.get(rid) or {'ItemID': rid}

                def _extract(d):
                    for k, v in d.items():
                        if isinstance(v, (int, float)):
                            rec[k] = float(v)
                        elif isinstance(v, str) and re.match(r'^[\+\-]?\d+(?:\.\d+)?$', v):
                            rec[k] = float(v)
                        elif k in STRING_PRESERVE_KEYS and isinstance(v, str):
                            rec[k] = v

                ov = obj.get('overrideProperties')
                if isinstance(ov, dict):
                    _extract(ov)
                _extract(obj)
                out[rid] = rec

        if isinstance(data, dict) and "item" in data and "info" in data:
            # ammo_v2.json shape.
            #   "info": {FieldName: [min, max]}  -> value bounds, not records
            #   "item": {Calibre: [ {id, name, ...ballistics}, ... ]}
            info = data.get("info")
            if isinstance(info, dict):
                for fname, rng in info.items():
                    if (isinstance(rng, (list, tuple)) and len(rng) == 2
                            and all(isinstance(x, (int, float)) and not isinstance(x, bool)
                                    for x in rng)):
                        lo, hi = float(rng[0]), float(rng[1])
                        AMMO_INFO_BOUNDS[fname] = (min(lo, hi), max(lo, hi))

            for _calibre, group in (data.get("item") or {}).items():
                if isinstance(group, list):
                    for obj in group:
                        if isinstance(obj, dict):
                            add(obj.get("id") or obj.get("_id") or obj.get("ItemID"), obj)
                elif isinstance(group, dict):
                    for gid, obj in group.items():
                        if isinstance(obj, dict):
                            add(obj.get("id") or obj.get("_id")
                                or obj.get("ItemID") or gid, obj)
            return out

        if isinstance(data, list):
            for obj in data:
                add(obj.get('ItemID') or obj.get('_id'), obj)
        elif isinstance(data, dict):
            for k, v in data.items():
                add(v.get('ItemID') or v.get('_id') or k, v)
        return out
    except Exception: return {}

def resolve_parent_class_id(item: Dict[str, Any], master_by_id: Dict[str, Dict[str, Any]],
                            trace: Optional[List[str]] = None) -> Optional[str]:
    """Walk the handbook/parent chain to a known class id.

    Pass `trace` to capture the ids visited; when resolution fails the last entry
    is the terminal node that PARENT_CLASSES is missing, which is what you need
    to extend the table."""
    pid = item.get('handbookParentId') or item.get('_parent')
    for _ in range(10):
        if not pid: break
        pid_l = pid.lower()
        if trace is not None: trace.append(pid_l)
        if pid_l in CLASS_ID_SET: return pid_l
        parent = master_by_id.get(pid_l)
        if not parent: break
        pid = parent.get('handbookParentId') or parent.get('_parent')
    return None

# Base _props that are pure economy / vendor / UI metadata with no physical meaning.
# NOTE: inventory *geometry* (Width, Height, ExtraSize*) is deliberately NOT blocked - in
# EFT the grid footprint tracks the weapon's real size, so Width proxies barrel / overall
# length (-> velocity range, balance/torque) and ExtraSizeLeft/Right mark a weapon
# extending outward (-> torque, ergonomics). Those are physically meaningful predictors and
# stay in the pool; the correlation gate keeps them out of targets they don't influence.
BASE_FEATURE_BLOCKLIST: Set[str] = {
    # economy / XP / vendor / repair
    'CreditsPrice', 'LootExperience', 'ExamineExperience', 'ExamineTime',
    'RepairCost', 'RepairSpeed', 'MinRepairDegradation', 'MaxRepairDegradation',
    'MinRepairKitDegradation', 'MaxRepairKitDegradation', 'BasePriceModifier',
    'RagFairCommissionModifier', 'DiscardLimit', 'InsuranceDisabled',
    # stack / spawn / UI-only flags
    'StackMaxSize', 'StackObjectsCount', 'StackMinRandom', 'StackMaxRandom',
    'SpawnChance', 'Rarity', 'ExtraSizeForceAdd',
}

def collect_feature_keys(samples: List) -> List[str]:
    keys = set()
    for m, _ in samples:
        for k, v in m.get('_props', {}).items():
            if k in BASE_FEATURE_BLOCKLIST:
                continue
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                keys.add(k)
    return sorted(list(keys))

def is_target_allowed_for_class(target: str, class_name: str, item_type: str) -> bool:
    t = target.lower().strip()
    if t in EXCLUDED_TARGETS_DEFAULT:
        return False

    if t.startswith('mod_') or t.startswith('slot_') or t.endswith('type') or t == 'parent':
        return False
    if t.startswith('weap') and t not in ('weapaccuracy', 'weaponallowads'):
        return False

    if item_type == "Gun":
        # A gun's fire rate is authored by hand and copied straight from the base
        # item; there is nothing here to predict, and every derivation attempted
        # (1:1 copy, class ratio, class constant) was wrong somewhere. Mods keep
        # their AutoROF/SemiROF because those are deltas the mod really applies.
        if t in ('autorof', 'semirof'):
            return False
        return t in GUN_ALLOWED_TARGETS

    if item_type == "Ammo":
        allowed_ammo = {"damage", "penetrationpower", "armordamage", "projectilecount",
                        "initialspeed", "ballisticcoeficient", "ricochetchance", "fragmentationchance",
                        "bulletmassgram", "heavybleedingdelta", "lightbleedingdelta",
                        "ammoaccr", "ammohear", "ammorec", "malfmisfirechance",
                        "misfirechance", "malffeedchance", "durabilityburnmodificator", "heatfactor"}
        return t in allowed_ammo

    if item_type == "WeaponMod":
        # 'BarrelPistol' etc. share their parent class's allow-list.
        base_cls = class_name
        for _suffix in ('Flush', 'Extended', 'Ambi', 'FreeFloat', 'Factory',
                        'Wipe', 'Pistol'):
            if base_cls.endswith(_suffix):
                base_cls = base_cls[:-len(_suffix)]
        if base_cls in MOD_CLASS_ALLOWED_TARGETS:
            return t in MOD_CLASS_ALLOWED_TARGETS[base_cls]

    if t in ('meleedamage', 'meleepen'):
        return False

    if class_name == "ArmorPlates":
        allowed = ["allowads", "reloadspeedmulti", "canspall", "spallreduction"]
        if not any(a in t for a in allowed): return False
    if class_name == "ArmorMasks":
        allowed = ["allowads", "canspall", "spallreduction", "reloadspeedmulti", "blocksmouth"]
        if not any(a in t for a in allowed): return False
    if class_name == "Headset":
        allowed =["allowads", "db", "speedpenaltypercent", "mousepenalty", "weaponergonomicpenalty"]
        if not any(a in t for a in allowed): return False
    if class_name == "Headwear":
        allowed =["allowads", "canspall", "spallreduction", "reloadspeedmulti", "comfort",
                   "speedpenaltypercent", "mousepenalty", "weaponergonomicpenalty"]
        if not any(a in t for a in allowed): return False
    if class_name == "Backpacks":
        allowed =["allowads", "reloadspeedmulti", "comfort", "speedpenaltypercent",
                   "mousepenalty", "weaponergonomicpenalty"]
        if not any(a in t for a in allowed): return False

    return True

# --- CORE LOGIC ---

def engineer_features_from_item(base_item_data: Dict[str, Any], template_data: Dict[str, Any] = None) -> Dict[str, float]:
    if template_data is None: template_data = {}
    engineered = {}
    props = base_item_data.get('_props', base_item_data)
    # WTT-commonlib mods store their real stats in overrideProperties (each key overrides the
    # cloned base item's prop; anything absent falls back to the base). Merge scalar overrides
    # over the base props so feature engineering sees the *effective* item, not just the base.
    _ov = base_item_data.get('overrideProperties')
    if isinstance(_ov, dict):
        props = {**props, **{_k: _v for _k, _v in _ov.items() if isinstance(_v, (int, float, str, bool))}}

    weight = to_f(props.get('Weight', 0.0))
    ergo = to_f(props.get('Ergonomics', 0.0))
    durability = to_f(props.get('MaxDurability', 100.0))

    name_str = ' '.join(str(base_item_data.get(_k, '') or '')for _k in ('_preset_hint', 'Name', '_name', 'shortName')).lower()
    caliber_field = str(props.get('Caliber', props.get('ammoCaliber', ''))).lower()
    weap_class = str(props.get('weapClass', props.get('WeapClass', ''))).lower()
    weap_use_type = str(props.get('weapUseType', props.get('WeapUseType', ''))).lower()
    reload_mode = str(props.get('ReloadMode', props.get('reloadMode', ''))).lower()
    fire_type = str(props.get('weapFireType', props.get('WeapFireType', ''))).lower()

    barrel_length_mm = 0.0
    mm_match = re.search(r'(\d+(?:\.\d+)?)mm', name_str)
    inch_match = re.search(r'(\d+(?:[.,]\d+)?)(?:_|-|\s)?inch', name_str)

    if mm_match:
        barrel_length_mm = float(mm_match.group(1))
    elif inch_match:
        barrel_length_mm = float(inch_match.group(1).replace(',', '.')) * 25.4

    engineered['BarrelLengthMM'] = barrel_length_mm

    # Prefer the exact calibre resolved from the item's slot graph (see
    # build_caliber_index). The name regex below is only a fallback: on mods it
    # happily reads a model number as a bore, turning barrel_ar15_260mm into
    # 15.0mm and barrel_mr133_610mm into 1.33mm.
    caliber_numeric = float(CALIBER_BY_ITEM_ID.get(
        str(base_item_data.get('_id', '') or '').lower(), 0.0) or 0.0)
    if caliber_numeric:
        pass
    elif '12g' in name_str or '12 gauge' in name_str or '12/70' in name_str or '12g' in caliber_field:
        caliber_numeric = 18.5
    elif '20g' in name_str or '20 gauge' in name_str or '20/70' in name_str or '20g' in caliber_field:
        caliber_numeric = 15.6
    elif '23x75' in name_str or '23x75' in caliber_field:
        caliber_numeric = 23.0
    elif '300blk' in name_str or 'blackout' in name_str or '300 black' in name_str:
        caliber_numeric = 7.62
    
    elif '5.56' in name_str or '556' in name_str or '5.56' in caliber_field:
        caliber_numeric = 5.56
    elif '5.45' in name_str or '545' in name_str or '5.45' in caliber_field:
        caliber_numeric = 5.45
    elif '7.62' in name_str or '762' in name_str or '7.62' in caliber_field:
        caliber_numeric = 7.62
    elif any(x in name_str for x in ('9x19', '9x18', '9x21', '9x39', '9mm', '9x33')) or '9x' in caliber_field or '9mm' in caliber_field:
        caliber_numeric = 9.0
    elif any(x in name_str for x in ('.45', '1143', 'acp')) or '.45' in caliber_field or '1143' in caliber_field:
        caliber_numeric = 11.43
    elif '4.6x' in name_str or '46x30' in caliber_field:
        caliber_numeric = 4.6
    elif '5.7x' in name_str or '57x28' in caliber_field:
        caliber_numeric = 5.7
    elif '.338' in name_str or 'lapua' in name_str:
        caliber_numeric = 8.6
    elif '.357' in name_str:
        caliber_numeric = 9.1
    elif '.44' in name_str or ('magnum' in name_str and '357' not in name_str):
        caliber_numeric = 10.9
    elif '6.8x' in name_str or '68x51' in name_str or '.277' in name_str or 'fury' in name_str:
        caliber_numeric = 6.8
    elif '12.7x' in name_str or '127x55' in caliber_field:
        caliber_numeric = 12.7
    elif '.366' in name_str or 'tkm' in name_str or '366' in caliber_field:
        caliber_numeric = 9.55
    else:
        cal_m = re.search(r'(?<!\d)(\d+(?:\.\d+)?)[x_]\d+', name_str)
        if cal_m:
            caliber_numeric = float(cal_m.group(1))
            if caliber_numeric in (762, 556, 545):
                caliber_numeric = {762: 7.62, 556: 5.56, 545: 5.45}[int(caliber_numeric)]
            elif caliber_numeric > 100:
                caliber_numeric /= 100.0

    engineered['CaliberNumeric'] = caliber_numeric

    # Magazine capacity lives inside props['Cartridges'][0]['_max_count'], which
    # the flat base-prop scan never reaches, so the fit had no way to see it.
    # Within a single size class it is the dominant driver of ReloadSpeed --
    # among standard-height mags the class means run +0.51 (16-30 rounds),
    # -6.50 (31-50) and -12.09 (51+). Log scale because the step from 30 to 60
    # matters far more than 60 to 90.
    _mag_cap = 0.0
    _carts = props.get('Cartridges')
    if isinstance(_carts, list) and _carts and isinstance(_carts[0], dict):
        _mc = _carts[0].get('_max_count')
        if isinstance(_mc, (int, float)) and not isinstance(_mc, bool):
            _mag_cap = float(_mc)
    engineered['MagCapacity'] = _mag_cap
    engineered['LogMagCapacity'] = math.log1p(max(0.0, _mag_cap))

    dura_factor = 1.0 - (durability / 100.0) if durability > 0 else 1.0
    engineered['DurabilityMalfRisk'] = pow(max(0.0, dura_factor), 2.0)
    engineered['DurabilityBurnMod'] = to_f(props.get('DurabilityBurnModificator', 1.0))

    engineered['LogWeight'] = math.log1p(max(0, weight))
    engineered['LogErgo'] = math.log1p(max(0, ergo))

    engineered['IsShort'] = 1.0 if 'short' in name_str else 0.0
    engineered['IsLong'] = 1.0 if 'long' in name_str else 0.0
    engineered['IsHeavy'] = 1.0 if 'heavy' in name_str or weight > 0.6 else 0.0
    engineered['IsLight'] = 1.0 if 'light' in name_str or (0 < weight < 0.15) else 0.0

    muzzle_mod_type = str(props.get('muzzleModType', '')).lower()
    engineered['IsSuppressor'] = 1.0 if muzzle_mod_type in ('silencer', 'pms') or any(x in name_str for x in['suppressor', 'silencer', 'sound']) else 0.0
    engineered['IsBrake'] = 1.0 if muzzle_mod_type in ('brake', 'conpensator', 'muzzlecombo') or any(x in name_str for x in ['brake', 'compensator', 'flash']) else 0.0
    engineered['IsAdapter'] = 1.0 if 'adapter' in name_str or 'thread' in name_str else 0.0
    engineered['IsCombo'] = 1.0 if muzzle_mod_type == 'muzzlecombo' else 0.0

    sr = to_f(props.get('SightingRange', 0.0))
    engineered['SightingRange'] = sr
    engineered['IsMagnified'] = 1.0 if sr > 400 or any(x in name_str for x in['scope', '4x', '6x', '8x', 'lpvo', 'acog', 'pso', 'leupold', 'nightforce', 'march', 'hensoldt', 'vortex', 's&b']) else 0.0
    engineered['IsCollimator'] = 1.0 if 50 < sr <= 400 or any(x in name_str for x in['red dot', 'holo', 'collimator', 'reflex', 'eotech', 'aimpoint', 'trijicon rmr', 'romeo']) else 0.0

    cartridges = props.get('Cartridges',[])
    cap = 0.0
    if cartridges and isinstance(cartridges, list) and isinstance(cartridges[0], dict):
        cap = float(cartridges[0].get('_max_count', 0))
    if cap == 0.0:
        m_cap = re.search(r'(\d+)[- ]?(?:round|rnd)', name_str)
        if m_cap:
            cap = float(m_cap.group(1))
    engineered['CapacityGuess'] = cap

    engineered['IsDrum'] = 1.0 if 'drum' in name_str else 0.0

    armor_class_val = template_data.get('ArmorClass')
    if not armor_class_val:
        armor_class_val = props.get('armorClass', props.get('ArmorClass', ''))
    engineered['ArmorClassNumeric'] = parse_armor_class_string(str(armor_class_val))

    db_val = template_data.get('dB')
    if db_val is not None:
        engineered['LoudnessHint'] = to_f(db_val)
    else:
        engineered['LoudnessHint'] = to_f(props.get('Loudness', props.get('dB', 0.0)))

    total_cells = sum(
        int(g.get('_props', {}).get('cellsH', 0)) * int(g.get('_props', {}).get('cellsV', 0))
        for g in props.get('Grids', []) if isinstance(g, dict)
    )
    engineered['GridCells'] = float(total_cells)

    # Total horizontal grid footprint ~ overall weapon length in cells. Width is the base
    # length; ExtraSizeLeft/Right extend it (folding stocks, long barrels, muzzle devices).
    # Physically this proxies barrel / overall length, which drives muzzle velocity range,
    # balance/torque (front-heaviness) and handling/ergonomics.
    engineered['WeaponFootprint'] = (
        to_f(props.get('Width', 0.0))
        + to_f(props.get('ExtraSizeLeft', 0.0))
        + to_f(props.get('ExtraSizeRight', 0.0))
    )

    bfire = to_f(props.get('bFirerate', 0.0))
    engineered['FireRateRPM'] = bfire

    is_shotgun = 1.0 if ('12g' in name_str or '20g' in name_str or '23x75' in name_str
                         or 'shotgun' in name_str or 'buckshot' in name_str or 'slug' in name_str
                         or 'shotgun' in caliber_field or '12g' in caliber_field
                         or '20g' in caliber_field or '23x75' in caliber_field
                         or 'shotgun' in weap_class or 'shotgun' in weap_use_type) else 0.0

    gauge_numeric = 0.0
    if '23x75' in name_str or '23x75' in caliber_field: gauge_numeric = 23.0
    elif '12g' in name_str or '12 gauge' in name_str or '12/70' in name_str or '12g' in caliber_field: gauge_numeric = 12.0
    elif '20g' in name_str or '20 gauge' in name_str or '20/70' in name_str or '20g' in caliber_field: gauge_numeric = 20.0

    engineered['IsShotgun'] = is_shotgun
    engineered['GaugeNumeric'] = gauge_numeric

    is_bolt = bool(props.get('BoltAction', False))
    is_only_barrel = 'onlybarr' in reload_mode

    engineered['IsPumpAction'] = 1.0 if (
        ('internal' in reload_mode and bfire <= 40)
        or 'pump' in name_str
        or is_bolt
    ) else 0.0

    engineered['IsManuallyOperatedGun'] = 1.0 if (
        is_only_barrel or is_bolt or (0 < bfire <= 30)
    ) else 0.0

    engineered['IsSemiAutoShotgun'] = 1.0 if ('semi' in name_str or 'semi' in fire_type) and is_shotgun else 0.0
    engineered['IsTubeFed'] = 1.0 if ('tubefed' in reload_mode or 'tube' in name_str) and is_shotgun else 0.0

    choke_tightness = 0.0
    if any(x in name_str for x in ['cylinder bore', 'cylinder']): choke_tightness = -0.35
    elif 'improved cylinder' in name_str: choke_tightness = -0.15
    elif 'improved modified' in name_str: choke_tightness = 0.28
    elif 'modified' in name_str: choke_tightness = 0.15
    elif any(x in name_str for x in ['extra full', 'turkey']): choke_tightness = 0.55
    elif any(x in name_str for x in['full choke', 'full']): choke_tightness = 0.40
    engineered['ChokeTightness'] = choke_tightness

    return engineered


dummy_eng = engineer_features_from_item({'_props': {}}, {})
ALL_ENG_KEYS = set(dummy_eng.keys())


# --- Physical feature affinity (per-target causal gating) ---
# Correlation ranking alone cannot distinguish causation from correlation, and on small
# per-class samples it will pick correlated-but-non-causal features - e.g. LootExperience
# correlates +0.72 with barrel Velocity and -0.90 with HeatFactor simply because longer
# barrels are rarer. Where the real-world causal drivers of a target are known, we restrict
# its candidate pool to features whose name matches one of these physical families
# (case-insensitive substring). Targets with NO entry fall through to unrestricted
# correlation ranking, so the map is purely additive. Families are deliberately generous
# unions (a target may be driven by different props on a gun vs a barrel) - the correlation
# gate then trims within the physically-allowed set.
_SIZE   = {'width', 'extrasize', 'weaponfootprint', 'barrellengthmm', 'islong', 'isshort'}
_MASS   = {'weight', 'logweight', 'isheavy', 'islight'}
_RECOIL = {'recoil', 'recoilforceup', 'recoilforceback'}   # 'recoil' substring covers RecoilCamera etc.
_CAL    = {'calibernumeric', 'gaugenumeric'}
TARGET_FEATURE_AFFINITY: Dict[str, Set[str]] = {
    'basetorque':                _SIZE | _MASS,
    'velocity':                  _SIZE | _CAL | {'velocity'},
    'verticalrecoil':            _RECOIL | _SIZE | _MASS | _CAL,
    'horizontalrecoil':          _RECOIL | _SIZE | _MASS | _CAL,
    'camerarecoil':              _RECOIL | _SIZE | _MASS | _CAL,
    'recoilangle':               _RECOIL | _SIZE | _CAL,
    'convergence':               _SIZE | _MASS | {'recoil'},
    'ergonomics':                _SIZE | _MASS,
    'heatfactor':                _SIZE | _MASS | _CAL | {'velocity', 'heatfactor'},
    'heatfactorgun':             _SIZE | _MASS | _CAL | {'velocity', 'heatfactor'},
    'coolfactor':                _SIZE | _MASS | _CAL | {'velocity', 'coolfactor', 'heatfactor'},
    'coolfactorgun':             _SIZE | _MASS | _CAL | {'velocity', 'coolfactor', 'heatfactor'},
    'durabilityburnmodificator': _SIZE | _MASS | _CAL | {'durabilityburn', 'heatfactor'},
    'durabilityburnratio':       _SIZE | _MASS | _CAL | {'durabilityburn', 'heatfactor'},
    'centerofimpact':            _SIZE | {'centerofimpact', 'deviation'},
    'dispersion':                _SIZE | _CAL | {'deviation', 'dispersion', 'centerofimpact'},
    'loudness':                  _SIZE | _CAL | {'loudness', 'issuppressor', 'isbrake'},
    'flash':                     _CAL | {'flash', 'issuppressor', 'isbrake', 'issilencer'},
}

def _affinity_ok(target_name: str, feature_name: str) -> bool:
    fam = TARGET_FEATURE_AFFINITY.get(str(target_name).lower())
    if not fam:
        return True  # no known causal restriction -> allow (correlation gate still applies)
    fl = feature_name.lower()
    return any(tok in fl for tok in fam)


def _fit_zero_gate(X: np.ndarray, y: np.ndarray, feature_keys: List[str],
                   target_name: str = ''):
    """Stage 1 of the hurdle model: does this item get a value for this target?

    Fits a linear discriminant on the binary indicator |y| > 0 using features
    chosen for their correlation with that indicator (which is NOT the same set
    that predicts the magnitude). Returns None unless the gate is meaningfully
    better than always guessing the majority class - a gate that just reproduces
    'everything is non-zero' adds risk without adding information.
    """
    n = len(y)
    is_real = (np.abs(y) > 1e-5).astype(float)
    n_real = int(is_real.sum())
    n_zero = n - n_real

    # Need a genuine mix, and enough of the minority class to fit anything.
    if n_real < 4 or n_zero < 4 or n < 12:
        return None

    baseline = max(n_real, n_zero) / float(n)

    # Rank features by correlation with the ZERO/NON-ZERO decision.
    cand = []
    tgt = is_real - is_real.mean()
    tgt_sd = float(np.std(is_real))
    if tgt_sd < 1e-12:
        return None
    for col in range(X.shape[1] - 1):
        f = feature_keys[col + 1]
        if not _affinity_ok(target_name, f):
            continue
        x = X[:, col + 1]
        sx = float(np.std(x))
        if sx < 1e-12:
            continue
        r = float(np.dot(x - x.mean(), tgt) / (n * sx * tgt_sd))
        if np.isfinite(r) and abs(r) > 0.12:
            cand.append((abs(r), col))
    if not cand:
        return None
    cand.sort(reverse=True)

    used, k_max = [], min(4, max(1, n // 12))
    for _, col in cand:
        if len(used) >= k_max:
            break
        xi = X[:, col + 1]
        if any(abs(np.corrcoef(xi, X[:, j + 1])[0, 1]) > 0.90 for j in used
               if float(np.std(X[:, j + 1])) > 1e-12):
            continue
        used.append(col)

    Xu = X[:, [j + 1 for j in used]]
    mu = Xu.mean(axis=0)
    sigma = Xu.std(axis=0)
    sigma[sigma < 1e-12] = 1.0
    Xs = (Xu - mu) / sigma

    # Fit with and without class re-weighting and keep whichever satisfies the
    # contract best. Plain weighting is maximised by "always valued" on lopsided
    # targets (RicochetChance is 154 valued vs 13 zeroed), which is the behaviour
    # the gate exists to stop; balanced weighting over-corrects on others and
    # starts deleting real values. Neither wins everywhere, so measure both.
    MIN_ZERO_RECALL = 0.50   # catch at least half the zeros
    MIN_REAL_RECALL = 0.85   # keep at least 85% of the real values
    MIN_BALANCED_ACC = 0.70

    best_gate = None
    for _weight in (None, 'balanced'):
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                clf = LogisticRegression(max_iter=1000, C=1.0,
                                         class_weight=_weight).fit(Xs, is_real)
            score = clf.intercept_[0] + Xs.dot(clf.coef_[0])
            pred_real = (score > 0).astype(float)
            acc = float(np.mean(pred_real == is_real))
            recall_zero = float(np.mean(pred_real[is_real == 0.0] == 0.0))
            recall_real = float(np.mean(pred_real[is_real == 1.0] == 1.0))
            bal_acc = 0.5 * (recall_zero + recall_real)
        except Exception:
            continue

        # Explicit contract rather than a single score: leaking a stat onto a
        # zeroed item and deleting a real one are both failures, so both
        # directions get a floor.
        if (recall_zero < MIN_ZERO_RECALL or recall_real < MIN_REAL_RECALL
                or bal_acc < MIN_BALANCED_ACC):
            continue
        cand = {'intercept': float(clf.intercept_[0]),
                'coef': [float(c) for c in clf.coef_[0]],
                'used_idx': used, 'mu': mu.tolist(), 'sigma': sigma.tolist(),
                'acc': acc, 'bal_acc': bal_acc, 'recall_zero': recall_zero,
                'recall_real': recall_real, 'baseline': baseline,
                'weight': _weight or 'none',
                'n_zero': n_zero, 'n_real': n_real}
        if best_gate is None or cand['bal_acc'] > best_gate['bal_acc']:
            best_gate = cand

    return best_gate


def _fit_single_target_strategies(X: np.ndarray, y: np.ndarray, is_int: bool,
                                   feature_keys: List[str], target_name: str = '',
                                   value_bounds: Optional[Tuple[float, float]] = None):
    n, p = X.shape
    if n < 2: return None

    median_val = float(np.median(y))
    median_mae = float(np.mean(np.abs(y - median_val)))

    non_zero_mask = np.abs(y) > 1e-5
    n_nonzero = int(np.sum(non_zero_mask))

    # HURDLE MODEL, STAGE 2 of 2.
    #
    # Realism mod templates are sparse by design: the author decides first
    # *whether* a mod touches a stat at all (most of the time it does not, and
    # they write an explicit 0), and only then by how much. Fitting the magnitude
    # on the non-zero rows alone - which is what the branch below does - is the
    # right way to learn "by how much". But applying that magnitude model to every
    # item means the zeros never come back: a linear fit trained only on real
    # values essentially never returns 0, so the emitted formula wrote a stat onto
    # every item the author had deliberately zeroed (100% zero-leak on Handguard
    # VerticalRecoil, Barrel Velocity, ChargingHandle ChamberSpeed and ~30 more).
    #
    # The missing stage is the decision itself. _fit_zero_gate below fits a linear
    # discriminant for "does this item get a value at all", and it is emitted as a
    # guard in front of the magnitude expression. Where no gate can be learned the
    # behaviour is unchanged.
    if n_nonzero >= max(3, int(n * 0.1)) and n_nonzero < n:
        X_eval = X[non_zero_mask]
        y_eval = y[non_zero_mask]
    else:
        X_eval = X
        y_eval = y

    y_eval_std = float(np.std(y_eval))

    if y_eval_std < 1e-6:
        # HARD_FLOOR_ZERO encodes *gun* semantics: on a weapon, Dispersion /
        # ModMalfunctionChance / AutoROF etc. are absolute quantities that cannot
        # go negative. On a *mod* the same field names are signed deltas (a
        # handguard that removes 1 dispersion, a suppressor that removes 11.7
        # malfunction chance). Only apply the floor when the class's own authored
        # data agrees with it - otherwise the clip throws away a correctly-signed fit.
        _floor_ok = target_name in HARD_FLOOR_ZERO and median_val >= 0.0
        clip_lo = max(0.0, median_val) if _floor_ok else median_val
        clip_hi = median_val
        if value_bounds:
            clip_lo = min(clip_lo, float(value_bounds[0]))
            clip_hi = max(clip_hi, float(value_bounds[1]))
        return {'beta_std':[median_val], 'used_idx': [], 'mu': [], 'sigma':[],
                'transform': 'identity', 'mae': 0.0, 'score': 0.0,
                'clip_lo': clip_lo, 'clip_hi': clip_hi, 'n_samples': int(n)}

    cors = []
    for col in range(X.shape[1] - 1):
        x_col = X_eval[:, col + 1]
        sx = float(np.std(x_col))
        if sx < 1e-12:
            cors.append(0.0)
            continue
        xm = x_col - float(np.mean(x_col))
        ym = y_eval - float(np.mean(y_eval))
        r = float(np.dot(xm, ym) / (len(x_col) * sx * y_eval_std))
        cors.append(abs(r) if np.isfinite(r) else 0.0)

    # These classes routinely train on 3-40 samples, where |corr| ~ 1/sqrt(n) arises from
    # pure noise. The old threshold of 0.05 (plus a forced minimum of 6 features) meant the
    # regressions memorised noise. Cap feature count to ~n/5 and require a real correlation.
    n_eff = len(y_eval)
    CORR_MIN = 0.20         # was 0.05 - below this a raw base prop is indistinguishable from noise
    PRESET_CORR_MIN = 0.10  # engineered/preset features are physically meaningful -> lower bar
    HARD_CAP = 8
    # Keep feature count safely below sample count (features < n) so we never hit the
    # perfect-interpolation overfitting that p>=n causes, while still retaining enough
    # predictors for genuinely multi-driver targets (recoil, for instance, is driven by
    # BOTH the up-force and back-force base props). ~n/2 balances those two pressures;
    # n/5 was over-corrected and starved real signal on small per-class datasets.
    max_k = min(p - 1, HARD_CAP, max(1, n_eff // 2))
    small_sample = n < 10

    # Rank all features by correlation strength and take the top max_k. Preset/engineered
    # features get a lower *entry threshold* (they're physically meaningful) but do NOT
    # jump the queue ahead of a stronger raw predictor. The old "presets first" rule let
    # LogWeight/LogErgo crowd out the actual driver - e.g. RecoilForceBack for recoil,
    # which is exactly the base->template relationship these formulas need to capture.
    candidates = []
    for i in range(len(cors)):
        f = feature_keys[i + 1]
        if not _affinity_ok(target_name, f):
            continue  # feature is not a physically-plausible driver of this target
        thr = PRESET_CORR_MIN if f in PRESET_KEYWORDS else CORR_MIN
        if cors[i] > thr:
            candidates.append(i)
    candidates.sort(key=lambda i: -cors[i])
    # Greedy selection with a collinearity guard: candidates are ordered by correlation with
    # the target, so we keep the strongest of any near-collinear group and skip the rest.
    # Physical proxies (Width, WeaponFootprint, ExtraSizeLeft, LogWeight...) are all length
    # surrogates and highly correlated with each other; stacking them just inflates
    # coefficients and hurts extrapolation. Exact-dup dedup runs earlier; this catches the
    # >0.92-correlated-but-not-identical case.
    used_idx = []
    for idx in candidates:
        if len(used_idx) >= max_k:
            break
        xi = X_eval[:, idx + 1]
        if float(np.std(xi)) < 1e-12:
            continue
        redundant = False
        for j in used_idx:
            xj = X_eval[:, j + 1]
            if float(np.std(xj)) < 1e-12:
                continue
            rr = np.corrcoef(xi, xj)[0, 1]
            if np.isfinite(rr) and abs(rr) > 0.90:
                redundant = True
                break
        if not redundant:
            used_idx.append(idx)

    X_used = X_eval[:, [j + 1 for j in used_idx]]

    if X_used.shape[1] > 0:
        mu = X_used.mean(axis=0)
        sigma = X_used.std(axis=0)
        sigma[sigma < 1e-12] = 1.0
        Xs = (X_used - mu) / sigma
    else:
        Xs, mu, sigma = np.zeros((len(y_eval), 0)), [],[]

    def eval_candidate(beta_std: np.ndarray, transform: str):
        z = beta_std[0] + (Xs.dot(beta_std[1:]) if Xs.shape[1] > 0 else 0)
        yhat = z
        err = np.round(yhat) - np.round(y_eval) if is_int else yhat - y_eval
        return float(np.mean(np.abs(err))), float(np.max(np.abs(err)))

    median_eval_mae = float(np.mean(np.abs(y_eval - np.median(y_eval))))
    best = {'beta_std': [float(np.median(y_eval))], 'used_idx': [], 'mu':[], 'sigma':[],
            'transform': 'identity', 'mae': median_eval_mae, 'score': median_eval_mae}

    alpha_grid = (0.001, 0.01, 0.1, 1.0, 10.0)
    strategies =[('ols', 'identity', None, None)]
    for a in alpha_grid:
        strategies.append(('ridge', 'identity', a, None))
        strategies.append(('elastic', 'identity', a, 0.5))
        strategies.append(('huber', 'identity', a, None))

    for model_name, transform, alpha, l1 in strategies:
        if Xs.shape[1] == 0:
            break  # no features survived affinity/collinearity/threshold -> keep median constant
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            if model_name == 'ols': reg = LinearRegression(fit_intercept=True).fit(Xs, y_eval)
            elif model_name == 'ridge': reg = Ridge(alpha=alpha, fit_intercept=True).fit(Xs, y_eval)
            elif model_name == 'elastic': reg = ElasticNet(alpha=alpha, l1_ratio=l1, fit_intercept=True).fit(Xs, y_eval)
            elif model_name == 'huber': reg = HuberRegressor(alpha=alpha, fit_intercept=True, max_iter=500).fit(Xs, y_eval)
            else: continue

        coef = [float(reg.intercept_)] +[0.0 if abs(c) < 1e-5 else float(c) for c in reg.coef_]
        mae, maxae = eval_candidate(np.asarray(coef), transform)

        complexity = sum(1 for c in coef[1:] if abs(c) > 1e-5)
        preset_count = sum(1 for b, j in zip(coef[1:], used_idx) if abs(b) > 1e-5 and feature_keys[j + 1] in PRESET_KEYWORDS)

        complexity_penalty = 0.20 if small_sample else 0.10
        score = mae * (1.0 + complexity_penalty * complexity)
        if preset_count > 0:
            score *= (0.5 ** preset_count)

        if score < best['score'] and maxae < (y_eval_std * 3.0 + 10.0):
            best = {'beta_std': coef, 'used_idx': used_idx, 'mu': mu.tolist(),
                    'sigma': sigma.tolist(), 'transform': transform, 'mae': mae, 'score': score}

    y_min, y_max = float(np.min(y)), float(np.max(y))
    spread = max(1e-6, y_max - y_min)
    clip_lo = y_min - (0.1 * spread)
    clip_hi = y_max + (0.1 * spread)

    # For ammo, ammo_v2.json's "info" block gives the authoritative range the base
    # game spans for this field. A custom cartridge is explicitly allowed to sit
    # outside it, so union the dump range with the sample range rather than
    # clamping to either - this only ever widens the clip, never narrows it.
    if value_bounds:
        clip_lo = min(clip_lo, float(value_bounds[0]))
        clip_hi = max(clip_hi, float(value_bounds[1]))

    # See the note on the constant path above: the zero floor is only valid when
    # the observed training values for THIS class never go negative. Asserting it
    # against negative mod deltas silently forced ~12 targets to a constant 0
    # (Dispersion on Handguard/Foregrip/PistolGrip/Stock/Gasblock/Barrel/
    # MuzzleBrakes/Suppressors, ModMalfunctionChance on Suppressors/Receiver,
    # AutoROF/SemiROF on MuzzleBrakes).
    if target_name in HARD_FLOOR_ZERO and y_min >= 0.0:
        clip_lo = max(0.0, clip_lo)

    best['clip_lo'] = clip_lo
    best['clip_hi'] = clip_hi
    best['n_samples'] = int(n)
    gate = _fit_zero_gate(X, y, feature_keys, target_name)
    if gate:
        best['zero_gate'] = gate
    return best


RATE_PASSTHROUGH_SOURCES = {
    'AutoROF': 'bFirerate',
    'SemiROF': 'SingleFireRate',
}


def _has_fullauto(master_item: Dict[str, Any]) -> bool:
    """True when the gun actually has a full-auto fire mode."""
    props = master_item.get('_props', {}) or {}
    modes = props.get('weapFireType') or props.get('WeapFireType') or []
    if isinstance(modes, str):
        modes = [modes]
    return any('fullauto' in str(m).lower().replace(' ', '').replace('_', '')
               for m in modes if m is not None)


def _best_rate_rule(pairs: List[Tuple[float, float]]):
    """Best of three derivations of an authored rate from its base-game prop.

        copy   value = base
        ratio  value = base * median(authored / base)
        const  value = median(authored)

    Returns (mode, param, mae, lo, hi) or None.
    """
    if len(pairs) < 3:
        return None
    ys = [v for _, v in pairs]
    med_ratio = float(np.median([v / b for b, v in pairs]))
    med_val = float(np.median(ys))

    options = [
        ('copy', 1.0, float(np.mean([abs(b - v) for b, v in pairs]))),
        ('ratio', med_ratio, float(np.mean([abs(round(b * med_ratio) - v) for b, v in pairs]))),
        ('const', med_val, float(np.mean([abs(round(med_val) - v) for b, v in pairs]))),
    ]
    mode, param, mae = min(options, key=lambda o: o[2])
    # Generous bounds - these exist to stop wild extrapolation on a custom gun
    # whose base prop sits far outside the class, not to pin it to the class range.
    return mode, param, mae, min(ys) * 0.75, max(ys) * 1.25


def _fit_rate_passthrough(samples: List[Tuple[Dict, Dict]], target: str, src_prop: str):
    """Pick how a gun's fire-rate target derives from its base-game prop.

    The original rule was an unconditional 1:1 copy. Measured against the authored
    Realism templates that is wrong in every class for SemiROF (bias equal to MAE -
    over on every gun, because Realism authors a hand-tuned trigger-pull ceiling
    rather than mirroring SingleFireRate).

    AutoROF needs a second axis: on a semi-only gun the base bFirerate is a junk
    placeholder (the PM carries 30) so no single rule fits both populations. When
    splitting on weapFireType measurably beats the ungated fit, emit both branches.
    """
    auto_pairs, semi_pairs = [], []
    for m, rec in samples:
        v = rec.get(target)
        b = m.get('_props', {}).get(src_prop)
        if (isinstance(v, (int, float)) and not isinstance(v, bool)
                and isinstance(b, (int, float)) and not isinstance(b, bool) and b > 0):
            (auto_pairs if _has_fullauto(m) else semi_pairs).append((float(b), float(v)))

    all_pairs = auto_pairs + semi_pairs
    if len(all_pairs) < 3:
        return None
    ys = [v for _, v in all_pairs]
    if max(ys) - min(ys) < 1e-9 and abs(max(ys)) < 1e-9:
        return None  # class genuinely has no value for this target (bolt guns)

    ungated = _best_rate_rule(all_pairs)
    if not ungated:
        return None
    u_mode, u_param, u_mae, u_lo, u_hi = ungated
    mae_copy = float(np.mean([abs(b - v) for b, v in all_pairs]))

    base = {'src': src_prop, 'n': len(all_pairs), 'mae_copy': mae_copy}

    a_rule = _best_rate_rule(auto_pairs)
    s_rule = _best_rate_rule(semi_pairs)
    if a_rule and s_rule:
        gated_mae = ((a_rule[2] * len(auto_pairs) + s_rule[2] * len(semi_pairs))
                     / len(all_pairs))
        # Require a real margin: splitting halves the sample count per branch, so a
        # marginal gain is more likely noise than signal.
        if gated_mae < u_mae * 0.85:
            base.update({'mode': 'gated', 'mae': gated_mae,
                         'auto': {'mode': a_rule[0], 'param': a_rule[1], 'mae': a_rule[2],
                                  'n': len(auto_pairs), 'lo': a_rule[3], 'hi': a_rule[4]},
                         'semi': {'mode': s_rule[0], 'param': s_rule[1], 'mae': s_rule[2],
                                  'n': len(semi_pairs), 'lo': s_rule[3], 'hi': s_rule[4]}})
            return base

    base.update({'mode': u_mode, 'param': u_param, 'mae': u_mae, 'lo': u_lo, 'hi': u_hi})
    return base


def _emit_rate_rule(indent: str, target: str, src: str, rule: Dict[str, Any]) -> List[str]:
    """One derivation branch: assigns item_entry[target] from the base prop."""
    if rule['mode'] == 'const':
        return [
            f'{indent}if isinstance(template, dict) and "{target}" in template and to_f(template["{target}"]) > 0:',
            f'{indent}    item_entry["{target}"] = int(to_f(template["{target}"]))',
            f'{indent}else:',
            f'{indent}    item_entry["{target}"] = int(round({rule["param"]:.6g}))',
        ]
    return [
        f'{indent}if _rate_src is not None and to_f(_rate_src) > 0:',
        f'{indent}    _rate = to_f(_rate_src) * {rule["param"]:.6g}',
        f'{indent}    item_entry["{target}"] = int(round(min(max(_rate, {rule["lo"]:.6g}), {rule["hi"]:.6g})))',
        f'{indent}elif isinstance(template, dict) and "{target}" in template:',
        f'{indent}    item_entry["{target}"] = int(to_f(template["{target}"]))',
    ]


def _emit_rate_block(indent: str, target: str, spec: Dict[str, Any]) -> List[str]:
    src = spec['src']
    L = [f"\n{indent}# {target}: derived from base {src} -- strategy '{spec['mode']}' "
         f"(fit MAE {spec['mae']:.1f} RPM over {spec['n']} items; 1:1 copy scored {spec['mae_copy']:.1f})"]
    L.append(f'{indent}_rate_src = explicit_override_value(base_data, ["{src}"])')
    L.append(f'{indent}if _rate_src is None: _rate_src = props.get("{src}")')

    if spec['mode'] != 'gated':
        L.extend(_emit_rate_rule(indent, target, src, spec))
        return L

    a, sm = spec['auto'], spec['semi']
    L.append(f'{indent}# Split on fire mode: the base {src} is a placeholder on semi-only')
    L.append(f'{indent}# guns, so one rule cannot serve both populations.')
    L.append(f'{indent}_fire_modes = props.get("weapFireType") or props.get("WeapFireType") or []')
    L.append(f'{indent}if isinstance(_fire_modes, str): _fire_modes = [_fire_modes]')
    L.append(f'{indent}_is_auto = any("fullauto" in str(_fm).lower().replace(" ", "").replace("_", "")')
    L.append(f'{indent}               for _fm in _fire_modes if _fm is not None)')
    L.append(f'{indent}if _is_auto:   # {a["mode"]}, MAE {a["mae"]:.1f} over {a["n"]} full-auto guns')
    L.extend(_emit_rate_rule(indent + '    ', target, src, a))
    L.append(f'{indent}else:          # {sm["mode"]}, MAE {sm["mae"]:.1f} over {sm["n"]} semi-only guns')
    L.extend(_emit_rate_rule(indent + '    ', target, src, sm))
    return L


ROUND_HALF_TARGETS = {"Ergonomics", "VerticalRecoil", "HorizontalRecoil",
                      "Recoil", "Velocity"}


def _apply_adjustments_in_sample(pred: np.ndarray, X: np.ndarray,
                                 feature_keys: List[str], exprs: List[str]) -> np.ndarray:
    """Run the hand-written CLASS_TARGET_ADJUSTMENTS the same way the emitted
    formula will. Without this the null-model check scored a formula the tool
    never actually emits - Suppressors VerticalRecoil carries a flat -0.6 nudge,
    which was enough to push it from 'better than zero' to 210% nMAE in the audit
    while the check still passed it."""
    out = np.array(pred, dtype=float)
    for i in range(X.shape[0]):
        ns = {feature_keys[j + 1]: float(X[i, j + 1])
              for j in range(X.shape[1] - 1)}
        ns['pred'] = float(out[i])
        for e in exprs:
            try:
                exec(e, {"__builtins__": {}}, ns)
            except Exception:
                pass  # an adjustment referencing a feature this class lacks
        out[i] = float(ns.get('pred', out[i]))
    return out


def _predict_in_sample(model: Dict[str, Any], X: np.ndarray,
                       target_name: str = '', class_name: str = '') -> np.ndarray:
    """Reproduce what the emitted formula will compute, for the training rows.

    Mirrors the emitted order exactly: linear term -> explicit blend (skipped,
    it needs base_data) -> hand adjustments -> clip -> zero-gate -> rounding.
    """
    beta = model['beta_std']
    used = model.get('used_idx') or []
    if used:
        Xu = X[:, [j + 1 for j in used]]
        mu = np.asarray(model['mu'], dtype=float)
        sg = np.asarray(model['sigma'], dtype=float)
        sg = np.where(sg < 1e-12, 1.0, sg)
        z = np.clip((Xu - mu) / sg, -4.0, 4.0)
        pred = beta[0] + z.dot(np.asarray(beta[1:], dtype=float))
    else:
        pred = np.full(X.shape[0], float(beta[0]))

    _adjs = CLASS_TARGET_ADJUSTMENTS.get(class_name, {}).get(target_name, [])
    if _adjs:
        pred = _apply_adjustments_in_sample(pred, X, model['feature_keys'], _adjs)

    pred = np.clip(pred, model.get('clip_lo', -1e18), model.get('clip_hi', 1e18))

    gate = model.get('zero_gate')
    if gate:
        Xg = X[:, [j + 1 for j in gate['used_idx']]]
        mu = np.asarray(gate['mu'], dtype=float)
        sg = np.asarray(gate['sigma'], dtype=float)
        sg = np.where(sg < 1e-12, 1.0, sg)
        zg = np.clip((Xg - mu) / sg, -4.0, 4.0)
        score = gate['intercept'] + zg.dot(np.asarray(gate['coef'], dtype=float))
        pred = np.where(score < 0, 0.0, pred)

    # Emission rounding, which is coarse enough to matter on small deltas:
    # r_half turns a -0.3 nudge into -0.5.
    if target_name in ROUND_HALF_TARGETS:
        pred = np.round(pred * 2.0) / 2.0
    elif target_name in ('AutoROF', 'SemiROF', 'BasePriceModifier', 'Price'):
        pred = np.round(pred)
    return pred


def _beats_writing_nothing(model: Dict[str, Any], X: np.ndarray, y: np.ndarray,
                           target_name: str = '', class_name: str = '',
                           margin: float = 0.90):
    """Is emitting this formula better than emitting nothing at all?

    The null model for a sparse Realism delta is not "the mean" - it is ZERO,
    because leaving the field unwritten is a real, available option and is what
    the author chose for most items. A formula whose error exceeds mean|y| is
    doing active harm: it writes a wrong non-zero onto items that should have
    been left alone, and it would be strictly better to omit the target.

    (In the audit that condition is exactly nMAE% > 100.)
    """
    mae_zero = float(np.mean(np.abs(y)))
    mae_model = float(np.mean(np.abs(
        _predict_in_sample(model, X, target_name, class_name) - y)))
    return mae_model <= mae_zero * margin, mae_model, mae_zero


def _dedupe_feature_columns(X_full: np.ndarray, all_feats: List[str]) -> Tuple[np.ndarray, List[str]]:
    """Drop later columns that are (near-)identical to an earlier column.
    Eliminates multicollinearity from aliased features - most notably the engineered
    'DurabilityBurnMod' which is literally a copy of the base prop 'DurabilityBurnModificator'.
    Column 0 (bias) is always kept. Only true aliases (|corr| > 0.9995 or exact match) are
    dropped, so genuinely-distinct-but-correlated features (e.g. Weight vs LogWeight) survive."""
    n_cols = X_full.shape[1]
    keep = [0]
    for j in range(1, n_cols):
        col_j = X_full[:, j]
        is_dup = False
        for k in keep[1:]:
            col_k = X_full[:, k]
            if np.allclose(col_j, col_k, atol=1e-9):
                is_dup = True
                break
            sj, sk = float(np.std(col_j)), float(np.std(col_k))
            if sj > 1e-12 and sk > 1e-12:
                rr = np.corrcoef(col_j, col_k)[0, 1]
                if np.isfinite(rr) and abs(rr) > 0.9995:
                    is_dup = True
                    break
        if not is_dup:
            keep.append(j)
    X_out = X_full[:, keep]
    feats_out = [all_feats[j - 1] for j in keep[1:]]
    return X_out, feats_out


def _learn_models_for_subset(samples: List[Tuple[Dict, Dict]], class_name: str, item_type: str) -> Tuple[Dict, List[str], int]:
    if not samples: return {},[], 0

    base_feat_keys = collect_feature_keys(samples)
    eng_feat_keys = set()
    eng_feats =[]

    for m, rec in samples:
        eng = engineer_features_from_item(m, rec)
        eng_feat_keys.update(eng.keys())
        eng_feats.append(eng)

    all_feats = base_feat_keys + sorted(list(eng_feat_keys))

    X_rows, y_dicts = [],[]
    for i, (m, rec) in enumerate(samples):
        valid_y = {k: float(v) for k, v in rec.items()
                   if isinstance(v, (int, float)) and is_target_allowed_for_class(k, class_name, item_type)}
        if not valid_y: continue

        props = m.get('_props', {})
        row = [1.0] +[float(props.get(k, 0.0)) for k in base_feat_keys] + [eng_feats[i].get(k, 0.0) for k in sorted(list(eng_feat_keys))]
        X_rows.append(np.array(row))
        y_dicts.append(valid_y)

    if not X_rows: return {},['bias'] + all_feats, 0

    X_full = np.vstack(X_rows)
    X_full, all_feats = _dedupe_feature_columns(X_full, all_feats)
    all_targets = set(k for d in y_dicts for k in d)

    models = {}
    rejected_targets = []
    for t in all_targets:
        t_y, t_X = [],[]
        for i, d in enumerate(y_dicts):
            if t in d:
                t_y.append(d[t])
                t_X.append(X_full[i])

        if len(t_y) < 2: continue

        best = _fit_single_target_strategies(
            np.vstack(t_X), np.asarray(t_y),
            t in ("AutoROF", "SemiROF"),
            ['bias'] + all_feats,
            t,
            AMMO_INFO_BOUNDS.get(t) if item_type == "Ammo" else None,
        )
        if not best:
            continue
        best['feature_keys'] = ['bias'] + all_feats

        # Reject formulas that lose to writing nothing. Skipping the target
        # leaves the field to the template / the mod author instead of stamping
        # a wrong value on every item.
        _tX, _tY = np.vstack(t_X), np.asarray(t_y)
        keep, mae_model, mae_zero = _beats_writing_nothing(
            best, _tX, _tY, t, class_name)

        # If the regression loses to writing nothing, that does not necessarily
        # mean nothing can be said - only that the *feature-driven* fit has no
        # signal. A far more modest claim is often still true and useful: "mods
        # of this class that touch this stat typically move it by X". Try the
        # gated class-typical constant before giving up, since dropping the
        # target entirely leaves the tool with nothing to offer (Mounts fell to
        # a single emitted field, PistolGrip to two).
        if not keep:
            _nz = _tY[np.abs(_tY) > 1e-5]
            for _label, _const in (('median of the values that are set',
                                    float(np.median(_nz)) if len(_nz) else None),
                                   ('class median', float(np.median(_tY)))):
                if _const is None or abs(_const) < 1e-9:
                    continue
                # A constant with no gate writes that value onto EVERY item,
                # including the ones the author zeroed -- 100% zero-leak by
                # construction. Realism FragmentationChance went exactly that
                # way: the class median 0.1 beat a plain zero on MAE while
                # stamping a value onto all 62 cartridges that had none. Only
                # allow the fallback where the gate can hold the zeros back, or
                # where there are barely any zeros to leak into.
                _zero_frac = float(np.mean(np.abs(_tY) <= 1e-5))
                if not best.get('zero_gate') and _zero_frac > 0.25:
                    continue
                _fallback = {
                    'beta_std': [_const], 'used_idx': [], 'mu': [], 'sigma': [],
                    'transform': 'identity', 'mae': 0.0, 'score': 0.0,
                    'clip_lo': min(_const, float(np.min(_tY))),
                    'clip_hi': max(_const, float(np.max(_tY))),
                    'n_samples': int(len(_tY)),
                    'feature_keys': ['bias'] + all_feats,
                }
                if best.get('zero_gate'):
                    _fallback['zero_gate'] = best['zero_gate']
                _ok, _mm, _mz = _beats_writing_nothing(
                    _fallback, _tX, _tY, t, class_name)
                if _ok:
                    print(f"      ↳ {t}: regression lost to a plain 0 "
                          f"({mae_model:.4f} vs {mae_zero:.4f}); using the "
                          f"{_label} instead ({_const:.4g}, MAE {_mm:.4f})")
                    best, keep, mae_model = _fallback, True, _mm
                    break

        best['mae_full'] = mae_model
        best['mae_zero'] = mae_zero
        # Booleans are not deltas - "worse than writing 0" is meaningless for a
        # flag, and passthrough fields are copied rather than predicted.
        if t in BOOL_FIELDS or t in BASE_PROP_PASSTHROUGH or KEEP_WEAK_TARGETS:
            keep = True
        if not keep:
            rejected_targets.append((t, mae_model, mae_zero, len(t_y)))
            continue
        models[t] = best

    if rejected_targets:
        print(f"      ↳ Skipped {len(rejected_targets)} target(s) that scored worse "
              f"than writing nothing:")
        for _t, _mm, _mz, _n in sorted(rejected_targets, key=lambda r: -r[1] / max(r[2], 1e-9)):
            print(f"         {_t:28} MAE {_mm:9.4f} vs {_mz:9.4f} for a plain 0 "
                  f"({_n} items)")

    return models, ['bias'] + all_feats, len(X_rows)


def _report_no_models(class_name: str, item_type: str, samples: List[Tuple[Dict, Dict]]) -> None:
    """Explain why a class with templates produced no formulas.

    Previously this failed silently: `Rounds` had 195 matched templates and no
    emitted function, with nothing in the log to say so. The cause is almost
    always is_target_allowed_for_class() rejecting every field name in the
    authored records, so print the rejected names and let the allow-list be fixed.
    """
    from collections import Counter
    rejected, accepted = Counter(), Counter()
    for _m, rec in samples:
        for k, v in rec.items():
            if not isinstance(v, (int, float)) or isinstance(v, bool):
                continue
            if is_target_allowed_for_class(k, class_name, item_type):
                accepted[k] += 1
            else:
                rejected[k] += 1
    print(f"      ⚠️  NO FORMULAS EMITTED for {class_name} ({item_type}) "
          f"despite {len(samples)} matched templates.")
    if accepted:
        print(f"         {len(accepted)} target(s) passed the allow-list but no model fit: "
              f"{', '.join(sorted(accepted)[:12])}")
    else:
        print(f"         Every numeric field was rejected by "
              f"is_target_allowed_for_class(..., '{class_name}', '{item_type}').")
    if rejected:
        top = ', '.join(f"{k}({n})" for k, n in rejected.most_common(15))
        print(f"         Rejected field names: {top}")


def _emit_caliber_index() -> str:
    """Serialise the resolved calibre map so the generated module can use it.

    engineer_features_from_item is copied verbatim into formulas.py, so the
    lookup table it reads has to travel with it.
    """
    items = sorted(CALIBER_BY_ITEM_ID.items())
    body = ",\n".join(f'    "{k}": {v:g}' for k, v in items)
    return ("# Exact bore diameter per item id, resolved from the slot graph at\n"
            "# generation time (see build_caliber_index). Consulted before the name\n"
            "# regex, which misreads model numbers as calibres on mods.\n"
            "CALIBER_BY_ITEM_ID = {\n" + body + "\n}\n\n")


def emit_class_function(class_name: str, models: Dict[str, Any], is_gun: bool) -> str:
    fn_suffix = "gun" if is_gun else "mod"
    fn_stub = sanitize_function_name(class_name)
    indent = "    "

    lines =[
        f"# --- {class_name} ({'Gun' if is_gun else 'Mod'}) Formulas ---",
        f"def apply_{fn_stub}_{fn_suffix}_formulas(item_entry, base_data, template=None, context=None):",
        f"{indent}props = base_data.get(\"_props\", base_data)",
        f"{indent}_ov = base_data.get(\"overrideProperties\")",
        f"{indent}if isinstance(_ov, dict):",
        f"{indent}    props = {{**props, **{{_k: _v for _k, _v in _ov.items() if isinstance(_v, (int, float, str, bool))}}}}",
        f"{indent}eng = engineer_features_from_item(base_data, template)",
    ]

    req_base = set()
    req_eng = set()

    for m in models.values():
        # The zero-gate selects its own features (what predicts *whether* a stat
        # is set is not what predicts *how much*), so both sets must be declared.
        _idxs = list(m.get('used_idx', []))
        _idxs += list(m.get('zero_gate', {}).get('used_idx', []))
        for idx in _idxs:
            f = m['feature_keys'][idx + 1]
            if f in ALL_ENG_KEYS:
                req_eng.add(f)
            else:
                req_base.add(f)

    # CLASS_TARGET_ADJUSTMENTS are hand-written expressions that name features
    # directly ('pred += (0.08 * IsSuppressor)'). Those names were never added to
    # the declaration sets, so a class whose ONLY use of a feature was inside an
    # adjustment emitted a function that raised NameError at runtime. It stayed
    # hidden while every such class also happened to use the feature in a fitted
    # term; the new SuppressorsPistol split had no fitted term using
    # IsSuppressor and the bug became a hard failure on 20 items.
    for _exprs in CLASS_TARGET_ADJUSTMENTS.get(class_name, {}).values():
        for _e in _exprs:
            for _tok in re.findall(r'[A-Za-z_][A-Za-z_0-9]*', _e):
                if _tok in ('pred', 'if', 'else', 'and', 'or', 'not'):
                    continue
                if _tok in ALL_ENG_KEYS:
                    req_eng.add(_tok)
                elif _tok not in ('int', 'float', 'abs', 'min', 'max', 'round'):
                    # Anything else an adjustment names is a base prop.
                    req_base.add(_tok)

    for f in CLASS_FORCE_FEATURES.get(class_name, set()):
        if f in ALL_ENG_KEYS:
            req_eng.add(f)
        else:
            req_base.add(f)

    if class_name in BARREL_LIKE_CLASSES:
        req_eng.update({'BarrelLengthMM', 'CaliberNumeric'})

    if req_base:
        for f in sorted(req_base):
            lines.append(f'{indent}{f} = to_f(props.get("{f}", 0.0))')

    if req_eng:
        for f in sorted(req_eng):
            lines.append(f'{indent}{f} = eng.get("{f}", 0.0)')

    if class_name in BARREL_LIKE_CLASSES:
        lines.append(f"{indent}_preset_len_norm = ((BarrelLengthMM - 406.4) / 101.6) if BarrelLengthMM else 0.0")
        lines.append(f"{indent}_preset_cal_norm = ((CaliberNumeric - 7.62) / 2.06) if CaliberNumeric else 0.0")

    target_adjustments = CLASS_TARGET_ADJUSTMENTS.get(class_name, {})

    for t, m in sorted(models.items()):
        # AutoROF / SemiROF on guns are a direct 1:1 copy of the base fire rates (emitted at
        # the end of the function), so skip the ML path for them here. On mods they stay ML
        # (a brake/suppressor genuinely nudges rate of fire).
        if is_gun and t in ('AutoROF', 'SemiROF'):
            continue
        # The tool seeds item_entry from a copy of the cloned template, so any target we
        # emit *overwrites* whatever the template had. A target whose training data was an
        # unvarying ~0 with no physical adjustment produces a constant `pred = 0` that
        # silently zeroes the template's real value. Leaving it unwritten is strictly better.
        _adjs_for_t = target_adjustments.get(t, [])
        if (len(m['beta_std']) == 1 and abs(m['beta_std'][0]) < 1e-9
                and not m['used_idx'] and not _adjs_for_t and t not in BOOL_FIELDS):
            continue

        lines.append(f'\n{indent}# Target: {t}')

        beta = m['beta_std']
        if len(beta) == 1 or not m['used_idx']:
            lines.append(f'{indent}pred = {beta[0]:.6g}')
        else:
            terms = [f"{beta[0]:.6g}"]
            for b, j, mu, sig in zip(beta[1:], m['used_idx'], m['mu'], m['sigma']):
                if abs(b) > 1e-6:
                    f = m['feature_keys'][j + 1]
                    terms.append(f"({b:.6g} * clampz(({f} - {mu:.6g}) / {sig:.6g}))")
            lines.append(f'{indent}pred = {" + ".join(terms)}')

        source_keys = EXPLICIT_SOURCE_MAP.get(t)
        if source_keys and t != 'Weight':
            # Blend ML prediction with the basegame override value (40/60).
            # Weight is excluded: it is handled as a full direct passthrough after clipping.
            lines.append(f'{indent}explicit_val = explicit_override_value(base_data, {source_keys!r})')
            lines.append(f'{indent}if explicit_val is not None:')
            lines.append(f'{indent}    pred = (0.40 * pred) + (0.60 * float(explicit_val))')

        for expr in target_adjustments.get(t,[]):
            lines.append(f'{indent}{expr}')

        _clip_lo = m["clip_lo"]
        _clip_hi = m["clip_hi"]
        _adjs = target_adjustments.get(t, [])
        # A zero-width clip means every training sample carried the same value.
        # That is two different situations and they need opposite treatment:
        #   few samples  -> no information; let the physical adjustment drive
        #   many samples -> a unanimous authoring decision across the whole class;
        #                   the adjustment must not override it
        # Conflating them made the hand adjustments win against a 79-item consensus
        # (Suppressors Ergonomics off by 1.5, FlashHiders by 0.5, Shotguns
        # WeapAccuracy by 4.33 - every one of them a DEGEN target the ML had right).
        _CONSENSUS_MIN_SAMPLES = 8
        _is_consensus = m.get('n_samples', 0) >= _CONSENSUS_MIN_SAMPLES
        if _adjs and abs(_clip_hi - _clip_lo) < 1e-4 and not _is_consensus:
            # ML saw all-zero training values — physical adjustments dominate.
            # Use a wide, field-aware fallback so adjustments aren't immediately squashed.
            _FALLBACK = {
                'Ergonomics':           (-50,  30),
                'VerticalRecoil':       (-25,   5),
                'HorizontalRecoil':     (-20,   5),
                'Loudness':             (-60,  10),
                'Flash':                (-60,  40),
                'CameraRecoil':         (-25,   5),
                'Velocity':             (-250, 150),
                'Accuracy':             (-30,  20),
                'WeapAccuracy':         (-10,  10),
                'AimSpeed':             (-10,  10),
                'ReloadSpeed':          (-10,  10),
                'FixSpeed':             (-10,  10),
                'ModMalfunctionChance': (-0.1, 0.1),
                'AutoROF':              (-200, 200),
                'SemiROF':              (-200, 200),
                'RecoilAngle':          (  0, 360),
                'Weight':               (  0,  15),
                'Dispersion':           (-10,  10),
                'Convergence':          (-15,  15),
            }
            _safe_lo, _safe_hi = _FALLBACK.get(t, (-1e5, 1e5))
            lines.append(f'{indent}pred = min(max(pred, {_safe_lo}), {_safe_hi})  # wide fallback: ML saw all-zero training data')
        else:
            lines.append(f'{indent}pred = min(max(pred, {_clip_lo:.6g}), {_clip_hi:.6g})')

        # Weight is always a direct passthrough - mod author set the real weight.
        # It must never be clamped by the ML clip or a template from a different item.
        if t == 'Weight':
            lines.append(f'{indent}explicit_weight = explicit_override_value(base_data, [\'Weight\'])')
            lines.append(f'{indent}if explicit_weight is not None:')
            lines.append(f'{indent}    pred = float(explicit_weight)')

        if t not in BOOL_FIELDS:
            lines.append(f'{indent}if isinstance(template, dict) and "{t}" in template:')
            lines.append(f'{indent}    t_val = to_f(template["{t}"])')
            lines.append(f'{indent}    if abs(t_val) < 1e-5:')
            lines.append(f'{indent}        pass  # template value is 0/unset -> keep ML prediction')
            lines.append(f'{indent}    else:')
            lines.append(f'{indent}        # Wide slack: cloned templates (often vanilla items) can differ a lot.')
            lines.append(f'{indent}        # 25% was pulling predictions to wrong defaults for guns/mods.')
            lines.append(f'{indent}        slack = max(abs(t_val) * 0.75 + 0.5, abs(pred) * 0.5 + 0.5)')
            lines.append(f'{indent}        pred = min(max(pred, t_val - slack), t_val + slack)')
        # NOTE: an earlier version passed these through from _props. That was
        # wrong -- Realism rescales DurabilityBurnRatio (1.15 -> 0.18),
        # HeatFactorGun (1.0 -> 0.2) and CoolFactorGun (3.168 -> 0.1), so the
        # vanilla figure is not an answer. They are predicted like everything else.

        # HURDLE MODEL, STAGE 1: zero/non-zero decision.
        # Emitted last so nothing downstream (adjustments, clip, template slack)
        # can re-inject a value onto an item the author would have left at 0.
        _gate = m.get('zero_gate')
        if _gate and t != 'Weight' and t not in BOOL_FIELDS:
            req_gate_base, req_gate_eng = set(), set()
            for _j in _gate['used_idx']:
                _f = m['feature_keys'][_j + 1]
                (req_gate_eng if _f in ALL_ENG_KEYS else req_gate_base).add(_f)
            _terms = [f"{_gate['intercept']:.6g}"]
            for _b, _j, _mu, _sg in zip(_gate['coef'], _gate['used_idx'],
                                        _gate['mu'], _gate['sigma']):
                if abs(_b) > 1e-6:
                    _f = m['feature_keys'][_j + 1]
                    _terms.append(f"({_b:.6g} * clampz(({_f} - {_mu:.6g}) / {_sg:.6g}))")
            lines.append(f'{indent}# zero-gate: catches {_gate["recall_zero"]*100:.0f}% of the '
                         f'{_gate["n_zero"]} zeroed items while keeping '
                         f'{_gate["recall_real"]*100:.0f}% of the {_gate["n_real"]} valued ones '
                         f'(balanced acc {_gate["bal_acc"]*100:.0f}%)')
            lines.append(f'{indent}if ({" + ".join(_terms)}) < 0:')
            lines.append(f'{indent}    pred = 0.0')

        if t in ('AutoROF', 'SemiROF', 'BasePriceModifier', 'Price'):
            lines.append(f'{indent}item_entry["{t}"] = int(round(pred))')
        elif t in BOOL_FIELDS:
            lines.append(f'{indent}if isinstance(template, dict) and "{t}" in template:')
            lines.append(f'{indent}    item_entry["{t}"] = bool(template.get("{t}", False))')
            lines.append(f'{indent}else:')
            lines.append(f'{indent}    item_entry["{t}"] = True if pred >= 0.5 else False')
        elif t in ("Ergonomics", "VerticalRecoil", "HorizontalRecoil", "Recoil", "Velocity"):
            lines.append(f'{indent}item_entry["{t}"] = r_half(pred)')
        elif t in HIGH_PRECISION_TARGETS:
            # These fields live in the 0.0001-0.5 range; 2 d.p. would round small values to 0.
            lines.append(f'{indent}item_entry["{t}"] = r(pred, 4)')
        elif t in ('RecoilDamping', 'RecoilHandDamping', 'RecoilIntensity',
                   'DurabilityBurnRatio', 'DurabilityBurnModificator',
                   'HeatFactor', 'CoolFactor', 'HeatFactorGun', 'CoolFactorGun',
                   'CoolFactorGunMods', 'HeatFactorByShot', 'VisualMulti'):
            # These fields are in the 0.0-2.0 range; 3 d.p. keeps small deltas alive.
            lines.append(f'{indent}item_entry["{t}"] = r(pred, {DEFAULT_EMIT_DECIMALS})')
        else:
            lines.append(f'{indent}item_entry["{t}"] = r(pred, {DEFAULT_EMIT_DECIMALS})')

    if is_gun:
        # Fire rate is deliberately NOT emitted for guns. It is hand-authored
        # in Realism and copied verbatim from the base item, so there is
        # nothing to predict; mod AutoROF/SemiROF deltas are unaffected.

        sg_default = SHOTGUN_DISP_DEFAULTS.get(class_name, 0)
        lines.append(f'\n{indent}# ShotgunDispersion (fixed value — not ML-calculated)')
        lines.append(f'{indent}if isinstance(template, dict) and "ShotgunDispersion" in template:')
        lines.append(f'{indent}    item_entry["ShotgunDispersion"] = int(to_f(template.get("ShotgunDispersion", {sg_default})))')
        lines.append(f'{indent}else:')
        lines.append(f'{indent}    item_entry["ShotgunDispersion"] = {sg_default}')

    lines.append(f"\n{indent}return item_entry\n")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--master', default='items_master.json')
    ap.add_argument('--templates-dir', default='templates_data')
    ap.add_argument('--out', default='formulas.py')
    ap.add_argument('--exclude-target', action='append')
    ap.add_argument('--keep-weak-targets', action='store_true',
                    help='Emit every target even when the fitted formula scores '
                         'worse than writing a plain 0. Off by default: a formula '
                         'that loses to the null model stamps a wrong value onto '
                         'items the author deliberately left alone.')
    args, _ = ap.parse_known_args()

    print("\n[INIT] Starting Realism Mod Formula Generation...")

    exclude = _build_excluded_targets(args)

    print(f"[DATA] Loading master items from '{args.master}'...")
    global KEEP_WEAK_TARGETS
    KEEP_WEAK_TARGETS = bool(args.keep_weak_targets)

    items = load_master(args.master)
    if not items:
        print("       ⚠️ Warning: No items found in master JSON or file missing!")
    else:
        print(f"       ✅ Loaded {len(items)} master items.")

    master_map = build_master_id_map(items)
    m_idx = index_master(items, '_id')

    global CALIBER_BY_ITEM_ID
    CALIBER_BY_ITEM_ID = build_caliber_index(m_idx)
    global PISTOL_CALIBER_ITEM_IDS
    PISTOL_CALIBER_ITEM_IDS = build_pistol_caliber_set(m_idx)
    print(f"       ✅ Resolved an exact calibre for {len(CALIBER_BY_ITEM_ID)} items "
          f"via the slot graph ({len(PISTOL_CALIBER_ITEM_IDS)} pistol-host).")

    print(f"[DATA] Searching for templates in '{args.templates_dir}'...")
    compat_files = find_templates(args.templates_dir)
    print(f"       ✅ Found {len(compat_files)} template files. Parsing...")

    compat_all = {}
    for p in compat_files:
        d = parse_compat_any(p)
        if d: compat_all.update(d)

    print(f"       ✅ Parsed {len(compat_all)} unique item compat records.")

    class_samples = {}
    matched_items = 0
    unmatched_ids = []
    unclassified = []          # (terminal parent id, master _name)
    for iid, rec in compat_all.items():
        m = m_idx.get(iid.lower())
        if not m:
            unmatched_ids.append(iid)
            continue
        trace = []
        cid = resolve_parent_class_id(m, master_map, trace)
        if cid:
            class_samples.setdefault(cid,[]).append((m, rec))
            matched_items += 1
        else:
            unclassified.append((trace[-1] if trace else '<no parent>',
                                 m.get('_name', '') or iid))

    print(f"[GROUPING] Successfully matched {matched_items} templates to master game data.")
    print(f"           Grouped into {len(class_samples)} specific parent classes.")

    if unmatched_ids:
        print(f"           {len(unmatched_ids)} template item(s) are not in the master file "
              f"(custom items - expected).")

    if unclassified:
        # These have master data but their parent chain never reaches a name in
        # PARENT_CLASSES, so they train nothing and predict nothing. Group by the
        # terminal node so the missing handbook ids are obvious at a glance.
        from collections import Counter, defaultdict
        counts = Counter(pid for pid, _ in unclassified)
        examples = defaultdict(list)
        for pid, nm in unclassified:
            if len(examples[pid]) < 3: examples[pid].append(nm)
        print(f"\n[UNCLASSIFIED] {len(unclassified)} item(s) whose parent chain hit no known "
              f"class. Add these ids to PARENT_CLASSES to bring them into training:")
        for pid, n in counts.most_common(20):
            print(f"    {pid}  x{n:<5} e.g. {', '.join(examples[pid])}")
        if len(counts) > 20:
            print(f"    ... and {len(counts) - 20} more distinct parent id(s)")
    print("\n[TRAINING] Starting Machine Learning analysis. This may take a moment due to Huber robustness...")

    sections, gun_map, mod_map, gear_map, ammo_map = [], [], [], [],[]

    # PARENT_CLASSES is many-to-one: several parent ids legitimately map to the
    # same class name (FunctionalMods has three). Iterating per-id trained the
    # class once per id and emitted the function once per id, so the LAST one
    # silently overwrote the others in the generated module - FunctionalMods
    # trained on 41 samples for 19 targets, then again on 3 samples for 4, and
    # the 3-sample model is the one that shipped. Merge by name first.
    merged_samples: Dict[str, List[Tuple[Dict, Dict]]] = {}
    for _cid, _samples in class_samples.items():
        _cname = PARENT_CLASSES.get(_cid)
        if not _cname:
            continue
        merged_samples.setdefault(_cname, []).extend(_samples)
    for _cname, _samples in merged_samples.items():
        _ids = [c for c in class_samples if PARENT_CLASSES.get(c) == _cname]
        if len(_ids) > 1:
            print(f"           Merged {len(_ids)} parent ids into {_cname} "
                  f"({len(_samples)} samples total).")

    for cname, samples in merged_samples.items():

        if cname in GUN_CLASS_NAMES:
            itype = "Gun"
        elif cname in GEAR_CLASS_NAMES:
            itype = "Gear"
        elif cname in ("Ammo", "AmmoBoxes", "Rounds"):
            itype = "Ammo"
        else:
            itype = "WeaponMod"

        if len(samples) < 3:
            print(f"   ➤ Skipping: {cname} ({itype}) - Not enough samples ({len(samples)} < 3)")
            continue

        print(f"   ➤ Processing: {cname} ({itype}) - {len(samples)} samples")

        if itype == "Gun":
            models, _, matched = _learn_models_for_subset(samples, cname, "Gun")
            if matched:
                sections.append(emit_class_function(cname, models, True))
                gun_map.append(f'    "{cname}": apply_{sanitize_function_name(cname)}_gun_formulas')
                print(f"      ↳ Created formulas for {len(models)} targets.")
            else:
                _report_no_models(cname, itype, samples)

        elif itype == "Ammo":
            models, _, matched = _learn_models_for_subset(samples, cname, "Ammo")
            if matched:
                sections.append(emit_class_function(cname, models, False))
                ammo_map.append(f'    "{cname}": apply_{sanitize_function_name(cname)}_mod_formulas')
                print(f"      ↳ Created formulas for {len(models)} targets.")
            else:
                _report_no_models(cname, itype, samples)

        elif itype == "WeaponMod":
            if cname == "Muzzle":
                subs = {"Suppressors": [], "MuzzleBrakes": [], "MuzzleBrakesFactory": [],
                        "Compensators": [], "MuzzleCombos": [], "FlashHiders": [],
                        "MuzzleAdapters": []}
                for s in samples:
                    # Master items carry '_name' (muzzle_brake_ar15_surefire_...),
                    # never 'Name'. Reading only 'Name' meant every name-based branch
                    # below was dead, so flash hiders and thread adapters were all
                    # swept into MuzzleBrakes and never got a model of their own.
                    n = " ".join(str(s[0].get(_k, "") or "")
                                 for _k in ("Name", "_name", "shortName")).lower()
                    t = str(s[0].get("_props", {}).get("muzzleModType", "")).lower()
                    # muzzleModType is the game's own categorical and already
                    # separates brake / conpensator / muzzlecombo (typo is BSG's).
                    # Those three are not interchangeable:
                    #                    Brake   Comp    Combo   FlashHider
                    #   Flash            -1.63   +4.82   +2.22   -51.83
                    #   Loudness        +26.46  +20.74   +3.33    +9.54
                    #   VerticalRecoil   -1.42   -0.47   -1.67    -4.65
                    #   CameraRecoil     -6.15   -3.82   -3.33     0.00
                    # A compensator makes flash WORSE while a brake barely moves
                    # it, and a flash hider does nothing for camera recoil.
                    if t in ("silencer", "pms") or "suppressor" in n or "silencer" in n:
                        subs["Suppressors"].append(s)
                    elif (t == "adapter" or "thread" in n or "adapter" in n
                          or "protector" in n or "nut" in n):
                        subs["MuzzleAdapters"].append(s)
                    elif t == "flashhider" or "flash" in n or "hider" in n:
                        subs["FlashHiders"].append(s)
                    elif t == "brake" and "_std" in n:
                        # The weapon's ISSUED muzzle device. In the game these are
                        # birdcage / combination units, not pure recoil brakes, and
                        # Realism authors them that way:
                        #                    factory _std   aftermarket
                        #   Flash               -20.23         +7.02
                        #   Loudness            +18.58        +29.12
                        #   CameraRecoil         -3.69         -7.14
                        # Pooling them is what made MuzzleBrakes Flash bimodal.
                        subs["MuzzleBrakesFactory"].append(s)
                    elif t == "conpensator": subs["Compensators"].append(s)
                    elif t == "muzzlecombo": subs["MuzzleCombos"].append(s)
                    else: subs["MuzzleBrakes"].append(s)

                for sname, s_samples in subs.items():
                    if len(s_samples) < 3:
                        print(f"      ➤ Sub-category: {sname} - only {len(s_samples)} sample(s), "
                              f"skipped (will fall back to MuzzleBrakes via CATEGORY_ALIASES)")
                        continue
                    print(f"      ➤ Sub-category: {sname} ({len(s_samples)} samples)")
                    halves = split_by_host_caliber(sname, s_samples) or {sname: s_samples}
                    # Then split suppressors again by mount type.
                    expanded = {}
                    for _hn, _hs in halves.items():
                        expanded.update(split_suppressors_by_mount(_hn, _hs) or {_hn: _hs})
                    halves = expanded
                    if len(halves) > 1:
                        print(f"         ➤ Split by host platform: " +
                              ", ".join(f"{k} ({len(v)})" for k, v in halves.items()))
                    for hname, hsamples in halves.items():
                        models, _, matched = _learn_models_for_subset(hsamples, hname, "WeaponMod")
                        if matched:
                            sections.append(emit_class_function(hname, models, False))
                            mod_map.append(f'    "{hname}": apply_{sanitize_function_name(hname)}_mod_formulas')
                            print(f"         ↳ {hname}: created formulas for {len(models)} targets.")
                        else:
                            _report_no_models(hname, itype, hsamples)
            else:
                # Pistol-host and rifle-host mods of the same class behave
                # differently enough that pooling drags both fits to the middle.
                halves = split_by_host_caliber(cname, samples) or {cname: samples}
                expanded = {}
                for _hn, _hs in halves.items():
                    expanded.update(split_magazines_by_size(_hn, _hs)
                                    or split_charging_handles(_hn, _hs)
                                    or split_handguards_by_mount(_hn, _hs) or {_hn: _hs})
                halves = expanded
                if len(halves) > 1:
                    print(f"      ➤ Split by host platform: " +
                          ", ".join(f"{k} ({len(v)})" for k, v in halves.items()))
                for hname, hsamples in halves.items():
                    models, _, matched = _learn_models_for_subset(hsamples, hname, "WeaponMod")
                    if matched:
                        sections.append(emit_class_function(hname, models, False))
                        mod_map.append(f'    "{hname}": apply_{sanitize_function_name(hname)}_mod_formulas')
                        print(f"      ↳ {hname}: created formulas for {len(models)} targets.")
                    else:
                        _report_no_models(hname, itype, hsamples)

        elif itype == "Gear":
            models, _, matched = _learn_models_for_subset(samples, cname, "Gear")
            if matched:
                sections.append(emit_class_function(cname, models, False))
                gear_map.append(f'    "{cname}": apply_{sanitize_function_name(cname)}_mod_formulas')
                print(f"      ↳ Created formulas for {len(models)} targets.")
            else:
                _report_no_models(cname, itype, samples)

    logic_engine_source = _emit_caliber_index() + inspect.getsource(engineer_features_from_item)

    file_header = f'''import re
import math
from typing import Dict, Any

def parse_armor_class_string(s: str) -> float:
    if not isinstance(s, str): return 0.0
    s = s.lower()
    if 'iiia' in s or '3a' in s: return 1.5
    if 'iii+' in s or '3+' in s: return 4.0
    if 'iii' in s or '3' in s: return 3.0
    if 'iv' in s or '4' in s: return 5.0
    if 'ii' in s or '2' in s: return 2.0
    if 'v0' in s or 'v50' in s: return 2.0
    if 'gost 1' in s: return 1.0
    if 'gost 2' in s or 'pm 5' in s: return 2.0
    if 'gost 3' in s or 'pm 8' in s: return 3.0
    if 'gost 4' in s or 'pm 10' in s or 'esapi' in s or 'xsapi' in s: return 4.0
    if 'gost 5' in s: return 5.0
    if 'gost 6' in s: return 6.0
    if 'unclassified' in s: return 2.0
    return 0.0

def to_f(x, d=0.0):
    try: return float(x)
    except: return d

def r(x, d=3):
    try: return round(float(x), d)
    except: return x

def r_half(x):
    try: return round(float(x) * 2.0) / 2.0
    except: return x

def clampz(z, lim=4.0):
    # Clamp a standardized (z-score) feature term. A real item whose feature sits far
    # outside the (often tiny) training distribution would otherwise produce an absurd
    # intermediate value that slams the prediction straight to a clip bound. +/-4 sigma
    # keeps extrapolation sane while leaving in-distribution items untouched.
    try:
        z = float(z)
    except (TypeError, ValueError):
        return 0.0
    if z > lim: return lim
    if z < -lim: return -lim
    return z

def explicit_override_value(base_data, keys):
    ov = base_data.get('overrideProperties', {{}})
    props = base_data.get('_props', base_data)
    explicit_keys = set(base_data.get('_explicit_override_keys', ()) or ())
    if isinstance(keys, str):
        keys = [keys]
    for key in keys:
        if isinstance(ov, dict) and key in ov:
            return ov.get(key)
        if key in explicit_keys:
            return props.get(key)
        # Weight is the only one of these where the vanilla prop and the
        # Realism field share a scale. DurabilityBurnRatio, HeatFactorGun,
        # CoolFactorGun etc. are all rescaled by Realism (1.15 -> 0.18,
        # 1.0 -> 0.2), so reading _props for them poisoned the prediction.
        if key in props and key == 'Weight':
            return props.get(key)
    return None

PARENT_CLASSES = {json.dumps(PARENT_CLASSES, indent=4)}
CATEGORY_ALIASES = {{}}

{logic_engine_source}
'''

    dispatcher = f'''

gun_formula_map = {{{",".join(gun_map)}}}
mod_formula_map = {{{",".join(mod_map)}}}
gear_formula_map = {{{",".join(gear_map)}}}
ammo_formula_map = {{{",".join(ammo_map)}}}

# Category aliases: maps a class name with no formula to its nearest equivalent.
# Built at emit time based on which classes successfully trained.
_all_formula_keys = set(gun_formula_map.keys()) | set(mod_formula_map.keys()) | set(gear_formula_map.keys()) | set(ammo_formula_map.keys())
_ALIAS_CANDIDATES = [
    ('ReceiversSlides', 'Receiver'), ('Receiver', 'ReceiversSlides'),
    ('Barrels', 'Barrel'),
    # If a pistol-host half was too small to fit, fall back to the pooled class.
    ('BarrelPistol', 'Barrel'), ('SuppressorsPistol', 'Suppressors'),
    ('SuppressorsWipe', 'Suppressors'),
    ('Compensators', 'MuzzleBrakes'), ('MuzzleCombos', 'MuzzleBrakes'),
    ('MuzzleBrakesFactory', 'MuzzleBrakes'),
    ('CompensatorsPistol', 'Compensators'), ('MuzzleCombosPistol', 'MuzzleCombos'),
    ('MagazinesFlush', 'Magazines'), ('MagazinesExtended', 'Magazines'),
    ('ChargingHandleAmbi', 'ChargingHandle'),
    ('HandguardFreeFloat', 'Handguard'),
    ('HandguardPistolFreeFloat', 'HandguardPistol'),
    ('ChargingHandleExtended', 'ChargingHandle'),
    ('MagazinesPistolFlush', 'MagazinesPistol'),
    ('MagazinesPistolExtended', 'MagazinesPistol'),
    ('SuppressorsPistolWipe', 'SuppressorsPistol'),
    ('MuzzleBrakesPistol', 'MuzzleBrakes'), ('HandguardPistol', 'Handguard'),
    ('MagazinesPistol', 'Magazines'), ('PistolGripPistol', 'PistolGrip'), ('Barrel', 'Barrels'),
    ('GasBlocks', 'Gasblock'), ('Gasblock', 'GasBlocks'),
    ('ForeGrips', 'Foregrip'), ('Foregrip', 'ForeGrips'),
    ('PistolGrips', 'PistolGrip'), ('PistolGrip', 'PistolGrips'),
    ('ChargingHandles', 'ChargingHandle'), ('ChargingHandle', 'ChargingHandles'),
    ('StocksChassis', 'Stock'), ('Stock', 'StocksChassis'),
    ('Handguards', 'Handguard'), ('Handguard', 'Handguards'),
    ('IronSights', 'Sights'), ('Sights', 'IronSights'),
    ('Visors', 'Visor'), ('Visor', 'Visors'),
    ('Headsets', 'Headset'), ('Headset', 'Headsets'),
    ('AssaultCarbines', 'AssaultRifles'), ('AssaultRifles', 'AssaultCarbines'),
    ('Launchers', 'GrenadeLaunchers'), ('GrenadeLaunchers', 'Launchers'),
    ('AmmoBoxes', 'Ammo'), ('Rounds', 'Ammo'),
    ('TacticalComboDevices', 'CombTactDevice'), ('CombTactDevice', 'TacticalComboDevices'),
    ('Flashlights', 'CombTactDevice'), ('LightLasers', 'CombTactDevice'),
    ('FlashHiders', 'MuzzleBrakes'), ('MuzzleAdapters', 'MuzzleBrakes'),
    ('Muzzle', 'MuzzleBrakes'),
    ('Pistols', 'Pistol'), ('Pistol', 'Pistols'),
    ('BoltActionRifles', 'SniperRifles'),
    ('ArmorPlates', 'ArmorVests'), ('ArmorMasks', 'Headwear'),
    ('TacticalRigs', 'ArmorVests'),
    ('Optics', 'Sights'), ('Collimators', 'Sights'),
    ('AssaultScopes', 'Sights'), ('CompactCollimators', 'Sights'),
    ('Stocks', 'Stock'),
]
CATEGORY_ALIASES = {{k: v for k, v in _ALIAS_CANDIDATES if k not in _all_formula_keys and v in _all_formula_keys}}



def get_formula_func(category: str):
    # CATEGORY_ALIASES was built above but never consulted here, so a class that
    # legitimately routes to a neighbour's model (Rounds -> Ammo, FlashHiders ->
    # MuzzleBrakes, Barrels -> Barrel) resolved to None and the caller had to
    # patch around it. Try the exact name first, then its alias.
    for cat in (category, CATEGORY_ALIASES.get(category)):
        if not cat: continue
        if cat in gun_formula_map: return gun_formula_map[cat]
        if cat in mod_formula_map: return mod_formula_map[cat]
        if cat in gear_formula_map: return gear_formula_map[cat]
        if cat in ammo_formula_map: return ammo_formula_map[cat]
    return None
'''

    with open(args.out, 'w', encoding='utf-8') as f:
        f.write(file_header + "\n".join(sections) + "\n" + dispatcher)

    print(f"\n[DONE] ✅ Successfully created generated module: {args.out}")
    print(f"         Formulas now perfectly respect presets and physics bounds.")


if __name__ == "__main__":
    main()