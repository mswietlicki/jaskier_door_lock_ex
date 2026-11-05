"""Build door-lock-c.kicad_pcb from the schematic netlist with KiCad's pcbnew API and route it.

Run with KiCad's own python:  python.exe gen_pcb.py <netlist> <out.kicad_pcb> [--pads]
Coordinates are mm from the board's top-left corner (x right, y down). Placement and the
routing jobs are in layout.py; router.py does the routing.
"""
import os, sys, math, time
sys.path.insert(0, os.path.dirname(__file__))
import pcbnew
import sexp
from sexp import find, find_all
from layout import PLACE, JOBS, BOARD_W, BOARD_H, KEEPOUT, SILK, REF, LINES, SHOW
from router import Router, F, B

NETLIST, OUT = sys.argv[1], sys.argv[2]
FPLIB = os.environ['LOCALAPPDATA'] + '/Programs/KiCad/10.0/share/kicad/footprints/'
OX, OY = 100.0, 100.0          # board origin on the KiCad canvas
SCH = 'door-lock-c.kicad_sch'


def mm(v):
    return pcbnew.FromMM(v)


def V(x, y):
    return pcbnew.VECTOR2I(mm(OX + x), mm(OY + y))


def read_netlist(path):
    tree = sexp.parse(open(path, encoding='utf-8').read())
    comps = {}
    for c in find_all(find(tree, 'components'), 'comp'):
        ref = find(c, 'ref')[1]
        comps[ref] = {
            'value': find(c, 'value')[1],
            'footprint': find(c, 'footprint')[1] if find(c, 'footprint') else '',
            'tstamp': find(c, 'tstamps')[1],
            'fields': {f[1][1]: (f[2] if len(f) > 2 else '') for f in find_all(find(c, 'fields'), 'field')} if find(c, 'fields') else {},
        }
    nets = {}
    for n in find_all(find(tree, 'nets'), 'net'):
        name = find(n, 'name')[1]
        for node in find_all(n, 'node'):
            nets[(find(node, 'ref')[1], find(node, 'pin')[1])] = name
    return comps, nets


def plain(name):
    return name[1:] if name.startswith('/') else name


