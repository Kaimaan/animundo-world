"""The blocks of a tree from its spec (models/trees/<id>.json), in plain Python.

The game's land is made of blocks, and so are its trees. A tree spec says
how tall the trunk is and what shape the crown has; this module turns that
into block templates: lists of [x, y, z] offsets for trunk and leaf blocks,
relative to the ground block the tree stands on (y = 1 is the first trunk
block). tools/blender/build_tree.py writes them to assets/trees/<id>.json,
which the game stamps into the land, and renders the preview sheet from the
same blocks, so the preview is exactly what the game shows.

Crown shapes:
  round     a ball of leaves on top (birch, oak, maple): radius, squash
  cone      a cone reaching down the trunk (spruce, fir): radius, height
  column    a tall narrow crown (cypress, poplar): radius, height
  umbrella  a wide flat crown on forked branches (acacia, stone pine): radius, thickness
  palm      fronds arching out from the top (palms): fronds, length, droop

Stilt roots (mangroves): trunk.roots = {"count", "spread", "height"} arches
`count` roots out from the trunk at `height` blocks down to the ground
`spread` blocks away, so the tree stands over shallow water (on: ["water"]).
"""

CROWNS = ("round", "cone", "column", "umbrella", "palm")
MAX_HEIGHT = 18   # blocks above the ground: the game's land is 32 blocks high
MAX_REACH = 8     # blocks from the trunk: a tree is stamped from its own and the neighbouring chunks
VARIANTS = 3      # trunk heights across the spec's range, so a forest isn't all one tree


def hash01(x, y, z, salt):
    """A repeatable 0..1 number for a block, so the same spec always gives the same tree."""
    h = (x * 73856093) ^ (y * 19349663) ^ (z * 83492791) ^ (salt * 2654435761)
    h &= 0xFFFFFFFF
    h ^= h >> 13
    h = (h * 1274126177) & 0xFFFFFFFF
    h ^= h >> 16
    return (h & 0xFFFF) / 65536.0


def problems(spec):
    """What's wrong with a tree spec, as sentences (empty when it's fine)."""
    out = []
    trunk = spec.get("trunk", {})
    crown = spec.get("crown", {})
    height = trunk.get("height")
    if not (isinstance(height, list) and len(height) == 2 and all(isinstance(v, int) for v in height)
            and 1 <= height[0] <= height[1]):
        out.append('"trunk.height" must be [lowest, highest] in blocks (metres), like [6, 9]')
    if trunk.get("girth", 1) not in (1, 2, 3):
        out.append('"trunk.girth" must be 1, 2 or 3 blocks')
    if crown.get("shape") not in CROWNS:
        out.append(f'"crown.shape" must be one of {", ".join(CROWNS)}')
    if out:
        return out
    for v in variants(spec):
        top = max(b[1] for b in v["trunk"] + v["leaf"])
        reach = max(max(abs(b[0]), abs(b[2])) for b in v["trunk"] + v["leaf"])
        if top > MAX_HEIGHT:
            out.append(f"the tree is {top} blocks tall; the most the game has room for is {MAX_HEIGHT}")
            break
        if reach > MAX_REACH:
            out.append(f"the crown reaches {reach} blocks from the trunk; the most is {MAX_REACH}")
            break
    return out


def variants(spec):
    """VARIANTS templates: {"trunk": [[x, y, z]...], "leaf": [...]}, shortest first."""
    lo, hi = spec["trunk"]["height"]
    out = []
    for i in range(VARIANTS):
        tall = round(lo + (hi - lo) * i / max(1, VARIANTS - 1))
        out.append(build(spec, tall, salt=i + 1))
    return out


