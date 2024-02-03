import json
from storage_manager import StorageManager


class GpsState:

    __slots__ = (
        "mode",
        "time",
        "ept",
        "lat",
        "lon",
        "alt",
        "epx",
        "epy",
        "epv",
        "track",
        "speed",
        "climb",
        "eps",
        "epc",
        "fix_status",
    )

    def __init__(self) -> None:
        self.mode = 0
        self.time = ""
        self.ept = 0
        self.lat = 0
        self.lon = 0
        self.alt = 0
        self.epx = 0
        self.epy = 0
        self.epv = 0
        self.track = 0
        self.speed = 0
        self.climb = 0
        self.eps = 0
        self.epc = 0
        self.fix_status = "NO_FIX"

    def update(self, state):
        if "mode" in state:
            self.mode = state["mode"]
        if "time" in state:
            self.time = state["time"]
        if "ept" in state:
            self.ept = state["ept"]
        if "lat" in state:
            self.lat = state["lat"]
        if "lon" in state:
            self.lon = state["lon"]
        if "alt" in state:
            self.alt = state["alt"]
        if "epx" in state:
            self.epx = state["epx"]
        if "epy" in state:
            self.epy = state["epy"]
        if "epv" in state:
            self.epv = state["epv"]
        if "track" in state:
            self.track = state["track"]
        if "speed" in state:
            self.speed = state["speed"]
        if "climb" in state:
            self.climb = state["climb"]
        if "eps" in state:
            self.eps = state["eps"]
        if "epc" in state:
            self.epc = state["epc"]
        if "fix_status" in state:
            self.fix_status = state["fix_status"]


class ImuState:

    __slots__ = (
        "heading",
        "accel_x",
        "accel_y",
        "accel_z",
        "gyro_x",
        "gyro_y",
        "gyro_z",
        "mag_x",
        "mag_y",
        "mag_z",
    )

    def __init__(self) -> None:
        self.heading = 0
        self.accel_x = 0
        self.accel_y = 0
        self.accel_z = 0
        self.gyro_x = 0
        self.gyro_y = 0
        self.gyro_z = 0
        self.mag_x = 0
        self.mag_y = 0
        self.mag_z = 0

    def update(self, state):
        if "heading" in state:
            self.heading = state["heading"]
        if "accel_x" in state:
            self.accel_x = state["accel_x"]
        if "accel_y" in state:
            self.accel_y = state["accel_y"]
        if "accel_z" in state:
            self.accel_z = state["accel_z"]
        if "gyro_x" in state:
            self.gyro_x = state["gyro_x"]
        if "gyro_y" in state:
            self.gyro_y = state["gyro_y"]
        if "gyro_z" in state:
            self.gyro_z = state["gyro_z"]
        if "mag_x" in state:
            self.mag_x = state["mag_x"]
        if "mag_y" in state:
            self.mag_y = state["mag_y"]
        if "mag_z" in state:
            self.mag_z = state["mag_z"]


class SimulationState:

    __slots__ = (
        "time",
        "timer",
        "primary_oxygen",
        "secondary_oxygen",
        "suits_pressure",
        "sub_pressure",
        "o2_pressure",
        "o2_rate",
        "h2o_gas_pressure",
        "h2o_liquid_pressure",
        "sop_pressure",
        "sop_rate",
        "heart_rate",
        "fan_tachometer",
        "battery_capacity",
        "temperature",
        "battery_time_left",
        "o2_time_left",
        "h2o_time_left",
        "battery_percentage",
        "battery_output",
        "oxygen_primary_time",
        "oxygen_secondary_time",
        "water_capacity",
    )

    def __init__(self) -> None:
        self.time = 0
        self.timer = ""
        self.primary_oxygen = 0
        self.secondary_oxygen = 0
        self.suits_pressure = 0
        self.sub_pressure = 0
        self.o2_pressure = 0
        self.o2_rate = 0
        self.h2o_gas_pressure = 0
        self.h2o_liquid_pressure = 0
        self.sop_pressure = 0
        self.sop_rate = 0
        self.heart_rate = 0
        self.fan_tachometer = 0
        self.battery_capacity = 0
        self.temperature = 0
        self.battery_time_left = 0
        self.o2_time_left = 0
        self.h2o_time_left = 0
        self.battery_percentage = 0
        self.battery_output = 0
        self.oxygen_primary_time = 0
        self.oxygen_secondary_time = 0
        self.water_capacity = 0

    def update(self, state):
        if "time" in state:
            self.time = state["time"]
        if "timer" in state:
            self.timer = state["timer"]
        if "primary_oxygen" in state:
            self.primary_oxygen = state["primary_oxygen"]
        if "secondary_oxygen" in state:
            self.secondary_oxygen = state["secondary_oxygen"]
        if "suits_pressure" in state:
            self.suits_pressure = state["suits_pressure"]
        if "sub_pressure" in state:
            self.sub_pressure = state["sub_pressure"]
        if "o2_pressure" in state:
            self.o2_pressure = state["o2_pressure"]
        if "o2_rate" in state:
            self.o2_rate = state["o2_rate"]
        if "h2o_gas_pressure" in state:
            self.h2o_gas_pressure = state["h2o_gas_pressure"]
        if "h2o_liquid_pressure" in state:
            self.h2o_liquid_pressure = state["h2o_liquid_pressure"]
        if "sop_pressure" in state:
            self.sop_pressure = state["sop_pressure"]
        if "sop_rate" in state:
            self.sop_rate = state["sop_rate"]
        if "heart_rate" in state:
            self.heart_rate = state["heart_rate"]
        if "fan_tachometer" in state:
            self.fan_tachometer = state["fan_tachometer"]
        if "battery_capacity" in state:
            self.battery_capacity = state["battery_capacity"]
        if "temperature" in state:
            self.temperature = state["temperature"]
        if "battery_time_left" in state:
            self.battery_time_left = state["battery_time_left"]
        if "o2_time_left" in state:
            self.o2_time_left = state["o2_time_left"]
        if "h2o_time_left" in state:
            self.h2o_time_left = state["h2o_time_left"]
        if "battery_percentage" in state:
            self.battery_percentage = state["battery_percentage"]
        if "battery_output" in state:
            self.battery_output = state["battery_output"]
        if "oxygen_primary_time" in state:
            self.oxygen_primary_time = state["oxygen_primary_time"]
        if "oxygen_secondary_time" in state:
            self.oxygen_secondary_time = state["oxygen_secondary_time"]
        if "water_capacity" in state:
            self.water_capacity = state["water_capacity"]


