"""Generate an SVG visualization of a .vtt Zoom transcript for pen
plotting.

"""
import sys

import vsketch
from shapely.affinity import translate
from shapely.geometry import LineString, MultiLineString, Polygon

from zoomzoom import zoom_timeseries, time_to_seconds

# Panel 00:42:34.230 01:17:49.680
# 
# Kristi Angel 01:40:52.620 01:45:29.850
# Lorena Mesa 01:46:27.030 01:52:19.500
# Alicia Boyd 01:52:47.910 01:55:28.920
# Marynia Kolak 01:56:00.930 01:59:58.470
# Vicky Kalogera 02:00:31.890 02:07:27.540
# Marshini Chetty 02:07:51.390 02:12:25.560
# Rebecca BurWei 02:12:44.910 02:16:30.450
# Bo Peng 02:16:48.420 02:21:08.070
# Hanna Parker 02:21:30.630 02:25:04.110

# PEN_SPACING = 0.7
# OFFSET_MULTIPLIER = 1
PEN_SPACING = 0.6
OFFSET_MULTIPLIER = 1.02
WIDTH = 4
HEIGHT = 6
MARGIN = 4 / 25.4
MM = 1 / 25.4
W = WIDTH - 2 * MARGIN

MAIN_HEIGHT = 1
N_SLICES = 10
SLICE_SPACING = (HEIGHT - 2 * MARGIN - MAIN_HEIGHT) / (N_SLICES - 1)

filename = sys.argv[1]
start = time_to_seconds(sys.argv[2])
end = time_to_seconds(sys.argv[3])

# speaker_list = ['Lucia Petito', 'Teodora Szasz', 'Dessa Gypalo', 'Ilana Marcus']
# speaker_list = ['Kristi Angel', 'Lorena Mesa']
# speaker_list = ['Alicia Boyd', 'Marynia Kolak']
speaker_list = ['Vicky Kalogera', 'Marshini Chetty']
# speaker_list = ['Rebecca BurWei', 'Bo Peng', 'Hanna Parker']
print('hi', start, end)

window_size = 5
outfilename = f"viz_{filename}_{window_size}_{start}:{end}.svg"

sketch = vsketch.Vsketch()
sketch.size("{}in".format(WIDTH), "{}in".format(HEIGHT))
sketch.scale("1in")
sketch._center_on_page = False

ts_list = zoom_timeseries(filename, window_size, 0.1, speaker_list)
for i_speaker, (speaker, ts) in enumerate(ts_list, 1):

    ts_max = max(v for t, v in ts)
    x = [N_SLICES * W * ((t - start) / (end - start)) for t, v in ts]
    y = [MAIN_HEIGHT * (1 - (v / ts_max)) for t, v in ts]
    poly = list(zip(x, y))
    poly.append((x[-1], 3 * MAIN_HEIGHT))
    poly.append((x[0], 3 * MAIN_HEIGHT))

    poly = Polygon(poly)
    # sketch.geometry(poly)

    all_poly = []
    offset = PEN_SPACING * MM
    while poly:
        all_poly.append(poly)
        poly = poly.buffer(-offset)
        offset *= OFFSET_MULTIPLIER

    baseline = Polygon([
        (x[0], MAIN_HEIGHT),
        (x[-1], MAIN_HEIGHT),
        (x[-1], 4 * MAIN_HEIGHT),
        (x[0], 4 * MAIN_HEIGHT),
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
    # sketch.geometry(parent)

    sketch.stroke(i_speaker)
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
sketch.save(outfilename)
