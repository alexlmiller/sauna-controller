# Wall Panel

The wall panel is an optional local interface. It is not the safety controller;
the control board remains the source of truth.

Supported panel targets:

- Elecrow CrowPanel 2.1" rotary display: wired UART install target.
- M5Stack Dial: WiFi/Home Assistant test target while the UI and hardware fit
  are evaluated.

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
link on the CrowPanel:

```bash
esphome run firmware/wall-panel/wifi.yaml
```

The M5Stack Dial WiFi target uses the same Home Assistant command/state model:

```bash
esphome run firmware/wall-panel/m5dial-wifi.yaml
```

The Dial hardware configuration follows the official M5Stack Dial pinout for
the GC9A01 display, FT3267-compatible touch controller, rotary encoder, and
HOLD power pin: <https://docs.m5stack.com/en/core/M5Dial>.

## Behavior

- Heater page: current temperature, target temperature, heater state, fault
  banner.
- Lights page: brightness and preset control.
- Status page: ceiling/bench temperatures, door, heater, high-temp, relay
  feedback, and clear-fault control.

## Control Model

The control board remains authoritative. The panel may show local draft UI state
so knob turns feel immediate, but controller state wins for heater mode, faults,
and actual heater activity.

Target temperature and heat mode are intentionally separate:

- Turning the knob changes only the draft target temperature.
- Pressing on the heater page sends an explicit heat-on command.
- Long-pressing on the heater page sends an explicit heat-off command.
- Home Assistant or control-board OFF updates the panel immediately and is not
  overwritten by a stale panel mirror.

The wired panel protocol uses one-shot command counters for heat on/off, light
toggle, and fault clearing. It does not publish mirrored heat mode as a command.
That avoids the panel re-enabling heat after another controller has turned it
off.

## Firmware Layout

The wall-panel package is split so alternate physical panels can reuse the same
state and command model:

- [`../firmware/wall-panel/packages/core.yaml`](../firmware/wall-panel/packages/core.yaml):
  shared local mirrors, command counters, pending flags, and link state.
- [`../firmware/wall-panel/packages/interaction.yaml`](../firmware/wall-panel/packages/interaction.yaml):
  knob/button behavior and local draft updates.
- [`../firmware/wall-panel/packages/hardware-crowpanel.yaml`](../firmware/wall-panel/packages/hardware-crowpanel.yaml):
  CrowPanel ESP32-S3, display, touch, encoder, and boot hardware setup.
- [`../firmware/wall-panel/packages/ui-crowpanel.yaml`](../firmware/wall-panel/packages/ui-crowpanel.yaml):
  CrowPanel LVGL pages and widgets.
- [`../firmware/wall-panel/packages/common-m5dial.yaml`](../firmware/wall-panel/packages/common-m5dial.yaml):
  M5Stack Dial package bundle.
- [`../firmware/wall-panel/packages/hardware-m5dial.yaml`](../firmware/wall-panel/packages/hardware-m5dial.yaml):
  Dial ESP32-S3, display, touch, encoder, backlight, and power-hold setup.
- [`../firmware/wall-panel/packages/interaction-m5dial.yaml`](../firmware/wall-panel/packages/interaction-m5dial.yaml):
  Dial-specific knob behavior on the smaller round screen.
- [`../firmware/wall-panel/packages/ui-m5dial.yaml`](../firmware/wall-panel/packages/ui-m5dial.yaml):
  Dial LVGL pages and widgets.
- [`../firmware/wall-panel/packages/wired.yaml`](../firmware/wall-panel/packages/wired.yaml):
  direct-UART packet transport.
- [`../firmware/wall-panel/packages/transport-wifi.yaml`](../firmware/wall-panel/packages/transport-wifi.yaml):
  Home Assistant desk-test transport.
- [`../firmware/control-board/packages/common.yaml`](../firmware/control-board/packages/common.yaml):
  authoritative heater, safety, and command handling.

## UART Notes

The installed Rev B design uses direct 3.3 V UART, not RS-485. That choice keeps
the panel wiring simple and has been sufficient for the short in-cabinet to
wall-panel run. Revisit RS-485 only if the direct UART link proves unreliable in
a specific installation.
