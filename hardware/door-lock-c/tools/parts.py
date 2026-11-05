"""Single source of the board's parts, nets and LCSC numbers (used by gen_sch and gen_pcb).

Variant C of jaskier_door_lock: two doors, a socketed ESP32-C3 SuperMini, optional RS485.
Schematic coordinates are mm on an A3 sheet. LCSC numbers checked against JLCPCB and
LCSC on 5 November 2026.
"""

PROJECT = 'door-lock-c'

R0603 = 'Resistor_SMD:R_0603_1608Metric'
C0603 = 'Capacitor_SMD:C_0603_1608Metric'
C1206 = 'Capacitor_SMD:C_1206_3216Metric'
TB = 'TerminalBlock_Phoenix:TerminalBlock_Phoenix_PT-1,5-{n}-3.5-H_1x0{n}_P3.50mm_Horizontal'
DRV_FP = 'Package_SO:Texas_HTSOP-8-1EP_3.9x4.9mm_P1.27mm_EP2.95x4.9mm_Mask2.4x3.1mm_ThermalVias'
SOCKET = 'Connector_PinSocket_2.54mm:PinSocket_1x08_P2.54mm_Vertical'
JUMPER = 'Jumper:SolderJumper-2_P1.3mm_Open_RoundedPad1.0x1.5mm'

LCSC = {
    '100n': 'C14663', '10u50': 'C13585', '10u25': 'C15850', '100u35': 'C72478',
    '100k': 'C25803', '56k': 'C23206', '10k': 'C25804', '4.7k': 'C23162', '1k': 'C21190',
    '680': 'C23228', '120': 'C22787', '100': 'C22775', '0R1': 'C25334',
}


def R(value, xy, rot, n1, n2, fp=R0603):
    return ('Device:R', value, fp, LCSC['0R1' if value == '0.1' else value], xy, rot, {'1': n1, '2': n2}, {})


def C(value, xy, rot, n1, n2, fp=C0603, code=None):
    return ('Device:C', value, fp, code or LCSC['100n'], xy, rot, {'1': n1, '2': n2}, {})


