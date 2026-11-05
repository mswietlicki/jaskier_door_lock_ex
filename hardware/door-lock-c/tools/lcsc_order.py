"""One LCSC parts order for hand-assembling door-lock-c boards, CAN-B nodes and RS485 tees.

Run with any Python 3 from the project directory:
    python tools/lcsc_order.py [--door 3] [--canb 2] [--tee 10] [--out jlcpcb/lcsc-order.csv]

Reads the three boards' bom.csv files (this one, the jaskier repo's hardware/canb-node and
hardware/rs485-tee), multiplies by the number of boards, merges equal LCSC numbers and adds
spares: +20 % (at least 2) for chip passives, +1 for everything else. LCSC's cart rounds each
line up to its minimum order quantity. Parts that are not on a board's BOM (jumper caps) come
from EXTRA.
"""
import argparse, csv, math, os

JASKIER = os.path.join('C:\\', 'Code', 'jaskier', 'hardware')
CAP = ('C100114', 'Jumper cap 2.54 mm, closed (TERM 120R)', 'P=2.54mm')
# BOM part -> part to buy instead, when LCSC runs out (same value, package and rating)
SUBSTITUTE = {
    'C57112': ('C1589', '10n 50V X7R (Samsung CL10B103KB8NNNC, for C57112: 0 at LCSC on 5 Nov 2026)'),
    'C14663': ('C1591', '100n 50V X7R (Samsung CL10B104KB8NNNC, for C14663: 50 at LCSC on 5 Nov 2026)'),
}
PASSIVE = ('R_0603', 'C_0603', 'C_0805', 'C_1206', 'R_1206', 'LED_0603')


def read(path, extra=()):
    rows = {}
    with open(path, encoding='utf-8') as f:
        for r in csv.DictReader(f):
            lcsc = r['LCSC Part #'].strip()
            if not lcsc:
                continue
            n = len([d for d in r['Designator'].split(',') if d.strip()])
            comment = r['Comment']
            if lcsc in SUBSTITUTE:
                lcsc, comment = SUBSTITUTE[lcsc]
            c, p, k = rows.get(lcsc, (comment, r['Footprint'], 0))
            rows[lcsc] = (c, p, k + n)
    for lcsc, c, p, n in extra:
        rows[lcsc] = (c, p, n)
    return rows


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser()
    ap.add_argument('--door', type=int, default=3, help='door-lock-c boards to build')
    ap.add_argument('--canb', type=int, default=2, help='CAN-B nodes to build')
    ap.add_argument('--tee', type=int, default=10, help='RS485 tees to build')
    ap.add_argument('--canb-bom', default=os.path.join(JASKIER, 'canb-node', 'jlcpcb', 'bom.csv'))
    ap.add_argument('--tee-bom', default=os.path.join(JASKIER, 'rs485-tee', 'jlcpcb', 'bom.csv'))
    ap.add_argument('--out', default=os.path.join(here, '..', 'jlcpcb', 'lcsc-order.csv'))
    a = ap.parse_args()

    boards = [  # (column name, BOM per board, number of boards)
        ('door-lock-c', read(os.path.join(here, '..', 'jlcpcb', 'bom.csv'), [CAP + (1,)]), a.door),
        ('CAN-B', read(a.canb_bom) if a.canb else {}, a.canb),
        ('RS485 tee', read(a.tee_bom, [CAP + (1,)]) if a.tee else {}, a.tee),
    ]
    codes = set().union(*(b for _, b, _ in boards))
    info = {k: next(b[k] for _, b, _ in boards if k in b) for k in codes}
    lines = []
    for lcsc in sorted(codes, key=lambda k: (info[k][1], info[k][0])):
        per = [b.get(lcsc, (None, None, 0))[2] for _, b, _ in boards]
        need = sum(n * cnt for n, (_, _, cnt) in zip(per, boards))
        if need == 0:
            continue
        spare = max(2, math.ceil(need * 0.2)) if info[lcsc][1].startswith(PASSIVE) else 1
        lines.append([lcsc, need + spare, info[lcsc][0], info[lcsc][1]] + per + [need])

    label = ' + '.join(f'{cnt} {name}' for name, _, cnt in boards if cnt)
    with open(a.out, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['LCSC Part Number', 'Quantity', 'Comment', 'Footprint']
                   + [f'Per {name}' for name, _, _ in boards] + [f'Needed ({label})'])
        w.writerows(lines)
    print(f'{len(lines)} lines for {label} written to {os.path.normpath(a.out)}')


if __name__ == '__main__':
    main()
