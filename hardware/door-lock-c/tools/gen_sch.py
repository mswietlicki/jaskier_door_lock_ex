"""Generate the door-lock-c KiCad schematic and project file.

Run with any Python 3:  python gen_sch.py <project dir>
Every pin gets a short wire stub and a net label, so the drawing is the netlist in parts.py.
Adapted from the CAN-B node generator (jaskier repo, hardware/canb-node/tools).
"""
import os, sys, uuid, json, math, datetime
sys.path.insert(0, os.path.dirname(__file__))
import sexp
from sexp import q, fmt, find, find_all
from parts import PROJECT, PARTS, NOTES, DIRECT

OUT = sys.argv[1]
KLIB = os.environ['LOCALAPPDATA'] + '/Programs/KiCad/10.0/share/kicad/symbols/'
NS = uuid.UUID('6f1c2b8e-0000-4000-8000-00000000d0c0')


def uid(*key):
    return str(uuid.uuid5(NS, '/'.join(key)))


ROOT = uid('root')


def font(hide=False, justify=None):
    e = '(effects (font (size 1.27 1.27))' + (f' (justify {justify})' if justify else '') + ')'
    return e + (' (hide yes)' if hide else '')


def prop(name, value, x, y, hide=False, justify=None, rot=0):
    return f'(property {q(name)} {q(value)} (at {fmt(x)} {fmt(y)} {rot}) {font(hide, justify)})'


# ---------------------------------------------------------------- library symbols
_libcache = {}


def lib_symbol(lib_id):
    lib, name = lib_id.split(':')
    if lib not in _libcache:
        _libcache[lib] = sexp.load_lib(KLIB + lib + '.kicad_sym')
    return sexp.flatten(_libcache[lib], name)


def embed(lib_id):
    tree = list(lib_symbol(lib_id))
    tree[1] = lib_id
    return sexp.dump(tree, 2)


# ---------------------------------------------------------------- geometry
def rot(x, y, r):
    a = math.radians(r)
    return (round(x * math.cos(a) - y * math.sin(a), 4), round(x * math.sin(a) + y * math.cos(a), 4))


def to_sch(sx, sy, px, py, r):
    rx, ry = rot(px, py, r)
    return round(sx + rx, 4), round(sy - ry, 4)


def outward(angle, r):
    """Unit vector (schematic coords) pointing away from the body at a pin."""
    a = math.radians(angle + 180 + r)
    return round(math.cos(a)), -round(math.sin(a))


DIRECT_PINS = {p for pair in DIRECT for p in pair}
IC_LIBS = ('Sensor_Energy:', 'Driver_Motor:', 'Interface_UART:', 'LED:WS2812', 'Transistor_FET:')


def pin_xy(ref, num):
    lib_id, _, _, _, (x, y), r, _, _ = PARTS[ref]
    for n, _, px, py, *_ in sexp.pins(lib_symbol(lib_id)):
        if n == num:
            return to_sch(x, y, px, py, r)
    raise KeyError((ref, num))


def fields(ref, lib_id, value, x, y, r, spins):
    hidden = ref.startswith('#')
    fa = 90 if r in (90, 270) else 0   # field angles are relative to the symbol's rotation
    vertical = bool(spins) and all(round(rot(p[2], p[3], r)[0], 2) == 0 for p in spins)
    if lib_id.startswith(IC_LIBS):
        pts = [to_sch(x, y, p[2], p[3], r) for p in spins]
        top = min(p[1] for p in pts)
        bot = max(p[1] for p in pts)
        return [prop('Reference', ref, x + 3.81, top - 3.81, justify='left'),
                prop('Value', value, x + 3.81, bot + 3.81, justify='left')]
    if lib_id.startswith(('Connector_Generic:Conn_01x', 'Connector:Screw_Terminal')):
        top = max(p[3] for p in spins); bot = min(p[3] for p in spins)
        return [prop('Reference', ref, x - 1.27, y - top - 2.54, justify='left'),
                prop('Value', value, x - 6.35, y - bot + 3.81, justify='left')]
    if lib_id.startswith('Converter_DCDC'):
        return [prop('Reference', ref, x, y - 5.08), prop('Value', value, x + 3.81, y + 5.08, justify='left')]
    if lib_id.startswith('Jumper:'):
        return [prop('Reference', ref, x, y - 3.81), prop('Value', value, x, y + 3.81)]
    if vertical or not spins:
        return [prop('Reference', ref, x + 2.54, y - 1.27, justify='left', hide=hidden, rot=fa),
                prop('Value', value, x + 2.54, y + 1.27, justify='left', hide=hidden, rot=fa)]
    return [prop('Reference', ref, x, y - 3.81, hide=hidden, rot=fa),
            prop('Value', value, x, y + 3.81, hide=hidden, rot=fa)]


