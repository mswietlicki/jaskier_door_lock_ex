"""Schematic text notes (kept apart from parts.py; lines joined with real newlines)."""
NL = '\n'

NOTES = [
    ((20.32, 20.32), NL.join([
        'jaskier_door_lock variant C: two 12 V linear-actuator door locks on a socketed ESP32-C3 SuperMini,',
        'with an optional RS485 (Modbus RTU) port. Docs: hardware/door-lock-c/README.md'])),
    ((20.32, 264.16), NL.join([
        'Supply: 4S LiFePO4 house bank, 10-14.6 V. F1 1.1 A PTC, Q1 P-MOSFET reverse-polarity switch',
        '(R1/R2 hold Vgs at -Vin/2, inside the AO3401A\'s 12 V limit), D1 16 V TVS: the INA219 bus input is 26 V max.',
        'PS1 5 V module (SIP-3, 7805 pinout). D2 feeds the SuperMini\'s 5V pin, so its USB-C and the 12 V supply',
        'never push into each other. The SuperMini makes the 3.3 V.'])),
    ((20.32, 281.94), NL.join([
        'Each door: VBAT -> 0.1 R shunt -> DRV8871 VM. The INA219 reads motor current and the bank voltage.',
        'Door A INA219 0x40 (A1 = A0 = GND), door B 0x44 (A1 = VS). Full on/off drive only, never PWM.',
        'R_ILIM 56k: DRV8871 current limit 64 kV / 56k = 1.14 A, above the 0.55 A stall measured in the van.',
        '4.7k pull-downs keep both bridge inputs low (coast) while the ESP32 resets or is unplugged.'])),
    ((20.32, 246.38), NL.join([
        'Door contact input: reed or micro switch to GND (closed = door shut). 1k + 100n filter, 10k pull-up.',
        'Unconnected input reads high (open door). Swap M+/M- at the terminal if the bolt moves the wrong way.'])),
    ((233.68, 22.86), NL.join([
        'ESP32-C3 SuperMini socket (antenna at the board edge):',
        'IO4/IO3 door A IN1/IN2, IO5/IO6 door B IN1/IN2, IO1 door A contact, IO0 door B contact,',
        'IO8/IO9 I2C SDA/SCL (pulled up: both strapping pins stay high at boot),',
        'IO2 status LED (strapping pin, 10k pull-up), IO10 RS485 DE/RE (10k pull-down),',
        'IO20 RS485 RO (UART0 RX), IO21 RS485 DI (UART0 TX), IO7 spare on J7.'])),
    ((233.68, 132.08), NL.join([
        'RS485, optional: Modbus RTU slave for control without Wi-Fi.',
        'DE/RE low at boot (R32), so the ROM boot log on IO21 never reaches the bus.',
        'JP1 120 ohm termination: fit a jumper cap on the last device of the bus. J4 has two A/B/GND sets for a pass-through.',
        'JP2/JP3 680 ohm fail-safe bias (bridge only if nothing else on the bus biases it).',
        'D3 SM712 clamps A and B (-7 V / +12 V).'])),
]
