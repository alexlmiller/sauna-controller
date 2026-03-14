# Physical Wall Panel — Software & Hardware Requirements

> Second ESP32-S3 device with round TFT display + rotary encoder, mounted at the sauna door. All control and status flows over wired RS-485 (no WiFi dependency). WiFi is enabled solely for OTA firmware updates.

---

## Architecture Overview

```
┌─────────────────────────┐      Wired RS-485 (Cat5e)        ┌──────────────────────────┐
│   MAIN CONTROLLER       │◄────────────────────────────────►│   WALL PANEL             │
│   (existing ESP32)      │                                   │   (ESP32-S3 + display)   │
│                         │    Status data  ────►             │                          │
│  - All safety logic     │    Commands     ◄────             │  - LVGL round display    │
│  - Contactor control    │    +5V / GND (power)              │  - Rotary encoder        │
│  - Temp sensors         │                                   │  - Capacitive touch      │
│  - Door monitoring      │                                   │                          │
│  - LED control          │                                   │  Read-only + setpoint    │
│  - Fault management     │                                   │  adjustment + commands   │
│                         │                                   │                          │
│  Also connects to HA    │                                   │  WiFi for OTA updates    │
│  via WiFi (unchanged)   │                                   │  only (not for control)  │
└─────────────────────────┘                                   └──────────────────────────┘
```

**Key principle**: The panel is a convenience interface — all safety logic and control remains on the main controller. If the panel loses power or the cable is disconnected, the controller continues operating on its last setpoint with all safeties intact.

---

## Phase 0: Transport Spike (Do This First)

Before buying hardware, selecting boards, or designing UI, validate the communication layer with a minimal proof-of-concept on two ESP32 dev boards connected over UART.

### What to prove

1. **Bidirectional Packet Transport on one UART**: Can a single `packet_transport: platform: uart` instance act as both provider and consumer simultaneously in full-duplex mode? This is the linchpin assumption — if it doesn't work, we fall back to a custom UART protocol.

2. **State-based sensor transport**: Send one float (temperature) and one boolean (door state) from controller → panel. Confirm values arrive and update on the consumer within 1-2s.

3. **State-based command transport**: Send one float (target temp setpoint) from panel → controller. Confirm `on_value` fires and the controller acts on it.

4. **Counter-based one-shot command**: Send an incrementing counter (sensor) from panel → controller. Confirm `on_value` fires exactly once per increment — not on every transport broadcast of the same value. This validates the pattern for edge-triggered actions (clear fault, light toggle).

### Spike topology

```
ESP32-A (controller mock)          ESP32-B (panel mock)
  GPIO14 (TX) ──────────────────► RX
  GPIO4  (RX) ◄──────────────── TX
  GND    ────────────────────── GND
```

Direct UART first (no RS-485). If it works at 115200 baud over a short jumper wire, the physical layer (RS-485 vs plain UART vs level-shifted) can be decided based on actual cable run distance and noise testing.

### Spike config (controller mock)

```yaml
esphome:
  name: spike-controller

esp32:
  board: esp32dev
  framework:
    type: esp-idf

logger:
  level: DEBUG

uart:
  tx_pin: GPIO14
  rx_pin: GPIO4
  baud_rate: 115200
  id: panel_uart

# --- Provide status data ---
packet_transport:
  platform: uart
  uart_id: panel_uart
  update_interval: 1s
  sensors:
    - fake_temp
  binary_sensors:
    - fake_door

sensor:
  - platform: template
    id: fake_temp
    name: "Fake Temp"
    lambda: 'return 82.0;'  # ~180°F
    update_interval: 5s

  # Consume: counter-based command from panel
  - platform: packet_transport
    provider: spike-panel
    id: cmd_counter
    name: "Command Counter"
    on_value:
      then:
        - logger.log:
            format: "Received command counter: %.0f"
            args: ['x']

  # Consume: float command from panel
  - platform: packet_transport
    provider: spike-panel
    id: cmd_setpoint
    name: "Command Setpoint"
    on_value:
      then:
        - logger.log:
            format: "Received setpoint command: %.1f°C"
            args: ['x']

binary_sensor:
  - platform: template
    id: fake_door
    name: "Fake Door"
    lambda: 'return false;'  # closed
```

### Spike config (panel mock)

```yaml
esphome:
  name: spike-panel

esp32:
  board: esp32dev
  framework:
    type: esp-idf

logger:
  level: DEBUG

uart:
  tx_pin: GPIOXX  # pick any free pin
  rx_pin: GPIOXX
  baud_rate: 115200
  id: controller_uart

globals:
  - id: action_counter
    type: int
    initial_value: "0"

# --- Provide commands ---
packet_transport:
  platform: uart
  uart_id: controller_uart
  update_interval: 500ms
  sensors:
    - cmd_counter
    - cmd_setpoint

# Command: incrementing counter (one-shot action test)
sensor:
  - platform: template
    id: cmd_counter
    name: "Action Counter"
    lambda: 'return (float)id(action_counter);'
    update_interval: 500ms

  - platform: template
    id: cmd_setpoint
    name: "Setpoint Command"
    lambda: 'return 80.0;'  # ~176°F
    update_interval: 500ms

  # Consume: status from controller
  - platform: packet_transport
    provider: spike-controller
    id: received_temp
    name: "Received Temp"
    on_value:
      then:
        - logger.log:
            format: "Got temp from controller: %.1f°C"
            args: ['x']

binary_sensor:
  - platform: packet_transport
    provider: spike-controller
    id: received_door
    name: "Received Door"
    on_state:
      then:
        - logger.log:
            format: "Got door state: %s"
            args: ['x ? "OPEN" : "CLOSED"']

# Simulate button press: increment counter via interval
button:
  - platform: template
    name: "Simulate Action"
    on_press:
      - lambda: 'id(action_counter) += 1;'
      - logger.log:
          format: "Action counter incremented to %d"
          args: ['id(action_counter)']
```

### Pass criteria

- [ ] Both devices boot and exchange data without crashes
- [ ] Controller mock logs received setpoint and counter values
- [ ] Panel mock logs received temp and door state
- [ ] Incrementing the counter triggers `on_value` exactly once per increment (not on every 500ms broadcast)
- [ ] A command sensor publishing NaN does **not** trigger `on_value` on the controller (validates sync-before-publish suppression)
- [ ] Changing the controller-side fake temp causes `on_value` on the panel (validates status data flow for sync-on-boot)
- [ ] Stable over 10+ minutes with no data corruption or watchdog resets

### If the spike fails

Fallback: custom UART protocol with lambda-based framing. Both devices share a simple binary packet format:

```
[START_BYTE] [MSG_TYPE] [PAYLOAD...] [CRC8]
```

More code, but fully flexible — supports any data type in either direction with explicit message semantics. The rest of this requirements doc (data model, UI, etc.) still applies regardless of transport choice.

---

## Communication Protocol

### Command Semantics

Commands fall into two categories with different transport patterns:

#### State-based commands (continuous values)

These represent the panel's current desired state. The controller applies them whenever the value changes. Re-receiving the same value is a no-op (idempotent).

| Command | Type | Example |
|---------|------|---------|
| Target temperature setpoint | sensor (float, °C) | `82.0` |
| Heat mode desired state | sensor (float) | `1.0` = HEAT, `0.0` = OFF |
| Light brightness | sensor (float, 0.0–1.0) | `0.75` |
| Light R/G/B/W channels | sensor (float, 0.0–1.0) | `0.5` |

**Heat mode** is a sensor (not binary_sensor) to avoid the edge-trigger problem. The controller compares the received value against current mode and only calls `climate.control` when they differ.

