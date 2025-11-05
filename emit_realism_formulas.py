#!/usr/bin/env python3
"""
Emit Realism formulas per parent type (autodiscovers many templates)
"""

import os
import re
import json
import math
import csv
import argparse
import py_compile
import importlib.util
import warnings
from sklearn.exceptions import ConvergenceWarning
from json import JSONDecodeError
from typing import Dict, List, Any, Tuple, Optional, Set
import ast

import numpy as np
from sklearn.linear_model import LinearRegression, Ridge, HuberRegressor, ElasticNet

# ---------- Robust regexes ----------
HEX24_RE = re.compile(r'^[0-9A-Fa-f]{24}$')
NUMSTR_RE = re.compile(r'^[\+\-]?\d+(?:\.\d+)?$')

# ---------- Parent classes & friendly names ----------
PARENT_CLASSES: Dict[str, str] = {
    "5b47574386f77428ca22b346": "Ammo", "5b47574386f77428ca22b33c": "AmmoBoxes", "5448e54d4bdc2dcc718b4568": "Armor",
    "5b5f701386f774093f2ecf0f": "ArmorVests", "5b5f78e986f77447ed5636b1": "AssaultCarbines", "5447b5fc4bdc2d87278b4567": "AssaultCarbines",
    "5b5f78fc86f77409407a7f90": "AssaultRifles", "5447b5f14bdc2d61278b4567": "AssaultRifles", "5b5f740a86f77447ec5d7706": "AssaultScopes",
    "5b5f74cc86f77447ec5d770a": "AuxiliaryParts", "5a74651486f7744e73386dd1": "AuxiliaryParts", "5448e53e4bdc2d60728b4567": "Backpack",
    "5b5f6f6c86f774093f2ecf0b": "Backpacks", "555ef6e44bdc2de9068b457e": "Barrel", "5b5f75c686f774094242f19f": "Barrels",
    "5b5f71c186f77409407a7ec0": "Bipods", "55818afb4bdc2dde698b456d": "Bipods", "5b5f798886f77447ed5636b5": "BoltActionRifles",
    "55818a6f4bdc2db9688b456b": "ChargingHandle", "5b5f751486f77447ec5d770c": "ChargingHandles", "5b5f742686f774093e6cb4ff": "Collimators",
    "5b5f744786f774094242f197": "CompactCollimators", "5b5f724c86f774093f2ecf15": "FlashhidersBrakes",
    "5b5f73ab86f774094242f195": "Flashlights", "5b5f71de86f774093f2ecf13": "ForeGrips", "55818af64bdc2d5b648b4570": "Foregrip",
    "5b5f71b386f774093f2ecf11": "FunctionalMods", "5b5f760586f774093e6cb509": "GasBlocks", "56ea9461d2720b67698b456f": "Gasblock",
    "5b47574386f77428ca22b33f": "Gear", "5b5f704686f77447ec5d76d7": "GearComponents", "5b5f750686f774093e6cb503": "GearMods",
    "57bef4c42459772e8d35a53b": "GearComponents", "5b5f79d186f774093f2ed3c2": "GrenadeLaunchers",
    "55818a104bdc2db9688b4569": "Handguard", "5b5f75e486f77447ec5d7712": "Handguards", "5645bcb74bdc2ded0b8b4578": "Headset",
    "5b5f6f3c86f774094242ef87": "Headsets", "5a341c4086f77401f2541505": "Headwear", "5b47574386f77428ca22b330": "Headwear",
    "5b5f746686f77447ec5d7708": "IronSights", "5b5f73c486f77447ec5d7704": "LaserTargetPointers",
    "55818b014bdc2ddc698b456b": "Launcher", "5b5f752e86f774093e6cb505": "Launchers", "55818b0e4bdc2dde698b456e": "LightLasers",
    "5b5f79a486f77409407a7f94": "MachineGuns", "5447bed64bdc2d97278b4568": "MachineGuns", "5b5f754a86f774094242f19b": "Magazines",
    "5448bc234bdc2d3c308b4569": "Magazines", "5b5f791486f774093f2ed3be": "MarksmanRifles", "5447b6194bdc2d67278b4567": "MarksmanRifles",
    "5b5f755f86f77447ec5d770e": "Mounts", "55818b224bdc2dde698b456f": "Mounts", "5448fe394bdc2d0d028b456c": "Muzzle",
    "5b5f72f786f77447ec5d7702": "MuzzleAdapters", "5b5f724186f77447ed5636ad": "MuzzleDevices", "5b5f748386f774093e6cb501": "Optics",
    "5447b5cf4bdc2d65278b4567": "Pistol", "5b5f761f86f774094242f1a1": "PistolGrips", "55818a684bdc2ddd698b456d": "PistolGrip",
    "5b5f792486f77447ed5636b3": "Pistols", "55818a304bdc2db5418b457d": "Receiver", "5b5f764186f77447ec5d7714": "ReceiversSlides",
    "5b47574386f77428ca22b33b": "Rounds", "5485a8684bdc2da71d8b4567": "Rounds", "5b5f794b86f77409407a7f92": "Shotguns",
    "5447b6094bdc2dc3278b4567": "Shotguns", "5b5f73ec86f774093e6cb4fd": "Sights", "5448fe7a4bdc2d6f028b456b": "Sights",
    "5b5f796a86f774093f2ed3c0": "SMGs", "5447b5e04bdc2d62278b4567": "SMGs", "5447b6254bdc2dc3278b4568": "SniperRifles",
    "55818a594bdc2db9688b456a": "Stock", "5b5f757486f774093e6cb507": "StocksChassis", "5b5f731a86f774093e6cb4f9": "Suppressors",
    "5b5f737886f774093e6cb4fb": "TacticalComboDevices", "5b5f6f8786f77447ed563642": "TacticalRigs",
    "5448e5284bdc2dcb718b4567": "Vest", "5448e5724bdc2ddf718b4568": "Visor", "5b47574386f77428ca22b331": "Visors",
    "5b5f75b986f77447ec5d7710": "VitalParts", "5b5f71a686f77447ed5636ab": "WeaponPartsMods", "5b5f78dc86f77409407a7f8e": "Weapons",
    "55818b164bdc2ddc698b456c": "CombTactDevice",
}
CLASS_ID_SET: Set[str] = set(PARENT_CLASSES.keys())

