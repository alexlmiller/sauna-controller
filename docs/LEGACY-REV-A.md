# Legacy Rev A

Rev A was an early board/hand-wired compatibility target. It is kept only for
the few existing early systems.

New builds should use:

- [`firmware/control-board/rev-b.yaml`](../firmware/control-board/rev-b.yaml)
- [`firmware/wall-panel/wired.yaml`](../firmware/wall-panel/wired.yaml)
- [`firmware/wall-panel/wifi.yaml`](../firmware/wall-panel/wifi.yaml)

Legacy files:

- [`firmware/legacy/rev-a/control-board.yaml`](../firmware/legacy/rev-a/control-board.yaml)
- [`firmware/legacy/rev-a/wall-panel-wired.yaml`](../firmware/legacy/rev-a/wall-panel-wired.yaml)
- [`firmware/legacy/rev-a/wall-panel-wifi.yaml`](../firmware/legacy/rev-a/wall-panel-wifi.yaml)

Do not use these for a new self-assembled or carrier-PCB build unless you are
intentionally matching an existing Rev A installation.