def build():
    os.makedirs(OUT, exist_ok=True)
    items, libs, seen = [], [], set()
    for ref, (lib_id, value, fp, lcsc, (x, y), r, pinmap, extra) in PARTS.items():
        if lib_id not in seen:
            seen.add(lib_id)
            libs.append(embed(lib_id))
        sym = lib_symbol(lib_id)
        spins = sexp.pins(sym)
        su = uid('sym', ref)
        in_bom = 'no' if (ref.startswith('#') or extra.get('in_bom') is False) else 'yes'
        on_board = 'no' if ref.startswith('#') else 'yes'
        props = fields(ref, lib_id, value, x, y, r, spins)
        props.append(prop('Footprint', fp, x, y, hide=True))
        sprops = {p[1]: p[2] for p in find_all(sym, 'property')}
        props.append(prop('Datasheet', sprops.get('Datasheet', ''), x, y, hide=True))
        props.append(prop('Description', sprops.get('Description', ''), x, y, hide=True))
        if not ref.startswith('#'):
            props.append(prop('LCSC', lcsc, x, y, hide=True))
            if extra.get('mpn'):
                props.append(prop('MPN', extra['mpn'], x, y, hide=True))
        pin_uuids = '\n'.join(f'(pin {q(p[0])} (uuid {q(uid("pin", ref, p[0], str(i)))}))' for i, p in enumerate(spins))
        items.append(f'''(symbol (lib_id {q(lib_id)}) (at {fmt(x)} {fmt(y)} {r}) (unit 1) (exclude_from_sim no) (in_bom {in_bom}) (on_board {on_board}) (dnp no)
(uuid {q(su)})
{chr(10).join(props)}
{pin_uuids}
(instances (project {q(PROJECT)} (path {q('/' + ROOT)} (reference {q(ref)}) (unit 1))))
)''')
        # wire stubs and labels at every pin (stacked pins with the same number share one)
        done = set()
        for num, name, px, py, pa, plen, ptype in spins:
            ex, ey = to_sch(x, y, px, py, r)
            if (ref, num) in DIRECT_PINS or (ex, ey) in done:
                continue
            done.add((ex, ey))
            net = pinmap.get(num)
            if net is None:
                items.append(f'(no_connect (at {fmt(ex)} {fmt(ey)}) (uuid {q(uid("nc", ref, num, str(ex), str(ey)))}))')
                continue
            dx, dy = outward(pa, r)
            lx, ly = round(ex + dx * 2.54, 4), round(ey + dy * 2.54, 4)
            items.append(f'(wire (pts (xy {fmt(ex)} {fmt(ey)}) (xy {fmt(lx)} {fmt(ly)})) (stroke (width 0) (type default)) (uuid {q(uid("w", ref, num, str(ex), str(ey)))}))')
            if dx > 0:
                ang, just = 0, 'left bottom'
            elif dx < 0:
                ang, just = 180, 'right bottom'
            elif dy < 0:
                ang, just = 90, 'left bottom'
            else:
                ang, just = 270, 'right bottom'
            items.append(f'(label {q(net)} (at {fmt(lx)} {fmt(ly)} {ang}) (effects (font (size 1.27 1.27)) (justify {just})) (uuid {q(uid("l", ref, num, str(ex), str(ey)))}))')
    for a, b in DIRECT:
        (x1, y1), (x2, y2) = pin_xy(*a), pin_xy(*b)
        items.append(f'(wire (pts (xy {fmt(x1)} {fmt(y1)}) (xy {fmt(x2)} {fmt(y2)})) (stroke (width 0) (type default)) (uuid {q(uid("dw", *a, *b))}))')
    for i, ((x, y), text) in enumerate(NOTES):
        items.append(f'(text {q(text)} (exclude_from_sim no) (at {fmt(x)} {fmt(y)} 0) (effects (font (size 1.27 1.27)) (justify left bottom)) (uuid {q(uid("note", str(i)))}))')

    today = datetime.date.today().isoformat()
    sch = f'''(kicad_sch (version 20250610) (generator "eeschema") (generator_version "10.0")
(uuid {q(ROOT)})
(paper "A3")
(title_block (title "Door lock C: two doors, ESP32-C3, RS485") (date {q(today)}) (rev "0.1") (company "Jaskier") (comment 1 "DRV8871 + INA219 per door, Modbus RTU slave on RS485"))
(lib_symbols
{chr(10).join(libs)}
)
{chr(10).join(items)}
(sheet_instances (path "/" (page "1")))
(embedded_fonts no)
)
'''
    tree = sexp.parse(sch)          # round-trip to validate the syntax and pretty-print
    with open(os.path.join(OUT, f'{PROJECT}.kicad_sch'), 'w', encoding='utf-8', newline='\n') as f:
        f.write(sexp.dump(tree) + '\n')

    pro_path = os.path.join(OUT, f'{PROJECT}.kicad_pro')
    if not os.path.exists(pro_path):
        pro = {
            'meta': {'filename': f'{PROJECT}.kicad_pro', 'version': 3},
            'board': {'design_settings': {'rules': {
                'min_clearance': 0.15, 'min_track_width': 0.15, 'min_via_diameter': 0.5,
                'min_through_hole_diameter': 0.3, 'min_hole_to_hole': 0.25, 'min_copper_edge_clearance': 0.3}}},
            'net_settings': {
                'classes': [
                    {'name': 'Default', 'clearance': 0.15, 'track_width': 0.25, 'via_diameter': 0.6, 'via_drill': 0.3,
                     'diff_pair_width': 0.2, 'diff_pair_gap': 0.25, 'diff_pair_via_gap': 0.25,
                     'microvia_diameter': 0.3, 'microvia_drill': 0.1, 'wire_width': 6, 'bus_width': 12,
                     'line_style': 0, 'schematic_color': 'rgba(0, 0, 0, 0.000)', 'pcb_color': 'rgba(0, 0, 0, 0.000)',
                     'priority': 2147483647},
                ],
                'meta': {'version': 4},
            },
            'sheets': [[ROOT, 'Root']],
            'text_variables': {},
        }
        with open(pro_path, 'w', encoding='utf-8', newline='\n') as f:
            json.dump(pro, f, indent=2)


if __name__ == '__main__':
    build()
    print('written', OUT)