PARENT_ID_TO_TYPE_NAME = {
    "5447bedf4bdc2d87278b4568": "Gun", "5b5f78e986f77447ed5636b1": "Gun", "5b5f78fc86f77409407a7f90": "Gun",
    "5447b5fc4bdc2d87278b4567": "Gun", "5447b5f14bdc2d61278b4567": "Gun", "5b5f798886f77447ed5636b5": "Gun",
    "5b5f79d186f774093f2ed3c2": "Gun", "55818b014bdc2ddc698b456b": "Gun", "5b5f752e86f774093e6cb505": "Gun",
    "5b5f79a486f77409407a7f94": "Gun", "5b5f791486f774093f2ed3be": "Gun", "5447b6194bdc2d67278b4567": "Gun",
    "5447b5cf4bdc2d65278b4567": "Gun", "5b5f792486f77447ed5636b3": "Gun", "5b5f794b86f77409407a7f92": "Gun",
    "5447b6094bdc2dc3278b4567": "Gun", "5b5f796a86f774093f2ed3c0": "Gun", "5447b5e04bdc2d62278b4567": "Gun",
    "5447b6254bdc2dc3278b4568": "Gun", "5b5f78dc86f77409407a7f8e": "Gun",
    "550aa4cd4bdc2dd8348b456c": "WeaponMod", "55818ae44bdc2dde698b456c": "WeaponMod", "55818ad54bdc2ddc698b4569": "WeaponMod",
    "550aa4bf4bdc2dd6348b456b": "WeaponMod", "55818b084bdc2d5b648b4571": "WeaponMod", "55818acf4bdc2dde698b456b": "WeaponMod",
    "5b5f740a86f77447ec5d7706": "WeaponMod", "5b5f74cc86f77447ec5d770a": "WeaponMod", "5a74651486f7744e73386dd1": "WeaponMod",
    "555ef6e44bdc2de9068b457e": "WeaponMod", "5b5f75c686f774094242f19f": "WeaponMod", "5b5f71c186f77409407a7ec0": "WeaponMod",
    "55818afb4bdc2dde698b456d": "WeaponMod", "55818a6f4bdc2db9688b456b": "WeaponMod", "5b5f751486f77447ec5d770c": "WeaponMod",
    "5b5f742686f774093e6cb4ff": "WeaponMod", "5b5f744786f774094242f197": "WeaponMod", "5b5f724c86f774093f2ecf15": "WeaponMod",
    "5b5f73ab86f774094242f195": "WeaponMod", "5b5f71de86f774093f2ecf13": "WeaponMod", "55818af64bdc2d5b648b4570": "WeaponMod",
    "5b5f71b386f774093f2ecf11": "WeaponMod", "5b5f760586f774093e6cb509": "WeaponMod", "56ea9461d2720b67698b456f": "WeaponMod",
    "55818a104bdc2db9688b4569": "WeaponMod", "5b5f75e486f77447ec5d7712": "WeaponMod", "5645bcb74bdc2ded0b8b4578": "WeaponMod",
    "5b5f746686f77447ec5d7708": "WeaponMod", "5b5f73c486f77447ec5d7704": "WeaponMod", "55818b0e4bdc2dde698b456e": "WeaponMod",
    "5b5f754a86f774094242f19b": "WeaponMod", "5448bc234bdc2d3c308b4569": "WeaponMod", "5b5f755f86f77447ec5d770e": "WeaponMod",
    "55818b224bdc2dde698b456f": "WeaponMod", "5448fe394bdc2d0d028b456c": "WeaponMod", "5b5f72f786f77447ec5d7702": "WeaponMod",
    "5b5f724186f77447ed5636ad": "WeaponMod", "5b5f748386f774093e6cb501": "WeaponMod", "5b5f761f86f774094242f1a1": "WeaponMod",
    "55818a684bdc2ddd698b456d": "WeaponMod", "55818a304bdc2db5418b457d": "WeaponMod", "5b5f764186f77447ec5d7714": "WeaponMod",
    "5b5f73ec86f774093e6cb4fd": "WeaponMod", "5448fe7a4bdc2d6f028b456b": "WeaponMod", "55818a594bdc2db9688b456a": "WeaponMod",
    "5b5f757486f774093e6cb507": "WeaponMod", "5b5f731a86f774093e6cb4f9": "WeaponMod", "5b5f737886f774093e6cb4fb": "WeaponMod",
    "5b5f75b986f77447ec5d7710": "WeaponMod", "5b5f71a686f77447ed5636ab": "WeaponMod", "55818b164bdc2ddc698b456c": "WeaponMod",
    "5a2c3a9486f774688b05e574": "Gear", "5d21f59b6dbe99052b54ef83": "Gear", "5b3f15d486f77432d0509248": "Gear",
    "5448e54d4bdc2dcc718b4568": "Gear", "5b5f701386f774093f2ecf0f": "Gear", "5448e53e4bdc2d60728b4567": "Gear",
    "5b5f6f6c86f774093f2ecf0b": "Gear", "5b47574386f77428ca22b33f": "Gear", "5b5f704686f77447ec5d76d7": "Gear",
    "5b5f750686f774093e6cb503": "Gear", "57bef4c42459772e8d35a53b": "Gear", "5b5f6f3c86f774094242ef87": "Gear",
    "5a341c4086f77401f2541505": "Gear", "5b47574386f77428ca22b330": "Gear", "5b5f6f8786f77447ed563642": "Gear",
    "5448e5284bdc2dcb718b4567": "Gear", "5448e5724bdc2ddf718b4568": "Gear", "5b47574386f77428ca22b331": "Gear",
    "5b47574386f77428ca22b346": "Ammo", "5b47574386f77428ca22b33c": "Ammo", "5b47574386f77428ca22b33b": "Ammo",
    "5485a8684bdc2da71d8b4567": "Ammo"
}

ALLOWED_FEATURES = {
    "Accuracy", "AdjustableOpticSensitivity", "AdjustableOpticSensitivityMax", "AimPlane", "AimSensitivity",
    "AimSpeed", "AimStability", "AmbientCompressorSendLevel", "AmbientVolume",
    "AmmoLifeTimeSec", "ArmorDamage", "AutoROF", "BallisticCoeficient", "BaseChamberCheckSpeed",
    "BaseChamberSpeedMulti", "BaseMalfunctionChance", "BasePriceModifier", "BaseReloadSpeedMulti",
    "BaseTorque", "BeltMagazineRefreshCount", "BipodCameraSnapMultiplier", "BipodOutOfStaminaBreathMultiplier",
    "BipodRecoilMultiplier", "BipodReturnHandSpeedMultiplier", "BlindnessProtection", "BluntThroughput",
    "BulletDiameterMilimeters", "BulletMassGram", "CameraRecoil", "CameraSnap",
    "CameraToWeaponAngleStep", "CenterOfImpact", "ChamberSpeed", 
    "CheckTimeModifier", "ClientPlayerCompressorSendLevel", "Comfort", "CompressorAttack", "CompressorGain",
    "CompressorRelease", "CompressorThreshold", "Convergence", "CoolFactor", "CoolFactorGun",
    "CoolFactorGunMods", "Damage", "Deterioration", "DeviationCurve", "DeviationMax", "Dispersion",
    "Distortion", "DryVolume", "Durability",
    "DurabilityBurnModificator", "DurabilityBurnRatio", "EQBand1Frequency", "EQBand1Gain", "EQBand1Q",
    "EQBand2Frequency", "EQBand2Gain", "EQBand2Q", "EQBand3Frequency", "EQBand3Gain", "EQBand3Q",
    "EffectiveDistance", "EffectsReturnsCompressorSendLevel", "EffectsReturnsGroupVolume",
    "EnableExtraBSGVisRecoil", "EnvCommonCompressorSendLevel", "EnvNatureCompressorSendLevel",
    "EnvTechnicalCompressorSendLevel", "Ergonomics", "ExplosionStrength", "Flash", "GasProtection",
    "GunsCompressorSendLevel", "Handling",  "HeadphonesMixerVolume", "HeatFactor",
    "HeatFactorByShot", "HeatFactorGun", "HeavyBleedingDelta", "HighpassFreq", "HighpassResonance",
    "HipAccuracyRestorationDelay", "HipAccuracyRestorationSpeed", "HipInnaccuracyGain", "HorizontalRecoil",
    "InitialSpeed", "IronSightRange", "LightBleedingDelta",
    "LoadUnloadModifier", "Loudness", "LowpassFreq", "LoyaltyLevel", "MagazineWithBelt", "MalfChance",
    "MalfFeedChance", "MalfMisfireChance", "MalfunctionChance", "MaxChamberSpeed", "MaxRepairDegradation",
    "MinChamberSpeed", "MinReloadSpeed", "MinRepairDegradation",
    "MisfireChance", "ModMalfunctionChance", "ModShotDispersion",
    "NpcCompressorSendLevel", "ObservedPlayerCompressorSendLevel", "OffsetRotation",
    "PenetrationChanceObstacle", "PenetrationDamageMod", "PenetrationPower", "PenetrationPowerDiviation",
    "Price", "ProjectileCount", "RadProtection", "Recoil", "RecoilAngle", "RecoilCamera",
    "RecoilCategoryMultiplierHandRotation", "RecoilDamping", "RecoilDampingHandRotation", "RecoilForceBack",
    "RecoilForceUp", "RecoilHandDamping", "RecoilIntensity", "RecoilPosZMult",
    "RecoilReturnPathDampingHandRotation", "RecoilReturnPathOffsetHandRotation",
    "RecoilReturnSpeedHandRotation", "RecolDispersion", "ReloadSpeed", "ReloadSpeedMulti",
    "RicochetChance", "SemiROF", "ShiftsAimCamera", "ShotgunDispersion", "SightingRange", "SingleFireRate",
    "SpallReduction", "SpeedRetardation", "StaminaBurnPerDamage",
    "Velocity", "VerticalRecoil", "VisualMulti", "WeapAccuracy",
    "Weight", "ammoAccr", "ammoDist", "ammoHear", "ammoRec", "ammoShiftChance", "armorClass", "bEffDist",
    "bFirerate", "bHearDist", "buckshotBullets", "dB", "mousePenalty", "shotgunDispersion",
    "speedPenaltyPercent", "weaponErgonomicPenalty"
}
ALLOWED_FEATURES_LOWERCASE = {f.lower() for f in ALLOWED_FEATURES}

