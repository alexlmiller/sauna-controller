"""Rev A/Dial contract and fail-off regression checks; no hardware required."""
import pathlib
import re
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
BOARD = ROOT / 'firmware/control-board/packages/common.yaml'
TRANSPORT = ROOT / 'firmware/wall-panel/packages/transport-wired.yaml'


class InstallationTests(unittest.TestCase):
    def test_uart_contract(self):
        board, panel = BOARD.read_text(), TRANSPORT.read_text()
        for sender, receiver in ((board, panel), (panel, board)):
            exports = set(re.findall(r'^ {4,6}- ([\w$}{]+)$', sender.split('\npacket_transport:')[1], re.M))
            consumers = re.findall(r'  - platform: packet_transport\n(.*?)(?=\n  - platform:|\Z)', receiver, re.S)
            for consumer in consumers:
                local = re.search(r'^    id: (.+)$', consumer, re.M).group(1)
                remote = re.search(r'^    remote_id: (.+)$', consumer, re.M)
                self.assertIn(remote.group(1) if remote else local, exports)
        for target, expected in [('sauna-controller.yaml', 'sauna-controller'),
                                 ('sauna-panel.yaml', 'sauna-panel-wired')]:
            self.assertIn(f'  device_name: {expected}\n', (ROOT / target).read_text())
        self.assertEqual(set(re.findall(r'    provider: (.+)', board)), {'sauna-panel-wired'})
        self.assertEqual(set(re.findall(r'    provider: (.+)', panel)), {'sauna-controller'})

    def test_sensor_and_high_limit_fail_off(self):
        source = BOARD.read_text()
        guard = source.split('          // Bypass thermostat minimum-run timers', 1)[1]
        guard = guard.split('\n          const bool ceiling_valid =', 1)[1]
        guard = 'const bool ceiling_valid =' + guard.split('          // ============================================', 1)[0]
        clear = source.split('  - id: try_clear_fault\n', 1)[1].split('      - lambda: |-\n', 1)[1]
        clear = clear.split('\nbutton:', 1)[0].replace('${feedback_sensor_id}', 'feedback')
        program = r'''
#include <cassert>
#include <cmath>
#include <cstdint>
#include <string>
#define id(x) x
#define ESP_LOGI(...)
namespace climate { enum { CLIMATE_MODE_OFF, CLIMATE_MODE_HEAT }; }
struct Sensor { float state = 20; bool ready = true; bool has_state() { return ready; } };
struct Binary { bool state = false; bool ready = true; bool has_state() { return ready; } };
struct Thermostat {
  int mode = climate::CLIMATE_MODE_HEAT;
  struct Call { Thermostat *owner; void set_mode(int m) { owner->mode = m; } void perform() {} };
  Call make_call() { return {this}; }
};
struct Output { bool on = true; void turn_off() { on = false; } };
Sensor ceiling_temp_c, soft_high_temp_f;
Binary high_limit_trip, door_sensor, feedback;
Thermostat sauna_thermostat;
Output coil_output;
bool fault_latched, coil_is_on;
int fault_code_val;
std::string last_trip_reason;
uint32_t now, ceiling_last_valid_ms;
uint32_t millis() { return now; }
void reset() {
  ceiling_temp_c = {}; high_limit_trip = {}; door_sensor = {}; feedback = {};
  sauna_thermostat = {}; coil_output = {};
  fault_latched = false; coil_is_on = true; fault_code_val = 0;
  now = 20000; ceiling_last_valid_ms = 19000; soft_high_temp_f.state = 210;
}
'''
        program += '\nvoid guard() {\n' + guard + '\n}\nvoid clear_fault() {\n' + clear + '\n}\n'
        program += r'''
int main() {
  reset(); guard(); assert(!fault_latched && coil_output.on);
  reset(); ceiling_temp_c.state = NAN; guard();
  assert(fault_latched && fault_code_val == 4 && !coil_output.on && !coil_is_on);
  clear_fault(); assert(fault_latched);
  ceiling_temp_c.state = 20; clear_fault();
  assert(!fault_latched && !coil_output.on && sauna_thermostat.mode == climate::CLIMATE_MODE_OFF);
  reset(); ceiling_temp_c.ready = false; guard(); assert(fault_latched && !coil_output.on);
  reset(); ceiling_last_valid_ms = 4000; guard(); assert(fault_code_val == 4 && !coil_output.on);
  reset(); ceiling_last_valid_ms = 0; guard(); assert(fault_code_val == 4 && !coil_output.on);
  reset(); high_limit_trip.state = true; guard();
  assert(fault_code_val == 5 && !coil_output.on); clear_fault(); assert(fault_latched);
  high_limit_trip.state = false; door_sensor.state = true; clear_fault(); assert(fault_latched);
  door_sensor.state = false; feedback.state = true; clear_fault(); assert(fault_latched);
  feedback.state = false; ceiling_temp_c.state = 110; clear_fault(); assert(fault_latched);
  ceiling_temp_c.state = 20; clear_fault(); assert(!fault_latched && !coil_output.on);
  reset(); high_limit_trip.ready = false; guard(); assert(fault_code_val == 5 && !coil_output.on);
  reset(); now = 1000; ceiling_last_valid_ms = UINT32_MAX - 1000;
  guard(); assert(!fault_latched); // millis rollover does not invalidate fresh data.
  reset(); sauna_thermostat.mode = climate::CLIMATE_MODE_OFF; coil_is_on = false;
  ceiling_temp_c.ready = false; guard(); assert(!fault_latched); // Normal startup before sensor discovery.
}
'''
        with tempfile.TemporaryDirectory() as tmp:
            cpp, exe = pathlib.Path(tmp) / 'guard.cpp', pathlib.Path(tmp) / 'guard'
            cpp.write_text(program)
            subprocess.run(['c++', '-std=c++17', str(cpp), '-o', str(exe)], check=True)
            subprocess.run([str(exe)], check=True)


if __name__ == '__main__':
    unittest.main()
