# Firmware

Current builds use the Rev B firmware targets.

## Targets

```bash
# Control board
esphome run firmware/control-board/rev-b.yaml

# Wired wall panel
esphome run firmware/wall-panel/wired.yaml

# WiFi/Home Assistant wall panel for desk testing
esphome run firmware/wall-panel/wifi.yaml
```

## Secrets

Create a root `secrets.yaml` with:

```yaml
wifi_ssid: "..."
wifi_password: "..."
wifi_fallback_pw: "..."
ota_password: "..."
api_key: "..."
syslog_host: "..."
```

The firmware folders contain relative `secrets.yaml` symlinks so ESPHome can
resolve `!secret` after the targets were moved into subdirectories. The real
root `secrets.yaml` is ignored by Git.

## Control Board Pins

The current pin map lives in the `substitutions:` block of
[`../firmware/control-board/rev-b.yaml`](../firmware/control-board/rev-b.yaml).
That file is the source of truth for both carrier-PCB and hand-wired Rev B
builds.

Rev B deliberately changed several Rev A pins to make the board route cleanly:
the relay coil is on GPIO23, the wall-panel UART is on GPIO32/GPIO33, the door
input is on GPIO25, relay feedback and high-temp status are on GPIO34/GPIO35,
and the RGBW LED channels are ordered GPIO19/GPIO18/GPIO17/GPIO16.

Rev B also includes [`../firmware/control-board/packages/rev-b-hardware.yaml`](../firmware/control-board/packages/rev-b-hardware.yaml),
which drives the on-board FAULT LED from GPIO22 and exposes GPIO4 as the
`AUX Output` switch. That package is included only by the Rev B control-board
target.

## Layout

```text
firmware/
  control-board/
    rev-b.yaml
    packages/common.yaml

  wall-panel/
    wired.yaml
    wifi.yaml
    packages/

  legacy/rev-a/
```

The control board owns safety and actuator control. The wall panel sends
requests and displays status but is not required for safe operation.

## Legacy Rev A

Rev A firmware wrappers are kept in [`firmware/legacy/rev-a/`](../firmware/legacy/rev-a/)
for early boards only. New component and carrier-PCB builds should use Rev B.