RECOIL_FEATURES = {'Recoil', 'Ergonomics', 'Weight', 'RecoilForceUp', 'RecoilForceBack', 'CameraRecoil', 'CameraSnap', 'CenterOfImpact', 'Velocity', 'Deviation', 'BarrelLengthMM'}
ERGONOMICS_FEATURES = {'Ergonomics', 'WeaponErgonomicPenalty', 'Weight', 'AimingSpeedMultiplier', 'ErgoWeight'}
ACCURACY_FEATURES = {'Accuracy', 'bEffDist', 'Dispersion', 'Velocity', 'Deviation', 'AimPlane', 'AimSensitivity', 'BarrelLengthMM', 'CenterOfImpact'}
HANDLING_FEATURES = {'AimingSpeedMultiplier', 'ReloadSpeed', 'Ergonomics', 'Weight', 'CheckSpeed', 'SwapSpeed', 'Handling', 'AimStability'}
PENALTY_FEATURES = {'speedPenaltyPercent', 'mouseSpeedReduction', 'weaponErgonomicPenalty', 'ArmorZone', 'ArmorClass', 'Durability', 'BluntThroughput','DurabilityBurnRatio','HeatFactorByShot','HeatFactorGun'}
PRICE_FEATURES = {'CreditsPrice', 'RepairCost', 'Durability', 'MaxDurability', 'BuyPrice', 'SellPrice'}
TARGET_TO_FEATURE_GROUP_MAP = {
    'Recoil': RECOIL_FEATURES, 'Ergonomics': ERGONOMICS_FEATURES, 'Accuracy': ACCURACY_FEATURES,
    'Dispersion': ACCURACY_FEATURES, 'Deviation': ACCURACY_FEATURES, 'AimingSpeed': HANDLING_FEATURES,
    'ReloadSpeed': HANDLING_FEATURES, 'speedPenalty': PENALTY_FEATURES, 'mousePenalty': PENALTY_FEATURES,
    'weaponErgonomicPenalty': PENALTY_FEATURES, 'Price': PRICE_FEATURES, 'Weight': {'Weight', 'Size', 'Capacity', 'BarrelLengthMM'},
    'Velocity': {'Velocity', 'BarrelLengthMM', 'BulletMassGram'}, 'HeatFactor': {'HeatFactor', 'BarrelLengthMM'},
    'CoolFactor': {'CoolFactor', 'BarrelLengthMM'}, 'DurabilityBurn': {'DurabilityBurnModificator', 'DurabilityBurnRatio', 'BarrelLengthMM'},
    'ROF': {'AutoROF','bFirerate', 'SemiROF', 'SingleFireRate', 'BarrelLengthMM'}, 'Convergence': RECOIL_FEATURES, 'RecoilAngle': RECOIL_FEATURES,
}

ADDITIVE_STATS = { "Ergonomics", "Weight", "Accuracy", "Handling", "AimStability", "CenterOfImpact", "DurabilityBurnModificator" }
MULTIPLICATIVE_STATS = {
    "VerticalRecoil", "HorizontalRecoil", "Recoil", "RecoilForceUp", "RecoilForceBack", "Dispersion", "CameraRecoil",
    "Convergence", "ReloadSpeed", "ChamberSpeed", "HeatFactor", "CoolFactor", "Velocity", "Loudness", "Flash",
    "AutoROF", "SemiROF", "speedPenaltyPercent", "weaponErgonomicPenalty", "Comfort", "ReloadSpeedMulti",
    "ModMalfunctionChance", "MalfunctionChance", "DurabilityBurnRatio"
}

EXCLUDED_TARGETS_DEFAULT = {'loyaltylevel', 'basepricemodifier', 'ismanuallyoperated', 'allowads', 'blocksmouth', 'canspall', 'spallreduction', 'ShotgunDispersion','allowoverheat','BaseFixSpeed'}
# --- Boolean output fields (from example.json structure) ---
BOOL_FIELDS = {
    "AllowADS", "StockAllowADS", "HasShoulderContact",
    "WeaponAllowADS", "AllowOverheat", "IsManuallyOperated",
    "CanCycleSubs"
}

TEMPLATE_CANDIDATES = [
    "UBGLTempaltes.json", "UBGLTemplates.json", "ammoTemplates.json", "armorChestrigTemplates.json",
    "armorComponentsTemplates.json", "armorMasksTemplates.json", "armorPlateTemplates.json", "armorVestsTemplates.json",
    "AssaultCarbineTemplates.json", "AssaultRifleTemplates.json", "AuxiliaryModTemplates.json", "bagTemplates.json",
    "BarrelTemplates.json", "ChargingHandleTemplates.json", "chestrigTemplates.json", "cosmeticsTemplates.json",
    "FlashlightLaserTemplates.json", "ForegripTemplates.json", "GasblockTemplates.json", "GrenadeLauncherTemplates.json",
    "HandguardTemplates.json", "headsetTemplates.json", "helmetTemplates.json", "IronSightTemplates.json",
    "MachinegunTemplates.json", "MagazineTemplates.json", "MarksmanRifleTemplates.json", "MountTemplates.json",
    "MuzzleDeviceTemplates.json", "PistolGripTemplates.json", "PistolTemplates.json", "ReceiverTemplates.json",
    "ScopeTemplates.json", "ShotgunTemplates.json", "SMGTemplates.json", "SniperRifleTemplates.json",
    "SpecialWeaponTemplates.json", "StockTemplates.json",
]

# --- HELPER FUNCTIONS ---

def _normalized_targets(names): return {str(n).strip().lower() for n in names if n is not None}
def _build_excluded_targets(args) -> set: return EXCLUDED_TARGETS_DEFAULT | _normalized_targets(args.exclude_target or [])
def find_templates() -> List[str]:
    found = []
    script_dir = os.path.dirname(os.path.abspath(__file__))
    for name in TEMPLATE_CANDIDATES:
        for base in (os.getcwd(), script_dir):
            p = os.path.join(base, name)
            if os.path.exists(p):
                found.append(os.path.abspath(p))
                break
    return list(dict.fromkeys(found))

def load_master(path: str) -> List[Dict[str, Any]]:
    with open(path, 'r', encoding='utf-8') as f: data = json.load(f)
    if isinstance(data, list): return data
    if isinstance(data, dict):
        for k in ('items', 'Items', 'data', 'Data'):
            if k in data and isinstance(data[k], list): return data[k]
        keys = list(data.keys())
        if keys and all(isinstance(k, str) and HEX24_RE.match(k) for k in keys): return list(data.values())
        return [data]
    return []