PARTS = {
    # ------------------------------------------------------------ 12 V input and 5 V
    'J1': ('Connector:Screw_Terminal_01x02', 'Power: +12V GND', TB.format(n=2), 'C466970',
           (25.4, 50.8), 0, {'1': '+12V_IN', '2': 'GND'}, {'mpn': 'DORABO DB125-3.5-2P-GN-S'}),
    'F1': ('Device:Polyfuse', '1.1A 24V', 'Fuse:Fuse_1812_4532Metric', 'C883149',
           (45.72, 40.64), 90, {'1': '+12V_IN', '2': 'VIN_F'}, {'mpn': 'BHFUSE BSMD1812-110-24V (hold 1.1 A, trip 2.2 A)'}),
    # P-MOSFET reverse-polarity switch: drain to the input, source to the board
    'Q1': ('Transistor_FET:AO3401A', 'AO3401A', 'Package_TO_SOT_SMD:SOT-23', 'C15127',
           (68.58, 40.64), 90, {'1': 'QG', '2': 'VBAT', '3': 'VIN_F'}, {}),
    'R1': R('100k', (83.82, 45.72), 0, 'VBAT', 'QG'),
    'R2': R('100k', (68.58, 58.42), 0, 'QG', 'GND'),
    'D1': ('Diode:SMAJ16A', 'SMAJ16A', 'Diode_SMD:D_SMA', 'C364288',
           (96.52, 50.8), 270, {'1': 'VBAT', '2': 'GND'}, {}),
    'C1': ('Device:C_Polarized', '100u 35V', 'Capacitor_SMD:CP_Elec_6.3x7.7', 'C72478',
           (109.22, 50.8), 0, {'1': 'VBAT', '2': 'GND'}, {'mpn': 'ROQANG RVT1V101M0607'}),
    'C2': C('10u 50V', (121.92, 50.8), 0, 'VBAT', 'GND', C1206, LCSC['10u50']),
    'PS1': ('Converter_DCDC:R-78E5.0-0.5', 'K7805-500R3', 'Converter_DCDC:Converter_DCDC_RECOM_R-78E-0.5_THT', 'C2992390',
            (144.78, 40.64), 0, {'1': 'VBAT', '2': 'GND', '3': '+5V'}, {'mpn': 'YLPTEC K7805-500R3 (6.5-36 V in, 5 V 0.5 A)'}),
    'C3': C('10u 25V', (162.56, 50.8), 0, '+5V', 'GND', 'Capacitor_SMD:C_0805_2012Metric', LCSC['10u25']),
    'D2': ('Diode:SS34', 'SS34', 'Diode_SMD:D_SMA', 'C8678',
           (190.5, 40.64), 180, {'2': '+5V', '1': '+5V_ESP'}, {}),
    # ------------------------------------------------------------ ESP32-C3 SuperMini socket
    # J5 is the SuperMini's 5V..IO0 row, J6 its IO5..IO21 row (pin 1 at the USB end).
    'J5': ('Connector_Generic:Conn_01x08', 'SuperMini: 5V..IO0', SOCKET, 'C27438',
           (264.16, 50.8), 0,
           {'1': '+5V_ESP', '2': 'GND', '3': '+3V3', '4': 'IN1_A', '5': 'IN2_A', '6': 'LED_IO',
            '7': 'DOOR_A', '8': 'DOOR_B'}, {'mpn': 'BOOMELE 2.54 1x8P female, 8.5 mm'}),
    'J6': ('Connector_Generic:Conn_01x08', 'SuperMini: IO5..IO21', SOCKET, 'C27438',
           (264.16, 86.36), 0,
           {'1': 'IN1_B', '2': 'IN2_B', '3': 'EXT', '4': 'SDA', '5': 'SCL', '6': 'RS_DE',
            '7': 'RS_RO', '8': 'RS_DI'}, {'mpn': 'BOOMELE 2.54 1x8P female, 8.5 mm'}),
    'C41': C('100n', (284.48, 99.06), 0, '+3V3', 'GND'),
    'R43': R('4.7k', (297.18, 96.52), 0, '+3V3', 'SDA'),
    'R44': R('4.7k', (309.88, 96.52), 0, '+3V3', 'SCL'),
    'J7': ('Connector_Generic:Conn_01x06', 'Extension', 'Connector_PinHeader_2.54mm:PinHeader_1x06_P2.54mm_Vertical', 'C492405',
           (340.36, 96.52), 0, {'1': '+3V3', '2': 'SDA', '3': 'SCL', '4': 'EXT', '5': '+5V_ESP', '6': 'GND'},
           {'mpn': 'XFCN PZ254V-11-06P'}),
    # ------------------------------------------------------------ status LED (WS2812-type)
    # Powered from 5 V through D4 (about 4.3 V), so the 3.3 V data line clears 0.7 x VDD.
    'D4': ('Diode:1N4148W', '1N4148W', 'Diode_SMD:D_SOD-123', 'C81598',
           (297.18, 40.64), 180, {'2': '+5V', '1': 'VLED'}, {}),
    'C42': C('100n', (312.42, 50.8), 0, 'VLED', 'GND'),
    # 5050 package: its pads stick out of the body, so it can be soldered with an iron
    'LED2': ('LED:WS2812B', 'XL-5050RGBC-2812B', 'LED_SMD:LED_WS2812B_PLCC4_5.0x5.0mm_P3.2mm', 'C2843785',
             (340.36, 55.88), 0, {'1': 'VLED', '3': 'GND', '4': 'LED_DIN'}, {'mpn': 'XINGLIGHT XL-5050RGBC-2812B'}),
    'R41': R('10k', (297.18, 63.5), 0, '+3V3', 'LED_IO'),     # IO2 is a strapping pin: high at boot
    'R42': R('100', (312.42, 68.58), 90, 'LED_IO', 'LED_DIN'),
    # ------------------------------------------------------------ RS485 (optional, Modbus RTU)
    'U5': ('Interface_UART:SP3485EN', 'SP3485EN', 'Package_SO:SOIC-8_3.9x4.9mm_P1.27mm', 'C8963',
           (279.4, 175.26), 0,
           {'1': 'RS_RO', '2': 'RS_DE', '3': 'RS_DE', '4': 'RS_DI', '5': 'GND', '6': 'RS485_A', '7': 'RS485_B', '8': '+3V3'},
           {'mpn': 'MaxLinear SP3485EN-L/TR'}),
    'C31': C('100n', (254.0, 152.4), 0, '+3V3', 'GND'),
    'R31': R('10k', (241.3, 160.02), 0, '+3V3', 'RS_RO'),
    'R32': R('10k', (241.3, 190.5), 0, 'RS_DE', 'GND'),       # transmitter off while the ESP boots
    'D3': ('Diode:SM712_SOT23', 'SM712', 'Package_TO_SOT_SMD:SOT-23', 'C172881',
           (314.96, 200.66), 0, {'1': 'RS485_A', '2': 'RS485_B', '3': 'GND'}, {'mpn': 'Littelfuse SM712-02HTG'}),
    'R33': R('120', (330.2, 165.1), 0, 'RS485_A', 'TERM'),
    # 120 ohm termination on a 2-pin header: fit a jumper cap on the last device of the bus
    'JP1': ('Connector_Generic:Conn_01x02', 'TERM 120R jumper', 'Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical',
            'C492401', (350.52, 167.64), 0, {'1': 'TERM', '2': 'RS485_B'}, {'mpn': 'XFCN PZ254V-11-02P (cap: BOOMELE C100114, not assembled)'}),
    'R34': R('680', (365.76, 147.32), 0, '+3V3', 'BIAS_A'),
    'JP2': ('Jumper:SolderJumper_2_Open', 'BIAS A (open)', JUMPER, '',
            (381.0, 157.48), 0, {'1': 'BIAS_A', '2': 'RS485_A'}, {'in_bom': False}),
    'R35': R('680', (365.76, 185.42), 0, 'BIAS_B', 'GND'),
    'JP3': ('Jumper:SolderJumper_2_Open', 'BIAS B (open)', JUMPER, '',
            (381.0, 175.26), 0, {'1': 'RS485_B', '2': 'BIAS_B'}, {'in_bom': False}),
    'J4': ('Connector:Screw_Terminal_01x06', 'RS485: A B GND A B GND', TB.format(n=6), 'C5290323',
           (398.78, 205.74), 0,
           {'1': 'RS485_A', '2': 'RS485_B', '3': 'GND', '4': 'RS485_A', '5': 'RS485_B', '6': 'GND'},
           {'mpn': 'DORABO DB125-3.5-6P-GN-S'}),
    # ------------------------------------------------------------ mechanical, ERC flags
    'H1': ('Mechanical:MountingHole', 'M3', 'MountingHole:MountingHole_3.2mm_M3', '', (279.4, 254.0), 0, {}, {'in_bom': False}),
    'H2': ('Mechanical:MountingHole', 'M3', 'MountingHole:MountingHole_3.2mm_M3', '', (292.1, 254.0), 0, {}, {'in_bom': False}),
    'H3': ('Mechanical:MountingHole', 'M3', 'MountingHole:MountingHole_3.2mm_M3', '', (304.8, 254.0), 0, {}, {'in_bom': False}),
    'H4': ('Mechanical:MountingHole', 'M3', 'MountingHole:MountingHole_3.2mm_M3', '', (317.5, 254.0), 0, {}, {'in_bom': False}),
    '#FLG01': ('power:PWR_FLAG', 'PWR_FLAG', '', '', (342.9, 233.68), 0, {'1': 'VBAT'}, {}),
    '#FLG02': ('power:PWR_FLAG', 'PWR_FLAG', '', '', (355.6, 233.68), 0, {'1': 'GND'}, {}),
    '#FLG03': ('power:PWR_FLAG', 'PWR_FLAG', '', '', (368.3, 233.68), 0, {'1': '+3V3'}, {}),
    '#FLG04': ('power:PWR_FLAG', 'PWR_FLAG', '', '', (381.0, 233.68), 0, {'1': 'VM_A'}, {}),   # fed through the shunts
    '#FLG05': ('power:PWR_FLAG', 'PWR_FLAG', '', '', (393.7, 233.68), 0, {'1': 'VM_B'}, {}),
    '#FLG06': ('power:PWR_FLAG', 'PWR_FLAG', '', '', (406.4, 233.68), 0, {'1': 'VLED'}, {}),   # fed through D4
}


