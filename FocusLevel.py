from enum import Enum

class FocusLevel(Enum):
    POS_HIGH = 10.5
    POS_MEDIUM = 6.0
    POS_LOW = 1.0
    NEG_LOW = -1.0
    NEG_MEDIUM = -4.0
    NEG_HIGH = -9.0

    # TODO for sure better train a domain specific language model instead

def init_words_focus_assets():
    regular_neg_lo_focus = [
        'lo', 'then', 'altaforte', 'generate', 'la',
        'stan', 'plate', 'his', 'her', 
        'theology', 'once', 'me',
            # maybe not so much ->
        'and', 'leg', 'so', 'some', 'little', 'a',
        'simple', 'better', 'bade', 'matter', 'them',
    ]
    regular_pos_lo_focus = [
        'close',
        'hold',
        'turn', 'on', 'off',
        'rock', 'show', 'screen',
        'read',
        'measurement',
        'monitoring', 'heart', 
        'stand',
        'start', 'recording',
        'sub',
        'gas',
        'red',
    ]

    regular_pos_med_focus = [
        'heads', 'up', 'display', 'show',
        'sample', 'rate', 'rock',
        'respiratory', 'note', 'map', 'terrain',
        'green', 'blue', 
        'pin',
        'read', 'condition', 'suit',
        'path',  
        'checklist',
        'data', 
        'take', 'photo',
        'vitals',
        'audio',
        'toggle',
        'set', 'north',
        'finder',
        'geo_logy', 'level', 
    ]

    regular_pos_hi_focus = [
        'map', 'terrain', 'battery', 'oxygen', 'rate',
        'pin', 'road', 'tag', 'hide',
    ]

    tagging_med_focus = [
        'measurement', 'rock', 'regolith', 'coordinates', 'sun',
        'shining', 'shine', 'visbility', 'outcrop', 'poor', 'optimal',
        'boulder', 'outskirts', 'crater', 'rim',
        'landslide', 'lava', 'flow', 'PSR', 'contacts', 'litho_logies',
        'pick', 'hammer', 'tools', 'used', 'using', 'use',
        'fist-sized', 'fist', 'shape', 'dimension', 'measures', 'centimeters',
        'inches', 'chip off', 'chip', 'fragment', 'scoop', 'material',
        'range', 'appearance',
        'color', 'dark', 'gray', 'basalts', 'white', 'anorthosites', 'mottled',
        'breccias', 'black', 'green', 'glass', 'beads', 
        'appearance' , 'texture', 'fine', 'grained', 'coarse',
        'vesiculated', 'coherent', 'brecciated', 'friable',
        'make out', 'variety', 'clasts', 'shiny', 'ilmenite',
        'opaque', 'phases', 'initial', 'geo_logic', 
        'interpretation', 'origin', 'breccia', 'formed', 'impacts',
        'anorthosite', 'represents', 'Moon’s', 'primary', 'crust',
        'secondary', 'rock', 'over',
    ]
    
    tagging_hi_focus = [
        'volcanic', 'orange', 'exit'
    ]

    tmp = _remove_from([regular_pos_lo_focus,
                            regular_pos_med_focus,
                            regular_pos_hi_focus])
    regular_pos_lo_focus = tmp[0]
    regular_pos_med_focus = tmp[1]
    regular_pos_hi_focus = tmp[2]

    tmp = _remove_from([tagging_med_focus,
                            tagging_hi_focus,
                            regular_pos_lo_focus,
                            regular_pos_med_focus,
                            regular_pos_hi_focus])

    tagging_med_focus = tmp[0]
    tagging_hi_focus = tmp[1]

    return [
        regular_neg_lo_focus,
        regular_pos_lo_focus,
        regular_pos_med_focus,
        regular_pos_hi_focus,
        tagging_med_focus,
        tagging_hi_focus
    ]






def _remove_from(lists):
    newListOfSets = []
    for i in range(len(lists)-1):
        othersSet = set()
        for other in lists[i+1:]:
            othersSet = othersSet.union(set(other))
        aSet = set(lists[i]).difference(othersSet)
        newListOfSets.append(aSet)
    newListOfSets.append(set(lists[-1]))
    return newListOfSets
    