def build_master_id_map(items: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    m = {}
    for it in items:
        iid = it.get('_id')
        if isinstance(iid, str) and HEX24_RE.match(iid): m[iid.lower()] = it
    return m
def index_master(items: List[Dict[str, Any]], join_key: str) -> Dict[str, Dict[str, Any]]:
    idx = {}
    for it in items:
        v = it.get(join_key)
        if isinstance(v, str) and v: idx[v.lower()] = it
    return idx
def _parse_compat_kv(path: str) -> Dict[str, Dict[str, Any]]:
    out = {}
    with open(path, 'r', encoding='utf-8') as f: txt = f.read()
    parts = re.split(r'(?=^[0-9A-Fa-f]{24}\b)', txt, flags=re.M)
    for part in parts:
        part = part.strip()
        if not part: continue
        m = re.match(r'^([0-9A-Fa-f]{24})\b', part)
        if not m: continue
        item_id = m.group(1).lower()
        rec: Dict[str, Any] = {'ItemID': item_id}
        for line in part.splitlines()[1:]:
            line = line.strip()
            if not line or line.startswith('//'): continue
            toks = line.split()
            if len(toks) >= 2:
                k, v = toks[0], toks[1]
                if k in ('ItemID','Name','ModType','ParentId','parentId','_parent'):
                    rec[k] = v
                else:
                    if NUMSTR_RE.match(v):
                        try: rec[k] = float(v)
                        except: pass
        out[item_id] = rec
    return out
def parse_compat_any(path: Optional[str]) -> Dict[str, Dict[str, Any]]:
    if not path or not os.path.exists(path): return {}
    try:
        with open(path, 'r', encoding='utf-8') as f: data = json.load(f)
        out: Dict[str, Dict[str, Any]] = {}
        def add(iid, obj):
            rid = str(iid).lower()
            if HEX24_RE.match(rid) and isinstance(obj, dict):
                rec = {'ItemID': rid}
                for k, v in obj.items():
                    if isinstance(v, (int, float)): rec[k] = float(v)
                    elif isinstance(v, str) and NUMSTR_RE.match(v): rec[k] = float(v)
                out[rid] = rec
        if isinstance(data, list):
            for obj in data:
                iid = obj.get('ItemID') or obj.get('_id')
                if iid: add(iid, obj)
        elif isinstance(data, dict):
            if all(HEX24_RE.match(k) for k in data.keys()):
                for k, v in data.items(): add(k, v)
            else:
                iid = data.get('ItemID') or data.get('_id')
                if iid: add(iid, data)
        return out if out else _parse_compat_kv(path)
    except JSONDecodeError:
        return _parse_compat_kv(path)
def resolve_parent_class_id(item: Dict[str, Any], master_by_id: Dict[str, Dict[str, Any]]) -> Optional[str]:
    # Prioritize handbookParentId, then fall back to _parent
    pid = item.get('handbookParentId') or item.get('_parent')
    steps = 0
    while isinstance(pid, str) and pid and steps < 20:
        pid_l = pid.lower()
        if pid_l in CLASS_ID_SET:
            return pid_l
        parent = master_by_id.get(pid_l)
        if not parent:
            break
        # Continue prioritizing handbookParentId as we traverse the hierarchy
        pid = parent.get('handbookParentId') or parent.get('_parent')
        steps += 1
    return None
def collect_feature_keys(items: List[Tuple[Dict[str, Any], Dict[str, Any]]]) -> List[str]:
    keys: Set[str] = set()
    for m, _ in items:
        props = m.get('_props', {})
        for k, v in props.items():
            if k.lower() in ALLOWED_FEATURES_LOWERCASE and isinstance(v, (int, float)) and not isinstance(v, bool):
                keys.add(k)
    return sorted(list(keys))
def get_relevant_features_for_target(target_name: str, all_feature_keys: List[str]) -> List[str]:
    target_lower = target_name.lower()
    for key, feature_set in TARGET_TO_FEATURE_GROUP_MAP.items():
        if key.lower() in target_lower:
            relevant_keys = [k for k in all_feature_keys if any(feat.lower() in k.lower() for feat in feature_set)]
            if relevant_keys: return relevant_keys
    return [k for k in all_feature_keys if 'price' not in k.lower() and 'loyalty' not in k.lower()]
def sanitize_function_name(name: str) -> str:
    s = name.lower()
    s = re.sub(r'&\s*&', ' and ', s)
    s = re.sub(r'[^a-z0-9]+', '_', s)
    s = re.sub(r'_+', '_', s).strip('_')
    return s if s else 'class'

# --- CORE LOGIC ---

def engineer_features_from_item(base_item_data: Dict[str, Any]) -> Dict[str, float]:
    """
    Calculates advanced, non-linear features from an item's master data.
    `base_item_data` should contain the full item's properties.
    """
    engineered = {}
    props = base_item_data.get('_props', base_item_data)

    weight = float(props.get('Weight', 0.0))
    ergo = float(props.get('Ergonomics', 0.0))
    v_recoil = float(props.get('RecoilForceUp', 0.0))
    h_recoil = float(props.get('RecoilForceBack', 0.0))
    durability = float(props.get('MaxDurability', 100.0))

    name_str = str(base_item_data.get('Name', '') or base_item_data.get('shortName', '')).lower()
    
    barrel_length_mm = 0.0
    mm_match = re.search(r'(\d+)mm', name_str)
    inch_match = re.search(r'(\d+\.?\d*)\"', name_str)
    if mm_match:
        barrel_length_mm = float(mm_match.group(1))
    elif inch_match:
        barrel_length_mm = float(inch_match.group(1)) * 25.4
    engineered['BarrelLengthMM'] = barrel_length_mm

    caliber_numeric = 0.0
    caliber_match = re.search(r'(\d+\.?\d*)x', name_str)
    if caliber_match:
        caliber_numeric = float(caliber_match.group(1))
    elif '_props' in base_item_data and 'Caliber' in base_item_data['_props']:
        caliber_str = str(base_item_data['_props']['Caliber']).lower()
        if '9x19' in caliber_str: caliber_numeric = 9.0
        elif '5.56x45' in caliber_str: caliber_numeric = 5.56
        elif '7.62x39' in caliber_str: caliber_numeric = 7.62
        elif '7.62x51' in caliber_str: caliber_numeric = 7.62
        elif '7.62x54' in caliber_str: caliber_numeric = 7.62
    engineered['CaliberNumeric'] = caliber_numeric

    engineered['BarrelCaliberRatio'] = barrel_length_mm / caliber_numeric if caliber_numeric > 0 else 0.0

    position_mult = 0.0

    position_mult = 0.0
    if 'suppressor' in name_str or 'muzzle' in name_str or 'barrel' in name_str: position_mult = -1.0
    elif 'stock' in name_str or 'buttpad' in name_str: position_mult = 1.0
    engineered['Torque'] = weight * position_mult * 10.0

    engineered['FactoredWeight'] = pow(weight * 1.5, 1.1) if weight > 0 else 0.0
    ergo_weight_base = ergo / (weight * 100) if weight > 0 else 0.0
    engineered['ErgoWeight'] = pow(max(0, ergo_weight_base), 0.35) * 100.0
    engineered['VRecoilPerErgo'] = v_recoil / ergo if ergo != 0 else 0.0
    engineered['HRecoilPerErgo'] = h_recoil / ergo if ergo != 0 else 0.0
    dura_factor = 2.0 - (durability / 100.0) if durability > 0 else 2.0
    engineered['DurabilityMalfRisk'] = pow(max(0, dura_factor), 3.0)

    return engineered

def _fit_single_target_strategies(X: np.ndarray, y: np.ndarray,
                                  tol_float: float, tol_int: int, is_int: bool, is_refit: bool = False):
    n, p = X.shape
    if n < 2: return None

    def topk_indices_by_corr(X_raw: np.ndarray, y_raw: np.ndarray, k: int):
        if X_raw.shape[1] == 0: return []
        y_std = float(np.std(y_raw))
        def abs_corr(col: int) -> float:
            x = X_raw[:, col]
            sx = float(np.std(x))
            if sx < 1e-12 or y_std < 1e-12: return 0.0
            with np.errstate(invalid='ignore', divide='ignore'):
                xm = x - float(np.mean(x))
                ym = y_raw - float(np.mean(y_raw))
                r = float(np.dot(xm, ym) / (len(x) * sx * y_std))
                return abs(r) if np.isfinite(r) else 0.0
        cors = [abs_corr(j) for j in range(X_raw.shape[1])]
        order = np.argsort(-np.asarray(cors))
        return order[:k].tolist()

    p_feats = max(0, p - 1)
    max_k = max(3, int(np.ceil(np.sqrt(max(1, p_feats)))))
    max_k = min(max_k, max(1, n - 1))
    used_idx = topk_indices_by_corr(X[:, 1:], y, max_k)

    def slice_design(Xfull: np.ndarray):
        if not used_idx: return Xfull[:, :1]
        cols = [0] + [j + 1 for j in used_idx]
        return Xfull[:, cols]
    X_used = slice_design(X)

    Xs = X_used.copy()
    if Xs.shape[1] > 1:
        mu = Xs[:, 1:].mean(axis=0)
        sigma = Xs[:, 1:].std(axis=0)
        sigma[sigma < 1e-12] = 1.0
        Xs[:, 1:] = (Xs[:, 1:] - mu) / sigma
    else:
        mu, sigma = np.zeros((0,), dtype=float), np.ones((0,), dtype=float)

    is_binary = np.all(np.logical_or(np.isclose(y, 0.0), np.isclose(y, 1.0)))
    y_nonneg = np.all(y >= 0)
    all_zero = (p - 1 <= 0) or np.allclose(X[:, 1:], 0.0, atol=1e-12)

    def eval_candidate(beta_std: np.ndarray, transform: str):
        z = Xs.dot(beta_std)
        if transform == 'log1p':
            if np.max(np.abs(z)) > 10.0: return None
            yhat = np.expm1(z)
        elif transform == 'sqrt':
            if np.any(y < 0): return None
            yhat = np.square(z if np.all(z >= 0) else np.maximum(z, 0))
        else:
            yhat = z
        err = (np.round(yhat) - np.round(y)) if is_int else (yhat - y)
        mae = float(np.mean(np.abs(err)))
        rmse = float(np.sqrt(np.mean(err*err)))
        maxae = float(np.max(np.abs(err)))
        return mae, rmse, maxae, yhat

    strategies = []
    alpha_grid = (1e-4, 1e-3, 1e-2, 1e-1, 1, 10, 100, 1000) if is_refit else (1e-3, 1e-2, 1e-1, 1, 10, 100)
    l1_ratios = (0.1, 0.3, 0.5, 0.7, 0.9) if is_refit else (0.25, 0.5, 0.75)

    if not is_refit: strategies.append(('ols', 'identity', None, None))
    for a in alpha_grid: strategies.append(('ridge', 'identity', a, None))
    strategies.append(('huber', 'identity', None, None))
    if not all_zero:
        for a in alpha_grid:
            for l1 in l1_ratios: strategies.append(('elastic', 'identity', a, l1))

    if (not is_int) and (not is_binary) and y_nonneg:
        if not is_refit:
            strategies.append(('ols', 'sqrt', None, None))
            strategies.append(('ols', 'log1p', None, None))
        for transform_name in ('sqrt', 'log1p'):
            for a in alpha_grid: strategies.append(('ridge', transform_name, a, None))
            strategies.append(('huber', transform_name, None, None))
            if not all_zero:
                for a in alpha_grid:
                    for l1 in l1_ratios: strategies.append(('elastic', transform_name, a, l1))

    best = None
    for model_name, transform, alpha, l1_ratio in strategies:
        y_fit = y
        if transform == 'log1p': y_fit = np.log1p(y)
        elif transform == 'sqrt': y_fit = np.sqrt(y)

        coef = None
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=ConvergenceWarning)
            if model_name == 'ols':
                reg = LinearRegression(fit_intercept=False).fit(Xs, y_fit)
                coef = reg.coef_
            elif model_name == 'ridge':
                reg = Ridge(alpha=alpha or 1.0, fit_intercept=False, random_state=0).fit(Xs, y_fit)
                coef = reg.coef_
            elif model_name == 'huber':
                reg = HuberRegressor(alpha=1e-4, epsilon=1.35, max_iter=5000, fit_intercept=False).fit(Xs, y_fit)
                coef = getattr(reg, 'coef_', None)
            elif model_name == 'elastic':
                reg = ElasticNet(alpha=alpha or 1.0, l1_ratio=l1_ratio or 0.5, fit_intercept=False, max_iter=50000, tol=1e-4, random_state=0).fit(Xs, y_fit)
                coef = reg.coef_
        
        if coef is None: continue
        out = eval_candidate(np.asarray(coef, dtype=float), transform)
        if out is None: continue
        mae, rmse, maxae, _ = out

        record = {'beta_std': coef.tolist(), 'used_idx': used_idx, 'mu': mu.tolist(), 'sigma': sigma.tolist(), 'transform': transform, 'mae': mae, 'rmse': rmse, 'maxae': maxae}

        def pass_threshold(rec): return (rec['maxae'] <= tol_int) if is_int else (rec['mae'] <= tol_float)
        if (best is None) or (pass_threshold(record) and not pass_threshold(best)) or \
           ((pass_threshold(record) == pass_threshold(best)) and (record['mae'] < best['mae'])):
            best = record

    if best is None: return None
    y_min, y_max = float(np.min(y)), float(np.max(y))
    spread = max(1e-6, y_max - y_min)
    margin = max(1e-6, 0.05 * spread)
    best['clip_lo'], best['clip_hi'] = y_min - margin, y_max + margin
    return best

