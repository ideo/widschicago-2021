import sys
import vsketch
import qrcode
import qrcode.image.svg
import networkx as nx
from networkx.algorithms.approximation import min_weighted_vertex_cover
from shapely.geometry import LineString

def path_cover(graph):

    # choose a node that hasn't been visited (start)
    # choose a neighbor that hasn't been visited (first), giving preference to node that's in the same direction.
    # set the direction as the direction from start -> first

    paths = []
    to_visit = set(graph.nodes)
    while to_visit:
    
        node = to_visit.pop()

        path = [node]
        direction = (0, 0)

        while node:

            unvisited_neighbors = []
            for neighbor in graph.neighbors(node):
                if neighbor in to_visit:
                    neighbor_direction = (neighbor[0]-node[0], neighbor[1]-node[1])
                    unvisited_neighbors.append((neighbor_direction, neighbor))
                    if neighbor_direction == direction:
                        break

            if unvisited_neighbors:
                direction, node = unvisited_neighbors[-1]
                path.append(node)
                to_visit.remove(node)
            else:
                node = None

        paths.append(path)
        
    return paths

def make_graph(maze):
    graph = nx.Graph()
    for y, row in enumerate(maze):
        for x, val in enumerate(row):
            if val:
                if (not y == 0) and maze[y - 1][x]:
                    graph.add_edge((x, y), (x, y - 1))
                if (not y == (len(maze) - 1)) and maze[y + 1][x]:
                    graph.add_edge((x, y), (x, y + 1))
                if (not x == 0) and maze[y][x - 1]:
                    graph.add_edge((x, y), (x - 1, y))
                if (not x) == (len(row) - 1) and maze[y][x + 1]:
                    graph.add_edge((x, y), (x + 1, y))
    return graph

PEN_SPACING = 0.7
OFFSET_MULTIPLIER = 1.02
WIDTH = 4
HEIGHT = 6
MARGIN = 4 / 25.4
MM = 1 / 25.4
W = WIDTH - 2 * MARGIN

qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H)
qr.add_data('https://ideo.github.io/widschicago-2021/')
qr.make()

outfilename = "back.svg"

sketch = vsketch.Vsketch()
sketch.size("{}in".format(WIDTH), "{}in".format(HEIGHT))
sketch.scale("1in")
sketch._center_on_page = False

actual_pen_width_mm = 0.5
dx = 5 * MM
dy = 5 * MM
size = actual_pen_width_mm * MM

sketch.stroke(1)
sketch.penWidth(f"{actual_pen_width_mm}mm", 1)

graph = make_graph(qr.modules)
for path in path_cover(graph):
    while len(path) < 3:
        path.append(path[-1])
    path = [(dx + x * size, dy + y * size) for (x, y) in path]
    line = LineString(path)
    sketch.geometry(line)
            
sketch.vpype("linemerge linesimplify reloop linesort")
sketch.display()
sketch.save(outfilename)
