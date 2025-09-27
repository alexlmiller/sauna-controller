# Local & Smart Sauna Controller
No more dealing with cloud services or crappy proprietary apps for your home sauna - this is an open-source sauna controller allowing you to control your sauna from anywhere but without any commercial/cloud dependenceies via ESPHome + Home Assistant.

The design offers robust controls of both the heater and lights, along with safeties similar to a commercial unit, including: 
- Contol of a heater via a **24 VDC coil contactor**
- Dual highly accuracy **PT100** temp sensors (primary high on the wall + one closer to the sitting bench)
- **RGBW under-bench lighting** (24 V, PWM via MOSFETs)

Safeties include
- **Hardware manual-reset high-limit** in series with the coil (failsafe)
- **Door safety** (instant off + timeout fault)
- Strong fault model (latching) + optional **contactor auxiliary feedback** + **high-limit status** sensing

While the ESP handles the actual control of the sauna, currently all input is done via Home Assistant - in the future I'll add a physical hardware controller based on a second ESP Board + TFT Display + rotary encoder that can be installed at the door of the sauna.

> ⚠️ **Electrical safety**: This project switches lethal voltages. Get a licensed electrician/PE to review & install. Use appropriately rated components and follow local code.

---

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
  - Door open **instant-off** + **timeout** fault
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
- **MAX31865 PT100** boards (2×) + **PT100 3-wire probes** (2×)
- **MOSFET driver boards** — Adafruit PID **5648** (5× total: 1× coil, 4× RGBW)
- **LEDYi 24 V RGBW sauna strip** ~5 m (1×), aluminum channel + frosted lens (~5 m)
- **Manual-reset high-limit** — SUPCO **SRL250** (~250 °F, NC) (1×)
- **DIN fuse holders** (10×38 mm) + fuses:
  - **1–2 A** (coil branch)
  - **7.5 A time-delay** (LED branch; size per LED power)
- Phoenix Contact DIN terminals (HV/LV), ground terminal, jumper bars
- **5-core high-temp silicone cable** (18 AWG) for LED, shielded twisted pair for PT100
- **High-temp cable glands** for LED/PT100/door
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
- Reed: one lead to **GND**, other to **GPIO21** (INPUT_PULLUP). Firmware: immediate OFF + timeout fault.

### PT100 Sensors (MAX31865, shared SPI)
- **CLK=GPIO18, MOSI=GPIO17, MISO=GPIO19** (both boards)  
- **CS1=GPIO5** (Ceiling), **CS2=GPIO4** (Bench)  
- 5V to VIN; 0 V common. Configure **3-wire** jumpers**.

### RGBW Lighting (24 V PWM via MOSFETs)
- **+24 V → DIN fuse (LED) ~7.5 A TD → strip V+**
- **R−/G−/B−/W− → each to its MOSFET driver OUT−**; **all OUT+ → OPEN**
- **PWM pins**:  
  - **GPIO32 → Red SIG**  
  - **GPIO33 → Green SIG**  
  - **GPIO26 → Blue SIG**  
  - **GPIO25 → White SIG**
- 5-core 18 AWG silicone cable through high-temp gland; mount strip **under benches** in **aluminum channel** with screws. Power-inject V+ at both ends if needed.

### Grounding & EMC
- Single **0 V star** (ESP32, drivers, MAX31865, DC-DC, PSU).
- Label terminals: **24V+**, **0V**, **COIL+**, **COIL−**, **LED_V+**, **LED_R−/G−/B−/W−**, **RTD1**, **RTD2**, **DOOR**, **AUX_FB**, **HLIMIT_FB**.

---

## ESP32 Pinout

**Power**
- **VIN (5 V)** ← DDR-15G-5
- **GND** ← 0 V common
- **3V3** → MAX31865 VCC (both)

**SPI (shared)**
- **GPIO18** CLK, **GPIO17** MOSI, **GPIO19** MISO  
- **GPIO5** CS (MAX31865 #1, Ceiling)  
- **GPIO4** CS (MAX31865 #2, Bench)

**Inputs**
- **GPIO21** Door (INPUT_PULLUP)
- **GPIOXX** High-Limit Tripped (via opto) — TRUE = SRL250 open  
- **GPIOXX** Contactor Aux Closed (via opto) — TRUE = aux closed

**Outputs**
- **GPIO13** Coil MOSFET SIG
- **GPIO32/33/26/25** RGBW MOSFET SIG (R/G/B/W)

**Reserved**
- **GPIO25/26** reserved for future RS-485
- **GPIO0/2/15** NC (boot straps)
- **GPIO1/3** UART (leave free)
  
---
