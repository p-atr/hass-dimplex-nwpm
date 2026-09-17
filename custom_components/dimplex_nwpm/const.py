"""Constants for the Dimplex NWPM Touch integration."""

from datetime import timedelta
from typing import Final

DOMAIN: Final = "dimplex_nwpm"
MANUFACTURER: Final = "Dimplex"

CONF_USE_MODBUS: Final = "use_modbus"

# Settings and slowly changing values are not part of the gateway telemetry
# configuration, so they are polled over MQTT in addition to the push updates.
POLL_INTERVAL: Final = timedelta(seconds=60)

# Datapoint ranges read on every poll. Ranges are kept small so that a
# datapoint missing on an older WPM software version only skips that range.
POLL_RANGES: Final[tuple[str, ...]] = (
    "1285-1305a",
    "1292a",
    "1297a",
    "637-638a",
    "629-632a",
    "1559-1560u",
    "530-533u",
    "714-715u",
    "1108u",
    "1564-1565u",
    "766-768u",
    "700-701a",
    "773u",
    "509u",
    "851-853u",
    "931-933u",
    "1042-1045u",
    "1074u",
    "1150u",
    "1153u",
    "1155u",
    "1481u",
    "564a",
    "750i",
    "1300-1308u",
    "1380-1390u",
    "3-4d",
    "1402d",
    "1245d",
    "1454d",
    "698-699d",
    "1500-1535d",
    "2662u",
    "2663i",
    "683a",
    "556a",
    "601a",
    "604a",
    "1280a",
    "1284a",
    "4865-4866a",
    "1260-1261i",
    "1472i",
    "1473-1475i",
    "1550i",
    "1556-1557i",
    "1991i",
    "2666-2668i",
    "2670i",
    "1572-1575i",
    "1578-1589i",
    "1592-1597i",
    "1604i",
    "1627-1634i",
    "1791i",
    "1660-1662i",
    "1406d",
    "1409d",
    "1413-1416d",
    "1249-1250d",
    "1491-1496u",
    "1647-1649i",
    "1675-1683i",
)

# Configuration flags ("conditions") of the heat pump manager describing the
# installed equipment. They only change when a technician reconfigures the
# system, so they are read once during setup and decide which entities exist.
CONDITION_RANGES: Final[tuple[str, ...]] = (
    "932d",
    "1001-1082d",
    "1099-1106d",
    "1148-1156d",
    "1171-1174d",
    "1194-1195d",
)

COND_INVERTER: Final = "932d"
COND_THERMAL_DISINFECTION: Final = "1001d"
COND_HEAT_METER: Final = "1002d"
COND_HEATING: Final = "1004d"
COND_REVERSIBLE: Final = "1007d"
COND_TWO_COMPRESSORS: Final = "1008d"
COND_ADDITIONAL_PUMP: Final = "1016d"
COND_AIR_HEAT_PUMP: Final = "1041d"
COND_PIPE_HEATER: Final = "1076d"
COND_IMMERSION_HEATER: Final = "1077d"
COND_BIVALENT: Final = "1082d"
COND_HOT_WATER_CIRCULATION: Final = "1171d"
COND_ROOM_SENSOR_1: Final = "1009d"
COND_ROOM_SENSOR_2: Final = "1010d"
COND_ROOM_SENSOR_3: Final = "1011d"
COND_REGENERATIVE: Final = "1032d"
COND_HEAT_METER_TOTAL: Final = "1039d"
COND_HOT_GAS_THERMOSTAT: Final = "1174d"
COND_COOLING: Final = "1005d"
COND_HEAT_METER_HOT_WATER: Final = "1017d"
COND_HEAT_METER_PRIMARY: Final = "1018d"
COND_HEATING_CIRCUIT_3: Final = "1026d"
COND_PASSIVE_COOLING: Final = "1028d"
COND_HEATING_CIRCUIT_2: Final = "1029d"
COND_HOT_WATER: Final = "1033d"
COND_POOL: Final = "1035d"
COND_HEAT_METER_POOL: Final = "1040d"
COND_SOLAR: Final = "1042d"
COND_ROOM_CONTROL_1: Final = "1056d"
COND_ROOM_CONTROL_2: Final = "1058d"
COND_TWO_PRESSURE_SENSORS: Final = "1099d"
COND_SECOND_HEAT_GENERATOR: Final = "1106d"
COND_FLOW_SENSOR: Final = "1148d"
COND_VENTILATION: Final = "1194d"

# Modbus TCP coils polled for datapoints that are not available over MQTT.
MODBUS_COIL_BLOCKS: Final[tuple[tuple[int, int], ...]] = ((177, 1),)
COIL_SMART_RTC_VALVE: Final = 177

# Power values are delivered in units of 10 W.
POWER_SCALE: Final = 10

# Composite energy counters are split into three 4-digit decimal parts
# (low, middle, high).
ENERGY_HEATING: Final = ("1300u", "1301u", "1302u")
ENERGY_HOT_WATER: Final = ("1303u", "1304u", "1305u")
ENERGY_POOL: Final = ("1306u", "1307u", "1308u")
ENERGY_ENVIRONMENTAL: Final = ("1475i", "1473i", "1474i")
ENERGY_TOTAL: Final = ("1660i", "1661i", "1662i")
ENERGY_HEATING_RESET: Final = ("1675i", "1676i", "1677i")
ENERGY_HOT_WATER_RESET: Final = ("1681i", "1682i", "1683i")
ENERGY_POOL_RESET: Final = ("1678i", "1679i", "1680i")
ENERGY_ENVIRONMENTAL_RESET: Final = ("1647i", "1648i", "1649i")

# Integer temperatures shown on the gateway UI are delivered in 0.1 K steps.
TEMPERATURE_SCALE: Final = 0.1