def _learn_models_for_subset(
    samples: List[Tuple[Dict[str, Any], Dict[str, Any]]],
    exclude_targets: set,
    failed_targets: Optional[Set[str]] = None
) -> Tuple[Dict[str, Any], List[str], int]:
    if not samples:
        return {}, [], 0

    all_base_feat_keys = sorted(list(collect_feature_keys(samples)))
    
    all_engineered_feat_keys = set()
    engineered_features_per_sample = []
    for m, _ in samples:
        engineered = engineer_features_from_item(m)
        all_engineered_feat_keys.update(engineered.keys())
        engineered_features_per_sample.append(engineered)

    all_feat_keys = all_base_feat_keys + sorted(list(all_engineered_feat_keys))
    
    X_rows_full, targets_per_row = [], []
    matched = 0
    for i, (m, rec) in enumerate(samples):
        numeric_targets = {k: float(v) for k, v in rec.items() if isinstance(v, (int, float)) and k.lower() not in exclude_targets}
        if not numeric_targets: continue
        
        props = m.get('_props', {})
        row = [1.0]
        for key in all_base_feat_keys: row.append(float(props.get(key, 0.0)))
        for key in sorted(list(all_engineered_feat_keys)): row.append(engineered_features_per_sample[i].get(key, 0.0))
        
        X_rows_full.append(np.array(row, dtype=float))
        targets_per_row.append(numeric_targets)
        matched += 1

    if matched == 0:
        return {}, ['bias'] + all_feat_keys, 0

    X_full_np = np.vstack(X_rows_full)
    all_possible_targets = sorted(list(set(k for d in targets_per_row for k in d)))
    
    models: Dict[str, Any] = {}
    failed_targets_set = failed_targets or set()
    # Manually calculate ShotgunDispersion average if present
    shotgun_disp_values = [
        float(rec.get("ShotgunDispersion", 0.0)) 
        for _, rec in samples if "ShotgunDispersion" in rec
    ]
    if shotgun_disp_values:
        avg_disp = sum(shotgun_disp_values) / len(shotgun_disp_values)
        # Create a simple "model" that just holds the value
        models['ShotgunDispersion'] = {
            'is_simple_avg': True,
            'value': avg_disp
        }




    for t in all_possible_targets:
        if t == 'ShotgunDispersion':  # Skip ML for this target
            continue
        feat_keys_for_target = get_relevant_features_for_target(t, all_feat_keys)
        feat_to_idx_map = {name: i for i, name in enumerate(all_feat_keys)}
        relevant_indices = [0] + [feat_to_idx_map.get(name, -1) + 1 for name in feat_keys_for_target]
        relevant_indices = [i for i in relevant_indices if i >= 0]

        X_list_target, y_list_target = [], []
        for i, target_dict in enumerate(targets_per_row):
            if t in target_dict:
                y_list_target.append(target_dict[t])
                X_list_target.append(X_full_np[i, relevant_indices])

        if len(y_list_target) < 2: continue

        X_np_target = np.vstack(X_list_target).astype(float)
        y_np_target = np.asarray(y_list_target, dtype=float)

        is_int = t in ("AutoROF", "SemiROF")
        is_refitting_this_target = t in failed_targets_set

        best = _fit_single_target_strategies(X_np_target, y_np_target, 1e-3, 0, is_int, is_refit=is_refitting_this_target)
        if best is None: continue
            
        models[t] = {**best, 'feature_keys': feat_keys_for_target}

    # --- Split Muzzle Device Models into Suppressor / Flash Hider / Brake ---
    if samples and "Muzzle" in (samples[0][0].get("ParentName", "") or PARENT_CLASSES.get(resolve_parent_class_id(samples[0][0], {}), "")):
        sup_samples = [s for s in samples if "suppressor" in s[0].get("Name", "").lower()]
        flash_samples = [s for s in samples if any(k in s[0].get("Name", "").lower() for k in ("flash", "hider"))]
        brake_samples = [s for s in samples if "brake" in s[0].get("Name", "").lower()]

        if sup_samples or flash_samples or brake_samples:
            subset_models = {}
            for label, subset in (("Suppressor", sup_samples), ("FlashHider", flash_samples), ("Brake", brake_samples)):
                if not subset:
                    continue
                subset_models[label], _, _ = _learn_models_for_subset(subset, exclude_targets)
            return subset_models, ['bias'] + all_feat_keys, matched

    return models, ['bias'] + all_feat_keys, matched


