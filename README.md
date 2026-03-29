# Local & Smart Sauna Controller
No more dealing with cloud services or crappy proprietary apps for your home sauna - this is an open-source sauna controller allowing you to control your sauna from anywhere but without any commercial/cloud dependenceies via ESPHome + Home Assistant.

The design offers robust controls of both the heater and lights, along with safeties similar to a commercial unit, including: 
- Contol of a heater via a **24 VDC coil contactor**
- Dual highly accuracy temp sensors (primary high on the wall + one closer to the sitting bench)
- **RGBW under-bench lighting** (24 V, PWM via MOSFETs)

Safeties include
- **Hardware manual-reset high-limit** in series with the coil (failsafe)
- **Door safety** (instant off + timeout fault)
- Strong fault model (latching) + optional **contactor auxiliary feedback** + **high-limit status** sensing

The ESP handles the actual control of the sauna. Input can come from Home Assistant or from a dedicated **wall-mounted panel** (CrowPanel 2.1" round display with rotary encoder) installed at the sauna door, connected via wired RS-485 or WiFi.

> ⚠️ **Electrical safety**: This project switches lethal voltages. Get a licensed electrician/PE to review & install. Use appropriately rated components and follow local code.

---
![Controller Box](https://github.com/user-attachments/assets/d93286e9-3aa9-4a17-b4d4-1751c39da36b)

## Hardware Design Overview
The total cost for the hardware should be a bit <$500 + whatever lighting you choose to use

The single largest cost is the contactor ($100-$150 USD, depending on size) - while there are cheaper options out there, this is the heart of the system and handles a lot of power flowing through it

The other big cost is that various DIN rail parts - I chose to use DIN rail components in order to keep things very clean, but if that's not a priority, you can skip many of those and save $50-$100.

### Power & Control Architecture
- **24 VDC single rail** (Mean Well HDR-150-24) feeds:
  - Contactor coil (through **DIN fuse → manual-reset high-limit → coil**)
  - **RGBW LED strip** branch (separate DIN fuse)
  - **DDR-15G-5** → **5 V** for ESP32 + MAX31865 boards
- **Low-side MOSFET drivers** (Adafruit PID 5648) for:
  - **Coil** (1× board)
  - **RGBW** (4× boards: R/G/B/W channels)
- **Separation**: HV (feeder → contactor → heater) and LV (24 V, logic) kept segregated

### Safety Layers
- **Hardware**: Manual-reset high-limit (e.g., SUPCO SRL250, ~250 °F) in series with coil kills heat independent of software.
- **Software**:
  - Software high-temp limit (default **210 °F**)
  - ΔT stratification fault (ceiling vs bench)
  - Door open **timeout** fault
  - Session auto-off
  - Sensor NaN faults + **bench fallback** (optional, with offset)
  - **WDT** (30 s): any hang → reboot → coil defaults **OFF**
- **Diagnostics**:
  - **Contactor aux feedback** (detects welded or failed-to-close)
  - Optional **SRL250 status** input (shows “High-Limit Tripped”)
  - `last_trip_reason` text + HA notifications (see automations)

---

## Parts List

- **ESP32 DevKitC-32E** (1×)
- **Contactor ≥65 A, 24 VDC coil** — Schneider Easy TeSys **DPE65BD** (1×)
- **Auxiliary contact block** compatible with DPE65BD (1× NO or 1NO/1NC)
- **24 V DIN PSU 150 W** — Mean Well **HDR-150-24** (1×)
- **24→5 V DIN DC-DC** — Mean Well **DDR-15G-5** (1×)
- **DB18B20** probes (2×)
- **MOSFET driver boards** — Adafruit PID **5648** (5× total: 1× coil, 4× RGBW)
- **LEDYi 24 V RGBW sauna strip** ~5 m (1×), aluminum channel + frosted lens (~5 m)
- **Manual-reset high-limit** — SUPCO **SRL250** (~250 °F, NC) (1×)
- **DIN fuse holders** (10×38 mm) + fuses:
  - **1–2 A** (coil branch)
  - **7.5 A time-delay** (LED branch; size per LED power)
- Phoenix Contact DIN terminals (HV/LV), ground terminal, jumper bars
- **5-core high-temp silicone cable** (18 AWG) for LED, shielded twisted pair for DS18B20s
- **High-temp cable glands** for wires
- **Enclosure** (recommended): **500×400×200 mm** polycarbonate with backplate

---

## Wiring Plan

### High Voltage (HV)
- **Feeder 240 V → contactor (power poles) → heater**. Ground/bond per code. Keep HV/LV physically separated.

### LV Power
- **HDR-150-24** → 24 V bus (+24 V/0 V).
- **DDR-15G-5** from 24 V → **5 V** to ESP32 **VIN**. **0 V common** for all LV.

### Contactor Coil Safety Loop (24 V)
- **+24 V → DIN fuse (1–2 A) → SRL250 (NC, manual-reset) → contactor coil (+)**  
- **Contactor coil (−) → MOSFET driver OUT− / OUT+ → OPEN** (coil channel)  
- **Driver VIN 24V; GPIO13 → SIG; GND → GND**

**Optional inputs (recommended):**
- **SRL250 status** (tripped/open = TRUE): 24 V across SRL250 → opto input → **GPIOXX**.
- **Contactor aux feedback** (aux closed = TRUE): 24 V → aux → opto input → **GPIOXX**.

### Door Sensor
- Reed: one lead to **GND**, other to **GPIO22** (INPUT_PULLUP). Firmware: immediate OFF + timeout fault.

### DS18B20 Sensors (One-Wire but Independent Busses)
- **BUS1=GPIO26** (Bench)  
- **BUS2=GPIO27** (Ceiling) 
- 3.3V to VIN; 0 V common

### RGBW Lighting (24 V PWM via MOSFETs)
- **+24 V → DIN fuse (LED) ~7.5 A TD → strip V+**
- **R−/G−/B−/W− → each to its MOSFET driver OUT−**; **all OUT+ → OPEN**
- **PWM pins**:  
  - **GPIO16 → Red SIG**  
  - **GPIO17 → Green SIG**  
  - **GPIO18 → Blue SIG**  
  - **GPIO19 → White SIG**
- 5-core 18 AWG silicone cable through high-temp gland; mount strip **under benches** in **aluminum channel** with screws. Power-inject V+ at both ends if needed.

### Grounding & EMC
- Single **0 V star** (ESP32, drivers, DC-DC, PSU, etc).
- Label terminals: **24V+**, **0V**, **COIL+**, **COIL−**, **LED_V+**, **LED_R−/G−/B−/W−**, **RTD1**, **RTD2**, **DOOR**, **AUX_FB**, **HLIMIT_FB**.

---

## ESP32 Pinout

**Power**
- **VIN (5 V)** ← DDR-15G-5
- **GND** ← 0 V common
- **3V3** → DS18B20 VCC (both)

**DS18B20 Temp Sensors**
- **GPIO26** Bench
- **GPIO27** Ceiling 

**Inputs**
- **GPIO22** Door (INPUT_PULLUP)
- **GPIO32** Contactor Aux Closed (via opto) — TRUE = aux closed
- **GPIO33** High-Limit Tripped (via opto) — TRUE = SRL250 open  

**Outputs**
- **GPIO13** Coil MOSFET SIG
- **GPIO16/17/18/19** RGBW MOSFET SIG (R/G/B/W)

**Panel UART (RS-485)**
- **GPIO14** TX to panel
- **GPIO4** RX from panel

**Reserved**
- **GPIO0/2/12/15** NC (boot straps)
- **GPIO1/3** UART (leave free)
  
---

## Software & UI
The control software runs entirely on the ESP32. Input comes from Home Assistant and/or the wall panel.

### HA Device Page
<img width="723" height="761" alt="Home Assistant" src="https://github.com/user-attachments/assets/819bb462-3065-4353-bc77-227a327b023d" />

### Phone Dashboard
<img width="606" height="767" alt="Dashboared" src="https://github.com/user-attachments/assets/f103d0ee-843a-4577-ad8f-8157f9dca8a7" />

---

## Wall Panel

A dedicated physical controller using the **Elecrow CrowPanel 2.1" Rotary Display** — a round 480x480 IPS touchscreen with a built-in rotary encoder, powered by an ESP32-S3.

The panel provides full local control of the sauna without needing a phone or WiFi for basic operation (when using wired RS-485). WiFi is available for OTA updates and as an alternative transport during development.

### Hardware
- **Display**: Elecrow CrowPanel 2.1" (ESP32-S3-R8, ST7701S 480x480 round IPS, CST826 capacitive touch)
- **Input**: Built-in rotary encoder with push button (via PCF8574 I/O expander)
- **Communication**: SP3485 RS-485 transceivers (3.3V) over Cat5e, or WiFi via Home Assistant API
- **Power**: 5V from existing DDR-15G-5 supply via Cat5e

### UI Design
Nest thermostat-inspired dark theme with a bold colored ring as the primary visual element. Three pages:

**Heater Page**
- Large temperature display (96px light-weight Montserrat)
- Colored ring shows heater state: gray (off), blue (standby), orange (heating), green (at target), red (fault)
- Target temperature and status text below

**Lights Page**
- Ring shows brightness level, color matches the active light preset
- 4 color preset circles in a 2x2 grid: White (4500K), Warm (2700K), Red, Green
- Tap a circle to activate that preset

**Status Page**
- Ceiling and bench temperature readouts
- Door, heater, hi-limit, and aux contact status (color-coded)
- Clear fault button (visible only when faulted)

### Interaction Model
| Input | Heater Page | Lights Page |
|-------|------------|-------------|
| **Encoder rotate** | Adjust target temp (pending) | Adjust brightness (live) |
| **Encoder click** | Set target + turn on | Toggle lights on/off |
| **Encoder long press** | Turn heater off | — |
| **Tap ring gap** | Next page | Next page |
| **Tap preset circle** | — | Activate color preset |

### Firmware Architecture
The panel firmware is split into three files using ESPHome's `packages:` system:

| File | Purpose |
|------|---------|
| `sauna-panel-common.yaml` | Shared UI, hardware config, encoder logic, LVGL pages, fonts, scripts |
| `sauna-panel-wifi.yaml` | WiFi transport — subscribes to controller entities via HA API, sends commands via HA service calls |
| `sauna-panel-wired.yaml` | Wired transport — UART packet_transport over RS-485, template command sensors |

The UI and interaction logic are identical regardless of transport. Only the data source and command mechanism differ.

### Building & Flashing

```bash
# WiFi version (for desk testing via Home Assistant)
esphome run sauna-panel-wifi.yaml

# Wired version (for production install via RS-485)
esphome run sauna-panel-wired.yaml
```

Both require a `secrets.yaml` with `wifi_ssid`, `wifi_password`, `ota_password`, and `api_key` (WiFi version only).

### Panel Wiring (Wired Mode)
- **Cat5e** from controller box to panel location (~5 ft)
- **SP3485** 3.3V RS-485 transceivers on both ends (DE/RE tied for full-duplex)
- **5V power** pulled from the existing DDR-15G-5 supply over spare Cat5e pairs
- **Controller UART**: GPIO14 (TX) / GPIO4 (RX)
- **Panel UART**: GPIO43 (TX) / GPIO44 (RX) — requires `logger: baud_rate: 0`

See `PANEL-REQUIREMENTS.md` for the full design specification including transport protocol details, command semantics, and safety architecture.
