
import re
import math

# --- Helper functions ---
def to_f(x, d=0.0):
    try: return float(x)
    except: return d

def r(x, d=3):
    try: return round(float(x), d)
    except: return x

def expm1_clamped(z, cap=20.0):
    z = min(max(z, -cap), cap)
    return math.expm1(z)



# --- Armor (Mod) Formulas ---
def apply_armor_mod_formulas(item_entry: dict, base_data: dict, template: dict = None, context: dict = None) -> dict:
    """Auto-generated formulas for parent class: Armor (Mod)"""
    # Helper functions
    def to_f(x, d=0.0):
        try: return float(x)
        except: return d
    def r(x, d=3):
        try: return round(float(x), d)
        except: return x
    def expm1_clamped(z, cap=20.0):
        z = min(max(z, -cap), cap)
        return math.expm1(z)
    props = base_data.get("_props", base_data)

    # 1. Bind base features from props
    BlindnessProtection = to_f(props.get("BlindnessProtection", base_data.get("BlindnessProtection", 0.0)))
    BluntThroughput = to_f(props.get("BluntThroughput", base_data.get("BluntThroughput", 0.0)))
    Durability = to_f(props.get("Durability", base_data.get("Durability", 0.0)))
    Ergonomics = to_f(props.get("Ergonomics", base_data.get("Ergonomics", 0.0)))
    RecoilForceBack = to_f(props.get("RecoilForceBack", base_data.get("RecoilForceBack", 0.0)))
    RecoilForceUp = to_f(props.get("RecoilForceUp", base_data.get("RecoilForceUp", 0.0)))
    Weight = to_f(props.get("Weight", base_data.get("Weight", 0.0)))
    mousePenalty = to_f(props.get("mousePenalty", base_data.get("mousePenalty", 0.0)))
    speedPenaltyPercent = to_f(props.get("speedPenaltyPercent", base_data.get("speedPenaltyPercent", 0.0)))
    weaponErgonomicPenalty = to_f(props.get("weaponErgonomicPenalty", base_data.get("weaponErgonomicPenalty", 0.0)))

    # 2. Engineer new features
    name_str = str(base_data.get('Name', '') or base_data.get('shortName', '')).lower()
    mm_match = re.search(r'(\d+)mm', name_str)
    inch_match = re.search(r'(\d+\.?\d*)"', name_str)
    BarrelLengthMM = float(mm_match.group(1)) if mm_match else (float(inch_match.group(1)) * 25.4 if inch_match else 0.0)
    caliber_match = re.search(r'(\d+\.?\d*)x', name_str)
    CaliberNumeric = float(caliber_match.group(1)) if caliber_match else 0.0
    position_mult = 0.0
    if 'suppressor' in name_str or 'muzzle' in name_str or 'barrel' in name_str: position_mult = -1.0
    elif 'stock' in name_str or 'buttpad' in name_str: position_mult = 1.0
    Torque = Weight * position_mult * 10.0
    FactoredWeight = pow(Weight * 1.5, 1.1) if Weight > 0 else 0.0
    base_ergo_calc_val = Ergonomics / (Weight * 100) if Weight > 0 else 0.0
    ErgoWeight = pow(max(0, base_ergo_calc_val), 0.35) * 100.0
    VRecoilPerErgo = RecoilForceUp / Ergonomics if Ergonomics != 0 else 0.0
    HRecoilPerErgo = RecoilForceBack / Ergonomics if Ergonomics != 0 else 0.0
    dura = to_f(props.get('MaxDurability', base_data.get('MaxDurability', 100.0)))
    dura_factor = 2.0 - (dura / 100.0) if dura > 0 else 2.0
    DurabilityMalfRisk = pow(max(0, dura_factor), 3.0)

    # 3. Calculate all target values

    # Target: Comfort
    z = 1.03472582267 + (0.9814640118 * ((Weight - 4.77117647059) / 3.11355930682)) + (0.0198431705579 * ((BluntThroughput - 0.255405882353) / 0.0950984627239)) + (-0.963261098169 * ((FactoredWeight - 8.91453084324) / 6.31607646952)) + (-0.00865220505251 * ((weaponErgonomicPenalty - -1.88235294118) / 2.5381177125))
    pred = z
    pred = min(max(pred, 0.8365), 1.1335)
    item_entry["Comfort"] = r(pred)

    # Target: Price
    z = 148.372964397
    pred = z*z if z >= 0 else 0.0
    pred = min(max(pred, -7220.75), 173635.75)
    item_entry["Price"] = r(pred)

    # Target: ReloadSpeedMulti
    z = 0.693147180414 + (4.58437337567e-09 * ((FactoredWeight - 8.91453084324) / 6.31607646952)) + (-4.81306695614e-09 * ((Weight - 4.77117647059) / 3.11355930682))
    pred = expm1_clamped(z)
    pred = min(max(pred, 0.99725), 1.05775)
    item_entry["ReloadSpeedMulti"] = r(pred)

    # Target: mousePenalty
    z = 0
    pred = z
    pred = min(max(pred, -1e-06), 1e-06)
    item_entry["mousePenalty"] = r(pred)

    # Target: speedPenaltyPercent
    z = -3.00430416069 + (1.19478446234 * ((weaponErgonomicPenalty - -1.88235294118) / 2.5381177125)) + (-0.35430071702 * ((BluntThroughput - 0.255405882353) / 0.0950984627239))
    pred = z
    pred = min(max(pred, -6.825), 0.325)
    item_entry["speedPenaltyPercent"] = r(pred)

    # Target: weaponErgonomicPenalty
    z = -2.4606339975 + (1.11976148588 * ((weaponErgonomicPenalty - -1.88235294118) / 2.5381177125)) + (0.0315963936905 * ((speedPenaltyPercent - -2.51470588235) / 3.20955671788)) + (-0.537678024047 * ((BluntThroughput - 0.255405882353) / 0.0950984627239))
    pred = z
    pred = min(max(pred, -8.4), 0.4)
    item_entry["weaponErgonomicPenalty"] = r(pred)

    return item_entry

# --- AssaultCarbines (Gun) Formulas ---
def apply_assaultcarbines_gun_formulas(item_entry: dict, base_data: dict, template: dict = None, context: dict = None) -> dict:
    """Auto-generated formulas for parent class: AssaultCarbines (Gun)"""
    # Helper functions
    def to_f(x, d=0.0):
        try: return float(x)
        except: return d
    def r(x, d=3):
        try: return round(float(x), d)
        except: return x
    def expm1_clamped(z, cap=20.0):
        z = min(max(z, -cap), cap)
        return math.expm1(z)
    props = base_data.get("_props", base_data)

    # 1. Bind base features from props
    AimPlane = to_f(props.get("AimPlane", base_data.get("AimPlane", 0.0)))
    AimSensitivity = to_f(props.get("AimSensitivity", base_data.get("AimSensitivity", 0.0)))
    BaseMalfunctionChance = to_f(props.get("BaseMalfunctionChance", base_data.get("BaseMalfunctionChance", 0.0)))
    CameraSnap = to_f(props.get("CameraSnap", base_data.get("CameraSnap", 0.0)))
    CameraToWeaponAngleStep = to_f(props.get("CameraToWeaponAngleStep", base_data.get("CameraToWeaponAngleStep", 0.0)))
    CenterOfImpact = to_f(props.get("CenterOfImpact", base_data.get("CenterOfImpact", 0.0)))
    CoolFactorGun = to_f(props.get("CoolFactorGun", base_data.get("CoolFactorGun", 0.0)))
    CoolFactorGunMods = to_f(props.get("CoolFactorGunMods", base_data.get("CoolFactorGunMods", 0.0)))
    DeviationCurve = to_f(props.get("DeviationCurve", base_data.get("DeviationCurve", 0.0)))
    DeviationMax = to_f(props.get("DeviationMax", base_data.get("DeviationMax", 0.0)))
    Durability = to_f(props.get("Durability", base_data.get("Durability", 0.0)))
    DurabilityBurnRatio = to_f(props.get("DurabilityBurnRatio", base_data.get("DurabilityBurnRatio", 0.0)))
    Ergonomics = to_f(props.get("Ergonomics", base_data.get("Ergonomics", 0.0)))
    HeatFactorByShot = to_f(props.get("HeatFactorByShot", base_data.get("HeatFactorByShot", 0.0)))
    HeatFactorGun = to_f(props.get("HeatFactorGun", base_data.get("HeatFactorGun", 0.0)))
    HipAccuracyRestorationDelay = to_f(props.get("HipAccuracyRestorationDelay", base_data.get("HipAccuracyRestorationDelay", 0.0)))
    HipAccuracyRestorationSpeed = to_f(props.get("HipAccuracyRestorationSpeed", base_data.get("HipAccuracyRestorationSpeed", 0.0)))
    HipInnaccuracyGain = to_f(props.get("HipInnaccuracyGain", base_data.get("HipInnaccuracyGain", 0.0)))
    IronSightRange = to_f(props.get("IronSightRange", base_data.get("IronSightRange", 0.0)))
    MaxRepairDegradation = to_f(props.get("MaxRepairDegradation", base_data.get("MaxRepairDegradation", 0.0)))
    MinRepairDegradation = to_f(props.get("MinRepairDegradation", base_data.get("MinRepairDegradation", 0.0)))
    RecoilAngle = to_f(props.get("RecoilAngle", base_data.get("RecoilAngle", 0.0)))
    RecoilCamera = to_f(props.get("RecoilCamera", base_data.get("RecoilCamera", 0.0)))
    RecoilCategoryMultiplierHandRotation = to_f(props.get("RecoilCategoryMultiplierHandRotation", base_data.get("RecoilCategoryMultiplierHandRotation", 0.0)))
    RecoilDampingHandRotation = to_f(props.get("RecoilDampingHandRotation", base_data.get("RecoilDampingHandRotation", 0.0)))
    RecoilForceBack = to_f(props.get("RecoilForceBack", base_data.get("RecoilForceBack", 0.0)))
    RecoilForceUp = to_f(props.get("RecoilForceUp", base_data.get("RecoilForceUp", 0.0)))
    RecoilPosZMult = to_f(props.get("RecoilPosZMult", base_data.get("RecoilPosZMult", 0.0)))
    RecoilReturnPathDampingHandRotation = to_f(props.get("RecoilReturnPathDampingHandRotation", base_data.get("RecoilReturnPathDampingHandRotation", 0.0)))
    RecoilReturnPathOffsetHandRotation = to_f(props.get("RecoilReturnPathOffsetHandRotation", base_data.get("RecoilReturnPathOffsetHandRotation", 0.0)))
    RecoilReturnSpeedHandRotation = to_f(props.get("RecoilReturnSpeedHandRotation", base_data.get("RecoilReturnSpeedHandRotation", 0.0)))
    RecolDispersion = to_f(props.get("RecolDispersion", base_data.get("RecolDispersion", 0.0)))
    SightingRange = to_f(props.get("SightingRange", base_data.get("SightingRange", 0.0)))
    SingleFireRate = to_f(props.get("SingleFireRate", base_data.get("SingleFireRate", 0.0)))
    Velocity = to_f(props.get("Velocity", base_data.get("Velocity", 0.0)))
    Weight = to_f(props.get("Weight", base_data.get("Weight", 0.0)))
    bEffDist = to_f(props.get("bEffDist", base_data.get("bEffDist", 0.0)))
    bFirerate = to_f(props.get("bFirerate", base_data.get("bFirerate", 0.0)))
    bHearDist = to_f(props.get("bHearDist", base_data.get("bHearDist", 0.0)))
    shotgunDispersion = to_f(props.get("shotgunDispersion", base_data.get("shotgunDispersion", 0.0)))

    # 2. Engineer new features
    name_str = str(base_data.get('Name', '') or base_data.get('shortName', '')).lower()
    mm_match = re.search(r'(\d+)mm', name_str)
    inch_match = re.search(r'(\d+\.?\d*)"', name_str)
    BarrelLengthMM = float(mm_match.group(1)) if mm_match else (float(inch_match.group(1)) * 25.4 if inch_match else 0.0)
    caliber_match = re.search(r'(\d+\.?\d*)x', name_str)
    CaliberNumeric = float(caliber_match.group(1)) if caliber_match else 0.0
    position_mult = 0.0
    if 'suppressor' in name_str or 'muzzle' in name_str or 'barrel' in name_str: position_mult = -1.0
    elif 'stock' in name_str or 'buttpad' in name_str: position_mult = 1.0
    Torque = Weight * position_mult * 10.0
    FactoredWeight = pow(Weight * 1.5, 1.1) if Weight > 0 else 0.0
    base_ergo_calc_val = Ergonomics / (Weight * 100) if Weight > 0 else 0.0
    ErgoWeight = pow(max(0, base_ergo_calc_val), 0.35) * 100.0
    VRecoilPerErgo = RecoilForceUp / Ergonomics if Ergonomics != 0 else 0.0
    HRecoilPerErgo = RecoilForceBack / Ergonomics if Ergonomics != 0 else 0.0
    dura = to_f(props.get('MaxDurability', base_data.get('MaxDurability', 100.0)))
    dura_factor = 2.0 - (dura / 100.0) if dura > 0 else 2.0
    DurabilityMalfRisk = pow(max(0, dura_factor), 3.0)

    # 3. Calculate all target values

    # Target: AllowOverheat
    z = 1
    pred = z
    pred = min(max(pred, 0.999999), 1.000001)
    item_entry["AllowOverheat"] = r(pred)

    # Target: AutoROF
    z = 520.041266733 + (348.74267259 * ((bFirerate - 520) / 348.743777324))
    pred = z
    pred = min(max(pred, -3), 943)
    item_entry["AutoROF"] = int(round(pred))

    # Target: BaseChamberCheckSpeed
    z = 1.10222222222 + (-0.0455837311243 * ((CenterOfImpact - 0.0701111111111) / 0.0455837311243)) + (1.24753399359 * ((BaseMalfunctionChance - 0.215752777778) / 0.0492145197134)) + (-1.35256920475 * ((VRecoilPerErgo - 4.25859148376) / 2.63597398396)) + (-0.482127419391 * ((shotgunDispersion - 4.44444444444) / 4.96903995)) + (0.427652033535 * ((AimPlane - 0.221111111111) / 0.026010444246)) + (0.396504044144 * ((RecoilForceUp - 131.555555556) / 36.6882091599))
    pred = z
    pred = min(max(pred, 0.8175), 1.5325)
    item_entry["BaseChamberCheckSpeed"] = r(pred)

    # Target: BaseChamberSpeedMulti
    z = 0.983333333333 + (-0.045006387703 * ((CoolFactorGunMods - 1.01433333333) / 0.0520683311727)) + (-0.0379179410258 * ((CenterOfImpact - 0.0701111111111) / 0.0455837311243)) + (0.0648422174554 * ((RecoilForceUp - 131.555555556) / 36.6882091599)) + (-0.0752849794408 * ((RecoilDampingHandRotation - 0.857777777778) / 0.0129338296965)) + (0.0294062560055 * ((bHearDist - 75.5555555556) / 4.96903995)) + (-0.0294062560055 * ((MaxRepairDegradation - 0.0444444444444) / 0.00496903995)) + (0.0894190994008 * ((DeviationCurve - 1.6) / 0.268741924943))
    pred = z
    pred = min(max(pred, 0.8425), 1.0075)
    item_entry["BaseChamberSpeedMulti"] = r(pred)

    # Target: BaseFixSpeed
    z = 1.01825079822 + (0.3008152022 * ((AimPlane - 0.221111111111) / 0.026010444246)) + (-0.285663239271 * ((shotgunDispersion - 4.44444444444) / 4.96903995)) + (0.0489169524479 * ((RecoilForceUp - 131.555555556) / 36.6882091599)) + (-0.0211619125052 * ((CenterOfImpact - 0.0701111111111) / 0.0455837311243)) + (-0.0320460085374 * ((VRecoilPerErgo - 4.25859148376) / 2.63597398396)) + (0.0199763360829 * ((RecoilDampingHandRotation - 0.857777777778) / 0.0129338296965))
    pred = z*z if z >= 0 else 0.0
    pred = min(max(pred, 0.8325), 1.2175)
    item_entry["BaseFixSpeed"] = r(pred)

    # Target: BaseMalfunctionChance
    z = 0.0439698438816 + (0.00288853407715 * ((RecolDispersion - 12.8888888889) / 1.79161283296)) + (0.0913629326356 * ((HRecoilPerErgo - 14.313127803) / 11.2423725202)) + (-0.15592653303 * ((BaseMalfunctionChance - 0.215752777778) / 0.0492145197134)) + (0.122207165415 * ((VRecoilPerErgo - 4.25859148376) / 2.63597398396)) + (-0.021040506089 * ((RecoilReturnSpeedHandRotation - 2.40555555556) / 0.360897372642)) + (0.00289494649739 * ((CenterOfImpact - 0.0701111111111) / 0.0455837311243)) + (-0.0750503931675 * ((RecoilForceBack - 415.555555556) / 167.737301961))
    pred = z*z if z >= 0 else 0.0
    pred = min(max(pred, 0.00112), 0.00288)
    item_entry["BaseMalfunctionChance"] = r(pred)

    # Target: BaseReloadSpeedMulti
    z = 0.996890393105 + (0.14162439941 * ((ErgoWeight - 68.6168910461) / 11.3702623037)) + (0.013357346679 * ((Ergonomics - 37.4444444444) / 11.0364155927)) + (0.0176389334054 * ((Weight - 1.13533333333) / 0.37891335861))
    pred = z
    pred = min(max(pred, 0.785), 1.115)
    item_entry["BaseReloadSpeedMulti"] = r(pred)

    # Target: BaseTorque
    z = -0.944444444444 + (2.42539984011 * ((RecoilAngle - 89.4444444444) / 1.57134840264)) + (-2.42539984006 * ((Velocity - 0.2) / 0.565685424949)) + (66.0048609398 * ((FactoredWeight - 1.80586588746) / 0.673913303629)) + (-64.2131987852 * ((Weight - 1.13533333333) / 0.37891335861)) + (0.43007303157 * ((HeatFactorByShot - 2.32) / 0.703041013503)) + (0.12489188969 * ((CoolFactorGunMods - 1.01433333333) / 0.0520683311727)) + (-0.653822914203 * ((HeatFactorGun - 0.9958) / 0.0616997028626))
    pred = z
    pred = min(max(pred, -7.35), 0.35)
    item_entry["BaseTorque"] = r(pred)

    # Target: CameraRecoil
    z = 0.060679039669 + (-0.0423586573895 * ((RecoilForceBack - 415.555555556) / 167.737301961)) + (0.0854218074869 * ((HRecoilPerErgo - 14.313127803) / 11.2423725202)) + (-0.0597615242318 * ((VRecoilPerErgo - 4.25859148376) / 2.63597398396)) + (-9.43799504205e-08 * ((RecoilReturnSpeedHandRotation - 2.40555555556) / 0.360897372642)) + (0.0405388005665 * ((RecoilDampingHandRotation - 0.857777777778) / 0.0129338296965))
    pred = z
    pred = min(max(pred, 0.032), 0.098)
    item_entry["CameraRecoil"] = r(pred)

    # Target: CenterOfImpact
    z = 0.0663706992231 + (0.00791170100283 * ((bFirerate - 520) / 348.743777324))
    pred = z
    pred = min(max(pred, 0.03175), 0.10325)
    item_entry["CenterOfImpact"] = r(pred)

    # Target: Convergence
    z = 10.184192039 + (23.1327562221 * ((RecoilReturnPathDampingHandRotation - 0.465555555556) / 0.0177081971672)) + (5.12041076967 * ((DeviationCurve - 1.6) / 0.268741924943)) + (9.9760940508 * ((CameraSnap - 3.1) / 0.520683311727)) + (11.6536916644 * ((DeviationMax - 19.5555555556) / 3.63963096759)) + (5.111559909 * ((RecoilForceUp - 131.555555556) / 36.6882091599))
    pred = z
    pred = min(max(pred, 4.28), 15.72)
    item_entry["Convergence"] = r(pred)

    # Target: CoolFactorGun
    z = 0.0953101784628 + (-5.95462645795e-10 * ((CoolFactorGun - 2.784) / 0.271529003976)) + (-2.13115449397e-09 * ((CoolFactorGunMods - 1.01433333333) / 0.0520683311727))
    pred = expm1_clamped(z)
    pred = min(max(pred, 0.0975), 0.1525)
    item_entry["CoolFactorGun"] = r(pred)

    # Target: CoolFactorGunMods
    z = 0.694700495699 + (0.00134919658996 * ((CoolFactorGunMods - 1.01433333333) / 0.0520683311727)) + (-0.00103836910871 * ((CoolFactorGun - 2.784) / 0.271529003976))
    pred = expm1_clamped(z)
    pred = min(max(pred, 0.9993), 1.0147)
    item_entry["CoolFactorGunMods"] = r(pred)

    # Target: Dispersion
    z = 2.71353513333 + (-0.462523318378 * ((CenterOfImpact - 0.0701111111111) / 0.0455837311243)) + (0.241331556971 * ((Velocity - 0.2) / 0.565685424949)) + (-1.23411328549 * ((DeviationMax - 19.5555555556) / 3.63963096759)) + (-0.919569167514 * ((DeviationCurve - 1.6) / 0.268741924943))
    pred = expm1_clamped(z)
    pred = min(max(pred, 10.45), 22.55)
    item_entry["Dispersion"] = r(pred)

    # Target: DurabilityBurnRatio
    z = 0.4
    pred = z
    pred = min(max(pred, 0.3375), 0.6125)
    item_entry["DurabilityBurnRatio"] = r(pred)

    # Target: Ergonomics
    z = 79.9998936176 + (-0.000431844144992 * ((Ergonomics - 37.4444444444) / 11.0364155927)) + (0.000465206990413 * ((ErgoWeight - 68.6168910461) / 11.3702623037)) + (0.000231723030357 * ((Weight - 1.13533333333) / 0.37891335861))
    pred = z
    pred = min(max(pred, 74.75), 80.25)
    item_entry["Ergonomics"] = r(pred)

    # Target: HasShoulderContact
    z = 0
    pred = z
    pred = min(max(pred, -1e-06), 1e-06)
    item_entry["HasShoulderContact"] = r(pred)

    # Target: HeatFactorByShot
    z = 1
    pred = z
    pred = min(max(pred, 0.999999), 1.000001)
    item_entry["HeatFactorByShot"] = r(pred)

    # Target: HeatFactorGun
    z = 0.318707427053 + (-0.00862929880076 * ((HeatFactorByShot - 2.32) / 0.703041013503)) + (-0.0627566304241 * ((HeatFactorGun - 0.9958) / 0.0616997028626))
    pred = z
    pred = min(max(pred, 0.1775), 0.6725)
    item_entry["HeatFactorGun"] = r(pred)

    # Target: HipAccuracyRestorationDelay
    z = 0.447213602382 + (5.92870693933e-09 * ((CenterOfImpact - 0.0701111111111) / 0.0455837311243)) + (1.35961690224e-08 * ((RecolDispersion - 12.8888888889) / 1.79161283296)) + (6.79588632508e-08 * ((shotgunDispersion - 4.44444444444) / 4.96903995)) + (-5.24707370666e-08 * ((AimPlane - 0.221111111111) / 0.026010444246))
    pred = z*z if z >= 0 else 0.0
    pred = min(max(pred, 0.195), 0.305)
    item_entry["HipAccuracyRestorationDelay"] = r(pred)

    # Target: HipAccuracyRestorationSpeed
    z = 7
    pred = z
    pred = min(max(pred, 6.999999), 7.000001)
    item_entry["HipAccuracyRestorationSpeed"] = r(pred)

    # Target: HipInnaccuracyGain
    z = 0.16
    pred = z
    pred = min(max(pred, 0.159999), 0.160001)
    item_entry["HipInnaccuracyGain"] = r(pred)

    # Target: HorizontalRecoil
    z = 5.32554659477 + (0.301423737649 * ((RecoilCamera - 0.0666666666667) / 0.0163299316186)) + (0.294401521306 * ((RecoilForceUp - 131.555555556) / 36.6882091599)) + (-0.304743186498 * ((DeviationMax - 19.5555555556) / 3.63963096759)) + (-0.434014721958 * ((DeviationCurve - 1.6) / 0.268741924943)) + (-0.321221637382 * ((RecoilDampingHandRotation - 0.857777777778) / 0.0129338296965))
    pred = expm1_clamped(z)
    pred = min(max(pred, 97), 383)
    item_entry["HorizontalRecoil"] = r(pred)

    # Target: MaxChamberSpeed
    z = 1.5
    pred = z
    pred = min(max(pred, 1.499999), 1.500001)
    item_entry["MaxChamberSpeed"] = r(pred)

    # Target: MinChamberSpeed
    z = 0.7
    pred = z
    pred = min(max(pred, 0.699999), 0.700001)
    item_entry["MinChamberSpeed"] = r(pred)

    # Target: OffsetRotation
    z = 0.00765542604286 + (0.000456694486681 * ((shotgunDispersion - 5) / 5)) + (0.000456694486681 * ((bHearDist - 75) / 5)) + (0.000456694486681 * ((AimPlane - 0.225) / 0.025)) + (-0.000456694486681 * ((MaxRepairDegradation - 0.045) / 0.005)) + (-0.00010191554159 * ((DeviationCurve - 1.63125) / 0.269185693342)) + (-6.88668414809e-05 * ((DeviationMax - 19.125) / 3.63790805271)) + (-0.000443787507807 * ((RecoilReturnPathDampingHandRotation - 0.4675) / 0.0178535710714))
    pred = expm1_clamped(z)
    pred = min(max(pred, 0.00475), 0.01025)
    item_entry["OffsetRotation"] = r(pred)

    # Target: RecoilAngle
    z = 4.45136324758 + (0.00279006226516 * ((ErgoWeight - 68.6168910461) / 11.3702623037)) + (-0.163426798102 * ((HRecoilPerErgo - 14.313127803) / 11.2423725202)) + (0.0418904825821 * ((Ergonomics - 37.4444444444) / 11.0364155927)) + (0.0274042389664 * ((RecoilForceBack - 415.555555556) / 167.737301961)) + (-0.130232294295 * ((RecoilReturnSpeedHandRotation - 2.40555555556) / 0.360897372642))
    pred = expm1_clamped(z)
    pred = min(max(pred, 77.4), 90.6)
    item_entry["RecoilAngle"] = r(pred)

    # Target: RecoilDamping
    z = 0.850313625233 + (-0.120639298003 * ((CenterOfImpact - 0.0701111111111) / 0.0455837311243)) + (0.0957592425513 * ((RecoilDampingHandRotation - 0.857777777778) / 0.0129338296965)) + (-0.0724927609555 * ((RecoilForceUp - 131.555555556) / 36.6882091599)) + (-0.00960357149077 * ((RecoilForceBack - 415.555555556) / 167.737301961)) + (-0.11014716242 * ((VRecoilPerErgo - 4.25859148376) / 2.63597398396))
    pred = z
    pred = min(max(pred, 0.74375), 0.88125)
    item_entry["RecoilDamping"] = r(pred)

    # Target: RecoilHandDamping
    z = 0.621703481655 + (0.0474098307573 * ((CenterOfImpact - 0.0701111111111) / 0.0455837311243)) + (-0.0296249535311 * ((RecoilForceUp - 131.555555556) / 36.6882091599)) + (0.032795773714 * ((VRecoilPerErgo - 4.25859148376) / 2.63597398396)) + (9.7911880321e-08 * ((RecoilReturnSpeedHandRotation - 2.40555555556) / 0.360897372642)) + (-0.0836909677019 * ((RecoilCamera - 0.0666666666667) / 0.0163299316186))
    pred = z
    pred = min(max(pred, 0.4305), 0.8595)
    item_entry["RecoilHandDamping"] = r(pred)

    # Target: RecoilIntensity
    z = 0.169063312787 + (0.00623638006761 * ((ErgoWeight - 68.6168910461) / 11.3702623037)) + (0.232742880323 * ((RecoilForceBack - 415.555555556) / 167.737301961)) + (-0.0880149683107 * ((HRecoilPerErgo - 14.313127803) / 11.2423725202)) + (0.0486991371249 * ((Ergonomics - 37.4444444444) / 11.0364155927)) + (-0.0644172133813 * ((RecoilDampingHandRotation - 0.857777777778) / 0.0129338296965))
    pred = z
    pred = min(max(pred, 0.12925), 0.25575)
    item_entry["RecoilIntensity"] = r(pred)

    # Target: SemiROF
    z = 350.314811768 + (2.76125674125 * ((bFirerate - 520) / 348.743777324))
    pred = z
    pred = min(max(pred, 338.25), 376.75)
    item_entry["SemiROF"] = int(round(pred))

    # Target: ShotgunDispersion
    z = 0
    pred = z
    pred = min(max(pred, -1e-06), 1e-06)
    item_entry["ShotgunDispersion"] = r(pred)

    # Target: Velocity
    z = 0.211111111111 + (0.597112393002 * ((Velocity - 0.2) / 0.565685424949))
    pred = z
    pred = min(max(pred, -0.095), 1.995)
    item_entry["Velocity"] = r(pred)

    # Target: VerticalRecoil
    z = 97.2 + (-20.7388210529 * ((RecoilForceBack - 415.555555556) / 167.737301961)) + (71.6821690419 * ((RecoilDampingHandRotation - 0.857777777778) / 0.0129338296965)) + (-50.9136429384 * ((RecoilCamera - 0.0666666666667) / 0.0163299316186)) + (-72.1087689403 * ((Ergonomics - 37.4444444444) / 11.0364155927)) + (-39.2044697237 * ((VRecoilPerErgo - 4.25859148376) / 2.63597398396))
    pred = z
    pred = min(max(pred, 55.8), 148.2)
    item_entry["VerticalRecoil"] = r(pred)

    # Target: VisualMulti
    z = 1.22444444444 + (0.211563721843 * ((CoolFactorGunMods - 1.01433333333) / 0.0520683311727)) + (0.7290253883 * ((ErgoWeight - 68.6168910461) / 11.3702623037)) + (0.0395599166488 * ((Weight - 1.13533333333) / 0.37891335861)) + (0.41237058938 * ((FactoredWeight - 1.80586588746) / 0.673913303629)) + (-0.0779222158141 * ((CameraSnap - 3.1) / 0.520683311727)) + (-0.675240671642 * ((Ergonomics - 37.4444444444) / 11.0364155927)) + (0.00786708598257 * ((RecoilReturnPathDampingHandRotation - 0.465555555556) / 0.0177081971672))
    pred = z
    pred = min(max(pred, 1.08), 1.52)
    item_entry["VisualMulti"] = r(pred)

    # Target: WeapAccuracy
    z = 0
    pred = z
    pred = min(max(pred, -1e-06), 1e-06)
    item_entry["WeapAccuracy"] = r(pred)

    # Target: WeaponAllowADS
    z = 0
    pred = z
    pred = min(max(pred, -1e-06), 1e-06)
    item_entry["WeaponAllowADS"] = r(pred)

    # Target: Weight
    z = 0.744535582406 + (-0.911057460787 * ((FactoredWeight - 1.80586588746) / 0.673913303629)) + (1.06969005637 * ((Weight - 1.13533333333) / 0.37891335861)) + (0.000960611839358 * ((ErgoWeight - 68.6168910461) / 11.3702623037))
    pred = expm1_clamped(z)
    pred = min(max(pred, 0.7564), 2.1556)
    item_entry["Weight"] = r(pred)

    return item_entry

# --- AssaultRifles (Gun) Formulas ---
def apply_assaultrifles_gun_formulas(item_entry: dict, base_data: dict, template: dict = None, context: dict = None) -> dict:
    """Auto-generated formulas for parent class: AssaultRifles (Gun)"""
    # Helper functions
    def to_f(x, d=0.0):
        try: return float(x)
        except: return d
    def r(x, d=3):
        try: return round(float(x), d)
        except: return x
    def expm1_clamped(z, cap=20.0):
        z = min(max(z, -cap), cap)
        return math.expm1(z)
    props = base_data.get("_props", base_data)

    # 1. Bind base features from props
    AimPlane = to_f(props.get("AimPlane", base_data.get("AimPlane", 0.0)))
    AimSensitivity = to_f(props.get("AimSensitivity", base_data.get("AimSensitivity", 0.0)))
    BaseMalfunctionChance = to_f(props.get("BaseMalfunctionChance", base_data.get("BaseMalfunctionChance", 0.0)))
    CameraSnap = to_f(props.get("CameraSnap", base_data.get("CameraSnap", 0.0)))
    CameraToWeaponAngleStep = to_f(props.get("CameraToWeaponAngleStep", base_data.get("CameraToWeaponAngleStep", 0.0)))
    CenterOfImpact = to_f(props.get("CenterOfImpact", base_data.get("CenterOfImpact", 0.0)))
    CoolFactorGun = to_f(props.get("CoolFactorGun", base_data.get("CoolFactorGun", 0.0)))
    CoolFactorGunMods = to_f(props.get("CoolFactorGunMods", base_data.get("CoolFactorGunMods", 0.0)))
    DeviationCurve = to_f(props.get("DeviationCurve", base_data.get("DeviationCurve", 0.0)))
    DeviationMax = to_f(props.get("DeviationMax", base_data.get("DeviationMax", 0.0)))
    Durability = to_f(props.get("Durability", base_data.get("Durability", 0.0)))
    DurabilityBurnRatio = to_f(props.get("DurabilityBurnRatio", base_data.get("DurabilityBurnRatio", 0.0)))
    Ergonomics = to_f(props.get("Ergonomics", base_data.get("Ergonomics", 0.0)))
    HeatFactorByShot = to_f(props.get("HeatFactorByShot", base_data.get("HeatFactorByShot", 0.0)))
    HeatFactorGun = to_f(props.get("HeatFactorGun", base_data.get("HeatFactorGun", 0.0)))
    HipAccuracyRestorationDelay = to_f(props.get("HipAccuracyRestorationDelay", base_data.get("HipAccuracyRestorationDelay", 0.0)))
    HipAccuracyRestorationSpeed = to_f(props.get("HipAccuracyRestorationSpeed", base_data.get("HipAccuracyRestorationSpeed", 0.0)))
    HipInnaccuracyGain = to_f(props.get("HipInnaccuracyGain", base_data.get("HipInnaccuracyGain", 0.0)))
    IronSightRange = to_f(props.get("IronSightRange", base_data.get("IronSightRange", 0.0)))
    MaxRepairDegradation = to_f(props.get("MaxRepairDegradation", base_data.get("MaxRepairDegradation", 0.0)))
    MinRepairDegradation = to_f(props.get("MinRepairDegradation", base_data.get("MinRepairDegradation", 0.0)))
    RecoilAngle = to_f(props.get("RecoilAngle", base_data.get("RecoilAngle", 0.0)))
    RecoilCamera = to_f(props.get("RecoilCamera", base_data.get("RecoilCamera", 0.0)))
    RecoilCategoryMultiplierHandRotation = to_f(props.get("RecoilCategoryMultiplierHandRotation", base_data.get("RecoilCategoryMultiplierHandRotation", 0.0)))
    RecoilDampingHandRotation = to_f(props.get("RecoilDampingHandRotation", base_data.get("RecoilDampingHandRotation", 0.0)))
    RecoilForceBack = to_f(props.get("RecoilForceBack", base_data.get("RecoilForceBack", 0.0)))
    RecoilForceUp = to_f(props.get("RecoilForceUp", base_data.get("RecoilForceUp", 0.0)))
    RecoilPosZMult = to_f(props.get("RecoilPosZMult", base_data.get("RecoilPosZMult", 0.0)))
    RecoilReturnPathDampingHandRotation = to_f(props.get("RecoilReturnPathDampingHandRotation", base_data.get("RecoilReturnPathDampingHandRotation", 0.0)))
    RecoilReturnPathOffsetHandRotation = to_f(props.get("RecoilReturnPathOffsetHandRotation", base_data.get("RecoilReturnPathOffsetHandRotation", 0.0)))
    RecoilReturnSpeedHandRotation = to_f(props.get("RecoilReturnSpeedHandRotation", base_data.get("RecoilReturnSpeedHandRotation", 0.0)))
    RecolDispersion = to_f(props.get("RecolDispersion", base_data.get("RecolDispersion", 0.0)))
    SightingRange = to_f(props.get("SightingRange", base_data.get("SightingRange", 0.0)))
    SingleFireRate = to_f(props.get("SingleFireRate", base_data.get("SingleFireRate", 0.0)))
    Velocity = to_f(props.get("Velocity", base_data.get("Velocity", 0.0)))
    Weight = to_f(props.get("Weight", base_data.get("Weight", 0.0)))
    bEffDist = to_f(props.get("bEffDist", base_data.get("bEffDist", 0.0)))
    bFirerate = to_f(props.get("bFirerate", base_data.get("bFirerate", 0.0)))
    bHearDist = to_f(props.get("bHearDist", base_data.get("bHearDist", 0.0)))
    shotgunDispersion = to_f(props.get("shotgunDispersion", base_data.get("shotgunDispersion", 0.0)))

    # 2. Engineer new features
    name_str = str(base_data.get('Name', '') or base_data.get('shortName', '')).lower()
    mm_match = re.search(r'(\d+)mm', name_str)
    inch_match = re.search(r'(\d+\.?\d*)"', name_str)
    BarrelLengthMM = float(mm_match.group(1)) if mm_match else (float(inch_match.group(1)) * 25.4 if inch_match else 0.0)
    caliber_match = re.search(r'(\d+\.?\d*)x', name_str)
    CaliberNumeric = float(caliber_match.group(1)) if caliber_match else 0.0
    position_mult = 0.0
    if 'suppressor' in name_str or 'muzzle' in name_str or 'barrel' in name_str: position_mult = -1.0
    elif 'stock' in name_str or 'buttpad' in name_str: position_mult = 1.0
    Torque = Weight * position_mult * 10.0
    FactoredWeight = pow(Weight * 1.5, 1.1) if Weight > 0 else 0.0
    base_ergo_calc_val = Ergonomics / (Weight * 100) if Weight > 0 else 0.0
    ErgoWeight = pow(max(0, base_ergo_calc_val), 0.35) * 100.0
    VRecoilPerErgo = RecoilForceUp / Ergonomics if Ergonomics != 0 else 0.0
    HRecoilPerErgo = RecoilForceBack / Ergonomics if Ergonomics != 0 else 0.0
    dura = to_f(props.get('MaxDurability', base_data.get('MaxDurability', 100.0)))
    dura_factor = 2.0 - (dura / 100.0) if dura > 0 else 2.0
    DurabilityMalfRisk = pow(max(0, dura_factor), 3.0)

    # 3. Calculate all target values

    # Target: AllowOverheat
    z = 1
    pred = z
    pred = min(max(pred, 0.999999), 1.000001)
    item_entry["AllowOverheat"] = r(pred)

    # Target: AutoROF
    z = 665.83348119 + (69.6278455882 * ((bFirerate - 665.365853659) / 69.6278455994)) + (2.06498717291 * ((SingleFireRate - 462.926829268) / 57.0833324287))
    pred = z
    pred = min(max(pred, 568.6), 863.4)
    item_entry["AutoROF"] = int(round(pred))

    # Target: BaseChamberCheckSpeed
    z = 1.34426179591 + (0.303106094136 * ((MaxRepairDegradation - 0.0360975609756) / 0.00487804878049)) + (-0.0359476109924 * ((CenterOfImpact - 0.0410243902439) / 0.0293278256326)) + (-0.0361731886838 * ((Ergonomics - 43.7804878049) / 14.540963492)) + (-0.0159228012626 * ((AimPlane - 0.176585365854) / 0.0186899942055)) + (0.0510043972185 * ((RecoilPosZMult - 0.960975609756) / 0.118688049372)) + (0.0145628987637 * ((HRecoilPerErgo - 8.70613652119) / 3.12281065606)) + (0.140649606008 * ((ErgoWeight - 67.8617859543) / 20.9336462719))
    pred = z
    pred = min(max(pred, 0.86), 1.74)
    item_entry["BaseChamberCheckSpeed"] = r(pred)

    # Target: BaseChamberSpeedMulti
    z = 0.720219938694 + (0.0508231510953 * ((bFirerate - 665.365853659) / 69.6278455994)) + (0.0970852569054 * ((ErgoWeight - 67.8617859543) / 20.9336462719)) + (0.768689894022 * ((Weight - 1.72309756098) / 0.921504120523)) + (-0.758715985905 * ((FactoredWeight - 2.88851819242) / 1.67841692936)) + (0.0380048460449 * ((BaseMalfunctionChance - 0.178512804878) / 0.00813745128859)) + (0.0752340404275 * ((MaxRepairDegradation - 0.0360975609756) / 0.00487804878049)) + (-0.00120866541213 * ((CenterOfImpact - 0.0410243902439) / 0.0293278256326))
    pred = expm1_clamped(z)
    pred = min(max(pred, 0.53), 2.07)
    item_entry["BaseChamberSpeedMulti"] = r(pred)

    # Target: BaseFixSpeed
    z = 1.11128279179 + (0.0916842749906 * ((RecoilReturnPathDampingHandRotation - 0.480243902439) / 0.00154257446837)) + (7.3638381129e-09 * ((AimPlane - 0.176585365854) / 0.0186899942055)) + (4.1378274108e-09 * ((HeatFactorByShot - 1.37524390244) / 0.129360298597)) + (0.0235218573151 * ((RecoilPosZMult - 0.960975609756) / 0.118688049372)) + (0.0445690637706 * ((MaxRepairDegradation - 0.0360975609756) / 0.00487804878049)) + (7.28492811602e-09 * ((Ergonomics - 43.7804878049) / 14.540963492)) + (6.61196087741e-09 * ((RecoilForceBack - 340.975609756) / 46.9288448429))
    pred = z*z if z >= 0 else 0.0
    pred = min(max(pred, 0.705), 2.795)
    item_entry["BaseFixSpeed"] = r(pred)

    # Target: BaseMalfunctionChance
    z = 0.00131763942725 + (0.000698690191503 * ((CoolFactorGunMods - 1.00557804878) / 0.0446346005575)) + (-0.00042062932894 * ((HeatFactorGun - 0.982631707317) / 0.0384132817416)) + (-0.000776917644532 * ((Velocity - -0.40487804878) / 4.98905882025)) + (0.00028428864081 * ((DeviationMax - 22.4512195122) / 1.95312407049)) + (0.00028428864081 * ((Durability - 99.6341463415) / 1.30208271366)) + (-0.00028428864081 * ((DeviationCurve - 1.39024390244) / 0.143229098503)) + (0.000155718219727 * ((RecoilReturnSpeedHandRotation - 2.49512195122) / 0.124354370724))
    pred = z
    pred = min(max(pred, 0.00029), 0.00271)
    item_entry["BaseMalfunctionChance"] = r(pred)

    # Target: BaseReloadSpeedMulti
    z = 0.982556373262 + (-0.0373064218925 * ((Ergonomics - 43.7804878049) / 14.540963492)) + (-0.323966011346 * ((Weight - 1.72309756098) / 0.921504120523)) + (0.319471089995 * ((FactoredWeight - 2.88851819242) / 1.67841692936))
    pred = z
    pred = min(max(pred, 0.835), 1.165)
    item_entry["BaseReloadSpeedMulti"] = r(pred)

    # Target: BaseTorque
    z = -0.942963838807 + (2.75989257301 * ((Ergonomics - 43.7804878049) / 14.540963492)) + (0.952647500174 * ((HRecoilPerErgo - 8.70613652119) / 3.12281065606)) + (-0.41717977648 * ((VRecoilPerErgo - 3.22619314864) / 1.33432508309)) + (-0.571784793605 * ((MaxRepairDegradation - 0.0360975609756) / 0.00487804878049)) + (0.0744828959987 * ((CenterOfImpact - 0.0410243902439) / 0.0293278256326)) + (0.165317486235 * ((ErgoWeight - 67.8617859543) / 20.9336462719)) + (-0.108015581365 * ((AimPlane - 0.176585365854) / 0.0186899942055))
    pred = z
    pred = min(max(pred, -4.45), 5.45)
    item_entry["BaseTorque"] = r(pred)

    # Target: CameraRecoil
    z = 0.199399644845 + (0.00977467738498 * ((RecoilDampingHandRotation - 0.853414634146) / 0.00684666773055)) + (0.00683463143167 * ((RecoilCamera - 0.0553414634146) / 0.00673762553563)) + (-0.00376600519098 * ((RecoilForceBack - 340.975609756) / 46.9288448429)) + (0.115020012692 * ((FactoredWeight - 2.88851819242) / 1.67841692936)) + (-0.114455855345 * ((Weight - 1.72309756098) / 0.921504120523))
    pred = z*z if z >= 0 else 0.0
    pred = min(max(pred, 0.0298875), 0.0763625)
    item_entry["CameraRecoil"] = r(pred)

    # Target: CenterOfImpact
    z = 0.179246904438 + (-0.0437660782942 * ((bFirerate - 665.365853659) / 69.6278455994)) + (-0.0335263375388 * ((SingleFireRate - 462.926829268) / 57.0833324287))
    pred = z*z if z >= 0 else 0.0
    pred = min(max(pred, -0.0035), 0.0735)
    item_entry["CenterOfImpact"] = r(pred)

    # Target: Convergence
    z = 13.6904194523 + (-2.5200931262 * ((RecoilCamera - 0.0553414634146) / 0.00673762553563)) + (-1.29220324612 * ((RecoilDampingHandRotation - 0.853414634146) / 0.00684666773055)) + (-1.43454147308 * ((RecoilForceUp - 124.902439024) / 24.5345002266)) + (-0.975401764153 * ((VRecoilPerErgo - 3.22619314864) / 1.33432508309)) + (3.36620654704 * ((RecoilForceBack - 340.975609756) / 46.9288448429))
    pred = z
    pred = min(max(pred, 6.725), 23.775)
    item_entry["Convergence"] = r(pred)

    # Target: CoolFactorGun
    z = 0.0997708760509 + (-0.00542591599119 * ((CoolFactorGun - 3.17404878049) / 0.143244282433)) + (-2.74890781059e-11 * ((CoolFactorGunMods - 1.00557804878) / 0.0446346005575))
    pred = z
    pred = min(max(pred, 0.068), 0.112)
    item_entry["CoolFactorGun"] = r(pred)

    # Target: CoolFactorGunMods
    z = 1
    pred = z
    pred = min(max(pred, 0.999999), 1.000001)
    item_entry["CoolFactorGunMods"] = r(pred)

    # Target: Dispersion
    z = 2.49538911601 + (0.0952627058977 * ((AimPlane - 0.176585365854) / 0.0186899942055)) + (-0.00493988451501 * ((RecolDispersion - 10.2682926829) / 1.32562714553)) + (-0.0564885109509 * ((bEffDist - 536.585365854) / 132.529053531)) + (-0.0102263211672 * ((Velocity - -0.40487804878) / 4.98905882025))
    pred = expm1_clamped(z)
    pred = min(max(pred, 5.35), 19.65)
    item_entry["Dispersion"] = r(pred)

    # Target: DurabilityBurnRatio
    z = 0.22926136608 + (0.00801702180255 * ((DurabilityBurnRatio - 1.14536585366) / 0.0233841264667))
    pred = expm1_clamped(z)
    pred = min(max(pred, 0.1375), 0.4125)
    item_entry["DurabilityBurnRatio"] = r(pred)

    # Target: Ergonomics
    z = 8.94427191016 + (6.40772937194e-10 * ((Ergonomics - 43.7804878049) / 14.540963492)) + (-6.49867082717e-10 * ((ErgoWeight - 67.8617859543) / 20.9336462719)) + (-3.98783530623e-10 * ((FactoredWeight - 2.88851819242) / 1.67841692936))
    pred = z*z if z >= 0 else 0.0
    pred = min(max(pred, 79.75), 85.25)
    item_entry["Ergonomics"] = r(pred)

    # Target: HasShoulderContact
    z = 0.118646299123 + (0.296815900251 * ((Ergonomics - 43.7804878049) / 14.540963492)) + (0.0804363847024 * ((SingleFireRate - 462.926829268) / 57.0833324287)) + (-0.01700462328 * ((HRecoilPerErgo - 8.70613652119) / 3.12281065606)) + (0.137746828277 * ((VRecoilPerErgo - 3.22619314864) / 1.33432508309)) + (3.8902083444 * ((FactoredWeight - 2.88851819242) / 1.67841692936)) + (-3.63896915832 * ((Weight - 1.72309756098) / 0.921504120523)) + (-0.153384783408 * ((bHearDist - 81.9512195122) / 9.42738931224))
    pred = z
    pred = min(max(pred, -0.05), 1.05)
    item_entry["HasShoulderContact"] = r(pred)

    # Target: HeatFactorByShot
    z = 1
    pred = z
    pred = min(max(pred, 0.999999), 1.000001)
    item_entry["HeatFactorByShot"] = r(pred)

    # Target: HeatFactorGun
    z = 0.50314806311 + (0.0248378762409 * ((HeatFactorGun - 0.982631707317) / 0.0384132817416)) + (0.00646894396196 * ((HeatFactorByShot - 1.37524390244) / 0.129360298597))
    pred = z*z if z >= 0 else 0.0
    pred = min(max(pred, 0.169), 0.411)
    item_entry["HeatFactorGun"] = r(pred)

    # Target: HipAccuracyRestorationDelay
    z = 0.182321556794
    pred = expm1_clamped(z)
    pred = min(max(pred, 0.199999), 0.200001)
    item_entry["HipAccuracyRestorationDelay"] = r(pred)

    # Target: HipAccuracyRestorationSpeed
    z = 7
    pred = z
    pred = min(max(pred, 6.999999), 7.000001)
    item_entry["HipAccuracyRestorationSpeed"] = r(pred)

    # Target: HipInnaccuracyGain
    z = 0.148420005118
    pred = expm1_clamped(z)
    pred = min(max(pred, 0.159999), 0.160001)
    item_entry["HipInnaccuracyGain"] = r(pred)

    # Target: HorizontalRecoil
    z = 5.2933522495 + (0.100192508161 * ((RecoilCamera - 0.0553414634146) / 0.00673762553563)) + (0.0796570575501 * ((RecoilDampingHandRotation - 0.853414634146) / 0.00684666773055)) + (-0.524465338343 * ((FactoredWeight - 2.88851819242) / 1.67841692936)) + (0.645937415892 * ((Weight - 1.72309756098) / 0.921504120523)) + (0.0204389615887 * ((RecoilForceBack - 340.975609756) / 46.9288448429))
    pred = expm1_clamped(z)
    pred = min(max(pred, 107.9), 550.1)
    item_entry["HorizontalRecoil"] = r(pred)

    # Target: MaxChamberSpeed
    z = 1.49024495085 + (0.00019429736345 * ((Weight - 1.72309756098) / 0.921504120523)) + (-0.000191912863691 * ((FactoredWeight - 2.88851819242) / 1.67841692936)) + (7.68589383596e-06 * ((ErgoWeight - 67.8617859543) / 20.9336462719)) + (-3.69390971918e-07 * ((BaseMalfunctionChance - 0.178512804878) / 0.00813745128859)) + (-0.0471309401512 * ((bHearDist - 81.9512195122) / 9.42738931224)) + (-2.77611363923e-07 * ((bFirerate - 665.365853659) / 69.6278455994)) + (8.66484560636e-08 * ((RecoilCamera - 0.0553414634146) / 0.00673762553563))
    pred = z
    pred = min(max(pred, 1.16), 2.04)
    item_entry["MaxChamberSpeed"] = r(pred)

    # Target: MinChamberSpeed
    z = 0.840064579181 + (0.00891504019298 * ((RecoilReturnPathDampingHandRotation - 0.480243902439) / 0.00154257446837)) + (0.000595035556764 * ((bFirerate - 665.365853659) / 69.6278455994)) + (0.0089838316814 * ((bHearDist - 81.9512195122) / 9.42738931224)) + (0.00073609314638 * ((ErgoWeight - 67.8617859543) / 20.9336462719)) + (0.000147701426527 * ((RecoilCamera - 0.0553414634146) / 0.00673762553563)) + (0.0017095177851 * ((MaxRepairDegradation - 0.0360975609756) / 0.00487804878049)) + (0.00348884467887 * ((BaseMalfunctionChance - 0.178512804878) / 0.00813745128859))
    pred = z*z if z >= 0 else 0.0
    pred = min(max(pred, 0.695), 0.805)
    item_entry["MinChamberSpeed"] = r(pred)

    # Target: OffsetRotation
    z = 0.00872443457116 + (0.000120535829472 * ((RecoilCamera - 0.0553414634146) / 0.00673762553563)) + (-0.00096610455941 * ((RecoilForceBack - 340.975609756) / 46.9288448429)) + (-5.98495630397e-05 * ((RecoilDampingHandRotation - 0.853414634146) / 0.00684666773055)) + (-0.000817627355969 * ((bHearDist - 81.9512195122) / 9.42738931224)) + (-0.000946162195006 * ((CameraSnap - 3.51219512195) / 0.1346995246)) + (0.000580798052959 * ((RecoilForceUp - 124.902439024) / 24.5345002266)) + (0.000116876347698 * ((RecolDispersion - 10.2682926829) / 1.32562714553))
    pred = z
    pred = min(max(pred, 0.00197), 0.01363)
    item_entry["OffsetRotation"] = r(pred)

    # Target: RecoilAngle
    z = 86.2093467691 + (-41.4709852407 * ((FactoredWeight - 2.88851819242) / 1.67841692936)) + (43.7269561724 * ((Weight - 1.72309756098) / 0.921504120523)) + (-1.05802566669 * ((RecoilPosZMult - 0.960975609756) / 0.118688049372)) + (5.04439802074 * ((ErgoWeight - 67.8617859543) / 20.9336462719)) + (-2.96433218724 * ((Ergonomics - 43.7804878049) / 14.540963492))
    pred = z
    pred = min(max(pred, 78.45), 90.55)
    item_entry["RecoilAngle"] = r(pred)

    # Target: RecoilDamping
    z = 0.8255479398 + (0.012582827984 * ((RecoilCamera - 0.0553414634146) / 0.00673762553563)) + (0.00996828750301 * ((CameraSnap - 3.51219512195) / 0.1346995246)) + (-0.00034465270863 * ((RecoilForceBack - 340.975609756) / 46.9288448429)) + (-0.00464760118975 * ((RecoilDampingHandRotation - 0.853414634146) / 0.00684666773055)) + (0.0049039620733 * ((FactoredWeight - 2.88851819242) / 1.67841692936))
    pred = z
    pred = min(max(pred, 0.7755), 0.8745)
    item_entry["RecoilDamping"] = r(pred)

    # Target: RecoilHandDamping
    z = 0.833772975531 + (-0.00984120562726 * ((RecoilPosZMult - 0.960975609756) / 0.118688049372)) + (0.0187755121147 * ((RecoilCamera - 0.0553414634146) / 0.00673762553563)) + (-0.0209847473076 * ((RecoilForceBack - 340.975609756) / 46.9288448429)) + (0.00580643851576 * ((RecoilDampingHandRotation - 0.853414634146) / 0.00684666773055)) + (-0.0108775515954 * ((DeviationMax - 22.4512195122) / 1.95312407049))
    pred = z*z if z >= 0 else 0.0
    pred = min(max(pred, 0.328), 0.812)
    item_entry["RecoilHandDamping"] = r(pred)

    # Target: RecoilIntensity
    z = 0.440617827957 + (-0.0196561759909 * ((RecoilReturnPathDampingHandRotation - 0.480243902439) / 0.00154257446837)) + (0.212504196556 * ((FactoredWeight - 2.88851819242) / 1.67841692936)) + (-0.212250627496 * ((Weight - 1.72309756098) / 0.921504120523)) + (0.00937373955254 * ((RecoilAngle - 89.8780487805) / 2.81282014504)) + (-0.00659132184532 * ((ErgoWeight - 67.8617859543) / 20.9336462719))
    pred = z*z if z >= 0 else 0.0
    pred = min(max(pred, 0.0925), 0.2575)
    item_entry["RecoilIntensity"] = r(pred)

    # Target: SemiROF
    z = 394.235853053 + (-14.4624637351 * ((SingleFireRate - 462.926829268) / 57.0833324287)) + (6.53643118515 * ((bFirerate - 665.365853659) / 69.6278455994))
    pred = z
    pred = min(max(pred, 326.75), 508.25)
    item_entry["SemiROF"] = int(round(pred))

    # Target: ShotgunDispersion
    z = 0
    pred = z
    pred = min(max(pred, -1e-06), 1e-06)
    item_entry["ShotgunDispersion"] = r(pred)

    # Target: Velocity
    z = -1.98927224355 + (6.48842681588 * ((Velocity - -0.40487804878) / 4.98905882025))
    pred = z
    pred = min(max(pred, -26.775), 1.275)
    item_entry["Velocity"] = r(pred)

    # Target: VerticalRecoil
    z = 4.47266649444 + (0.106732352952 * ((RecoilForceUp - 124.902439024) / 24.5345002266)) + (0.0181285555627 * ((RecoilForceBack - 340.975609756) / 46.9288448429)) + (0.0441682818885 * ((RecoilCamera - 0.0553414634146) / 0.00673762553563)) + (0.0105212425867 * ((RecoilDampingHandRotation - 0.853414634146) / 0.00684666773055)) + (0.00237447779771 * ((VRecoilPerErgo - 3.22619314864) / 1.33432508309))
    pred = expm1_clamped(z)
    pred = min(max(pred, 56.5), 133.5)
    item_entry["VerticalRecoil"] = r(pred)

    # Target: VisualMulti
    z = 1.02307362484 + (0.0360789980342 * ((RecoilPosZMult - 0.960975609756) / 0.118688049372)) + (0.000104659655156 * ((CameraSnap - 3.51219512195) / 0.1346995246)) + (-0.00193371694712 * ((Ergonomics - 43.7804878049) / 14.540963492)) + (-0.0679428613917 * ((Weight - 1.72309756098) / 0.921504120523)) + (0.0618824159038 * ((FactoredWeight - 2.88851819242) / 1.67841692936)) + (-0.0131457323975 * ((RecoilForceBack - 340.975609756) / 46.9288448429)) + (-0.0133990128616 * ((bEffDist - 536.585365854) / 132.529053531))
    pred = z*z if z >= 0 else 0.0
    pred = min(max(pred, 0.7945), 1.7955)
    item_entry["VisualMulti"] = r(pred)

    # Target: WeapAccuracy
    z = 0
    pred = z
    pred = min(max(pred, -17), 27)
    item_entry["WeapAccuracy"] = r(pred)

    # Target: WeaponAllowADS
    z = 0
    pred = z
    pred = min(max(pred, -1e-06), 1e-06)
    item_entry["WeaponAllowADS"] = r(pred)

    # Target: Weight
    z = 1.84837908475 + (2.81826362216 * ((FactoredWeight - 2.88851819242) / 1.67841692936)) + (-2.09452610137 * ((Weight - 1.72309756098) / 0.921504120523)) + (-0.0859093095708 * ((ErgoWeight - 67.8617859543) / 20.9336462719))
    pred = z
    pred = min(max(pred, 0.165), 5.335)
    item_entry["Weight"] = r(pred)

    return item_entry

# --- AuxiliaryParts (Mod) Formulas ---
def apply_auxiliaryparts_mod_formulas(item_entry: dict, base_data: dict, template: dict = None, context: dict = None) -> dict:
    """Auto-generated formulas for parent class: AuxiliaryParts (Mod)"""
    # Helper functions
    def to_f(x, d=0.0):
        try: return float(x)
        except: return d
    def r(x, d=3):
        try: return round(float(x), d)
        except: return x
    def expm1_clamped(z, cap=20.0):
        z = min(max(z, -cap), cap)
        return math.expm1(z)
    props = base_data.get("_props", base_data)

    # 1. Bind base features from props
    Accuracy = to_f(props.get("Accuracy", base_data.get("Accuracy", 0.0)))
    CoolFactor = to_f(props.get("CoolFactor", base_data.get("CoolFactor", 0.0)))
    Durability = to_f(props.get("Durability", base_data.get("Durability", 0.0)))
    DurabilityBurnModificator = to_f(props.get("DurabilityBurnModificator", base_data.get("DurabilityBurnModificator", 0.0)))
    EffectiveDistance = to_f(props.get("EffectiveDistance", base_data.get("EffectiveDistance", 0.0)))
    Ergonomics = to_f(props.get("Ergonomics", base_data.get("Ergonomics", 0.0)))
    HeatFactor = to_f(props.get("HeatFactor", base_data.get("HeatFactor", 0.0)))
    Loudness = to_f(props.get("Loudness", base_data.get("Loudness", 0.0)))
    Recoil = to_f(props.get("Recoil", base_data.get("Recoil", 0.0)))
    RecoilForceBack = to_f(props.get("RecoilForceBack", base_data.get("RecoilForceBack", 0.0)))
    RecoilForceUp = to_f(props.get("RecoilForceUp", base_data.get("RecoilForceUp", 0.0)))
    ShiftsAimCamera = to_f(props.get("ShiftsAimCamera", base_data.get("ShiftsAimCamera", 0.0)))
    SightingRange = to_f(props.get("SightingRange", base_data.get("SightingRange", 0.0)))
    Velocity = to_f(props.get("Velocity", base_data.get("Velocity", 0.0)))
    Weight = to_f(props.get("Weight", base_data.get("Weight", 0.0)))

    # 2. Engineer new features
    name_str = str(base_data.get('Name', '') or base_data.get('shortName', '')).lower()
    mm_match = re.search(r'(\d+)mm', name_str)
    inch_match = re.search(r'(\d+\.?\d*)"', name_str)
    BarrelLengthMM = float(mm_match.group(1)) if mm_match else (float(inch_match.group(1)) * 25.4 if inch_match else 0.0)
    caliber_match = re.search(r'(\d+\.?\d*)x', name_str)
    CaliberNumeric = float(caliber_match.group(1)) if caliber_match else 0.0
    position_mult = 0.0
    if 'suppressor' in name_str or 'muzzle' in name_str or 'barrel' in name_str: position_mult = -1.0
    elif 'stock' in name_str or 'buttpad' in name_str: position_mult = 1.0
    Torque = Weight * position_mult * 10.0
    FactoredWeight = pow(Weight * 1.5, 1.1) if Weight > 0 else 0.0
    base_ergo_calc_val = Ergonomics / (Weight * 100) if Weight > 0 else 0.0
    ErgoWeight = pow(max(0, base_ergo_calc_val), 0.35) * 100.0
    VRecoilPerErgo = RecoilForceUp / Ergonomics if Ergonomics != 0 else 0.0
    HRecoilPerErgo = RecoilForceBack / Ergonomics if Ergonomics != 0 else 0.0
    dura = to_f(props.get('MaxDurability', base_data.get('MaxDurability', 100.0)))
    dura_factor = 2.0 - (dura / 100.0) if dura > 0 else 2.0
    DurabilityMalfRisk = pow(max(0, dura_factor), 3.0)

    # 3. Calculate all target values

    # Target: Accuracy
    z = 0.260103167033
    pred = z*z if z >= 0 else 0.0
    pred = min(max(pred, -0.75), 15.75)
    item_entry["Accuracy"] = r(pred)

    # Target: AimSpeed
    z = 0
    pred = z
    pred = min(max(pred, -0.05), 1.05)
    item_entry["AimSpeed"] = r(pred)

    # Target: AimStability
    z = 3.33333333333 + (0.438096478961 * ((Ergonomics - 3) / 0.816496580928)) + (0.433447014236 * ((ErgoWeight - 185.574588131) / 18.2460434193)) + (-0.408860783784 * ((Recoil - -0.333333333333) / 0.471404520791)) + (0.0589162073913 * ((HeatFactor - 0.986666666667) / 0.00471404520791))
    pred = z
    pred = min(max(pred, 1.85), 5.15)
    item_entry["AimStability"] = r(pred)

    # Target: AutoROF
    z = 0
    pred = z
    pred = min(max(pred, -1e-06), 1e-06)
    item_entry["AutoROF"] = int(round(pred))

    # Target: ChamberSpeed
    z = 4.375 + (-0.973022558209 * ((DurabilityBurnModificator - 0.9975) / 0.00433012701892)) + (1.0593696399 * ((Ergonomics - 2) / 0.707106781187)) + (0.623513216053 * ((FactoredWeight - 0.00851375397933) / 0.000888904124255))
    pred = z
    pred = min(max(pred, 2.2), 8.8)
    item_entry["ChamberSpeed"] = r(pred)

    # Target: CoolFactor
    z = 0.693147180513 + (-3.47682462268e-12 * ((CoolFactor - 1.00687179487) / 0.0327470331302))
    pred = expm1_clamped(z)
    pred = min(max(pred, 0.9475), 1.0025)
    item_entry["CoolFactor"] = r(pred)

    # Target: Dispersion
    z = -1
    pred = z
    pred = min(max(pred, -2.075), -0.425)
    item_entry["Dispersion"] = r(pred)

    # Target: DurabilityBurnModificator
    z = 1
    pred = z
    pred = min(max(pred, 0.999999), 1.000001)
    item_entry["DurabilityBurnModificator"] = r(pred)

    # Target: Ergonomics
    z = 0
    pred = z
    pred = min(max(pred, -0.3), 6.3)
    item_entry["Ergonomics"] = r(pred)

    # Target: FixSpeed
    z = 0
    pred = z
    pred = min(max(pred, -1e-06), 1e-06)
    item_entry["FixSpeed"] = r(pred)

    # Target: Handling
    z = 1.5 + (0.184815676223 * ((Ergonomics - 3) / 0.816496580928)) + (0.201575632364 * ((ErgoWeight - 185.574588131) / 18.2460434193)) + (-0.0257121397062 * ((Recoil - -0.333333333333) / 0.471404520791))
    pred = z
    pred = min(max(pred, 0.95), 2.05)
    item_entry["Handling"] = r(pred)

    # Target: HeatFactor
    z = 0.999999999969 + (1.24285938911e-10 * ((HeatFactor - 0.992153846154) / 0.0317179383537))
    pred = z*z if z >= 0 else 0.0
    pred = min(max(pred, 0.9475), 1.0025)
    item_entry["HeatFactor"] = r(pred)

    # Target: HorizontalRecoil
    z = -0.102564104871 + (0.441144884532 * ((Recoil - -0.0512820512821) / 0.220572442745)) + (-1.99497555055e-09 * ((Ergonomics - 3.17948717949) / 1.59922729533)) + (-2.66081150394e-10 * ((Weight - 0.0176666666667) / 0.0325366328718))
    pred = z
    pred = min(max(pred, -10.5), 0.5)
    item_entry["HorizontalRecoil"] = r(pred)

    # Target: ModMalfunctionChance
    z = 1.13675220402 + (-3.4191667739 * ((DurabilityBurnModificator - 0.995128205128) / 0.0146535713459)) + (4.87155434596e-08 * ((Ergonomics - 3.17948717949) / 1.59922729533)) + (-1.33511611197e-08 * ((ShiftsAimCamera - 0.00307692307692) / 0.00646642062201)) + (1.13365716289e-08 * ((HeatFactor - 0.992153846154) / 0.0317179383537)) + (3.6791988236e-08 * ((Recoil - -0.0512820512821) / 0.220572442745))
    pred = z
    pred = min(max(pred, -16.65), 19.65)
    item_entry["ModMalfunctionChance"] = r(pred)

    # Target: ReloadSpeed
    z = 0
    pred = z
    pred = min(max(pred, -1), 21)
    item_entry["ReloadSpeed"] = r(pred)

    # Target: SemiROF
    z = 0.179856115108
    pred = z
    pred = min(max(pred, -0.375), 7.875)
    item_entry["SemiROF"] = int(round(pred))

    # Target: VerticalRecoil
    z = -0.102564104366 + (0.441144886014 * ((Recoil - -0.0512820512821) / 0.220572442745)) + (1.75740603263e-09 * ((ErgoWeight - 151.867405004) / 56.058328991)) + (-5.57898828252e-10 * ((Weight - 0.0176666666667) / 0.0325366328718))
    pred = z
    pred = min(max(pred, -2.1), 0.1)
    item_entry["VerticalRecoil"] = r(pred)

    # Target: Weight
    z = 0.0176666666667 + (0.0325366328718 * ((Weight - 0.0176666666667) / 0.0325366328718))
    pred = z
    pred = min(max(pred, -0.00475), 0.20975)
    item_entry["Weight"] = r(pred)

    return item_entry

# --- Backpack (Mod) Formulas ---
def apply_backpack_mod_formulas(item_entry: dict, base_data: dict, template: dict = None, context: dict = None) -> dict:
    """Auto-generated formulas for parent class: Backpack (Mod)"""
    # Helper functions
    def to_f(x, d=0.0):
        try: return float(x)
        except: return d
    def r(x, d=3):
        try: return round(float(x), d)
        except: return x
    def expm1_clamped(z, cap=20.0):
        z = min(max(z, -cap), cap)
        return math.expm1(z)
    props = base_data.get("_props", base_data)

    # 1. Bind base features from props
    Ergonomics = to_f(props.get("Ergonomics", base_data.get("Ergonomics", 0.0)))
    RecoilForceBack = to_f(props.get("RecoilForceBack", base_data.get("RecoilForceBack", 0.0)))
    RecoilForceUp = to_f(props.get("RecoilForceUp", base_data.get("RecoilForceUp", 0.0)))
    Weight = to_f(props.get("Weight", base_data.get("Weight", 0.0)))
    mousePenalty = to_f(props.get("mousePenalty", base_data.get("mousePenalty", 0.0)))
    speedPenaltyPercent = to_f(props.get("speedPenaltyPercent", base_data.get("speedPenaltyPercent", 0.0)))
    weaponErgonomicPenalty = to_f(props.get("weaponErgonomicPenalty", base_data.get("weaponErgonomicPenalty", 0.0)))

    # 2. Engineer new features
    name_str = str(base_data.get('Name', '') or base_data.get('shortName', '')).lower()
    mm_match = re.search(r'(\d+)mm', name_str)
    inch_match = re.search(r'(\d+\.?\d*)"', name_str)
    BarrelLengthMM = float(mm_match.group(1)) if mm_match else (float(inch_match.group(1)) * 25.4 if inch_match else 0.0)
    caliber_match = re.search(r'(\d+\.?\d*)x', name_str)
    CaliberNumeric = float(caliber_match.group(1)) if caliber_match else 0.0
    position_mult = 0.0
    if 'suppressor' in name_str or 'muzzle' in name_str or 'barrel' in name_str: position_mult = -1.0
    elif 'stock' in name_str or 'buttpad' in name_str: position_mult = 1.0
    Torque = Weight * position_mult * 10.0
    FactoredWeight = pow(Weight * 1.5, 1.1) if Weight > 0 else 0.0
    base_ergo_calc_val = Ergonomics / (Weight * 100) if Weight > 0 else 0.0
    ErgoWeight = pow(max(0, base_ergo_calc_val), 0.35) * 100.0
    VRecoilPerErgo = RecoilForceUp / Ergonomics if Ergonomics != 0 else 0.0
    HRecoilPerErgo = RecoilForceBack / Ergonomics if Ergonomics != 0 else 0.0
    dura = to_f(props.get('MaxDurability', base_data.get('MaxDurability', 100.0)))
    dura_factor = 2.0 - (dura / 100.0) if dura > 0 else 2.0
    DurabilityMalfRisk = pow(max(0, dura_factor), 3.0)

    # 3. Calculate all target values

    # Target: Comfort
    z = 0.941662078423 + (0.0127477396068 * ((mousePenalty - -1.075) / 1.034105894)) + (0.00833740575299 * ((weaponErgonomicPenalty - -3.55) / 2.07304124416)) + (0.0122272646363 * ((speedPenaltyPercent - -2.7) / 1.77763888346)) + (0.000648980169524 * ((Weight - 2.1053) / 2.25986937897))
    pred = z*z if z >= 0 else 0.0
    pred = min(max(pred, 0.717), 1.223)
    item_entry["Comfort"] = r(pred)

    # Target: ReloadSpeedMulti
    z = 1
    pred = z
    pred = min(max(pred, 0.999999), 1.000001)
    item_entry["ReloadSpeedMulti"] = r(pred)

    # Target: mousePenalty
    z = 0
    pred = z
    pred = min(max(pred, -1e-06), 1e-06)
    item_entry["mousePenalty"] = r(pred)

    # Target: speedPenaltyPercent
    z = -2.69631605012 + (0.285714677159 * ((weaponErgonomicPenalty - -3.55) / 2.07304124416)) + (0.388896770749 * ((speedPenaltyPercent - -2.7) / 1.77763888346))
    pred = z
    pred = min(max(pred, -5.01), -0.39)
    item_entry["speedPenaltyPercent"] = r(pred)

    # Target: weaponErgonomicPenalty
    z = 0
    pred = z
    pred = min(max(pred, -1e-06), 1e-06)
    item_entry["weaponErgonomicPenalty"] = r(pred)

    return item_entry

# --- Barrel (Mod) Formulas ---
def apply_barrel_mod_formulas(item_entry: dict, base_data: dict, template: dict = None, context: dict = None) -> dict:
    """Auto-generated formulas for parent class: Barrel (Mod)"""
    # Helper functions
    def to_f(x, d=0.0):
        try: return float(x)
        except: return d
    def r(x, d=3):
        try: return round(float(x), d)
        except: return x
    def expm1_clamped(z, cap=20.0):
        z = min(max(z, -cap), cap)
        return math.expm1(z)
    props = base_data.get("_props", base_data)

    # 1. Bind base features from props
    Accuracy = to_f(props.get("Accuracy", base_data.get("Accuracy", 0.0)))
    CenterOfImpact = to_f(props.get("CenterOfImpact", base_data.get("CenterOfImpact", 0.0)))
    CoolFactor = to_f(props.get("CoolFactor", base_data.get("CoolFactor", 0.0)))
    DeviationCurve = to_f(props.get("DeviationCurve", base_data.get("DeviationCurve", 0.0)))
    DeviationMax = to_f(props.get("DeviationMax", base_data.get("DeviationMax", 0.0)))
    Durability = to_f(props.get("Durability", base_data.get("Durability", 0.0)))
    DurabilityBurnModificator = to_f(props.get("DurabilityBurnModificator", base_data.get("DurabilityBurnModificator", 0.0)))
    EffectiveDistance = to_f(props.get("EffectiveDistance", base_data.get("EffectiveDistance", 0.0)))
    Ergonomics = to_f(props.get("Ergonomics", base_data.get("Ergonomics", 0.0)))
    HeatFactor = to_f(props.get("HeatFactor", base_data.get("HeatFactor", 0.0)))
    Loudness = to_f(props.get("Loudness", base_data.get("Loudness", 0.0)))
    Recoil = to_f(props.get("Recoil", base_data.get("Recoil", 0.0)))
    RecoilForceBack = to_f(props.get("RecoilForceBack", base_data.get("RecoilForceBack", 0.0)))
    RecoilForceUp = to_f(props.get("RecoilForceUp", base_data.get("RecoilForceUp", 0.0)))
    ShotgunDispersion = to_f(props.get("ShotgunDispersion", base_data.get("ShotgunDispersion", 0.0)))
    SightingRange = to_f(props.get("SightingRange", base_data.get("SightingRange", 0.0)))
    Velocity = to_f(props.get("Velocity", base_data.get("Velocity", 0.0)))
    Weight = to_f(props.get("Weight", base_data.get("Weight", 0.0)))

    # 2. Engineer new features
    name_str = str(base_data.get('Name', '') or base_data.get('shortName', '')).lower()
    mm_match = re.search(r'(\d+)mm', name_str)
    inch_match = re.search(r'(\d+\.?\d*)"', name_str)
    BarrelLengthMM = float(mm_match.group(1)) if mm_match else (float(inch_match.group(1)) * 25.4 if inch_match else 0.0)
    caliber_match = re.search(r'(\d+\.?\d*)x', name_str)
    CaliberNumeric = float(caliber_match.group(1)) if caliber_match else 0.0
    position_mult = 0.0
    if 'suppressor' in name_str or 'muzzle' in name_str or 'barrel' in name_str: position_mult = -1.0
    elif 'stock' in name_str or 'buttpad' in name_str: position_mult = 1.0
    Torque = Weight * position_mult * 10.0
    FactoredWeight = pow(Weight * 1.5, 1.1) if Weight > 0 else 0.0
    base_ergo_calc_val = Ergonomics / (Weight * 100) if Weight > 0 else 0.0
    ErgoWeight = pow(max(0, base_ergo_calc_val), 0.35) * 100.0
    VRecoilPerErgo = RecoilForceUp / Ergonomics if Ergonomics != 0 else 0.0
    HRecoilPerErgo = RecoilForceBack / Ergonomics if Ergonomics != 0 else 0.0
    dura = to_f(props.get('MaxDurability', base_data.get('MaxDurability', 100.0)))
    dura_factor = 2.0 - (dura / 100.0) if dura > 0 else 2.0
    DurabilityMalfRisk = pow(max(0, dura_factor), 3.0)

    # 3. Calculate all target values

    # Target: Accuracy
    z = 0
    pred = z
    pred = min(max(pred, -1e-06), 1e-06)
    item_entry["Accuracy"] = r(pred)

    # Target: AutoROF
    z = 0.230303030303
    pred = z
    pred = min(max(pred, -4.8), 12.8)
    item_entry["AutoROF"] = int(round(pred))

    # Target: CameraRecoil
    z = -3.05626697721 + (3.59017225803 * ((Ergonomics - -13.4324324324) / 7.42727093506)) + (1.53954402317 * ((Recoil - -4.51351351351) / 2.51075117027)) + (-0.469345254339 * ((CenterOfImpact - 0.0611891891892) / 0.0468654415626)) + (-3.05935560123 * ((DeviationMax - 22.7162162162) / 5.25375096445))
    pred = z
    pred = min(max(pred, -18.45), 13.45)
    item_entry["CameraRecoil"] = r(pred)

    # Target: CenterOfImpact
    z = 0.073836
    pred = z
    pred = min(max(pred, -0.01975), 0.52475)
    item_entry["CenterOfImpact"] = r(pred)

    # Target: Convergence
    z = 0
    pred = z
    pred = min(max(pred, -11), 11)
    item_entry["Convergence"] = r(pred)

    # Target: CoolFactor
    z = 1.0060909091 + (0.102057251582 * ((CoolFactor - 1.00609090909) / 0.102057251798))
    pred = z
    pred = min(max(pred, 0.78785), 1.42915)
    item_entry["CoolFactor"] = r(pred)

    # Target: Dispersion
    z = -5.34762126316 + (-31.0644621178 * ((DeviationCurve - 1.71153846154) / 0.511842015197)) + (-16.0281618077 * ((DeviationMax - 19) / 8.11456430415)) + (10.8274629036 * ((CenterOfImpact - 0.126153846154) / 0.111993712841))
    pred = z
    pred = min(max(pred, -15.75), 0.75)
    item_entry["Dispersion"] = r(pred)

    # Target: DurabilityBurnModificator
    z = 0.693147908097 + (-1.01016431144e-05 * ((DurabilityBurnModificator - 0.978) / 0.0920882317359))
    pred = expm1_clamped(z)
    pred = min(max(pred, 0.7175), 1.4325)
    item_entry["DurabilityBurnModificator"] = r(pred)

    # Target: Ergonomics
    z = 0.0202813906621 + (0.183559477798 * ((ErgoWeight - 0.358701674193) / 3.24647768255)) + (3.56686421724e-08 * ((Weight - 0.826163636364) / 0.628102860626)) + (-3.28602773706e-08 * ((FactoredWeight - 1.30426065014) / 1.08187980141))
    pred = expm1_clamped(z)
    pred = min(max(pred, -0.25), 5.25)
    item_entry["Ergonomics"] = r(pred)

    # Target: Flash
    z = -1.41503751721 + (60.4864813823 * ((Recoil - -6.5) / 4.06761042204)) + (4.22609466402 * ((CenterOfImpact - 0.117545454545) / 0.093541788072)) + (52.6422226652 * ((CoolFactor - 1.01236363636) / 0.100953880314)) + (-34.2522640098 * ((HeatFactor - 0.95) / 0.117354939471)) + (-63.0886550736 * ((Ergonomics - -7.59090909091) / 4.81861061557))
    pred = z
    pred = min(max(pred, -64.5), 34.5)
    item_entry["Flash"] = r(pred)

    # Target: HeatFactor
    z = 0.969981818243 + (0.097945716162 * ((HeatFactor - 0.969981818182) / 0.0979457161176))
    pred = z
    pred = min(max(pred, 0.76095), 1.15805)
    item_entry["HeatFactor"] = r(pred)

    # Target: HorizontalRecoil
    z = -0
    pred = z
    pred = min(max(pred, -18.45), 13.45)
    item_entry["HorizontalRecoil"] = r(pred)

    # Target: Loudness
    z = 0
    pred = z
    pred = min(max(pred, -64.5), 34.5)
    item_entry["Loudness"] = r(pred)

    # Target: MalfChance
    z = 0
    pred = z
    pred = min(max(pred, -1e-06), 1e-06)
    item_entry["MalfChance"] = r(pred)

    # Target: ModMalfunctionChance
    z = 0
    pred = z
    pred = min(max(pred, -22.85), 105.85)
    item_entry["ModMalfunctionChance"] = r(pred)

    # Target: SemiROF
    z = 0.0354545454545
    pred = z
    pred = min(max(pred, -4.45), 5.45)
    item_entry["SemiROF"] = int(round(pred))

    # Target: ShotgunDispersion
    z = 1.01293939394
    pred = z
    pred = min(max(pred, 0.911645454545), 1.11423333333)
    item_entry["ShotgunDispersion"] = r(pred)

    # Target: Velocity
    z = -3.33427592202 + (3.53345586466 * ((Velocity - -0.100484848485) / 8.31680109002))
    pred = z
    pred = min(max(pred, -39.335), 12.035)
    item_entry["Velocity"] = r(pred)

    # Target: VerticalRecoil
    z = -0
    pred = z
    pred = min(max(pred, -21), 1)
    item_entry["VerticalRecoil"] = r(pred)

    # Target: Weight
    z = 0.548647510721 + (1.81919587071 * ((Weight - 0.826163636364) / 0.628102860626)) + (-1.50887605267 * ((FactoredWeight - 1.30426065014) / 1.08187980141)) + (3.33258891508e-05 * ((ErgoWeight - 0.358701674193) / 3.24647768255))
    pred = expm1_clamped(z)
    pred = min(max(pred, -0.0635), 2.6535)
    item_entry["Weight"] = r(pred)

    return item_entry

# --- Bipods (Mod) Formulas ---
def apply_bipods_mod_formulas(item_entry: dict, base_data: dict, template: dict = None, context: dict = None) -> dict:
    """Auto-generated formulas for parent class: Bipods (Mod)"""
    # Helper functions
    def to_f(x, d=0.0):
        try: return float(x)
        except: return d
    def r(x, d=3):
        try: return round(float(x), d)
        except: return x
    def expm1_clamped(z, cap=20.0):
        z = min(max(z, -cap), cap)
        return math.expm1(z)
    props = base_data.get("_props", base_data)

    # 1. Bind base features from props
    Accuracy = to_f(props.get("Accuracy", base_data.get("Accuracy", 0.0)))
    BipodCameraSnapMultiplier = to_f(props.get("BipodCameraSnapMultiplier", base_data.get("BipodCameraSnapMultiplier", 0.0)))
    BipodOutOfStaminaBreathMultiplier = to_f(props.get("BipodOutOfStaminaBreathMultiplier", base_data.get("BipodOutOfStaminaBreathMultiplier", 0.0)))
    BipodRecoilMultiplier = to_f(props.get("BipodRecoilMultiplier", base_data.get("BipodRecoilMultiplier", 0.0)))
    BipodReturnHandSpeedMultiplier = to_f(props.get("BipodReturnHandSpeedMultiplier", base_data.get("BipodReturnHandSpeedMultiplier", 0.0)))
    Durability = to_f(props.get("Durability", base_data.get("Durability", 0.0)))
    EffectiveDistance = to_f(props.get("EffectiveDistance", base_data.get("EffectiveDistance", 0.0)))
    Ergonomics = to_f(props.get("Ergonomics", base_data.get("Ergonomics", 0.0)))
    Loudness = to_f(props.get("Loudness", base_data.get("Loudness", 0.0)))
    Recoil = to_f(props.get("Recoil", base_data.get("Recoil", 0.0)))
    RecoilForceBack = to_f(props.get("RecoilForceBack", base_data.get("RecoilForceBack", 0.0)))
    RecoilForceUp = to_f(props.get("RecoilForceUp", base_data.get("RecoilForceUp", 0.0)))
    SightingRange = to_f(props.get("SightingRange", base_data.get("SightingRange", 0.0)))
    Velocity = to_f(props.get("Velocity", base_data.get("Velocity", 0.0)))
    Weight = to_f(props.get("Weight", base_data.get("Weight", 0.0)))

    # 2. Engineer new features
    name_str = str(base_data.get('Name', '') or base_data.get('shortName', '')).lower()
    mm_match = re.search(r'(\d+)mm', name_str)
    inch_match = re.search(r'(\d+\.?\d*)"', name_str)
    BarrelLengthMM = float(mm_match.group(1)) if mm_match else (float(inch_match.group(1)) * 25.4 if inch_match else 0.0)
    caliber_match = re.search(r'(\d+\.?\d*)x', name_str)
    CaliberNumeric = float(caliber_match.group(1)) if caliber_match else 0.0
    position_mult = 0.0
    if 'suppressor' in name_str or 'muzzle' in name_str or 'barrel' in name_str: position_mult = -1.0
    elif 'stock' in name_str or 'buttpad' in name_str: position_mult = 1.0
    Torque = Weight * position_mult * 10.0
    FactoredWeight = pow(Weight * 1.5, 1.1) if Weight > 0 else 0.0
    base_ergo_calc_val = Ergonomics / (Weight * 100) if Weight > 0 else 0.0
    ErgoWeight = pow(max(0, base_ergo_calc_val), 0.35) * 100.0
    VRecoilPerErgo = RecoilForceUp / Ergonomics if Ergonomics != 0 else 0.0
    HRecoilPerErgo = RecoilForceBack / Ergonomics if Ergonomics != 0 else 0.0
    dura = to_f(props.get('MaxDurability', base_data.get('MaxDurability', 100.0)))
    dura_factor = 2.0 - (dura / 100.0) if dura > 0 else 2.0
    DurabilityMalfRisk = pow(max(0, dura_factor), 3.0)

    # 3. Calculate all target values

    # Target: Accuracy
    z = -3.34498245492e-10
    pred = z*z if z >= 0 else 0.0
    pred = min(max(pred, -1), 21)
    item_entry["Accuracy"] = r(pred)

    # Target: AimSpeed
    z = 0
    pred = z
    pred = min(max(pred, -1e-06), 1e-06)
    item_entry["AimSpeed"] = r(pred)

    # Target: AutoROF
    z = 0
    pred = z
    pred = min(max(pred, -1e-06), 1e-06)
    item_entry["AutoROF"] = int(round(pred))

    # Target: Ergonomics
    z = 0
    pred = z
    pred = min(max(pred, -1e-06), 1e-06)
    item_entry["Ergonomics"] = r(pred)

    # Target: FixSpeed
    z = 0
    pred = z
    pred = min(max(pred, -1e-06), 1e-06)
    item_entry["FixSpeed"] = r(pred)

    # Target: HorizontalRecoil
    z = 0
    pred = z
    pred = min(max(pred, -1e-06), 1e-06)
    item_entry["HorizontalRecoil"] = r(pred)

    # Target: MalfChance
    z = 0
    pred = z
    pred = min(max(pred, -1e-06), 1e-06)
    item_entry["MalfChance"] = r(pred)

    # Target: ModMalfunctionChance
    z = 0
    pred = z
    pred = min(max(pred, -1e-06), 1e-06)
    item_entry["ModMalfunctionChance"] = r(pred)

    # Target: ReloadSpeed
    z = 0
    pred = z
    pred = min(max(pred, -1e-06), 1e-06)
    item_entry["ReloadSpeed"] = r(pred)

    # Target: SemiROF
    z = 0
    pred = z
    pred = min(max(pred, -1e-06), 1e-06)
    item_entry["SemiROF"] = int(round(pred))

    # Target: VerticalRecoil
    z = 0
    pred = z
    pred = min(max(pred, -1e-06), 1e-06)
    item_entry["VerticalRecoil"] = r(pred)

    # Target: Weight
    z = 0.392714285714 + (0.109971053705 * ((Weight - 0.392714285714) / 0.109971053705))
    pred = z
    pred = min(max(pred, 0.21045), 0.55255)
    item_entry["Weight"] = r(pred)

    return item_entry

# --- ChargingHandle (Mod) Formulas ---
def apply_charginghandle_mod_formulas(item_entry: dict, base_data: dict, template: dict = None, context: dict = None) -> dict:
    """Auto-generated formulas for parent class: ChargingHandle (Mod)"""
    # Helper functions
    def to_f(x, d=0.0):
        try: return float(x)
        except: return d
    def r(x, d=3):
        try: return round(float(x), d)
        except: return x
    def expm1_clamped(z, cap=20.0):
        z = min(max(z, -cap), cap)
        return math.expm1(z)
    props = base_data.get("_props", base_data)

    # 1. Bind base features from props
    Accuracy = to_f(props.get("Accuracy", base_data.get("Accuracy", 0.0)))
    Durability = to_f(props.get("Durability", base_data.get("Durability", 0.0)))
    DurabilityBurnModificator = to_f(props.get("DurabilityBurnModificator", base_data.get("DurabilityBurnModificator", 0.0)))
    EffectiveDistance = to_f(props.get("EffectiveDistance", base_data.get("EffectiveDistance", 0.0)))
    Ergonomics = to_f(props.get("Ergonomics", base_data.get("Ergonomics", 0.0)))
    Loudness = to_f(props.get("Loudness", base_data.get("Loudness", 0.0)))
    Recoil = to_f(props.get("Recoil", base_data.get("Recoil", 0.0)))
    RecoilForceBack = to_f(props.get("RecoilForceBack", base_data.get("RecoilForceBack", 0.0)))
    RecoilForceUp = to_f(props.get("RecoilForceUp", base_data.get("RecoilForceUp", 0.0)))
    SightingRange = to_f(props.get("SightingRange", base_data.get("SightingRange", 0.0)))
    Velocity = to_f(props.get("Velocity", base_data.get("Velocity", 0.0)))
    Weight = to_f(props.get("Weight", base_data.get("Weight", 0.0)))

    # 2. Engineer new features
    name_str = str(base_data.get('Name', '') or base_data.get('shortName', '')).lower()
    mm_match = re.search(r'(\d+)mm', name_str)
    inch_match = re.search(r'(\d+\.?\d*)"', name_str)
    BarrelLengthMM = float(mm_match.group(1)) if mm_match else (float(inch_match.group(1)) * 25.4 if inch_match else 0.0)
    caliber_match = re.search(r'(\d+\.?\d*)x', name_str)
    CaliberNumeric = float(caliber_match.group(1)) if caliber_match else 0.0
    position_mult = 0.0
    if 'suppressor' in name_str or 'muzzle' in name_str or 'barrel' in name_str: position_mult = -1.0
    elif 'stock' in name_str or 'buttpad' in name_str: position_mult = 1.0
    Torque = Weight * position_mult * 10.0
    FactoredWeight = pow(Weight * 1.5, 1.1) if Weight > 0 else 0.0
    base_ergo_calc_val = Ergonomics / (Weight * 100) if Weight > 0 else 0.0
    ErgoWeight = pow(max(0, base_ergo_calc_val), 0.35) * 100.0
    VRecoilPerErgo = RecoilForceUp / Ergonomics if Ergonomics != 0 else 0.0
    HRecoilPerErgo = RecoilForceBack / Ergonomics if Ergonomics != 0 else 0.0
    dura = to_f(props.get('MaxDurability', base_data.get('MaxDurability', 100.0)))
    dura_factor = 2.0 - (dura / 100.0) if dura > 0 else 2.0
    DurabilityMalfRisk = pow(max(0, dura_factor), 3.0)

    # 3. Calculate all target values

    # Target: CameraRecoil
    z = 0
    pred = z
    pred = min(max(pred, -1e-06), 1e-06)
    item_entry["CameraRecoil"] = r(pred)

    # Target: ChamberSpeed
    z = 21.1237247411 + (1.32603812742 * ((Ergonomics - 1.2) / 1.10754984839)) + (6.54416498777 * ((ErgoWeight - 57.3872840552) / 45.7469830593)) + (-273.895719278 * ((FactoredWeight - 0.0428009745796) / 0.0327262909978)) + (274.280056865 * ((Weight - 0.0373) / 0.0253550126536))
    pred = z
    pred = min(max(pred, -7.15), 40.15)
    item_entry["ChamberSpeed"] = r(pred)

    # Target: Ergonomics
    z = 0
    pred = z
    pred = min(max(pred, -1e-06), 1e-06)
    item_entry["Ergonomics"] = r(pred)

    # Target: FixSpeed
    z = 0
    pred = z
    pred = min(max(pred, -1e-06), 1e-06)
    item_entry["FixSpeed"] = r(pred)

    # Target: Flash
    z = -19 + (-3.07852194036 * ((Ergonomics - 1.42857142857) / 1.04978131834)) + (801.612633945 * ((Weight - 0.0337142857143) / 0.00465109159889)) + (-797.540241742 * ((FactoredWeight - 0.037561186349) / 0.0057191354428)) + (5.72426354707 * ((ErgoWeight - 59.5690499003) / 39.1441903592))
    pred = z
    pred = min(max(pred, -31), -9)
    item_entry["Flash"] = r(pred)

    # Target: HorizontalRecoil
    z = 0
    pred = z
    pred = min(max(pred, -1e-06), 1e-06)
    item_entry["HorizontalRecoil"] = r(pred)

    # Target: ReloadSpeed
    z = 0
    pred = z
    pred = min(max(pred, -1e-06), 1e-06)
    item_entry["ReloadSpeed"] = r(pred)

    # Target: VerticalRecoil
    z = 0
    pred = z
    pred = min(max(pred, -1e-06), 1e-06)
    item_entry["VerticalRecoil"] = r(pred)

    # Target: Weight
    z = 0.0506129028332 + (0.0770658392952 * ((Weight - 0.0506129032258) / 0.0770658191332)) + (-2.30156458744e-08 * ((FactoredWeight - 0.0623552734466) / 0.111837290446)) + (-2.65111854994e-10 * ((ErgoWeight - 55.5360813438) / 46.1311799414))
    pred = z
    pred = min(max(pred, -0.01095), 0.47195)
    item_entry["Weight"] = r(pred)

    return item_entry

# --- CombTactDevice (Mod) Formulas ---
def apply_combtactdevice_mod_formulas(item_entry: dict, base_data: dict, template: dict = None, context: dict = None) -> dict:
    """Auto-generated formulas for parent class: CombTactDevice (Mod)"""
    # Helper functions
    def to_f(x, d=0.0):
        try: return float(x)
        except: return d
    def r(x, d=3):
        try: return round(float(x), d)
        except: return x
    def expm1_clamped(z, cap=20.0):
        z = min(max(z, -cap), cap)
        return math.expm1(z)
    props = base_data.get("_props", base_data)

    # 1. Bind base features from props
    Ergonomics = to_f(props.get("Ergonomics", base_data.get("Ergonomics", 0.0)))
    Recoil = to_f(props.get("Recoil", base_data.get("Recoil", 0.0)))
    RecoilForceBack = to_f(props.get("RecoilForceBack", base_data.get("RecoilForceBack", 0.0)))
    RecoilForceUp = to_f(props.get("RecoilForceUp", base_data.get("RecoilForceUp", 0.0)))
    Velocity = to_f(props.get("Velocity", base_data.get("Velocity", 0.0)))
    Weight = to_f(props.get("Weight", base_data.get("Weight", 0.0)))

    # 2. Engineer new features
    name_str = str(base_data.get('Name', '') or base_data.get('shortName', '')).lower()
    mm_match = re.search(r'(\d+)mm', name_str)
    inch_match = re.search(r'(\d+\.?\d*)"', name_str)
    BarrelLengthMM = float(mm_match.group(1)) if mm_match else (float(inch_match.group(1)) * 25.4 if inch_match else 0.0)
    FactoredWeight = pow(Weight * 1.5, 1.1) if Weight > 0 else 0.0
    base_ergo_calc_val = Ergonomics / (Weight * 100) if Weight > 0 else 0.0
    ErgoWeight = pow(max(0, base_ergo_calc_val), 0.35) * 100.0
    VRecoilPerErgo = RecoilForceUp / Ergonomics if Ergonomics != 0 else 0.0
    HRecoilPerErgo = RecoilForceBack / Ergonomics if Ergonomics != 0 else 0.0

    # 3. Calculate all target values

    # Target: Ergonomics
    z = 0
    pred = z
    pred = min(max(pred, -1e-06), 1e-06)
    item_entry["Ergonomics"] = r(pred)

    # Target: HorizontalRecoil
    z = 0
    pred = z
    pred = min(max(pred, -1e-06), 1e-06)
    item_entry["HorizontalRecoil"] = r(pred)

    # Target: VerticalRecoil
    z = 0
    pred = z
    pred = min(max(pred, -1e-06), 1e-06)
    item_entry["VerticalRecoil"] = r(pred)

    # Target: Weight
    z = 0.410048142573 + (-0.553064609678 * ((FactoredWeight - 0.227198005199) / 0.110653241122)) + (0.654305633936 * ((Weight - 0.1715) / 0.0770451166525))
    pred = z*z if z >= 0 else 0.0
    pred = min(max(pred, 0.02775), 0.40725)
    item_entry["Weight"] = r(pred)

    return item_entry

# --- Foregrip (Mod) Formulas ---
def apply_foregrip_mod_formulas(item_entry: dict, base_data: dict, template: dict = None, context: dict = None) -> dict:
    """Auto-generated formulas for parent class: Foregrip (Mod)"""
    # Helper functions
    def to_f(x, d=0.0):
        try: return float(x)
        except: return d
    def r(x, d=3):
        try: return round(float(x), d)
        except: return x
    def expm1_clamped(z, cap=20.0):
        z = min(max(z, -cap), cap)
        return math.expm1(z)
    props = base_data.get("_props", base_data)

    # 1. Bind base features from props
    Accuracy = to_f(props.get("Accuracy", base_data.get("Accuracy", 0.0)))
    Durability = to_f(props.get("Durability", base_data.get("Durability", 0.0)))
    EffectiveDistance = to_f(props.get("EffectiveDistance", base_data.get("EffectiveDistance", 0.0)))
    Ergonomics = to_f(props.get("Ergonomics", base_data.get("Ergonomics", 0.0)))
    Loudness = to_f(props.get("Loudness", base_data.get("Loudness", 0.0)))
    Recoil = to_f(props.get("Recoil", base_data.get("Recoil", 0.0)))
    RecoilForceBack = to_f(props.get("RecoilForceBack", base_data.get("RecoilForceBack", 0.0)))
    RecoilForceUp = to_f(props.get("RecoilForceUp", base_data.get("RecoilForceUp", 0.0)))
    SightingRange = to_f(props.get("SightingRange", base_data.get("SightingRange", 0.0)))
    Velocity = to_f(props.get("Velocity", base_data.get("Velocity", 0.0)))
    Weight = to_f(props.get("Weight", base_data.get("Weight", 0.0)))

    # 2. Engineer new features
    name_str = str(base_data.get('Name', '') or base_data.get('shortName', '')).lower()
    mm_match = re.search(r'(\d+)mm', name_str)
    inch_match = re.search(r'(\d+\.?\d*)"', name_str)
    BarrelLengthMM = float(mm_match.group(1)) if mm_match else (float(inch_match.group(1)) * 25.4 if inch_match else 0.0)
    caliber_match = re.search(r'(\d+\.?\d*)x', name_str)
    CaliberNumeric = float(caliber_match.group(1)) if caliber_match else 0.0
    position_mult = 0.0
    if 'suppressor' in name_str or 'muzzle' in name_str or 'barrel' in name_str: position_mult = -1.0
    elif 'stock' in name_str or 'buttpad' in name_str: position_mult = 1.0
    Torque = Weight * position_mult * 10.0
    FactoredWeight = pow(Weight * 1.5, 1.1) if Weight > 0 else 0.0
    base_ergo_calc_val = Ergonomics / (Weight * 100) if Weight > 0 else 0.0
    ErgoWeight = pow(max(0, base_ergo_calc_val), 0.35) * 100.0
    VRecoilPerErgo = RecoilForceUp / Ergonomics if Ergonomics != 0 else 0.0
    HRecoilPerErgo = RecoilForceBack / Ergonomics if Ergonomics != 0 else 0.0
    dura = to_f(props.get('MaxDurability', base_data.get('MaxDurability', 100.0)))
    dura_factor = 2.0 - (dura / 100.0) if dura > 0 else 2.0
    DurabilityMalfRisk = pow(max(0, dura_factor), 3.0)

    # 3. Calculate all target values

    # Target: Accuracy
    z = 0
    pred = z
    pred = min(max(pred, -1e-06), 1e-06)
    item_entry["Accuracy"] = r(pred)

    # Target: AimSpeed
    z = -0
    pred = z
    pred = min(max(pred, -21), 1)
    item_entry["AimSpeed"] = r(pred)

    # Target: AimStability
    z = 6.66013228039 + (-78.0141378645 * ((FactoredWeight - 0.109863282472) / 0.0545988320003)) + (76.6548306147 * ((Weight - 0.088652173913) / 0.0400690802356)) + (2.67514639108 * ((ErgoWeight - 88.4705816046) / 25.2052277141)) + (1.15807403927 * ((Ergonomics - 5.41304347826) / 2.67090675823)) + (-2.48024754462 * ((Recoil - -1.61956521739) / 0.745892976709))
    pred = z
    pred = min(max(pred, -21.75), 16.75)
    item_entry["AimStability"] = r(pred)

    # Target: Dispersion
    z = -0.936363636364
    pred = z
    pred = min(max(pred, -4.8), 12.8)
    item_entry["Dispersion"] = r(pred)

    # Target: Ergonomics
    z = 2.46210713637 + (0.179028437291 * ((Ergonomics - 5.29090909091) / 2.60190648475)) + (0.206118705199 * ((ErgoWeight - 86.93819457) / 24.8308378583)) + (0.152532090476 * ((FactoredWeight - 0.109627184881) / 0.0512788715938))
    pred = z*z if z >= 0 else 0.0
    pred = min(max(pred, 1.65), 9.35)
    item_entry["Ergonomics"] = r(pred)

    # Target: Handling
    z = 2.60584255649 + (45.7243472688 * ((FactoredWeight - 0.116698428904) / 0.0536017239701)) + (-46.7064415363 * ((Weight - 0.0937727272727) / 0.0392213205218)) + (0.184132930674 * ((Recoil - -1.44318181818) / 0.948778575393)) + (1.83836208639 * ((Ergonomics - 4.90909090909) / 2.71626566697)) + (-2.93596407798 * ((ErgoWeight - 83.065844649) / 25.3762857297))
    pred = z*z if z >= 0 else 0.0
    pred = min(max(pred, 2.425), 26.075)
    item_entry["Handling"] = r(pred)

    # Target: HorizontalRecoil
    z = -1.97125883493 + (-10.4062181879 * ((FactoredWeight - 0.109627184881) / 0.0512788715938)) + (10.2173286274 * ((Weight - 0.0885818181818) / 0.037628176536)) + (0.165628433206 * ((Recoil - -1.5) / 0.879049072992))
    pred = z
    pred = min(max(pred, -16.8), 0.8)
    item_entry["HorizontalRecoil"] = r(pred)

    # Target: VerticalRecoil
    z = -2.12154936335 + (0.433628646137 * ((Ergonomics - 5.29090909091) / 2.60190648475)) + (-0.357696234856 * ((ErgoWeight - 86.93819457) / 24.8308378583)) + (-0.476549384778 * ((FactoredWeight - 0.109627184881) / 0.0512788715938))
    pred = z
    pred = min(max(pred, -4.725), 0.225)
    item_entry["VerticalRecoil"] = r(pred)

    # Target: Weight
    z = 0.29001977336 + (0.445061908804 * ((Weight - 0.0885818181818) / 0.037628176536)) + (-0.385612592587 * ((FactoredWeight - 0.109627184881) / 0.0512788715938)) + (-0.000353073060935 * ((ErgoWeight - 86.93819457) / 24.8308378583))
    pred = z*z if z >= 0 else 0.0
    pred = min(max(pred, 0.02015), 0.19285)
    item_entry["Weight"] = r(pred)

    return item_entry

# --- Gasblock (Mod) Formulas ---
def apply_gasblock_mod_formulas(item_entry: dict, base_data: dict, template: dict = None, context: dict = None) -> dict:
    """Auto-generated formulas for parent class: Gasblock (Mod)"""
    # Helper functions
    def to_f(x, d=0.0):
        try: return float(x)
        except: return d
    def r(x, d=3):
        try: return round(float(x), d)
        except: return x
    def expm1_clamped(z, cap=20.0):
        z = min(max(z, -cap), cap)
        return math.expm1(z)
    props = base_data.get("_props", base_data)

    # 1. Bind base features from props
    Accuracy = to_f(props.get("Accuracy", base_data.get("Accuracy", 0.0)))
    CoolFactor = to_f(props.get("CoolFactor", base_data.get("CoolFactor", 0.0)))
    Durability = to_f(props.get("Durability", base_data.get("Durability", 0.0)))
    DurabilityBurnModificator = to_f(props.get("DurabilityBurnModificator", base_data.get("DurabilityBurnModificator", 0.0)))
    EffectiveDistance = to_f(props.get("EffectiveDistance", base_data.get("EffectiveDistance", 0.0)))
    Ergonomics = to_f(props.get("Ergonomics", base_data.get("Ergonomics", 0.0)))
    HeatFactor = to_f(props.get("HeatFactor", base_data.get("HeatFactor", 0.0)))
    Loudness = to_f(props.get("Loudness", base_data.get("Loudness", 0.0)))
    Recoil = to_f(props.get("Recoil", base_data.get("Recoil", 0.0)))
    RecoilForceBack = to_f(props.get("RecoilForceBack", base_data.get("RecoilForceBack", 0.0)))
    RecoilForceUp = to_f(props.get("RecoilForceUp", base_data.get("RecoilForceUp", 0.0)))
    SightingRange = to_f(props.get("SightingRange", base_data.get("SightingRange", 0.0)))
    Velocity = to_f(props.get("Velocity", base_data.get("Velocity", 0.0)))
    Weight = to_f(props.get("Weight", base_data.get("Weight", 0.0)))

    # 2. Engineer new features
    name_str = str(base_data.get('Name', '') or base_data.get('shortName', '')).lower()
    mm_match = re.search(r'(\d+)mm', name_str)
    inch_match = re.search(r'(\d+\.?\d*)"', name_str)
    BarrelLengthMM = float(mm_match.group(1)) if mm_match else (float(inch_match.group(1)) * 25.4 if inch_match else 0.0)
    caliber_match = re.search(r'(\d+\.?\d*)x', name_str)
    CaliberNumeric = float(caliber_match.group(1)) if caliber_match else 0.0
    position_mult = 0.0
    if 'suppressor' in name_str or 'muzzle' in name_str or 'barrel' in name_str: position_mult = -1.0
    elif 'stock' in name_str or 'buttpad' in name_str: position_mult = 1.0
    Torque = Weight * position_mult * 10.0
    FactoredWeight = pow(Weight * 1.5, 1.1) if Weight > 0 else 0.0
    base_ergo_calc_val = Ergonomics / (Weight * 100) if Weight > 0 else 0.0
    ErgoWeight = pow(max(0, base_ergo_calc_val), 0.35) * 100.0
    VRecoilPerErgo = RecoilForceUp / Ergonomics if Ergonomics != 0 else 0.0
    HRecoilPerErgo = RecoilForceBack / Ergonomics if Ergonomics != 0 else 0.0
    dura = to_f(props.get('MaxDurability', base_data.get('MaxDurability', 100.0)))
    dura_factor = 2.0 - (dura / 100.0) if dura > 0 else 2.0
    DurabilityMalfRisk = pow(max(0, dura_factor), 3.0)

    # 3. Calculate all target values

    # Target: Accuracy
    z = -2.52033623994e-08
    pred = z
    pred = min(max(pred, -14.55), 19.55)
    item_entry["Accuracy"] = r(pred)

    # Target: AutoROF
    z = -0.193548387097
    pred = z
    pred = min(max(pred, -5.4), 3.4)
    item_entry["AutoROF"] = int(round(pred))

    # Target: CameraRecoil
    z = -4.96744240295 + (4.86707517903 * ((Recoil - -2.83333333333) / 0.687184270936)) + (-7.49855809411 * ((Ergonomics - -0.5) / 1.11803398875)) + (9.66376072094 * ((ErgoWeight - 18.5944009298) / 26.2964539792))
    pred = z
    pred = min(max(pred, -10.85), 7.85)
    item_entry["CameraRecoil"] = r(pred)

    # Target: CanCycleSubs
    z = 0
    pred = z
    pred = min(max(pred, -1e-06), 1e-06)
    item_entry["CanCycleSubs"] = r(pred)

    # Target: Convergence
    z = -4.27098014127 + (7.45532576053 * ((Recoil - -2.83333333333) / 0.687184270936)) + (4.34545965941 * ((Ergonomics - -0.5) / 1.11803398875)) + (6.07146710047 * ((FactoredWeight - 0.110946842139) / 0.0836619183688))
    pred = z
    pred = min(max(pred, -10.9), 8.9)
    item_entry["Convergence"] = r(pred)

    # Target: CoolFactor
    z = 1.01112903408 + (0.0183034345929 * ((CoolFactor - 1.01112903226) / 0.0183034316111))
    pred = z
    pred = min(max(pred, 0.9791), 1.0869)
    item_entry["CoolFactor"] = r(pred)

    # Target: Dispersion
    z = -2.8368231402e-10
    pred = z
    pred = min(max(pred, -3.25), 2.25)
    item_entry["Dispersion"] = r(pred)

    # Target: DurabilityBurnModificator
    z = 0.997419355003 + (0.00841187407285 * ((DurabilityBurnModificator - 0.997419354839) / 0.00841187407123))
    pred = z
    pred = min(max(pred, 0.78625), 1.08875)
    item_entry["DurabilityBurnModificator"] = r(pred)

    # Target: Ergonomics
    z = 0.533569820929 + (0.780263966598 * ((Ergonomics - 1.45161290323) / 4.24141417133)) + (5.45657886139 * ((FactoredWeight - 0.195501387928) / 0.186251833456)) + (-4.93752806137 * ((Weight - 0.147096774194) / 0.124790755147))
    pred = z*z if z >= 0 else 0.0
    pred = min(max(pred, -0.7), 14.7)
    item_entry["Ergonomics"] = r(pred)

    # Target: Flash
    z = -15.9967434363 + (1.05253797982 * ((HeatFactor - 0.979529411765) / 0.0216906530346)) + (-60.1522997262 * ((Weight - 0.173529411765) / 0.162282294945)) + (-0.278331829193 * ((CoolFactor - 1.01764705882) / 0.0221145179263)) + (57.1168757322 * ((FactoredWeight - 0.236937632315) / 0.241963522677)) + (4.71406675336 * ((ErgoWeight - 21.332854858) / 29.1735451592))
    pred = z
    pred = min(max(pred, -26.75), 11.75)
    item_entry["Flash"] = r(pred)

    # Target: HeatFactor
    z = 0.987322580213 + (0.0193146906278 * ((HeatFactor - 0.987322580645) / 0.0193146895406))
    pred = z
    pred = min(max(pred, 0.8875), 1.1625)
    item_entry["HeatFactor"] = r(pred)

    # Target: HorizontalRecoil
    z = -0.103578025194 + (0.0809843081051 * ((Recoil - -1.56451612903) / 1.64974062225)) + (-0.416414223362 * ((Ergonomics - 1.45161290323) / 4.24141417133)) + (0.217093404312 * ((ErgoWeight - 14.2295787863) / 26.6905704936))
    pred = z
    pred = min(max(pred, -10.75), 5.75)
    item_entry["HorizontalRecoil"] = r(pred)

    # Target: MalfChance
    z = 0
    pred = z
    pred = min(max(pred, -1e-06), 1e-06)
    item_entry["MalfChance"] = r(pred)

    # Target: ModMalfunctionChance
    z = 0
    pred = z
    pred = min(max(pred, -20.5), 100.5)
    item_entry["ModMalfunctionChance"] = r(pred)

    # Target: SemiROF
    z = -0.112903225806
    pred = z
    pred = min(max(pred, -6.55), 5.55)
    item_entry["SemiROF"] = int(round(pred))

    # Target: VerticalRecoil
    z = -0.338609632408 + (-1.00811200549 * ((Ergonomics - 1.45161290323) / 4.24141417133)) + (0.10974484388 * ((ErgoWeight - 14.2295787863) / 26.6905704936)) + (0.0763508917334 * ((Weight - 0.147096774194) / 0.124790755147))
    pred = z
    pred = min(max(pred, -3.15), 0.15)
    item_entry["VerticalRecoil"] = r(pred)

    # Target: Weight
    z = 0.147096779726 + (0.124790708739 * ((Weight - 0.147096774194) / 0.124790755147)) + (4.16864601933e-08 * ((FactoredWeight - 0.195501387928) / 0.186251833456)) + (-7.01072759989e-09 * ((ErgoWeight - 14.2295787863) / 26.6905704936))
    pred = z
    pred = min(max(pred, 0.004), 0.576)
    item_entry["Weight"] = r(pred)

    return item_entry

# --- GearComponents (Mod) Formulas ---
def apply_gearcomponents_mod_formulas(item_entry: dict, base_data: dict, template: dict = None, context: dict = None) -> dict:
    """Auto-generated formulas for parent class: GearComponents (Mod)"""
    # Helper functions
    def to_f(x, d=0.0):
        try: return float(x)
        except: return d
    def r(x, d=3):
        try: return round(float(x), d)
        except: return x
    def expm1_clamped(z, cap=20.0):
        z = min(max(z, -cap), cap)
        return math.expm1(z)
    props = base_data.get("_props", base_data)

    # 1. Bind base features from props
    BlindnessProtection = to_f(props.get("BlindnessProtection", base_data.get("BlindnessProtection", 0.0)))
    BluntThroughput = to_f(props.get("BluntThroughput", base_data.get("BluntThroughput", 0.0)))
    Durability = to_f(props.get("Durability", base_data.get("Durability", 0.0)))
    Ergonomics = to_f(props.get("Ergonomics", base_data.get("Ergonomics", 0.0)))
    RecoilForceBack = to_f(props.get("RecoilForceBack", base_data.get("RecoilForceBack", 0.0)))
    RecoilForceUp = to_f(props.get("RecoilForceUp", base_data.get("RecoilForceUp", 0.0)))
    Weight = to_f(props.get("Weight", base_data.get("Weight", 0.0)))
    mousePenalty = to_f(props.get("mousePenalty", base_data.get("mousePenalty", 0.0)))
    speedPenaltyPercent = to_f(props.get("speedPenaltyPercent", base_data.get("speedPenaltyPercent", 0.0)))
    weaponErgonomicPenalty = to_f(props.get("weaponErgonomicPenalty", base_data.get("weaponErgonomicPenalty", 0.0)))

    # 2. Engineer new features
    name_str = str(base_data.get('Name', '') or base_data.get('shortName', '')).lower()
    mm_match = re.search(r'(\d+)mm', name_str)
    inch_match = re.search(r'(\d+\.?\d*)"', name_str)
    BarrelLengthMM = float(mm_match.group(1)) if mm_match else (float(inch_match.group(1)) * 25.4 if inch_match else 0.0)
    caliber_match = re.search(r'(\d+\.?\d*)x', name_str)
    CaliberNumeric = float(caliber_match.group(1)) if caliber_match else 0.0
    position_mult = 0.0
    if 'suppressor' in name_str or 'muzzle' in name_str or 'barrel' in name_str: position_mult = -1.0
    elif 'stock' in name_str or 'buttpad' in name_str: position_mult = 1.0
    Torque = Weight * position_mult * 10.0
    FactoredWeight = pow(Weight * 1.5, 1.1) if Weight > 0 else 0.0
    base_ergo_calc_val = Ergonomics / (Weight * 100) if Weight > 0 else 0.0
    ErgoWeight = pow(max(0, base_ergo_calc_val), 0.35) * 100.0
    VRecoilPerErgo = RecoilForceUp / Ergonomics if Ergonomics != 0 else 0.0
    HRecoilPerErgo = RecoilForceBack / Ergonomics if Ergonomics != 0 else 0.0
    dura = to_f(props.get('MaxDurability', base_data.get('MaxDurability', 100.0)))
    dura_factor = 2.0 - (dura / 100.0) if dura > 0 else 2.0
    DurabilityMalfRisk = pow(max(0, dura_factor), 3.0)

    # 3. Calculate all target values

    # Target: Comfort
    z = 1
    pred = z
    pred = min(max(pred, 0.999999), 1.000001)
    item_entry["Comfort"] = r(pred)

    # Target: ReloadSpeedMulti
    z = 1
    pred = z
    pred = min(max(pred, 0.999999), 1.000001)
    item_entry["ReloadSpeedMulti"] = r(pred)

    return item_entry

# --- Handguard (Mod) Formulas ---
def apply_handguard_mod_formulas(item_entry: dict, base_data: dict, template: dict = None, context: dict = None) -> dict:
    """Auto-generated formulas for parent class: Handguard (Mod)"""
    # Helper functions
    def to_f(x, d=0.0):
        try: return float(x)
        except: return d
    def r(x, d=3):
        try: return round(float(x), d)
        except: return x
    def expm1_clamped(z, cap=20.0):
        z = min(max(z, -cap), cap)
        return math.expm1(z)
    props = base_data.get("_props", base_data)

    # 1. Bind base features from props
    Accuracy = to_f(props.get("Accuracy", base_data.get("Accuracy", 0.0)))
    CoolFactor = to_f(props.get("CoolFactor", base_data.get("CoolFactor", 0.0)))
    Durability = to_f(props.get("Durability", base_data.get("Durability", 0.0)))
    EffectiveDistance = to_f(props.get("EffectiveDistance", base_data.get("EffectiveDistance", 0.0)))
    Ergonomics = to_f(props.get("Ergonomics", base_data.get("Ergonomics", 0.0)))
    HeatFactor = to_f(props.get("HeatFactor", base_data.get("HeatFactor", 0.0)))
    Loudness = to_f(props.get("Loudness", base_data.get("Loudness", 0.0)))
    Recoil = to_f(props.get("Recoil", base_data.get("Recoil", 0.0)))
    RecoilForceBack = to_f(props.get("RecoilForceBack", base_data.get("RecoilForceBack", 0.0)))
    RecoilForceUp = to_f(props.get("RecoilForceUp", base_data.get("RecoilForceUp", 0.0)))
    SightingRange = to_f(props.get("SightingRange", base_data.get("SightingRange", 0.0)))
    Velocity = to_f(props.get("Velocity", base_data.get("Velocity", 0.0)))
    Weight = to_f(props.get("Weight", base_data.get("Weight", 0.0)))

    # 2. Engineer new features
    name_str = str(base_data.get('Name', '') or base_data.get('shortName', '')).lower()
    mm_match = re.search(r'(\d+)mm', name_str)
    inch_match = re.search(r'(\d+\.?\d*)"', name_str)
    BarrelLengthMM = float(mm_match.group(1)) if mm_match else (float(inch_match.group(1)) * 25.4 if inch_match else 0.0)
    caliber_match = re.search(r'(\d+\.?\d*)x', name_str)
    CaliberNumeric = float(caliber_match.group(1)) if caliber_match else 0.0
    position_mult = 0.0
    if 'suppressor' in name_str or 'muzzle' in name_str or 'barrel' in name_str: position_mult = -1.0
    elif 'stock' in name_str or 'buttpad' in name_str: position_mult = 1.0
    Torque = Weight * position_mult * 10.0
    FactoredWeight = pow(Weight * 1.5, 1.1) if Weight > 0 else 0.0
    base_ergo_calc_val = Ergonomics / (Weight * 100) if Weight > 0 else 0.0
    ErgoWeight = pow(max(0, base_ergo_calc_val), 0.35) * 100.0
    VRecoilPerErgo = RecoilForceUp / Ergonomics if Ergonomics != 0 else 0.0
    HRecoilPerErgo = RecoilForceBack / Ergonomics if Ergonomics != 0 else 0.0
    dura = to_f(props.get('MaxDurability', base_data.get('MaxDurability', 100.0)))
    dura_factor = 2.0 - (dura / 100.0) if dura > 0 else 2.0
    DurabilityMalfRisk = pow(max(0, dura_factor), 3.0)

    # 3. Calculate all target values

    # Target: Accuracy
    z = 2.25524475524 + (1.21317982163 * ((Accuracy - 0.0268817204301) / 0.192124391239))
    pred = z
    pred = min(max(pred, -22.25), 27.25)
    item_entry["Accuracy"] = r(pred)

    # Target: AimSpeed
    z = 0
    pred = z
    pred = min(max(pred, -1e-06), 1e-06)
    item_entry["AimSpeed"] = r(pred)

    # Target: AimStability
    z = 1.61612852412 + (-0.0921417712108 * ((Recoil - -1.34536082474) / 1.16291675767)) + (0.127369866343 * ((Ergonomics - 8.96391752577) / 2.96825769184)) + (-0.0284840477837 * ((HeatFactor - 0.995701030928) / 0.0402031349622)) + (-0.00557584010286 * ((ErgoWeight - 67.1363130572) / 14.7863679258)) + (0.0492601933717 * ((Accuracy - 0.020618556701) / 0.142103595382))
    pred = expm1_clamped(z)
    pred = min(max(pred, 0.3), 15.7)
    item_entry["AimStability"] = r(pred)

    # Target: ChamberSpeed
    z = 0
    pred = z
    pred = min(max(pred, -6.35), 23.35)
    item_entry["ChamberSpeed"] = r(pred)

    # Target: CoolFactor
    z = 1.01961742972 + (0.0452879718044 * ((CoolFactor - 1.0196172973) / 0.0452891637089))
    pred = z
    pred = min(max(pred, 0.88775), 1.15725)
    item_entry["CoolFactor"] = r(pred)

    # Target: Dispersion
    z = -0.952797202797 + (-0.066877039123 * ((Accuracy - 0.0268817204301) / 0.192124391239))
    pred = z
    pred = min(max(pred, -10.55), 1.55)
    item_entry["Dispersion"] = r(pred)

    # Target: Ergonomics
    z = 7.24019541661 + (3.45915167303 * ((Ergonomics - 7.44892473118) / 3.27278184338)) + (-1.04505680745 * ((ErgoWeight - 64.4397503992) / 16.0896061551)) + (-0.577640827341 * ((Weight - 0.301290322581) / 0.167391343711))
    pred = z
    pred = min(max(pred, -1.1), 23.1)
    item_entry["Ergonomics"] = r(pred)

    # Target: Handling
    z = 1.38184628082 + (-0.127752677475 * ((Recoil - -1.3152173913) / 1.14615944549)) + (-0.152050254472 * ((CoolFactor - 1.02672826087) / 0.0498606979627)) + (0.0932706036804 * ((Durability - 99.8913043478) / 1.03689043632)) + (-0.101986630927 * ((ErgoWeight - 64.1802006343) / 13.5343070153)) + (-0.0168781888421 * ((Ergonomics - 7.70108695652) / 2.91832644735))
    pred = expm1_clamped(z)
    pred = min(max(pred, 0.3), 15.7)
    item_entry["Handling"] = r(pred)

    # Target: HeatFactor
    z = 1.00174517033 + (0.0386042561063 * ((HeatFactor - 1.00199459459) / 0.0389341088976))
    pred = z
    pred = min(max(pred, 0.89), 1.11)
    item_entry["HeatFactor"] = r(pred)

    # Target: HorizontalRecoil
    z = -1.47181994295 + (-1.69782316906 * ((Weight - 0.301290322581) / 0.167391343711)) + (1.38681686445 * ((FactoredWeight - 0.424212687673) / 0.258800930671)) + (0.123205665234 * ((Recoil - -1.03494623656) / 1.14540420968))
    pred = z
    pred = min(max(pred, -10.55), 1.55)
    item_entry["HorizontalRecoil"] = r(pred)

    # Target: ReloadSpeed
    z = 0
    pred = z
    pred = min(max(pred, -1e-06), 1e-06)
    item_entry["ReloadSpeed"] = r(pred)

    # Target: VerticalRecoil
    z = -1.37462450586 + (-0.419182162902 * ((Ergonomics - 7.44892473118) / 3.27278184338)) + (0.196853534089 * ((Recoil - -1.03494623656) / 1.14540420968)) + (-0.179556923306 * ((Weight - 0.301290322581) / 0.167391343711))
    pred = z
    pred = min(max(pred, -13.1), 11.1)
    item_entry["VerticalRecoil"] = r(pred)

    # Target: Weight
    z = 0.301290322457 + (0.167391340646 * ((Weight - 0.301290322581) / 0.167391343711)) + (2.74710172282e-09 * ((FactoredWeight - 0.424212687673) / 0.258800930671)) + (-4.55664923271e-10 * ((ErgoWeight - 64.4397503992) / 16.0896061551))
    pred = z
    pred = min(max(pred, -0.00985), 0.93285)
    item_entry["Weight"] = r(pred)

    return item_entry

# --- Headset (Mod) Formulas ---
def apply_headset_mod_formulas(item_entry: dict, base_data: dict, template: dict = None, context: dict = None) -> dict:
    """Auto-generated formulas for parent class: Headset (Mod)"""
    # Helper functions
    def to_f(x, d=0.0):
        try: return float(x)
        except: return d
    def r(x, d=3):
        try: return round(float(x), d)
        except: return x
    def expm1_clamped(z, cap=20.0):
        z = min(max(z, -cap), cap)
        return math.expm1(z)
    props = base_data.get("_props", base_data)

    # 1. Bind base features from props
    AmbientCompressorSendLevel = to_f(props.get("AmbientCompressorSendLevel", base_data.get("AmbientCompressorSendLevel", 0.0)))
    AmbientVolume = to_f(props.get("AmbientVolume", base_data.get("AmbientVolume", 0.0)))
    ClientPlayerCompressorSendLevel = to_f(props.get("ClientPlayerCompressorSendLevel", base_data.get("ClientPlayerCompressorSendLevel", 0.0)))
    CompressorAttack = to_f(props.get("CompressorAttack", base_data.get("CompressorAttack", 0.0)))
    CompressorGain = to_f(props.get("CompressorGain", base_data.get("CompressorGain", 0.0)))
    CompressorRelease = to_f(props.get("CompressorRelease", base_data.get("CompressorRelease", 0.0)))
    CompressorThreshold = to_f(props.get("CompressorThreshold", base_data.get("CompressorThreshold", 0.0)))
    Distortion = to_f(props.get("Distortion", base_data.get("Distortion", 0.0)))
    DryVolume = to_f(props.get("DryVolume", base_data.get("DryVolume", 0.0)))
    EQBand1Frequency = to_f(props.get("EQBand1Frequency", base_data.get("EQBand1Frequency", 0.0)))
    EQBand1Gain = to_f(props.get("EQBand1Gain", base_data.get("EQBand1Gain", 0.0)))
    EQBand1Q = to_f(props.get("EQBand1Q", base_data.get("EQBand1Q", 0.0)))
    EQBand2Frequency = to_f(props.get("EQBand2Frequency", base_data.get("EQBand2Frequency", 0.0)))
    EQBand2Gain = to_f(props.get("EQBand2Gain", base_data.get("EQBand2Gain", 0.0)))
    EQBand2Q = to_f(props.get("EQBand2Q", base_data.get("EQBand2Q", 0.0)))
    EQBand3Frequency = to_f(props.get("EQBand3Frequency", base_data.get("EQBand3Frequency", 0.0)))
    EQBand3Gain = to_f(props.get("EQBand3Gain", base_data.get("EQBand3Gain", 0.0)))
    EQBand3Q = to_f(props.get("EQBand3Q", base_data.get("EQBand3Q", 0.0)))
    EffectsReturnsCompressorSendLevel = to_f(props.get("EffectsReturnsCompressorSendLevel", base_data.get("EffectsReturnsCompressorSendLevel", 0.0)))
    EffectsReturnsGroupVolume = to_f(props.get("EffectsReturnsGroupVolume", base_data.get("EffectsReturnsGroupVolume", 0.0)))
    EnvCommonCompressorSendLevel = to_f(props.get("EnvCommonCompressorSendLevel", base_data.get("EnvCommonCompressorSendLevel", 0.0)))
    EnvNatureCompressorSendLevel = to_f(props.get("EnvNatureCompressorSendLevel", base_data.get("EnvNatureCompressorSendLevel", 0.0)))
    EnvTechnicalCompressorSendLevel = to_f(props.get("EnvTechnicalCompressorSendLevel", base_data.get("EnvTechnicalCompressorSendLevel", 0.0)))
    Ergonomics = to_f(props.get("Ergonomics", base_data.get("Ergonomics", 0.0)))
    GunsCompressorSendLevel = to_f(props.get("GunsCompressorSendLevel", base_data.get("GunsCompressorSendLevel", 0.0)))
    HeadphonesMixerVolume = to_f(props.get("HeadphonesMixerVolume", base_data.get("HeadphonesMixerVolume", 0.0)))
    HighpassFreq = to_f(props.get("HighpassFreq", base_data.get("HighpassFreq", 0.0)))
    HighpassResonance = to_f(props.get("HighpassResonance", base_data.get("HighpassResonance", 0.0)))
    LowpassFreq = to_f(props.get("LowpassFreq", base_data.get("LowpassFreq", 0.0)))
    NpcCompressorSendLevel = to_f(props.get("NpcCompressorSendLevel", base_data.get("NpcCompressorSendLevel", 0.0)))
    ObservedPlayerCompressorSendLevel = to_f(props.get("ObservedPlayerCompressorSendLevel", base_data.get("ObservedPlayerCompressorSendLevel", 0.0)))
    RecoilForceBack = to_f(props.get("RecoilForceBack", base_data.get("RecoilForceBack", 0.0)))
    RecoilForceUp = to_f(props.get("RecoilForceUp", base_data.get("RecoilForceUp", 0.0)))
    Weight = to_f(props.get("Weight", base_data.get("Weight", 0.0)))

    # 2. Engineer new features
    name_str = str(base_data.get('Name', '') or base_data.get('shortName', '')).lower()
    mm_match = re.search(r'(\d+)mm', name_str)
    inch_match = re.search(r'(\d+\.?\d*)"', name_str)
    BarrelLengthMM = float(mm_match.group(1)) if mm_match else (float(inch_match.group(1)) * 25.4 if inch_match else 0.0)
    caliber_match = re.search(r'(\d+\.?\d*)x', name_str)
    CaliberNumeric = float(caliber_match.group(1)) if caliber_match else 0.0
    position_mult = 0.0
    if 'suppressor' in name_str or 'muzzle' in name_str or 'barrel' in name_str: position_mult = -1.0
    elif 'stock' in name_str or 'buttpad' in name_str: position_mult = 1.0
    Torque = Weight * position_mult * 10.0
    FactoredWeight = pow(Weight * 1.5, 1.1) if Weight > 0 else 0.0
    base_ergo_calc_val = Ergonomics / (Weight * 100) if Weight > 0 else 0.0
    ErgoWeight = pow(max(0, base_ergo_calc_val), 0.35) * 100.0
    VRecoilPerErgo = RecoilForceUp / Ergonomics if Ergonomics != 0 else 0.0
    HRecoilPerErgo = RecoilForceBack / Ergonomics if Ergonomics != 0 else 0.0
    dura = to_f(props.get('MaxDurability', base_data.get('MaxDurability', 100.0)))
    dura_factor = 2.0 - (dura / 100.0) if dura > 0 else 2.0
    DurabilityMalfRisk = pow(max(0, dura_factor), 3.0)

    # 3. Calculate all target values

    # Target: dB
    z = 21.9330217009 + (-15.3587524663 * ((FactoredWeight - 0.724847087921) / 0.181650410837)) + (14.5133794247 * ((Weight - 0.496285714286) / 0.11326922957)) + (-0.479541590561 * ((EQBand1Gain - 1.17857142857) / 0.0646813224153)) + (-0.084507516573 * ((HeadphonesMixerVolume - -4.85714285714) / 1.6413036133)) + (0.199822059167 * ((EQBand1Q - 1.27857142857) / 0.30978926346)) + (-0.00618849381922 * ((ClientPlayerCompressorSendLevel - -4.67857142857) / 1.47123785172)) + (-0.140844898764 * ((AmbientCompressorSendLevel - -13.6071428571) / 1.50212434606))
    pred = z
    pred = min(max(pred, 18.65), 26.35)
    item_entry["dB"] = r(pred)

    # Target: mousePenalty
    z = 0
    pred = z
    pred = min(max(pred, -1e-06), 1e-06)
    item_entry["mousePenalty"] = r(pred)

    # Target: speedPenaltyPercent
    z = 0
    pred = z
    pred = min(max(pred, -1e-06), 1e-06)
    item_entry["speedPenaltyPercent"] = r(pred)

    # Target: weaponErgonomicPenalty
    z = 0
    pred = z
    pred = min(max(pred, -1e-06), 1e-06)
    item_entry["weaponErgonomicPenalty"] = r(pred)

    return item_entry

# --- Headwear (Mod) Formulas ---
def apply_headwear_mod_formulas(item_entry: dict, base_data: dict, template: dict = None, context: dict = None) -> dict:
    """Auto-generated formulas for parent class: Headwear (Mod)"""
    # Helper functions
    def to_f(x, d=0.0):
        try: return float(x)
        except: return d
    def r(x, d=3):
        try: return round(float(x), d)
        except: return x
    def expm1_clamped(z, cap=20.0):
        z = min(max(z, -cap), cap)
        return math.expm1(z)
    props = base_data.get("_props", base_data)

    # 1. Bind base features from props
    BlindnessProtection = to_f(props.get("BlindnessProtection", base_data.get("BlindnessProtection", 0.0)))
    BluntThroughput = to_f(props.get("BluntThroughput", base_data.get("BluntThroughput", 0.0)))
    Durability = to_f(props.get("Durability", base_data.get("Durability", 0.0)))
    Ergonomics = to_f(props.get("Ergonomics", base_data.get("Ergonomics", 0.0)))
    RecoilForceBack = to_f(props.get("RecoilForceBack", base_data.get("RecoilForceBack", 0.0)))
    RecoilForceUp = to_f(props.get("RecoilForceUp", base_data.get("RecoilForceUp", 0.0)))
    Weight = to_f(props.get("Weight", base_data.get("Weight", 0.0)))
    mousePenalty = to_f(props.get("mousePenalty", base_data.get("mousePenalty", 0.0)))
    speedPenaltyPercent = to_f(props.get("speedPenaltyPercent", base_data.get("speedPenaltyPercent", 0.0)))
    weaponErgonomicPenalty = to_f(props.get("weaponErgonomicPenalty", base_data.get("weaponErgonomicPenalty", 0.0)))

    # 2. Engineer new features
    name_str = str(base_data.get('Name', '') or base_data.get('shortName', '')).lower()
    mm_match = re.search(r'(\d+)mm', name_str)
    inch_match = re.search(r'(\d+\.?\d*)"', name_str)
    BarrelLengthMM = float(mm_match.group(1)) if mm_match else (float(inch_match.group(1)) * 25.4 if inch_match else 0.0)
    caliber_match = re.search(r'(\d+\.?\d*)x', name_str)
    CaliberNumeric = float(caliber_match.group(1)) if caliber_match else 0.0
    position_mult = 0.0
    if 'suppressor' in name_str or 'muzzle' in name_str or 'barrel' in name_str: position_mult = -1.0
    elif 'stock' in name_str or 'buttpad' in name_str: position_mult = 1.0
    Torque = Weight * position_mult * 10.0
    FactoredWeight = pow(Weight * 1.5, 1.1) if Weight > 0 else 0.0
    base_ergo_calc_val = Ergonomics / (Weight * 100) if Weight > 0 else 0.0
    ErgoWeight = pow(max(0, base_ergo_calc_val), 0.35) * 100.0
    VRecoilPerErgo = RecoilForceUp / Ergonomics if Ergonomics != 0 else 0.0
    HRecoilPerErgo = RecoilForceBack / Ergonomics if Ergonomics != 0 else 0.0
    dura = to_f(props.get('MaxDurability', base_data.get('MaxDurability', 100.0)))
    dura_factor = 2.0 - (dura / 100.0) if dura > 0 else 2.0
    DurabilityMalfRisk = pow(max(0, dura_factor), 3.0)

    # 3. Calculate all target values

    # Target: Comfort
    z = 0.989838000086 + (0.154773790758 * ((Weight - 1.70386363636) / 0.929773227261)) + (-0.127794924414 * ((FactoredWeight - 2.85015295458) / 1.71667679305)) + (-0.0108429347162 * ((mousePenalty - -1.43181818182) / 0.889272615751)) + (-0.0103922717699 * ((weaponErgonomicPenalty - -1.45454545455) / 1.05431031861))
    pred = z*z if z >= 0 else 0.0
    pred = min(max(pred, 0.78), 1.22)
    item_entry["Comfort"] = r(pred)

    # Target: Price
    z = 151.595787079 + (64.7646921945 * ((DurabilityMalfRisk - 7.73229545455) / 1.29775636072)) + (35.9961040162 * ((Durability - 4.31818181818) / 23.0017516401))
    pred = z*z if z >= 0 else 0.0
    pred = min(max(pred, -2000), 42000)
    item_entry["Price"] = r(pred)

    # Target: ReloadSpeedMulti
    z = 1
    pred = z
    pred = min(max(pred, 0.999999), 1.000001)
    item_entry["ReloadSpeedMulti"] = r(pred)

    # Target: mousePenalty
    z = 0
    pred = z
    pred = min(max(pred, -1e-06), 1e-06)
    item_entry["mousePenalty"] = r(pred)

    # Target: speedPenaltyPercent
    z = 0
    pred = z
    pred = min(max(pred, -1e-06), 1e-06)
    item_entry["speedPenaltyPercent"] = r(pred)

    # Target: weaponErgonomicPenalty
    z = 0
    pred = z
    pred = min(max(pred, -1e-06), 1e-06)
    item_entry["weaponErgonomicPenalty"] = r(pred)

    return item_entry

# --- Launcher (Gun) Formulas ---
def apply_launcher_gun_formulas(item_entry: dict, base_data: dict, template: dict = None, context: dict = None) -> dict:
    """Auto-generated formulas for parent class: Launcher (Gun)"""
    # Helper functions
    def to_f(x, d=0.0):
        try: return float(x)
        except: return d
    def r(x, d=3):
        try: return round(float(x), d)
        except: return x
    def expm1_clamped(z, cap=20.0):
        z = min(max(z, -cap), cap)
        return math.expm1(z)
    props = base_data.get("_props", base_data)

    # 1. Bind base features from props
    Accuracy = to_f(props.get("Accuracy", base_data.get("Accuracy", 0.0)))
    Durability = to_f(props.get("Durability", base_data.get("Durability", 0.0)))
    EffectiveDistance = to_f(props.get("EffectiveDistance", base_data.get("EffectiveDistance", 0.0)))
    Ergonomics = to_f(props.get("Ergonomics", base_data.get("Ergonomics", 0.0)))
    Loudness = to_f(props.get("Loudness", base_data.get("Loudness", 0.0)))
    Recoil = to_f(props.get("Recoil", base_data.get("Recoil", 0.0)))
    RecoilForceBack = to_f(props.get("RecoilForceBack", base_data.get("RecoilForceBack", 0.0)))
    RecoilForceUp = to_f(props.get("RecoilForceUp", base_data.get("RecoilForceUp", 0.0)))
    SightingRange = to_f(props.get("SightingRange", base_data.get("SightingRange", 0.0)))
    Velocity = to_f(props.get("Velocity", base_data.get("Velocity", 0.0)))
    Weight = to_f(props.get("Weight", base_data.get("Weight", 0.0)))

    # 2. Engineer new features
    name_str = str(base_data.get('Name', '') or base_data.get('shortName', '')).lower()
    mm_match = re.search(r'(\d+)mm', name_str)
    inch_match = re.search(r'(\d+\.?\d*)"', name_str)
    BarrelLengthMM = float(mm_match.group(1)) if mm_match else (float(inch_match.group(1)) * 25.4 if inch_match else 0.0)
    caliber_match = re.search(r'(\d+\.?\d*)x', name_str)
    CaliberNumeric = float(caliber_match.group(1)) if caliber_match else 0.0
    position_mult = 0.0
    if 'suppressor' in name_str or 'muzzle' in name_str or 'barrel' in name_str: position_mult = -1.0
    elif 'stock' in name_str or 'buttpad' in name_str: position_mult = 1.0
    Torque = Weight * position_mult * 10.0
    FactoredWeight = pow(Weight * 1.5, 1.1) if Weight > 0 else 0.0
    base_ergo_calc_val = Ergonomics / (Weight * 100) if Weight > 0 else 0.0
    ErgoWeight = pow(max(0, base_ergo_calc_val), 0.35) * 100.0
    VRecoilPerErgo = RecoilForceUp / Ergonomics if Ergonomics != 0 else 0.0
    HRecoilPerErgo = RecoilForceBack / Ergonomics if Ergonomics != 0 else 0.0
    dura = to_f(props.get('MaxDurability', base_data.get('MaxDurability', 100.0)))
    dura_factor = 2.0 - (dura / 100.0) if dura > 0 else 2.0
    DurabilityMalfRisk = pow(max(0, dura_factor), 3.0)

    # 3. Calculate all target values

    # Target: Accuracy
    z = -15
    pred = z
    pred = min(max(pred, -20.5), -9.5)
    item_entry["Accuracy"] = r(pred)

    # Target: AimSpeed
    z = 0
    pred = z
    pred = min(max(pred, -1e-06), 1e-06)
    item_entry["AimSpeed"] = r(pred)

    # Target: AutoROF
    z = 0
    pred = z
    pred = min(max(pred, -1e-06), 1e-06)
    item_entry["AutoROF"] = int(round(pred))

    # Target: BlocksFolding
    z = 0
    pred = z
    pred = min(max(pred, -1e-06), 1e-06)
    item_entry["BlocksFolding"] = r(pred)

    # Target: CameraRecoil
    z = 0
    pred = z
    pred = min(max(pred, -1e-06), 1e-06)
    item_entry["CameraRecoil"] = r(pred)

    # Target: CoolFactor
    z = 1
    pred = z
    pred = min(max(pred, 0.999999), 1.000001)
    item_entry["CoolFactor"] = r(pred)

    # Target: Dispersion
    z = 0
    pred = z
    pred = min(max(pred, -1e-06), 1e-06)
    item_entry["Dispersion"] = r(pred)

    # Target: Ergonomics
    z = 0
    pred = z
    pred = min(max(pred, -1e-06), 1e-06)
    item_entry["Ergonomics"] = r(pred)

    # Target: HasShoulderContact
    z = 0
    pred = z
    pred = min(max(pred, -1e-06), 1e-06)
    item_entry["HasShoulderContact"] = r(pred)

    # Target: HeatFactor
    z = 1
    pred = z
    pred = min(max(pred, 0.999999), 1.000001)
    item_entry["HeatFactor"] = r(pred)

    # Target: HorizontalRecoil
    z = 0
    pred = z
    pred = min(max(pred, -1e-06), 1e-06)
    item_entry["HorizontalRecoil"] = r(pred)

    # Target: ModMalfunctionChance
    z = 0
    pred = z
    pred = min(max(pred, -1e-06), 1e-06)
    item_entry["ModMalfunctionChance"] = r(pred)

    # Target: SemiROF
    z = 0
    pred = z
    pred = min(max(pred, -1e-06), 1e-06)
    item_entry["SemiROF"] = int(round(pred))

    # Target: StockAllowADS
    z = 0
    pred = z
    pred = min(max(pred, -1e-06), 1e-06)
    item_entry["StockAllowADS"] = r(pred)

    # Target: VerticalRecoil
    z = 0
    pred = z
    pred = min(max(pred, -1e-06), 1e-06)
    item_entry["VerticalRecoil"] = r(pred)

    # Target: Weight
    z = 1.43 + (0.07 * ((Weight - 1.38) / 0.02))
    pred = z
    pred = min(max(pred, 1.353), 1.507)
    item_entry["Weight"] = r(pred)

    return item_entry

# --- Magazines (Mod) Formulas ---
def apply_magazines_mod_formulas(item_entry: dict, base_data: dict, template: dict = None, context: dict = None) -> dict:
    """Auto-generated formulas for parent class: Magazines (Mod)"""
    # Helper functions
    def to_f(x, d=0.0):
        try: return float(x)
        except: return d
    def r(x, d=3):
        try: return round(float(x), d)
        except: return x
    def expm1_clamped(z, cap=20.0):
        z = min(max(z, -cap), cap)
        return math.expm1(z)
    props = base_data.get("_props", base_data)

    # 1. Bind base features from props
    Accuracy = to_f(props.get("Accuracy", base_data.get("Accuracy", 0.0)))
    BeltMagazineRefreshCount = to_f(props.get("BeltMagazineRefreshCount", base_data.get("BeltMagazineRefreshCount", 0.0)))
    CheckTimeModifier = to_f(props.get("CheckTimeModifier", base_data.get("CheckTimeModifier", 0.0)))
    Durability = to_f(props.get("Durability", base_data.get("Durability", 0.0)))
    EffectiveDistance = to_f(props.get("EffectiveDistance", base_data.get("EffectiveDistance", 0.0)))
    Ergonomics = to_f(props.get("Ergonomics", base_data.get("Ergonomics", 0.0)))
    LoadUnloadModifier = to_f(props.get("LoadUnloadModifier", base_data.get("LoadUnloadModifier", 0.0)))
    Loudness = to_f(props.get("Loudness", base_data.get("Loudness", 0.0)))
    MalfunctionChance = to_f(props.get("MalfunctionChance", base_data.get("MalfunctionChance", 0.0)))
    Recoil = to_f(props.get("Recoil", base_data.get("Recoil", 0.0)))
    RecoilForceBack = to_f(props.get("RecoilForceBack", base_data.get("RecoilForceBack", 0.0)))
    RecoilForceUp = to_f(props.get("RecoilForceUp", base_data.get("RecoilForceUp", 0.0)))
    SightingRange = to_f(props.get("SightingRange", base_data.get("SightingRange", 0.0)))
    Velocity = to_f(props.get("Velocity", base_data.get("Velocity", 0.0)))
    Weight = to_f(props.get("Weight", base_data.get("Weight", 0.0)))

    # 2. Engineer new features
    name_str = str(base_data.get('Name', '') or base_data.get('shortName', '')).lower()
    mm_match = re.search(r'(\d+)mm', name_str)
    inch_match = re.search(r'(\d+\.?\d*)"', name_str)
    BarrelLengthMM = float(mm_match.group(1)) if mm_match else (float(inch_match.group(1)) * 25.4 if inch_match else 0.0)
    caliber_match = re.search(r'(\d+\.?\d*)x', name_str)
    CaliberNumeric = float(caliber_match.group(1)) if caliber_match else 0.0
    position_mult = 0.0
    if 'suppressor' in name_str or 'muzzle' in name_str or 'barrel' in name_str: position_mult = -1.0
    elif 'stock' in name_str or 'buttpad' in name_str: position_mult = 1.0
    Torque = Weight * position_mult * 10.0
    FactoredWeight = pow(Weight * 1.5, 1.1) if Weight > 0 else 0.0
    base_ergo_calc_val = Ergonomics / (Weight * 100) if Weight > 0 else 0.0
    ErgoWeight = pow(max(0, base_ergo_calc_val), 0.35) * 100.0
    VRecoilPerErgo = RecoilForceUp / Ergonomics if Ergonomics != 0 else 0.0
    HRecoilPerErgo = RecoilForceBack / Ergonomics if Ergonomics != 0 else 0.0
    dura = to_f(props.get('MaxDurability', base_data.get('MaxDurability', 100.0)))
    dura_factor = 2.0 - (dura / 100.0) if dura > 0 else 2.0
    DurabilityMalfRisk = pow(max(0, dura_factor), 3.0)

    # 3. Calculate all target values

    # Target: CheckTimeModifier
    z = -2.57211538425 + (14.090865534 * ((CheckTimeModifier - -2.57211538462) / 14.0908655404)) + (-8.21252238232e-09 * ((LoadUnloadModifier - -0.144230769231) / 17.1315151948)) + (8.51598069447e-09 * ((Ergonomics - -3.81971153846) / 6.46141996729)) + (9.56201912981e-09 * ((MalfunctionChance - 0.0776153846154) / 0.0834044026338)) + (2.62274878362e-09 * ((Weight - 0.270283653846) / 0.230194673721))
    pred = z
    pred = min(max(pred, -54.25), 39.25)
    item_entry["CheckTimeModifier"] = r(pred)

    # Target: Ergonomics
    z = -0
    pred = z
    pred = min(max(pred, -31.5), 1.5)
    item_entry["Ergonomics"] = r(pred)

    # Target: HorizontalRecoil
    z = 0
    pred = z
    pred = min(max(pred, -1e-06), 1e-06)
    item_entry["HorizontalRecoil"] = r(pred)

    # Target: LoadUnloadModifier
    z = -0.144230769261 + (17.1315151922 * ((LoadUnloadModifier - -0.144230769231) / 17.1315151948)) + (2.2861046799e-09 * ((MalfunctionChance - 0.0776153846154) / 0.0834044026338)) + (-9.84974876188e-10 * ((Ergonomics - -3.81971153846) / 6.46141996729)) + (-4.67684847125e-10 * ((CheckTimeModifier - -2.57211538462) / 14.0908655404)) + (8.00395286285e-10 * ((Weight - 0.270283653846) / 0.230194673721))
    pred = z
    pred = min(max(pred, -36), 96)
    item_entry["LoadUnloadModifier"] = r(pred)

    # Target: MalfunctionChance
    z = 0.250958374712 + (0.184159976313 * ((MalfunctionChance - 0.0776153846154) / 0.0834044026338)) + (-0.102033182172 * ((Ergonomics - -3.81971153846) / 6.46141996729)) + (0.0152763926605 * ((LoadUnloadModifier - -0.144230769231) / 17.1315151948)) + (0.0343007447734 * ((CheckTimeModifier - -2.57211538462) / 14.0908655404)) + (-0.0423091256746 * ((Weight - 0.270283653846) / 0.230194673721))
    pred = z*z if z >= 0 else 0.0
    pred = min(max(pred, -0.5), 10.5)
    item_entry["MalfunctionChance"] = r(pred)

    # Target: ReloadSpeed
    z = -1.64859464173 + (3.91542187936 * ((Ergonomics - -3.81971153846) / 6.46141996729)) + (-7.62618412866 * ((Weight - 0.270283653846) / 0.230194673721)) + (7.31798778826 * ((FactoredWeight - 0.381858641004) / 0.36662498179))
    pred = z
    pred = min(max(pred, -23.4), 7.4)
    item_entry["ReloadSpeed"] = r(pred)

    # Target: VerticalRecoil
    z = 0
    pred = z
    pred = min(max(pred, -1e-06), 1e-06)
    item_entry["VerticalRecoil"] = r(pred)

    # Target: Weight
    z = 0.270283653613 + (0.230194671915 * ((Weight - 0.270283653846) / 0.230194673721)) + (1.91085267801e-09 * ((FactoredWeight - 0.381858641004) / 0.36662498179)) + (-8.15502752524e-11 * ((ErgoWeight - 9.02713616756) / 21.7084061614))
    pred = z
    pred = min(max(pred, -0.06975), 1.57475)
    item_entry["Weight"] = r(pred)

    return item_entry

# --- MarksmanRifles (Gun) Formulas ---
def apply_marksmanrifles_gun_formulas(item_entry: dict, base_data: dict, template: dict = None, context: dict = None) -> dict:
    """Auto-generated formulas for parent class: MarksmanRifles (Gun)"""
    # Helper functions
    def to_f(x, d=0.0):
        try: return float(x)
        except: return d
    def r(x, d=3):
        try: return round(float(x), d)
        except: return x
    def expm1_clamped(z, cap=20.0):
        z = min(max(z, -cap), cap)
        return math.expm1(z)
    props = base_data.get("_props", base_data)

    # 1. Bind base features from props
    AimPlane = to_f(props.get("AimPlane", base_data.get("AimPlane", 0.0)))
    AimSensitivity = to_f(props.get("AimSensitivity", base_data.get("AimSensitivity", 0.0)))
    BaseMalfunctionChance = to_f(props.get("BaseMalfunctionChance", base_data.get("BaseMalfunctionChance", 0.0)))
    CameraSnap = to_f(props.get("CameraSnap", base_data.get("CameraSnap", 0.0)))
    CameraToWeaponAngleStep = to_f(props.get("CameraToWeaponAngleStep", base_data.get("CameraToWeaponAngleStep", 0.0)))
    CenterOfImpact = to_f(props.get("CenterOfImpact", base_data.get("CenterOfImpact", 0.0)))
    CoolFactorGun = to_f(props.get("CoolFactorGun", base_data.get("CoolFactorGun", 0.0)))
    CoolFactorGunMods = to_f(props.get("CoolFactorGunMods", base_data.get("CoolFactorGunMods", 0.0)))
    DeviationCurve = to_f(props.get("DeviationCurve", base_data.get("DeviationCurve", 0.0)))
    DeviationMax = to_f(props.get("DeviationMax", base_data.get("DeviationMax", 0.0)))
    Durability = to_f(props.get("Durability", base_data.get("Durability", 0.0)))
    DurabilityBurnRatio = to_f(props.get("DurabilityBurnRatio", base_data.get("DurabilityBurnRatio", 0.0)))
    Ergonomics = to_f(props.get("Ergonomics", base_data.get("Ergonomics", 0.0)))
    HeatFactorByShot = to_f(props.get("HeatFactorByShot", base_data.get("HeatFactorByShot", 0.0)))
    HeatFactorGun = to_f(props.get("HeatFactorGun", base_data.get("HeatFactorGun", 0.0)))
    HipAccuracyRestorationDelay = to_f(props.get("HipAccuracyRestorationDelay", base_data.get("HipAccuracyRestorationDelay", 0.0)))
    HipAccuracyRestorationSpeed = to_f(props.get("HipAccuracyRestorationSpeed", base_data.get("HipAccuracyRestorationSpeed", 0.0)))
    HipInnaccuracyGain = to_f(props.get("HipInnaccuracyGain", base_data.get("HipInnaccuracyGain", 0.0)))
    IronSightRange = to_f(props.get("IronSightRange", base_data.get("IronSightRange", 0.0)))
    MaxRepairDegradation = to_f(props.get("MaxRepairDegradation", base_data.get("MaxRepairDegradation", 0.0)))
    MinRepairDegradation = to_f(props.get("MinRepairDegradation", base_data.get("MinRepairDegradation", 0.0)))
    RecoilAngle = to_f(props.get("RecoilAngle", base_data.get("RecoilAngle", 0.0)))
    RecoilCamera = to_f(props.get("RecoilCamera", base_data.get("RecoilCamera", 0.0)))
    RecoilCategoryMultiplierHandRotation = to_f(props.get("RecoilCategoryMultiplierHandRotation", base_data.get("RecoilCategoryMultiplierHandRotation", 0.0)))
    RecoilDampingHandRotation = to_f(props.get("RecoilDampingHandRotation", base_data.get("RecoilDampingHandRotation", 0.0)))
    RecoilForceBack = to_f(props.get("RecoilForceBack", base_data.get("RecoilForceBack", 0.0)))
    RecoilForceUp = to_f(props.get("RecoilForceUp", base_data.get("RecoilForceUp", 0.0)))
    RecoilPosZMult = to_f(props.get("RecoilPosZMult", base_data.get("RecoilPosZMult", 0.0)))
    RecoilReturnPathDampingHandRotation = to_f(props.get("RecoilReturnPathDampingHandRotation", base_data.get("RecoilReturnPathDampingHandRotation", 0.0)))
    RecoilReturnPathOffsetHandRotation = to_f(props.get("RecoilReturnPathOffsetHandRotation", base_data.get("RecoilReturnPathOffsetHandRotation", 0.0)))
    RecoilReturnSpeedHandRotation = to_f(props.get("RecoilReturnSpeedHandRotation", base_data.get("RecoilReturnSpeedHandRotation", 0.0)))
    RecolDispersion = to_f(props.get("RecolDispersion", base_data.get("RecolDispersion", 0.0)))
    SightingRange = to_f(props.get("SightingRange", base_data.get("SightingRange", 0.0)))
    SingleFireRate = to_f(props.get("SingleFireRate", base_data.get("SingleFireRate", 0.0)))
    Velocity = to_f(props.get("Velocity", base_data.get("Velocity", 0.0)))
    Weight = to_f(props.get("Weight", base_data.get("Weight", 0.0)))
    bEffDist = to_f(props.get("bEffDist", base_data.get("bEffDist", 0.0)))
    bFirerate = to_f(props.get("bFirerate", base_data.get("bFirerate", 0.0)))
    bHearDist = to_f(props.get("bHearDist", base_data.get("bHearDist", 0.0)))
    shotgunDispersion = to_f(props.get("shotgunDispersion", base_data.get("shotgunDispersion", 0.0)))

    # 2. Engineer new features
    name_str = str(base_data.get('Name', '') or base_data.get('shortName', '')).lower()
    mm_match = re.search(r'(\d+)mm', name_str)
    inch_match = re.search(r'(\d+\.?\d*)"', name_str)
    BarrelLengthMM = float(mm_match.group(1)) if mm_match else (float(inch_match.group(1)) * 25.4 if inch_match else 0.0)
    caliber_match = re.search(r'(\d+\.?\d*)x', name_str)
    CaliberNumeric = float(caliber_match.group(1)) if caliber_match else 0.0
    position_mult = 0.0
    if 'suppressor' in name_str or 'muzzle' in name_str or 'barrel' in name_str: position_mult = -1.0
    elif 'stock' in name_str or 'buttpad' in name_str: position_mult = 1.0
    Torque = Weight * position_mult * 10.0
    FactoredWeight = pow(Weight * 1.5, 1.1) if Weight > 0 else 0.0
    base_ergo_calc_val = Ergonomics / (Weight * 100) if Weight > 0 else 0.0
    ErgoWeight = pow(max(0, base_ergo_calc_val), 0.35) * 100.0
    VRecoilPerErgo = RecoilForceUp / Ergonomics if Ergonomics != 0 else 0.0
    HRecoilPerErgo = RecoilForceBack / Ergonomics if Ergonomics != 0 else 0.0
    dura = to_f(props.get('MaxDurability', base_data.get('MaxDurability', 100.0)))
    dura_factor = 2.0 - (dura / 100.0) if dura > 0 else 2.0
    DurabilityMalfRisk = pow(max(0, dura_factor), 3.0)

    # 3. Calculate all target values

    # Target: AllowOverheat
    z = 1
    pred = z
    pred = min(max(pred, 0.999999), 1.000001)
    item_entry["AllowOverheat"] = r(pred)

    # Target: AutoROF
    z = 641.25 + (240.126919565 * ((bFirerate - 641.25) / 240.126919565))
    pred = z
    pred = min(max(pred, -13.5), 943.5)
    item_entry["AutoROF"] = int(round(pred))

    # Target: BaseChamberCheckSpeed
    z = 1.15251657837 + (4.18897363046 * ((HRecoilPerErgo - 18.5167803726) / 21.2703088241)) + (8.13932812255 * ((RecoilForceUp - 206) / 131.012403993)) + (-12.7050644196 * ((VRecoilPerErgo - 8.57245014912) / 11.4443834241)) + (-0.933707897292 * ((RecoilForceBack - 470.875) / 234.749034876)) + (-0.510459743921 * ((HeatFactorByShot - 2.54875) / 0.680008042232)) + (3.24451753342 * ((bFirerate - 641.25) / 240.126919565)) + (5.35324771504 * ((bHearDist - 90) / 26.4575131106))
    pred = z*z if z >= 0 else 0.0
    pred = min(max(pred, 0.7425), 3.1075)
    item_entry["BaseChamberCheckSpeed"] = r(pred)

    # Target: BaseChamberSpeedMulti
    z = 0.695775601459 + (-0.0597420385953 * ((Ergonomics - 38) / 12.5996031684)) + (0.0946466872427 * ((RecoilForceBack - 470.875) / 234.749034876)) + (0.0180818089818 * ((MaxRepairDegradation - 0.0375) / 0.00661437827766)) + (0.0476224172283 * ((RecoilReturnSpeedHandRotation - 2.6125) / 0.301817411691)) + (-0.102649455823 * ((HRecoilPerErgo - 18.5167803726) / 21.2703088241)) + (0.0169126961924 * ((HeatFactorByShot - 2.54875) / 0.680008042232)) + (0.0173689513178 * ((ErgoWeight - 67.0329379602) / 20.3876118186))
    pred = expm1_clamped(z)
    pred = min(max(pred, 0.8875), 1.1625)
    item_entry["BaseChamberSpeedMulti"] = r(pred)

    # Target: BaseFixSpeed
    z = 1.34375 + (5.50161385929 * ((HRecoilPerErgo - 18.5167803726) / 21.2703088241)) + (-15.81780571 * ((VRecoilPerErgo - 8.57245014912) / 11.4443834241)) + (10.3524841747 * ((RecoilForceUp - 206) / 131.012403993)) + (-1.17950732918 * ((RecoilForceBack - 470.875) / 234.749034876)) + (-0.56416230094 * ((HeatFactorByShot - 2.54875) / 0.680008042232)) + (6.71956880477 * ((bHearDist - 90) / 26.4575131106)) + (4.28493605325 * ((bFirerate - 641.25) / 240.126919565))
    pred = z
    pred = min(max(pred, 0.7425), 3.1075)
    item_entry["BaseFixSpeed"] = r(pred)

    # Target: BaseMalfunctionChance
    z = 0.00191725461871 + (0.0115147331625 * ((Weight - 1.478) / 0.740848162581)) + (-0.0113536844043 * ((FactoredWeight - 2.43497289467) / 1.32416559039)) + (-0.000135497808668 * ((ErgoWeight - 67.0329379602) / 20.3876118186)) + (-6.64566123653e-05 * ((RecoilReturnPathDampingHandRotation - 0.41) / 0.0264575131106)) + (6.64566123653e-05 * ((RecoilCategoryMultiplierHandRotation - 0.227125) / 0.00760653501931)) + (6.64566123653e-05 * ((DeviationMax - 29.125) / 2.31503239718)) + (-6.64566123653e-05 * ((RecolDispersion - 11.125) / 0.330718913883))
    pred = z
    pred = min(max(pred, 0.0009), 0.0031)
    item_entry["BaseMalfunctionChance"] = r(pred)

    # Target: BaseReloadSpeedMulti
    z = 0.709021980895 + (-0.0457550341056 * ((Ergonomics - 38) / 12.5996031684)) + (0.990171205294 * ((FactoredWeight - 2.43497289467) / 1.32416559039)) + (-0.958220972988 * ((Weight - 1.478) / 0.740848162581))
    pred = expm1_clamped(z)
    pred = min(max(pred, 0.8175), 1.5325)
    item_entry["BaseReloadSpeedMulti"] = r(pred)

    # Target: BaseTorque
    z = 0.564831272137 + (0.555202312442 * ((bEffDist - 812.5) / 169.096865731)) + (-0.273474202563 * ((CenterOfImpact - 0.014375) / 0.0311686440995)) + (-0.240189338439 * ((AimPlane - 0.3375) / 0.257572805242)) + (0.0580873943063 * ((RecoilReturnPathDampingHandRotation - 0.41) / 0.0264575131106)) + (-0.0580873943063 * ((RecoilCategoryMultiplierHandRotation - 0.227125) / 0.00760653501931)) + (0.0580873943063 * ((DeviationCurve - 1.13125) / 0.0826797284708)) + (0.0580873943063 * ((RecolDispersion - 11.125) / 0.330718913883))
    pred = z
    pred = min(max(pred, -1.875), 6.375)
    item_entry["BaseTorque"] = r(pred)

    # Target: CameraRecoil
    z = 0.0780158075272 + (-0.0577032375127 * ((RecoilForceUp - 206) / 131.012403993)) + (0.0855955269842 * ((VRecoilPerErgo - 8.57245014912) / 11.4443834241)) + (-0.0201016003941 * ((HRecoilPerErgo - 18.5167803726) / 21.2703088241)) + (0.0210206826246 * ((RecoilCamera - 0.0825) / 0.0178535710714)) + (0.0132631514807 * ((RecoilDampingHandRotation - 0.85875) / 0.0105326872165))
    pred = z
    pred = min(max(pred, 0.0259), 0.1821)
    item_entry["CameraRecoil"] = r(pred)

    # Target: CenterOfImpact
    z = 0
    pred = z
    pred = min(max(pred, -0.002), 0.042)
    item_entry["CenterOfImpact"] = r(pred)

    # Target: Convergence
    z = 9.74858981544 + (-0.709036873209 * ((FactoredWeight - 2.43497289467) / 1.32416559039)) + (-0.534878099537 * ((Weight - 1.478) / 0.740848162581)) + (-2.32824520318 * ((VRecoilPerErgo - 8.57245014912) / 11.4443834241)) + (0.566567502158 * ((RecoilForceUp - 206) / 131.012403993)) + (0.411528812028 * ((HRecoilPerErgo - 18.5167803726) / 21.2703088241))
    pred = z
    pred = min(max(pred, 3.2625), 13.9875)
    item_entry["Convergence"] = r(pred)

    # Target: CoolFactorGun
    z = 0.100000000806 + (3.89270172059e-10 * ((CoolFactorGunMods - 1.0239375) / 0.0261249372009))
    pred = z
    pred = min(max(pred, 0.0765), 0.1535)
    item_entry["CoolFactorGun"] = r(pred)

    # Target: CoolFactorGunMods
    z = 1
    pred = z
    pred = min(max(pred, 0.999999), 1.000001)
    item_entry["CoolFactorGunMods"] = r(pred)

    # Target: Dispersion
    z = 10.6249998619 + (5.97600548246 * ((bEffDist - 812.5) / 169.096865731)) + (-4.56909520025 * ((CenterOfImpact - 0.014375) / 0.0311686440995)) + (12.8786380208 * ((AimPlane - 0.3375) / 0.257572805242)) + (-2.77913900426 * ((DeviationCurve - 1.13125) / 0.0826797284708))
    pred = z
    pred = min(max(pred, 7.8), 12.2)
    item_entry["Dispersion"] = r(pred)

    # Target: DurabilityBurnRatio
    z = 0.672637466697
    pred = z*z if z >= 0 else 0.0
    pred = min(max(pred, 0.1825), 0.5675)
    item_entry["DurabilityBurnRatio"] = r(pred)

    # Target: Ergonomics
    z = 8.94427191547 + (7.70927255065e-09 * ((Ergonomics - 38) / 12.5996031684)) + (4.13570237347e-08 * ((Weight - 1.478) / 0.740848162581)) + (-3.42361987308e-08 * ((FactoredWeight - 2.43497289467) / 1.32416559039))
    pred = z*z if z >= 0 else 0.0
    pred = min(max(pred, 79.85), 83.15)
    item_entry["Ergonomics"] = r(pred)

    # Target: HasShoulderContact
    z = 0.125 + (0.984916005188 * ((RecoilReturnSpeedHandRotation - 2.6125) / 0.301817411691)) + (-0.0207019874107 * ((RecoilDampingHandRotation - 0.85875) / 0.0105326872165)) + (-0.859433422811 * ((Ergonomics - 38) / 12.5996031684)) + (-0.13498785994 * ((RecoilForceBack - 470.875) / 234.749034876)) + (-7.29204219484 * ((Weight - 1.478) / 0.740848162581)) + (-0.158973118285 * ((HeatFactorByShot - 2.54875) / 0.680008042232)) + (7.61959894412 * ((FactoredWeight - 2.43497289467) / 1.32416559039))
    pred = z
    pred = min(max(pred, -0.05), 1.05)
    item_entry["HasShoulderContact"] = r(pred)

    # Target: HeatFactorByShot
    z = 1
    pred = z
    pred = min(max(pred, 0.999999), 1.000001)
    item_entry["HeatFactorByShot"] = r(pred)

    # Target: HeatFactorGun
    z = 0.442496422 + (0.102755549468 * ((HeatFactorByShot - 2.54875) / 0.680008042232)) + (-0.0533060169615 * ((HeatFactorGun - 0.9924125) / 0.0514571286971))
    pred = expm1_clamped(z)
    pred = min(max(pred, 0.265), 1.035)
    item_entry["HeatFactorGun"] = r(pred)

    # Target: HipAccuracyRestorationDelay
    z = 0.2
    pred = z
    pred = min(max(pred, 0.199999), 0.200001)
    item_entry["HipAccuracyRestorationDelay"] = r(pred)

    # Target: HipAccuracyRestorationSpeed
    z = 2.64575131106
    pred = z*z if z >= 0 else 0.0
    pred = min(max(pred, 6.999999), 7.000001)
    item_entry["HipAccuracyRestorationSpeed"] = r(pred)

    # Target: HipInnaccuracyGain
    z = 0.148420005118
    pred = expm1_clamped(z)
    pred = min(max(pred, 0.159999), 0.160001)
    item_entry["HipInnaccuracyGain"] = r(pred)

    # Target: HorizontalRecoil
    z = 14.8928424639 + (4.38544226595 * ((RecoilDampingHandRotation - 0.85875) / 0.0105326872165)) + (3.9497133842 * ((RecoilCamera - 0.0825) / 0.0178535710714)) + (-20.0567315077 * ((RecoilForceUp - 206) / 131.012403993)) + (18.5586722333 * ((VRecoilPerErgo - 8.57245014912) / 11.4443834241)) + (-3.65436391731 * ((HRecoilPerErgo - 18.5167803726) / 21.2703088241))
    pred = z*z if z >= 0 else 0.0
    pred = min(max(pred, 94.5), 435.5)
    item_entry["HorizontalRecoil"] = r(pred)

    # Target: MaxChamberSpeed
    z = 0.934843232514 + (0.0487008254685 * ((CoolFactorGunMods - 1.0239375) / 0.0261249372009)) + (-0.213293061693 * ((Ergonomics - 38) / 12.5996031684)) + (-0.0304376257726 * ((HeatFactorGun - 0.9924125) / 0.0514571286971)) + (0.0748221791728 * ((RecoilForceBack - 470.875) / 234.749034876)) + (0.08238236621 * ((ErgoWeight - 67.0329379602) / 20.3876118186)) + (0.194266336351 * ((RecoilReturnSpeedHandRotation - 2.6125) / 0.301817411691)) + (0.0503761334521 * ((AimPlane - 0.3375) / 0.257572805242))
    pred = expm1_clamped(z)
    pred = min(max(pred, 1.48), 1.92)
    item_entry["MaxChamberSpeed"] = r(pred)

    # Target: MinChamberSpeed
    z = 0.7 + (-0.201098836134 * ((CoolFactorGunMods - 1.0239375) / 0.0261249372009)) + (2.83654787202 * ((ErgoWeight - 67.0329379602) / 20.3876118186)) + (31.5496826008 * ((Weight - 1.478) / 0.740848162581)) + (-29.5874154804 * ((FactoredWeight - 2.43497289467) / 1.32416559039)) + (-0.295949140484 * ((HeatFactorGun - 0.9924125) / 0.0514571286971)) + (0.360724634813 * ((MaxRepairDegradation - 0.0375) / 0.00661437827766)) + (-0.916079059608 * ((RecoilReturnSpeedHandRotation - 2.6125) / 0.301817411691))
    pred = z
    pred = min(max(pred, 0.5925), 0.7575)
    item_entry["MinChamberSpeed"] = r(pred)

    # Target: MinReloadSpeed
    z = 0.75 + (-0.1 * ((Ergonomics - 21) / 7))
    pred = z
    pred = min(max(pred, 0.64), 0.86)
    item_entry["MinReloadSpeed"] = r(pred)

    # Target: OffsetRotation
    z = 0.0962501634283 + (-0.00198467789096 * ((RecoilReturnPathDampingHandRotation - 0.41) / 0.0264575131106)) + (0.00198467789096 * ((RecoilCategoryMultiplierHandRotation - 0.227125) / 0.00760653501931)) + (0.00198467789096 * ((DeviationMax - 29.125) / 2.31503239718)) + (-0.00198467789096 * ((DeviationCurve - 1.13125) / 0.0826797284708)) + (-0.00198467789096 * ((RecolDispersion - 11.125) / 0.330718913883)) + (2.12957226226e-05 * ((CenterOfImpact - 0.014375) / 0.0311686440995)) + (-1.96116600644e-05 * ((AimPlane - 0.3375) / 0.257572805242))
    pred = z*z if z >= 0 else 0.0
    pred = min(max(pred, 0.004645), 0.010255)
    item_entry["OffsetRotation"] = r(pred)

    # Target: RecoilAngle
    z = 88.3221894794 + (-18.0150602682 * ((Weight - 1.478) / 0.740848162581)) + (12.9041522947 * ((FactoredWeight - 2.43497289467) / 1.32416559039)) + (-3.17593051785 * ((ErgoWeight - 67.0329379602) / 20.3876118186)) + (0.938480517773 * ((DeviationMax - 29.125) / 2.31503239718)) + (-0.938480517773 * ((DeviationCurve - 1.13125) / 0.0826797284708))
    pred = z
    pred = min(max(pred, 79.35), 93.65)
    item_entry["RecoilAngle"] = r(pred)

    # Target: RecoilDamping
    z = 0.845178843928 + (-0.0807234891276 * ((ErgoWeight - 67.0329379602) / 20.3876118186)) + (-1.07009952537 * ((Weight - 1.478) / 0.740848162581)) + (1.04622477276 * ((FactoredWeight - 2.43497289467) / 1.32416559039)) + (0.0125031842368 * ((Ergonomics - 38) / 12.5996031684)) + (-0.028655209072 * ((HRecoilPerErgo - 18.5167803726) / 21.2703088241))
    pred = z
    pred = min(max(pred, 0.796), 0.884)
    item_entry["RecoilDamping"] = r(pred)

    # Target: RecoilHandDamping
    z = 0.443753551056 + (-0.0289397365803 * ((DeviationMax - 29.125) / 2.31503239718)) + (0.0289397365803 * ((DeviationCurve - 1.13125) / 0.0826797284708)) + (-0.0289397365803 * ((RecoilCategoryMultiplierHandRotation - 0.227125) / 0.00760653501931)) + (0.0289397365803 * ((RecoilReturnPathDampingHandRotation - 0.41) / 0.0264575131106)) + (-9.34779447293e-06 * ((CenterOfImpact - 0.014375) / 0.0311686440995))
    pred = z
    pred = min(max(pred, 0.3825), 0.7675)
    item_entry["RecoilHandDamping"] = r(pred)

    # Target: RecoilIntensity
    z = 0.219124999686 + (-0.00719313623735 * ((RecoilReturnPathDampingHandRotation - 0.41) / 0.0264575131106)) + (0.00719313623735 * ((DeviationMax - 29.125) / 2.31503239718)) + (0.00719313623735 * ((RecoilCategoryMultiplierHandRotation - 0.227125) / 0.00760653501931)) + (-0.00719313623735 * ((DeviationCurve - 1.13125) / 0.0826797284708)) + (-3.19442670223e-10 * ((CenterOfImpact - 0.014375) / 0.0311686440995))
    pred = z
    pred = min(max(pred, 0.13865), 0.23435)
    item_entry["RecoilIntensity"] = r(pred)

    # Target: SemiROF
    z = 378.125 + (3.91394580708 * ((bFirerate - 641.25) / 240.126919565))
    pred = z
    pred = min(max(pred, 341.25), 423.75)
    item_entry["SemiROF"] = int(round(pred))

    # Target: ShotgunDispersion
    z = 0
    pred = z
    pred = min(max(pred, -1e-06), 1e-06)
    item_entry["ShotgunDispersion"] = r(pred)

    # Target: Velocity
    z = 0
    pred = z
    pred = min(max(pred, -1e-06), 1e-06)
    item_entry["Velocity"] = r(pred)

    # Target: VerticalRecoil
    z = 111.953368773 + (8.17575166609 * ((RecoilDampingHandRotation - 0.85875) / 0.0105326872165)) + (7.14071035725 * ((RecoilCamera - 0.0825) / 0.0178535710714)) + (20.9599160075 * ((RecoilForceUp - 206) / 131.012403993)) + (13.7851846024 * ((VRecoilPerErgo - 8.57245014912) / 11.4443834241)) + (-20.5832776749 * ((HRecoilPerErgo - 18.5167803726) / 21.2703088241))
    pred = z
    pred = min(max(pred, 62.4), 185.6)
    item_entry["VerticalRecoil"] = r(pred)

    # Target: VisualMulti
    z = 0.755196092788 + (0.281206751324 * ((bEffDist - 812.5) / 169.096865731)) + (0.500422952392 * ((AimPlane - 0.3375) / 0.257572805242)) + (-0.1632612871 * ((CenterOfImpact - 0.014375) / 0.0311686440995)) + (0.0157980565072 * ((BaseMalfunctionChance - 0.208725) / 0.013039321541)) + (-0.0224100965588 * ((RecolDispersion - 11.125) / 0.330718913883)) + (-0.0224100965588 * ((RecoilReturnPathDampingHandRotation - 0.41) / 0.0264575131106)) + (-0.0224100965588 * ((DeviationCurve - 1.13125) / 0.0826797284708))
    pred = expm1_clamped(z)
    pred = min(max(pred, 0.9875), 1.2625)
    item_entry["VisualMulti"] = r(pred)

    # Target: WeapAccuracy
    z = 0
    pred = z
    pred = min(max(pred, -1e-06), 1e-06)
    item_entry["WeapAccuracy"] = r(pred)

    # Target: WeaponAllowADS
    z = 0
    pred = z
    pred = min(max(pred, -1e-06), 1e-06)
    item_entry["WeaponAllowADS"] = r(pred)

    # Target: Weight
    z = 0.821745181586 + (-3.10966784854 * ((FactoredWeight - 2.43497289467) / 1.32416559039)) + (3.48175138451 * ((Weight - 1.478) / 0.740848162581)) + (0.11858603147 * ((ErgoWeight - 67.0329379602) / 20.3876118186))
    pred = expm1_clamped(z)
    pred = min(max(pred, 0.4195), 2.4105)
    item_entry["Weight"] = r(pred)

    return item_entry

# --- Mounts (Mod) Formulas ---
def apply_mounts_mod_formulas(item_entry: dict, base_data: dict, template: dict = None, context: dict = None) -> dict:
    """Auto-generated formulas for parent class: Mounts (Mod)"""
    # Helper functions
    def to_f(x, d=0.0):
        try: return float(x)
        except: return d
    def r(x, d=3):
        try: return round(float(x), d)
        except: return x
    def expm1_clamped(z, cap=20.0):
        z = min(max(z, -cap), cap)
        return math.expm1(z)
    props = base_data.get("_props", base_data)

    # 1. Bind base features from props
    Accuracy = to_f(props.get("Accuracy", base_data.get("Accuracy", 0.0)))
    CoolFactor = to_f(props.get("CoolFactor", base_data.get("CoolFactor", 0.0)))
    Durability = to_f(props.get("Durability", base_data.get("Durability", 0.0)))
    EffectiveDistance = to_f(props.get("EffectiveDistance", base_data.get("EffectiveDistance", 0.0)))
    Ergonomics = to_f(props.get("Ergonomics", base_data.get("Ergonomics", 0.0)))
    HeatFactor = to_f(props.get("HeatFactor", base_data.get("HeatFactor", 0.0)))
    Loudness = to_f(props.get("Loudness", base_data.get("Loudness", 0.0)))
    Recoil = to_f(props.get("Recoil", base_data.get("Recoil", 0.0)))
    RecoilForceBack = to_f(props.get("RecoilForceBack", base_data.get("RecoilForceBack", 0.0)))
    RecoilForceUp = to_f(props.get("RecoilForceUp", base_data.get("RecoilForceUp", 0.0)))
    SightingRange = to_f(props.get("SightingRange", base_data.get("SightingRange", 0.0)))
    Velocity = to_f(props.get("Velocity", base_data.get("Velocity", 0.0)))
    Weight = to_f(props.get("Weight", base_data.get("Weight", 0.0)))

    # 2. Engineer new features
    name_str = str(base_data.get('Name', '') or base_data.get('shortName', '')).lower()
    mm_match = re.search(r'(\d+)mm', name_str)
    inch_match = re.search(r'(\d+\.?\d*)"', name_str)
    BarrelLengthMM = float(mm_match.group(1)) if mm_match else (float(inch_match.group(1)) * 25.4 if inch_match else 0.0)
    caliber_match = re.search(r'(\d+\.?\d*)x', name_str)
    CaliberNumeric = float(caliber_match.group(1)) if caliber_match else 0.0
    position_mult = 0.0
    if 'suppressor' in name_str or 'muzzle' in name_str or 'barrel' in name_str: position_mult = -1.0
    elif 'stock' in name_str or 'buttpad' in name_str: position_mult = 1.0
    Torque = Weight * position_mult * 10.0
    FactoredWeight = pow(Weight * 1.5, 1.1) if Weight > 0 else 0.0
    base_ergo_calc_val = Ergonomics / (Weight * 100) if Weight > 0 else 0.0
    ErgoWeight = pow(max(0, base_ergo_calc_val), 0.35) * 100.0
    VRecoilPerErgo = RecoilForceUp / Ergonomics if Ergonomics != 0 else 0.0
    HRecoilPerErgo = RecoilForceBack / Ergonomics if Ergonomics != 0 else 0.0
    dura = to_f(props.get('MaxDurability', base_data.get('MaxDurability', 100.0)))
    dura_factor = 2.0 - (dura / 100.0) if dura > 0 else 2.0
    DurabilityMalfRisk = pow(max(0, dura_factor), 3.0)

    # 3. Calculate all target values

    # Target: Accuracy
    z = 8.93027320476e-10
    pred = z
    pred = min(max(pred, -22.8), 16.8)
    item_entry["Accuracy"] = r(pred)

    # Target: AimSpeed
    z = -2.5 + (2.20218584894 * ((Weight - 0.233) / 0.0926093947718)) + (2.0991367997 * ((FactoredWeight - 0.317412249507) / 0.137313719789)) + (1.84153004267 * ((Recoil - -6.25) / 6.49519052838))
    pred = z
    pred = min(max(pred, -5.25), 0.25)
    item_entry["AimSpeed"] = r(pred)

    # Target: AimStability
    z = 1.43767605673 + (-0.742633211062 * ((HeatFactor - 0.964909090909) / 0.0336545405432)) + (-0.699687246593 * ((FactoredWeight - 0.146990382021) / 0.109498897351)) + (0.449624294448 * ((Weight - 0.113454545455) / 0.0799481236762)) + (-0.030239784791 * ((CoolFactor - 1.00854545455) / 0.0116958705717)) + (0.244802216828 * ((Recoil - -0.363636363636) / 0.481045692921))
    pred = expm1_clamped(z)
    pred = min(max(pred, 1.7), 8.3)
    item_entry["AimStability"] = r(pred)

    # Target: CoolFactor
    z = 1.01576598368 + (-0.0129082450107 * ((CoolFactor - 1.0024) / 0.0048))
    pred = z*z if z >= 0 else 0.0
    pred = min(max(pred, 0.976), 1.064)
    item_entry["CoolFactor"] = r(pred)

    # Target: Dispersion
    z = -1.5
    pred = z
    pred = min(max(pred, -3.675), 0.175)
    item_entry["Dispersion"] = r(pred)

    # Target: Ergonomics
    z = 0.0934272828928 + (0.38084933945 * ((ErgoWeight - 4.74635448442) / 19.3481000445)) + (-5.52697917334e-07 * ((Ergonomics - -0.426724137931) / 1.44698603278)) + (-2.17013687273e-07 * ((FactoredWeight - 0.135351861052) / 0.128158528477))
    pred = z
    pred = min(max(pred, -13.2), 13.2)
    item_entry["Ergonomics"] = r(pred)

    # Target: Handling
    z = 1.97373761968 + (0.722208571269 * ((HeatFactor - 0.961555555556) / 0.0363657687366)) + (0.000689559499866 * ((Recoil - -0.666666666667) / 0.816496580928)) + (0.0172097062557 * ((Ergonomics - 3.44444444444) / 2.1140330656)) + (0.469884621903 * ((FactoredWeight - 0.230229029054) / 0.137663266774))
    pred = z*z if z >= 0 else 0.0
    pred = min(max(pred, 0.7), 7.3)
    item_entry["Handling"] = r(pred)

    # Target: HeatFactor
    z = 0.989949585764 + (1.66986858746e-06 * ((HeatFactor - 0.9464) / 0.0411319826899))
    pred = z*z if z >= 0 else 0.0
    pred = min(max(pred, 0.9465), 1.0235)
    item_entry["HeatFactor"] = r(pred)

    # Target: HorizontalRecoil
    z = -1.56171808399 + (1.51384724176 * ((Ergonomics - -0.333333333333) / 5.61743318212)) + (-1.4767214928 * ((ErgoWeight - 28.6433495892) / 25.7766550386)) + (-1.33728014409 * ((Recoil - -3.44444444444) / 5.03567519717))
    pred = z
    pred = min(max(pred, -2.625), 0.125)
    item_entry["HorizontalRecoil"] = r(pred)

    # Target: VerticalRecoil
    z = -1.44444444444 + (-0.706571408211 * ((Recoil - -3.44444444444) / 5.03567519717))
    pred = z
    pred = min(max(pred, -3.15), 0.15)
    item_entry["VerticalRecoil"] = r(pred)

    # Target: Weight
    z = 0.104943965535 + (0.0898706031842 * ((Weight - 0.104943965517) / 0.0898706031381)) + (-6.79989396676e-11 * ((FactoredWeight - 0.135351861052) / 0.128158528477)) + (-6.46985626895e-12 * ((ErgoWeight - 4.74635448442) / 19.3481000445))
    pred = z
    pred = min(max(pred, -0.0187), 0.5247)
    item_entry["Weight"] = r(pred)

    return item_entry

# --- Muzzle (Mod) Formulas ---
def apply_muzzle_mod_formulas(item_entry: dict, base_data: dict, template: dict = None, context: dict = None) -> dict:
    """Auto-generated formulas for parent class: Muzzle (Mod)"""
    # Helper functions
    def to_f(x, d=0.0):
        try: return float(x)
        except: return d
    def r(x, d=3):
        try: return round(float(x), d)
        except: return x
    def expm1_clamped(z, cap=20.0):
        z = min(max(z, -cap), cap)
        return math.expm1(z)
    props = base_data.get("_props", base_data)

    # 1. Bind base features from props
    Accuracy = to_f(props.get("Accuracy", base_data.get("Accuracy", 0.0)))
    CoolFactor = to_f(props.get("CoolFactor", base_data.get("CoolFactor", 0.0)))
    Durability = to_f(props.get("Durability", base_data.get("Durability", 0.0)))
    DurabilityBurnModificator = to_f(props.get("DurabilityBurnModificator", base_data.get("DurabilityBurnModificator", 0.0)))
    EffectiveDistance = to_f(props.get("EffectiveDistance", base_data.get("EffectiveDistance", 0.0)))
    Ergonomics = to_f(props.get("Ergonomics", base_data.get("Ergonomics", 0.0)))
    HeatFactor = to_f(props.get("HeatFactor", base_data.get("HeatFactor", 0.0)))
    Loudness = to_f(props.get("Loudness", base_data.get("Loudness", 0.0)))
    Recoil = to_f(props.get("Recoil", base_data.get("Recoil", 0.0)))
    RecoilForceBack = to_f(props.get("RecoilForceBack", base_data.get("RecoilForceBack", 0.0)))
    RecoilForceUp = to_f(props.get("RecoilForceUp", base_data.get("RecoilForceUp", 0.0)))
    SightingRange = to_f(props.get("SightingRange", base_data.get("SightingRange", 0.0)))
    Velocity = to_f(props.get("Velocity", base_data.get("Velocity", 0.0)))
    Weight = to_f(props.get("Weight", base_data.get("Weight", 0.0)))

    # 2. Engineer new features
    name_str = str(base_data.get('Name', '') or base_data.get('shortName', '')).lower()
    mm_match = re.search(r'(\d+)mm', name_str)
    inch_match = re.search(r'(\d+\.?\d*)"', name_str)
    BarrelLengthMM = float(mm_match.group(1)) if mm_match else (float(inch_match.group(1)) * 25.4 if inch_match else 0.0)
    caliber_match = re.search(r'(\d+\.?\d*)x', name_str)
    CaliberNumeric = float(caliber_match.group(1)) if caliber_match else 0.0
    position_mult = 0.0
    if 'suppressor' in name_str or 'muzzle' in name_str or 'barrel' in name_str: position_mult = -1.0
    elif 'stock' in name_str or 'buttpad' in name_str: position_mult = 1.0
    Torque = Weight * position_mult * 10.0
    FactoredWeight = pow(Weight * 1.5, 1.1) if Weight > 0 else 0.0
    base_ergo_calc_val = Ergonomics / (Weight * 100) if Weight > 0 else 0.0
    ErgoWeight = pow(max(0, base_ergo_calc_val), 0.35) * 100.0
    VRecoilPerErgo = RecoilForceUp / Ergonomics if Ergonomics != 0 else 0.0
    HRecoilPerErgo = RecoilForceBack / Ergonomics if Ergonomics != 0 else 0.0
    dura = to_f(props.get('MaxDurability', base_data.get('MaxDurability', 100.0)))
    dura_factor = 2.0 - (dura / 100.0) if dura > 0 else 2.0
    DurabilityMalfRisk = pow(max(0, dura_factor), 3.0)

    # 3. Calculate all target values

    # Target: Accuracy
    z = 1.02371593631 + (1.08015577176 * ((Velocity - 0.24953271028) / 0.371722143185)) + (0.789170946669 * ((Accuracy - 0.640186915888) / 1.44250300462))
    pred = z
    pred = min(max(pred, -32.6), 24.6)
    item_entry["Accuracy"] = r(pred)

    # Target: AutoROF
    z = 0.432102803738
    pred = z
    pred = min(max(pred, -9.7), 5.7)
    item_entry["AutoROF"] = int(round(pred))

    # Target: CameraRecoil
    z = -4.67737282152 + (-36.1085495929 * ((Weight - 0.23411682243) / 0.21406827105)) + (33.6510105634 * ((FactoredWeight - 0.328918943922) / 0.329107383079)) + (1.38762943329 * ((Ergonomics - -7.02336448598) / 8.84283414879))
    pred = z
    pred = min(max(pred, -31.5), 1.5)
    item_entry["CameraRecoil"] = r(pred)

    # Target: CanCycleSubs
    z = 0
    pred = z
    pred = min(max(pred, -0.05), 1.05)
    item_entry["CanCycleSubs"] = r(pred)

    # Target: Convergence
    z = 4.16384672668 + (-1.68452022354 * ((Velocity - 0.244811320755) / 0.370264390831)) + (0.792342013847 * ((Ergonomics - -7.07075471698) / 8.87091353681)) + (-0.503234882076 * ((Weight - 0.233051886792) / 0.214209102889))
    pred = z
    pred = min(max(pred, -7.25), 42.25)
    item_entry["Convergence"] = r(pred)

    # Target: CoolFactor
    z = 1.01328997073 + (0.0315147932853 * ((CoolFactor - 1.01329439252) / 0.0315252793736))
    pred = z
    pred = min(max(pred, 0.885), 1.215)
    item_entry["CoolFactor"] = r(pred)

    # Target: Dispersion
    z = -9.6818951323 + (-0.601032173191 * ((Accuracy - 0.640186915888) / 1.44250300462)) + (0.247237660316 * ((Velocity - 0.24953271028) / 0.371722143185))
    pred = z
    pred = min(max(pred, -29.4), 1.4)
    item_entry["Dispersion"] = r(pred)

    # Target: DurabilityBurnModificator
    z = 1.05808544152 + (0.0836771109851 * ((DurabilityBurnModificator - 1.20051401869) / 0.322535540735))
    pred = z
    pred = min(max(pred, 0.9745), 1.3155)
    item_entry["DurabilityBurnModificator"] = r(pred)

    # Target: Ergonomics
    z = -0
    pred = z
    pred = min(max(pred, -1.05), 0.05)
    item_entry["Ergonomics"] = r(pred)

    # Target: Flash
    z = 1.09613597241 + (-16.179985302 * ((Recoil - -7.38038277512) / 2.81316927763)) + (30.4583483532 * ((DurabilityBurnModificator - 1.20224880383) / 0.323151667639)) + (-5.90190967702 * ((Velocity - 0.251913875598) / 0.37294402552)) + (-4.91797212609 * ((HeatFactor - 1.0420861244) / 0.0746652000876)) + (12.0908436849 * ((Ergonomics - -7.16267942584) / 8.89961799608))
    pred = z
    pred = min(max(pred, -92.25), 67.25)
    item_entry["Flash"] = r(pred)

    # Target: HeatFactor
    z = 1.02317339883 + (0.0335804142342 * ((HeatFactor - 1.04137383178) / 0.0744519569566))
    pred = z*z if z >= 0 else 0.0
    pred = min(max(pred, 0.7775), 1.2725)
    item_entry["HeatFactor"] = r(pred)

    # Target: HorizontalRecoil
    z = -6.81221473593 + (1.80043474185 * ((Velocity - 0.24953271028) / 0.371722143185)) + (-0.355472017787 * ((Ergonomics - -7.02336448598) / 8.84283414879)) + (1.8789304877 * ((Recoil - -7.23130841121) / 2.94561311204))
    pred = z
    pred = min(max(pred, -31.5), 1.5)
    item_entry["HorizontalRecoil"] = r(pred)

    # Target: Loudness
    z = 3.39928168277 + (14.0011993789 * ((Loudness - -6.59345794393) / 13.7463046591)) + (-13.8731660098 * ((DurabilityBurnModificator - 1.20051401869) / 0.322535540735)) + (-2.22235242852 * ((Velocity - 0.24953271028) / 0.371722143185)) + (-1.74354027755 * ((HeatFactor - 1.04137383178) / 0.0744519569566)) + (-6.31169334318 * ((Ergonomics - -7.02336448598) / 8.84283414879))
    pred = z
    pred = min(max(pred, -57.3), 81.3)
    item_entry["Loudness"] = r(pred)

    # Target: MeleeDamage
    z = 2.47863267981 + (0.223393359208 * ((Recoil - -6.84615384615) / 1.79083795797)) + (-0.110843108256 * ((DurabilityBurnModificator - 1.1) / 0.238424314713)) + (0.380832640595 * ((Velocity - 0.153846153846) / 0.28720238004)) + (-0.154295777293 * ((HeatFactor - 1.02007692308) / 0.0564752655709)) + (-0.135618605772 * ((Accuracy - 0.538461538462) / 1.15127919593))
    pred = expm1_clamped(z)
    pred = min(max(pred, 5.3), 20.7)
    item_entry["MeleeDamage"] = r(pred)

    # Target: MeleePen
    z = 2.0291915381 + (0.630404663589 * ((DurabilityBurnModificator - 1.12181818182) / 0.253011612447)) + (1.15363022507 * ((HeatFactor - 1.02490909091) / 0.0600824502367)) + (-0.399342559535 * ((Velocity - 0.181818181818) / 0.303968245405)) + (-13.3501269251 * ((FactoredWeight - 0.301228914212) / 0.233403623954)) + (12.1639494032 * ((Weight - 0.218363636364) / 0.156649157922))
    pred = expm1_clamped(z)
    pred = min(max(pred, 4.8), 9.2)
    item_entry["MeleePen"] = r(pred)

    # Target: ModMalfunctionChance
    z = -5.22533755619 + (3.97280353114 * ((Ergonomics - -7.02336448598) / 8.84283414879)) + (-5.13035910436 * ((DurabilityBurnModificator - 1.20051401869) / 0.322535540735)) + (0.0434705447196 * ((Weight - 0.23411682243) / 0.21406827105)) + (1.26683721124 * ((HeatFactor - 1.04137383178) / 0.0744519569566)) + (-0.00196912438391 * ((FactoredWeight - 0.328918943922) / 0.329107383079))
    pred = z
    pred = min(max(pred, -26.25), 1.25)
    item_entry["ModMalfunctionChance"] = r(pred)

    # Target: ModShotDispersion
    z = 0
    pred = z
    pred = min(max(pred, -0.75), 15.75)
    item_entry["ModShotDispersion"] = r(pred)

    # Target: RecoilAngle
    z = 0
    pred = z
    pred = min(max(pred, -1.5), 31.5)
    item_entry["RecoilAngle"] = r(pred)

    # Target: SemiROF
    z = 0.383439490446
    pred = z
    pred = min(max(pred, -9.7), 5.7)
    item_entry["SemiROF"] = int(round(pred))

    # Target: Velocity
    z = 0.209154742707 + (0.31157217394 * ((Velocity - 0.24953271028) / 0.371722143185))
    pred = z
    pred = min(max(pred, -1.9125), 1.6625)
    item_entry["Velocity"] = r(pred)

    # Target: VerticalRecoil
    z = -0
    pred = z
    pred = min(max(pred, -10.5), 0.5)
    item_entry["VerticalRecoil"] = r(pred)

    # Target: Weight
    z = 0.234116822431 + (0.214068271 * ((Weight - 0.23411682243) / 0.21406827105)) + (4.47717771161e-11 * ((FactoredWeight - 0.328918943922) / 0.329107383079)) + (2.32126198518e-11 * ((ErgoWeight - 0.467289719626) / 6.81986893426))
    pred = z
    pred = min(max(pred, -0.0445), 1.1545)
    item_entry["Weight"] = r(pred)

    return item_entry

# --- Pistol (Gun) Formulas ---
def apply_pistol_gun_formulas(item_entry: dict, base_data: dict, template: dict = None, context: dict = None) -> dict:
    """Auto-generated formulas for parent class: Pistol (Gun)"""
    # Helper functions
    def to_f(x, d=0.0):
        try: return float(x)
        except: return d
    def r(x, d=3):
        try: return round(float(x), d)
        except: return x
    def expm1_clamped(z, cap=20.0):
        z = min(max(z, -cap), cap)
        return math.expm1(z)
    props = base_data.get("_props", base_data)

    # 1. Bind base features from props
    AimPlane = to_f(props.get("AimPlane", base_data.get("AimPlane", 0.0)))
    AimSensitivity = to_f(props.get("AimSensitivity", base_data.get("AimSensitivity", 0.0)))
    BaseMalfunctionChance = to_f(props.get("BaseMalfunctionChance", base_data.get("BaseMalfunctionChance", 0.0)))
    CameraSnap = to_f(props.get("CameraSnap", base_data.get("CameraSnap", 0.0)))
    CameraToWeaponAngleStep = to_f(props.get("CameraToWeaponAngleStep", base_data.get("CameraToWeaponAngleStep", 0.0)))
    CenterOfImpact = to_f(props.get("CenterOfImpact", base_data.get("CenterOfImpact", 0.0)))
    CoolFactorGun = to_f(props.get("CoolFactorGun", base_data.get("CoolFactorGun", 0.0)))
    CoolFactorGunMods = to_f(props.get("CoolFactorGunMods", base_data.get("CoolFactorGunMods", 0.0)))
    DeviationCurve = to_f(props.get("DeviationCurve", base_data.get("DeviationCurve", 0.0)))
    DeviationMax = to_f(props.get("DeviationMax", base_data.get("DeviationMax", 0.0)))
    Durability = to_f(props.get("Durability", base_data.get("Durability", 0.0)))
    DurabilityBurnRatio = to_f(props.get("DurabilityBurnRatio", base_data.get("DurabilityBurnRatio", 0.0)))
    Ergonomics = to_f(props.get("Ergonomics", base_data.get("Ergonomics", 0.0)))
    HeatFactorByShot = to_f(props.get("HeatFactorByShot", base_data.get("HeatFactorByShot", 0.0)))
    HeatFactorGun = to_f(props.get("HeatFactorGun", base_data.get("HeatFactorGun", 0.0)))
    HipAccuracyRestorationDelay = to_f(props.get("HipAccuracyRestorationDelay", base_data.get("HipAccuracyRestorationDelay", 0.0)))
    HipAccuracyRestorationSpeed = to_f(props.get("HipAccuracyRestorationSpeed", base_data.get("HipAccuracyRestorationSpeed", 0.0)))
    HipInnaccuracyGain = to_f(props.get("HipInnaccuracyGain", base_data.get("HipInnaccuracyGain", 0.0)))
    IronSightRange = to_f(props.get("IronSightRange", base_data.get("IronSightRange", 0.0)))
    MaxRepairDegradation = to_f(props.get("MaxRepairDegradation", base_data.get("MaxRepairDegradation", 0.0)))
    MinRepairDegradation = to_f(props.get("MinRepairDegradation", base_data.get("MinRepairDegradation", 0.0)))
    RecoilAngle = to_f(props.get("RecoilAngle", base_data.get("RecoilAngle", 0.0)))
    RecoilCamera = to_f(props.get("RecoilCamera", base_data.get("RecoilCamera", 0.0)))
    RecoilCategoryMultiplierHandRotation = to_f(props.get("RecoilCategoryMultiplierHandRotation", base_data.get("RecoilCategoryMultiplierHandRotation", 0.0)))
    RecoilDampingHandRotation = to_f(props.get("RecoilDampingHandRotation", base_data.get("RecoilDampingHandRotation", 0.0)))
    RecoilForceBack = to_f(props.get("RecoilForceBack", base_data.get("RecoilForceBack", 0.0)))
    RecoilForceUp = to_f(props.get("RecoilForceUp", base_data.get("RecoilForceUp", 0.0)))
    RecoilPosZMult = to_f(props.get("RecoilPosZMult", base_data.get("RecoilPosZMult", 0.0)))
    RecoilReturnPathDampingHandRotation = to_f(props.get("RecoilReturnPathDampingHandRotation", base_data.get("RecoilReturnPathDampingHandRotation", 0.0)))
    RecoilReturnPathOffsetHandRotation = to_f(props.get("RecoilReturnPathOffsetHandRotation", base_data.get("RecoilReturnPathOffsetHandRotation", 0.0)))
    RecoilReturnSpeedHandRotation = to_f(props.get("RecoilReturnSpeedHandRotation", base_data.get("RecoilReturnSpeedHandRotation", 0.0)))
    RecolDispersion = to_f(props.get("RecolDispersion", base_data.get("RecolDispersion", 0.0)))
    SightingRange = to_f(props.get("SightingRange", base_data.get("SightingRange", 0.0)))
    SingleFireRate = to_f(props.get("SingleFireRate", base_data.get("SingleFireRate", 0.0)))
    Velocity = to_f(props.get("Velocity", base_data.get("Velocity", 0.0)))
    Weight = to_f(props.get("Weight", base_data.get("Weight", 0.0)))
    bEffDist = to_f(props.get("bEffDist", base_data.get("bEffDist", 0.0)))
    bFirerate = to_f(props.get("bFirerate", base_data.get("bFirerate", 0.0)))
    bHearDist = to_f(props.get("bHearDist", base_data.get("bHearDist", 0.0)))
    shotgunDispersion = to_f(props.get("shotgunDispersion", base_data.get("shotgunDispersion", 0.0)))

    # 2. Engineer new features
    name_str = str(base_data.get('Name', '') or base_data.get('shortName', '')).lower()
    mm_match = re.search(r'(\d+)mm', name_str)
    inch_match = re.search(r'(\d+\.?\d*)"', name_str)
    BarrelLengthMM = float(mm_match.group(1)) if mm_match else (float(inch_match.group(1)) * 25.4 if inch_match else 0.0)
    caliber_match = re.search(r'(\d+\.?\d*)x', name_str)
    CaliberNumeric = float(caliber_match.group(1)) if caliber_match else 0.0
    position_mult = 0.0
    if 'suppressor' in name_str or 'muzzle' in name_str or 'barrel' in name_str: position_mult = -1.0
    elif 'stock' in name_str or 'buttpad' in name_str: position_mult = 1.0
    Torque = Weight * position_mult * 10.0
    FactoredWeight = pow(Weight * 1.5, 1.1) if Weight > 0 else 0.0
    base_ergo_calc_val = Ergonomics / (Weight * 100) if Weight > 0 else 0.0
    ErgoWeight = pow(max(0, base_ergo_calc_val), 0.35) * 100.0
    VRecoilPerErgo = RecoilForceUp / Ergonomics if Ergonomics != 0 else 0.0
    HRecoilPerErgo = RecoilForceBack / Ergonomics if Ergonomics != 0 else 0.0
    dura = to_f(props.get('MaxDurability', base_data.get('MaxDurability', 100.0)))
    dura_factor = 2.0 - (dura / 100.0) if dura > 0 else 2.0
    DurabilityMalfRisk = pow(max(0, dura_factor), 3.0)

    # 3. Calculate all target values

    # Target: AllowOverheat
    z = 0.999999999949 + (-5.69603943793e-10 * ((ErgoWeight - 132.158398031) / 33.9525920818)) + (-2.81014406085e-10 * ((DeviationMax - 10.8461538462) / 0.360801212294)) + (2.81014406085e-10 * ((DeviationCurve - 2.28846153846) / 0.0902003030735)) + (3.09928354967e-10 * ((Ergonomics - 78.7307692308) / 9.85884098473)) + (2.95245379815e-10 * ((CenterOfImpact - 0.101923076923) / 0.155885047163)) + (-9.74002221627e-10 * ((CoolFactorGunMods - 1.13989830769) / 0.159125731583)) + (-5.41415924082e-10 * ((RecolDispersion - 9.5) / 1.59927868356))
    pred = z
    pred = min(max(pred, -0.05), 1.05)
    item_entry["AllowOverheat"] = r(pred)

    # Target: AutoROF
    z = 130.384669452 + (287.140793339 * ((bFirerate - 130.384615385) / 287.140822718))
    pred = z
    pred = min(max(pred, -23.5), 1153.5)
    item_entry["AutoROF"] = int(round(pred))

    # Target: BaseChamberCheckSpeed
    z = 0.999999999953 + (-3.83838299822e-10 * ((DeviationMax - 10.8461538462) / 0.360801212294)) + (3.83838299822e-10 * ((DeviationCurve - 2.28846153846) / 0.0902003030735)) + (-1.82796172807e-09 * ((CenterOfImpact - 0.101923076923) / 0.155885047163)) + (-2.25252745007e-08 * ((FactoredWeight - 0.667154876327) / 0.386560701023)) + (1.11726838319e-09 * ((CoolFactorGunMods - 1.13989830769) / 0.159125731583)) + (2.35223329843e-08 * ((Weight - 0.454769230769) / 0.243351804168)) + (9.30367037819e-10 * ((ErgoWeight - 132.158398031) / 33.9525920818))
    pred = z
    pred = min(max(pred, 0.9875), 1.2625)
    item_entry["BaseChamberCheckSpeed"] = r(pred)

    # Target: BaseChamberSpeedMulti
    z = 0.693147497014 + (-1.36514991516e-06 * ((DeviationMax - 10.8461538462) / 0.360801212294)) + (1.36514991516e-06 * ((DeviationCurve - 2.28846153846) / 0.0902003030735)) + (-8.58353564657e-07 * ((CenterOfImpact - 0.101923076923) / 0.155885047163)) + (0.000149480688559 * ((FactoredWeight - 0.667154876327) / 0.386560701023)) + (-1.40714648243e-06 * ((CoolFactorGunMods - 1.13989830769) / 0.159125731583)) + (-0.000152678174078 * ((Weight - 0.454769230769) / 0.243351804168)) + (-5.37078589581e-06 * ((ErgoWeight - 132.158398031) / 33.9525920818))
    pred = expm1_clamped(z)
    pred = min(max(pred, 0.9925), 1.1575)
    item_entry["BaseChamberSpeedMulti"] = r(pred)

    # Target: BaseFixSpeed
    z = 1
    pred = z
    pred = min(max(pred, 0.999999), 1.000001)
    item_entry["BaseFixSpeed"] = r(pred)

    # Target: BaseMalfunctionChance
    z = 0.0414296562725 + (-0.00963090688468 * ((ErgoWeight - 132.158398031) / 33.9525920818)) + (-0.00212001429465 * ((DeviationMax - 10.8461538462) / 0.360801212294)) + (0.00212001429465 * ((DeviationCurve - 2.28846153846) / 0.0902003030735)) + (-0.00236487597946 * ((Ergonomics - 78.7307692308) / 9.85884098473)) + (-0.000790640514134 * ((CenterOfImpact - 0.101923076923) / 0.155885047163)) + (-0.00696679897594 * ((CoolFactorGunMods - 1.13989830769) / 0.159125731583)) + (0.00108850377863 * ((RecolDispersion - 9.5) / 1.59927868356))
    pred = z*z if z >= 0 else 0.0
    pred = min(max(pred, -0.01086), 0.23906)
    item_entry["BaseMalfunctionChance"] = r(pred)

    # Target: BaseReloadSpeedMulti
    z = 1.00000000024 + (3.06123106526e-08 * ((Weight - 0.454769230769) / 0.243351804168)) + (-2.89714553877e-08 * ((FactoredWeight - 0.667154876327) / 0.386560701023)) + (2.13772220845e-09 * ((ErgoWeight - 132.158398031) / 33.9525920818))
    pred = z
    pred = min(max(pred, 0.9925), 1.1575)
    item_entry["BaseReloadSpeedMulti"] = r(pred)

    # Target: BaseTorque
    z = -0.885626217813 + (-20.2683021102 * ((Weight - 0.454769230769) / 0.243351804168)) + (19.6243830334 * ((FactoredWeight - 0.667154876327) / 0.386560701023)) + (-0.459179496494 * ((ErgoWeight - 132.158398031) / 33.9525920818)) + (0.27980751922 * ((shotgunDispersion - 9.23076923077) / 2.66469355011)) + (0.195286711526 * ((Velocity - -1.26615384615) / 2.8818838349)) + (-0.194765288275 * ((CoolFactorGunMods - 1.13989830769) / 0.159125731583)) + (-0.269103403632 * ((HeatFactorByShot - 2.63092307692) / 1.02782095579))
    pred = z
    pred = min(max(pred, -2.73), 0.13)
    item_entry["BaseTorque"] = r(pred)

    # Target: CameraRecoil
    z = 0.00599969544694 + (0.00124386769259 * ((RecoilCamera - 0.0160384615385) / 0.0166974912193)) + (-0.029467481365 * ((CameraSnap - 4.48076923077) / 1.78928847714)) + (0.0240350637155 * ((RecoilReturnSpeedHandRotation - 4.61538461538) / 1.52987991175)) + (-0.0016159658281 * ((RecoilDampingHandRotation - 0.814230769231) / 0.038045830351)) + (-6.94598496303e-05 * ((HRecoilPerErgo - 3.78249643135) / 0.858097226347))
    pred = z
    pred = min(max(pred, 0.0011), 0.0209)
    item_entry["CameraRecoil"] = r(pred)

    # Target: CenterOfImpact
    z = 0.0292790821648 + (0.0837490242588 * ((bFirerate - 130.384615385) / 287.140822718))
    pred = z
    pred = min(max(pred, -0.0195), 0.4095)
    item_entry["CenterOfImpact"] = r(pred)

    # Target: Convergence
    z = 2.92989934244 + (-0.19016268816 * ((RecoilReturnSpeedHandRotation - 4.61538461538) / 1.52987991175)) + (0.274879108604 * ((CameraSnap - 4.48076923077) / 1.78928847714)) + (0.0138789599834 * ((DeviationMax - 10.8461538462) / 0.360801212294)) + (-0.0138789599834 * ((DeviationCurve - 2.28846153846) / 0.0902003030735)) + (-0.0085128490601 * ((RecoilCamera - 0.0160384615385) / 0.0166974912193))
    pred = expm1_clamped(z)
    pred = min(max(pred, 4.25), 20.75)
    item_entry["Convergence"] = r(pred)

    # Target: CoolFactorGun
    z = 0.0953101800302 + (5.9309891379e-10 * ((CoolFactorGunMods - 1.13989830769) / 0.159125731583)) + (3.5487225043e-12 * ((CoolFactorGun - 3.94338461538) / 0.285432341023))
    pred = expm1_clamped(z)
    pred = min(max(pred, -0.0966), 4.2286)
    item_entry["CoolFactorGun"] = r(pred)

    # Target: CoolFactorGunMods
    z = 1.00000000013 + (1.15007410111e-10 * ((CoolFactorGunMods - 1.13989830769) / 0.159125731583)) + (2.15826058778e-11 * ((CoolFactorGun - 3.94338461538) / 0.285432341023))
    pred = z
    pred = min(max(pred, 0.9786514), 1.4483206)
    item_entry["CoolFactorGunMods"] = r(pred)

    # Target: Dispersion
    z = 2.35753211223 + (0.22748362982 * ((shotgunDispersion - 9.23076923077) / 2.66469355011)) + (0.116588316778 * ((Velocity - -1.26615384615) / 2.8818838349)) + (0.111660009226 * ((CenterOfImpact - 0.101923076923) / 0.155885047163)) + (-0.0405630308761 * ((DeviationCurve - 2.28846153846) / 0.0902003030735))
    pred = expm1_clamped(z)
    pred = min(max(pred, 3.3), 18.7)
    item_entry["Dispersion"] = r(pred)

    # Target: DoubleActionAccuracyPenalty
    z = 1
    pred = z
    pred = min(max(pred, 0.999999), 1.000001)
    item_entry["DoubleActionAccuracyPenalty"] = r(pred)

    # Target: DurabilityBurnRatio
    z = 0.21789075698 + (0.0117012965781 * ((DurabilityBurnRatio - 1.14730769231) / 0.0134615384615))
    pred = expm1_clamped(z)
    pred = min(max(pred, -0.0155), 1.2055)
    item_entry["DurabilityBurnRatio"] = r(pred)

    # Target: EnableExtraBSGVisRecoil
    z = 0
    pred = z
    pred = min(max(pred, -1e-06), 1e-06)
    item_entry["EnableExtraBSGVisRecoil"] = r(pred)

    # Target: Ergonomics
    z = 4.3044220119 + (0.15099261713 * ((ErgoWeight - 132.158398031) / 33.9525920818)) + (1.02345775122 * ((Weight - 0.454769230769) / 0.243351804168)) + (-0.926867399118 * ((FactoredWeight - 0.667154876327) / 0.386560701023))
    pred = expm1_clamped(z)
    pred = min(max(pred, 62.2), 101.8)
    item_entry["Ergonomics"] = r(pred)

    # Target: HasShoulderContact
    z = 0
    pred = z
    pred = min(max(pred, -1e-06), 1e-06)
    item_entry["HasShoulderContact"] = r(pred)

    # Target: HeatFactorByShot
    z = 1.00000000009 + (-1.75912268232e-10 * ((HeatFactorGun - 1.00458215385) / 0.0533322100537)) + (4.37680043234e-11 * ((HeatFactorByShot - 2.63092307692) / 1.02782095579))
    pred = z*z if z >= 0 else 0.0
    pred = min(max(pred, 0.972), 1.588)
    item_entry["HeatFactorByShot"] = r(pred)

    # Target: HeatFactorGun
    z = 0.249572879788 + (-0.0039908810027 * ((HeatFactorGun - 1.00458215385) / 0.0533322100537)) + (-0.00131458066583 * ((HeatFactorByShot - 2.63092307692) / 1.02782095579))
    pred = z
    pred = min(max(pred, 0.1556256), 1.1318624)
    item_entry["HeatFactorGun"] = r(pred)

    # Target: HipAccuracyRestorationDelay
    z = 0.2
    pred = z
    pred = min(max(pred, 0.199999), 0.200001)
    item_entry["HipAccuracyRestorationDelay"] = r(pred)

    # Target: HipAccuracyRestorationSpeed
    z = 2.64575131106
    pred = z*z if z >= 0 else 0.0
    pred = min(max(pred, 6.999999), 7.000001)
    item_entry["HipAccuracyRestorationSpeed"] = r(pred)

    # Target: HipInnaccuracyGain
    z = 0.4
    pred = z*z if z >= 0 else 0.0
    pred = min(max(pred, 0.159999), 0.160001)
    item_entry["HipInnaccuracyGain"] = r(pred)

    # Target: HorizontalRecoil
    z = 15.9549580963 + (2.36274820383 * ((RecoilDampingHandRotation - 0.814230769231) / 0.038045830351)) + (10.2486458343 * ((RecoilCamera - 0.0160384615385) / 0.0166974912193)) + (64.4512985083 * ((CameraSnap - 4.48076923077) / 1.78928847714)) + (-56.6684068988 * ((RecoilReturnSpeedHandRotation - 4.61538461538) / 1.52987991175)) + (-0.785100742985 * ((HRecoilPerErgo - 3.78249643135) / 0.858097226347))
    pred = z*z if z >= 0 else 0.0
    pred = min(max(pred, -6), 566)
    item_entry["HorizontalRecoil"] = r(pred)

    # Target: MaxChamberSpeed
    z = 1.5
    pred = z
    pred = min(max(pred, 1.499999), 1.500001)
    item_entry["MaxChamberSpeed"] = r(pred)

    # Target: MinChamberSpeed
    z = 0.799999999969 + (-1.95007107725e-10 * ((ErgoWeight - 132.158398031) / 33.9525920818)) + (-7.55187960059e-11 * ((DeviationMax - 10.8461538462) / 0.360801212294)) + (7.55187960059e-11 * ((DeviationCurve - 2.28846153846) / 0.0902003030735)) + (1.00223081941e-10 * ((Ergonomics - 78.7307692308) / 9.85884098473)) + (-2.11353959612e-11 * ((CenterOfImpact - 0.101923076923) / 0.155885047163)) + (-2.24544991717e-10 * ((CoolFactorGunMods - 1.13989830769) / 0.159125731583)) + (-8.21933864135e-11 * ((RecolDispersion - 9.5) / 1.59927868356))
    pred = z
    pred = min(max(pred, 0.695), 0.805)
    item_entry["MinChamberSpeed"] = r(pred)

    # Target: OffsetRotation
    z = 0.0995939507456 + (0.00203024601665 * ((Durability - 99.6153846154) / 1.92307692308)) + (8.8527693971e-10 * ((RecoilForceBack - 290.038461538) / 35.241453704)) + (-3.31413674967e-10 * ((RecolDispersion - 9.5) / 1.59927868356)) + (-9.84764633656e-10 * ((HRecoilPerErgo - 3.78249643135) / 0.858097226347)) + (4.51565064005e-10 * ((RecoilDampingHandRotation - 0.814230769231) / 0.038045830351)) + (-1.94604341418e-11 * ((CoolFactorGunMods - 1.13989830769) / 0.159125731583)) + (-4.17728376508e-11 * ((Ergonomics - 78.7307692308) / 9.85884098473))
    pred = z*z if z >= 0 else 0.0
    pred = min(max(pred, 0.0078), 0.0122)
    item_entry["OffsetRotation"] = r(pred)

    # Target: RecoilAngle
    z = 94.1107443573 + (2.24182926432 * ((RecoilDampingHandRotation - 0.814230769231) / 0.038045830351)) + (5.51410465536 * ((CameraSnap - 4.48076923077) / 1.78928847714)) + (-0.373394125651 * ((RecoilCamera - 0.0160384615385) / 0.0166974912193)) + (-6.41156841284 * ((RecoilReturnSpeedHandRotation - 4.61538461538) / 1.52987991175)) + (-0.479679814896 * ((Ergonomics - 78.7307692308) / 9.85884098473))
    pred = z
    pred = min(max(pred, 84.25), 100.75)
    item_entry["RecoilAngle"] = r(pred)

    # Target: RecoilDamping
    z = 0.751816399493 + (-0.0114140457945 * ((DeviationMax - 10.8461538462) / 0.360801212294)) + (0.000298948602416 * ((DeviationCurve - 2.28846153846) / 0.0902003030735)) + (0.0220379480237 * ((RecoilForceUp - 396.923076923) / 76.5375338173)) + (0.0114031973647 * ((RecoilCamera - 0.0160384615385) / 0.0166974912193)) + (-0.0183974205746 * ((VRecoilPerErgo - 5.20947053404) / 1.52518058256))
    pred = z
    pred = min(max(pred, 0.6845), 0.8055)
    item_entry["RecoilDamping"] = r(pred)

    # Target: RecoilHandDamping
    z = 0.459452234953 + (0.0813297376699 * ((RecoilDampingHandRotation - 0.814230769231) / 0.038045830351)) + (0.785867081626 * ((CameraSnap - 4.48076923077) / 1.78928847714)) + (-0.716720775983 * ((RecoilReturnSpeedHandRotation - 4.61538461538) / 1.52987991175)) + (0.0630475523336 * ((RecoilCamera - 0.0160384615385) / 0.0166974912193)) + (-0.0117062210341 * ((HRecoilPerErgo - 3.78249643135) / 0.858097226347))
    pred = z
    pred = min(max(pred, 0.3915), 0.5785)
    item_entry["RecoilHandDamping"] = r(pred)

    # Target: RecoilIntensity
    z = 0.630371109773 + (0.135630035153 * ((RecoilCamera - 0.0160384615385) / 0.0166974912193)) + (0.668787642171 * ((CameraSnap - 4.48076923077) / 1.78928847714)) + (-0.658543825288 * ((RecoilReturnSpeedHandRotation - 4.61538461538) / 1.52987991175)) + (-0.0251023490369 * ((RecoilDampingHandRotation - 0.814230769231) / 0.038045830351)) + (-0.00388217841088 * ((HRecoilPerErgo - 3.78249643135) / 0.858097226347))
    pred = z*z if z >= 0 else 0.0
    pred = min(max(pred, 0.1119), 0.6861)
    item_entry["RecoilIntensity"] = r(pred)

    # Target: SemiROF
    z = 361.369146203 + (-4.94530259096 * ((bFirerate - 130.384615385) / 287.140822718))
    pred = z
    pred = min(max(pred, 292.5), 457.5)
    item_entry["SemiROF"] = int(round(pred))

    # Target: ShotgunDispersion
    z = 7.4
    pred = z
    pred = min(max(pred, 6.66), 8.14)
    item_entry["ShotgunDispersion"] = r(pred)

    # Target: Velocity
    z = -0
    pred = z
    pred = min(max(pred, -19.495), 17.795)
    item_entry["Velocity"] = r(pred)

    # Target: VerticalRecoil
    z = 6.03515380598 + (0.11923687204 * ((RecoilDampingHandRotation - 0.814230769231) / 0.038045830351)) + (0.119011213756 * ((RecoilCamera - 0.0160384615385) / 0.0166974912193)) + (0.194624407682 * ((HRecoilPerErgo - 3.78249643135) / 0.858097226347)) + (0.19383175956 * ((Ergonomics - 78.7307692308) / 9.85884098473)) + (0.0729039851786 * ((CameraSnap - 4.48076923077) / 1.78928847714))
    pred = expm1_clamped(z)
    pred = min(max(pred, -19.5), 629.5)
    item_entry["VerticalRecoil"] = r(pred)

    # Target: VisualMulti
    z = 2.19787966637 + (-0.694353801057 * ((ErgoWeight - 132.158398031) / 33.9525920818)) + (0.035394035959 * ((Ergonomics - 78.7307692308) / 9.85884098473)) + (-0.174118365915 * ((Velocity - -1.26615384615) / 2.8818838349)) + (0.903274759723 * ((Weight - 0.454769230769) / 0.243351804168)) + (-1.30761078213 * ((FactoredWeight - 0.667154876327) / 0.386560701023)) + (-0.211350241959 * ((VRecoilPerErgo - 5.20947053404) / 1.52518058256)) + (0.211252306058 * ((HRecoilPerErgo - 3.78249643135) / 0.858097226347))
    pred = z
    pred = min(max(pred, 0.375), 3.125)
    item_entry["VisualMulti"] = r(pred)

    # Target: WeapAccuracy
    z = 0
    pred = z
    pred = min(max(pred, -1e-06), 1e-06)
    item_entry["WeapAccuracy"] = r(pred)

    # Target: WeaponAllowADS
    z = 0
    pred = z
    pred = min(max(pred, -1e-06), 1e-06)
    item_entry["WeaponAllowADS"] = r(pred)

    # Target: Weight
    z = 0.454768483436 + (-4.26588708763e-05 * ((FactoredWeight - 0.667154876327) / 0.386560701023)) + (0.243394129538 * ((Weight - 0.454769230769) / 0.243351804168)) + (2.38668702854e-07 * ((ErgoWeight - 132.158398031) / 33.9525920818))
    pred = z
    pred = min(max(pred, 0.04625), 0.89875)
    item_entry["Weight"] = r(pred)

    return item_entry

# --- PistolGrip (Mod) Formulas ---
def apply_pistolgrip_mod_formulas(item_entry: dict, base_data: dict, template: dict = None, context: dict = None) -> dict:
    """Auto-generated formulas for parent class: PistolGrip (Mod)"""
    # Helper functions
    def to_f(x, d=0.0):
        try: return float(x)
        except: return d
    def r(x, d=3):
        try: return round(float(x), d)
        except: return x
    def expm1_clamped(z, cap=20.0):
        z = min(max(z, -cap), cap)
        return math.expm1(z)
    props = base_data.get("_props", base_data)

    # 1. Bind base features from props
    Accuracy = to_f(props.get("Accuracy", base_data.get("Accuracy", 0.0)))
    Durability = to_f(props.get("Durability", base_data.get("Durability", 0.0)))
    EffectiveDistance = to_f(props.get("EffectiveDistance", base_data.get("EffectiveDistance", 0.0)))
    Ergonomics = to_f(props.get("Ergonomics", base_data.get("Ergonomics", 0.0)))
    Loudness = to_f(props.get("Loudness", base_data.get("Loudness", 0.0)))
    Recoil = to_f(props.get("Recoil", base_data.get("Recoil", 0.0)))
    RecoilForceBack = to_f(props.get("RecoilForceBack", base_data.get("RecoilForceBack", 0.0)))
    RecoilForceUp = to_f(props.get("RecoilForceUp", base_data.get("RecoilForceUp", 0.0)))
    SightingRange = to_f(props.get("SightingRange", base_data.get("SightingRange", 0.0)))
    Velocity = to_f(props.get("Velocity", base_data.get("Velocity", 0.0)))
    Weight = to_f(props.get("Weight", base_data.get("Weight", 0.0)))

    # 2. Engineer new features
    name_str = str(base_data.get('Name', '') or base_data.get('shortName', '')).lower()
    mm_match = re.search(r'(\d+)mm', name_str)
    inch_match = re.search(r'(\d+\.?\d*)"', name_str)
    BarrelLengthMM = float(mm_match.group(1)) if mm_match else (float(inch_match.group(1)) * 25.4 if inch_match else 0.0)
    caliber_match = re.search(r'(\d+\.?\d*)x', name_str)
    CaliberNumeric = float(caliber_match.group(1)) if caliber_match else 0.0
    position_mult = 0.0
    if 'suppressor' in name_str or 'muzzle' in name_str or 'barrel' in name_str: position_mult = -1.0
    elif 'stock' in name_str or 'buttpad' in name_str: position_mult = 1.0
    Torque = Weight * position_mult * 10.0
    FactoredWeight = pow(Weight * 1.5, 1.1) if Weight > 0 else 0.0
    base_ergo_calc_val = Ergonomics / (Weight * 100) if Weight > 0 else 0.0
    ErgoWeight = pow(max(0, base_ergo_calc_val), 0.35) * 100.0
    VRecoilPerErgo = RecoilForceUp / Ergonomics if Ergonomics != 0 else 0.0
    HRecoilPerErgo = RecoilForceBack / Ergonomics if Ergonomics != 0 else 0.0
    dura = to_f(props.get('MaxDurability', base_data.get('MaxDurability', 100.0)))
    dura_factor = 2.0 - (dura / 100.0) if dura > 0 else 2.0
    DurabilityMalfRisk = pow(max(0, dura_factor), 3.0)

    # 3. Calculate all target values

    # Target: Accuracy
    z = -7.62875879298e-12
    pred = z*z if z >= 0 else 0.0
    pred = min(max(pred, -0.5), 10.5)
    item_entry["Accuracy"] = r(pred)

    # Target: AimSpeed
    z = 0
    pred = z
    pred = min(max(pred, -0.5), 10.5)
    item_entry["AimSpeed"] = r(pred)

    # Target: AimStability
    z = 4.57762413576 + (0.829941727767 * ((Weight - 0.0877837837838) / 0.0350290498248)) + (0.605197537562 * ((FactoredWeight - 0.108291242206) / 0.0488689526563)) + (1.50228956071 * ((Ergonomics - 8.60810810811) / 3.08907214079)) + (-1.13759151559 * ((ErgoWeight - 100.052142424) / 14.6024464416))
    pred = z
    pred = min(max(pred, -16.75), 21.75)
    item_entry["AimStability"] = r(pred)

    # Target: Dispersion
    z = -4.13830932369e-09
    pred = z
    pred = min(max(pred, -11.25), 16.25)
    item_entry["Dispersion"] = r(pred)

    # Target: Ergonomics
    z = 1.95809392372 + (0.383373609206 * ((ErgoWeight - 91.0455527451) / 19.6937840572)) + (-0.0604456693817 * ((Ergonomics - 7.35416666667) / 3.21998695218)) + (0.230604310506 * ((Weight - 0.0938416666667) / 0.037218050243))
    pred = z*z if z >= 0 else 0.0
    pred = min(max(pred, -0.75), 15.75)
    item_entry["Ergonomics"] = r(pred)

    # Target: Handling
    z = 4.39089323385 + (22.4304489888 * ((Weight - 0.0981587301587) / 0.0377410585854)) + (-20.6972017992 * ((FactoredWeight - 0.122432929724) / 0.0528051421218)) + (1.70162698481 * ((ErgoWeight - 93.8469191905) / 13.637564921)) + (0.3393069257 * ((Durability - 99.8412698413) / 1.24984251968)) + (-1.06544961848 * ((Ergonomics - 7.9126984127) / 2.65703570738))
    pred = z
    pred = min(max(pred, -16.6), 18.6)
    item_entry["Handling"] = r(pred)

    # Target: HorizontalRecoil
    z = -0
    pred = z
    pred = min(max(pred, -10.875), 8.375)
    item_entry["HorizontalRecoil"] = r(pred)

    # Target: VerticalRecoil
    z = -0
    pred = z
    pred = min(max(pred, -21), 1)
    item_entry["VerticalRecoil"] = r(pred)

    # Target: Weight
    z = 0.0938416666578 + (0.0372180504289 * ((Weight - 0.0938416666667) / 0.037218050243)) + (-1.8674431234e-10 * ((FactoredWeight - 0.116591339968) / 0.0517004681347)) + (-5.72084787812e-12 * ((ErgoWeight - 91.0455527451) / 19.6937840572))
    pred = z
    pred = min(max(pred, 0.02115), 0.28185)
    item_entry["Weight"] = r(pred)

    return item_entry

# --- Receiver (Mod) Formulas ---
def apply_receiver_mod_formulas(item_entry: dict, base_data: dict, template: dict = None, context: dict = None) -> dict:
    """Auto-generated formulas for parent class: Receiver (Mod)"""
    # Helper functions
    def to_f(x, d=0.0):
        try: return float(x)
        except: return d
    def r(x, d=3):
        try: return round(float(x), d)
        except: return x
    def expm1_clamped(z, cap=20.0):
        z = min(max(z, -cap), cap)
        return math.expm1(z)
    props = base_data.get("_props", base_data)

    # 1. Bind base features from props
    Accuracy = to_f(props.get("Accuracy", base_data.get("Accuracy", 0.0)))
    CoolFactor = to_f(props.get("CoolFactor", base_data.get("CoolFactor", 0.0)))
    Durability = to_f(props.get("Durability", base_data.get("Durability", 0.0)))
    DurabilityBurnModificator = to_f(props.get("DurabilityBurnModificator", base_data.get("DurabilityBurnModificator", 0.0)))
    EffectiveDistance = to_f(props.get("EffectiveDistance", base_data.get("EffectiveDistance", 0.0)))
    Ergonomics = to_f(props.get("Ergonomics", base_data.get("Ergonomics", 0.0)))
    HeatFactor = to_f(props.get("HeatFactor", base_data.get("HeatFactor", 0.0)))
    Loudness = to_f(props.get("Loudness", base_data.get("Loudness", 0.0)))
    Recoil = to_f(props.get("Recoil", base_data.get("Recoil", 0.0)))
    RecoilForceBack = to_f(props.get("RecoilForceBack", base_data.get("RecoilForceBack", 0.0)))
    RecoilForceUp = to_f(props.get("RecoilForceUp", base_data.get("RecoilForceUp", 0.0)))
    SightingRange = to_f(props.get("SightingRange", base_data.get("SightingRange", 0.0)))
    Velocity = to_f(props.get("Velocity", base_data.get("Velocity", 0.0)))
    Weight = to_f(props.get("Weight", base_data.get("Weight", 0.0)))

    # 2. Engineer new features
    name_str = str(base_data.get('Name', '') or base_data.get('shortName', '')).lower()
    mm_match = re.search(r'(\d+)mm', name_str)
    inch_match = re.search(r'(\d+\.?\d*)"', name_str)
    BarrelLengthMM = float(mm_match.group(1)) if mm_match else (float(inch_match.group(1)) * 25.4 if inch_match else 0.0)
    caliber_match = re.search(r'(\d+\.?\d*)x', name_str)
    CaliberNumeric = float(caliber_match.group(1)) if caliber_match else 0.0
    position_mult = 0.0
    if 'suppressor' in name_str or 'muzzle' in name_str or 'barrel' in name_str: position_mult = -1.0
    elif 'stock' in name_str or 'buttpad' in name_str: position_mult = 1.0
    Torque = Weight * position_mult * 10.0
    FactoredWeight = pow(Weight * 1.5, 1.1) if Weight > 0 else 0.0
    base_ergo_calc_val = Ergonomics / (Weight * 100) if Weight > 0 else 0.0
    ErgoWeight = pow(max(0, base_ergo_calc_val), 0.35) * 100.0
    VRecoilPerErgo = RecoilForceUp / Ergonomics if Ergonomics != 0 else 0.0
    HRecoilPerErgo = RecoilForceBack / Ergonomics if Ergonomics != 0 else 0.0
    dura = to_f(props.get('MaxDurability', base_data.get('MaxDurability', 100.0)))
    dura_factor = 2.0 - (dura / 100.0) if dura > 0 else 2.0
    DurabilityMalfRisk = pow(max(0, dura_factor), 3.0)

    # 3. Calculate all target values

    # Target: Accuracy
    z = 0.126322395916 + (1.22467511492 * ((Accuracy - 0.0526315789474) / 0.510282090254)) + (6.65945919736e-06 * ((Velocity - -0.347368421053) / 3.36786179568))
    pred = z
    pred = min(max(pred, -21.8), 17.8)
    item_entry["Accuracy"] = r(pred)

    # Target: ChamberSpeed
    z = 6.04233551643 + (14.6141570222 * ((CoolFactor - 1.02893411765) / 0.035219515155)) + (-2.01334834217 * ((Recoil - -0.664705882353) / 1.22567684853)) + (12.1284608639 * ((HeatFactor - 0.984045882353) / 0.0296593663529)) + (0.31480553648 * ((ErgoWeight - 52.7860399153) / 16.9081274133)) + (0.863077567191 * ((Accuracy - 0.0588235294118) / 0.539126552348))
    pred = z
    pred = min(max(pred, -1.8), 37.8)
    item_entry["ChamberSpeed"] = r(pred)

    # Target: CoolFactor
    z = 1.02759368419 + (0.0352727263148 * ((CoolFactor - 1.02759368421) / 0.0352727263373))
    pred = z
    pred = min(max(pred, 0.95499), 1.13121)
    item_entry["CoolFactor"] = r(pred)

    # Target: DurabilityBurnModificator
    z = 0.988938922374 + (0.0125513961849 * ((DurabilityBurnModificator - 0.986894736842) / 0.0148710058303))
    pred = z*z if z >= 0 else 0.0
    pred = min(max(pred, 0.475), 1.025)
    item_entry["DurabilityBurnModificator"] = r(pred)

    # Target: Ergonomics
    z = 0
    pred = z
    pred = min(max(pred, -0.2), 4.2)
    item_entry["Ergonomics"] = r(pred)

    # Target: HeatFactor
    z = 0.985146315793 + (0.0292086822365 * ((HeatFactor - 0.985146315789) / 0.0292086822367))
    pred = z
    pred = min(max(pred, 0.91793), 1.06467)
    item_entry["HeatFactor"] = r(pred)

    # Target: HorizontalRecoil
    z = 0
    pred = z
    pred = min(max(pred, -1e-06), 1e-06)
    item_entry["HorizontalRecoil"] = r(pred)

    # Target: MalfChance
    z = 0
    pred = z
    pred = min(max(pred, -1e-06), 1e-06)
    item_entry["MalfChance"] = r(pred)

    # Target: ModMalfunctionChance
    z = -1.89932646759 + (1.3057009999 * ((DurabilityBurnModificator - 0.986894736842) / 0.0148710058303)) + (-0.00319580834413 * ((ErgoWeight - 52.4478698721) / 17.4192656251)) + (0.365215676602 * ((CoolFactor - 1.02759368421) / 0.0352727263373)) + (22.718918792 * ((Weight - 0.278768421053) / 0.169303368489)) + (-22.2719497162 * ((FactoredWeight - 0.389980058299) / 0.264487393981))
    pred = z
    pred = min(max(pred, -6.3), 0.3)
    item_entry["ModMalfunctionChance"] = r(pred)

    # Target: VerticalRecoil
    z = 0
    pred = z
    pred = min(max(pred, -1e-06), 1e-06)
    item_entry["VerticalRecoil"] = r(pred)

    # Target: Weight
    z = 0.278768420917 + (0.169303369495 * ((Weight - 0.278768421053) / 0.169303368489)) + (-7.48955447193e-10 * ((FactoredWeight - 0.389980058299) / 0.264487393981)) + (1.25511523665e-10 * ((ErgoWeight - 52.4478698721) / 17.4192656251))
    pred = z
    pred = min(max(pred, -0.0025), 1.1525)
    item_entry["Weight"] = r(pred)

    return item_entry

# --- SMGs (Gun) Formulas ---
def apply_smgs_gun_formulas(item_entry: dict, base_data: dict, template: dict = None, context: dict = None) -> dict:
    """Auto-generated formulas for parent class: SMGs (Gun)"""
    # Helper functions
    def to_f(x, d=0.0):
        try: return float(x)
        except: return d
    def r(x, d=3):
        try: return round(float(x), d)
        except: return x
    def expm1_clamped(z, cap=20.0):
        z = min(max(z, -cap), cap)
        return math.expm1(z)
    props = base_data.get("_props", base_data)

    # 1. Bind base features from props
    AimPlane = to_f(props.get("AimPlane", base_data.get("AimPlane", 0.0)))
    AimSensitivity = to_f(props.get("AimSensitivity", base_data.get("AimSensitivity", 0.0)))
    BaseMalfunctionChance = to_f(props.get("BaseMalfunctionChance", base_data.get("BaseMalfunctionChance", 0.0)))
    CameraSnap = to_f(props.get("CameraSnap", base_data.get("CameraSnap", 0.0)))
    CameraToWeaponAngleStep = to_f(props.get("CameraToWeaponAngleStep", base_data.get("CameraToWeaponAngleStep", 0.0)))
    CenterOfImpact = to_f(props.get("CenterOfImpact", base_data.get("CenterOfImpact", 0.0)))
    CoolFactorGun = to_f(props.get("CoolFactorGun", base_data.get("CoolFactorGun", 0.0)))
    CoolFactorGunMods = to_f(props.get("CoolFactorGunMods", base_data.get("CoolFactorGunMods", 0.0)))
    DeviationCurve = to_f(props.get("DeviationCurve", base_data.get("DeviationCurve", 0.0)))
    DeviationMax = to_f(props.get("DeviationMax", base_data.get("DeviationMax", 0.0)))
    Durability = to_f(props.get("Durability", base_data.get("Durability", 0.0)))
    DurabilityBurnRatio = to_f(props.get("DurabilityBurnRatio", base_data.get("DurabilityBurnRatio", 0.0)))
    Ergonomics = to_f(props.get("Ergonomics", base_data.get("Ergonomics", 0.0)))
    HeatFactorByShot = to_f(props.get("HeatFactorByShot", base_data.get("HeatFactorByShot", 0.0)))
    HeatFactorGun = to_f(props.get("HeatFactorGun", base_data.get("HeatFactorGun", 0.0)))
    HipAccuracyRestorationDelay = to_f(props.get("HipAccuracyRestorationDelay", base_data.get("HipAccuracyRestorationDelay", 0.0)))
    HipAccuracyRestorationSpeed = to_f(props.get("HipAccuracyRestorationSpeed", base_data.get("HipAccuracyRestorationSpeed", 0.0)))
    HipInnaccuracyGain = to_f(props.get("HipInnaccuracyGain", base_data.get("HipInnaccuracyGain", 0.0)))
    IronSightRange = to_f(props.get("IronSightRange", base_data.get("IronSightRange", 0.0)))
    MaxRepairDegradation = to_f(props.get("MaxRepairDegradation", base_data.get("MaxRepairDegradation", 0.0)))
    MinRepairDegradation = to_f(props.get("MinRepairDegradation", base_data.get("MinRepairDegradation", 0.0)))
    RecoilAngle = to_f(props.get("RecoilAngle", base_data.get("RecoilAngle", 0.0)))
    RecoilCamera = to_f(props.get("RecoilCamera", base_data.get("RecoilCamera", 0.0)))
    RecoilCategoryMultiplierHandRotation = to_f(props.get("RecoilCategoryMultiplierHandRotation", base_data.get("RecoilCategoryMultiplierHandRotation", 0.0)))
    RecoilDampingHandRotation = to_f(props.get("RecoilDampingHandRotation", base_data.get("RecoilDampingHandRotation", 0.0)))
    RecoilForceBack = to_f(props.get("RecoilForceBack", base_data.get("RecoilForceBack", 0.0)))
    RecoilForceUp = to_f(props.get("RecoilForceUp", base_data.get("RecoilForceUp", 0.0)))
    RecoilPosZMult = to_f(props.get("RecoilPosZMult", base_data.get("RecoilPosZMult", 0.0)))
    RecoilReturnPathDampingHandRotation = to_f(props.get("RecoilReturnPathDampingHandRotation", base_data.get("RecoilReturnPathDampingHandRotation", 0.0)))
    RecoilReturnPathOffsetHandRotation = to_f(props.get("RecoilReturnPathOffsetHandRotation", base_data.get("RecoilReturnPathOffsetHandRotation", 0.0)))
    RecoilReturnSpeedHandRotation = to_f(props.get("RecoilReturnSpeedHandRotation", base_data.get("RecoilReturnSpeedHandRotation", 0.0)))
    RecolDispersion = to_f(props.get("RecolDispersion", base_data.get("RecolDispersion", 0.0)))
    SightingRange = to_f(props.get("SightingRange", base_data.get("SightingRange", 0.0)))
    SingleFireRate = to_f(props.get("SingleFireRate", base_data.get("SingleFireRate", 0.0)))
    Velocity = to_f(props.get("Velocity", base_data.get("Velocity", 0.0)))
    Weight = to_f(props.get("Weight", base_data.get("Weight", 0.0)))
    bEffDist = to_f(props.get("bEffDist", base_data.get("bEffDist", 0.0)))
    bFirerate = to_f(props.get("bFirerate", base_data.get("bFirerate", 0.0)))
    bHearDist = to_f(props.get("bHearDist", base_data.get("bHearDist", 0.0)))
    shotgunDispersion = to_f(props.get("shotgunDispersion", base_data.get("shotgunDispersion", 0.0)))

    # 2. Engineer new features
    name_str = str(base_data.get('Name', '') or base_data.get('shortName', '')).lower()
    mm_match = re.search(r'(\d+)mm', name_str)
    inch_match = re.search(r'(\d+\.?\d*)"', name_str)
    BarrelLengthMM = float(mm_match.group(1)) if mm_match else (float(inch_match.group(1)) * 25.4 if inch_match else 0.0)
    caliber_match = re.search(r'(\d+\.?\d*)x', name_str)
    CaliberNumeric = float(caliber_match.group(1)) if caliber_match else 0.0
    position_mult = 0.0
    if 'suppressor' in name_str or 'muzzle' in name_str or 'barrel' in name_str: position_mult = -1.0
    elif 'stock' in name_str or 'buttpad' in name_str: position_mult = 1.0
    Torque = Weight * position_mult * 10.0
    FactoredWeight = pow(Weight * 1.5, 1.1) if Weight > 0 else 0.0
    base_ergo_calc_val = Ergonomics / (Weight * 100) if Weight > 0 else 0.0
    ErgoWeight = pow(max(0, base_ergo_calc_val), 0.35) * 100.0
    VRecoilPerErgo = RecoilForceUp / Ergonomics if Ergonomics != 0 else 0.0
    HRecoilPerErgo = RecoilForceBack / Ergonomics if Ergonomics != 0 else 0.0
    dura = to_f(props.get('MaxDurability', base_data.get('MaxDurability', 100.0)))
    dura_factor = 2.0 - (dura / 100.0) if dura > 0 else 2.0
    DurabilityMalfRisk = pow(max(0, dura_factor), 3.0)

    # 3. Calculate all target values

    # Target: AllowOverheat
    z = 0.872173871936 + (0.0266719531796 * ((RecoilAngle - 90.4545454545) / 3.34021328561)) + (0.326160367759 * ((HeatFactorGun - 1.01639090909) / 0.0567916279769)) + (-0.0598084968038 * ((Ergonomics - 58.1818181818) / 15.1436646329)) + (0.0728695872169 * ((AimPlane - 0.173636363636) / 0.0911814103136)) + (-0.273162732283 * ((Velocity - 4.57636363636) / 11.3321323298)) + (0.0445482491232 * ((bEffDist - 209.090909091) / 104.050210384)) + (0.0990200468736 * ((RecoilDampingHandRotation - 0.844090909091) / 0.00576753524566))
    pred = z
    pred = min(max(pred, -0.05), 1.05)
    item_entry["AllowOverheat"] = r(pred)

    # Target: AutoROF
    z = 893.181817887 + (146.97360216 * ((bFirerate - 893.181818182) / 146.973601947))
    pred = z
    pred = min(max(pred, 575), 1125)
    item_entry["AutoROF"] = int(round(pred))

    # Target: BaseChamberCheckSpeed
    z = 0.699975382463 + (0.0087920829689 * ((DeviationMax - 11.2954545455) / 1.6831996783)) + (-0.0806495253681 * ((ErgoWeight - 80.0608249715) / 15.3775837237)) + (-0.0205655544793 * ((DeviationCurve - 2.26818181818) / 0.296013457367)) + (-0.0395860390181 * ((RecoilForceBack - 244.863636364) / 42.3087090267)) + (-0.934858091605 * ((Weight - 1.21481818182) / 0.504026662026)) + (0.888455307605 * ((FactoredWeight - 1.95347489381) / 0.884257483672)) + (0.019301231847 * ((Velocity - 4.57636363636) / 11.3321323298))
    pred = expm1_clamped(z)
    pred = min(max(pred, 0.775), 1.325)
    item_entry["BaseChamberCheckSpeed"] = r(pred)

    # Target: BaseChamberSpeedMulti
    z = 1.00000000189 + (6.86800193285e-09 * ((Velocity - 4.57636363636) / 11.3321323298)) + (4.29996894774e-09 * ((HeatFactorGun - 1.01639090909) / 0.0567916279769)) + (-6.60238640041e-09 * ((RecoilForceBack - 244.863636364) / 42.3087090267)) + (-4.64447690685e-09 * ((Durability - 98.6363636364) / 2.22680885708)) + (1.10603019261e-09 * ((DeviationMax - 11.2954545455) / 1.6831996783)) + (-2.79515407589e-09 * ((HeatFactorByShot - 2.00681818182) / 0.31762451193)) + (-5.30916541228e-09 * ((Ergonomics - 58.1818181818) / 15.1436646329))
    pred = z*z if z >= 0 else 0.0
    pred = min(max(pred, 0.8375), 1.1125)
    item_entry["BaseChamberSpeedMulti"] = r(pred)

    # Target: BaseFixSpeed
    z = 0.694420050598 + (0.0279009186458 * ((DeviationMax - 11.2954545455) / 1.6831996783)) + (-0.00678424168435 * ((DeviationCurve - 2.26818181818) / 0.296013457367)) + (-0.0228635703294 * ((RecoilForceBack - 244.863636364) / 42.3087090267)) + (-0.223732489049 * ((Weight - 1.21481818182) / 0.504026662026)) + (0.216144130557 * ((FactoredWeight - 1.95347489381) / 0.884257483672)) + (-0.0158083530412 * ((ErgoWeight - 80.0608249715) / 15.3775837237)) + (-0.00149269808835 * ((bFirerate - 893.181818182) / 146.973601947))
    pred = expm1_clamped(z)
    pred = min(max(pred, 0.775), 1.325)
    item_entry["BaseFixSpeed"] = r(pred)

    # Target: BaseMalfunctionChance
    z = 0.0403519372027 + (0.00474335611107 * ((bFirerate - 893.181818182) / 146.973601947)) + (-0.00210225372981 * ((RecoilPosZMult - 0.972727272727) / 0.0686348585025)) + (0.00210225372981 * ((shotgunDispersion - 1.36363636364) / 3.43174292512)) + (-0.000875537975573 * ((Ergonomics - 58.1818181818) / 15.1436646329)) + (0.0036418177132 * ((CameraSnap - 3.6) / 0.317661912903)) + (0.00429723023866 * ((IronSightRange - 50) / 13.0558241967)) + (-0.00220785555032 * ((DeviationMax - 11.2954545455) / 1.6831996783))
    pred = z*z if z >= 0 else 0.0
    pred = min(max(pred, 0.00035), 0.00365)
    item_entry["BaseMalfunctionChance"] = r(pred)

    # Target: BaseReloadSpeedMulti
    z = 0.917367055116 + (0.0148682189618 * ((FactoredWeight - 1.95347489381) / 0.884257483672)) + (-0.0378499979964 * ((Weight - 1.21481818182) / 0.504026662026)) + (0.0041135231056 * ((ErgoWeight - 80.0608249715) / 15.3775837237))
    pred = z
    pred = min(max(pred, 0.8425), 1.0075)
    item_entry["BaseReloadSpeedMulti"] = r(pred)

    # Target: BaseTorque
    z = -0.295924377029 + (0.834519923131 * ((ErgoWeight - 80.0608249715) / 15.3775837237)) + (-2.21599736187 * ((Weight - 1.21481818182) / 0.504026662026)) + (2.68118993223 * ((FactoredWeight - 1.95347489381) / 0.884257483672)) + (-0.449511418925 * ((RecoilReturnSpeedHandRotation - 3.10681818182) / 0.507062721274)) + (0.0244809050878 * ((CoolFactorGun - 3.14181818182) / 0.082794178739)) + (-0.0938900940035 * ((DeviationMax - 11.2954545455) / 1.6831996783)) + (0.325468839553 * ((RecoilDampingHandRotation - 0.844090909091) / 0.00576753524566))
    pred = z
    pred = min(max(pred, -2.4625), 2.2125)
    item_entry["BaseTorque"] = r(pred)

    # Target: CameraRecoil
    z = 0.198877530083 + (0.00114477077695 * ((RecoilCamera - 0.0322727272727) / 0.00516264395073)) + (0.00161934357421 * ((RecoilForceUp - 54.9545454545) / 9.46513829668)) + (-0.0062980075243 * ((RecoilReturnSpeedHandRotation - 3.10681818182) / 0.507062721274)) + (-0.00813537270982 * ((RecoilAngle - 90.4545454545) / 3.34021328561)) + (-0.000926516327433 * ((ErgoWeight - 80.0608249715) / 15.3775837237))
    pred = z*z if z >= 0 else 0.0
    pred = min(max(pred, 0.0175), 0.0725)
    item_entry["CameraRecoil"] = r(pred)

    # Target: CenterOfImpact
    z = 0.118648006331 + (0.0186547255514 * ((bFirerate - 893.181818182) / 146.973601947))
    pred = expm1_clamped(z)
    pred = min(max(pred, -0.0125), 0.2625)
    item_entry["CenterOfImpact"] = r(pred)

    # Target: Convergence
    z = 18.1957138547 + (4.12579309279 * ((CenterOfImpact - 0.191363636364) / 0.0762946116616)) + (-0.787492514002 * ((Ergonomics - 58.1818181818) / 15.1436646329)) + (-1.39357755686 * ((DeviationMax - 11.2954545455) / 1.6831996783)) + (-1.46595716916 * ((HRecoilPerErgo - 4.94555323825) / 3.28377322799)) + (-1.27312374713 * ((Velocity - 4.57636363636) / 11.3321323298))
    pred = z
    pred = min(max(pred, 8.275), 24.225)
    item_entry["Convergence"] = r(pred)

    # Target: CoolFactorGun
    z = 0.0990399326498 + (-8.70702993068e-12 * ((CoolFactorGunMods - 1.02302727273) / 0.0526847500949)) + (-0.0117945139732 * ((CoolFactorGun - 3.14181818182) / 0.082794178739))
    pred = expm1_clamped(z)
    pred = min(max(pred, 0.08), 0.52)
    item_entry["CoolFactorGun"] = r(pred)

    # Target: CoolFactorGunMods
    z = 1
    pred = z
    pred = min(max(pred, 0.999999), 1.000001)
    item_entry["CoolFactorGunMods"] = r(pred)

    # Target: Dispersion
    z = 8.8248428969 + (-0.705773096125 * ((DeviationCurve - 2.26818181818) / 0.296013457367)) + (0.442363122757 * ((RecolDispersion - 11.5454545455) / 3.701686013)) + (-0.401943802926 * ((shotgunDispersion - 1.36363636364) / 3.43174292512)) + (-0.312839134683 * ((bEffDist - 209.090909091) / 104.050210384))
    pred = z
    pred = min(max(pred, 4.65), 12.35)
    item_entry["Dispersion"] = r(pred)

    # Target: DurabilityBurnRatio
    z = 0.387745555477
    pred = z*z if z >= 0 else 0.0
    pred = min(max(pred, -0.012), 0.472)
    item_entry["DurabilityBurnRatio"] = r(pred)

    # Target: Ergonomics
    z = 4.40292177836 + (-0.237551050706 * ((FactoredWeight - 1.95347489381) / 0.884257483672)) + (0.233075986911 * ((Weight - 1.21481818182) / 0.504026662026)) + (0.00572811888173 * ((ErgoWeight - 80.0608249715) / 15.3775837237))
    pred = expm1_clamped(z)
    pred = min(max(pred, 69.2), 86.8)
    item_entry["Ergonomics"] = r(pred)

    # Target: HasShoulderContact
    z = 0.136363632805 + (-0.171587148359 * ((RecoilPosZMult - 0.972727272727) / 0.0686348585025)) + (0.171587148359 * ((shotgunDispersion - 1.36363636364) / 3.43174292512)) + (2.02717754257e-09 * ((CoolFactorGunMods - 1.02302727273) / 0.0526847500949)) + (-9.24759053681e-09 * ((HeatFactorByShot - 2.00681818182) / 0.31762451193)) + (-1.63095635383e-09 * ((Durability - 98.6363636364) / 2.22680885708)) + (1.72460333944e-09 * ((RecoilDampingHandRotation - 0.844090909091) / 0.00576753524566)) + (2.14478121026e-09 * ((bEffDist - 209.090909091) / 104.050210384))
    pred = z
    pred = min(max(pred, -0.05), 1.05)
    item_entry["HasShoulderContact"] = r(pred)

    # Target: HeatFactorByShot
    z = 1
    pred = z
    pred = min(max(pred, 0.999999), 1.000001)
    item_entry["HeatFactorByShot"] = r(pred)

    # Target: HeatFactorGun
    z = 0.455782515005 + (0.00145466773514 * ((HeatFactorByShot - 2.00681818182) / 0.31762451193)) + (0.0433080931178 * ((HeatFactorGun - 1.01639090909) / 0.0567916279769))
    pred = z*z if z >= 0 else 0.0
    pred = min(max(pred, 0.0275), 0.5225)
    item_entry["HeatFactorGun"] = r(pred)

    # Target: HipAccuracyRestorationDelay
    z = 0.2
    pred = z
    pred = min(max(pred, 0.199999), 0.200001)
    item_entry["HipAccuracyRestorationDelay"] = r(pred)

    # Target: HipAccuracyRestorationSpeed
    z = 7
    pred = z
    pred = min(max(pred, 6.999999), 7.000001)
    item_entry["HipAccuracyRestorationSpeed"] = r(pred)

    # Target: HipInnaccuracyGain
    z = 0.16
    pred = z
    pred = min(max(pred, 0.159999), 0.160001)
    item_entry["HipInnaccuracyGain"] = r(pred)

    # Target: HorizontalRecoil
    z = 117 + (9.33757510676 * ((RecoilAngle - 90.4545454545) / 3.34021328561)) + (-2.76183863268 * ((CameraSnap - 3.6) / 0.317661912903)) + (7.11868377403 * ((RecoilPosZMult - 0.972727272727) / 0.0686348585025)) + (-7.63292764488 * ((CenterOfImpact - 0.191363636364) / 0.0762946116616)) + (8.56794173433 * ((RecoilForceUp - 54.9545454545) / 9.46513829668))
    pred = z
    pred = min(max(pred, 70.95), 160.05)
    item_entry["HorizontalRecoil"] = r(pred)

    # Target: MaxChamberSpeed
    z = 1.49999999999 + (2.8519075317e-11 * ((DeviationMax - 11.2954545455) / 1.6831996783)) + (2.8133369785e-10 * ((Velocity - 4.57636363636) / 11.3321323298)) + (-2.40632167104e-10 * ((Durability - 98.6363636364) / 2.22680885708)) + (9.5971996663e-11 * ((ErgoWeight - 80.0608249715) / 15.3775837237)) + (-1.27850625578e-11 * ((Ergonomics - 58.1818181818) / 15.1436646329)) + (4.84131479452e-11 * ((bFirerate - 893.181818182) / 146.973601947)) + (9.76511625443e-11 * ((HeatFactorGun - 1.01639090909) / 0.0567916279769))
    pred = z
    pred = min(max(pred, 1.2375), 1.5125)
    item_entry["MaxChamberSpeed"] = r(pred)

    # Target: MinChamberSpeed
    z = 0.840087886941 + (-0.00792925116849 * ((RecoilForceBack - 244.863636364) / 42.3087090267)) + (0.00410597673115 * ((HeatFactorGun - 1.01639090909) / 0.0567916279769)) + (0.00463793387368 * ((AimPlane - 0.173636363636) / 0.0911814103136)) + (-0.00156618001845 * ((HeatFactorByShot - 2.00681818182) / 0.31762451193)) + (-0.00303856365063 * ((CenterOfImpact - 0.191363636364) / 0.0762946116616)) + (0.0511921039543 * ((Weight - 1.21481818182) / 0.504026662026)) + (-0.0463315274101 * ((FactoredWeight - 1.95347489381) / 0.884257483672))
    pred = z*z if z >= 0 else 0.0
    pred = min(max(pred, 0.6975), 0.7525)
    item_entry["MinChamberSpeed"] = r(pred)

    # Target: OffsetRotation
    z = 0.104134459305 + (-0.00033771643929 * ((AimPlane - 0.173636363636) / 0.0911814103136)) + (-3.24517218084e-05 * ((HeatFactorByShot - 2.00681818182) / 0.31762451193)) + (-0.00214662131808 * ((RecoilPosZMult - 0.972727272727) / 0.0686348585025)) + (0.00214662131808 * ((shotgunDispersion - 1.36363636364) / 3.43174292512)) + (-0.000253053578027 * ((CoolFactorGunMods - 1.02302727273) / 0.0526847500949)) + (-0.0044931679519 * ((Durability - 98.6363636364) / 2.22680885708)) + (-0.00692452269291 * ((DeviationCurve - 2.26818181818) / 0.296013457367))
    pred = z*z if z >= 0 else 0.0
    pred = min(max(pred, 0.00425), 0.02075)
    item_entry["OffsetRotation"] = r(pred)

    # Target: RecoilAngle
    z = 103.841541689 + (52.7029901211 * ((CameraSnap - 3.6) / 0.317661912903)) + (0.818183107614 * ((RecoilAngle - 90.4545454545) / 3.34021328561)) + (-1.05932257205 * ((RecoilForceBack - 244.863636364) / 42.3087090267)) + (-58.6436867861 * ((FactoredWeight - 1.95347489381) / 0.884257483672)) + (59.1182449827 * ((Weight - 1.21481818182) / 0.504026662026))
    pred = z
    pred = min(max(pred, 70), 290)
    item_entry["RecoilAngle"] = r(pred)

    # Target: RecoilDamping
    z = 0.850011242218 + (-0.00709990478923 * ((DeviationCurve - 2.26818181818) / 0.296013457367)) + (2.17373783717e-08 * ((RecoilCamera - 0.0322727272727) / 0.00516264395073)) + (0.00208694006201 * ((RecoilReturnPathOffsetHandRotation - 0.0100909090909) / 0.000416597790451)) + (7.88561116813e-06 * ((Velocity - 4.57636363636) / 11.3321323298)) + (-3.71039386415e-07 * ((Weight - 1.21481818182) / 0.504026662026))
    pred = z
    pred = min(max(pred, 0.797), 0.863)
    item_entry["RecoilDamping"] = r(pred)

    # Target: RecoilHandDamping
    z = 0.488140282686 + (0.0387403950919 * ((CameraSnap - 3.6) / 0.317661912903)) + (-0.000488677822451 * ((RecoilAngle - 90.4545454545) / 3.34021328561)) + (0.406224314267 * ((FactoredWeight - 1.95347489381) / 0.884257483672)) + (-0.38191864381 * ((Weight - 1.21481818182) / 0.504026662026)) + (0.00860679039154 * ((Velocity - 4.57636363636) / 11.3321323298))
    pred = z
    pred = min(max(pred, 0.3875), 0.6625)
    item_entry["RecoilHandDamping"] = r(pred)

    # Target: RecoilIntensity
    z = 0.217543536758 + (-0.00870512804559 * ((RecoilAngle - 90.4545454545) / 3.34021328561)) + (0.00374876095086 * ((CameraSnap - 3.6) / 0.317661912903)) + (0.00109450147706 * ((RecoilForceBack - 244.863636364) / 42.3087090267)) + (-0.0030610235909 * ((RecoilForceUp - 54.9545454545) / 9.46513829668)) + (-0.000320449786153 * ((CenterOfImpact - 0.191363636364) / 0.0762946116616))
    pred = z
    pred = min(max(pred, 0.19725), 0.25775)
    item_entry["RecoilIntensity"] = r(pred)

    # Target: SemiROF
    z = 357.232592416 + (-5.53865836672 * ((bFirerate - 893.181818182) / 146.973601947))
    pred = z
    pred = min(max(pred, 303), 457)
    item_entry["SemiROF"] = int(round(pred))

    # Target: ShotgunDispersion
    z = 1.36363636364
    pred = z
    pred = min(max(pred, 1.22727272727), 1.5)
    item_entry["ShotgunDispersion"] = r(pred)

    # Target: Velocity
    z = 0
    pred = z
    pred = min(max(pred, -13.065), 14.765)
    item_entry["Velocity"] = r(pred)

    # Target: VerticalRecoil
    z = 3.59535369051 + (0.148527584156 * ((RecoilAngle - 90.4545454545) / 3.34021328561)) + (-0.0179021200829 * ((CameraSnap - 3.6) / 0.317661912903)) + (0.0639254664601 * ((DeviationMax - 11.2954545455) / 1.6831996783)) + (-0.0454721744721 * ((CenterOfImpact - 0.191363636364) / 0.0762946116616)) + (-0.0241168801658 * ((DeviationCurve - 2.26818181818) / 0.296013457367))
    pred = expm1_clamped(z)
    pred = min(max(pred, 21.65), 51.35)
    item_entry["VerticalRecoil"] = r(pred)

    # Target: VisualMulti
    z = 0.837818968543 + (0.073090284546 * ((DeviationMax - 11.2954545455) / 1.6831996783)) + (-0.0497144754862 * ((Durability - 98.6363636364) / 2.22680885708)) + (0.0358600788556 * ((Velocity - 4.57636363636) / 11.3321323298)) + (0.0264358497416 * ((BaseMalfunctionChance - 0.1817) / 0.00813172798365)) + (0.0185852411431 * ((RecoilReturnSpeedHandRotation - 3.10681818182) / 0.507062721274)) + (0.0110342946193 * ((ErgoWeight - 80.0608249715) / 15.3775837237)) + (0.041850659122 * ((DeviationCurve - 2.26818181818) / 0.296013457367))
    pred = expm1_clamped(z)
    pred = min(max(pred, 1.055), 2.045)
    item_entry["VisualMulti"] = r(pred)

    # Target: WeapAccuracy
    z = 0
    pred = z
    pred = min(max(pred, -1e-06), 1e-06)
    item_entry["WeapAccuracy"] = r(pred)

    # Target: WeaponAllowADS
    z = 0.136363636364 + (-0.171587146256 * ((RecoilPosZMult - 0.972727272727) / 0.0686348585025)) + (0.171587146256 * ((shotgunDispersion - 1.36363636364) / 3.43174292512))
    pred = z
    pred = min(max(pred, -0.05), 1.05)
    item_entry["WeaponAllowADS"] = r(pred)

    # Target: Weight
    z = 1.21481818248 + (-7.84199119083e-09 * ((FactoredWeight - 1.95347489381) / 0.884257483672)) + (0.504026669376 * ((Weight - 1.21481818182) / 0.504026662026)) + (-2.88241798498e-10 * ((ErgoWeight - 80.0608249715) / 15.3775837237))
    pred = z
    pred = min(max(pred, 0.2545), 2.3555)
    item_entry["Weight"] = r(pred)

    return item_entry

# --- Shotguns (Gun) Formulas ---
def apply_shotguns_gun_formulas(item_entry: dict, base_data: dict, template: dict = None, context: dict = None) -> dict:
    """Auto-generated formulas for parent class: Shotguns (Gun)"""
    # Helper functions
    def to_f(x, d=0.0):
        try: return float(x)
        except: return d
    def r(x, d=3):
        try: return round(float(x), d)
        except: return x
    def expm1_clamped(z, cap=20.0):
        z = min(max(z, -cap), cap)
        return math.expm1(z)
    props = base_data.get("_props", base_data)

    # 1. Bind base features from props
    AimPlane = to_f(props.get("AimPlane", base_data.get("AimPlane", 0.0)))
    AimSensitivity = to_f(props.get("AimSensitivity", base_data.get("AimSensitivity", 0.0)))
    BaseMalfunctionChance = to_f(props.get("BaseMalfunctionChance", base_data.get("BaseMalfunctionChance", 0.0)))
    CameraSnap = to_f(props.get("CameraSnap", base_data.get("CameraSnap", 0.0)))
    CameraToWeaponAngleStep = to_f(props.get("CameraToWeaponAngleStep", base_data.get("CameraToWeaponAngleStep", 0.0)))
    CenterOfImpact = to_f(props.get("CenterOfImpact", base_data.get("CenterOfImpact", 0.0)))
    CoolFactorGun = to_f(props.get("CoolFactorGun", base_data.get("CoolFactorGun", 0.0)))
    CoolFactorGunMods = to_f(props.get("CoolFactorGunMods", base_data.get("CoolFactorGunMods", 0.0)))
    DeviationCurve = to_f(props.get("DeviationCurve", base_data.get("DeviationCurve", 0.0)))
    DeviationMax = to_f(props.get("DeviationMax", base_data.get("DeviationMax", 0.0)))
    Durability = to_f(props.get("Durability", base_data.get("Durability", 0.0)))
    DurabilityBurnRatio = to_f(props.get("DurabilityBurnRatio", base_data.get("DurabilityBurnRatio", 0.0)))
    Ergonomics = to_f(props.get("Ergonomics", base_data.get("Ergonomics", 0.0)))
    HeatFactorByShot = to_f(props.get("HeatFactorByShot", base_data.get("HeatFactorByShot", 0.0)))
    HeatFactorGun = to_f(props.get("HeatFactorGun", base_data.get("HeatFactorGun", 0.0)))
    HipAccuracyRestorationDelay = to_f(props.get("HipAccuracyRestorationDelay", base_data.get("HipAccuracyRestorationDelay", 0.0)))
    HipAccuracyRestorationSpeed = to_f(props.get("HipAccuracyRestorationSpeed", base_data.get("HipAccuracyRestorationSpeed", 0.0)))
    HipInnaccuracyGain = to_f(props.get("HipInnaccuracyGain", base_data.get("HipInnaccuracyGain", 0.0)))
    IronSightRange = to_f(props.get("IronSightRange", base_data.get("IronSightRange", 0.0)))
    MaxRepairDegradation = to_f(props.get("MaxRepairDegradation", base_data.get("MaxRepairDegradation", 0.0)))
    MinRepairDegradation = to_f(props.get("MinRepairDegradation", base_data.get("MinRepairDegradation", 0.0)))
    RecoilAngle = to_f(props.get("RecoilAngle", base_data.get("RecoilAngle", 0.0)))
    RecoilCamera = to_f(props.get("RecoilCamera", base_data.get("RecoilCamera", 0.0)))
    RecoilCategoryMultiplierHandRotation = to_f(props.get("RecoilCategoryMultiplierHandRotation", base_data.get("RecoilCategoryMultiplierHandRotation", 0.0)))
    RecoilDampingHandRotation = to_f(props.get("RecoilDampingHandRotation", base_data.get("RecoilDampingHandRotation", 0.0)))
    RecoilForceBack = to_f(props.get("RecoilForceBack", base_data.get("RecoilForceBack", 0.0)))
    RecoilForceUp = to_f(props.get("RecoilForceUp", base_data.get("RecoilForceUp", 0.0)))
    RecoilPosZMult = to_f(props.get("RecoilPosZMult", base_data.get("RecoilPosZMult", 0.0)))
    RecoilReturnPathDampingHandRotation = to_f(props.get("RecoilReturnPathDampingHandRotation", base_data.get("RecoilReturnPathDampingHandRotation", 0.0)))
    RecoilReturnPathOffsetHandRotation = to_f(props.get("RecoilReturnPathOffsetHandRotation", base_data.get("RecoilReturnPathOffsetHandRotation", 0.0)))
    RecoilReturnSpeedHandRotation = to_f(props.get("RecoilReturnSpeedHandRotation", base_data.get("RecoilReturnSpeedHandRotation", 0.0)))
    RecolDispersion = to_f(props.get("RecolDispersion", base_data.get("RecolDispersion", 0.0)))
    ShotgunDispersion = to_f(props.get("ShotgunDispersion", base_data.get("ShotgunDispersion", 0.0)))
    SightingRange = to_f(props.get("SightingRange", base_data.get("SightingRange", 0.0)))
    SingleFireRate = to_f(props.get("SingleFireRate", base_data.get("SingleFireRate", 0.0)))
    Velocity = to_f(props.get("Velocity", base_data.get("Velocity", 0.0)))
    Weight = to_f(props.get("Weight", base_data.get("Weight", 0.0)))
    bEffDist = to_f(props.get("bEffDist", base_data.get("bEffDist", 0.0)))
    bFirerate = to_f(props.get("bFirerate", base_data.get("bFirerate", 0.0)))
    bHearDist = to_f(props.get("bHearDist", base_data.get("bHearDist", 0.0)))
    shotgunDispersion = to_f(props.get("shotgunDispersion", base_data.get("shotgunDispersion", 0.0)))

    # 2. Engineer new features
    name_str = str(base_data.get('Name', '') or base_data.get('shortName', '')).lower()
    mm_match = re.search(r'(\d+)mm', name_str)
    inch_match = re.search(r'(\d+\.?\d*)"', name_str)
    BarrelLengthMM = float(mm_match.group(1)) if mm_match else (float(inch_match.group(1)) * 25.4 if inch_match else 0.0)
    caliber_match = re.search(r'(\d+\.?\d*)x', name_str)
    CaliberNumeric = float(caliber_match.group(1)) if caliber_match else 0.0
    position_mult = 0.0
    if 'suppressor' in name_str or 'muzzle' in name_str or 'barrel' in name_str: position_mult = -1.0
    elif 'stock' in name_str or 'buttpad' in name_str: position_mult = 1.0
    Torque = Weight * position_mult * 10.0
    FactoredWeight = pow(Weight * 1.5, 1.1) if Weight > 0 else 0.0
    base_ergo_calc_val = Ergonomics / (Weight * 100) if Weight > 0 else 0.0
    ErgoWeight = pow(max(0, base_ergo_calc_val), 0.35) * 100.0
    VRecoilPerErgo = RecoilForceUp / Ergonomics if Ergonomics != 0 else 0.0
    HRecoilPerErgo = RecoilForceBack / Ergonomics if Ergonomics != 0 else 0.0
    dura = to_f(props.get('MaxDurability', base_data.get('MaxDurability', 100.0)))
    dura_factor = 2.0 - (dura / 100.0) if dura > 0 else 2.0
    DurabilityMalfRisk = pow(max(0, dura_factor), 3.0)

    # 3. Calculate all target values

    # Target: AllowOverheat
    z = 1
    pred = z
    pred = min(max(pred, 0.999999), 1.000001)
    item_entry["AllowOverheat"] = r(pred)

    # Target: AutoROF
    z = 202.322317406 + (303.643670819 * ((bFirerate - 200) / 303.644529014)) + (-4.47895991108 * ((SingleFireRate - 422.142857143) / 53.7425837314))
    pred = z
    pred = min(max(pred, -13.5), 943.5)
    item_entry["AutoROF"] = int(round(pred))

    # Target: BaseChamberCheckSpeed
    z = 0.700121924081 + (-0.0199958009827 * ((DurabilityBurnRatio - 1.13928571429) / 0.0386309065228)) + (-0.00721960499474 * ((HRecoilPerErgo - 11.0628691711) / 3.44436494484)) + (0.00357086682145 * ((RecolDispersion - 13.7857142857) / 5.42716147103)) + (-0.000880879975818 * ((CameraSnap - 2.48571428571) / 0.269542318059)) + (0.0133889453926 * ((RecoilForceBack - 484.857142857) / 130.95247619)) + (-0.00934447795664 * ((HeatFactorByShot - 6.79521428571) / 2.66473837308)) + (-0.0157574755838 * ((CoolFactorGunMods - 1.02782857143) / 0.0102055607091))
    pred = expm1_clamped(z)
    pred = min(max(pred, 0.7485), 1.2215)
    item_entry["BaseChamberCheckSpeed"] = r(pred)

    # Target: BaseChamberSpeedMulti
    z = 0.997929409609 + (0.0527336497913 * ((RecoilReturnPathOffsetHandRotation - 0.0148571428571) / 0.000515078753638)) + (-1.21230366479e-08 * ((Ergonomics - 44.6428571429) / 5.72721751011)) + (0.026687950546 * ((HeatFactorGun - 0.976557142857) / 0.0231946026445)) + (-0.0710639648717 * ((RecoilForceUp - 348.857142857) / 117.708997801)) + (0.0548967652536 * ((bHearDist - 23.5714285714) / 35.6885621648)) + (0.104273485791 * ((RecolDispersion - 13.7857142857) / 5.42716147103)) + (0.194266708284 * ((AimPlane - 0.0922142857143) / 0.0536299204488))
    pred = z*z if z >= 0 else 0.0
    pred = min(max(pred, 0.825), 1.375)
    item_entry["BaseChamberSpeedMulti"] = r(pred)

    # Target: BaseFixSpeed
    z = 0.893640149454 + (-0.0584730863105 * ((VRecoilPerErgo - 7.8178028417) / 2.29272734445)) + (1.36223168685 * ((FactoredWeight - 2.61688512967) / 1.31560398731)) + (-1.32062327682 * ((Weight - 1.58371428571) / 0.717996759699)) + (-0.0576401743645 * ((CameraSnap - 2.48571428571) / 0.269542318059)) + (-0.16181183885 * ((Velocity - 0.707857142857) / 1.13801944856)) + (-0.0474424571077 * ((RecoilForceUp - 348.857142857) / 117.708997801)) + (-0.183348070268 * ((HeatFactorGun - 0.976557142857) / 0.0231946026445))
    pred = z
    pred = min(max(pred, 0.575), 1.125)
    item_entry["BaseFixSpeed"] = r(pred)

    # Target: BaseMalfunctionChance
    z = 0.00167263688281 + (-0.0015592197821 * ((HeatFactorByShot - 6.79521428571) / 2.66473837308)) + (0.000403056812373 * ((CenterOfImpact - 0.405714285714) / 0.222829668636)) + (0.00180129874209 * ((BaseMalfunctionChance - 0.264475357143) / 0.0275013954493)) + (0.00108752126121 * ((bEffDist - 76.4285714286) / 12.3097770997)) + (-0.00108752126121 * ((shotgunDispersion - 15.7142857143) / 8.20651806648)) + (0.000593682335199 * ((bHearDist - 23.5714285714) / 35.6885621648)) + (-2.6176243327e-08 * ((CoolFactorGun - 4.176) / 0.541540659336))
    pred = z
    pred = min(max(pred, -0.000225), 0.004725)
    item_entry["BaseMalfunctionChance"] = r(pred)

    # Target: BaseReloadSpeedMulti
    z = 1.04934765502 + (-1.0084263921 * ((FactoredWeight - 2.61688512967) / 1.31560398731)) + (0.87734741624 * ((Weight - 1.58371428571) / 0.717996759699)) + (-0.0945319714712 * ((ErgoWeight - 66.8356904001) / 10.0699535444))
    pred = z*z if z >= 0 else 0.0
    pred = min(max(pred, 0.8435), 1.4265)
    item_entry["BaseReloadSpeedMulti"] = r(pred)

    # Target: BaseTorque
    z = -1.00000000056 + (1.53225603874 * ((RecoilReturnPathOffsetHandRotation - 0.0148571428571) / 0.000515078753638)) + (2.39119615418 * ((HeatFactorGun - 0.976557142857) / 0.0231946026445)) + (-2.12731323856e-09 * ((RecoilForceUp - 348.857142857) / 117.708997801)) + (5.86418878075e-09 * ((AimPlane - 0.0922142857143) / 0.0536299204488)) + (-5.45368405207e-09 * ((CenterOfImpact - 0.405714285714) / 0.222829668636)) + (-1.07712472617e-09 * ((Ergonomics - 44.6428571429) / 5.72721751011)) + (1.30357325754 * ((Velocity - 0.707857142857) / 1.13801944856))
    pred = z
    pred = min(max(pred, -10.625), 3.125)
    item_entry["BaseTorque"] = r(pred)

    # Target: CameraRecoil
    z = 0.342038717572 + (-0.0224692871424 * ((CenterOfImpact - 0.405714285714) / 0.222829668636)) + (-0.0107671070882 * ((ErgoWeight - 66.8356904001) / 10.0699535444)) + (-1.02620032909 * ((Weight - 1.58371428571) / 0.717996759699)) + (0.985769861087 * ((FactoredWeight - 2.61688512967) / 1.31560398731)) + (0.000683433163002 * ((Velocity - 0.707857142857) / 1.13801944856))
    pred = z*z if z >= 0 else 0.0
    pred = min(max(pred, 0.0635), 0.2065)
    item_entry["CameraRecoil"] = r(pred)

    # Target: CenterOfImpact
    z = 0.443797821389 + (-0.156116560697 * ((bFirerate - 200) / 303.644529014)) + (-0.00388894559767 * ((SingleFireRate - 422.142857143) / 53.7425837314))
    pred = z*z if z >= 0 else 0.0
    pred = min(max(pred, -0.025), 0.525)
    item_entry["CenterOfImpact"] = r(pred)

    # Target: Convergence
    z = 7.50917756174 + (-1.49216377153 * ((RecoilCamera - 0.06) / 0.00925820099773)) + (2.17331927025 * ((Velocity - 0.707857142857) / 1.13801944856)) + (0.527522806152 * ((RecoilDampingHandRotation - 0.841428571429) / 0.015971914125)) + (-0.190291460921 * ((RecoilReturnPathOffsetHandRotation - 0.0148571428571) / 0.000515078753638)) + (-1.15105400998 * ((FactoredWeight - 2.61688512967) / 1.31560398731))
    pred = z
    pred = min(max(pred, 1.5), 12.5)
    item_entry["Convergence"] = r(pred)

    # Target: CoolFactorGun
    z = 0.498139324371 + (0.428587531948 * ((CoolFactorGun - 4.176) / 0.541540659336)) + (-0.0849429448352 * ((CoolFactorGunMods - 1.02782857143) / 0.0102055607091))
    pred = z*z if z >= 0 else 0.0
    pred = min(max(pred, -0.183), 6.043)
    item_entry["CoolFactorGun"] = r(pred)

    # Target: CoolFactorGunMods
    z = 0.693147182867 + (6.47217293744e-09 * ((CoolFactorGun - 4.176) / 0.541540659336)) + (-2.72681453028e-09 * ((CoolFactorGunMods - 1.02782857143) / 0.0102055607091))
    pred = expm1_clamped(z)
    pred = min(max(pred, 0.999), 1.021)
    item_entry["CoolFactorGunMods"] = r(pred)

    # Target: Dispersion
    z = 1.77602240951 + (0.513194358539 * ((CenterOfImpact - 0.405714285714) / 0.222829668636)) + (-0.260702823472 * ((RecolDispersion - 13.7857142857) / 5.42716147103)) + (-0.259150222993 * ((shotgunDispersion - 15.7142857143) / 8.20651806648)) + (0.192262667215 * ((bEffDist - 76.4285714286) / 12.3097770997))
    pred = expm1_clamped(z)
    pred = min(max(pred, 0.45), 12.55)
    item_entry["Dispersion"] = r(pred)

    # Target: DurabilityBurnRatio
    z = 0.40583309763
    pred = expm1_clamped(z)
    pred = min(max(pred, 0.055), 1.045)
    item_entry["DurabilityBurnRatio"] = r(pred)

    # Target: EnableExtraBSGVisRecoil
    z = 0.719675881044 + (0.113612075755 * ((CameraSnap - 2.50769230769) / 0.267356110723)) + (4.57871293912 * ((RecoilForceUp - 353) / 121.164859084)) + (0.624684629702 * ((RecoilReturnPathOffsetHandRotation - 0.0148461538462) / 0.000532938710021)) + (-1.94984480367 * ((Ergonomics - 44.6923076923) / 5.94053371579)) + (-3.86445107851 * ((VRecoilPerErgo - 7.90343802532) / 2.35760154285))
    pred = z
    pred = min(max(pred, -0.05), 1.05)
    item_entry["EnableExtraBSGVisRecoil"] = r(pred)

    # Target: Ergonomics
    z = 80.0000000035 + (3.50940717795e-09 * ((Ergonomics - 44.6428571429) / 5.72721751011)) + (-4.54920909905e-09 * ((ErgoWeight - 66.8356904001) / 10.0699535444)) + (-3.45518463083e-09 * ((Weight - 1.58371428571) / 0.717996759699))
    pred = z
    pred = min(max(pred, 79.6), 88.4)
    item_entry["Ergonomics"] = r(pred)

    # Target: HasShoulderContact
    z = 0
    pred = z
    pred = min(max(pred, -0.05), 1.05)
    item_entry["HasShoulderContact"] = r(pred)

    # Target: HeatFactorByShot
    z = 0.693147180531 + (1.53525886152e-10 * ((HeatFactorByShot - 6.79521428571) / 2.66473837308)) + (5.84921129969e-11 * ((HeatFactorGun - 0.976557142857) / 0.0231946026445))
    pred = expm1_clamped(z)
    pred = min(max(pred, 0.469), 12.151)
    item_entry["HeatFactorByShot"] = r(pred)

    # Target: HeatFactorGun
    z = 0.579290317227 + (0.0799982360855 * ((HeatFactorByShot - 6.79521428571) / 2.66473837308)) + (0.00121725712977 * ((HeatFactorGun - 0.976557142857) / 0.0231946026445))
    pred = z
    pred = min(max(pred, 0.3705), 1.0195)
    item_entry["HeatFactorGun"] = r(pred)

    # Target: HipAccuracyRestorationDelay
    z = 0.2
    pred = z
    pred = min(max(pred, 0.199999), 0.200001)
    item_entry["HipAccuracyRestorationDelay"] = r(pred)

    # Target: HipAccuracyRestorationSpeed
    z = 7
    pred = z
    pred = min(max(pred, 6.999999), 7.000001)
    item_entry["HipAccuracyRestorationSpeed"] = r(pred)

    # Target: HipInnaccuracyGain
    z = 0.4
    pred = z*z if z >= 0 else 0.0
    pred = min(max(pred, 0.159999), 0.160001)
    item_entry["HipInnaccuracyGain"] = r(pred)

    # Target: HorizontalRecoil
    z = 5.8968760799 + (0.167831636605 * ((CenterOfImpact - 0.405714285714) / 0.222829668636)) + (-0.218932546801 * ((ErgoWeight - 66.8356904001) / 10.0699535444)) + (-0.0176421696936 * ((RecoilReturnSpeedHandRotation - 2.17142857143) / 0.504874201345)) + (-0.00933088477381 * ((Velocity - 0.707857142857) / 1.13801944856)) + (-0.203915653132 * ((Weight - 1.58371428571) / 0.717996759699))
    pred = expm1_clamped(z)
    pred = min(max(pred, 227), 513)
    item_entry["HorizontalRecoil"] = r(pred)

    # Target: MaxChamberSpeed
    z = 0.882638651428 + (0.0678411600391 * ((RecoilAngle - 90.3571428571) / 1.28769688409)) + (-0.000388055913875 * ((RecoilReturnPathOffsetHandRotation - 0.0148571428571) / 0.000515078753638)) + (-0.166059673502 * ((RecoilForceUp - 348.857142857) / 117.708997801)) + (-0.0853359466033 * ((RecoilCamera - 0.06) / 0.00925820099773)) + (0.136984468698 * ((VRecoilPerErgo - 7.8178028417) / 2.29272734445)) + (0.0582301833861 * ((AimPlane - 0.0922142857143) / 0.0536299204488)) + (-0.0806562298202 * ((CenterOfImpact - 0.405714285714) / 0.222829668636))
    pred = expm1_clamped(z)
    pred = min(max(pred, 0.95), 2.05)
    item_entry["MaxChamberSpeed"] = r(pred)

    # Target: MinChamberSpeed
    z = 0.805693627153 + (-0.758440819275 * ((FactoredWeight - 2.61688512967) / 1.31560398731)) + (0.724973100432 * ((Weight - 1.58371428571) / 0.717996759699)) + (-0.0585204713839 * ((ErgoWeight - 66.8356904001) / 10.0699535444)) + (-0.00644740096692 * ((RecoilForceUp - 348.857142857) / 117.708997801)) + (-0.0310770789483 * ((RecoilCategoryMultiplierHandRotation - 0.215714285714) / 0.0349927106112)) + (0.031089747854 * ((RecoilReturnSpeedHandRotation - 2.17142857143) / 0.504874201345)) + (-0.0114743072718 * ((SingleFireRate - 422.142857143) / 53.7425837314))
    pred = z*z if z >= 0 else 0.0
    pred = min(max(pred, 0.54), 0.76)
    item_entry["MinChamberSpeed"] = r(pred)

    # Target: OffsetRotation
    z = 0.0141290993537 + (-0.00303564216082 * ((RecoilForceBack - 484.857142857) / 130.95247619)) + (0.00426525172932 * ((DurabilityBurnRatio - 1.13928571429) / 0.0386309065228)) + (0.000183453704983 * ((HRecoilPerErgo - 11.0628691711) / 3.44436494484)) + (0.00722284633211 * ((RecolDispersion - 13.7857142857) / 5.42716147103)) + (0.00474706449062 * ((CoolFactorGun - 4.176) / 0.541540659336)) + (-0.00573807910624 * ((bHearDist - 23.5714285714) / 35.6885621648)) + (-0.00383319290486 * ((bFirerate - 200) / 303.644529014))
    pred = z
    pred = min(max(pred, 0.0108), 0.0152)
    item_entry["OffsetRotation"] = r(pred)

    # Target: RecoilAngle
    z = 82.5704247021 + (10.4049919387 * ((ErgoWeight - 66.8356904001) / 10.0699535444)) + (1.76997542889 * ((RecoilAngle - 90.3571428571) / 1.28769688409)) + (-1.73877583395 * ((VRecoilPerErgo - 7.8178028417) / 2.29272734445)) + (-2.30870203284 * ((Ergonomics - 44.6428571429) / 5.72721751011)) + (7.59145307462 * ((Weight - 1.58371428571) / 0.717996759699))
    pred = z
    pred = min(max(pred, 69), 91)
    item_entry["RecoilAngle"] = r(pred)

    # Target: RecoilDamping
    z = 0.845321774531 + (-0.00980232472053 * ((RecoilReturnSpeedHandRotation - 2.17142857143) / 0.504874201345)) + (0.0080682251831 * ((RecoilCategoryMultiplierHandRotation - 0.215714285714) / 0.0349927106112)) + (0.00213372843075 * ((RecoilCamera - 0.06) / 0.00925820099773)) + (-0.00458718059145 * ((RecoilForceBack - 484.857142857) / 130.95247619)) + (0.00224209819455 * ((RecoilAngle - 90.3571428571) / 1.28769688409))
    pred = z
    pred = min(max(pred, 0.8075), 0.8625)
    item_entry["RecoilDamping"] = r(pred)

    # Target: RecoilHandDamping
    z = 0.511229083414 + (0.0286110361517 * ((RecoilForceBack - 484.857142857) / 130.95247619)) + (-0.0496863139875 * ((HRecoilPerErgo - 11.0628691711) / 3.44436494484)) + (0.0105975604351 * ((CenterOfImpact - 0.405714285714) / 0.222829668636)) + (-0.0820611685638 * ((ErgoWeight - 66.8356904001) / 10.0699535444)) + (-0.0792731507123 * ((Weight - 1.58371428571) / 0.717996759699))
    pred = z
    pred = min(max(pred, 0.42025), 0.52475)
    item_entry["RecoilHandDamping"] = r(pred)

    # Target: RecoilIntensity
    z = 0.579692320465 + (0.0295185575531 * ((RecoilForceBack - 484.857142857) / 130.95247619)) + (0.171015292466 * ((ErgoWeight - 66.8356904001) / 10.0699535444)) + (-0.0538828295001 * ((CenterOfImpact - 0.405714285714) / 0.222829668636)) + (0.05317830218 * ((HRecoilPerErgo - 11.0628691711) / 3.44436494484)) + (0.157249935516 * ((Weight - 1.58371428571) / 0.717996759699))
    pred = z*z if z >= 0 else 0.0
    pred = min(max(pred, 0.16225), 0.88275)
    item_entry["RecoilIntensity"] = r(pred)

    # Target: SemiROF
    z = 422.142817542 + (53.7425132443 * ((SingleFireRate - 422.142857143) / 53.7425837314)) + (2.94225748736e-05 * ((bFirerate - 200) / 303.644529014))
    pred = z
    pred = min(max(pred, 324), 456)
    item_entry["SemiROF"] = int(round(pred))

    # Target: ShotgunDispersion
    z = 0.928571428571
    pred = z
    pred = min(max(pred, 0.835714285714), 1.02142857143)
    item_entry["ShotgunDispersion"] = r(pred)

    # Target: Velocity
    z = -0
    pred = z
    pred = min(max(pred, -9.765), 0.465)
    item_entry["Velocity"] = r(pred)

    # Target: VerticalRecoil
    z = 201.671692907 + (76.1111064967 * ((RecoilCamera - 0.06) / 0.00925820099773)) + (12.4547578356 * ((VRecoilPerErgo - 7.8178028417) / 2.29272734445)) + (0.763221059245 * ((RecoilDampingHandRotation - 0.841428571429) / 0.015971914125)) + (-11.3536647428 * ((Ergonomics - 44.6428571429) / 5.72721751011)) + (-25.8807984374 * ((HRecoilPerErgo - 11.0628691711) / 3.44436494484))
    pred = z
    pred = min(max(pred, 98.25), 466.75)
    item_entry["VerticalRecoil"] = r(pred)

    # Target: VisualMulti
    z = 1.00036937721 + (0.167689817265 * ((SingleFireRate - 422.142857143) / 53.7425837314)) + (-0.193131275017 * ((RecoilCategoryMultiplierHandRotation - 0.215714285714) / 0.0349927106112)) + (0.0426203552348 * ((RecoilDampingHandRotation - 0.841428571429) / 0.015971914125)) + (-0.100933926028 * ((CoolFactorGunMods - 1.02782857143) / 0.0102055607091)) + (-0.00415456540897 * ((CenterOfImpact - 0.405714285714) / 0.222829668636)) + (-0.0377582067718 * ((Velocity - 0.707857142857) / 1.13801944856)) + (-0.0982842306698 * ((Weight - 1.58371428571) / 0.717996759699))
    pred = expm1_clamped(z)
    pred = min(max(pred, 0.7675), 2.5825)
    item_entry["VisualMulti"] = r(pred)

    # Target: WeapAccuracy
    z = 0
    pred = z
    pred = min(max(pred, -1e-06), 1e-06)
    item_entry["WeapAccuracy"] = r(pred)

    # Target: WeaponAllowADS
    z = 0
    pred = z
    pred = min(max(pred, -1e-06), 1e-06)
    item_entry["WeaponAllowADS"] = r(pred)

    # Target: Weight
    z = 1.58371429068 + (0.717997232048 * ((Weight - 1.58371428571) / 0.717996759699)) + (-4.43176598573e-07 * ((FactoredWeight - 2.61688512967) / 1.31560398731)) + (3.78493366906e-09 * ((ErgoWeight - 66.8356904001) / 10.0699535444))
    pred = z
    pred = min(max(pred, 0.623), 3.637)
    item_entry["Weight"] = r(pred)

    return item_entry

# --- Sights (Mod) Formulas ---
def apply_sights_mod_formulas(item_entry: dict, base_data: dict, template: dict = None, context: dict = None) -> dict:
    """Auto-generated formulas for parent class: Sights (Mod)"""
    # Helper functions
    def to_f(x, d=0.0):
        try: return float(x)
        except: return d
    def r(x, d=3):
        try: return round(float(x), d)
        except: return x
    def expm1_clamped(z, cap=20.0):
        z = min(max(z, -cap), cap)
        return math.expm1(z)
    props = base_data.get("_props", base_data)

    # 1. Bind base features from props
    Accuracy = to_f(props.get("Accuracy", base_data.get("Accuracy", 0.0)))
    AdjustableOpticSensitivity = to_f(props.get("AdjustableOpticSensitivity", base_data.get("AdjustableOpticSensitivity", 0.0)))
    AdjustableOpticSensitivityMax = to_f(props.get("AdjustableOpticSensitivityMax", base_data.get("AdjustableOpticSensitivityMax", 0.0)))
    Durability = to_f(props.get("Durability", base_data.get("Durability", 0.0)))
    EffectiveDistance = to_f(props.get("EffectiveDistance", base_data.get("EffectiveDistance", 0.0)))
    Ergonomics = to_f(props.get("Ergonomics", base_data.get("Ergonomics", 0.0)))
    Loudness = to_f(props.get("Loudness", base_data.get("Loudness", 0.0)))
    Recoil = to_f(props.get("Recoil", base_data.get("Recoil", 0.0)))
    RecoilForceBack = to_f(props.get("RecoilForceBack", base_data.get("RecoilForceBack", 0.0)))
    RecoilForceUp = to_f(props.get("RecoilForceUp", base_data.get("RecoilForceUp", 0.0)))
    SightingRange = to_f(props.get("SightingRange", base_data.get("SightingRange", 0.0)))
    Velocity = to_f(props.get("Velocity", base_data.get("Velocity", 0.0)))
    Weight = to_f(props.get("Weight", base_data.get("Weight", 0.0)))

    # 2. Engineer new features
    name_str = str(base_data.get('Name', '') or base_data.get('shortName', '')).lower()
    mm_match = re.search(r'(\d+)mm', name_str)
    inch_match = re.search(r'(\d+\.?\d*)"', name_str)
    BarrelLengthMM = float(mm_match.group(1)) if mm_match else (float(inch_match.group(1)) * 25.4 if inch_match else 0.0)
    caliber_match = re.search(r'(\d+\.?\d*)x', name_str)
    CaliberNumeric = float(caliber_match.group(1)) if caliber_match else 0.0
    position_mult = 0.0
    if 'suppressor' in name_str or 'muzzle' in name_str or 'barrel' in name_str: position_mult = -1.0
    elif 'stock' in name_str or 'buttpad' in name_str: position_mult = 1.0
    Torque = Weight * position_mult * 10.0
    FactoredWeight = pow(Weight * 1.5, 1.1) if Weight > 0 else 0.0
    base_ergo_calc_val = Ergonomics / (Weight * 100) if Weight > 0 else 0.0
    ErgoWeight = pow(max(0, base_ergo_calc_val), 0.35) * 100.0
    VRecoilPerErgo = RecoilForceUp / Ergonomics if Ergonomics != 0 else 0.0
    HRecoilPerErgo = RecoilForceBack / Ergonomics if Ergonomics != 0 else 0.0
    dura = to_f(props.get('MaxDurability', base_data.get('MaxDurability', 100.0)))
    dura_factor = 2.0 - (dura / 100.0) if dura > 0 else 2.0
    DurabilityMalfRisk = pow(max(0, dura_factor), 3.0)

    # 3. Calculate all target values

    # Target: Accuracy
    z = 0.600609756098
    pred = z
    pred = min(max(pred, -32.75), 27.75)
    item_entry["Accuracy"] = r(pred)

    # Target: AimSpeed
    z = -6.73481221274 + (-8.59676907916 * ((SightingRange - 503.125) / 518.928809544)) + (-3.11366813894 * ((FactoredWeight - 0.623487459457) / 0.417996523013)) + (1.66087303003 * ((Weight - 0.4256875) / 0.262919716537)) + (3.26132089263 * ((Ergonomics - -3.2734375) / 2.1793234463)) + (3.35877894066 * ((AdjustableOpticSensitivity - 0.069209375) / 0.166716823647))
    pred = z
    pred = min(max(pred, -52.3), 20.3)
    item_entry["AimSpeed"] = r(pred)

    # Target: Ergonomics
    z = 0
    pred = z
    pred = min(max(pred, -1e-06), 1e-06)
    item_entry["Ergonomics"] = r(pred)

    # Target: HorizontalRecoil
    z = 0
    pred = z
    pred = min(max(pred, -1e-06), 1e-06)
    item_entry["HorizontalRecoil"] = r(pred)

    # Target: VerticalRecoil
    z = 0
    pred = z
    pred = min(max(pred, -1e-06), 1e-06)
    item_entry["VerticalRecoil"] = r(pred)

    # Target: Weight
    z = 0.425687499955 + (0.262919715146 * ((Weight - 0.4256875) / 0.262919716537)) + (1.41946134454e-09 * ((FactoredWeight - 0.623487459457) / 0.417996523013))
    pred = z
    pred = min(max(pred, -0.0294), 1.1674)
    item_entry["Weight"] = r(pred)

    return item_entry

# --- SniperRifles (Gun) Formulas ---
def apply_sniperrifles_gun_formulas(item_entry: dict, base_data: dict, template: dict = None, context: dict = None) -> dict:
    """Auto-generated formulas for parent class: SniperRifles (Gun)"""
    # Helper functions
    def to_f(x, d=0.0):
        try: return float(x)
        except: return d
    def r(x, d=3):
        try: return round(float(x), d)
        except: return x
    def expm1_clamped(z, cap=20.0):
        z = min(max(z, -cap), cap)
        return math.expm1(z)
    props = base_data.get("_props", base_data)

    # 1. Bind base features from props
    AimPlane = to_f(props.get("AimPlane", base_data.get("AimPlane", 0.0)))
    AimSensitivity = to_f(props.get("AimSensitivity", base_data.get("AimSensitivity", 0.0)))
    BaseMalfunctionChance = to_f(props.get("BaseMalfunctionChance", base_data.get("BaseMalfunctionChance", 0.0)))
    CameraSnap = to_f(props.get("CameraSnap", base_data.get("CameraSnap", 0.0)))
    CameraToWeaponAngleStep = to_f(props.get("CameraToWeaponAngleStep", base_data.get("CameraToWeaponAngleStep", 0.0)))
    CenterOfImpact = to_f(props.get("CenterOfImpact", base_data.get("CenterOfImpact", 0.0)))
    CoolFactorGun = to_f(props.get("CoolFactorGun", base_data.get("CoolFactorGun", 0.0)))
    CoolFactorGunMods = to_f(props.get("CoolFactorGunMods", base_data.get("CoolFactorGunMods", 0.0)))
    DeviationCurve = to_f(props.get("DeviationCurve", base_data.get("DeviationCurve", 0.0)))
    DeviationMax = to_f(props.get("DeviationMax", base_data.get("DeviationMax", 0.0)))
    Durability = to_f(props.get("Durability", base_data.get("Durability", 0.0)))
    DurabilityBurnRatio = to_f(props.get("DurabilityBurnRatio", base_data.get("DurabilityBurnRatio", 0.0)))
    Ergonomics = to_f(props.get("Ergonomics", base_data.get("Ergonomics", 0.0)))
    HeatFactorByShot = to_f(props.get("HeatFactorByShot", base_data.get("HeatFactorByShot", 0.0)))
    HeatFactorGun = to_f(props.get("HeatFactorGun", base_data.get("HeatFactorGun", 0.0)))
    HipAccuracyRestorationDelay = to_f(props.get("HipAccuracyRestorationDelay", base_data.get("HipAccuracyRestorationDelay", 0.0)))
    HipAccuracyRestorationSpeed = to_f(props.get("HipAccuracyRestorationSpeed", base_data.get("HipAccuracyRestorationSpeed", 0.0)))
    HipInnaccuracyGain = to_f(props.get("HipInnaccuracyGain", base_data.get("HipInnaccuracyGain", 0.0)))
    IronSightRange = to_f(props.get("IronSightRange", base_data.get("IronSightRange", 0.0)))
    MaxRepairDegradation = to_f(props.get("MaxRepairDegradation", base_data.get("MaxRepairDegradation", 0.0)))
    MinRepairDegradation = to_f(props.get("MinRepairDegradation", base_data.get("MinRepairDegradation", 0.0)))
    RecoilAngle = to_f(props.get("RecoilAngle", base_data.get("RecoilAngle", 0.0)))
    RecoilCamera = to_f(props.get("RecoilCamera", base_data.get("RecoilCamera", 0.0)))
    RecoilCategoryMultiplierHandRotation = to_f(props.get("RecoilCategoryMultiplierHandRotation", base_data.get("RecoilCategoryMultiplierHandRotation", 0.0)))
    RecoilDampingHandRotation = to_f(props.get("RecoilDampingHandRotation", base_data.get("RecoilDampingHandRotation", 0.0)))
    RecoilForceBack = to_f(props.get("RecoilForceBack", base_data.get("RecoilForceBack", 0.0)))
    RecoilForceUp = to_f(props.get("RecoilForceUp", base_data.get("RecoilForceUp", 0.0)))
    RecoilPosZMult = to_f(props.get("RecoilPosZMult", base_data.get("RecoilPosZMult", 0.0)))
    RecoilReturnPathDampingHandRotation = to_f(props.get("RecoilReturnPathDampingHandRotation", base_data.get("RecoilReturnPathDampingHandRotation", 0.0)))
    RecoilReturnPathOffsetHandRotation = to_f(props.get("RecoilReturnPathOffsetHandRotation", base_data.get("RecoilReturnPathOffsetHandRotation", 0.0)))
    RecoilReturnSpeedHandRotation = to_f(props.get("RecoilReturnSpeedHandRotation", base_data.get("RecoilReturnSpeedHandRotation", 0.0)))
    RecolDispersion = to_f(props.get("RecolDispersion", base_data.get("RecolDispersion", 0.0)))
    SightingRange = to_f(props.get("SightingRange", base_data.get("SightingRange", 0.0)))
    SingleFireRate = to_f(props.get("SingleFireRate", base_data.get("SingleFireRate", 0.0)))
    Velocity = to_f(props.get("Velocity", base_data.get("Velocity", 0.0)))
    Weight = to_f(props.get("Weight", base_data.get("Weight", 0.0)))
    bEffDist = to_f(props.get("bEffDist", base_data.get("bEffDist", 0.0)))
    bFirerate = to_f(props.get("bFirerate", base_data.get("bFirerate", 0.0)))
    bHearDist = to_f(props.get("bHearDist", base_data.get("bHearDist", 0.0)))
    shotgunDispersion = to_f(props.get("shotgunDispersion", base_data.get("shotgunDispersion", 0.0)))

    # 2. Engineer new features
    name_str = str(base_data.get('Name', '') or base_data.get('shortName', '')).lower()
    mm_match = re.search(r'(\d+)mm', name_str)
    inch_match = re.search(r'(\d+\.?\d*)"', name_str)
    BarrelLengthMM = float(mm_match.group(1)) if mm_match else (float(inch_match.group(1)) * 25.4 if inch_match else 0.0)
    caliber_match = re.search(r'(\d+\.?\d*)x', name_str)
    CaliberNumeric = float(caliber_match.group(1)) if caliber_match else 0.0
    position_mult = 0.0
    if 'suppressor' in name_str or 'muzzle' in name_str or 'barrel' in name_str: position_mult = -1.0
    elif 'stock' in name_str or 'buttpad' in name_str: position_mult = 1.0
    Torque = Weight * position_mult * 10.0
    FactoredWeight = pow(Weight * 1.5, 1.1) if Weight > 0 else 0.0
    base_ergo_calc_val = Ergonomics / (Weight * 100) if Weight > 0 else 0.0
    ErgoWeight = pow(max(0, base_ergo_calc_val), 0.35) * 100.0
    VRecoilPerErgo = RecoilForceUp / Ergonomics if Ergonomics != 0 else 0.0
    HRecoilPerErgo = RecoilForceBack / Ergonomics if Ergonomics != 0 else 0.0
    dura = to_f(props.get('MaxDurability', base_data.get('MaxDurability', 100.0)))
    dura_factor = 2.0 - (dura / 100.0) if dura > 0 else 2.0
    DurabilityMalfRisk = pow(max(0, dura_factor), 3.0)

    # 3. Calculate all target values

    # Target: AllowOverheat
    z = 1
    pred = z
    pred = min(max(pred, 0.999999), 1.000001)
    item_entry["AllowOverheat"] = r(pred)

    # Target: AutoROF
    z = 30
    pred = z
    pred = min(max(pred, 29.999999), 30.000001)
    item_entry["AutoROF"] = int(round(pred))

    # Target: BaseChamberCheckSpeed
    z = 0.913566008005 + (-0.122262339793 * ((CenterOfImpact - 0.010125) / 0.00337036719068)) + (0.201158062592 * ((Velocity - 3.545) / 1.51122466894)) + (-0.473467184408 * ((HeatFactorByShot - 6.808125) / 1.06333184349)) + (-0.0142474979614 * ((AimPlane - 0.29375) / 0.0338886042793)) + (0.0990232056725 * ((RecoilCamera - 0.10875) / 0.0161535599792)) + (0.101894751481 * ((CoolFactorGunMods - 0.98035) / 0.0519890132624)) + (-0.252183562861 * ((Weight - 0.834) / 0.311049835235))
    pred = expm1_clamped(z)
    pred = min(max(pred, 0.9), 3.1)
    item_entry["BaseChamberCheckSpeed"] = r(pred)

    # Target: BaseChamberSpeedMulti
    z = 0.814072997792 + (0.679794720553 * ((ErgoWeight - 69.8192734906) / 12.0775922708)) + (19.2205328837 * ((Weight - 0.834) / 0.311049835235)) + (-19.004095196 * ((FactoredWeight - 1.28841422301) / 0.532518784861)) + (-0.314847102635 * ((HeatFactorByShot - 6.808125) / 1.06333184349)) + (0.242259222763 * ((bHearDist - 100) / 24.4948974278)) + (0.458899400566 * ((IronSightRange - 53.125) / 36.3092188707)) + (-0.0899438087844 * ((CenterOfImpact - 0.010125) / 0.00337036719068))
    pred = expm1_clamped(z)
    pred = min(max(pred, 0.795), 2.005)
    item_entry["BaseChamberSpeedMulti"] = r(pred)

    # Target: BaseFixSpeed
    z = 1.23038292554 + (-0.124035181405 * ((CenterOfImpact - 0.010125) / 0.00337036719068)) + (0.221169804728 * ((Velocity - 3.545) / 1.51122466894)) + (0.102432165746 * ((CoolFactorGunMods - 0.98035) / 0.0519890132624)) + (-0.0156314658803 * ((AimPlane - 0.29375) / 0.0338886042793)) + (0.100746231762 * ((RecoilCamera - 0.10875) / 0.0161535599792)) + (-0.493221545434 * ((HeatFactorByShot - 6.808125) / 1.06333184349)) + (-0.268739668811 * ((Weight - 0.834) / 0.311049835235))
    pred = z*z if z >= 0 else 0.0
    pred = min(max(pred, 0.9), 3.1)
    item_entry["BaseFixSpeed"] = r(pred)

    # Target: BaseMalfunctionChance
    z = 0.001375 + (0.000799814855869 * ((RecoilCamera - 0.10875) / 0.0161535599792)) + (0.000529171205935 * ((IronSightRange - 53.125) / 36.3092188707)) + (0.000227055632122 * ((AimPlane - 0.29375) / 0.0338886042793)) + (0.00146794872786 * ((HRecoilPerErgo - 30.2586092142) / 15.9964271246)) + (0.00047345869887 * ((Ergonomics - 28.5) / 9.30053761887)) + (-0.000948342047417 * ((RecoilDampingHandRotation - 0.84) / 0.01)) + (-0.00049155916129 * ((VRecoilPerErgo - 10.5370821416) / 6.84667850958))
    pred = z
    pred = min(max(pred, 1e-05), 0.00419)
    item_entry["BaseMalfunctionChance"] = r(pred)

    # Target: BaseReloadSpeedMulti
    z = 0.820818995909 + (0.103635864049 * ((Ergonomics - 28.5) / 9.30053761887)) + (-0.380493686627 * ((ErgoWeight - 69.8192734906) / 12.0775922708)) + (-0.285883826611 * ((FactoredWeight - 1.28841422301) / 0.532518784861))
    pred = expm1_clamped(z)
    pred = min(max(pred, 0.95), 2.05)
    item_entry["BaseReloadSpeedMulti"] = r(pred)

    # Target: BaseTorque
    z = -0.75 + (5.11553871993 * ((CoolFactorGunMods - 0.98035) / 0.0519890132624)) + (-0.617551055689 * ((CenterOfImpact - 0.010125) / 0.00337036719068)) + (99.8435643296 * ((FactoredWeight - 1.28841422301) / 0.532518784861)) + (-97.7492348279 * ((Weight - 0.834) / 0.311049835235)) + (0.56505271954 * ((IronSightRange - 53.125) / 36.3092188707))
    pred = z
    pred = min(max(pred, -8.5), 2.5)
    item_entry["BaseTorque"] = r(pred)

    # Target: CameraRecoil
    z = 0.378676784584 + (0.108489942938 * ((RecoilForceUp - 243.125) / 103.88507773)) + (2.60398053142 * ((Weight - 0.834) / 0.311049835235)) + (-2.56342826393 * ((FactoredWeight - 1.28841422301) / 0.532518784861)) + (0.0455385104835 * ((ErgoWeight - 69.8192734906) / 12.0775922708)) + (-0.0591896448528 * ((VRecoilPerErgo - 10.5370821416) / 6.84667850958))
    pred = z*z if z >= 0 else 0.0
    pred = min(max(pred, 0.12125), 0.20375)
    item_entry["CameraRecoil"] = r(pred)

    # Target: CenterOfImpact
    z = 0.104880884805
    pred = z*z if z >= 0 else 0.0
    pred = min(max(pred, -0.001), 0.021)
    item_entry["CenterOfImpact"] = r(pred)

    # Target: Convergence
    z = 1.81095853763 + (-0.382160873327 * ((RecoilForceBack - 718.125) / 162.690225198)) + (0.0600678744322 * ((Velocity - 3.545) / 1.51122466894)) + (0.155711604424 * ((RecoilReturnSpeedHandRotation - 2.5) / 0.409267638594)) + (0.203822646121 * ((VRecoilPerErgo - 10.5370821416) / 6.84667850958)) + (-0.246670594648 * ((Ergonomics - 28.5) / 9.30053761887))
    pred = expm1_clamped(z)
    pred = min(max(pred, 3.3), 7.7)
    item_entry["Convergence"] = r(pred)

    # Target: CoolFactorGun
    z = 0.1
    pred = z
    pred = min(max(pred, 0.099999), 0.100001)
    item_entry["CoolFactorGun"] = r(pred)

    # Target: CoolFactorGunMods
    z = 1
    pred = z
    pred = min(max(pred, 0.999999), 1.000001)
    item_entry["CoolFactorGunMods"] = r(pred)

    # Target: Dispersion
    z = 1.15019221894 + (0.0486964778919 * ((AimPlane - 0.29375) / 0.0338886042793)) + (0.0724741922378 * ((Velocity - 3.545) / 1.51122466894)) + (0.0324738085729 * ((CenterOfImpact - 0.010125) / 0.00337036719068))
    pred = expm1_clamped(z)
    pred = min(max(pred, 1.85), 5.15)
    item_entry["Dispersion"] = r(pred)

    # Target: DurabilityBurnRatio
    z = 0.587645414355
    pred = expm1_clamped(z)
    pred = min(max(pred, 0.465), 1.235)
    item_entry["DurabilityBurnRatio"] = r(pred)

    # Target: Ergonomics
    z = 80
    pred = z
    pred = min(max(pred, 79.999999), 80.000001)
    item_entry["Ergonomics"] = r(pred)

    # Target: HasShoulderContact
    z = 0
    pred = z
    pred = min(max(pred, -1e-06), 1e-06)
    item_entry["HasShoulderContact"] = r(pred)

    # Target: HeatFactorByShot
    z = 1
    pred = z
    pred = min(max(pred, 0.999999), 1.000001)
    item_entry["HeatFactorByShot"] = r(pred)

    # Target: HeatFactorGun
    z = 1.13953488372 + (-0.0276755834986 * ((HeatFactorByShot - 6.808125) / 1.06333184349))
    pred = z
    pred = min(max(pred, 0.855), 1.845)
    item_entry["HeatFactorGun"] = r(pred)

    # Target: HipAccuracyRestorationDelay
    z = 0.2
    pred = z
    pred = min(max(pred, 0.199999), 0.200001)
    item_entry["HipAccuracyRestorationDelay"] = r(pred)

    # Target: HipAccuracyRestorationSpeed
    z = 7
    pred = z
    pred = min(max(pred, 6.999999), 7.000001)
    item_entry["HipAccuracyRestorationSpeed"] = r(pred)

    # Target: HipInnaccuracyGain
    z = 0.16
    pred = z
    pred = min(max(pred, 0.159999), 0.160001)
    item_entry["HipInnaccuracyGain"] = r(pred)

    # Target: HorizontalRecoil
    z = 6.22892951087 + (0.333435283969 * ((RecoilForceUp - 243.125) / 103.88507773)) + (-0.376383370886 * ((VRecoilPerErgo - 10.5370821416) / 6.84667850958)) + (0.217072164281 * ((RecoilForceBack - 718.125) / 162.690225198)) + (-0.000204381434944 * ((RecoilReturnSpeedHandRotation - 2.5) / 0.409267638594)) + (0.0808668770507 * ((Velocity - 3.545) / 1.51122466894))
    pred = expm1_clamped(z)
    pred = min(max(pred, 469), 711)
    item_entry["HorizontalRecoil"] = r(pred)

    # Target: MaxChamberSpeed
    z = 0.763951081967 + (0.505620943249 * ((RecoilReturnSpeedHandRotation - 2.5) / 0.409267638594)) + (-0.207897192186 * ((RecoilForceUp - 243.125) / 103.88507773)) + (0.226061284713 * ((VRecoilPerErgo - 10.5370821416) / 6.84667850958)) + (0.443592760854 * ((RecoilDampingHandRotation - 0.84) / 0.01)) + (-0.0299145042443 * ((bHearDist - 100) / 24.4948974278)) + (0.185367690382 * ((RecoilForceBack - 718.125) / 162.690225198)) + (0.193349102498 * ((Ergonomics - 28.5) / 9.30053761887))
    pred = expm1_clamped(z)
    pred = min(max(pred, 0.765), 1.535)
    item_entry["MaxChamberSpeed"] = r(pred)

    # Target: MinChamberSpeed
    z = 0.821293543946 + (-0.024632221046 * ((bHearDist - 100) / 24.4948974278)) + (0.0457329802169 * ((IronSightRange - 53.125) / 36.3092188707)) + (0.0345404890223 * ((RecoilForceUp - 243.125) / 103.88507773)) + (2.47764060035 * ((Weight - 0.834) / 0.311049835235)) + (-2.46838458027 * ((FactoredWeight - 1.28841422301) / 0.532518784861)) + (-0.0462017008536 * ((HeatFactorByShot - 6.808125) / 1.06333184349)) + (0.0899844604798 * ((ErgoWeight - 69.8192734906) / 12.0775922708))
    pred = z*z if z >= 0 else 0.0
    pred = min(max(pred, 0.595), 0.705)
    item_entry["MinChamberSpeed"] = r(pred)

    # Target: OffsetRotation
    z = 0.01
    pred = z
    pred = min(max(pred, 0.009999), 0.010001)
    item_entry["OffsetRotation"] = r(pred)

    # Target: RecoilAngle
    z = 88.4799766622 + (-14.4337775361 * ((RecoilForceUp - 243.125) / 103.88507773)) + (18.3299385043 * ((VRecoilPerErgo - 10.5370821416) / 6.84667850958)) + (-11.4683977275 * ((RecoilForceBack - 718.125) / 162.690225198)) + (-0.0591243592326 * ((RecoilReturnSpeedHandRotation - 2.5) / 0.409267638594)) + (-3.60137578379 * ((Velocity - 3.545) / 1.51122466894))
    pred = z
    pred = min(max(pred, 74.25), 90.75)
    item_entry["RecoilAngle"] = r(pred)

    # Target: RecoilDamping
    z = 0.895553155333 + (0.0106919022714 * ((RecoilForceUp - 243.125) / 103.88507773)) + (-0.0135780208685 * ((VRecoilPerErgo - 10.5370821416) / 6.84667850958)) + (0.00849526930389 * ((RecoilForceBack - 718.125) / 162.690225198)) + (4.37871052034e-05 * ((RecoilReturnSpeedHandRotation - 2.5) / 0.409267638594)) + (0.00266772616655 * ((Velocity - 3.545) / 1.51122466894))
    pred = z*z if z >= 0 else 0.0
    pred = min(max(pred, 0.799), 0.821)
    item_entry["RecoilDamping"] = r(pred)

    # Target: RecoilHandDamping
    z = 0.408356215197 + (-0.0051409645762 * ((ErgoWeight - 69.8192734906) / 12.0775922708)) + (-0.000889838678336 * ((Velocity - 3.545) / 1.51122466894)) + (0.00713589132062 * ((RecoilForceBack - 718.125) / 162.690225198)) + (0.00382317869377 * ((Ergonomics - 28.5) / 9.30053761887)) + (0.00553426589416 * ((RecoilReturnSpeedHandRotation - 2.5) / 0.409267638594))
    pred = z
    pred = min(max(pred, 0.3995), 0.4105)
    item_entry["RecoilHandDamping"] = r(pred)

    # Target: RecoilIntensity
    z = 0.557265223323 + (0.0411265798345 * ((ErgoWeight - 69.8192734906) / 12.0775922708)) + (0.616128793709 * ((Weight - 0.834) / 0.311049835235)) + (-0.588540369232 * ((FactoredWeight - 1.28841422301) / 0.532518784861)) + (0.024300409265 * ((RecoilForceUp - 243.125) / 103.88507773)) + (0.0114010240022 * ((RecoilCamera - 0.10875) / 0.0161535599792))
    pred = z*z if z >= 0 else 0.0
    pred = min(max(pred, 0.2975), 0.3525)
    item_entry["RecoilIntensity"] = r(pred)

    # Target: SemiROF
    z = 450
    pred = z
    pred = min(max(pred, 449.999999), 450.000001)
    item_entry["SemiROF"] = int(round(pred))

    # Target: ShotgunDispersion
    z = 0
    pred = z
    pred = min(max(pred, -1e-06), 1e-06)
    item_entry["ShotgunDispersion"] = r(pred)

    # Target: Velocity
    z = 0.818540960567 + (0.885271484755 * ((Velocity - 3.545) / 1.51122466894))
    pred = z*z if z >= 0 else 0.0
    pred = min(max(pred, -0.295), 6.195)
    item_entry["Velocity"] = r(pred)

    # Target: VerticalRecoil
    z = 4.97295655129 + (0.627977978226 * ((RecoilForceUp - 243.125) / 103.88507773)) + (0.882039737811 * ((RecoilForceBack - 718.125) / 162.690225198)) + (-1.23882476161 * ((VRecoilPerErgo - 10.5370821416) / 6.84667850958)) + (-0.13553909923 * ((RecoilReturnSpeedHandRotation - 2.5) / 0.409267638594)) + (0.127526779954 * ((Velocity - 3.545) / 1.51122466894))
    pred = expm1_clamped(z)
    pred = min(max(pred, 81), 279)
    item_entry["VerticalRecoil"] = r(pred)

    # Target: VisualMulti
    z = 1.875 + (-1.22868940736 * ((bHearDist - 100) / 24.4948974278)) + (32.8423106967 * ((Weight - 0.834) / 0.311049835235)) + (0.866908043223 * ((ErgoWeight - 69.8192734906) / 12.0775922708)) + (-32.9453850946 * ((FactoredWeight - 1.28841422301) / 0.532518784861)) + (1.30839363465 * ((RecoilForceUp - 243.125) / 103.88507773)) + (-0.570040951558 * ((HeatFactorByShot - 6.808125) / 1.06333184349)) + (-0.0180996321132 * ((AimPlane - 0.29375) / 0.0338886042793))
    pred = z
    pred = min(max(pred, 1.475), 2.025)
    item_entry["VisualMulti"] = r(pred)

    # Target: WeapAccuracy
    z = -0.624999961842 + (1.32033529295 * ((AimPlane - 0.29375) / 0.0338886042793)) + (7.51490882257e-08 * ((Velocity - 3.545) / 1.51122466894)) + (-1.53198508306 * ((CenterOfImpact - 0.010125) / 0.00337036719068))
    pred = z
    pred = min(max(pred, -7), 37)
    item_entry["WeapAccuracy"] = r(pred)

    # Target: WeaponAllowADS
    z = 0
    pred = z
    pred = min(max(pred, -1e-06), 1e-06)
    item_entry["WeaponAllowADS"] = r(pred)

    # Target: Weight
    z = 1.00395776204 + (9.08337517848 * ((Weight - 0.834) / 0.311049835235)) + (-8.70633421614 * ((FactoredWeight - 1.28841422301) / 0.532518784861)) + (0.172828613585 * ((ErgoWeight - 69.8192734906) / 12.0775922708))
    pred = z*z if z >= 0 else 0.0
    pred = min(max(pred, 0.4665), 2.3035)
    item_entry["Weight"] = r(pred)

    return item_entry

# --- Stock (Mod) Formulas ---
def apply_stock_mod_formulas(item_entry: dict, base_data: dict, template: dict = None, context: dict = None) -> dict:
    """Auto-generated formulas for parent class: Stock (Mod)"""
    # Helper functions
    def to_f(x, d=0.0):
        try: return float(x)
        except: return d
    def r(x, d=3):
        try: return round(float(x), d)
        except: return x
    def expm1_clamped(z, cap=20.0):
        z = min(max(z, -cap), cap)
        return math.expm1(z)
    props = base_data.get("_props", base_data)

    # 1. Bind base features from props
    Accuracy = to_f(props.get("Accuracy", base_data.get("Accuracy", 0.0)))
    CoolFactor = to_f(props.get("CoolFactor", base_data.get("CoolFactor", 0.0)))
    Durability = to_f(props.get("Durability", base_data.get("Durability", 0.0)))
    DurabilityBurnModificator = to_f(props.get("DurabilityBurnModificator", base_data.get("DurabilityBurnModificator", 0.0)))
    EffectiveDistance = to_f(props.get("EffectiveDistance", base_data.get("EffectiveDistance", 0.0)))
    Ergonomics = to_f(props.get("Ergonomics", base_data.get("Ergonomics", 0.0)))
    HeatFactor = to_f(props.get("HeatFactor", base_data.get("HeatFactor", 0.0)))
    Loudness = to_f(props.get("Loudness", base_data.get("Loudness", 0.0)))
    Recoil = to_f(props.get("Recoil", base_data.get("Recoil", 0.0)))
    RecoilForceBack = to_f(props.get("RecoilForceBack", base_data.get("RecoilForceBack", 0.0)))
    RecoilForceUp = to_f(props.get("RecoilForceUp", base_data.get("RecoilForceUp", 0.0)))
    SightingRange = to_f(props.get("SightingRange", base_data.get("SightingRange", 0.0)))
    Velocity = to_f(props.get("Velocity", base_data.get("Velocity", 0.0)))
    Weight = to_f(props.get("Weight", base_data.get("Weight", 0.0)))

    # 2. Engineer new features
    name_str = str(base_data.get('Name', '') or base_data.get('shortName', '')).lower()
    mm_match = re.search(r'(\d+)mm', name_str)
    inch_match = re.search(r'(\d+\.?\d*)"', name_str)
    BarrelLengthMM = float(mm_match.group(1)) if mm_match else (float(inch_match.group(1)) * 25.4 if inch_match else 0.0)
    caliber_match = re.search(r'(\d+\.?\d*)x', name_str)
    CaliberNumeric = float(caliber_match.group(1)) if caliber_match else 0.0
    position_mult = 0.0
    if 'suppressor' in name_str or 'muzzle' in name_str or 'barrel' in name_str: position_mult = -1.0
    elif 'stock' in name_str or 'buttpad' in name_str: position_mult = 1.0
    Torque = Weight * position_mult * 10.0
    FactoredWeight = pow(Weight * 1.5, 1.1) if Weight > 0 else 0.0
    base_ergo_calc_val = Ergonomics / (Weight * 100) if Weight > 0 else 0.0
    ErgoWeight = pow(max(0, base_ergo_calc_val), 0.35) * 100.0
    VRecoilPerErgo = RecoilForceUp / Ergonomics if Ergonomics != 0 else 0.0
    HRecoilPerErgo = RecoilForceBack / Ergonomics if Ergonomics != 0 else 0.0
    dura = to_f(props.get('MaxDurability', base_data.get('MaxDurability', 100.0)))
    dura_factor = 2.0 - (dura / 100.0) if dura > 0 else 2.0
    DurabilityMalfRisk = pow(max(0, dura_factor), 3.0)

    # 3. Calculate all target values

    # Target: Accuracy
    z = 0.171748777963 + (1.94322063673 * ((Accuracy - 0.0717299578059) / 0.57287707799)) + (-1.09935601541 * ((Velocity - 0.0084388185654) / 0.129639590681))
    pred = z
    pred = min(max(pred, -23.5), 53.5)
    item_entry["Accuracy"] = r(pred)

    # Target: AimSpeed
    z = -0.0142785000852 + (-0.114524250419 * ((Accuracy - 0.071129707113) / 0.570512486998)) + (-7.8058796379e-08 * ((ErgoWeight - 45.5974067234) / 26.6414755613)) + (-1.29512665481e-07 * ((Recoil - -14.4518828452) / 10.0774607973)) + (-6.16353862762e-08 * ((CoolFactor - 0.996658995816) / 0.0230113177683)) + (-3.6367418881e-08 * ((FactoredWeight - 0.728142558856) / 0.752303391698))
    pred = z
    pred = min(max(pred, -6.2), 20.2)
    item_entry["AimSpeed"] = r(pred)

    # Target: AimStability
    z = 4.75327847121 + (-4.96290918536 * ((Recoil - -18.8636363636) / 8.03993133477)) + (-7.04362181189 * ((Weight - 0.500090909091) / 0.465759184556)) + (8.94438459545 * ((FactoredWeight - 0.755377937495) / 0.793061297967)) + (3.48373357128 * ((Accuracy - 0.121212121212) / 0.728534259404)) + (-0.316644082946 * ((Ergonomics - 9.53535353535) / 7.46786128338))
    pred = z
    pred = min(max(pred, -22.9), 40.9)
    item_entry["AimStability"] = r(pred)

    # Target: AutoROF
    z = 0.0569620253165
    pred = z
    pred = min(max(pred, -5.55), 6.55)
    item_entry["AutoROF"] = int(round(pred))

    # Target: BlocksFolding
    z = 0
    pred = z
    pred = min(max(pred, -0.05), 1.05)
    item_entry["BlocksFolding"] = r(pred)

    # Target: CameraRecoil
    z = -3.45764038781 + (2.20832682846 * ((Recoil - -14.4915966387) / 10.0799291367)) + (-0.368649193643 * ((ErgoWeight - 45.5844252547) / 26.6966320641)) + (-0.810349126884 * ((Weight - 0.477844537815) / 0.441148230809))
    pred = z
    pred = min(max(pred, -44.5), 54.5)
    item_entry["CameraRecoil"] = r(pred)

    # Target: Convergence
    z = 0.802392023223 + (-2.39464484172 * ((Weight - 0.155857142857) / 0.0624463851669)) + (-2.43919695402 * ((FactoredWeight - 0.203719596296) / 0.0913107029522)) + (4.74866641661 * ((Ergonomics - 0.142857142857) / 1.55182578446))
    pred = z
    pred = min(max(pred, -21.5), 11.5)
    item_entry["Convergence"] = r(pred)

    # Target: CoolFactor
    z = 0.693147180559 + (-8.44560662281e-12 * ((CoolFactor - 0.984686046512) / 0.0515433914353))
    pred = expm1_clamped(z)
    pred = min(max(pred, 0.895), 1.005)
    item_entry["CoolFactor"] = r(pred)

    # Target: Dispersion
    z = -0
    pred = z
    pred = min(max(pred, -53.5), 23.5)
    item_entry["Dispersion"] = r(pred)

    # Target: DurabilityBurnModificator
    z = 1.00180064513
    pred = z*z if z >= 0 else 0.0
    pred = min(max(pred, 0.8375), 1.1125)
    item_entry["DurabilityBurnModificator"] = r(pred)

    # Target: Ergonomics
    z = 5.96714690912 + (2.39177322298 * ((Ergonomics - 7.25523012552) / 7.31206115512)) + (24.587052339 * ((Weight - 0.483041841004) / 0.447466571911)) + (-23.454418047 * ((FactoredWeight - 0.728142558856) / 0.752303391698))
    pred = z
    pred = min(max(pred, -11.9), 29.9)
    item_entry["Ergonomics"] = r(pred)

    # Target: Handling
    z = 6.68350699926 + (15.0778193129 * ((Weight - 0.537463157895) / 0.452390581374)) + (-12.888945711 * ((FactoredWeight - 0.814503286651) / 0.762297022886)) + (-0.025551593951 * ((Ergonomics - 8.05263157895) / 6.80459352752)) + (-1.27729479504 * ((DurabilityBurnModificator - 0.999578947368) / 0.00247760048336)) + (0.468315437282 * ((CoolFactor - 0.999857894737) / 0.024545196031))
    pred = z
    pred = min(max(pred, -16.8), 22.8)
    item_entry["Handling"] = r(pred)

    # Target: HasShoulderContact
    z = 0.713629755009 + (-0.304280334443 * ((Recoil - -14.4518828452) / 10.0774607973)) + (0.161542725257 * ((ErgoWeight - 45.5974067234) / 26.6414755613)) + (-0.0850166247752 * ((Ergonomics - 7.25523012552) / 7.31206115512)) + (0.659238655044 * ((Weight - 0.483041841004) / 0.447466571911)) + (-0.592584602965 * ((FactoredWeight - 0.728142558856) / 0.752303391698))
    pred = z
    pred = min(max(pred, -0.05), 1.05)
    item_entry["HasShoulderContact"] = r(pred)

    # Target: HeatFactor
    z = 1.00000000005 + (-4.7020311385e-11 * ((HeatFactor - 1.02125581395) / 0.0570618159393))
    pred = z*z if z >= 0 else 0.0
    pred = min(max(pred, 0.995), 1.105)
    item_entry["HeatFactor"] = r(pred)

    # Target: HorizontalRecoil
    z = -6.20592156262 + (3.88392556482 * ((Recoil - -14.4518828452) / 10.0774607973)) + (-9.14796283719 * ((Weight - 0.483041841004) / 0.447466571911)) + (7.67852143399 * ((FactoredWeight - 0.728142558856) / 0.752303391698))
    pred = z
    pred = min(max(pred, -41.95), 22.95)
    item_entry["HorizontalRecoil"] = r(pred)

    # Target: ModMalfunctionChance
    z = 0.0843036317366 + (2.03737916833 * ((Velocity - 0.0084388185654) / 0.129639590681)) + (7.5973251384e-08 * ((Accuracy - 0.0717299578059) / 0.57287707799)) + (-2.41722741454e-10 * ((Recoil - -14.3797468354) / 10.0891224344)) + (0.258515034862 * ((DurabilityBurnModificator - 0.999324894515) / 0.00361197207747)) + (-1.1211200732e-09 * ((ErgoWeight - 45.3418209354) / 26.6073598081))
    pred = z
    pred = min(max(pred, -33.5), 43.5)
    item_entry["ModMalfunctionChance"] = r(pred)

    # Target: RecoilAngle
    z = -12.5 + (-2.5 * ((Ergonomics - 2) / 2))
    pred = z
    pred = min(max(pred, -15.25), -9.75)
    item_entry["RecoilAngle"] = r(pred)

    # Target: SemiROF
    z = 0.200421940928
    pred = z
    pred = min(max(pred, -3.75), 12.75)
    item_entry["SemiROF"] = int(round(pred))

    # Target: StockAllowADS
    z = 0
    pred = z
    pred = min(max(pred, -0.05), 1.05)
    item_entry["StockAllowADS"] = r(pred)

    # Target: VerticalRecoil
    z = -0
    pred = z
    pred = min(max(pred, -42.75), 17.75)
    item_entry["VerticalRecoil"] = r(pred)

    # Target: Weight
    z = 0.483041841984 + (0.447466573478 * ((Weight - 0.483041841004) / 0.447466571911)) + (-1.39962721847e-09 * ((FactoredWeight - 0.728142558856) / 0.752303391698)) + (-1.30501935266e-09 * ((ErgoWeight - 45.5974067234) / 26.6414755613))
    pred = z
    pred = min(max(pred, -0.10145), 2.79045)
    item_entry["Weight"] = r(pred)

    return item_entry

# --- Vest (Mod) Formulas ---
def apply_vest_mod_formulas(item_entry: dict, base_data: dict, template: dict = None, context: dict = None) -> dict:
    """Auto-generated formulas for parent class: Vest (Mod)"""
    # Helper functions
    def to_f(x, d=0.0):
        try: return float(x)
        except: return d
    def r(x, d=3):
        try: return round(float(x), d)
        except: return x
    def expm1_clamped(z, cap=20.0):
        z = min(max(z, -cap), cap)
        return math.expm1(z)
    props = base_data.get("_props", base_data)

    # 1. Bind base features from props
    BluntThroughput = to_f(props.get("BluntThroughput", base_data.get("BluntThroughput", 0.0)))
    Ergonomics = to_f(props.get("Ergonomics", base_data.get("Ergonomics", 0.0)))
    RecoilForceBack = to_f(props.get("RecoilForceBack", base_data.get("RecoilForceBack", 0.0)))
    RecoilForceUp = to_f(props.get("RecoilForceUp", base_data.get("RecoilForceUp", 0.0)))
    Weight = to_f(props.get("Weight", base_data.get("Weight", 0.0)))
    armorClass = to_f(props.get("armorClass", base_data.get("armorClass", 0.0)))
    mousePenalty = to_f(props.get("mousePenalty", base_data.get("mousePenalty", 0.0)))
    speedPenaltyPercent = to_f(props.get("speedPenaltyPercent", base_data.get("speedPenaltyPercent", 0.0)))
    weaponErgonomicPenalty = to_f(props.get("weaponErgonomicPenalty", base_data.get("weaponErgonomicPenalty", 0.0)))

    # 2. Engineer new features
    name_str = str(base_data.get('Name', '') or base_data.get('shortName', '')).lower()
    mm_match = re.search(r'(\d+)mm', name_str)
    inch_match = re.search(r'(\d+\.?\d*)"', name_str)
    BarrelLengthMM = float(mm_match.group(1)) if mm_match else (float(inch_match.group(1)) * 25.4 if inch_match else 0.0)
    caliber_match = re.search(r'(\d+\.?\d*)x', name_str)
    CaliberNumeric = float(caliber_match.group(1)) if caliber_match else 0.0
    position_mult = 0.0
    if 'suppressor' in name_str or 'muzzle' in name_str or 'barrel' in name_str: position_mult = -1.0
    elif 'stock' in name_str or 'buttpad' in name_str: position_mult = 1.0
    Torque = Weight * position_mult * 10.0
    FactoredWeight = pow(Weight * 1.5, 1.1) if Weight > 0 else 0.0
    base_ergo_calc_val = Ergonomics / (Weight * 100) if Weight > 0 else 0.0
    ErgoWeight = pow(max(0, base_ergo_calc_val), 0.35) * 100.0
    VRecoilPerErgo = RecoilForceUp / Ergonomics if Ergonomics != 0 else 0.0
    HRecoilPerErgo = RecoilForceBack / Ergonomics if Ergonomics != 0 else 0.0
    dura = to_f(props.get('MaxDurability', base_data.get('MaxDurability', 100.0)))
    dura_factor = 2.0 - (dura / 100.0) if dura > 0 else 2.0
    DurabilityMalfRisk = pow(max(0, dura_factor), 3.0)

    # 3. Calculate all target values

    # Target: Comfort
    z = 0.91991450576 + (-0.0234277597755 * ((weaponErgonomicPenalty - -0.857142857143) / 1.36837457576)) + (0.569074037165 * ((FactoredWeight - 4.1717750175) / 4.23161329401)) + (-0.558259236289 * ((Weight - 2.37091071429) / 2.12782650069)) + (-0.00802792514524 * ((BluntThroughput - 0.138344642857) / 0.207507504098))
    pred = z*z if z >= 0 else 0.0
    pred = min(max(pred, 0.675), 1.225)
    item_entry["Comfort"] = r(pred)

    # Target: Price
    z = 174.404342305
    pred = z*z if z >= 0 else 0.0
    pred = min(max(pred, 14800), 41200)
    item_entry["Price"] = r(pred)

    # Target: ReloadSpeedMulti
    z = 1.00439503425 + (-0.341555142866 * ((FactoredWeight - 4.1717750175) / 4.23161329401)) + (0.340080937318 * ((Weight - 2.37091071429) / 2.12782650069))
    pred = z*z if z >= 0 else 0.0
    pred = min(max(pred, 0.8445), 1.1855)
    item_entry["ReloadSpeedMulti"] = r(pred)

    # Target: mousePenalty
    z = 0
    pred = z
    pred = min(max(pred, -1e-06), 1e-06)
    item_entry["mousePenalty"] = r(pred)

    # Target: speedPenaltyPercent
    z = -0.789564520161 + (0.362199285514 * ((weaponErgonomicPenalty - -0.857142857143) / 1.36837457576)) + (0.566249098652 * ((speedPenaltyPercent - -1.03571428571) / 1.51143599782)) + (0.0846352633735 * ((BluntThroughput - 0.138344642857) / 0.207507504098))
    pred = z
    pred = min(max(pred, -6.3), 0.3)
    item_entry["speedPenaltyPercent"] = r(pred)

    # Target: weaponErgonomicPenalty
    z = -0.537408188875 + (0.545812158183 * ((speedPenaltyPercent - -1.03571428571) / 1.51143599782)) + (0.355655391452 * ((weaponErgonomicPenalty - -0.857142857143) / 1.36837457576)) + (0.0411806503994 * ((BluntThroughput - 0.138344642857) / 0.207507504098))
    pred = z
    pred = min(max(pred, -5.775), 0.275)
    item_entry["weaponErgonomicPenalty"] = r(pred)

    return item_entry

# --- Visor (Mod) Formulas ---
def apply_visor_mod_formulas(item_entry: dict, base_data: dict, template: dict = None, context: dict = None) -> dict:
    """Auto-generated formulas for parent class: Visor (Mod)"""
    # Helper functions
    def to_f(x, d=0.0):
        try: return float(x)
        except: return d
    def r(x, d=3):
        try: return round(float(x), d)
        except: return x
    def expm1_clamped(z, cap=20.0):
        z = min(max(z, -cap), cap)
        return math.expm1(z)
    props = base_data.get("_props", base_data)

    # 1. Bind base features from props
    Ergonomics = to_f(props.get("Ergonomics", base_data.get("Ergonomics", 0.0)))
    Weight = to_f(props.get("Weight", base_data.get("Weight", 0.0)))

    # 2. Engineer new features
    name_str = str(base_data.get('Name', '') or base_data.get('shortName', '')).lower()
    FactoredWeight = pow(Weight * 1.5, 1.1) if Weight > 0 else 0.0
    base_ergo_calc_val = Ergonomics / (Weight * 100) if Weight > 0 else 0.0
    ErgoWeight = pow(max(0, base_ergo_calc_val), 0.35) * 100.0

    # 3. Calculate all target values

    # Target: ReloadSpeedMulti
    z = 1
    pred = z
    pred = min(max(pred, 0.999999), 1.000001)
    item_entry["ReloadSpeedMulti"] = r(pred)

    return item_entry

import re
import math

PARENT_CLASSES = {
    "5b47574386f77428ca22b346": "Ammo",
    "5b47574386f77428ca22b33c": "AmmoBoxes",
    "5448e54d4bdc2dcc718b4568": "Armor",
    "5b5f701386f774093f2ecf0f": "ArmorVests",
    "5b5f78e986f77447ed5636b1": "AssaultCarbines",
    "5447b5fc4bdc2d87278b4567": "AssaultCarbines",
    "5b5f78fc86f77409407a7f90": "AssaultRifles",
    "5447b5f14bdc2d61278b4567": "AssaultRifles",
    "5b5f740a86f77447ec5d7706": "AssaultScopes",
    "5b5f74cc86f77447ec5d770a": "AuxiliaryParts",
    "5a74651486f7744e73386dd1": "AuxiliaryParts",
    "5448e53e4bdc2d60728b4567": "Backpack",
    "5b5f6f6c86f774093f2ecf0b": "Backpacks",
    "555ef6e44bdc2de9068b457e": "Barrel",
    "5b5f75c686f774094242f19f": "Barrels",
    "5b5f71c186f77409407a7ec0": "Bipods",
    "55818afb4bdc2dde698b456d": "Bipods",
    "5b5f798886f77447ed5636b5": "BoltActionRifles",
    "55818a6f4bdc2db9688b456b": "ChargingHandle",
    "5b5f751486f77447ec5d770c": "ChargingHandles",
    "5b5f742686f774093e6cb4ff": "Collimators",
    "5b5f744786f774094242f197": "CompactCollimators",
    "5b5f724c86f774093f2ecf15": "FlashhidersBrakes",
    "5b5f73ab86f774094242f195": "Flashlights",
    "5b5f71de86f774093f2ecf13": "ForeGrips",
    "55818af64bdc2d5b648b4570": "Foregrip",
    "5b5f71b386f774093f2ecf11": "FunctionalMods",
    "5b5f760586f774093e6cb509": "GasBlocks",
    "56ea9461d2720b67698b456f": "Gasblock",
    "5b47574386f77428ca22b33f": "Gear",
    "5b5f704686f77447ec5d76d7": "GearComponents",
    "5b5f750686f774093e6cb503": "GearMods",
    "57bef4c42459772e8d35a53b": "GearComponents",
    "5b5f79d186f774093f2ed3c2": "GrenadeLaunchers",
    "55818a104bdc2db9688b4569": "Handguard",
    "5b5f75e486f77447ec5d7712": "Handguards",
    "5645bcb74bdc2ded0b8b4578": "Headset",
    "5b5f6f3c86f774094242ef87": "Headsets",
    "5a341c4086f77401f2541505": "Headwear",
    "5b47574386f77428ca22b330": "Headwear",
    "5b5f746686f77447ec5d7708": "IronSights",
    "5b5f73c486f77447ec5d7704": "LaserTargetPointers",
    "55818b014bdc2ddc698b456b": "Launcher",
    "5b5f752e86f774093e6cb505": "Launchers",
    "55818b0e4bdc2dde698b456e": "LightLasers",
    "5b5f79a486f77409407a7f94": "MachineGuns",
    "5447bed64bdc2d97278b4568": "MachineGuns",
    "5b5f754a86f774094242f19b": "Magazines",
    "5448bc234bdc2d3c308b4569": "Magazines",
    "5b5f791486f774093f2ed3be": "MarksmanRifles",
    "5447b6194bdc2d67278b4567": "MarksmanRifles",
    "5b5f755f86f77447ec5d770e": "Mounts",
    "55818b224bdc2dde698b456f": "Mounts",
    "5448fe394bdc2d0d028b456c": "Muzzle",
    "5b5f72f786f77447ec5d7702": "MuzzleAdapters",
    "5b5f724186f77447ed5636ad": "MuzzleDevices",
    "5b5f748386f774093e6cb501": "Optics",
    "5447b5cf4bdc2d65278b4567": "Pistol",
    "5b5f761f86f774094242f1a1": "PistolGrips",
    "55818a684bdc2ddd698b456d": "PistolGrip",
    "5b5f792486f77447ed5636b3": "Pistols",
    "55818a304bdc2db5418b457d": "Receiver",
    "5b5f764186f77447ec5d7714": "ReceiversSlides",
    "5b47574386f77428ca22b33b": "Rounds",
    "5485a8684bdc2da71d8b4567": "Rounds",
    "5b5f794b86f77409407a7f92": "Shotguns",
    "5447b6094bdc2dc3278b4567": "Shotguns",
    "5b5f73ec86f774093e6cb4fd": "Sights",
    "5448fe7a4bdc2d6f028b456b": "Sights",
    "5b5f796a86f774093f2ed3c0": "SMGs",
    "5447b5e04bdc2d62278b4567": "SMGs",
    "5447b6254bdc2dc3278b4568": "SniperRifles",
    "55818a594bdc2db9688b456a": "Stock",
    "5b5f757486f774093e6cb507": "StocksChassis",
    "5b5f731a86f774093e6cb4f9": "Suppressors",
    "5b5f737886f774093e6cb4fb": "TacticalComboDevices",
    "5b5f6f8786f77447ed563642": "TacticalRigs",
    "5448e5284bdc2dcb718b4567": "Vest",
    "5448e5724bdc2ddf718b4568": "Visor",
    "5b47574386f77428ca22b331": "Visors",
    "5b5f75b986f77447ec5d7710": "VitalParts",
    "5b5f71a686f77447ed5636ab": "WeaponPartsMods",
    "5b5f78dc86f77409407a7f8e": "Weapons",
    "55818b164bdc2ddc698b456c": "CombTactDevice"
}

gun_formula_map = {
    "AssaultCarbines": apply_assaultcarbines_gun_formulas,
    "AssaultRifles": apply_assaultrifles_gun_formulas,
    "Launcher": apply_launcher_gun_formulas,
    "MarksmanRifles": apply_marksmanrifles_gun_formulas,
    "Pistol": apply_pistol_gun_formulas,
    "SMGs": apply_smgs_gun_formulas,
    "Shotguns": apply_shotguns_gun_formulas,
    "SniperRifles": apply_sniperrifles_gun_formulas
}

mod_formula_map = {
    "AuxiliaryParts": apply_auxiliaryparts_mod_formulas,
    "Barrel": apply_barrel_mod_formulas,
    "Bipods": apply_bipods_mod_formulas,
    "ChargingHandle": apply_charginghandle_mod_formulas,
    "CombTactDevice": apply_combtactdevice_mod_formulas,
    "Foregrip": apply_foregrip_mod_formulas,
    "Gasblock": apply_gasblock_mod_formulas,
    "Handguard": apply_handguard_mod_formulas,
    "Headset": apply_headset_mod_formulas,
    "Magazines": apply_magazines_mod_formulas,
    "Mounts": apply_mounts_mod_formulas,
    "Muzzle": apply_muzzle_mod_formulas,
    "PistolGrip": apply_pistolgrip_mod_formulas,
    "Receiver": apply_receiver_mod_formulas,
    "Sights": apply_sights_mod_formulas,
    "Stock": apply_stock_mod_formulas
}

gear_formula_map = {
    "Armor": apply_armor_mod_formulas,
    "Backpack": apply_backpack_mod_formulas,
    "GearComponents": apply_gearcomponents_mod_formulas,
    "Headwear": apply_headwear_mod_formulas,
    "Vest": apply_vest_mod_formulas,
    "Visor": apply_visor_mod_formulas
}


# --- Utility: get formula function by category ---
def get_formula_func(category: str):
    if category in gun_formula_map:
        return gun_formula_map[category]
    if category in mod_formula_map:
        return mod_formula_map[category]
    if category in gear_formula_map:
        return gear_formula_map[category]
    
    for maps in (gun_formula_map, mod_formula_map, gear_formula_map):
        if category in maps:
            return maps[category]
    # Try alias
    if category in CATEGORY_ALIASES:
        alias = CATEGORY_ALIASES[category]
        for maps in (gun_formula_map, mod_formula_map, gear_formula_map):
            if alias in maps:
                return maps[alias]
    return None

