                   
import random

                          
_current_outfit = None
_current_hair = None

BASE_STATE = {
    'formchange': -1.0,
    'negligeeONOFF': 0.0,
    'mizugiONOFF': 0.0,
    'minzokucloth': 0.0,
    'bunny': 0.0,
    'bath_taol_ON': 0.0,
    'FudeONOFF': 0.0,
    'pantsuONFOFF': 0.0,
    'buraONFOFF': 0.0,
    'negligeeinnerONOFF': 0.0,
    'mizugiSUKE': 0.0,
    'bunnycuffsONOFF': 0.0,
    'bunnyamiamiONOFF': 0.0,
    'bunnyneckONOFF': 0.0,
    'bunnyearONOFF': 0.0
}

HAIRSTYLES = {
    "bun": 0.0,
    "loose": 30.0
}

OUTFITS = {
    "uniform_tight": {"formchange": 0.0},
    "uniform_dress": {"formchange": 1.0},
    "sleepwear": {"formchange": -1.0, "negligeeONOFF": 1.0, "negligeeinnerONOFF": 0.0},
    "swimsuit": {"formchange": -1.0, "mizugiONOFF": 1.0, "mizugiSUKE": 0.0, "hearchange": HAIRSTYLES["bun"]},
    "ethnic_wear": {"formchange": -1.0, "minzokucloth": 1.0, "FudeONOFF": 0.0},           
    "ethnic_cloak": {"formchange": -1.0, "minzokucloth": 1.0, "FudeONOFF": 1.0},         
    "towel": {"formchange": -1.0, "bath_taol_ON": 1.0, "buraONFOFF": 30.0, "pantsuONFOFF": random.choice([0.0, 30.0])},
    "bunny": {"formchange": -1.0, "bunny": 1.0}
}


def get_outfit_params(outfit_name, hair_style=None):
    global _current_outfit, _current_hair

                   
    is_new_outfit = (_current_outfit != outfit_name)
    _current_outfit = outfit_name

    params_to_apply = BASE_STATE.copy()

    if outfit_name in OUTFITS:
        params_to_apply.update(OUTFITS[outfit_name])

                
                                
    if "hearchange" in params_to_apply:
        forced_val = params_to_apply["hearchange"]
                                                   
        for k, v in HAIRSTYLES.items():
            if v == forced_val:
                _current_hair = k
                break
                  
    else:
        if hair_style in HAIRSTYLES:
                      
            _current_hair = hair_style
            params_to_apply["hearchange"] = HAIRSTYLES[_current_hair]
        else:
                                         
            if _current_hair is None or is_new_outfit:
                _current_hair = random.choices(["loose", "bun"], weights=[85, 15], k=1)[0]

                                         
            params_to_apply["hearchange"] = HAIRSTYLES[_current_hair]

    return params_to_apply