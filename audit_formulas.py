#!/usr/bin/env python3
"""
Full-sweep audit of the emitted Realism formulas.

Walks every *Templates.json under a directory, resolves each item to its parent
class exactly the way emit_form_test.py does, dispatches to the matching emitted
formula, and scores every numeric target against the authored Realism value.

For each target it reports:
  MAE           mean absolute error vs the authored template value
  nMAE%         MAE normalised by the mean magnitude of the truth (comparable
                across targets on wildly different scales)
  bias          mean signed error; |bias|/MAE near 1.0 means the model is wrong
                in one direction on every item, which is a fit problem rather
                than noise
  name-dep      YES if the prediction changes when a top-level 'Name' is present.
                After the train/inference parity fix this column should be empty
                everywhere - any YES means a name-derived engineered feature is
                still trained on one string form and evaluated on another.
  flags         DEGEN   truth is constant across every item (nothing to learn)
                SPARSE  >70% of truth values are zero
                1-SIDED |bias|/MAE > 0.9
                BIG     nMAE% > 25

Usage:
    python audit_formulas.py --templates-dir templates_data --master items_master.json
    python audit_formulas.py --class AssaultRifles --target HorizontalRecoil
    python audit_formulas.py --csv audit.csv --with-template
"""

import argparse
import importlib.util
import json
import os
import re
import statistics
import sys
from typing import Any, Dict, List, Optional

# Engineered features derived from the item's name string. Any target whose
# formula references one of these is exposed to the train/inference parity bug.
NAME_DERIVED = (
    "CaliberNumeric", "BarrelLengthMM", "IsShort", "IsLong", "IsHeavy", "IsLight",
    "IsSuppressor", "IsBrake", "IsAdapter", "IsCombo", "IsMagnified", "IsCollimator",
    "IsDrum", "IsShotgun", "GaugeNumeric", "ChokeTightness", "IsPumpAction",
    "CapacityGuess", "IsTubeFed", "IsSemiAutoShotgun", "IsManuallyOperatedGun",
)


# ----------------------------------------------------------------- loading ---

