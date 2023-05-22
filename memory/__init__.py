from .WorldState import WorldState

def get_world_state():
    return __gWorldState

__gWorldState = WorldState()