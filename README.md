# SPT-Realism-Compat-Creator

Legend:



All Panes:





$itemID - This is the MongoID of the item in question. It is a 24 character string of letters and numbers, and every item in the game has one. Anywhere it is referenced below or in the program, it must be in quotations, and it must fully replace the "$itemID" placeholder, unlike the other variables.



Name - This can be anything at all. The program takes the item name from the mod's data.



$type - must be "RealismMod.$itemtype, RealismMod". The $itemtype can be Ammo, Gun, Gear or WeaponMod only.



WeapType and OperationType are only for guns.



WeapType - Can be left blank, only fill if it is: "DI" (direct impingement ala M4A1), "bullpup" for bullpups, "pistol" for pistols (duh) and "short\_AK" for gas piston driven short semi-autos/full autos



OperationType - Can be left blank, only fill if it is: "buffer" for a weapon that uses a buffer tube for its action. Not used on guns that use an adapter to have a buffer tube for a stock, only for guns that require the buffer. The other options are pretty explanatory, "magForward", "tubefed", "tubefed-m", "p90", with "p90" being for guns that have the mag horizontally on the top.



ModType - "bipod", "short\_barrel", "booster", "762x39", "300", "556", "366TKM", "308", "277",

        "sight", "mount", "shotTube", "foregrip\_adapter", "shot\_pump\_grip\_adapt", "counterWeight",

        "muzzle\_supp\_adapter", "sig\_taper\_brake", "barrel\_2slot",

        "grip\_stock\_adapter", "buffer\_adapter", "stock\_adapter",

        "hydraulic\_buffer", "buffer", "buffer\_stock", "Stock", "StockR", "StockN", "StockF"





value - a number, positive or negative



bool - must be either "true" or "false"







Left Pane





 	Paths button - set all of the paths required to find your SPT install, realism install and add any ignore keys



 	 - Mod Selection:

 				Each mod folder will be listed in this window, and opening one up will show you a list of items contained within the mod. Barring any bugs, you should ignore anything that does not have a name in this section as they are most likely either placeholders or MongoID's that are being picked up by the mod but don't correspond to an item.



 				Green Highlight - Template found locally

 				Yellow Highlight - No Template exists locally



 	-User Templates:

 				This section breaks down all of the existing Realism Templates in your SPT install. Anything with ".json" in the main window is a template that is not stored in a sub folder, anything without ".json" is a folder that contains sub-items. Each JSON can be opened to see the individual items within, and can then be edited.





Middle Pane

 	Mid-Left Pane:

 			Shows the base game item stats from the mod

 	Mid-Right Pane:

 			Shows realism stats of the item the mod creator chose to clone. In order to bring new items into the game, a basegame object must be cloned. This can give you a good idea of what sort of stats to expect for a similar item but be aware some items may be cloned due to things such as parts compatability, or lack of basegame stats that need to be overwritten so do not take this data as gospel.





Right Pane:

 	Lists the parent and $type that the program has deduced from the mod stats. There is always a chance this is wrong so if you run into issues, double check this. Below the Formula Category, it will tell you what the formula you've selected (see below) has for $type, how many stats fields are addable to the item, and which special fields are selectable for said item



 		Formula Category - This lists all of the formulas currently available for items. Select the one that is closest to the item you are making the compat for. All of the data it writes below is editable and/or removable, and you can also add new fields. The formula is just a best guess to start you off. Selecting "Reload formulas.py" is only for if you are editing the formula's script in another program and you want those changes to apply immediately.



 

 











