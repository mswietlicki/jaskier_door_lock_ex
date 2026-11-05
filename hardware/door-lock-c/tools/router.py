"""Small two-layer grid router (A* with vias) for gen_pcb.py.

Copper is kept as shapes (axis-aligned pad rectangles, track capsules, via discs). For each
connection the foreign copper is rasterised onto a grid, inflated by half the new track width
plus the clearance plus a safety margin, and A* searches the free cells on F.Cu and B.Cu.
Pure Python + numpy (KiCad's bundled Python has numpy).
"""
import heapq, math
import numpy as np

F, B = 0, 1


class Router:
    def __init__(self, w, h, grid=0.1, clearance=0.15, margin=0.05, edge=0.3,
                 via_d=0.6, via_cost=2.5, b_cost=1.6, bend45=0.6, bend90=1.5):
        self.g = grid
        self.nx, self.ny = int(math.ceil(w / grid)), int(math.ceil(h / grid))
        self.w, self.h = w, h
        self.clr, self.margin, self.edge = clearance, margin, edge
        self.via_d, self.via_cost, self.b_cost = via_d, via_cost, b_cost
        self.bend45, self.bend90 = bend45, bend90
        self.shapes = []          # (net, layers, kind, data)
        self.keepout = []         # (layers, x1, y1, x2, y2)
        self.drills = []          # (x, y, radius) of every hole, any net
        self.padlist = []         # (layers, kind, data) of every pad, any net
        self.tracks, self.vias = [], []
        xs = (np.arange(self.nx) + 0.5) * grid
        ys = (np.arange(self.ny) + 0.5) * grid
        self.X, self.Y = np.meshgrid(xs, ys)          # [iy, ix]

    # ------------------------------------------------------------- copper bookkeeping
    def add_pad(self, net, layers, cx, cy, sx, sy):
        self.shapes.append((net, tuple(layers), 'rect', (cx, cy, sx / 2, sy / 2)))

    def add_track(self, net, layer, w, x1, y1, x2, y2):
        self.shapes.append((net, (layer,), 'seg', (x1, y1, x2, y2, w / 2)))
        self.tracks.append((net, layer, w, x1, y1, x2, y2))

    def add_via(self, net, x, y):
        self.shapes.append((net, (F, B), 'disc', (x, y, self.via_d / 2)))
        self.vias.append((net, x, y))
        self.drills.append((x, y, 0.15))

    def via_ok(self, net):
        """Cells where a via of this net may go."""
        vb = self.blocked(net, self.via_d / 2)
        m = vb[F] | vb[B]
        for x, y, r in self.drills:
            self._paint(m, 'disc', (x, y, r), 0.15 + 0.3)
        for layers, kind, data in self.padlist:
            self._paint(m, kind, data, self.via_d / 2 + 0.1)
        return ~m

    def add_keepout(self, layers, x1, y1, x2, y2):
        self.keepout.append((tuple(layers), x1, y1, x2, y2))

    # ------------------------------------------------------------- rasterising
    def _window(self, x1, y1, x2, y2):
        g = self.g
        i1, i2 = max(0, int((x1) / g) - 1), min(self.nx, int((x2) / g) + 2)
        j1, j2 = max(0, int((y1) / g) - 1), min(self.ny, int((y2) / g) + 2)
        return i1, i2, j1, j2

    def _paint(self, mask, kind, data, infl):
        if kind == 'rect':
            cx, cy, hx, hy = data
            i1, i2, j1, j2 = self._window(cx - hx - infl, cy - hy - infl, cx + hx + infl, cy + hy + infl)
            X, Y = self.X[j1:j2, i1:i2], self.Y[j1:j2, i1:i2]
            dx = np.maximum(np.abs(X - cx) - hx, 0)
            dy = np.maximum(np.abs(Y - cy) - hy, 0)
            mask[j1:j2, i1:i2] |= (dx * dx + dy * dy) < infl * infl
        elif kind == 'seg':
            x1, y1, x2, y2, hw = data
            r = hw + infl
            i1, i2, j1, j2 = self._window(min(x1, x2) - r, min(y1, y2) - r, max(x1, x2) + r, max(y1, y2) + r)
            X, Y = self.X[j1:j2, i1:i2], self.Y[j1:j2, i1:i2]
            vx, vy = x2 - x1, y2 - y1
            L2 = vx * vx + vy * vy
            if L2 == 0:
                t = 0
            else:
                t = np.clip(((X - x1) * vx + (Y - y1) * vy) / L2, 0, 1)
            px, py = x1 + t * vx, y1 + t * vy
            mask[j1:j2, i1:i2] |= ((X - px) ** 2 + (Y - py) ** 2) < r * r
        elif kind == 'disc':
            cx, cy, rr = data
            r = rr + infl
            i1, i2, j1, j2 = self._window(cx - r, cy - r, cx + r, cy + r)
            X, Y = self.X[j1:j2, i1:i2], self.Y[j1:j2, i1:i2]
            mask[j1:j2, i1:i2] |= ((X - cx) ** 2 + (Y - cy) ** 2) < r * r

    def blocked(self, net, half):
        """Per-layer masks of cells where a centreline of half-width `half` would violate clearance."""
        infl = half + self.clr + self.margin
        masks = [np.zeros((self.ny, self.nx), bool), np.zeros((self.ny, self.nx), bool)]
        for n, layers, kind, data in self.shapes:
            if n == net:
                continue
            for L in layers:
                self._paint(masks[L], kind, data, infl)
        e = half + self.edge
        for m in masks:
            m[self.Y < e] = True; m[self.Y > self.h - e] = True
            m[self.X < e] = True; m[self.X > self.w - e] = True
        for layers, x1, y1, x2, y2 in self.keepout:
            for L in layers:
                masks[L] |= (self.X > x1 - half) & (self.X < x2 + half) & (self.Y > y1 - half) & (self.Y < y2 + half)
        return masks

    def own_cells(self, net, shapes=None, shrink=0.12):
        """Cells well inside this net's copper, per layer (the search may start or end there)."""
        masks = [np.zeros((self.ny, self.nx), bool), np.zeros((self.ny, self.nx), bool)]
        for n, layers, kind, data in (shapes if shapes is not None else self.shapes):
            if n != net:
                continue
            if kind == 'rect':
                cx, cy, hx, hy = data
                d = (cx, cy, max(hx - shrink, 0.01), max(hy - shrink, 0.01))
            elif kind == 'seg':
                d = data[:4] + (max(data[4] - shrink, 0.0),)
            else:
                d = data[:2] + (max(data[2] - shrink, 0.0),)
            for L in layers:
                self._paint(masks[L], kind, d, 0.011)
        return masks

    # ------------------------------------------------------------- search
    def route(self, net, width, src, dst, layers=(F, B), allow_via=True, goal_layer=None):
        """src/dst: list of shapes (net, layers, kind, data). Returns list of (layer, ix, iy) or None."""
        half = width / 2
        blk = self.blocked(net, half)
        vok = self.via_ok(net)
        smask = self.own_cells(net, src)
        if goal_layer is not None:
            tmask = [np.zeros_like(blk[0]), np.zeros_like(blk[0])]
            tmask[goal_layer][:] = ~blk[goal_layer]
        else:
            tmask = self.own_cells(net, dst)
        for L in (F, B):
            if L not in layers:
                blk[L][:] = True
            smask[L] &= ~blk[L] | smask[L]
        nx, ny = self.nx, self.ny
        N = nx * ny
        free = np.concatenate([(~blk[F]).ravel(), (~blk[B]).ravel()])
        tgt = np.concatenate([tmask[F].ravel(), tmask[B].ravel()])
        if not tgt.any():
            return None
        # target centre for the heuristic
        tj, ti = np.nonzero(tmask[F] | tmask[B])
        tx, ty = ti.mean(), tj.mean()
        rad = max(ti.max() - ti.min(), tj.max() - tj.min()) / 2
        D = 9                                    # 8 headings + "none" (start, after a via)
        gcost = np.full(2 * N * D, np.inf, np.float32)
        came = np.full(2 * N * D, -1, np.int32)
        heap = []
        s_idx = np.nonzero(np.concatenate([smask[F].ravel(), smask[B].ravel()]))[0]
        if len(s_idx) == 0:
            return None
        for k in s_idx:
            st = int(k) * D + 8
            gcost[st] = 0
            L, r = divmod(int(k), N); iy, ix = divmod(r, nx)
            hh = max(0.0, math.hypot(ix - tx, iy - ty) - rad)
            heapq.heappush(heap, (hh, 0.0, st))
        dirs = [(1, 0, 1.0), (1, 1, 1.4142), (0, 1, 1.0), (-1, 1, 1.4142),
                (-1, 0, 1.0), (-1, -1, 1.4142), (0, -1, 1.0), (1, -1, 1.4142)]
        turn = [0.0, self.bend45 / self.g, self.bend90 / self.g, None, None, None, self.bend90 / self.g, self.bend45 / self.g]
        vcost = self.via_cost / self.g
        found = -1
        expanded = 0
        while heap:
            f, gc, st = heapq.heappop(heap)
            if gc > gcost[st]:
                continue
            k, hd = divmod(st, D)
            if tgt[k]:
                found = st
                break
            expanded += 1
            if expanded > 4_000_000:
                break
            L, r = divmod(k, N); iy, ix = divmod(r, nx)
            mult = self.b_cost if L == B else 1.0
            for d, (dx, dy, c) in enumerate(dirs):
                if hd != 8:
                    t = turn[(d - hd) % 8]
                    if t is None:
                        continue
                else:
                    t = 0.0
                jx, jy = ix + dx, iy + dy
                if jx < 0 or jy < 0 or jx >= nx or jy >= ny:
                    continue
                kk = L * N + jy * nx + jx
                if not free[kk]:
                    continue
                if dx and dy and not (free[L * N + iy * nx + jx] and free[L * N + jy * nx + ix]):
                    continue
                ng = gc + c * mult + t
                s2 = kk * D + d
                if ng < gcost[s2]:
                    gcost[s2] = ng; came[s2] = st
                    hh = max(0.0, math.hypot(jx - tx, jy - ty) - rad)
                    heapq.heappush(heap, (ng + hh, ng, s2))
            if allow_via and vok[iy, ix]:
                kk = (1 - L) * N + iy * nx + ix
                if free[kk]:
                    ng = gc + vcost
                    s2 = kk * D + 8
                    if ng < gcost[s2]:
                        gcost[s2] = ng; came[s2] = st
                        hh = max(0.0, math.hypot(ix - tx, iy - ty) - rad)
                        heapq.heappush(heap, (ng + hh, ng, s2))
        if found < 0:
            return None
        path = []
        st = found
        while st >= 0:
            k = st // D
            L, r = divmod(int(k), N); iy, ix = divmod(r, nx)
            path.append((L, ix, iy))
            st = int(came[st])
        return path[::-1]

    def commit(self, net, width, path):
        """Turn a cell path into tracks and vias and add them to the copper."""
        g = self.g
        pt = lambda c: (round((c[1] + 0.5) * g, 4), round((c[2] + 0.5) * g, 4))
        segs, vias = [], []
        i = 0
        while i < len(path) - 1:
            a, b = path[i], path[i + 1]
            if a[0] != b[0]:
                vias.append(pt(a)); i += 1; continue
            d = (b[1] - a[1], b[2] - a[2])
            j = i + 1
            while j + 1 < len(path) and path[j + 1][0] == a[0] and (path[j + 1][1] - path[j][1], path[j + 1][2] - path[j][2]) == d:
                j += 1
            segs.append((a[0], pt(a), pt(path[j])))
            i = j
        for L, p1, p2 in segs:
            self.add_track(net, L, width, p1[0], p1[1], p2[0], p2[1])
        for x, y in vias:
            self.add_via(net, x, y)
        return segs, vias