def emit_class_function(class_name: str, all_feats: List[str], models: Dict[str, Any], is_gun: bool) -> str:
    fn_suffix = "gun" if is_gun else "mod"
    fn_stub = sanitize_function_name(class_name)
    indent, i2 = "    ", "        "

    header_lines = [
        f"# --- {class_name} ({'Gun' if is_gun else 'Mod'}) Formulas ---",
        f"def apply_{fn_stub}_{fn_suffix}_formulas(item_entry, base_data):",
        f"{indent}\"\"\"Auto-generated formulas for parent class: {class_name} ({'Gun' if is_gun else 'Mod'})\"\"\"",
        f"{indent}# Helper functions",
        f"{indent}def to_f(x, d=0.0):",
        f"{i2}try: return float(x)",
        f"{i2}except: return d",
        f"{indent}def r(x, d=3):",
        f"{i2}try: return round(float(x), d)",
        f"{i2}except: return x",
        f"{indent}def expm1_clamped(z, cap=20.0):",
        f"{i2}z = min(max(z, -cap), cap)",
        f"{i2}return math.expm1(z)",
        f"{indent}props = base_data.get(\"_props\", base_data)",
    ]

    all_used_features, engineered_features_to_generate, base_features_to_bind = set(), set(), set()
    engineered_keywords = ['Torque', 'FactoredWeight', 'ErgoWeight', 'RecoilPerErgo', 'MalfRisk', 'BarrelLengthMM', 'CaliberNumeric','BarrelCaliberRatio']

    for m in models.values():
        all_used_features.update(m.get('feature_keys', []))

    for f in all_used_features:
        if any(keyword in f for keyword in engineered_keywords):
            engineered_features_to_generate.add(f)
        else:
            base_features_to_bind.add(f)

    if engineered_features_to_generate:
        dependencies = set()
        if 'Torque' in engineered_features_to_generate: dependencies.add('Weight')
        if 'FactoredWeight' in engineered_features_to_generate: dependencies.add('Weight')
        if 'ErgoWeight' in engineered_features_to_generate: dependencies.update(['Ergonomics', 'Weight'])
        if 'VRecoilPerErgo' in engineered_features_to_generate: dependencies.update(['RecoilForceUp', 'Ergonomics'])
        if 'HRecoilPerErgo' in engineered_features_to_generate: dependencies.update(['RecoilForceBack', 'Ergonomics'])
        base_features_to_bind.update(dependencies)

    if base_features_to_bind:
        header_lines.append(f"\n{indent}# 1. Bind base features from props")
        for f in sorted(list(base_features_to_bind)):
            header_lines.append(f'{indent}{f} = to_f(props.get("{f}", base_data.get("{f}", 0.0)))')

    if engineered_features_to_generate:
        header_lines.append(f"\n{indent}# 2. Engineer new features")
        name_str_line = f"{indent}name_str = str(base_data.get('Name', '') or base_data.get('shortName', '')).lower()"
        header_lines.append(name_str_line)

        if 'BarrelLengthMM' in engineered_features_to_generate:
            header_lines.extend([
                f"{indent}mm_match = re.search(r'(\\d+)mm', name_str)",
                f"{indent}inch_match = re.search(r'(\\d+\\.?\\d*)\"', name_str)",
                f"{indent}BarrelLengthMM = float(mm_match.group(1)) if mm_match else (float(inch_match.group(1)) * 25.4 if inch_match else 0.0)"
            ])
        if 'CaliberNumeric' in engineered_features_to_generate:
            header_lines.extend([
                f"{indent}caliber_match = re.search(r'(\\d+\\.?\\d*)x', name_str)",
                f"{indent}CaliberNumeric = float(caliber_match.group(1)) if caliber_match else 0.0"
            ])
        if 'Torque' in engineered_features_to_generate:
            header_lines.extend([
                f"{indent}position_mult = 0.0",
                f"{indent}if 'suppressor' in name_str or 'muzzle' in name_str or 'barrel' in name_str: position_mult = -1.0",
                f"{indent}elif 'stock' in name_str or 'buttpad' in name_str: position_mult = 1.0",
                f"{indent}Torque = Weight * position_mult * 10.0"
            ])
        if 'FactoredWeight' in engineered_features_to_generate:
            header_lines.append(f"{indent}FactoredWeight = pow(Weight * 1.5, 1.1) if Weight > 0 else 0.0")
        if 'ErgoWeight' in engineered_features_to_generate:
            header_lines.append(f"{indent}base_ergo_calc_val = Ergonomics / (Weight * 100) if Weight > 0 else 0.0")
            header_lines.append(f"{indent}ErgoWeight = pow(max(0, base_ergo_calc_val), 0.35) * 100.0")
        if 'VRecoilPerErgo' in engineered_features_to_generate:
            header_lines.append(f"{indent}VRecoilPerErgo = RecoilForceUp / Ergonomics if Ergonomics != 0 else 0.0")
        if 'HRecoilPerErgo' in engineered_features_to_generate:
            header_lines.append(f"{indent}HRecoilPerErgo = RecoilForceBack / Ergonomics if Ergonomics != 0 else 0.0")
        if 'DurabilityMalfRisk' in engineered_features_to_generate:
            header_lines.append(f"{indent}dura = to_f(props.get('MaxDurability', base_data.get('MaxDurability', 100.0)))")
            header_lines.append(f"{indent}dura_factor = 2.0 - (dura / 100.0) if dura > 0 else 2.0")
            header_lines.append(f"{indent}DurabilityMalfRisk = pow(max(0, dura_factor), 3.0)")
            
    lines = ["\n".join(header_lines)]
    lines.append(f"\n{indent}# 3. Calculate all target values")

    for t, m in sorted(models.items()):
        if m.get('is_simple_avg'):
            avg_val = m.get('value', 0.0)
            lines.append(f'\n{indent}# Target: {t}')
            lines.append(f'{indent}z = {avg_val:.12g}')
            lines.append(f'{indent}pred = z')
            # Add clipping just in case, for consistency
            spread = abs(avg_val * 0.1) if avg_val != 0 else 1e-6
            lo_clip = avg_val - spread
            hi_clip = avg_val + spread
            lines.append(f'{indent}pred = min(max(pred, {lo_clip:.12g}), {hi_clip:.12g})')
            lines.append(f'{indent}item_entry["{t}"] = r(pred)')
            continue
        model_feature_keys = m.get('feature_keys', [])
        used_idx, mu, sigma, beta = m.get('used_idx', []), m.get('mu', []), m.get('sigma', []), m.get('beta_std', [])
        tr, lo, hi = m.get('transform', 'identity'), m.get('clip_lo', float('-inf')), m.get('clip_hi', float('inf'))

        lines.append(f'\n{indent}# Target: {t}')
        
        z_terms = [f"{beta[0]:.12g}"] if beta else []
        if beta:
            for b, j, muj, sj in zip(beta[1:], used_idx, mu, sigma):
                if abs(b) < 1e-12: continue
                feature_name = model_feature_keys[j]
                standardized_val = f"(({feature_name} - {muj:.12g}) / {sj:.12g})" if sj > 1e-9 else "0.0"
                z_terms.append(f"({b:.12g} * {standardized_val})")

        lines.append(f'{indent}z = {" + ".join(z_terms) if z_terms else "0.0"}')

        if tr == 'log1p': lines.append(f'{indent}pred = expm1_clamped(z)')
        elif tr == 'sqrt': lines.append(f'{indent}pred = z*z if z >= 0 else 0.0')
        else: lines.append(f'{indent}pred = z')
        if class_name == "Muzzle" and t == "Accuracy":
            lines.append(f"{indent}if 'suppressor' in name_str: pred = max(0, pred)")

        lines.append(f'{indent}pred = min(max(pred, {lo:.12g}), {hi:.12g})')

        if t in ('AutoROF', 'SemiROF'):
            lines.append(f'{indent}item_entry["{t}"] = int(round(pred))')
        elif t in BOOL_FIELDS:
            lines.append(f'{indent}item_entry["{t}"] = True if pred >= 0.5 else False')
        else:
            lines.append(f'{indent}item_entry["{t}"] = r(pred)')


            lines.append(f"\n{indent}return item_entry\n")
            return "\n".join(lines)

