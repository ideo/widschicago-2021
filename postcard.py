"""Generate an SVG visualization of a .vtt Zoom transcript for pen
plotting.

"""
import sys

import numpy as np
import vsketch
from shapely.affinity import translate
from shapely.geometry import LineString, MultiLineString, Polygon

from zoomzoom import zoom_timeseries

PEN_SPACING = 0.7
WIDTH = 4
HEIGHT = 6
MARGIN = 4 / 25.4
MM = 1 / 25.4
W = WIDTH - 2 * MARGIN

MAIN_HEIGHT = 1
N_SLICES = 10
SLICE_SPACING = (HEIGHT - 2 * MARGIN - MAIN_HEIGHT) / (N_SLICES - 1)

filename = sys.argv[1]
ts = zoom_timeseries(filename, 5)
ts_max = max(v for t, v in ts)
y = [MAIN_HEIGHT * (1 - (v / ts_max)) for t, v in ts]
x = list(np.linspace(0, N_SLICES * W, len(y)))
poly = list(zip(x, y))
poly.append((x[-1], 3 * MAIN_HEIGHT))
poly.append((x[0], 3 * MAIN_HEIGHT))

sketch = vsketch.Vsketch()
sketch.size("{}in".format(WIDTH), "{}in".format(HEIGHT))
sketch.scale("1in")
sketch._center_on_page = False

sketch.stroke(1)
poly = Polygon(poly)
all_poly = []
while poly:
    all_poly.append(poly)
    poly = poly.buffer(-PEN_SPACING * MM)

baseline = Polygon([
    (-MARGIN, MAIN_HEIGHT),
    (WIDTH * N_SLICES, MAIN_HEIGHT),
    (WIDTH * N_SLICES, 4 * MAIN_HEIGHT),
    (-MARGIN, 4 * MAIN_HEIGHT),
])

all_lines = []
for poly in all_poly:
    result = poly.difference(baseline)
    if result.geom_type == "MultiPolygon":
        for poly in result.geoms:
            line = LineString(list(poly.exterior.coords)[:-1])
            if line:
                all_lines.append(line)

    elif result.geom_type == "Polygon":
        line = LineString(list(result.exterior.coords)[:-1])
        if line:
            all_lines.append(line)

parent = MultiLineString(all_lines)

sketch.stroke(1)
for i in range(N_SLICES):
    box = Polygon([
        (i * W, 0),
        ((i + 1) * W, 0),
        ((i + 1) * W, MAIN_HEIGHT),
        (i * W, MAIN_HEIGHT),
    ])
    inter = parent.intersection(box)
    dx = i * W
    dy = i * SLICE_SPACING
    inter = translate(inter, -dx + MARGIN, dy + MARGIN)
    sketch.geometry(inter)

sketch.vpype("linemerge linesimplify reloop linesort")
sketch.display()
sketch.save(f"viz-{filename}.svg")
