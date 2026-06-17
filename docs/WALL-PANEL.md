# Wall Panel

The wall panel is an optional local interface based on the Elecrow CrowPanel
2.1" rotary display. It is not the safety controller; the control board remains
the source of truth.

## Normal Wired Build

- Direct 3.3 V UART over a short Cat5e run
- Control board UART: GPIO32 TX / GPIO33 RX
- Wall panel UART: GPIO43 TX / GPIO44 RX
- 5 V power from the control board
- WiFi remains available for OTA updates

Firmware:

```bash
esphome run firmware/wall-panel/wired.yaml
```

## WiFi Desk-Test Build

The WiFi/Home Assistant target is useful for UI testing without the wired UART
link:

```bash
esphome run firmware/wall-panel/wifi.yaml
```

## Behavior

- Heater page: current temperature, target temperature, heater state, fault
  banner.
- Lights page: brightness and preset control.
- Status page: ceiling/bench temperatures, door, heater, high-temp, relay
  feedback, and clear-fault control.

## Control Model

The control board remains authoritative. The panel displays exported control
board state and sends commands for target temperature, heat mode, lights, and
fault clearing.

The panel suppresses command publishing until it has synced from the control
board, so it should not overwrite Home Assistant changes on boot. The live
implementation is in:

- [`../firmware/wall-panel/packages/common.yaml`](../firmware/wall-panel/packages/common.yaml)
- [`../firmware/wall-panel/packages/wired.yaml`](../firmware/wall-panel/packages/wired.yaml)
- [`../firmware/wall-panel/packages/wifi.yaml`](../firmware/wall-panel/packages/wifi.yaml)
- [`../firmware/control-board/packages/common.yaml`](../firmware/control-board/packages/common.yaml)

## UART Notes

The installed Rev B design uses direct 3.3 V UART, not RS-485. That choice keeps
the panel wiring simple and has been sufficient for the short in-cabinet to
wall-panel run. Revisit RS-485 only if the direct UART link proves unreliable in
a specific installation.