def main():
    t0 = time.time()
    comps, pinnet = read_netlist(NETLIST)
    board = pcbnew.BOARD()
    board.SetCopperLayerCount(2)
    ds = board.GetDesignSettings()
    netinfo = {}
    for name in sorted(set(pinnet.values())):
        ni = pcbnew.NETINFO_ITEM(board, name)
        board.Add(ni)
        netinfo[plain(name)] = ni

    fps = {}
    for ref, c in comps.items():
        if not c['footprint']:
            continue
        lib, name = c['footprint'].split(':')
        fp = pcbnew.FootprintLoad(FPLIB + lib + '.pretty', name)
        fp.SetReference(ref)
        fp.SetValue(c['value'])
        fp.SetFPID(pcbnew.LIB_ID(lib, name))
        fp.SetPath(pcbnew.KIID_PATH('/' + c['tstamp']))
        try:
            fp.SetSheetname('/'); fp.SetSheetfile(SCH)
        except Exception:
            pass
        x, y, rot = PLACE[ref]
        fp.SetPosition(V(x, y))
        fp.SetOrientationDegrees(rot)
        for pad in fp.Pads():
            n = pinnet.get((ref, pad.GetNumber()))
            if n:
                pad.SetNet(netinfo[plain(n)])
        rt = fp.Reference()
        rt.SetTextSize(pcbnew.VECTOR2I(mm(0.8), mm(0.8)))
        rt.SetTextThickness(mm(0.12))
        fp.Value().SetVisible(False)
        if ref not in SHOW:
            rt.SetVisible(False)        # the footprint's own ${REFERENCE} on F.Fab names it on the assembly drawing
        elif ref in REF:
            if REF[ref] is None:
                rt.SetLayer(pcbnew.F_Fab)
            else:
                rt.SetPosition(V(*REF[ref][:2]))
                rt.SetTextAngleDegrees(REF[ref][2] if len(REF[ref]) > 2 else 0)
        for fname, fval in c['fields'].items():
            if fname in ('Footprint',) or not isinstance(fval, str):
                continue
            fp.SetField(fname, fval)
            f = fp.GetField(fname)
            if f is not None:
                f.SetVisible(False)
                f.SetLayer(pcbnew.F_Fab)
        board.Add(fp)
        fps[ref] = fp

    # --- outline
    pts = [(0, 0), (BOARD_W, 0), (BOARD_W, BOARD_H), (0, BOARD_H)]
    for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]):
        s = pcbnew.PCB_SHAPE(board)
        s.SetShape(pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(V(x1, y1)); s.SetEnd(V(x2, y2))
        s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(mm(0.1))
        board.Add(s)

    # --- router copper model from the placed pads
    R = Router(BOARD_W, BOARD_H)
    padshapes = {}

    def to_mm(v):
        return pcbnew.ToMM(v)

    for ref, fp in fps.items():
        for pad in fp.Pads():
            bb = pad.GetBoundingBox()
            cx = to_mm(bb.GetCenter().x) - OX; cy = to_mm(bb.GetCenter().y) - OY
            sx = to_mm(bb.GetWidth()); sy = to_mm(bb.GetHeight())
            layers = [L for L, kl in ((F, pcbnew.F_Cu), (B, pcbnew.B_Cu)) if pad.IsOnLayer(kl)]
            net = plain(pad.GetNetname()) or f'__nc_{ref}_{pad.GetNumber()}'
            drill = to_mm(pad.GetDrillSizeX())
            if not layers:
                if drill > 0:      # NPTH hole: keep copper away
                    R.shapes.append(('__hole__', (F, B), 'disc', (cx, cy, drill / 2 + 0.2)))
                    R.drills.append((cx, cy, drill / 2))
                continue
            pc = pad.GetPosition(); px = to_mm(pc.x) - OX; py = to_mm(pc.y) - OY
            st = pad.GetShape(pcbnew.F_Cu) if pad.IsOnLayer(pcbnew.F_Cu) else pad.GetShape(pcbnew.B_Cu)
            if st in (pcbnew.PAD_SHAPE_CIRCLE, pcbnew.PAD_SHAPE_OVAL):
                if abs(sx - sy) < 1e-3:
                    shape = (net, tuple(layers), 'seg', (px, py, px, py, sx / 2))
                elif sx > sy:
                    d = (sx - sy) / 2
                    shape = (net, tuple(layers), 'seg', (px - d, py, px + d, py, sy / 2))
                else:
                    d = (sy - sx) / 2
                    shape = (net, tuple(layers), 'seg', (px, py - d, px, py + d, sx / 2))
            else:
                shape = (net, tuple(layers), 'rect', (cx, cy, sx / 2, sy / 2))
            R.shapes.append(shape)
            R.padlist.append(shape[1:])
            if drill > 0:
                R.drills.append((px, py, drill / 2))
            padshapes.setdefault(f'{ref}.{pad.GetNumber()}', []).append(shape)
    (kx1, ky1), (kx2, ky2) = KEEPOUT
    R.add_keepout((F, B), kx1, ky1, kx2, ky2)

    if '--pads' in sys.argv:
        for k, v in sorted(padshapes.items()):
            print(k, v[0][0], [round(a, 3) for a in v[0][3][:2]])

    # --- routing jobs
    tree = {}
    failed = []

    def run(net, width, src, dst, label, goal_layer=None):
        path = R.route(net, width, src, dst, goal_layer=goal_layer)
        if path is None:
            failed.append(label)
            print('  FAILED', label)
            return []
        n0 = len(R.shapes)
        R.commit(net, width, path)
        return R.shapes[n0:]

    viaed = set()
    for job in JOBS:
        kind, net, width = job[:3]
        if kind == 'via':
            run(net, width, padshapes[job[3]], None, f'{net} via {job[3]}', goal_layer=B)
            viaed.add(job[3])
            continue
        if kind == 'p2p':
            a, b = job[3], job[4]
            if run(net, width, padshapes[a], padshapes[b], f'{net} {a}-{b}') and net == 'GND':
                viaed.add(a)                 # joined to a pad that gets its own via
            continue
        pads = job[3]
        cur = tree.setdefault(net, [])
        todo = list(pads)
        if not cur:
            cur.extend(padshapes[todo.pop(0)])
        while todo:
            # nearest remaining pad to the tree first
            def dist(p):
                px, py = padshapes[p][0][3][:2]
                return min(math.hypot(px - s[3][0], py - s[3][1]) for s in cur)
            todo.sort(key=dist)
            p = todo.pop(0)
            new = run(net, width, cur, padshapes[p], f'{net} -> {p}')
            if new:
                cur.extend(new)
                cur.extend(padshapes[p])
        print(f'{net:10s} done  ({time.time() - t0:.0f} s)')

    # --- a via next to every SMD ground pad (the pours do the rest)
    gnd_smd = [k for k, v in padshapes.items() if v[0][0] == 'GND' and v[0][1] == (F,)
               and not (k.startswith(('U2.', 'U4.')) and k.endswith('.9'))]
    for k in sorted(gnd_smd):
        if k not in viaed:
            run('GND', 0.3, padshapes[k], None, f'GND via {k}', goal_layer=B)
    print(f'GND vias done ({time.time() - t0:.0f} s)')

    # --- stitching vias on a grid wherever they fit
    R.clr += 0.15                      # stitching vias sit well inside the pours
    vok = R.via_ok('GND')
    R.clr -= 0.15
    g = R.g
    for yy in [y * 3.0 + 1.5 for y in range(int(BOARD_H / 3.0))]:
        for xx in [x * 3.0 + 1.5 for x in range(int(BOARD_W / 3.0))]:
            i, j = int(xx / g), int(yy / g)
            if vok[j, i]:
                R.add_via('GND', round((i + 0.5) * g, 4), round((j + 0.5) * g, 4))
                r = int(1.5 / g)
                vok[max(0, j - r):j + r, max(0, i - r):i + r] = False

    # --- copper into the board
    layers = {F: pcbnew.F_Cu, B: pcbnew.B_Cu}
    for net, L, w, x1, y1, x2, y2 in R.tracks:
        t = pcbnew.PCB_TRACK(board)
        t.SetStart(V(x1, y1)); t.SetEnd(V(x2, y2))
        t.SetWidth(mm(w)); t.SetLayer(layers[L]); t.SetNet(netinfo[net])
        board.Add(t)
    for net, x, y in R.vias:
        v = pcbnew.PCB_VIA(board)
        v.SetPosition(V(x, y))
        v.SetViaType(pcbnew.VIATYPE_THROUGH)
        v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
        v.SetDrill(mm(0.3))
        try:
            v.SetWidth(mm(R.via_d))
        except TypeError:
            v.SetWidth(pcbnew.F_Cu, mm(R.via_d))
        v.SetNet(netinfo[net])
        board.Add(v)

    # --- GND pours on both layers
    for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
        z = pcbnew.ZONE(board)
        z.SetLayer(layer)
        z.SetNet(netinfo['GND'])
        o = z.Outline(); o.NewOutline()
        for x, y in [(0.3, 0.3), (BOARD_W - 0.3, 0.3), (BOARD_W - 0.3, BOARD_H - 0.3), (0.3, BOARD_H - 0.3)]:
            o.Append(mm(OX + x), mm(OY + y))
        z.SetLocalClearance(mm(0.3))
        z.SetMinThickness(mm(0.25))
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_THT_THERMAL)   # SMD pads solid, THT pads thermal
        z.SetThermalReliefGap(mm(0.3))
        z.SetThermalReliefSpokeWidth(mm(0.4))
        z.SetAssignedPriority(0)
        board.Add(z)
    k = pcbnew.ZONE(board)
    k.SetIsRuleArea(True)
    ls = pcbnew.LSET(); ls.AddLayer(pcbnew.F_Cu); ls.AddLayer(pcbnew.B_Cu)
    k.SetLayerSet(ls)
    k.SetDoNotAllowTracks(True); k.SetDoNotAllowVias(True)
    for m in ('SetDoNotAllowZoneFills', 'SetDoNotAllowCopperPour'):
        if hasattr(k, m):
            getattr(k, m)(True)
    k.SetDoNotAllowPads(False); k.SetDoNotAllowFootprints(False)
    o = k.Outline(); o.NewOutline()
    for x, y in [(kx1, ky1), (kx2, ky1), (kx2, ky2), (kx1, ky2)]:
        o.Append(mm(OX + x), mm(OY + y))
    k.SetZoneName('antenna keep-out')
    board.Add(k)

    # --- silkscreen
    for text, (x, y), size, rot in SILK:
        t = pcbnew.PCB_TEXT(board)
        t.SetText(text)
        t.SetPosition(V(x, y))
        t.SetLayer(pcbnew.F_SilkS)
        t.SetTextSize(pcbnew.VECTOR2I(mm(size), mm(size)))
        t.SetTextThickness(mm(max(0.1, size * 0.15)))
        t.SetTextAngleDegrees(rot)
        board.Add(t)
    for (x1, y1), (x2, y2) in LINES:
        s = pcbnew.PCB_SHAPE(board)
        s.SetShape(pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(V(x1, y1)); s.SetEnd(V(x2, y2))
        s.SetLayer(pcbnew.F_SilkS); s.SetWidth(mm(0.15))
        board.Add(s)

    if '--preview' in sys.argv:
        pcbnew.SaveBoard(OUT.replace('.kicad_pcb', '-nofill.kicad_pcb'), board)
    filler = pcbnew.ZONE_FILLER(board)
    filler.Fill(board.Zones())
    pcbnew.SaveBoard(OUT, board)
    print('saved', OUT, f'({time.time() - t0:.0f} s)', 'failed:', failed)


if __name__ == '__main__':
    main()