#### Command ownership: controller is source of truth

The panel must **never** push stale or default state into the controller. This requires two mechanisms:

1. **Sync-on-boot**: Panel local mirrors (`local_target_temp`, `local_heat_mode`, `local_brightness`, `local_light_r/g/b/w`) initialize to `NaN` (not to defaults like 0 or OFF). The panel suppresses publishing any command sensor that is still `NaN`. When the first status data arrives from the controller (via consumed `target_temp_current`, `heat_mode_active`, `light_brightness_current`, `light_r/g/b/w_current`), the panel seeds its local mirrors from that data. Only then are those commands eligible for publishing.

2. **Dirty flags with echo-back release**: Each command has a dirty flag, initially false. A command sensor is only published (returns a real value from its lambda) after the user has interacted with that specific control. Until the user touches the encoder or taps a preset, the panel echoes back what the controller told it — which is a no-op on the controller side (same value → `on_value` doesn't fire). This prevents the panel from overwriting out-of-band changes made via Home Assistant while the panel is idle.

   **Dirty flag lifecycle**:
   - **Set**: When the user interacts with a control (encoder rotation, touch, preset selection).
   - **Cleared**: When the controller echoes back a status value matching the panel's local mirror (within ±0.3°C for temperature, ±0.02 for brightness/RGBW). This confirms the controller has applied the panel's command, and the panel can resume mirroring controller state for that control. Later HA-originated changes will then flow through again.
   - **Cleared (bulk)**: On link reconnect (see below), all dirty flags reset to re-sync from controller truth.

3. **Link state detection**: The panel tracks `last_rx_ms` (updated on every consumed `on_value` or `on_state` callback). A 1-second interval checks `millis() - last_rx_ms > 5000` to derive `link_up`. On a `false → true` transition (link restored), all dirty flags reset and the panel re-enters sync mode. On `true → false` (link lost), the panel shows a "NO LINK" warning overlay.

These rules are implemented concretely in the Panel Firmware section. The key touchpoints:

- **Globals**: `synced` flag, `local_*` mirrors (init to NaN), `*_dirty` flags (init to false), `last_rx_ms`, `link_up` — see UART & Packet Transport globals.
- **Sync-on-boot**: Each consumed status handler seeds its corresponding local mirror when the dirty flag is false — see Consumed Status Data handlers for `target_temp_current`, `heat_mode_active`, `light_brightness_current`, and `light_r/g/b/w_current`.
- **Echo-back release**: Each consumed status handler clears its dirty flag when the received value matches the local mirror within tolerance — see Consumed Status Data handlers.
- **Conditional publishing**: Each `cmd_*` template sensor returns `NAN` (suppressing transport) until `synced && *_dirty` — see Command Entities.
- **Dirty flag set on user interaction**: Encoder rotation and touch preset handlers set the relevant dirty flag before updating the local mirror — see LVGL UI encoder behavior.
- **Link state interval**: 1-second interval checks `last_rx_ms` freshness, manages `link_up` transitions, and resets dirty flags on reconnect — see Link State Detection.

#### Counter-based commands (one-shot actions)

These represent discrete events (button presses). The panel increments a counter each time the user triggers the action. The controller acts on value *changes*, ignoring repeated broadcasts of the same counter value. `on_value` in ESPHome only fires when the value actually changes, which is exactly the behavior we need.

| Command | Type | Pattern |
|---------|------|---------|
| Clear fault | sensor (float) | Increment counter: `1 → 2 → 3 → ...` |
| Light toggle | sensor (float) | Increment counter: `1 → 2 → 3 → ...` |

**Reboot safety**: Counters reset to 0 on panel boot. The controller must ignore the transition to 0 (treat it as a reset, not an action). Guard: `if (x > 0 && x != id(last_seen_counter)) { act(); id(last_seen_counter) = x; }`.

### Controller → Panel (status data)

| Entity ID | Transport Type | Source | Notes |
|-----------|---------------|--------|-------|
| `ceiling_temp_c` | sensor | Existing DS18B20 | Primary display temp |
| `bench_temp_c` | sensor | Existing DS18B20 | Secondary display temp |
| `target_temp_current` | sensor | **New** template | Reads `sauna_thermostat.target_temperature` |
| `fault_code` | sensor | **New** global | First-class numeric fault enum (see below) |
| `light_brightness_current` | sensor | **New** template | Current light brightness (0.0–1.0) |
| `light_r_current` | sensor | **New** template | Current red channel (0.0–1.0) |
| `light_g_current` | sensor | **New** template | Current green channel (0.0–1.0) |
| `light_b_current` | sensor | **New** template | Current blue channel (0.0–1.0) |
| `light_w_current` | sensor | **New** template | Current white channel (0.0–1.0) |
| `door_sensor` | binary_sensor | Existing GPIO22 | Open/closed |
| `contactor_aux_closed` | binary_sensor | Existing GPIO32 | **Truth source for "heater is actually on"** |
| `high_limit_trip` | binary_sensor | Existing GPIO33 | Hardware safety status |
| `fault_latched_bs` | binary_sensor | **New** template | Mirrors `fault_latched` global |
| `heat_mode_active` | binary_sensor | **New** template | True when thermostat mode == HEAT |
| `light_on` | binary_sensor | **New** template | True when light is on |

Note: `coil_is_on` (commanded coil state) is deliberately **not** sent to the panel. The panel should show heating status based on `contactor_aux_closed` — the actual confirmed contactor position via auxiliary feedback — not command intent. If the contactor fails to pull in, the panel will correctly show "not heating" even though the coil was commanded on.

The light status entities (`light_brightness_current`, `light_r/g/b/w_current`, `light_on`) enable the panel to mirror the controller's actual light state. This is required for:
- Sync-on-boot: panel seeds its local light mirrors from controller truth
- Reflecting HA-originated light changes on the panel display
- Detecting whether the active RGBW values match a known preset or are "Custom"

### First-Class Fault Code Enum

The controller maintains a `fault_code` global (uint8_t) set directly at each fault site. No string parsing.

| Code | Constant | Meaning |
|------|----------|---------|
| 0 | `FAULT_NONE` | No fault |
| 1 | `FAULT_DOOR_TIMEOUT` | Door open timeout |
| 2 | `FAULT_HIGH_TEMP` | Software high temperature |
| 3 | `FAULT_WELDED_CONTACTOR` | Welded contactor detected |
| 4 | `FAULT_SENSOR_NAN` | Sensor invalid/NaN |

The existing `last_trip_reason` string stays for HA / logging. Both are set at the same fault sites:

```cpp
// In safety interval lambda, at each fault:
id(fault_code_val) = 1;  // FAULT_DOOR_TIMEOUT
id(last_trip_reason) = "Door open timeout (" + to_string(...) + "s exceeded)";
```

The panel decodes the numeric code to display text locally — no coupling to the controller's human-readable strings.

### Panel → Controller (commands)

| Entity ID | Type | Category | Controller Action |
|-----------|------|----------|-------------------|
| `cmd_target_temp` | sensor (°C) | State-based | Validate + `climate.control` target_temperature |
| `cmd_heat_mode` | sensor (float) | State-based | `1.0`=HEAT, `0.0`=OFF → `climate.control` mode |
| `cmd_light_brightness` | sensor (0.0–1.0) | State-based | Validate + `light.control` brightness |
| `cmd_light_r` | sensor (0.0–1.0) | State-based | Validate + set channel |
| `cmd_light_g` | sensor (0.0–1.0) | State-based | Validate + set channel |
| `cmd_light_b` | sensor (0.0–1.0) | State-based | Validate + set channel |
| `cmd_light_w` | sensor (0.0–1.0) | State-based | Validate + set channel |
| `cmd_clear_fault_ctr` | sensor (counter) | Counter-based | On increment → run clear fault logic |
| `cmd_light_toggle_ctr` | sensor (counter) | Counter-based | On increment → `light.toggle` |

### Controller-Side Validation

Every incoming command is validated before acting. The controller is the authority — the panel's values are suggestions, not instructions.

```yaml
# Target temperature — clamp to safe range
- platform: packet_transport
  provider: sauna-panel
  id: cmd_target_temp
  on_value:
    then:
      - lambda: |-
          // Hard clamp to thermostat operating range (65.5–93.5°C / 150–200°F)
          float clamped = clamp(x, 65.5f, 93.5f);
          // Reject obviously invalid values (0, NaN, negative)
          if (std::isnan(x) || x < 1.0f) {
            ESP_LOGW("panel", "Rejected invalid target temp: %.1f", x);
            return;
          }
          auto call = id(sauna_thermostat).make_call();
          call.set_target_temperature(clamped);
          call.perform();
          ESP_LOGI("panel", "Set target temp to %.1f°C (received %.1f)", clamped, x);

# Heat mode — only act on actual change, validate value
- platform: packet_transport
  provider: sauna-panel
  id: cmd_heat_mode
  on_value:
    then:
      - lambda: |-
          bool want_heat = (x >= 0.5f);
          bool currently_heat = (id(sauna_thermostat).mode == climate::CLIMATE_MODE_HEAT);
          if (want_heat == currently_heat) return;  // no-op
          auto call = id(sauna_thermostat).make_call();
          call.set_mode(want_heat ? climate::CLIMATE_MODE_HEAT : climate::CLIMATE_MODE_OFF);
          call.perform();
          ESP_LOGI("panel", "Set heat mode to %s", want_heat ? "HEAT" : "OFF");

# Light brightness — clamp 0.0–1.0, reject NaN
- platform: packet_transport
  provider: sauna-panel
  id: cmd_light_brightness
  on_value:
    then:
      - lambda: |-
          if (std::isnan(x)) return;
          float b = clamp(x, 0.0f, 1.0f);
          auto call = id(sauna_light).make_call();
          call.set_brightness(b);
          call.perform();

# Clear fault counter — act on increment, ignore reset to 0
- platform: packet_transport
  provider: sauna-panel
  id: cmd_clear_fault_ctr
  on_value:
    then:
      - lambda: |-
          static float last_ctr = 0.0f;
          if (x <= 0.0f || x == last_ctr) return;  // ignore 0 (reboot) and duplicates
          last_ctr = x;
          // Same validation as existing Clear Fault button:
          float soft_limit_c = (id(soft_high_temp_f).state - 32.0) * 5.0 / 9.0;
          if (id(fault_latched) && id(ceiling_temp_c).has_state() && id(ceiling_temp_c).state < soft_limit_c) {
            id(fault_latched) = false;
            id(fault_code_val) = 0;
            id(last_trip_reason) = "";
            ESP_LOGI("panel", "Fault cleared via panel (counter=%.0f)", x);
          } else {
            ESP_LOGW("panel", "Panel clear fault rejected (temp still high or no fault)");
          }

# Light toggle counter — same pattern
- platform: packet_transport
  provider: sauna-panel
  id: cmd_light_toggle_ctr
  on_value:
    then:
      - lambda: |-
          static float last_ctr = 0.0f;
          if (x <= 0.0f || x == last_ctr) return;
          last_ctr = x;
          auto call = id(sauna_light).toggle();
          call.perform();
          ESP_LOGI("panel", "Light toggled via panel (counter=%.0f)", x);
```

---

## Controller Firmware Changes

Changes required to `sauna-controller.yaml`:

### 1. New Global: Fault Code

```yaml
globals:
  # ... existing globals ...
  - id: fault_code_val
    type: uint8_t
    restore_value: no
    initial_value: "0"
```

### 2. Fault Code Assignment (in safety interval lambda)

Replace string-only fault reporting with dual numeric + string assignment at each fault site:

```cpp
// Door open timeout fault:
id(fault_latched) = true;
id(fault_code_val) = 1;  // FAULT_DOOR_TIMEOUT
id(last_trip_reason) = "Door open timeout (" + to_string((int)id(door_open_fault_s).state) + "s exceeded)";

// Software high temperature fault:
id(fault_latched) = true;
id(fault_code_val) = 2;  // FAULT_HIGH_TEMP
id(last_trip_reason) = "Software high temperature (" + to_string((int)temp_f) + "°F > " + ...);

// Welded contactor fault:
id(fault_latched) = true;
id(fault_code_val) = 3;  // FAULT_WELDED_CONTACTOR
id(last_trip_reason) = "Welded contactor detected (aux closed when coil OFF)";
```

Clear fault resets both:
```cpp
id(fault_latched) = false;
id(fault_code_val) = 0;
id(last_trip_reason) = "";
```

### 3. UART Bus Configuration

```yaml
uart:
  tx_pin: GPIO14
  rx_pin: GPIO4
  baud_rate: 115200
  id: panel_uart
```

### 4. Packet Transport (provider + consumer)

```yaml
packet_transport:
  platform: uart
  uart_id: panel_uart
  update_interval: 1s
  sensors:
    - ceiling_temp_c
    - bench_temp_c
    - target_temp_current
    - fault_code_sensor
    - light_brightness_current
    - light_r_current
    - light_g_current
    - light_b_current
    - light_w_current
  binary_sensors:
    - door_sensor
    - contactor_aux_closed
    - high_limit_trip
    - fault_latched_bs
    - heat_mode_active
    - light_on
```

### 5. New Template Entities (expose internal state for transport)

```yaml
sensor:
  # ... existing sensors ...
  - platform: template
    name: "Target Temp Current"
    id: target_temp_current
    unit_of_measurement: "°C"
    lambda: 'return id(sauna_thermostat).target_temperature;'
    update_interval: 5s

  - platform: template
    name: "Fault Code"
    id: fault_code_sensor
    lambda: 'return (float)id(fault_code_val);'
    update_interval: 1s

  # Light state — read from the light entity's current output values
  - platform: template
    name: "Light Brightness Current"
    id: light_brightness_current
    lambda: |-
      if (id(sauna_light).current_values.is_on()) {
        return id(sauna_light).current_values.get_brightness();
      }
      return 0.0f;
    update_interval: 2s

  - platform: template
    name: "Light R Current"
    id: light_r_current
    lambda: 'return id(sauna_light).current_values.get_red();'
    update_interval: 2s

  - platform: template
    name: "Light G Current"
    id: light_g_current
    lambda: 'return id(sauna_light).current_values.get_green();'
    update_interval: 2s

  - platform: template
    name: "Light B Current"
    id: light_b_current
    lambda: 'return id(sauna_light).current_values.get_blue();'
    update_interval: 2s

  - platform: template
    name: "Light W Current"
    id: light_w_current
    lambda: 'return id(sauna_light).current_values.get_white();'
    update_interval: 2s

binary_sensor:
  # ... existing binary sensors ...
  - platform: template
    name: "Fault Latched"
    id: fault_latched_bs
    lambda: 'return id(fault_latched);'

  - platform: template
    name: "Heat Mode Active"
    id: heat_mode_active
    lambda: 'return id(sauna_thermostat).mode == climate::CLIMATE_MODE_HEAT;'

  - platform: template
    name: "Light On"
    id: light_on
    lambda: 'return id(sauna_light).current_values.is_on();'
```

### 6. Command Consumers

See "Controller-Side Validation" section above for the full YAML with guards on every command.

### 7. Existing Entity Changes

- The existing `Clear Fault` button logic stays as-is for HA use. The panel clear-fault path runs the same validation inline (see `cmd_clear_fault_ctr` handler above).
- No changes to safety logic, thermostat config, LED config, or HA integration.

---

## Controller GPIO Assignment

```
Left (J2)                Right (J3)
─────────                ──────────
3V3                      GND
EN                       GPIO23
GPIO36/VP [input only]   GPIO22  [USED: door sensor]
GPIO39/VN [input only]   GPIO1   [RESERVED: UART0 TX]
GPIO34    [input only]   GPIO3   [RESERVED: UART0 RX]
GPIO35    [input only]   GPIO21
GPIO32    [USED: aux]    GND
GPIO33    [USED: hlimit] GPIO19  [USED: white PWM]
GPIO25                   GPIO18  [USED: blue PWM]
GPIO26    [USED: bus1]   GPIO5
GPIO27    [USED: bus2]   GPIO17  [USED: green PWM]
GPIO14    ◄── UART TX    GPIO16  [USED: red PWM]
GPIO12    [bootstrap]    GPIO4   ◄── UART RX
GND                      GPIO0   [bootstrap]
GPIO13    [USED: coil]   GPIO2   [bootstrap]
```

GPIO14 (TX) and GPIO4 (RX) sit directly across from each other on the same board row. No truly adjacent free pair exists given current pin usage; this is the physically closest available option.

---

## Hardware

### Panel Board: Elecrow CrowPanel 2.1" Rotary Display

| Spec | Value |
|------|-------|
| MCU | ESP32-S3R8 (dual-core LX7, 240 MHz) |
| Memory | 512 KB SRAM, 8 MB PSRAM (octal), 16 MB flash |
| Display | 2.1" IPS, 480x480, ST7701S (RGB parallel) |
| Touch | CST826 capacitive (I2C, addr `0x15`) |
| Encoder | Built-in rotary (GPIO42/GPIO4) + push button (PCF8574 P5) |
| I/O Expander | PCF8574 (I2C, addr `0x21`) — manages LCD power/reset, touch reset/INT, encoder button |
| Backlight | GPIO6 (PWM via LEDC) |
| I2C Bus | SDA=GPIO38, SCL=GPIO39 (shared: touch + PCF8574) |
| Price | ~$36 |

#### CrowPanel GPIO Map

**Display (25 GPIOs consumed):**

| Function | GPIOs |
|----------|-------|
| SPI init (CLK, MOSI, CS) | 2, 1, 16 |
| RGB control (DE, HSYNC, VSYNC, PCLK) | 40, 15, 7, 41 |
| Red data (R0–R4) | 46, 3, 8, 18, 17 |
| Green data (G0–G5) | 14, 13, 12, 11, 10, 9 |
| Blue data (B0–B4) | 5, 45, 48, 47, 21 |

**Other peripherals:**

| Function | GPIO/Pin |
|----------|----------|
| Backlight PWM | GPIO6 |
| I2C SDA / SCL | GPIO38 / GPIO39 |
| Encoder A / B | GPIO42 / GPIO4 |
| Encoder button | PCF8574 P5 |
| LCD power | PCF8574 P3 |
| LCD reset | PCF8574 P4 (inverted) |
| Touch reset | PCF8574 P0 |
| Touch INT | PCF8574 P2 |
| USB-UART (programming) | GPIO43 (TX) / GPIO44 (RX) |
| Onboard LED | GPIO43 (shared with UART0 TX) |

**UART for RS-485 (GPIO43 TX / GPIO44 RX):** The only free GPIOs suitable for UART. Requires `logger: baud_rate: 0` to release UART0. USB serial is sacrificed — first flash via USB, subsequent updates via WiFi OTA. Onboard LED on GPIO43 is also sacrificed (acceptable).

**Unavailable GPIOs:** GPIO26–37 are internally connected to octal PSRAM/flash on ESP32-S3R8 and cannot be used.

#### CrowPanel-Specific Gotchas

1. **PCF8574 boot sequence is mandatory** — LCD power (P3), LCD reset (P4), touch reset (P0), and touch INT (P2) must be toggled in a specific sequence on boot or the display stays black.
2. **CST826 touch requires external component** — not in mainline ESPHome. Use `external_components: source: github://sEbola76/Makerfabs` with `skip_probe: true`.
3. **PSRAM config is critical** — 480x480 RGB framebuffer is ~450 KB. Must set `platformio_options` for `qio_opi` memory type and `psram: mode: octal`.
4. **ESP-IDF framework only** — Arduino framework does not support RGB parallel display on ESP32-S3.
5. **Round display = square framebuffer** — 480x480 buffer behind a circular bezel. No clipping needed; just keep content within ~220px radius from center. Corner content is behind the bezel and invisible.
6. **Encoder direction may be inverted** — swap pin_a/pin_b if CW/CCW feels backwards.
7. **ST7701S platform deprecation** — current `st7701s` component works but will migrate to `mipi_rgb` in a future ESPHome release. Same pins and timings.

### Physical Layer

**Lab/spike**: Direct 3.3V UART with jumper wires on the bench. This is for validating the transport software only — not representative of production conditions.

**Production**: RS-485 differential signaling is the expected production layer. The environment has a 65A contactor switching, 240V heater, and PWM-driven LEDs generating EMI, and the cable run through conduit will be several meters. Plain 3.3V UART over field wiring is not reliable in this environment.

**Transceiver selection**: Use **3.3V-compatible** RS-485 transceivers. The ESP32 and ESP32-S3 are 3.3V logic — the common MAX485 is a 5V part and not a correct match without level shifting. Suitable 3.3V transceivers:

| Part | VCC | Notes |
|------|-----|-------|
| **SP3485** (MaxLinear) | 3.3V | Drop-in pinout, widely available on breakout modules |
| **MAX3485** (Analog Devices) | 3.3V | 3.3V version of MAX485, same pinout |
| **SN65HVD75** (TI) | 3.3V | Robust, good ESD protection |

The spike results determine half-duplex vs full-duplex topology:

| Topology | When to use | Hardware | Wires |
|----------|-------------|----------|-------|
| **RS-485 full-duplex** | If packet_transport requires simultaneous TX/RX (expected) | 2x 3.3V transceiver per device (4 total), DE/RE permanently tied | 4 signal + GND |
| **RS-485 half-duplex** | If using custom protocol with explicit bus arbitration | 1x 3.3V transceiver per device (2 total), ESP32 `flow_control_pin` manages DE/RE | 2 signal + GND |

Cat5e through existing conduit in all cases — twisted pairs are ideal for RS-485 differential signaling. Power (5V or 24V + buck) on a separate pair.

### Power

Panel powered via the Cat5e cable. Options:
- Tap the existing DDR-15G-5 (24V→5V) output and run 5V over the cable (simple, but voltage drop over long runs)
- Run 24V over the cable and add a small buck converter at the panel (better for longer runs)
- USB-C power at the panel location (independent, but requires a separate outlet)

---

## Panel Firmware (new file: `sauna-panel.yaml`)

### Board & Framework

```yaml
esphome:
  name: sauna-panel
  friendly_name: Sauna Panel
  platformio_options:
    build_flags: "-DBOARD_HAS_PSRAM"
    board_build.esp-idf.memory_type: qio_opi
    board_build.flash_mode: dio
  on_boot:
    priority: 800
    then:
      # CrowPanel PCF8574 boot sequence — mandatory or display stays black
      - output.turn_on: lcd_power
      - output.turn_on: display_reset
      - delay: 100ms
      - output.turn_off: display_reset
      - delay: 100ms
      - output.turn_on: tp_reset
      - delay: 100ms
      - output.turn_off: tp_reset
      - delay: 120ms
      - output.turn_on: tp_reset
      - delay: 120ms
      - output.turn_on: tp_intr

esp32:
  board: esp32-s3-devkitc-1
  framework:
    type: esp-idf
    sdkconfig_options:
      CONFIG_ESP32S3_DEFAULT_CPU_FREQ_240: "y"
      CONFIG_ESP32S3_DATA_CACHE_64KB: "y"
      CONFIG_SPIRAM_FETCH_INSTRUCTIONS: "y"
      CONFIG_SPIRAM_RODATA: "y"

psram:
  mode: octal
  speed: 80MHz

logger:
  level: INFO
  baud_rate: 0  # Disable UART0 serial output — frees GPIO43/44 for RS-485

# WiFi is for OTA firmware updates ONLY — not used for control, status, or HA integration.
# All sauna control flows over the wired UART/RS-485 link.
wifi:
  ssid: !secret wifi_ssid
  password: !secret wifi_password

ota:
  platform: esphome
  password: !secret ota_password

# No api: block — the panel does NOT connect to Home Assistant.
# This prevents HA from discovering the panel as a device or sending commands to it.
# All control authority stays with the main controller over the wired link.
```

### CrowPanel Hardware Configuration

```yaml
i2c:
  sda: GPIO38
  scl: GPIO39
  id: bus_a

pcf8574:
  - id: pcf
    address: 0x21

# --- PCF8574-mapped control outputs ---
output:
  - platform: ledc
    pin: 6
    id: bl_pwm
    frequency: 19531Hz
  - platform: gpio
    id: lcd_power
    pin:
      pcf8574: pcf
      number: 3
      mode: { output: true }
      inverted: false
  - platform: gpio
    id: display_reset
    pin:
      pcf8574: pcf
      number: 4
      mode: { output: true }
      inverted: true
  - platform: gpio
    id: tp_reset
    pin:
      pcf8574: pcf
      number: 0
      mode: { output: true }
  - platform: gpio
    id: tp_intr
    pin:
      pcf8574: pcf
      number: 2
      mode: { output: true }

# --- Backlight ---
light:
  - platform: monochromatic
    name: "LCD Backlight"
    output: bl_pwm
    id: display_backlight
    default_transition_length: 0s
    restore_mode: ALWAYS_ON

# --- SPI for display init ---
spi:
  clk_pin: 2
  mosi_pin: 1

# --- Touchscreen (external component required) ---
external_components:
  - source: github://sEbola76/Makerfabs
    components: [cst826]

touchscreen:
  platform: cst826
  id: panel_touch
  i2c_id: bus_a
  skip_probe: true
  update_interval: 25ms
  address: 0x15

# --- Rotary Encoder ---
sensor:
  - platform: rotary_encoder
    id: panel_encoder
    pin_a:
      number: GPIO42
      mode: { input: true, pullup: true }
    pin_b:
      number: GPIO4
      mode: { input: true, pullup: true }
    resolution: 1

binary_sensor:
  - platform: gpio
    id: encoder_button
    pin:
      pcf8574: pcf
      number: 5
      mode: { input: true }
      inverted: true

# --- Display (ST7701S RGB parallel) ---
display:
  - platform: st7701s
    id: panel_display
    update_interval: never
    spi_mode: MODE3
    color_order: RGB
    invert_colors: false
    dimensions:
      width: 480
      height: 480
    cs_pin: 16
    de_pin: 40
    hsync_pin: 15
    vsync_pin: 7
    pclk_pin: 41
    data_pins:
      red: [46, 3, 8, 18, 17]
      green: [14, 13, 12, 11, 10, 9]
      blue: [5, 45, 48, 47, 21]
    hsync_front_porch: 20
    hsync_pulse_width: 10
    hsync_back_porch: 10
    vsync_front_porch: 8
    vsync_pulse_width: 10
    vsync_back_porch: 10
    pclk_frequency: 18MHz
    pclk_inverted: true
    init_sequence:
      - [0x01]
      - [0xFF, 0x77, 0x01, 0x00, 0x00, 0x10]
      - [0xCC, 0x10]
      - [0xCD, 0x08]
      - [0xB0, 0x02, 0x13, 0x1B, 0x0D, 0x10, 0x05, 0x08, 0x07, 0x07, 0x24, 0x04, 0x11, 0x0E, 0x2C, 0x33, 0x1D]
      - [0xB1, 0x05, 0x13, 0x1B, 0x0D, 0x11, 0x05, 0x08, 0x07, 0x07, 0x24, 0x04, 0x11, 0x0E, 0x2C, 0x33, 0x1D]
      - [0xFF, 0x77, 0x01, 0x00, 0x00, 0x11]
      - [0xB0, 0x5D]
      - [0xB1, 0x43]
      - [0xB2, 0x81]
      - [0xB3, 0x80]
      - [0xB5, 0x43]
      - [0xB7, 0x85]
      - [0xB8, 0x20]
      - [0xC1, 0x78]
      - [0xC2, 0x78]
      - [0xD0, 0x88]
      - [0xE0, 0x00, 0x00, 0x02]
      - [0xE1, 0x03, 0xA0, 0x00, 0x00, 0x04, 0xA0, 0x00, 0x00, 0x00, 0x20, 0x20]
      - [0xE2, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
      - [0xE3, 0x00, 0x00, 0x11, 0x00]
      - [0xE4, 0x22, 0x00]
      - [0xE5, 0x05, 0xEC, 0xA0, 0xA0, 0x07, 0xEE, 0xA0, 0xA0, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
      - [0xE6, 0x00, 0x00, 0x11, 0x00]
      - [0xE7, 0x22, 0x00]
      - [0xE8, 0x06, 0xED, 0xA0, 0xA0, 0x08, 0xEF, 0xA0, 0xA0, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
      - [0xEB, 0x00, 0x00, 0x40, 0x40, 0x00, 0x00, 0x00]
      - [0xED, 0xFF, 0xFF, 0xFF, 0xBA, 0x0A, 0xBF, 0x45, 0xFF, 0xFF, 0x54, 0xFB, 0xA0, 0xAB, 0xFF, 0xFF, 0xFF]
      - [0xEF, 0x10, 0x0D, 0x04, 0x08, 0x3F, 0x1F]
      - [0xFF, 0x77, 0x01, 0x00, 0x00, 0x13]
      - [0xEF, 0x08]
      - [0xFF, 0x77, 0x01, 0x00, 0x00, 0x00]
      - [0x36, 0x00]
      - [0x3A, 0x60]
      - [0x11]
      - delay 100ms
      - [0x29]
      - delay 50ms
```

### UART & Packet Transport

```yaml
uart:
  tx_pin: GPIO43
  rx_pin: GPIO44
  baud_rate: 115200
  id: controller_uart

globals:
  # Sync state
  - id: synced
    type: bool
    initial_value: "false"

  # Local mirrors — NaN = not yet synced, do not publish
  - id: local_target_temp
    type: float
    initial_value: "NAN"
  - id: local_heat_mode
    type: float
    initial_value: "NAN"
  - id: local_brightness
    type: float
    initial_value: "NAN"
  - id: local_light_r
    type: float
    initial_value: "NAN"
  - id: local_light_g
    type: float
    initial_value: "NAN"
  - id: local_light_b
    type: float
    initial_value: "NAN"
  - id: local_light_w
    type: float
    initial_value: "NAN"

  # Dirty flags — true after user interaction with that control
  - id: target_temp_dirty
    type: bool
    initial_value: "false"
  - id: heat_mode_dirty
    type: bool
    initial_value: "false"
  - id: brightness_dirty
    type: bool
    initial_value: "false"
  - id: light_color_dirty
    type: bool
    initial_value: "false"

  # One-shot action counters
  - id: clear_fault_ctr
    type: int
    initial_value: "0"
  - id: light_toggle_ctr
    type: int
    initial_value: "0"

  # Active preset tracker (for UI highlighting)
  - id: active_preset
    type: int
    initial_value: "-1"  # -1 = unknown/custom

  # Link state detection
  - id: last_rx_ms
    type: uint32_t
    initial_value: "0"
  - id: link_up
    type: bool
    initial_value: "false"

  # Status ring color (for cross-lambda access)
  - id: status_ring_color
    type: uint32_t
    initial_value: "0x3366FF"

packet_transport:
  platform: uart
  uart_id: controller_uart
  update_interval: 500ms
  sensors:
    - cmd_target_temp
    - cmd_heat_mode
    - cmd_light_brightness
    - cmd_light_r
    - cmd_light_g
    - cmd_light_b
    - cmd_light_w
    - cmd_clear_fault_ctr
    - cmd_light_toggle_ctr
```

### Consumed Status Data

Every `on_value` / `on_state` handler updates `last_rx_ms` for link detection. Status handlers also implement the echo-back dirty flag release: when the controller echoes back a value matching the panel's local mirror (within tolerance), the dirty flag clears and the panel resumes mirroring controller state.

```yaml
sensor:
  - platform: packet_transport
    provider: sauna-controller
    id: ceiling_temp_c
    on_value:
      then:
        - lambda: 'id(last_rx_ms) = millis();'
        - lvgl.arc.update:
            id: temp_arc
            value: !lambda 'return x * 9.0/5.0 + 32.0;'
        - lvgl.label.update:
            id: current_temp_label
            text: !lambda 'return str_sprintf("%.0f°", x * 9.0/5.0 + 32.0);'
        - script.execute: update_status_ring

  - platform: packet_transport
    provider: sauna-controller
    id: bench_temp_c
    on_value:
      then:
        - lambda: 'id(last_rx_ms) = millis();'

  - platform: packet_transport
    provider: sauna-controller
    id: target_temp_current
    on_value:
      then:
        - lambda: |-
            id(last_rx_ms) = millis();
            if (!id(synced)) {
              id(synced) = true;
              ESP_LOGI("panel", "Initial sync from controller");
            }
            // Echo-back release: if controller confirms our value, release ownership
            if (id(target_temp_dirty) && abs(x - id(local_target_temp)) < 0.3f) {
              id(target_temp_dirty) = false;
              ESP_LOGD("panel", "Target temp dirty flag released (echo-back confirmed)");
            }
            // Seed/update local mirror if not dirty
            if (!id(target_temp_dirty)) {
              id(local_target_temp) = x;
            }
        - lvgl.label.update:
            id: target_temp_label
            text: !lambda 'return str_sprintf("target %.0f°F", x * 9.0/5.0 + 32.0);'

  - platform: packet_transport
    provider: sauna-controller
    id: fault_code
    on_value:
      then:
        - lambda: 'id(last_rx_ms) = millis();'
        - lvgl.label.update:
            id: fault_label
            text: !lambda |-
              int code = (int)x;
              switch(code) {
                case 1: return std::string("DOOR OPEN TIMEOUT");
                case 2: return std::string("HIGH TEMPERATURE");
                case 3: return std::string("WELDED CONTACTOR");
                case 4: return std::string("SENSOR FAULT");
                default: return std::string("");
              }

binary_sensor:
  - platform: packet_transport
    provider: sauna-controller
    id: door_sensor
    on_state:
      then:
        - lambda: 'id(last_rx_ms) = millis();'

  - platform: packet_transport
    provider: sauna-controller
    id: contactor_aux_closed
    on_state:
      then:
        - lambda: 'id(last_rx_ms) = millis();'
        - script.execute: update_status_ring

  - platform: packet_transport
    provider: sauna-controller
    id: high_limit_trip
    on_state:
      then:
        - lambda: 'id(last_rx_ms) = millis();'

  - platform: packet_transport
    provider: sauna-controller
    id: fault_latched_bs
    on_state:
      then:
        - lambda: 'id(last_rx_ms) = millis();'
        - if:
            condition:
              lambda: 'return x;'
            then:
              - lvgl.widget.show: fault_banner
            else:
              - lvgl.widget.hide: fault_banner
        - script.execute: update_status_ring

  - platform: packet_transport
    provider: sauna-controller
    id: heat_mode_active
    on_state:
      then:
        - lambda: |-
            id(last_rx_ms) = millis();
            float controller_val = x ? 1.0f : 0.0f;
            // Echo-back release
            if (id(heat_mode_dirty) && abs(controller_val - id(local_heat_mode)) < 0.1f) {
              id(heat_mode_dirty) = false;
              ESP_LOGD("panel", "Heat mode dirty flag released (echo-back confirmed)");
            }
            if (!id(heat_mode_dirty)) {
              id(local_heat_mode) = controller_val;
            }
        - script.execute: update_status_ring

  # --- Light status (for sync, echo-back release, and display) ---
  - platform: packet_transport
    provider: sauna-controller
    id: light_brightness_current
    on_value:
      then:
        - lambda: |-
            id(last_rx_ms) = millis();
            // Echo-back release
            if (id(brightness_dirty) && abs(x - id(local_brightness)) < 0.02f) {
              id(brightness_dirty) = false;
              ESP_LOGD("panel", "Brightness dirty flag released (echo-back confirmed)");
            }
            if (!id(brightness_dirty)) {
              id(local_brightness) = x;
            }
        - lvgl.arc.update:
            id: brightness_arc
            value: !lambda 'return id(light_brightness_current).state * 100.0;'

  - platform: packet_transport
    provider: sauna-controller
    id: light_r_current
    on_value:
      then:
        - lambda: |-
            id(last_rx_ms) = millis();
            if (id(light_color_dirty) && abs(x - id(local_light_r)) < 0.02f) {
              // Check all 4 channels before releasing — release only when all match
              // (partial match means controller hasn't fully applied the preset yet)
            }
            if (!id(light_color_dirty)) { id(local_light_r) = x; }

  - platform: packet_transport
    provider: sauna-controller
    id: light_g_current
    on_value:
      then:
        - lambda: |-
            id(last_rx_ms) = millis();
            if (!id(light_color_dirty)) { id(local_light_g) = x; }

  - platform: packet_transport
    provider: sauna-controller
    id: light_b_current
    on_value:
      then:
        - lambda: |-
            id(last_rx_ms) = millis();
            if (!id(light_color_dirty)) { id(local_light_b) = x; }

  - platform: packet_transport
    provider: sauna-controller
    id: light_w_current
    on_value:
      then:
        - lambda: |-
            id(last_rx_ms) = millis();
            if (!id(light_color_dirty)) { id(local_light_w) = x; }

binary_sensor:
  - platform: packet_transport
    provider: sauna-controller
    id: light_on
    on_state:
      then:
        - lambda: 'id(last_rx_ms) = millis();'
```

**Light color echo-back release**: Because RGBW channels arrive as 4 separate sensors, the dirty flag release is checked in a dedicated 1-second interval rather than per-channel (to avoid releasing mid-update when only some channels have arrived):

```yaml
interval:
  - interval: 1s
    then:
      - lambda: |-
          if (id(light_color_dirty)) {
            bool r_match = abs(id(light_r_current).state - id(local_light_r)) < 0.02f;
            bool g_match = abs(id(light_g_current).state - id(local_light_g)) < 0.02f;
            bool b_match = abs(id(light_b_current).state - id(local_light_b)) < 0.02f;
            bool w_match = abs(id(light_w_current).state - id(local_light_w)) < 0.02f;
            if (r_match && g_match && b_match && w_match) {
              id(light_color_dirty) = false;
              ESP_LOGD("panel", "Light color dirty flag released (all channels echo-back confirmed)");
            }
          }
```

### Status Ring Script

All status-affecting callbacks (`contactor_aux_closed`, `fault_latched_bs`, `heat_mode_active`, and ceiling temp `on_value`) call a single script that recomputes the ring color from all inputs. This eliminates race conditions where independent callbacks overwrite each other.

```yaml
script:
  - id: update_status_ring
    then:
      - lambda: |-
          uint32_t color;
          if (id(fault_latched_bs).state) {
            // Fault takes highest priority — always red
            color = 0xFF0000;
          } else if (!id(heat_mode_active).state) {
            // Heat mode off — blue (idle)
            color = 0x3366FF;
          } else if (id(contactor_aux_closed).state) {
            // Contactor confirmed closed — check if at target
            float current_f = id(ceiling_temp_c).state * 9.0/5.0 + 32.0;
            float target_f = id(target_temp_current).state * 9.0/5.0 + 32.0;
            if (abs(current_f - target_f) <= 2.0) {
              color = 0x00CC66;  // At target — green
            } else {
              color = 0xFF6B00;  // Actively heating — orange
            }
          } else {
            // Heat mode on but contactor not yet closed (waiting for cycle)
            color = 0x3366FF;  // Blue — idle within heat mode
          }
          id(status_ring_color) = color;
      - lvgl.arc.update:
          id: status_ring
          arc_color: !lambda 'return lv_color_hex(id(status_ring_color));'
```

### Link State Detection

A 1-second interval monitors `last_rx_ms` to detect link loss and recovery. On reconnect, all dirty flags reset so the panel re-syncs from controller truth.

```yaml
interval:
  - interval: 1s
    then:
      - lambda: |-
          bool was_up = id(link_up);
          bool is_up = (id(last_rx_ms) > 0) && (millis() - id(last_rx_ms) < 5000);
          id(link_up) = is_up;

          if (!was_up && is_up) {
            // Link restored — reset all dirty flags to re-sync from controller
            id(target_temp_dirty) = false;
            id(heat_mode_dirty) = false;
            id(brightness_dirty) = false;
            id(light_color_dirty) = false;
            id(synced) = false;  // re-enter sync mode
            ESP_LOGI("panel", "Link restored — dirty flags reset, re-syncing");
          }

          if (was_up && !is_up) {
            ESP_LOGW("panel", "Link lost — no data for >5s");
          }
      - if:
          condition:
            lambda: 'return !id(link_up) && id(last_rx_ms) > 0;'
          then:
            - lvgl.widget.show: no_link_warning
          else:
            - lvgl.widget.hide: no_link_warning
```

### Command Entities (sent to controller)

Every state-based command lambda enforces sync-before-publish: it returns `NAN` (suppressing the transport) until the panel has synced from the controller **and** the user has interacted with that specific control. This prevents stale/default values from overwriting controller state on boot or during idle periods.

```yaml
sensor:
  # State-based commands — guarded by synced + dirty flags
  - platform: template
    id: cmd_target_temp
    lambda: |-
      if (!id(synced) || !id(target_temp_dirty)) return NAN;
      return id(local_target_temp);
    update_interval: 500ms

  - platform: template
    id: cmd_heat_mode
    lambda: |-
      if (!id(synced) || !id(heat_mode_dirty)) return NAN;
      return id(local_heat_mode);
    update_interval: 500ms

  - platform: template
    id: cmd_light_brightness
    lambda: |-
      if (!id(synced) || !id(brightness_dirty)) return NAN;
      return id(local_brightness);
    update_interval: 500ms

  - platform: template
    id: cmd_light_r
    lambda: |-
      if (!id(synced) || !id(light_color_dirty)) return NAN;
      return id(local_light_r);
    update_interval: 500ms

  - platform: template
    id: cmd_light_g
    lambda: |-
      if (!id(synced) || !id(light_color_dirty)) return NAN;
      return id(local_light_g);
    update_interval: 500ms

  - platform: template
    id: cmd_light_b
    lambda: |-
      if (!id(synced) || !id(light_color_dirty)) return NAN;
      return id(local_light_b);
    update_interval: 500ms

  - platform: template
    id: cmd_light_w
    lambda: |-
      if (!id(synced) || !id(light_color_dirty)) return NAN;
      return id(local_light_w);
    update_interval: 500ms

  # Counter-based one-shot commands — no dirty guard needed
  # (counters are 0 on boot, controller ignores 0)
  - platform: template
    id: cmd_clear_fault_ctr
    lambda: 'return (float)id(clear_fault_ctr);'
    update_interval: 500ms

  - platform: template
    id: cmd_light_toggle_ctr
    lambda: 'return (float)id(light_toggle_ctr);'
    update_interval: 500ms
```

### Display & Input Hardware

All display, touch, encoder, I2C, SPI, and PCF8574 configuration is defined in the "CrowPanel Hardware Configuration" section above. No placeholder pins — all values are final for the CrowPanel 2.1".

### LVGL Configuration

Full LVGL UI implementation is in `sauna-panel.yaml`. Three pages:
- **main_page**: Temperature display, status ring arc, target temp adjustment via encoder
- **light_page**: Brightness arc, 4 color preset buttons (Warm/Sunset/Red/Blue)
- **info_page**: Status readouts for all sensors, clear fault button

Encoder input group: `main_group`. Buffer size: 50% (PSRAM-backed). Page wrap enabled.

---

## LVGL UI Design

### Page 1 — Main (Temperature Control)

The primary interface. Round display with a thermostat-like layout.

```
         ┌─────────────────┐
        ╱   ┌───────────┐   ╲
       │  ╱  Status Ring  ╲  │
       │ │                 │ │
       │ │     182°F       │ │     ← Current temp (large)
       │ │   target 180°   │ │     ← Target temp (smaller)
       │ │                 │ │
       │ │    ◆ HEATING    │ │     ← Status indicator
       │  ╲               ╱  │
        ╲   └───────────┘   ╱
         └─────────────────┘
```

- **Status ring** (outer arc): Color indicates state based on truth sources:
  - Blue (`0x3366FF`): Heat mode off or idle
  - Orange (`0xFF6B00`): Contactor confirmed closed (`contactor_aux_closed` = true)
  - Red (`0xFF0000`): Fault latched
  - Green (`0x00CC66`): At target (within ±2°F) and contactor cycling normally
- **Temperature arc** (inner): Shows current temp position within 150–200°F range, encoder-adjustable to set target
- **Center labels**: Current temp (large, ~48px), target temp (smaller, ~20px), status text
- **Fault banner**: Red overlay with decoded fault text, shown when `fault_latched_bs` is true
- **Encoder behavior**:
  - Rotate: Adjust target temperature (0.5°C / ~1°F per click, clamped 150–200°F)
  - Short press: Toggle heating on/off (HEAT ↔ OFF)
  - Long press: Navigate to light page

### Page 2 — Lighting

```
         ┌─────────────────┐
        ╱                   ╲
       │      LIGHTS  ◉ ON   │     ← Toggle (encoder press)
       │                     │
       │   ████████░░░ 75%   │     ← Brightness arc (encoder rotate)
       │                     │
       │  ┌────┐ ┌────┐     │
       │  │Warm│ │Snst│     │     ← Preset buttons (touch)
       │  └────┘ └────┘     │
       │  ┌────┐ ┌────┐     │
       │  │ Red│ │Blue│     │     ← Preset buttons (touch)
       │  └────┘ └────┘     │
        ╲                   ╱
         └─────────────────┘
```

- **On/off toggle**: Encoder press to toggle (increments `light_toggle_ctr`)
- **Brightness arc**: Encoder rotation adjusts brightness (0–100%). Applies on top of the active color preset.
- **Color presets**: Touch buttons to select a preset. Active preset is highlighted. Selecting a preset sets all four RGBW channels at once via the existing `cmd_light_r/g/b/w` commands — no new protocol entity needed.
- **Encoder behavior**:
  - Rotate: Adjust brightness
  - Short press: Toggle light on/off
  - Long press: Navigate to info page

#### Light Color Presets

Presets are defined on the panel. Each is a set of RGBW channel values (0.0–1.0). Selecting a preset updates the local RGBW globals, which the normal state-based commands carry to the controller.

| Preset | R | G | B | W | Description |
|--------|---|---|---|---|-------------|
| **Warm White** | 0.0 | 0.0 | 0.0 | 1.0 | Pure white channel — clean, bright, neutral |
| **Sunset** | 1.0 | 0.3 | 0.0 | 0.2 | Warm amber/orange glow |
| **Red Glow** | 1.0 | 0.0 | 0.0 | 0.0 | Deep red — traditional sauna feel |
| **Nordic Blue** | 0.0 | 0.2 | 1.0 | 0.1 | Cool blue accent — contrast to the heat |

Panel-side implementation: each preset button sets the four local RGBW globals and updates the brightness arc color indicator to preview the selected color. The panel tracks which preset is active (or "Custom" if the user manually adjusted channels via HA, which the panel can detect by comparing received RGBW values against known presets on status update).

```yaml
# Example preset button handler (panel-side lambda)
- lvgl.button:
    id: preset_sunset
    on_click:
      then:
        - lambda: |-
            id(local_light_r) = 1.0f;
            id(local_light_g) = 0.3f;
            id(local_light_b) = 0.0f;
            id(local_light_w) = 0.2f;
            id(active_preset) = 2;  // 0=warm, 1=red, 2=sunset, 3=blue
        # Highlight active preset button, dim others
        - lvgl.button.update:
            id: preset_sunset
            bg_color: 0xFF6B00
        - lvgl.button.update:
            id: preset_warm
            bg_color: 0x333333
        # ... etc
```

### Page 3 — Status / Info

```
         ┌─────────────────┐
        ╱                   ╲
       │   Ceiling  182°F    │
       │   Bench    165°F    │
       │                     │
       │   Door     CLOSED   │
       │   Heater   ON       │     ← From contactor_aux_closed (actual state)
       │   Hi-Limit OK       │
       │   Aux      OK       │
       │                     │
       │   [ CLEAR FAULT ]   │     ← Button (if faulted)
        ╲                   ╱
         └─────────────────┘
```

- **Sensor readouts**: Both temperatures in °F
- **Status indicators**: Color-coded (green=OK, red=fault/open)
  - **Heater**: Based on `contactor_aux_closed` (actual contactor position), not commanded state
  - **Door**: Based on `door_sensor`
  - **Hi-Limit**: Based on `high_limit_trip`
  - **Aux**: Based on `contactor_aux_closed` — shows mismatch warning if `heat_mode_active` is true but aux reports open (contactor failed to close)
- **Clear fault button**: Only visible when fault is latched. Encoder press increments `clear_fault_ctr`.
- **Link status**: "NO LINK" warning if no data received for >5 seconds
- **Encoder behavior**:
  - Rotate: Scroll through status items (if needed)
  - Short press: Activate clear fault button
  - Long press: Navigate to main page

### Visual Theming

- **Background**: Dark (`0x1A1A2E` or similar) — readable in dim sauna anteroom
- **Text**: Warm white (`0xF0E6D3`)
- **Accent**: Orange (`0xFF6B00`) for heating, blue (`0x3366FF`) for idle
- **Fonts**: Montserrat — 48px for current temp, 20-24px for labels, 16px for status items
- **Transitions**: Smooth page swipes (LVGL built-in)

---

## Edge Cases & Failure Modes

| Scenario | Behavior |
|----------|----------|
| Panel powers off / disconnected | Controller continues on last setpoint, all safeties active. No impact. |
| Panel boots after controller | Consumer receives data on next provider broadcast (~1s). UI populates automatically. |
| Controller reboots | Panel shows stale data briefly, refreshes within 1s. No commands sent during gap. |
| UART cable disconnected | Panel detects no data for 5s → shows "NO LINK" warning. Controller unaffected. |
| Encoder sets temp outside range | Clamped on panel (65.5–93.5°C). Controller also clamps independently (hard guard in `on_value` lambda). Double protection — neither is UI metadata. |
| Clear fault sent while temp high | Controller's clear-fault lambda rejects it (checks temp < limit). Counter still incremented but no action taken. |
| Both devices boot simultaneously | Packet transport syncs within `update_interval`. No ordering dependency. |
| Panel reboots (counters reset to 0) | Controller ignores counter transitions to 0 via `if (x > 0)` guard. No spurious actions. |
| Panel reboots (state commands) | Local mirrors initialize to NaN. Panel suppresses all command publishing until first status data received from controller (sync-on-boot). No stale values pushed. |
| HA changes setpoint while panel idle | Panel's dirty flag for target temp is false → panel re-syncs from controller's `target_temp_current` on next update. Panel displays the HA-set value and does not overwrite it. |
| Panel idle for extended period | All dirty flags remain false. Panel continuously mirrors controller state without asserting its own values. Only user interaction sets dirty flags and begins publishing panel-originated commands. |
| Multiple rapid encoder turns | `cmd_target_temp` updated locally on panel, sent on next transport cycle (500ms). Controller receives latest value. Intermediate values naturally debounced by transport interval. |
| Contactor fails to close | `heat_mode_active` = true but `contactor_aux_closed` = false. Panel shows "Heater: OFF" correctly. Info page shows aux mismatch warning. Controller's existing welded-contactor detection handles the inverse case. |

---

## Implementation Order

1. **Transport spike** (Phase 0) — Validate bidirectional packet_transport on bare ESP32 dev boards over direct UART (bench only). Includes: bidirectional data flow, counter-based one-shot commands, NaN suppression for sync-before-publish. Pass/fail gates all subsequent work.
2. **Controller firmware changes** — Add fault_code global, UART, packet transport provider/consumer, command handlers with validation. Test against spike panel mock.
3. **Board selection & procurement** — Pick CrowPanel or MaTouch based on spike experience with GPIO availability and ESPHome config complexity.
4. **RS-485 integration** — Add 3.3V RS-485 transceivers (SP3485, MAX3485, or SN65HVD75) to both devices. Test over actual Cat5e cable run through conduit. Confirm full-duplex vs half-duplex topology. Direct 3.3V UART is lab-only; RS-485 is the expected production layer given EMI from the contactor and cable run distance.
5. **Panel firmware** — Build `sauna-panel.yaml` with display, encoder, LVGL UI, packet transport, sync-before-publish logic, and status ring script.
6. **Enclosure** — Design or source 3D-printed wall mount for chosen panel board.

---

## Open Items

### Nice to have (post-MVP)

1. **Session timer** — Elapsed time display on main page. Computed on panel from `heat_mode_active` transitions.
2. **Startup animation** — Brief boot screen while waiting for first data from controller.
3. **Screensaver / dimming** — Dim display after N minutes of no interaction. Wake on encoder turn or touch.
