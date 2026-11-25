"""Door lock C: settings for the soldering guide (docs/soldering-guide.md).

The engine lives in the jaskier repo (C:\\Code\\jaskier). Build from this repo's root:
    python ../jaskier/tools/soldering_guide.py hardware/door-lock-c

The standard is hardware/SOLDERING.md in the jaskier repo.
"""

VALUE = {
    'U1': 'INA219', 'U3': 'INA219', 'U2': 'DRV8871', 'U4': 'DRV8871', 'U5': 'SP3485',
    'R11': '0.1Ω', 'R21': '0.1Ω', 'LED2': 'WS2812B',
    'J1': 'terminal 2-pin', 'J2': 'terminal 4-pin', 'J3': 'terminal 4-pin', 'J4': 'terminal 6-pin',
    'J5': 'socket 1×8', 'J6': 'socket 1×8', 'J7': 'header 1×6', 'JP1': 'header 1×2',
    'JP2': 'leave OPEN', 'JP3': 'leave OPEN',
}

# LED2's mark on the real part is its cut corner at pin 3 (GND), not a pin-1 dot
NO_MARK = ('LED2',)


def details(g, b):
    """The cut corner of LED2, where the part's own cut corner goes."""
    x0, y0, x1, y1 = g.body_box(b['fps']['LED2'])
    return (f'<path d="M{x1:.2f},{y1 - 1.3:.2f} L{x1:.2f},{y1:.2f} L{x1 - 1.3:.2f},{y1:.2f} Z" fill="#111827"/>'
            f'<text x="{x1 - 0.5:.2f}" y="{y1 + 1.1:.2f}" text-anchor="end" font-size="0.72" fill="#1f2937" '
            f'class="lbl">cut corner</text>')


# The A3 sheet in four parts, so each prints large enough to read (sheet millimetres)
SCHEMATIC_VIEWS = [
    ('Supply: fuse, reverse-polarity switch, surge clamp, 5 V module', (3, 27, 212, 70)),
    ('Door A (top) and door B (bottom): current sensor and motor driver', (3, 80, 186, 222)),
    ('SuperMini socket, extension header and status LED', (232, 30, 356, 110)),
    ('RS485 port', (232, 118, 419, 222)),
]