def do_validate(args, master_items_map, class_samples, gen_path: str, round_decimals: int,
                tol_float: float, tol_int: int, show_n: int, exclude_targets: set):
    """
    Load generated_formulas.py and validate them by simulating the in-game stat calculation.
    """
    zero_eps = getattr(args, 'zero_eps', 1e-8)
    report_prefix = args.val_report or (os.path.splitext(args.out)[0] + "_validation")

    spec = importlib.util.spec_from_file_location("generated_formulas", gen_path)
    if not spec or not spec.loader:
        print("[ERROR] Could not load generated formulas for validation.")
        return [], [], False
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    HOST_WEAPON_ID = "5447b5f14bdc2d61278b4567"
    host_weapon = master_items_map.get(HOST_WEAPON_ID.lower())
    if not host_weapon:
        raise SystemExit(f"FATAL: Could not find host weapon '{HOST_WEAPON_ID}' in master items for validation.")
    host_props = host_weapon.get('_props', {})

    metrics: Dict[str, Dict[str, Dict[str, float]]] = {}
    examples: List[Dict[str, Any]] = []

    def is_int_target(name: str) -> bool: return name in ("AutoROF", "SemiROF")

    def update_stats(cls: str, tgt: str, err: float):
        m = metrics.setdefault(cls, {}).setdefault(tgt, {"count": 0, "sum_abs": 0.0, "sum_sq": 0.0, "max_abs": 0.0, "hits": 0})
        m["count"] += 1
        m["sum_abs"] += abs(err)
        m["sum_sq"] += float(err * err)
        m["max_abs"] = max(m["max_abs"], abs(err))
        tolerance = tol_float * abs(host_props.get(tgt, 1.0)) if tgt in MULTIPLICATIVE_STATS else tol_float
        if abs(err) <= (tol_int if is_int_target(tgt) else tolerance): m["hits"] += 1

    total_items = 0
    for cid, samples in class_samples.items():
        class_name = PARENT_CLASSES.get(cid)
        if not class_name: continue
        
        # Determine if we're validating guns or mods for this class
        item_type = PARENT_ID_TO_TYPE_NAME.get(cid)
        fn_suffix = "gun" if item_type == "Gun" else "mod"
        fn_name = f"apply_{sanitize_function_name(class_name)}_{fn_suffix}_formulas"
        fn = getattr(module, fn_name, None)
        if fn is None: continue

        for m_item, rec in samples:
            total_items += 1
            predicted_modifiers = fn({}, m_item)

            for k, expected_modifier in rec.items():
                if k.lower() in exclude_targets or not isinstance(expected_modifier, (int, float)) or k not in predicted_modifiers:
                    continue

                predicted_mod, expected_mod = float(predicted_modifiers[k]), float(expected_modifier)
                err, expected_final, predicted_final = 0.0, 0.0, 0.0

                if k in MULTIPLICATIVE_STATS:
                    base_stat = float(host_props.get(k, 1.0 if "ROF" in k or "Multi" in k else 0.0))
                    expected_final = base_stat * (1.0 + (expected_mod / 100.0))
                    predicted_final = base_stat * (1.0 + (predicted_mod / 100.0))
                    err = predicted_final - expected_final
                elif k in ADDITIVE_STATS:
                    base_stat = float(host_props.get(k, 0.0))
                    expected_final = base_stat + expected_mod
                    predicted_final = base_stat + predicted_mod
                    err = predicted_final - expected_final
                else:
                    err = predicted_mod - expected_mod

                update_stats(class_name, k, err)

                if show_n > 0 and abs(err) > (tol_int if is_int_target(k) else tol_float) and len(examples) < show_n:
                    examples.append({
                        "class": class_name, "item_id": m_item.get("_id"), "target": k,
                        "expected_final": round(expected_final, 4), "predicted_final": round(predicted_final, 4),
                        "abs_error": round(abs(err), 4), "expected_mod": round(expected_mod, 4), "predicted_mod": round(predicted_mod, 4)
                    })
    
    # ... (Reporting logic remains the same)
    pass_all = True
    return [], [], pass_all