def build(spec, tall, salt=1):
    trunk_spec = spec["trunk"]
    crown = spec["crown"]
    girth = trunk_spec.get("girth", 1)
    lean = trunk_spec.get("lean", 0)   # blocks the top of the trunk leans over, toward +x
    trunk, leaf = set(), set()
    lo = -(girth // 2)
    cols = [(dx, dz) for dx in range(lo, lo + girth) for dz in range(lo, lo + girth)]

    def offset(y):   # a leaning trunk bends more toward the top
        return round(lean * (y / tall) ** 2) if lean else 0

    shape = crown["shape"]
    stem = tall
    if shape == "umbrella":
        stem = max(2, round(tall * 0.55))   # the trunk forks below the crown
    for y in range(1, stem + 1):
        for dx, dz in cols:
            trunk.add((dx + offset(y), y, dz))
    top = (offset(stem), stem, 0)

    def put(x, y, z):
        if (x, y, z) not in trunk:
            leaf.add((x, y, z))

    if shape == "round":
        r = crown.get("radius", 2.5)
        squash = crown.get("squash", 1.3)
        cy = stem + 1
        blob(put, top[0], cy, 0, r, r / squash, salt)
    elif shape == "column":
        r = crown.get("radius", 1.2)
        h = crown.get("height", max(3, tall - 1))
        cy = stem + 1 - h / 2 + 1
        blob(put, top[0], round(cy), 0, r, h / 2, salt)
        for y in range(round(cy), stem + 1):   # the trunk runs up inside the crown
            trunk.add((top[0], y, 0))
    elif shape == "cone":
        r = crown.get("radius", 2.8)
        h = crown.get("height", tall - 1)
        base = stem + 2 - h
        for i in range(h):
            y = base + i
            rr = r * (1 - i / max(1, h - 1)) + 0.4
            ri = int(rr)
            for dz in range(-ri, ri + 1):
                for dx in range(-ri, ri + 1):
                    if abs(dx) + abs(dz) <= ri + 1 and hash01(dx, y, dz, salt) > 0.06:
                        put(offset(y) + dx, y, dz)
        put(top[0], stem + 2, 0)
    elif shape == "umbrella":
        r = crown.get("radius", 4.0)
        thick = crown.get("thickness", 2)
        cy = tall
        # two or three branches climb from the fork out to the crown
        for k, (bx, bz) in enumerate(((1, 0), (-1, 1), (0, -1))[:crown.get("branches", 3)]):
            for s in range(1, tall - stem + 1):
                f = s / (tall - stem)
                trunk.add((top[0] + round(bx * f * r * 0.45), stem + s, round(bz * f * r * 0.45)))
        ri = int(r + 0.5)
        for dy in range(thick):
            y = cy + dy
            rr = r - dy * 0.8
            for dz in range(-ri, ri + 1):
                for dx in range(-ri, ri + 1):
                    d = (dx * dx + dz * dz) ** 0.5
                    if d <= rr + (hash01(dx, y, dz, salt) - 0.5) * 0.8:
                        put(top[0] + dx, y, dz)
    elif shape == "palm":
        n = crown.get("fronds", 8)
        length = crown.get("length", 4)
        droop = crown.get("droop", 0.6)
        import math
        put(top[0], stem + 1, 0)
        for k in range(n):
            a = 2 * math.pi * k / n + hash01(k, 0, 0, salt) * 0.4
            dx, dz = math.cos(a), math.sin(a)
            for s in range(1, length + 1):
                y = stem + 1 + round(s * 0.5 - droop * s * s / length)
                put(top[0] + round(dx * s), y, round(dz * s))
    roots = trunk_spec.get("roots")
    if roots:
        import math
        n, spread, rh = roots.get("count", 6), roots.get("spread", 2), roots.get("height", 2)
        for k in range(n):
            a = 2 * math.pi * k / n + 0.3
            y = rh
            for s in range(1, spread + 1):
                # out from the trunk at `rh`, sloping down, then straight down into the water
                x, z = round(math.cos(a) * s), round(math.sin(a) * s)
                if s < spread:
                    y = max(2, rh - round((rh - 2) * s / spread))
                    trunk.add((x, y, z))
                else:
                    for yy in range(1, y + 1):
                        trunk.add((x, yy, z))
    return {"trunk": sorted([list(b) for b in trunk]), "leaf": sorted([list(b) for b in leaf])}


def blob(put, cx, cy, cz, r, ry, salt):
    """An ellipsoid of leaves, a little ragged at the edge."""
    ri, rj = int(r + 1), int(ry + 1)
    for dy in range(-rj, rj + 1):
        for dz in range(-ri, ri + 1):
            for dx in range(-ri, ri + 1):
                d = ((dx / r) ** 2 + (dy / max(ry, 0.5)) ** 2 + (dz / r) ** 2) ** 0.5
                if d <= 1.0 + (hash01(dx, cy + dy, dz, salt) - 0.6) * 0.3:
                    put(cx + dx, cy + dy, cz + dz)
