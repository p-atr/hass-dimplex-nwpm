# Changelog

All notable changes to this project are documented in this file. The format
is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the
project adheres to [Semantic Versioning](https://semver.org/).

## [0.2.0] - 2026-09-17

### Changed

- Requires pydimplex-nwpm 0.2.0, which now owns the datapoint table, scaling,
  equipment flags, polling and Modbus TCP handling and uses aiomqtt.
- Discovered gateways only ask for the password.
- Runtimes, cycle counters, digital inputs, valves and mixers are disabled by
  default; valves are diagnostic entities.
- PV surplus and external outdoor temperature are no longer configuration
  entities.
- The gateway device reports its firmware as software version.

### Removed

- Coefficient of performance sensor (use a template helper instead).
- Hot water temperature sensor and hot water setpoint number; both are part of
  the hot water entity.
- `code` and history detail attributes.

### Fixed

- Settings, Modbus values and authentication failures were no longer polled
  while push updates kept arriving.
- Energy counters could briefly jump when a push update delivered only part of
  a counter.
- Heating circuit 1 temperature and setpoint were never polled.
- The stored password was sent to the browser in the reconfigure form.
- Repeated DHCP announcements started duplicate discovery flows.
- Unexpected errors during setup of a new gateway are reported as such.
- The hot water entity reported `off` whenever no hot water was being heated.

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

[0.2.0]: https://github.com/p-atr/hass-dimplex-nwpm/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/p-atr/hass-dimplex-nwpm/releases/tag/v0.1.0