Below is an outline of what each value does, and if it is required or not. Note that missing required fields will, in the case of a missing ItemID or type, cause the file to not be loaded by realism, and in the case of a missing modtype when one is required, cause the weapon or attachment in question to either lock your hands up or shoot directly into the ground in front.







    Ammo:



    "$itemID": {

        "$type": "RealismMod.Ammo, RealismMod",

        "ItemID": "$itemID",

        "Name": "$\_shortname or $name",

 		"Damage": value,

 		"PenetrationPower": value

        "LoyaltyLevel": value,

        "BasePriceModifier": 1

    },

    //gear

    "$itemID": {

        "$type": "RealismMod.Gear, RealismMod",

        "ItemID": "$itemID",

        "Name": "$\_shortname or $name",

        "AllowADS \[should the item block ADS, if toggleable faceshield only applies when deployed]": bool,

        "LoyaltyLevel \[Trader LL if using trader changes]": value,

        "ReloadSpeedMulti \[higher is better]": value,

        "Comfort \[lower is better, weight modifier]": value,

        "speedPenaltyPercent \[lower is worse]": value,

        "mousePenalty \[keep at 0]": value,

        "weaponErgonomicPenalty \[lower is worse]": value

    },

    //attatchments

    "$itemID": {

        "$type": "RealismMod.WeaponMod, RealismMod",

        "ItemID": "$itemID",

        "Name": "$\_shortname or $name",

        "ModType \[refer to documentation linked in the SPT mod page]": "",

        "VerticalRecoil \[lower is better]": value

        "HorizontalRecoil \[lower is better]": value,

        "Dispersion \[lower is better, the overall spread]": value,

        "CameraRecoil \[lower is better]": value,

        "AutoROF \[1 means 1% ROF increase]": value,

        "SemiROF\[2.5 means 2.5% ROF increase]": value,

        "ModMalfunctionChance \[lower is better]": value,

        "CanCycleSubs \[does it allow the cycling of subsonic ammo in calibres that can't normally cycle subs]": false,

        "Accuracy": value,

        "HeatFactor \[higher is worse]": value,

        "CoolFactor \[higher is better]": value,

        "DurabilityBurnModificator \[higher is worse]": value,

        "Velocity \[2% increase in muzzle velocity, if it's a barrel use Realism stats of comparable barrel length in same calibre]": value,

        "RecoilAngle \[5 = 5+ percent recoil angle, towards 90 degrees which is straight up]": value,

        "ConflictingItems \[items that should conflict, will be combined with orginal, not overwrite]": \[],

        "Ergonomics": value,

        "Weight": value,

        "Loudness \[negative is quieter, used for deafening mechanic and SAIN]": value,

        "Convergence \[Higher = more snappy, less floaty, less muzzle flip and recoil climb]": value,

        "LoyaltyLevel": 3,

        "Flash \[higher means more gas if suppressor or non-muzzle device, more flash otherwise]": value,

        "Handling \[weapon will have less inertia and drag when moving mouse or walking/strafing]": value,

        "AimStability \[weapon will have less aim sway]": value,

        "AimSpeed \[Higher is better]": value,

        "StockAllowADS \[Overrides gear items that are set to block ADS]": bool,

        "HasShoulderContact \[does the stock actually touch the player's shoulder]": bool,

        "CenterOfImpact \[accuracy if barrel, higher = less accurate]": value,

        "ModShotDispersion \[negative values reduse the spread of buckshot]": value

    },

    //weapons

    "$itemID": {

        "$type": "RealismMod.Gun, RealismMod",

        "ItemID": "$itemID",

        "Name": "$\_shortname or $name",

        "WeapType \[refer to documentation linked in the SPT mod page]": "",

        "OperationType \[refer to documentation linked in the SPT mod page]": "",

        "WeapAccuracy \[base weapon accuracy modifier]": value,

        "BaseTorque \[the default balance of the rifle, negative values means more front heavy]": value,

        "HasShoulderContact \[does the weapon come with a built in stock that contacs the shoulder]": bool,

        "Ergonomics": value,

        "VerticalRecoil": value,

        "HorizontalRecoil": value,

        "Dispersion \[spread]": value,

        "CameraRecoil": value,

        "VisualMulti \[visual recoil, higher = more visual recoil (shaking, rotating))]": value,

        "Convergence \[snappiness/flatness]": value,

        "RecoilAngle \[90 is straight up, 65 is to the right]": value,

        "BaseMalfunctionChance": value,

        "HeatFactorGun": value,

        "HeatFactorByShot": value,

        "CoolFactorGun": value,

        "CoolFactorGunMods": value,

        "AllowOverheat": bool,

        "CenterOfImpact \[accuracy if build in barrel, higher = less accurate]": value,

        "HipAccuracyRestorationDelay": value,

        "HipAccuracyRestorationSpeed": value,

        "HipInnaccuracyGain": value,

        "ShotgunDispersion": 0,

        "Velocity \[if the gun has a built in barrel, it will need a velocity stat, refer to Realism stats for barrels and weapons]": value,

        "RecoilDamping \[up and down wiggle, higher = wigglier]": value,

        "RecoilHandDamping \[back and forward, higher = wigglier]": value,

        "WeaponAllowADS \[should weapon allow ADS regardless if gear blocks it and what stock it has]": bool,

        "Weight": value,

        "DurabilityBurnRatio": value,

        "AutoROF": value,

        "SemiROF": value,

        "LoyaltyLevel": value,

        "BaseReloadSpeedMulti \[reload speed modifier]": value,

        "BaseChamberSpeedMulti \[chambering a round speed modifier, applies to manually operated guns too]": value,

        "MinChamberSpeed": value,

        "MaxChamberSpeed": value,

        "IsManuallyOperated \[true if a bolt or pump action]": bool,

        "BaseChamberCheckSpeed": value,

        "BaseFixSpeed \[malfunction fix speed]": value,

        "OffsetRotation \[higher is worse, how much the gun is off target after firing]": value,

        "RecoilIntensity \[overall recoil procedrual animation itensity]": value

    }









Clone Compats -

TemplateID - Only used in a pure clone compat, which directly clones the realism stats of an existing basegame item. Useful for reskins or quickly fixing the "blablabla" errors, but cloning some items can cause issues, most notably cloning a weapon that does not have integrated ironsights or an integrated barrel and applying it to a new modded gun that does contain those.

The program will not create a clone compat, but it is useful to know especially for editing older compat files or quickly troubleshooting on your own.

Example, a clone compat template would look like:



    "$itemID": {

        "$type": "RealismMod.Ammo, RealismMod",

        "ItemID": "$itemID",

        "Name": "$\_shortname or $name",

 	"TemplateID": "$itemtoclone"

}



and an item would look like:

    "692b153abe0fe3f9189e08b5": {

        "$type": "RealismMod.Gun, RealismMod",

        "ItemID": "692b153abe0fe3f9189e08b5",

        "Name": "NerfGun",

 	"TemplateID": "66015072e9f84d5680039678"

}



For magazines values:



Reload speed: negative value is slower

LoadUnloadModifier and CheckTimeModifier: positive value is slower





