# Dimplex NWPM Touch for Home Assistant

[![HACS](https://img.shields.io/badge/HACS-custom-orange.svg)](https://hacs.xyz)
[![Validate](https://github.com/p-atr/hass-dimplex-nwpm/actions/workflows/validate.yml/badge.svg)](https://github.com/p-atr/hass-dimplex-nwpm/actions/workflows/validate.yml)
[![Tests](https://github.com/p-atr/hass-dimplex-nwpm/actions/workflows/tests.yml/badge.svg)](https://github.com/p-atr/hass-dimplex-nwpm/actions/workflows/tests.yml)

Local integration for Dimplex heat pumps equipped with the **NWPM Touch**
network extension (order number 378800) or a **System M** heat pump, which
ships with the same gateway built in. The gateway (a Carel pCOWeb board) runs
a local Mosquitto MQTT broker and, optionally, a Modbus TCP server; this
integration talks to both and does not depend on the Dimplex cloud.

## Supported devices

- Dimplex heat pumps with a heat pump manager (WPM) with touch display and the
  NWPM Touch extension, WPM software **M3.3 or newer**, gateway firmware
  A2.1.0/B2.1.0 or newer, plugin version 5.0.4 or newer.
- Dimplex System M heat pumps.

Tested with WPM software M3.13 on gateway plugin 10.0.1.

## How data is updated

The integration is **local push**. It keeps an MQTT v5 connection to the
gateway and receives every value the gateway has in its telemetry
configuration (temperatures, status, outputs, ...) as soon as it changes. On
connection it asks the gateway to re-send all cached values so entities are
populated immediately.

Settings and slowly changing values that the gateway does not push (setpoints,
heating curve parameters, runtimes, energy counters, ...) are polled over the
same MQTT connection once a minute.

The heat pump manager's equipment flags (inverter, pressure sensors, flow
sensor, heat meter, second/third heating circuit, pool, solar, ventilation,
...) are read once during setup; entities for equipment that is not installed
are not created at all.

Only the Smart-RTC valve state is unavailable over MQTT. When
*Use Modbus TCP* is enabled, that coil is polled once a minute as well.
Everything else uses MQTT.

## Installation

### HACS (recommended)

1. In HACS open *Integrations → ⋮ (top right) → Custom repositories*, add
   `https://github.com/p-atr/hass-dimplex-nwpm` with type *Integration* and
   click *Add*. This step is only needed until the repository is part of the
   HACS default store; without it HACS reports the repository as not found.
2. Open the repository in HACS (search for **Dimplex NWPM Touch** or use the
   button below), download it and restart Home Assistant.

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=p-atr&repository=hass-dimplex-nwpm&category=integration)

### Manual

1. Copy `custom_components/dimplex_nwpm` from this repository into
   `custom_components` of your Home Assistant configuration directory and
   restart Home Assistant.

### Heat pump side

2. Make sure the heat pump manager's network setting is set to *Home App*
   (Settings → Network on the display) so the NWPM Touch is active.
3. Optional, for the Modbus TCP values: open the gateway web interface
   (`https://<gateway-ip>`), go to *Settings* → *Gateway access* and enable
   *Network services*, then restart the gateway.

## Configuration

The gateway is discovered automatically via DHCP (hostname `pcoweb…`). You can
also add it manually via **Settings → Devices & services → Add integration →
Dimplex NWPM Touch**.

| Parameter | Description |
| --- | --- |
| Host | Hostname or IP address of the NWPM Touch gateway. |
| Password | Local gateway password. It is shown on the heat pump display under *Analytics → Hardware and software → Network → Gateway access* and in the Dimplex Home app under *Service data*. The MQTT user name is always `mqtt`. |
| Use Modbus TCP for additional datapoints | Also poll the Smart-RTC valve state over Modbus TCP (port 502). Requires the network services to be enabled on the gateway. Off by default. |

The host, password and Modbus option can be changed later via
*Reconfigure* on the integration entry. If the gateway password is changed,
Home Assistant asks for the new one (re-authentication).

## Entities

Two devices are created: the **heat pump manager** with all heating related
entities and the **NWPM Touch gateway** with its connection diagnostics.

### Sensors

- Key operating data: outdoor, flow and return temperature, flow rate (L/h),
  heating system pressure, high and low refrigerant pressure, inverter
  frequency and power, current power stage (heating/cooling), status.
- Further temperatures: heat source inlet/outlet, heating circuits 1 to 3, room temperature and humidity 1/2, passive cooling, solar and
  ventilation temperatures, ventilation fan speeds, hot gas temperature.
- Refrigerant circuit diagnostics: evaporation temperature, suction gas
  temperature, superheat, expansion valve position, inverter voltage.
- Status, lock reason, fault and sensor fault as translated enum sensors.
- Runtimes of the compressors, pumps, second heat generator, flange heater
  and cooling, plus compressor cycle counters (disabled by default).
- Heat meter values: thermal, cooling and electrical power, energy counters for heating, hot water, pool and environmental
  energy (heat pumps with an integrated or external heat meter only).
- Last fault and last lock timestamps from the appliance history.

Setpoints, runtimes and refrigerant diagnostics are in the *Diagnostic*
section of the device page so the key operating data stays on top. Entities of
optional equipment are only created when the heat pump manager reports that
equipment as installed.

### Binary sensors

- Outputs: compressors, fan, nozzle ring heater, pumps, boiler,
  pipe/immersion/flange heater, circulation pump, collective fault.
- Diagnostic signals, disabled by default: digital inputs (smart grid 1/2,
  utility (EVU) lock, external lock), pressure switches, hot gas and frost
  protection thermostat, flow switch, motor protection, 4-way and switch
  valves, mixers.
- Modbus TCP only: Smart-RTC valve state.
- Gateway: heat pump connection, cloud connection, internet connection.

### Controls

- **Operating mode** select: summer, auto, holiday, party, second heat
  generator, cooling.
- **Smart grid** select: hardware input, normal (yellow), boost (green),
  reduced (red), maximum (dark green). The heat pump manager resets this to
  *hardware input* after a power cycle.
- **External lock** select: hardware input, inactive, active (WPM software
  M3.8 or newer).
- **Hot water** water heater entity with the current hot water temperature
  and the setpoint (limited by the configured minimum and maximum hot water
  temperature).
- Number entities for all documented settings: party hours, holiday days,
  ventilation level, heating curve parameters and hysteresis for all heating
  circuits, hot water and pool temperatures, second heat generator limits,
  external outdoor temperature (for feeding a weather station value to the
  heat pump) and the PV surplus register (for feeding the current PV surplus
  from an automation).
- **Synchronize time** button writing the current time to the heat pump
  manager.

## Examples

Dashboard card with the most important operating data:

```yaml
type: entities
title: Heat pump
entities:
  - sensor.dimplex_heat_pump_status
  - sensor.dimplex_heat_pump_outdoor_temperature
  - sensor.dimplex_heat_pump_flow_temperature
  - sensor.dimplex_heat_pump_return_temperature
  - sensor.dimplex_heat_pump_flow_rate
  - sensor.dimplex_heat_pump_system_pressure
  - sensor.dimplex_heat_pump_high_pressure
  - sensor.dimplex_heat_pump_low_pressure
  - sensor.dimplex_heat_pump_inverter_frequency
  - sensor.dimplex_heat_pump_power_stage_heating
  - sensor.dimplex_heat_pump_thermal_power
  - sensor.dimplex_heat_pump_electrical_power
```

Raise the hot water setpoint while the photovoltaic system exports energy:

```yaml
automation:
  - alias: Hot water boost on PV surplus
    triggers:
      - trigger: numeric_state
        entity_id: sensor.grid_export_power
        above: 2000
        for: "00:10:00"
    actions:
      - action: select.select_option
        target:
          entity_id: select.dimplex_heat_pump_smart_grid
        data:
          option: green
```

Notify when the heat pump reports a fault:

```yaml
automation:
  - alias: Heat pump fault
    triggers:
      - trigger: state
        entity_id: sensor.dimplex_heat_pump_fault
        from: none
    actions:
      - action: notify.notify
        data:
          message: "Heat pump fault: {{ states('sensor.dimplex_heat_pump_fault') }}"
```

## Known limitations

- Only WPM software versions with the NWPM Touch (L/M software) are supported;
  the message tables of older H/J software are different.
- Values that the gateway does not push are polled once a minute, so changes
  made on the display can take up to a minute to show up.
- Writing analog (decimal) settings such as the room temperature setpoint
  sends the value with one decimal, as the gateway reports it. This path could
  not be verified against a live system.
- On WPM software M3.13 the setpoint datapoints listed in the Dimplex wiki as
  `1594a`, `1620a`, `1622a` and `1624a` do not exist; the integration uses the
  integer variables `1594i`, `1620i`, `1622i` and `1624i` (in 0.1 K steps)
  that the gateway's own web interface displays.
- The flow rate (`1472i`) is reported without a unit by the gateway; it is
  assumed to be L/h as shown on the heat pump display.
- The room temperature control (Smart-RTC+) write registers are not exposed.

## Troubleshooting

- **Cannot connect**: check that the gateway is reachable on port 61894 and
  that the network setting of the heat pump manager is *Home App*.
- **Invalid authentication**: the local password changed; it is shown on the
  display under *Analytics → Hardware and software → Network → Gateway access*.
  Within 10 minutes after a gateway restart the password can be reset to the
  default via the reset port (see the Dimplex wiki).
- **Modbus TCP not reachable**: enable *Network services* under *Settings →
  Gateway access* in the gateway web interface and restart the gateway, or
  disable the Modbus TCP option.
- **Entities unavailable**: the MQTT connection dropped; the integration
  reconnects automatically with increasing delays. Enable debug logging for
  `custom_components.dimplex_nwpm` to see the reconnect attempts.

## Removal

Remove the integration entry via *Settings → Devices & services*. No settings
are left behind on the gateway; the local MQTT user and password are managed by
the gateway itself.

## Development

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements_test.txt
ruff check . && pytest
```

The integration is written against the Home Assistant
[integration quality scale](https://developers.home-assistant.io/docs/core/integration-quality-scale/)
platinum rules; see `custom_components/dimplex_nwpm/quality_scale.yaml`.

## Library

The protocol implementation lives in the separate
[pydimplex-nwpm](https://pypi.org/project/pydimplex-nwpm/) package
([source](https://github.com/p-atr/pydimplex-nwpm)); this integration only
maps its data to Home Assistant entities.

## References

- [Dimplex Wiki: MQTT Anbindung](https://dimplex.atlassian.net/wiki/spaces/DW/pages/3021930597/MQTT+Anbindung)
- [Dimplex Wiki: Modbus TCP Anbindung](https://dimplex.atlassian.net/wiki/spaces/DW/pages/3303571457/Modbus+TCP+Anbindung)