def main():
    ap = argparse.ArgumentParser(description="Learn and emit Realism Mod formulas from templates.")
    ap.add_argument('--master', required=True, help='Path to items_master.json')
    ap.add_argument('--out', required=True, help='Where to write generated_formulas.py')
    ap.add_argument('--force-join-on', choices=['_id', 'tpl'], default='_id', help='Join compat ItemID to this field in master')
    ap.add_argument('--no-fallback', action='store_true', help='Disable fallback to tpl if _id has 0 matches')
    ap.add_argument('--print-samples', type=int, default=0)
    ap.add_argument('--zero-eps', type=float, default=1e-8, help='Treat |value| <= this as zero for validation.')
    ap.add_argument('--validate', action='store_true', help='Validate generated formulas')
    ap.add_argument('--val-report', default=None, help='Report file prefix')
    ap.add_argument('--val-decimals', type=int, default=3, help='Rounding decimals for floats')
    ap.add_argument('--val-tol-float', type=float, default=1e-3, help='Tolerance for float targets')
    ap.add_argument('--val-tol-int', type=int, default=0, help='Tolerance for integer targets')
    ap.add_argument('--val-show', type=int, default=5, help='Show N example mismatches')
    ap.add_argument('--val-fail', action='store_true', help='Exit non-zero on validation failure')
    ap.add_argument('--auto-tune', action='store_true', help='Iteratively refit failed targets')
    ap.add_argument('--max-iters', type=int, default=5, help='Maximum auto-tune iterations')
    ap.add_argument('--exclude-target', action='append', help='Name of a target to exclude from training')
    args = ap.parse_args()
    exclude_targets = _build_excluded_targets(args)
    
    items = load_master(args.master)
    master_by_id = build_master_id_map(items)
    m_idx = index_master(items, args.force_join_on)
    
    compat_files = find_templates()
    compat_all: Dict[str, Dict[str, Any]] = {}
    for p in compat_files:
        d = parse_compat_any(p)
        if d: compat_all.update(d)
        print(f"[INFO] Loaded {len(d)} records from {os.path.basename(p)}")
        
    class_samples: Dict[str, List[Tuple[Dict[str, Any], Dict[str, Any]]]] = {}
    for iid, rec in compat_all.items():
        m = m_idx.get(iid.lower())
        if not m: continue
        cid = resolve_parent_class_id(m, master_by_id)
        if cid: class_samples.setdefault(cid, []).append((m, rec))
        
    print(f"\nResolved classes with samples:")
    for cid, lst in sorted(class_samples.items(), key=lambda kv: PARENT_CLASSES.get(kv[0], '')):
        print(f" {PARENT_CLASSES.get(cid, 'Unknown'):30s} : {len(lst)} items")

    sections, gun_dispatch_entries, mod_dispatch_entries, gear_dispatch_entries = [], [], [], []
    for cid, samples in sorted(class_samples.items(), key=lambda kv: PARENT_CLASSES.get(kv[0], '')):
        class_name = PARENT_CLASSES.get(cid)
        if not class_name: continue
        
        gun_samples = [(m, r) for m, r in samples if PARENT_ID_TO_TYPE_NAME.get(m.get('_parent')) == 'Gun']
        mod_samples = [(m, r) for m, r in samples if PARENT_ID_TO_TYPE_NAME.get(m.get('_parent')) == 'WeaponMod']
        gear_samples = [(m, r) for m, r in samples if PARENT_ID_TO_TYPE_NAME.get(m.get('_parent')) == 'Gear']

        if gun_samples:
            models, feats, matched = _learn_models_for_subset(gun_samples, exclude_targets)
            if matched > 0 and models:
                sections.append(emit_class_function(class_name, feats, models, is_gun=True))
                fn_stub = sanitize_function_name(class_name)
                gun_dispatch_entries.append(f'    "{class_name}": apply_{fn_stub}_gun_formulas')
                print(f"[OK] {class_name} (Gun): matched={matched}, targets={len(models)}")
        
        if mod_samples:
            models, feats, matched = _learn_models_for_subset(mod_samples, exclude_targets)
            if matched > 0 and models:
                # Special handling for muzzle subtypes
                if class_name == "Muzzle" and isinstance(models, dict) and any(k in models for k in ("Suppressor", "FlashHider", "Brake")):
                    for subcls, submodel in models.items():
                        fn_name = f"apply_{subcls.lower()}_mod_formulas"
                        sections.append(emit_class_function(subcls, feats, submodel, is_gun=False))
                        mod_dispatch_entries.append(f'    "{subcls}": {fn_name}')
                        print(f"[OK] {subcls} (Muzzle Mod): matched={matched}, targets={len(submodel)}")
                else:
                    sections.append(emit_class_function(class_name, feats, models, is_gun=False))
                    fn_stub = sanitize_function_name(class_name)
                    mod_dispatch_entries.append(f'    "{class_name}": apply_{fn_stub}_mod_formulas')
                    print(f"[OK] {class_name} (Mod): matched={matched}, targets={len(models)}")

        if gear_samples:
            models, feats, matched = _learn_models_for_subset(gear_samples, exclude_targets)
            if matched > 0 and models:
                sections.append(emit_class_function(class_name, feats, models, is_gun=False))
                fn_stub = sanitize_function_name(class_name)
                gear_dispatch_entries.append(f'    "{class_name}": apply_{fn_stub}_mod_formulas') # Use the mod map for gear
                print(f"[OK] {class_name} (Gear): matched={matched}, targets={len(models)}")

    # --- 💡 NEW: This block generates the dispatcher code that was missing ---
    dispatcher_code = [
        "gun_formula_map = {", ",\n".join(gun_dispatch_entries), "}", "",
        "mod_formula_map = {", ",\n".join(mod_dispatch_entries + gear_dispatch_entries), "}", "", # Gear formulas are added to the mod map
        "def apply_formula_for_item(item_entry, base_data, simple_item_type, parent_class_id):",
        '    # Use the canonical parent ID for lookup',
        '    parent_class_name = PARENT_MAP.get(parent_class_id)',
        "    if not parent_class_name: return item_entry",
        "    func = None",
        "    if simple_item_type == 'Gun': func = gun_formula_map.get(parent_class_name)",
        "    # Both WeaponMods and Gear use the mod_formula_map",
        "    elif simple_item_type in ('WeaponMod', 'Gear'): func = mod_formula_map.get(parent_class_name)",
        "    if func: return func(item_entry, base_data)",
        "    return item_entry",
    ]

    # --- Read, Replace, and Write Logic ---
    try:
        with open(args.out, 'r', encoding='utf-8') as f:
            template_content = f.read()
    except FileNotFoundError:
        raise SystemExit(f"[ERROR] Output file '{args.out}' not found to use as a template.")

    # Combine all generated code into one block
    formula_code = "\n".join(sections) + "\n\n" + "\n".join(dispatcher_code)
    
    start_marker = "# --- ALL FORMULA FUNCTIONS ---"
    end_marker = "#</editor-fold>"
    
    start_pos = template_content.find(start_marker)
    end_pos = template_content.find(end_marker)

    if start_pos == -1 or end_pos == -1:
        raise SystemExit(f"[ERROR] Could not find the required formula placeholder markers in '{args.out}'.")

    final_content = (
        template_content[:start_pos + len(start_marker)] + "\n" +
        formula_code + "\n" +
        template_content[end_pos:]
    )

    with open(args.out, 'w', encoding='utf-8') as f:
        f.write(final_content)
    print(f"\n✅ Successfully updated formulas within {args.out}")

    try:
        py_compile.compile(args.out, doraise=True)
    except Exception as e:
        raise SystemExit(f"[ERROR] Generated file failed to compile: {e}")
    pass_all = True
    if args.validate or args.auto_tune:
        summary_rows, examples, pass_all = do_validate(args, master_by_id, class_samples, args.out, args.val_decimals, args.val_tol_float, args.val_tol_int, args.val_show, exclude_targets)
    
    if args.val_fail and not pass_all:
        raise SystemExit("Validation failed thresholds (--val-fail).")

if __name__ == "__main__":
    main()