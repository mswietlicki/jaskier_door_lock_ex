"""One LCSC parts order for hand-assembling door-lock-c boards and CAN-B nodes.

Run with any Python 3 from the project directory:
    python tools/lcsc_order.py [--door 2] [--canb 2] [--canb-bom PATH] [--out jlcpcb/lcsc-order.csv]

Reads jlcpcb/bom.csv (this board) and the CAN-B node's bom.csv (jaskier repo,
hardware/canb-node/jlcpcb/bom.csv), multiplies by the number of boards, merges equal LCSC
numbers and adds spares: +20 % (at least 2) for chip passives, +1 for everything else. LCSC's
cart rounds each line up to its minimum order quantity. Parts JLCPCB would not have placed (the
termination jumper's cap) are added from EXTRA.
"""
import argparse, csv, math, os

EXTRA = {   # lcsc: (comment, package, per door-lock board)
    'C100114': ('Jumper cap 2.54 mm, closed (JP1, TERM 120R)', 'P=2.54mm', 1),
}
PASSIVE = ('R_0603', 'C_0603', 'C_0805', 'C_1206', 'R_1206', 'LED_0603')


def read(path):
    rows = {}
    with open(path, encoding='utf-8') as f:
        for r in csv.DictReader(f):
            lcsc = r['LCSC Part #'].strip()
            if not lcsc:
                continue
            n = len([d for d in r['Designator'].split(',') if d.strip()])
            c, p, k = rows.get(lcsc, (r['Comment'], r['Footprint'], 0))
            rows[lcsc] = (c, p, k + n)
    return rows


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser()
    ap.add_argument('--door', type=int, default=2, help='door-lock-c boards to build')
    ap.add_argument('--canb', type=int, default=2, help='CAN-B nodes to build')
    ap.add_argument('--canb-bom', default=os.path.join('C:\\', 'Code', 'jaskier', 'hardware', 'canb-node', 'jlcpcb', 'bom.csv'))
    ap.add_argument('--out', default=os.path.join(here, '..', 'jlcpcb', 'lcsc-order.csv'))
    a = ap.parse_args()

    door = read(os.path.join(here, '..', 'jlcpcb', 'bom.csv'))
    for k, (c, p, n) in EXTRA.items():
        door[k] = (c, p, n)
    canb = read(a.canb_bom) if a.canb else {}

    lines = []
    for lcsc in sorted(set(door) | set(canb), key=lambda k: (door.get(k) or canb.get(k))[1]):
        c, p, nd = door.get(lcsc, (None, None, 0))
        c2, p2, nc = canb.get(lcsc, (None, None, 0))
        need = nd * a.door + nc * a.canb
        if need == 0:
            continue
        spare = max(2, math.ceil(need * 0.2)) if (p or p2).startswith(PASSIVE) else 1
        lines.append((lcsc, need + spare, c or c2, p or p2, nd, nc, need))

    with open(a.out, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['LCSC Part Number', 'Quantity', 'Comment', 'Footprint',
                    'Per door-lock-c', 'Per CAN-B', f'Needed ({a.door} door-lock-c + {a.canb} CAN-B)'])
        w.writerows(lines)
    print(f'{len(lines)} lines written to {os.path.normpath(a.out)}')


if __name__ == '__main__':
    main()
