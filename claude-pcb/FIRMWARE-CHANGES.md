# Firmware changes required for the Rev B board

Three small edits to `sauna-controller.yaml`. Nothing else changes — the
panel firmware is unaffected.

## 1. LED PWM GPIO remap (required)

Rev B routes the gate resistors so the channels land crossing-free, which
swaps the GPIO order (see REV-B-DESIGN-REVIEW.md, "Layout-driven
improvement"). Update the four `output:` pins:

| Channel | Rev A pin | Rev B pin |
|---|---|---|
| Red    | GPIO16 | **GPIO19** |
| Green  | GPIO17 | **GPIO18** |
| Blue   | GPIO18 | **GPIO17** |
| White  | GPIO19 | **GPIO16** |

```yaml
# output: section — Rev B pin assignments
  - platform: ledc
    id: out_red
    pin: GPIO19    # was GPIO16
  - platform: ledc
    id: out_green
    pin: GPIO18    # was GPIO17
  - platform: ledc
    id: out_blue
    pin: GPIO17    # was GPIO18
  - platform: ledc
    id: out_white
    pin: GPIO16    # was GPIO19
```

If the Rev B board is flashed with Rev A firmware the lights still work —
colors are just shuffled (R<->W, G<->B). Safe failure mode, but fix it.

## 2. FAULT LED on GPIO23 (optional, new hardware)

Rev B has a red LED wired to GPIO23 through 1 k. Suggested addition:

```yaml
output:
  - platform: gpio
    id: fault_led_out
    pin: GPIO23

# drive it wherever fault_latched changes, e.g.:
#   - output.turn_on: fault_led_out   when fault latches
#   - output.turn_off: fault_led_out  when fault clears
```

Unused, the LED simply stays dark.

## 3. High-limit comment fix (cosmetic)

The GPIO33 binary sensor comment `# FALSE when tripped (opto pulls high)`
contradicts the lambda. The circuit (Rev A and Rev B) senses 24 V presence at
the post-SRL250 node: opto conducts when the loop is healthy (GPIO33 low),
GPIO33 goes high when tripped, and `return x;` is correct. Suggested comment:
`# opto ON (GPIO low) = loop OK; GPIO high = SRL250 open / tripped`.

## 4. Spare opto input (only if OPT3 is populated)

The Rev B board carries a third opto channel on GPIO25 fed from J_SPARE.
The firmware block for it already exists, commented out, as
`Future Opto Monitoring` — uncomment it when you wire something to J_SPARE.