def load_module(path: str, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"cannot import {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# Mirrors emit_form_test: ammo lives in ammo_v2.json, and ammoTemplates.json
# holds only names / LoyaltyLevel / BasePriceModifier, which are banned targets.
EXTRA_TEMPLATE_FILES = {"ammo_v2.json"}
SKIP_TEMPLATE_FILES = {"ammotemplates.json"}


def find_templates(search_dir: str) -> List[str]:
    """Same discovery rule as emit_form_test.find_templates."""
    found = []
    for root, _, files in os.walk(search_dir):
        for f in files:
            low = f.lower()
            if low in SKIP_TEMPLATE_FILES:
                continue
            if low.endswith("templates.json") or low in EXTRA_TEMPLATE_FILES:
                found.append(os.path.join(root, f))
    return list(dict.fromkeys(found))


def load_master(path: str) -> Dict[str, Dict[str, Any]]:
    """items_master.json ships as either an id-keyed dict or a flat list."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    items = list(data.values()) if isinstance(data, dict) else data
    return {
        it["_id"].lower(): it
        for it in items
        if isinstance(it, dict) and isinstance(it.get("_id"), str)
    }


def load_template_file(path: str) -> Dict[str, Dict[str, Any]]:
    """Keep the raw records - unlike parse_compat_any we need 'Name' intact."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as exc:
        print(f"  !! could not parse {path}: {exc}")
        return {}

    out: Dict[str, Dict[str, Any]] = {}

    def add(iid, obj):
        if iid and isinstance(obj, dict):
            out[str(iid).lower()] = obj

    if isinstance(data, dict) and "item" in data and "info" in data:
        for _, lst in data["item"].items():          # ammo files are caliber-keyed
            if isinstance(lst, list):
                for obj in lst:
                    add(obj.get("id") or obj.get("_id") or obj.get("ItemID"), obj)
    elif isinstance(data, list):
        for obj in data:
            add(obj.get("ItemID") or obj.get("_id"), obj)
    elif isinstance(data, dict):
        for k, v in data.items():
            if isinstance(v, dict):
                add(v.get("ItemID") or v.get("_id") or k, v)
    return out


# ------------------------------------------------------------- class logic ---

def resolve_class_name(item, master, parent_classes, class_id_set) -> Optional[str]:
    """Walk the handbook/parent chain until a known parent class id is hit."""
    pid = item.get("handbookParentId") or item.get("_parent")
    for _ in range(10):
        if not pid:
            break
        pid_l = pid.lower()
        if pid_l in class_id_set:
            return parent_classes[pid_l]
        parent = master.get(pid_l)
        if not parent:
            break
        pid = parent.get("handbookParentId") or parent.get("_parent")
    return None


# --- the emitter's sub-splits, mirrored so the audit scores each item against
# --- the model it was actually trained under. Without this, a pistol barrel is
# --- graded by the rifle formula and every split class reads wrong.
PISTOL_CALIBER_IDS = {
    "caliber9x19para", "caliber9x18pm", "caliber9x21", "caliber1143x23acp",
    "caliber762x25tt", "caliber57x28", "caliber46x30", "caliber127x33",
    "caliber9x33r",
}
SPLIT_PISTOL_RIFLE = {"Barrel", "Barrels", "Suppressors", "MuzzleBrakes",
                      "Compensators", "MuzzleCombos", "Handguard", "Handguards",
                      "Magazines", "PistolGrip"}
FREE_FLOAT_HINTS = ("mlok", "m-lok", "keymod", "key_mod", "free", "ffs", "quad",
                    "ris", "rahg", "urx", "mrf", "slr", "geissele", "mcmr",
                    "smr", "hera", "midwest", "ff")
CHARGING_HANDLE_TIER_HINTS = [
    ("Ambi", ("ambi", "raptor", "grip_n_rip", "avalanche", "geissele_ach",
              "geissele_sch", "double_latch", "masp", "mod2", "knurled",
              "zenit_rp1", "css", "cmmg_mid", "spear")),
    ("Extended", ("extended", "tactical_latch", "badger", "handler", "a3_handle",
                  "single_latch", "kac_charging_handle", "mcx")),
]
SUPPRESSOR_WIPE_HINTS = (
    "pbs-1", "pbs1", "pbs-4", "pbs4", "bramit", "hexagon", "rotor", "tochmash",
    "9a91", "val", "vss", "kbp", "6p9", "dvl", "buben", "tundra",
    "tt_custom_noname", "pab-9", "fischer", "fd917", "alpha_dog", "alpha_9",
    "noname", "spectehnika",
)


def build_pistol_host_set(master):
    """Item ids whose only resolvable host chambering is a handgun round."""
    from collections import defaultdict
    parents = defaultdict(set)
    for it in master.values():
        for slot in (it.get("_props", {}).get("Slots") or []):
            for filt in (slot.get("_props", {}).get("filters") or []):
                for child in (filt.get("Filter") or []):
                    parents[str(child).lower()].add(str(it.get("_id", "")).lower())

    def resolve(iid, depth=0, seen=None):
        seen = seen or set()
        if iid in seen or depth > 6:
            return set()
        seen.add(iid)
        found = set()
        it = master.get(iid)
        if it:
            cal = it.get("_props", {}).get("ammoCaliber")
            if isinstance(cal, str) and cal.strip():
                found.add(cal.strip().lower())
        for par in parents.get(iid, ()):
            found |= resolve(par, depth + 1, seen)
        return found

    out = set()
    for iid in master:
        cals = resolve(iid)
        if cals and cals <= PISTOL_CALIBER_IDS:
            out.add(iid)
    return out


def _has_own_model(mod, name):
    """True only when `name` is a direct key in one of the formula maps -- an
    alias to another class does not count as having its own model."""
    for attr in ("gun_formula_map", "mod_formula_map",
                 "gear_formula_map", "ammo_formula_map"):
        table = getattr(mod, attr, None)
        if isinstance(table, dict) and name in table:
            return True
    return False


def apply_emitter_splits(cname, master_item, tmpl, pistol_ids, mod):
    """Return the sub-class name the emitter would have trained this item under,
    falling back through CATEGORY_ALIASES to whatever actually has a model."""
    name = tmpl.get("Name") or master_item.get("_name") or ""
    iid = str(master_item.get("_id", "") or "").lower()

    candidates = [cname]
    if cname in SPLIT_PISTOL_RIFLE and iid in pistol_ids:
        candidates.insert(0, cname + "Pistol")

    expanded = []
    for c in candidates:
        if c.startswith("Suppressors") and any(
                k in name.lower() for k in SUPPRESSOR_WIPE_HINTS):
            expanded.append(c + "Wipe")
        expanded.append(c)

    with_hg = []
    for c in expanded:
        if c.startswith("Handguard") and any(k in name.lower() for k in FREE_FLOAT_HINTS):
            with_hg.append(c + "FreeFloat")
        with_hg.append(c)
    expanded = with_hg

    with_ch = []
    for c in expanded:
        if c.startswith("ChargingHandle"):
            tier = next((t for t, keys in CHARGING_HANDLE_TIER_HINTS
                         if any(k in name.lower() for k in keys)), "")
            if tier:
                with_ch.append(c + tier)
        with_ch.append(c)
    expanded = with_ch

    final = []
    for c in expanded:
        if c.startswith("Magazines"):
            esd = master_item.get("_props", {}).get("ExtraSizeDown")
            esd = int(esd) if isinstance(esd, (int, float)) and not isinstance(esd, bool) else 1
            suffix = {0: "Flush", 1: "", 2: "Extended"}.get(min(max(esd, 0), 2), "")
            if suffix:
                final.append(c + suffix)
        final.append(c)

    # Accept a sub-class name ONLY if it has a model of its very own. Since
    # get_formula_func now follows CATEGORY_ALIASES, a name that merely aliases
    # back to its parent would otherwise be reported as a separate class -- which
    # is how 'MuzzleCombosPistol (3 items)' and 'MagazinesPistolExtended (1 item)'
    # appeared, splitting one model's results across several phantom rows.
    for c in final:
        if _has_own_model(mod, c):
            return c
    return cname


def muzzle_subclass(master_item) -> str:
    """Mirror the Muzzle split in emit_form_test.main().

    NOTE: the emitter reads s[0].get('Name'), which is absent on master items -
    only '_name' exists - so its name-based branches never fire during training.
    We read both so the audit reflects what the split was *meant* to do; expect
    disagreement on flash hiders and thread adapters until that is fixed too.
    """
    n = (str(master_item.get("Name", "") or "") + " " +
         str(master_item.get("_name", "") or "")).lower()
    t = str(master_item.get("_props", {}).get("muzzleModType", "") or "").lower()
    if t in ("silencer", "pms") or "suppressor" in n or "silencer" in n:
        return "Suppressors"
    if t == "adapter" or "thread" in n or "adapter" in n or "protector" in n or "nut" in n:
        return "MuzzleAdapters"
    if t == "flashhider" or "flash" in n or "hider" in n:
        return "FlashHiders"
    if t == "brake" and "_std" in n:
        return "MuzzleBrakesFactory"   # the weapon's issued device, not a brake
    if t == "conpensator":          # BSG's spelling
        return "Compensators"
    if t == "muzzlecombo":
        return "MuzzleCombos"
    return "MuzzleBrakes"


# ----------------------------------------------------------------- scoring ---

def predict(func, master_item, tmpl, use_name, template_arg):
    base = dict(master_item)
    base["_props"] = dict(master_item.get("_props", {}))
    if use_name:
        nm = tmpl.get("Name") or master_item.get("_name") or ""
        if nm:
            base["Name"] = nm
    entry = {}
    func(entry, base, template_arg, None)
    return entry


def formula_name_dependence(formulas_path: str) -> Dict[str, set]:
    """Static scan: which targets in each emitted function use a name-derived feature."""
    src = open(formulas_path, "r", encoding="utf-8", errors="replace").read()
    out: Dict[str, set] = {}
    for block in re.split(r"\n(?=def apply_)", src):
        m = re.match(r"def apply_(\w+)_(?:gun|mod)_formulas", block)
        if not m:
            continue
        hits = {
            tgt for tgt, expr in re.findall(r"# Target: (\w+)\r?\n\s+pred = ([^\r\n]+)", block)
            if any(nf in expr for nf in NAME_DERIVED)
        }
        out[m.group(1)] = hits
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--templates-dir", default="templates_data")
    ap.add_argument("--master", default="items_master.json")
    ap.add_argument("--formulas", default="formulas.py")
    ap.add_argument("--class", dest="only_class", help="audit a single class only")
    ap.add_argument("--target", help="per-item breakdown for one target")
    ap.add_argument("--with-template", action="store_true",
                    help="pass the authored record as `template` (enables the "
                         "clamp-to-truth slack). Default is raw ML, which is what "
                         "a genuinely new item gets.")
    ap.add_argument("--csv", help="write the full per-target table here")
    ap.add_argument("--min-nmae", type=float, default=0.0,
                    help="only print targets above this nMAE%% (default 0 = all)")
    args = ap.parse_args()

    F = load_module(args.formulas, "formulas_under_test")
    if not hasattr(F, "get_formula_func"):
        raise SystemExit("formulas.py has no get_formula_func()")
    parent_classes = {k.lower(): v for k, v in F.PARENT_CLASSES.items()}
    class_id_set = set(parent_classes)

    master = load_master(args.master)
    print(f"[master]    {len(master)} items from {args.master}")
    pistol_ids = build_pistol_host_set(master)
    print(f"[hosts]     {len(pistol_ids)} items resolve to a pistol-only chambering")

    files = find_templates(args.templates_dir)
    print(f"[templates] {len(files)} file(s) under {args.templates_dir}")
    if not files:
        raise SystemExit("no *Templates.json found")

    name_dep_static = formula_name_dependence(args.formulas)

    # class -> target -> lists
    scores: Dict[str, Dict[str, Dict[str, list]]] = {}
    per_class_items: Dict[str, int] = {}
    unmatched, no_class, no_formula = [], [], {}
    drill = []

    for path in files:
        records = load_template_file(path)
        if not records:
            continue
        for iid, tmpl in records.items():
            m = master.get(iid)
            if not m:
                unmatched.append((os.path.basename(path), iid, tmpl.get("Name", "")))
                continue
            cname = resolve_class_name(m, master, parent_classes, class_id_set)
            if not cname:
                no_class.append((iid, tmpl.get("Name", "")))
                continue
            if cname == "Muzzle":
                cname = muzzle_subclass(m)
            cname = apply_emitter_splits(cname, m, tmpl, pistol_ids, F)
            if args.only_class and cname != args.only_class:
                continue
            func = F.get_formula_func(cname)
            if not callable(func):
                no_formula[cname] = no_formula.get(cname, 0) + 1
                continue

            targ = tmpl if args.with_template else None
            try:
                named = predict(func, m, tmpl, True, targ)
                bare = predict(func, m, tmpl, False, targ)
            except Exception as exc:
                print(f"  !! {cname} {iid} raised {type(exc).__name__}: {exc}")
                continue

            per_class_items[cname] = per_class_items.get(cname, 0) + 1
            cls = scores.setdefault(cname, {})
            for k, truth in tmpl.items():
                if isinstance(truth, bool) or not isinstance(truth, (int, float)):
                    continue
                if k not in named:
                    continue
                d = cls.setdefault(k, {"abs": [], "signed": [], "truth": [],
                                       "pred": [], "dep": False})
                d["abs"].append(abs(float(named[k]) - truth))
                d["signed"].append(float(named[k]) - truth)
                d["truth"].append(float(truth))
                d["pred"].append(float(named[k]))
                if abs(float(named[k]) - float(bare.get(k, named[k]))) > 1e-9:
                    d["dep"] = True
                if args.target and k == args.target:
                    drill.append((abs(float(named[k]) - truth), cname,
                                  tmpl.get("Name") or m.get("_name", ""),
                                  truth, float(named[k]), float(bare.get(k, 0.0))))

    total_items = sum(per_class_items.values())
    print(f"[scored]    {total_items} items across {len(scores)} classes"
          f"  (mode: {'template-clamped' if args.with_template else 'raw ML'})\n")

    if unmatched:
        print(f"[unmatched] {len(unmatched)} template item(s) absent from master "
              f"(custom items - the clone chain has to resolve these):")
        for fn, iid, nm in unmatched[:25]:
            print(f"    {fn:34} {iid}  {nm}")
        if len(unmatched) > 25:
            print(f"    ... and {len(unmatched) - 25} more")
        print()
    if no_class:
        print(f"[no class]  {len(no_class)} item(s) whose parent chain hit no known class\n")
    if no_formula:
        print("[no formula] classes with templates but no emitted function:")
        for c, n in sorted(no_formula.items(), key=lambda x: -x[1]):
            print(f"    {c:24} {n} item(s)")
        print()

    rows = []
    for cname, targets in scores.items():
        for tname, d in targets.items():
            n = len(d["abs"])
            mae = statistics.mean(d["abs"])
            bias = statistics.mean(d["signed"])
            scale = statistics.mean(abs(t) for t in d["truth"]) or 1.0
            nmae = 100.0 * mae / scale
            uniq = len(set(d["truth"]))
            zeros = sum(1 for t in d["truth"] if t == 0.0)

            # Zero-handling. EPS is scaled to the target so it means "small enough
            # that the game would not notice", not an absolute threshold.
            nonzero_mags = [abs(t) for t in d["truth"] if t != 0.0]
            eps = (min(nonzero_mags) * 0.5) if nonzero_mags else 1e-9
            leak_den = zeros
            leak_num = sum(1 for t, pr in zip(d["truth"], d["pred"])
                           if t == 0.0 and abs(pr) > eps)
            real_den = n - zeros
            miss_num = sum(1 for t, pr in zip(d["truth"], d["pred"])
                           if t != 0.0 and abs(pr) <= eps)
            sign_num = sum(1 for t, pr in zip(d["truth"], d["pred"])
                           if t != 0.0 and abs(pr) > eps and (pr > 0) == (t > 0))
            leak = 100.0 * leak_num / leak_den if leak_den else None
            miss = 100.0 * miss_num / real_den if real_den else None
            sign = 100.0 * sign_num / real_den if real_den else None
            flags = []
            if uniq <= 1:
                flags.append("DEGEN")
            elif zeros / n > 0.7:
                flags.append("SPARSE")
            if mae > 1e-12 and abs(bias) / mae > 0.9:
                flags.append("1-SIDED")
            if nmae > 25.0:
                flags.append("BIG")
            if leak is not None and leak > 50.0 and leak_den >= 5:
                flags.append("LEAK")
            if sign is not None and sign < 60.0 and real_den >= 5:
                flags.append("SIGN")
            static = tname in name_dep_static.get(
                re.sub(r"[^a-z0-9]+", "", cname.lower()), set())
            rows.append({
                "class": cname, "target": tname, "n": n, "mae": mae, "nmae": nmae,
                "bias": bias, "scale": scale, "uniq": uniq,
                "zeros": zeros, "leak": leak, "miss": miss, "sign": sign,
                "dep": d["dep"], "static": static, "flags": " ".join(flags),
            })

    def _pct(v):
        return "    -" if v is None else f"{v:5.0f}"

    print("=" * 126)
    print(f"{'class':22} {'target':28} {'n':>4} {'MAE':>11} {'nMAE%':>7} "
          f"{'bias':>11} {'0s':>4} {'leak':>5} {'miss':>5} {'sign':>5} {'nd':>3}  flags")
    print("=" * 126)
    for cname in sorted(scores, key=lambda c: -per_class_items.get(c, 0)):
        sub = [r for r in rows if r["class"] == cname and r["nmae"] >= args.min_nmae]
        if not sub:
            continue
        print(f"\n-- {cname}  ({per_class_items[cname]} items) "
              f"{'-' * max(0, 80 - len(cname))}")
        for r in sorted(sub, key=lambda r: -r["nmae"]):
            nd = "YES" if r["dep"] else ("~" if r["static"] else "-")
            print(f"{'':22} {r['target']:28} {r['n']:4} {r['mae']:11.4f} "
                  f"{r['nmae']:7.1f} {r['bias']:+11.4f} {r['zeros']:4} "
                  f"{_pct(r['leak'])} {_pct(r['miss'])} {_pct(r['sign'])} "
                  f"{nd:>3}  {r['flags']}")

    dep = [r for r in rows if r["dep"]]
    print("\n" + "=" * 108)
    if dep:
        print(f"!! PARITY: {len(dep)} target(s) still change when 'Name' is present:")
        for r in sorted(dep, key=lambda r: -r["nmae"]):
            print(f"    {r['class']:22} {r['target']:28} nMAE {r['nmae']:6.1f}%")
    else:
        print("OK PARITY: no target's prediction depends on whether 'Name' is set.")

    # nMAE% alone puts near-zero sparse mod deltas at the top and buries real
    # problems, so rank the headline lists by the failures that actually matter:
    # inventing stats on items the author zeroed, and pushing a stat the wrong way.
    # Rank by the NUMBER of items affected, not the percentage: leaking onto all
    # 13 zeroed RicochetChance rows is a smaller problem than leaking onto 59
    # FragmentationChance rows, and sorting by percentage alone hides that.
    leaky = [r for r in rows if r["leak"] is not None and r["zeros"] >= 5
             and r["leak"] > 0]
    for r in leaky:
        r["leak_n"] = round(r["leak"] * r["zeros"] / 100.0)
    leaky.sort(key=lambda r: (-r["leak_n"], -r["leak"]))
    if leaky:
        print("\nWorst 15 by ZERO LEAK (author wrote 0, model writes a value):")
        for r in leaky[:15]:
            print(f"    {r['class']:22} {r['target']:28} {r['leak_n']:5} items  "
                  f"({r['leak']:3.0f}% of {r['zeros']:4} zeroed)   MAE {r['mae']:>10.4f}")

    wrong_sign = [r for r in rows if r["sign"] is not None
                  and (r["n"] - r["zeros"]) >= 5 and r["sign"] < 75.0]
    wrong_sign.sort(key=lambda r: r["sign"])
    if wrong_sign:
        print("\nWorst 15 by WRONG SIGN (model pushes the stat the wrong way):")
        for r in wrong_sign[:15]:
            print(f"    {r['class']:22} {r['target']:28} {r['sign']:5.0f}% correct  "
                  f"over {r['n'] - r['zeros']:4} real values   MAE {r['mae']:>10.4f}")

    worst = sorted(rows, key=lambda r: -r["nmae"])[:20]
    print("\nWorst 20 targets overall by nMAE% (read with the sparse caveat above):")
    for r in worst:
        print(f"    {r['class']:22} {r['target']:28} {r['nmae']:7.1f}%  "
              f"MAE {r['mae']:>10.4f}  {r['flags']}")

    degen = [r for r in rows if "DEGEN" in r["flags"]]
    if degen:
        print(f"\n{len(degen)} degenerate target(s) - truth is constant, drop or pin these:")
        for r in degen:
            print(f"    {r['class']:22} {r['target']:28} constant, "
                  f"model emits mean|err| {r['mae']:.4f}")

    if args.target:
        print(f"\nper-item breakdown for {args.target}")
        print(f"{'class':18} {'name':44} {'truth':>10} {'pred':>10} {'err':>10}")
        for _, cname, nm, truth, pred, bare in sorted(drill, reverse=True):
            print(f"{cname:18} {nm[:44]:44} {truth:10.3f} {pred:10.3f} {pred-truth:+10.3f}")

    if args.csv:
        import csv
        with open(args.csv, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
        print(f"\nwrote {len(rows)} rows to {args.csv}")


if __name__ == "__main__":
    sys.exit(main())