class UiaState:

    __slots__ = (
        "emu1_pwr_switch",
        "ev1_supply_switch",
        "emu1_water_waste",
        "emu1_o2_supply_switch",
        "o2_vent_switch",
        "depress_pump_switch",
    )

    def __init__(self) -> None:
        self.emu1_pwr_switch = False
        self.ev1_supply_switch = False
        self.emu1_water_waste = False
        self.emu1_o2_supply_switch = False
        self.o2_vent_switch = False
        self.depress_pump_switch = False

    def update(self, state):
        if "emu1_pwr_switch" in state:
            self.emu1_pwr_switch = state["emu1_pwr_switch"]
        if "ev1_supply_switch" in state:
            self.ev1_supply_switch = state["ev1_supply_switch"]
        if "emu1_water_waste" in state:
            self.emu1_water_waste = state["emu1_water_waste"]
        if "emu1_o2_supply_switch" in state:
            self.emu1_o2_supply_switch = state["emu1_o2_supply_switch"]
        if "o2_vent_switch" in state:
            self.o2_vent_switch = state["o2_vent_switch"]
        if "depress_pump_switch" in state:
            self.depress_pump_switch = state["depress_pump_switch"]


class SpecState:

    __slots__ = ("SiO2", "TiO2", "Al2O3", "FeO", "MnO", "MgO", "CaO", "K2O", "P2O3")

    def __init__(self) -> None:
        self.SiO2 = 0
        self.TiO2 = 0
        self.Al2O3 = 0
        self.FeO = 0
        self.MnO = 0
        self.MgO = 0
        self.CaO = 0
        self.K2O = 0
        self.P2O3 = 0

    def update(self, state):
        if "SiO2" in state:
            self.SiO2 = state["SiO2"]
        if "TiO2" in state:
            self.TiO2 = state["TiO2"]
        if "Al2O3" in state:
            self.Al2O3 = state["Al2O3"]
        if "FeO" in state:
            self.FeO = state["FeO"]
        if "MnO" in state:
            self.MnO = state["MnO"]
        if "MgO" in state:
            self.MgO = state["MgO"]
        if "CaO" in state:
            self.CaO = state["CaO"]
        if "K2O" in state:
            self.K2O = state["K2O"]
        if "P2O3" in state:
            self.P2O3 = state["P2O3"]


class RoverState:

    __slots__ = ("lat", "lon", "navigation_status", "goal_lat", "goal_lon")

    def __init__(self) -> None:
        self.lat = 0
        self.lon = 0
        self.navigation_status = "NOT_NAVIGATING"
        self.goal_lat = 0
        self.goal_lon = 0

    def update(self, state):
        if "lat" in state:
            self.lat = state["lat"]
        if "lon" in state:
            self.lon = state["lon"]
        if "navigation_status" in state:
            self.navigation_status = state["navigation_status"]
        if "goal_lat" in state:
            self.goal_lat = state["goal_lat"]
        if "goal_lon" in state:
            self.goal_lon = state["goal_lon"]


class WorldState:

    _self = None

    def __new__(cls):
        if cls._self is None:
            cls._self = super().__new__(cls)
        return cls._self

    def __init__(self) -> None:
        self.gps_state = GpsState()
        self.imu_state = ImuState()
        self.sim_state = SimulationState()
        self.uia_state = UiaState()
        self.spec_state = SpecState()
        self.rover_state = RoverState()
        # self.bot_state = BotState()

    def update(self, state):
        self.self = WorldState()
        state = json.loads(state)
        StorageManager.log_state(state)
        self.gps_state.update(state["gps_msg"])
        self.imu_state.update(state["imu_msg"])
        self.sim_state.update(state["simulation_states"])
        self.uia_state.update(state["uia_state"])
        self.spec_state.update(state["spec_message"])
        self.rover_state.update(state["rover_msg"])
