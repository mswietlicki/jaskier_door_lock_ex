"""Write the order files: gerbers + drills (zip), bom.csv, the assembly drawing, and with
--cpl a JLCPCB placement file (only needed if JLCPCB assembles the board).

Run with KiCad's own python from the project directory:  python.exe tools/jlcpcb.py [--cpl]
Placement corrections, as learned on the CAN-B node's JLCPCB preview (jaskier repo,
hardware/canb-node/README.md): through-hole parts at the centre of their pins (KiCad exports
pin 1), and JLCPCB's SOIC/SOT footprints are KiCad's turned by 90 degrees (pin 1 bottom-left at
0 degrees), so their rotation is KiCad's minus 90. Passives and two-pin diodes go as exported.
Check every part in JLCPCB's placement preview anyway.
"""
import os, sys, csv, subprocess, zipfile, glob
import pcbnew

PROJECT = 'door-lock-c'
KC = os.path.join(os.environ['LOCALAPPDATA'], 'Programs', 'KiCad', '10.0', 'bin', 'kicad-cli.exe')
OX, OY = 100.0, 100.0
OUT = 'jlcpcb'
ROT_MINUS_90 = ('Package_SO:', 'Package_TO_SOT_SMD:', 'Connector_PinSocket', 'Connector_PinHeader')

os.makedirs(OUT, exist_ok=True)
board = pcbnew.LoadBoard(f'{PROJECT}.kicad_pcb')

# ---------------------------------------------------------------- gerbers and drills
gdir = os.path.join(OUT, 'gerbers')
os.makedirs(gdir, exist_ok=True)
for f in glob.glob(os.path.join(gdir, '*')):
    os.remove(f)
subprocess.run([KC, 'pcb', 'export', 'gerbers', '--layers',
                'F.Cu,B.Cu,F.Paste,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,Edge.Cuts',
                '--no-x2', '--subtract-soldermask', '-o', gdir + os.sep, f'{PROJECT}.kicad_pcb'], check=True)
subprocess.run([KC, 'pcb', 'export', 'drill', '--format', 'excellon', '--excellon-units', 'mm',
                '--excellon-separate-th', '-o', gdir + os.sep, f'{PROJECT}.kicad_pcb'], check=True)
with zipfile.ZipFile(os.path.join(OUT, f'{PROJECT}-gerbers.zip'), 'w', zipfile.ZIP_DEFLATED) as z:
    for f in sorted(glob.glob(os.path.join(gdir, '*'))):
        z.write(f, os.path.basename(f))

# ---------------------------------------------------------------- BOM and CPL
groups = {}
cpl = []
for fp in sorted(board.GetFootprints(), key=lambda f: f.GetReference()):
    ref = fp.GetReference()
    lcsc = fp.GetFieldText('LCSC') if fp.HasField('LCSC') else ''
    if not lcsc:                                   # solder jumpers, mounting holes
        continue
    fpname = str(fp.GetFPID().GetLibItemName())
    lib = str(fp.GetFPID().GetLibNickname())
    value = fp.GetValue()
    if ref in ('J5', 'J6'):
        value = '1x8 female 2.54 mm, 8.5 mm'      # one BOM line for both socket rows
    key = (value, fpname, lcsc)
    groups.setdefault(key, []).append(ref)
    # placement
    tht = any(p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH for p in fp.Pads())
    if tht:
        xs = [pcbnew.ToMM(p.GetPosition().x) for p in fp.Pads()]
        ys = [pcbnew.ToMM(p.GetPosition().y) for p in fp.Pads()]
        x, y = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    else:
        x, y = pcbnew.ToMM(fp.GetPosition().x), pcbnew.ToMM(fp.GetPosition().y)
    rot = fp.GetOrientationDegrees()
    if lib.startswith(ROT_MINUS_90) or (lib + ':').startswith(ROT_MINUS_90):
        rot -= 90
    rot %= 360
    cpl.append((ref, f'{x:.4f}mm', f'{-y:.4f}mm', 'Top', f'{rot:g}'))

with open(os.path.join(OUT, 'bom.csv'), 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f)
    w.writerow(['Comment', 'Designator', 'Footprint', 'LCSC Part #'])
    for (value, fpname, lcsc), refs in sorted(groups.items(), key=lambda kv: kv[1][0]):
        w.writerow([value, ','.join(refs), fpname, lcsc])
if '--cpl' in sys.argv:
    with open(os.path.join(OUT, 'cpl.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['Designator', 'Mid X', 'Mid Y', 'Layer', 'Rotation'])
        w.writerows(cpl)
elif os.path.exists(os.path.join(OUT, 'cpl.csv')):
    os.remove(os.path.join(OUT, 'cpl.csv'))

# ---------------------------------------------------------------- assembly drawing (hand assembly)
subprocess.run([KC, 'pcb', 'export', 'pdf', '--layers', 'Edge.Cuts,F.Fab', '--mode-single', '--sketch-pads-on-fab-layers',
                '--exclude-value', '--scale', '0',
                '-o', os.path.join('docs', 'assembly-top.pdf'), f'{PROJECT}.kicad_pcb'], check=True)
print('bom lines', len(groups), 'placements', len(cpl))
