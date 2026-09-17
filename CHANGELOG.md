# Changelog

All notable changes to this project are documented in this file. The format
is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the
project adheres to [Semantic Versioning](https://semver.org/).

## [0.1.0] - 2026-09-17

### Added

- Initial release of the Dimplex NWPM Touch integration for Home Assistant,
  built on [pydimplex-nwpm](https://pypi.org/project/pydimplex-nwpm/).
- Local push via the gateway's MQTT broker with once-a-minute polling of
  settings; optional Modbus TCP for the Smart-RTC valve state.
- Entities are created according to the heat pump manager's equipment flags
  (inverter, pressure sensors, flow sensor, heat meter, heating circuits,
  hot water, pool, solar, ventilation, cooling).
- Sensors for temperatures, pressures, flow rate, inverter, power stages,
  status/lock/fault messages, runtimes, cycle counters and energy counters;
  binary sensors for inputs and outputs; number, select, water heater and
  button entities for the documented settings.
- Config flow with DHCP discovery, re-authentication and reconfiguration;
  diagnostics; English and German translations.

[0.1.0]: https://github.com/p-atr/hass-dimplex-nwpm/releases/tag/v0.1.0
