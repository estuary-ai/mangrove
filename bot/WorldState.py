from bot.BotState import BotState


class GpsState:

    __slots__ = \
    'mode',
    'time',
    'ept',
    'lat',
    'lon',
    'alt',
    'epx',
    'epy',
    'epv',
    'track',
    'speed',
    'climb',
    'eps',
    'epc',
    'fix_status'

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


class ImuState:

    __slots__ = \
    'heading',
    'accel_x',
    'accel_y',
    'accel_z',
    'gyro_x',
    'gyro_y',
    'gyro_z',
    'mag_x',
    'mag_y',
    'mag_z'

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


class SimulationState:

    __slots__ = \
    'time',
    'timer',
    'primary_oxygen',
    'secondary_oxygen',
    'suits_pressure',
    'sub_pressure',
    'o2_pressure',
    'o2_rate',
    'h2o_gas_pressure',
    'h2o_liquid_pressure',
    'sop_pressure',
    'sop_rate',
    'heart_rate',
    'fan_tachometer',
    'battery_capacity',
    'temperature',
    'battery_time_left',
    'o2_time_left',
    'h2o_time_left',
    'battery_percentage',
    'battery_output',
    'oxygen_primary_time',
    'oxygen_secondary_time',
    'water_capacity'

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


class UiaState:

    __slots__ = \
    'emu1_pwr_switch',
    'ev1_supply_switch',
    'emu1_water_waste',
    'emu1_o2_supply_switch',
    'o2_vent_switch',
    'depress_pump_switch'

    def __init__(self) -> None:
        self.emu1_pwr_switch = False
        self.ev1_supply_switch = False
        self.emu1_water_waste = False
        self.emu1_o2_supply_switch = False
        self.o2_vent_switch = False
        self.depress_pump_switch = False


class SpecState:

    __slots__ = \
    'SiO2',
    'TiO2',
    'Al2O3',
    'FeO',
    'MnO',
    'MgO',
    'CaO',
    'K2O',
    'P2O3'

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


class RoverState:

    __slots__ = \
    'lat',
    'lon',
    'navigation_status',
    'goal_lat',
    'goal_lon'

    def __init__(self) -> None:
        self.lat = 0
        self.lon = 0
        self.navigation_status = "NOT_NAVIGATING"
        self.goal_lat = 0
        self.goal_lon = 0


class WorldState:

    def __init__(self) -> None:
        self.gps_state = GpsState()
        self.imu_state = ImuState()
        self.sim_state = SimulationState()
        self.uia_state = UiaState()
        self.spec_state = SpecState()
        self.rover_state = RoverState()
        self.bot_state = BotState()