def door(s, dy, n, ina_a1, jref, uina, udrv):
    """One door: shunt + INA219, DRV8871, terminal, door-contact input. n = ref decade."""
    y = lambda v: v + dy
    return {
        jref: ('Connector:Screw_Terminal_01x04', f'Door {s}: M+ M- DOOR GND', TB.format(n=4), 'C2757925',
               (25.4, y(127.0)), 0, {'1': f'OUT1_{s}', '2': f'OUT2_{s}', '3': f'DOOR_{s}_IN', '4': 'GND'},
               {'mpn': 'DORABO DB125-3.5-4P-GN-S'}),
        f'R{n}1': R('0.1', (55.88, y(101.6)), 90, 'VBAT', f'VM_{s}', 'Resistor_SMD:R_1206_3216Metric'),
        uina: ('Sensor_Energy:INA219AxDCN', 'INA219AIDCNR', 'Package_TO_SOT_SMD:SOT-23-8', 'C87469',
               (91.44, y(104.14)), 0,
               {'1': 'VBAT', '2': f'VM_{s}', '3': 'GND', '4': '+3V3', '5': 'SCL', '6': 'SDA', '7': 'GND', '8': ina_a1},
               {'mpn': 'TI INA219AIDCNR'}),
        f'C{n}1': C('100n', (111.76, y(93.98)), 0, '+3V3', 'GND'),
        udrv: ('Driver_Motor:DRV8871DDA', 'DRV8871DDAR', DRV_FP, 'C75864',
               (149.86, y(114.3)), 0,
               {'1': 'GND', '2': f'IN2_{s}', '3': f'IN1_{s}', '4': f'ILIM_{s}', '5': f'VM_{s}', '6': f'OUT1_{s}',
                '7': 'GND', '8': f'OUT2_{s}', '9': 'GND'},
               {'mpn': 'TI DRV8871DDAR'}),
        f'C{n}2': C('10u 50V', (124.46, y(96.52)), 0, f'VM_{s}', 'GND', C1206, LCSC['10u50']),
        f'C{n}3': C('100n', (137.16, y(96.52)), 0, f'VM_{s}', 'GND'),
        f'R{n}2': R('56k', (172.72, y(124.46)), 0, f'ILIM_{s}', 'GND'),   # 64 kV / 56k = 1.14 A limit
        f'R{n}3': R('4.7k', (119.38, y(124.46)), 0, f'IN1_{s}', 'GND'),
        f'R{n}4': R('4.7k', (129.54, y(124.46)), 0, f'IN2_{s}', 'GND'),
        f'R{n}5': R('1k', (55.88, y(132.08)), 90, f'DOOR_{s}_IN', f'DOOR_{s}'),
        f'R{n}6': R('10k', (76.2, y(127.0)), 0, '+3V3', f'DOOR_{s}'),
        f'C{n}4': C('100n', (88.9, y(137.16)), 0, f'DOOR_{s}', 'GND'),
    }


PARTS.update(door('A', 0, 1, 'GND', 'J2', 'U1', 'U2'))       # INA219 0x40 (A1 = A0 = GND)
PARTS.update(door('B', 71.12, 2, '+3V3', 'J3', 'U3', 'U4'))  # INA219 0x44 (A1 = VS, A0 = GND)

from notes import NOTES  # noqa: E402

# pin pairs joined by a drawn wire instead of two labels
DIRECT = []
