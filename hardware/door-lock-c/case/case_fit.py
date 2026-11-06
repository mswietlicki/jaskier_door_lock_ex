"""Fit check of the door-lock-c case against the board's KiCad 3D model.

Exports the board (kicad-cli pcb export stl) and the case in assembled position
(OpenSCAD, part="base_fit" and "lid_fit"), then measures the clearance from every part of
the board to the case. The SuperMini in its socket and the board screw heads, which the KiCad
model does not have, are added as boxes. It also checks that a wire from each terminal entry
leaves through its window, that the lid screws miss the parts, and that base and lid do not
overlap. Exit status 1 on any interference.

Needs numpy, trimesh, rtree and manifold3d (pip install trimesh rtree manifold3d), KiCad 10's
kicad-cli and OpenSCAD.

    python case/case_fit.py
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

import numpy as np
import trimesh

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, '..', 'door-lock-c.kicad_pcb')
SCAD = os.path.join(HERE, 'door-lock-c-case.scad')
KICAD_CLI = shutil.which('kicad-cli') or os.path.expandvars(
    r'%LOCALAPPDATA%\Programs\KiCad\10.0\bin\kicad-cli.exe')
OPENSCAD = shutil.which('openscad') or r'C:\Program Files\OpenSCAD\openscad.com'

MODEL_PCB_T = 1.51      # board body thickness in KiCad's model (components sit on it)
MIN_CLEAR = 0.4         # report anything closer than this, in mm (the board edge has 0.5 by design)


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        sys.exit(f'{cmd[0]} failed:\n{r.stdout}\n{r.stderr}')
    return r.stdout + r.stderr


def box(x0, x1, y0, y1, z0, z1):
    b = trimesh.creation.box(extents=[x1 - x0, y1 - y0, z1 - z0])
    b.apply_translation([(x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2])
    return b


def cyl_x(x0, x1, y, z, r):
    c = trimesh.creation.cylinder(radius=r, height=x1 - x0, sections=24)
    c.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [0, 1, 0]))
    c.apply_translation([(x0 + x1) / 2, y, z])
    return c


def cyl_y(x, y0, y1, z, r):
    c = trimesh.creation.cylinder(radius=r, height=y1 - y0, sections=24)
    c.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0]))
    c.apply_translation([x, (y0 + y1) / 2, z])
    return c


def points(mesh, n):
    p, _ = trimesh.sample.sample_surface(mesh, n, seed=1)
    return np.vstack([p, mesh.vertices])


def clearance(case, pts):
    """Smallest distance from the points to the case; negative means inside it."""
    return float((-trimesh.proximity.signed_distance(case, pts)).min())


def main():
    tmp = tempfile.mkdtemp(prefix='case_fit_')
    board_stl = os.path.join(tmp, 'board.stl')
    run([KICAD_CLI, 'pcb', 'export', 'stl', '--subst-models', '-f', '-o', board_stl, PCB])
    fit = {}
    case = {}
    for part in ('base', 'lid'):
        out = os.path.join(tmp, f'{part}.stl')
        log = run([OPENSCAD, '-D', f'part="{part}_fit"', '-o', out, SCAD])
        fit.update({k: float(v) for k, v in re.findall(r'(\w+)=(-?[\d.]+)', log.split('FIT ', 1)[1].split('"')[0])})
        case[part] = trimesh.load(out)
    top, bot = fit['top_z'], fit['pcb_z']
    print(f"Case {fit['out_w']:.1f} x {fit['out_h']:.1f} x {fit['box_h']:.1f} mm; "
          f"board top face {top:.1f} mm from the wall, lid underside {fit['wall_top']:.1f} mm")

    board = trimesh.load(board_stl)
    board.apply_translation([-100, 164, top - MODEL_PCB_T])     # KiCad (100, 100) is the board corner
    pts = points(board, 60000)
    x, y, z = pts.T
    comp = pts[z > top + 0.05]
    pins = pts[z < bot - 0.05]
    # board edge to the walls, away from the standoffs it rests on
    away = np.min([np.hypot(x - hx, y - hy) for hx in (3.5, 76.5) for hy in (3.5, 60.5)], axis=0) > 4.0
    edge = pts[(np.minimum.reduce([x, 80 - x, y, 64 - y]) < 0.05) & (z > bot + 0.2) & (z < top - 0.05) & away]

    extra = {
        'SuperMini PCB': box(36.62, 54.62, 41.3, 63.82, top + 11.1, top + 12.1),
        'SuperMini USB-C': box(41.12, 50.12, 40.3, 47.7, top + 12.1, top + 15.3),
        'SuperMini header pins': box(36.6, 54.7, 41.8, 62.2, top + 8.6, top + 14.1),
        'Board screw heads': trimesh.util.concatenate(
            [trimesh.creation.cylinder(radius=2.8, height=3.0, sections=24).apply_translation([hx, hy, top + 1.5])
             for hx in (3.5, 76.5) for hy in (3.5, 60.5)]),
    }
    rows = [('Parts on the board', comp), ('Pins under the board', pins), ('Board edge', edge)]
    rows += [(k, points(m, 4000)) for k, m in extra.items()]

    bad = []
    print(f"\n{'Item':28s} {'to base':>9s} {'to lid':>9s}")
    for name, p in rows:
        cb, cl = clearance(case['base'], p), clearance(case['lid'], p)
        flag = '' if min(cb, cl) >= MIN_CLEAR else ('  INTERFERES' if min(cb, cl) < 0 else '  close')
        print(f'{name:28s} {cb:8.2f}  {cl:8.2f}{flag}')
        if min(cb, cl) < 0:
            bad.append(name)

    # wires: 2.0 mm insulation, from each terminal entry straight out through its window
    wz = top + 4.35
    wires = [cyl_y(px, -5.0, 1.0, wz, 1.0) for px in (9.5, 13, 16.5, 20, 30.5, 34, 37.5, 41,
                                                      53, 56.5, 60, 63.5, 67, 70.5)]
    wires += [cyl_x(-5.0, 0.9, py, wz, 1.0) for py in (50.0, 53.5)]
    cw = min(clearance(case['base'], points(w, 600)) for w in wires)
    print(f"{'Wires out of the terminals':28s} {cw:8.2f}  {'-':>8s}{'  INTERFERES' if cw < 0 else ''}")
    if cw < 0:
        bad.append('wires')

    # lid screws, M3 x 8 from the outside of each side wall
    ly, lz = fit['lid_screw_y'], fit['lid_screw_z']
    x0 = fit['out_x0']
    screws = trimesh.util.concatenate([cyl_x(x0, x0 + 8, ly, lz, 1.5), cyl_x(80 - x0 - 8, 80 - x0, ly, lz, 1.5)])
    d = trimesh.proximity.signed_distance(screws, pts[z > top + 0.05])
    print(f"{'Lid screws to the parts':28s} {float(-d.max()):8.2f}")
    if d.max() > 0:
        bad.append('lid screws')

    both = trimesh.boolean.intersection([case['base'], case['lid']], engine='manifold')
    v = float(both.volume) if not both.is_empty else 0.0
    print(f"{'Base and lid overlap':28s} {v:8.3f} mm3")
    if v > 1e-3:
        bad.append('base/lid overlap')

    print('\nOK: nothing touches.' if not bad else f'\nInterference: {", ".join(bad)}')
    shutil.rmtree(tmp, ignore_errors=True)
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