DATAPOINT_STATUS: Final = "530u"
DATAPOINT_FAULT: Final = "531u"
DATAPOINT_SENSOR_FAULT: Final = "532u"
DATAPOINT_LOCK: Final = "533u"
DATAPOINT_OPERATING_MODE: Final = "714u"
DATAPOINT_HOT_WATER_TEMPERATURE: Final = "1305a"
DATAPOINT_HOT_WATER_SETPOINT: Final = "1042u"
DATAPOINT_HOT_WATER_MIN: Final = "1045u"
DATAPOINT_HOT_WATER_MAX: Final = "1044u"
DATAPOINT_THERMAL_POWER: Final = "2666i"
DATAPOINT_COOLING_POWER: Final = "2667i"
DATAPOINT_ELECTRICAL_POWER: Final = "2668i"
DATAPOINT_PV_SURPLUS: Final = "2670i"

STATUS_HOT_WATER: Final = 4

REQUEST_STATES: Final[dict[int, str]] = {0: "none", 1: "request", 2: "locked"}
CIRCUIT_STATES: Final[dict[int, str]] = {
    0: "operating_mode",
    1: "heating",
    2: "cooling",
}
HOT_WATER_STATES: Final[dict[int, str]] = {
    0: "none",
    1: "temperature_reached",
    2: "flush_time",
    3: "standstill_time",
    4: "waste_heat",
}
POOL_STATES: Final[dict[int, str]] = {
    0: "none",
    1: "temperature_reached",
    2: "flush_time",
    3: "standstill_time",
}

OPERATING_MODES: Final[dict[int, str]] = {
    0: "summer",
    1: "auto",
    2: "holiday",
    3: "party",
    4: "second_heat_generator",
    5: "cooling",
}

SMART_GRID_STATES: Final[dict[int, str]] = {
    0: "hardware_input",
    10: "yellow",
    11: "green",
    12: "red",
    13: "dark_green",
}

EXTERNAL_LOCK_STATES: Final[dict[int, str]] = {
    0: "hardware_input",
    10: "inactive",
    11: "active",
}

# Message tables for WPM software L/M (the only versions with an NWPM Touch)
STATUS_MESSAGES: Final[dict[int, str]] = {
    0: "off",
    1: "off",
    2: "heating",
    3: "pool",
    4: "hot_water",
    5: "cooling",
    10: "defrosting",
    11: "flow_monitoring",
    24: "mode_switch_delay",
    30: "locked",
}

LOCK_MESSAGES: Final[dict[int, str]] = {
    0: "none",
    2: "flow_rate",
    5: "function_check",
    6: "high_temperature_limit",
    7: "system_check",
    8: "cooling_switch_delay",
    9: "pump_lead_time",
    10: "minimum_standstill",
    11: "grid_load",
    12: "cycle_lock",
    13: "hot_water_reheating",
    14: "regenerative",
    15: "utility_lock",
    16: "soft_starter",
    17: "flow",
    18: "heat_pump_limit",
    19: "high_pressure",
    20: "low_pressure",
    21: "heat_source_limit",
    23: "system_limit",
    24: "primary_circuit_load",
    25: "external_lock",
    29: "inverter",
    31: "warm_up",
    33: "eev_initialization",
    34: "second_heat_generator_enabled",
    35: "fault",
}

FAULT_MESSAGES: Final[dict[int, str]] = {
    0: "none",
    1: "n17_1",
    2: "n17_2",
    3: "n17_3",
    4: "n17_4",
    5: "n17",
    6: "electronic_expansion_valve",
    7: "room_controller_rtm_econ",
    8: "outdoor_unit",
    9: "flow_frost_protection",
    10: "wpio_extension",
    12: "inverter",
    13: "wqif_extension",
    14: "wet_run",
    15: "sensor",
    16: "low_pressure_brine",
    19: "primary_circuit",
    20: "defrosting",
    21: "low_pressure_brine_critical",
    22: "hot_water",
    23: "compressor_load",
    24: "coding",
    25: "low_pressure",
    26: "frost_protection",
    28: "high_pressure",
    29: "temperature_difference",
    30: "hot_gas_thermostat",
    31: "flow",
    32: "warm_up",
}

SENSOR_FAULT_MESSAGES: Final[dict[int, str]] = {
    0: "none",
    1: "outdoor_sensor",
    2: "return_sensor",
    3: "hot_water_sensor",
    4: "coding",
    5: "flow_sensor",
    6: "heating_circuit_2_sensor",
    7: "heating_circuit_3_sensor",
    8: "regenerative_sensor",
    9: "room_sensor_1",
    10: "room_sensor_2",
    11: "heat_source_outlet_sensor",
    12: "heat_source_inlet_sensor",
    14: "collector_sensor",
    15: "low_pressure_sensor",
    16: "high_pressure_sensor",
    17: "room_humidity_1",
    18: "room_humidity_2",
    19: "frost_protection_cooling_sensor",
    20: "hot_gas",
    21: "return_sensor_2",
    22: "pool_sensor",
    23: "passive_cooling_flow_sensor",
    24: "passive_cooling_return_sensor",
    26: "solar_storage_sensor",
    28: "heating_demand_sensor",
    29: "rtm_econ",
    30: "cooling_demand_sensor",
    37: "oil_temperature_compressor_1",
    39: "oil_temperature_compressor_2",
    41: "hot_gas_compressor_1",
    43: "hot_gas_compressor_2",
    45: "evaporator_air_inlet_sensor",
    48: "secondary_flow_sensor",
    49: "secondary_pressure_sensor",
    50: "primary_flow_sensor",
    51: "primary_pressure_sensor",
    52: "suction_gas_sensor",
}
