"""Exercise the actual C++ counter guards without ESP32 hardware.

Run: python3 -m unittest discover -s tests
Requires a host C++ compiler (c++).
"""
import pathlib
import re
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


class PacketCounterTests(unittest.TestCase):
    def test_rebroadcast_and_panel_restart(self):
        source = (ROOT / "firmware/control-board/packages/common.yaml").read_text()
        functions = []
        checks = []
        for name in ("heat_on", "heat_off", "clear_fault", "light_toggle"):
            block = source.split(f"    id: cmd_{name}_ctr\n", 1)[1]
            gate = block.split("        - lambda: |-\n", 1)[1]
            # Stop after the counter guard, before any hardware/action code.
            gate = gate.split("            if (x <= 0.0f) return;", 1)[0]
            self.assertNotIn("\n  - platform:", gate)
            gate += "            if (x <= 0.0f) return;"
            functions.append(f"void {name}(float x, int &actions) {{\n{gate}\n++actions;\n}}")
            checks.append(f"""
              {{ int actions = 0;
                 {name}(NAN, actions);
                 {name}(42, actions); // Controller reboot: baseline, no action.
                 {name}(42, actions); // Rebroadcast, no action.
                 assert(actions == 0);
                 {name}(43, actions);
                 {name}(43, actions);
                 assert(actions == 1);
                 {name}(0, actions); // Panel reboot resets its counter.
                 {name}(0, actions);
                 assert(actions == 1);
                 {name}(1, actions); // First post-reboot command must work.
                 {name}(1, actions);
                 assert(actions == 2);
                 {name}(0, actions);
                 {name}(1, actions); // Repeated restart at counter 1.
                 assert(actions == 3);
              }}
            """)
        program = "#include <cmath>\n#include <cassert>\n" + "\n".join(functions)
        program += "\nint main() {" + "\n".join(checks) + "\n}"
        with tempfile.TemporaryDirectory() as tmp:
            cpp = pathlib.Path(tmp) / "counters.cpp"
            exe = pathlib.Path(tmp) / "counters"
            cpp.write_text(program)
            subprocess.run(["c++", "-std=c++17", str(cpp), "-o", str(exe)], check=True)
            subprocess.run([str(exe)], check=True)


if __name__ == "__main__":
    unittest.main()
