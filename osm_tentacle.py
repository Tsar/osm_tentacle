#!/usr/bin/env python3

import sys

import psycopg2

import OpenGL
from OpenGL.GL import *
from OpenGL.GLUT import *

DEFAULT_WINDOW_SIZE_X = 800
DEFAULT_WINDOW_SIZE_Y = 600
DEFAULT_WINDOW_POS_X = 100
DEFAULT_WINDOW_POS_Y = 50

NODE_CROSS_DELTA = 0.00003

def load_all_relation_members(rel_id, conn):
    new_relation = []
    cur2 = conn.cursor()
    cur2.execute("SELECT member_id FROM relation_members WHERE relation_id = %d AND relation_members.member_type = 'W' ORDER BY relation_members.sequence_id" % rel_id)
    for rel_way in cur2:
        new_way = ('W', rel_way[0], [])
        cur3 = conn.cursor()
        cur3.execute("SELECT ST_X(nodes.geom), ST_Y(nodes.geom) FROM way_nodes, nodes WHERE way_nodes.node_id = nodes.id AND way_nodes.way_id = %d ORDER BY way_nodes.sequence_id" % rel_way[0])
        for coords in cur3:
            new_way[2].append(coords)
        new_relation.append(new_way)
    cur2.execute("SELECT member_id FROM relation_members WHERE relation_id = %d AND relation_members.member_type = 'N' ORDER BY relation_members.sequence_id" % rel_id)
    for rel_node in cur2:
        cur3 = conn.cursor()
        cur3.execute("SELECT 'N', id, ST_X(geom), ST_Y(geom) FROM nodes WHERE id = %d" % rel_node[0])
        if cur3.rowcount != 0:
            new_relation.append(cur3.fetchone())
    cur2.execute("SELECT member_id FROM relation_members WHERE relation_id = %d AND relation_members.member_type = 'R' ORDER BY relation_members.sequence_id" % rel_id)
    for rel_relation in cur2:
        inside_relation = load_all_relation_members(rel_relation[0], conn)
        new_relation.extend(inside_relation)  # Merging all inside_relation members into new_relation
    return new_relation

# Load osm from pgsnapshot db
def loadDB(pgSqlConnOpts):
    global bounds
    global nodes
    global ways
    global relations

    conn = psycopg2.connect(pgSqlConnOpts)
    cur = conn.cursor()
    cur.execute("SELECT MIN(ST_X(geom)), MIN(ST_Y(geom)), MAX(ST_X(geom)), MAX(ST_Y(geom)) FROM nodes")
    bounds = [coord for coord in cur.fetchone()]

    cur.execute("SELECT id FROM ways")
    for way in cur:
        new_way = (way[0], [], dict())
        cur2 = conn.cursor()
        cur2.execute("SELECT ST_X(nodes.geom), ST_Y(nodes.geom) FROM way_nodes, nodes WHERE way_nodes.node_id = nodes.id AND way_nodes.way_id = %d ORDER BY way_nodes.sequence_id" % way[0])
        for coords in cur2:
            new_way[1].append(coords)
        cur2.execute("SELECT skeys(tags), svals(tags) FROM ways WHERE id = %d" % way[0])
        for way_tag in cur2:
            new_way[2][way_tag[0]] = way_tag[1]
        ways.append(new_way)

    cur.execute("SELECT id, ST_X(geom), ST_Y(geom) FROM nodes WHERE tags != ''")
    for node in cur:
        node_tags = dict()
        cur2 = conn.cursor()
        cur2.execute("SELECT skeys(tags), svals(tags) FROM nodes WHERE id = %d" % node[0])
        for node_tag in cur2:
            node_tags[node_tag[0]] = node_tag[1]
        nodes.append((node[0], node[1], node[2], node_tags))

    cur.execute("SELECT id FROM relations")
    for relation in cur:
        rel_tags = dict()
        cur2 = conn.cursor()
        cur2.execute("SELECT skeys(tags), svals(tags) FROM relations WHERE id = %d" % relation[0])
        for rel_tag in cur2:
            rel_tags[rel_tag[0]] = rel_tag[1]
        relations.append((relation[0], load_all_relation_members(relation[0], conn), rel_tags))

    cur.close()
    conn.close()

def convX(x):
    global bounds
    return 2.0 * (x - bounds[0]) / (bounds[2] - bounds[0]) - 1

def convY(y):
    global bounds
    return 2.0 * (y - bounds[1]) / (bounds[3] - bounds[1]) - 1

def myVertex(x, y):
    glVertex(convX(x), convY(y))

def drawWay(way_coords):
    glBegin(GL_LINE_STRIP)
    for coords in way_coords:
        myVertex(coords[0], coords[1])
    glEnd()

def drawNode(node_x, node_y):
    glBegin(GL_LINES)
    myVertex(node_x - NODE_CROSS_DELTA, node_y - NODE_CROSS_DELTA)
    myVertex(node_x + NODE_CROSS_DELTA, node_y + NODE_CROSS_DELTA)
    myVertex(node_x + NODE_CROSS_DELTA, node_y - NODE_CROSS_DELTA)
    myVertex(node_x - NODE_CROSS_DELTA, node_y + NODE_CROSS_DELTA)
    glEnd()

def drawRelation(relation_members, selected):
    for rel_member in relation_members:
        if rel_member[0] == 'W':
            if selected:
                glLineWidth(3.0)
                glColor(1.0, 1.0, 0.0)
            else:
                glLineWidth(1.5)
                glColor(0.156, 0.675, 1.0)
            glBegin(GL_LINE_STRIP)
            for coords in rel_member[2]:
                myVertex(coords[0], coords[1])
            glEnd()
        elif rel_member[0] == 'N':
            if selected:
                glLineWidth(1.5)
                glColor(1.0, 1.0, 0.0)
            else:
                glLineWidth(1.0)
                glColor(0.0, 0.675, 0.0)
            drawNode(rel_member[2], rel_member[3])

def displayFunc():
    global nodes
    global ways
    global relations
    global selectedWay
    global selectedRelation
    global selectedNode

    glClear(GL_COLOR_BUFFER_BIT)

    glLineWidth(1.0)
    glColor(1.0, 1.0, 1.0)
    for way in ways:
        drawWay(way[1])

    glColor(1.0, 0.0, 0.0)
    for node in nodes:
        drawNode(node[1], node[2])

    for relation in relations:
        drawRelation(relation[1], False)

    print("==================================")

    if selectedWay != -1:
        glLineWidth(3.0)
        glColor(1.0, 1.0, 0.0)
        drawWay(ways[selectedWay][1])
        print("* Selected way:      ", end = "")
        print(ways[selectedWay][2])
    else:
        print("* No way selected")

    if selectedRelation != -1:
        drawRelation(relations[selectedRelation][1], True)
        print("* Selected relation: ", end = "")
        print(relations[selectedRelation][2])
    else:
        print("* No relation selected")

    if selectedNode != -1:
        glLineWidth(1.5)
        glColor(1.0, 1.0, 0.0)
        drawNode(nodes[selectedNode][1], nodes[selectedNode][2])
        print("* Selected node:     ", end = "")
        print(nodes[selectedNode][3])
    else:
        print("* No node selected")

    glutSwapBuffers()

def keyboardFunc(key, x, y):
    global bounds

    if key == b'\x1b':
        sys.exit(0)
    elif key == b'f' or key == b'F':
        global fullscreenMode
        if fullscreenMode:
            glutReshapeWindow(DEFAULT_WINDOW_SIZE_X, DEFAULT_WINDOW_SIZE_Y)
            glutPositionWindow(DEFAULT_WINDOW_POS_X, DEFAULT_WINDOW_POS_Y)
        else:
            glutFullScreen()
        fullscreenMode = not fullscreenMode
    elif key == b'+':
        deltaX = (bounds[2] - bounds[0]) / 4.0
        deltaY = (bounds[3] - bounds[1]) / 4.0
        bounds[0] += deltaX
        bounds[2] -= deltaX
        bounds[1] += deltaY
        bounds[3] -= deltaY
        glutPostRedisplay()
    elif key == b'-':
        deltaX = (bounds[2] - bounds[0]) / 2.0
        deltaY = (bounds[3] - bounds[1]) / 2.0
        bounds[0] -= deltaX
        bounds[2] += deltaX
        bounds[1] -= deltaY
        bounds[3] += deltaY
        glutPostRedisplay()

def specialFunc(key, x, y):
    global bounds
    global nodes
    global ways
    global relations
    global selectedWay
    global selectedRelation
    global selectedNode

    deltaX = (bounds[2] - bounds[0]) / 10.0
    deltaY = (bounds[1] - bounds[3]) / 10.0

    if key == GLUT_KEY_LEFT:
        bounds[0] -= deltaX
        bounds[2] -= deltaX
    elif key == GLUT_KEY_RIGHT:
        bounds[0] += deltaX
        bounds[2] += deltaX
    elif key == GLUT_KEY_UP:
        bounds[1] -= deltaY
        bounds[3] -= deltaY
    elif key == GLUT_KEY_DOWN:
        bounds[1] += deltaY
        bounds[3] += deltaY
    elif key == GLUT_KEY_F1:
        selectedWay -= 1
        if selectedWay < -1:
            selectedWay = len(ways) - 1
    elif key == GLUT_KEY_F2:
        selectedWay += 1
        if selectedWay > len(ways) - 1:
            selectedWay = -1
    elif key == GLUT_KEY_F3:
        selectedRelation -= 1
        if selectedRelation < -1:
            selectedRelation = len(relations) - 1
    elif key == GLUT_KEY_F4:
        selectedRelation += 1
        if selectedRelation > len(relations) - 1:
            selectedRelation = -1
    elif key == GLUT_KEY_F5:
        selectedNode -= 1
        if selectedNode < -1:
            selectedNode = len(nodes) - 1
    elif key == GLUT_KEY_F6:
        selectedNode += 1
        if selectedNode > len(nodes) - 1:
            selectedNode = -1

    glutPostRedisplay()

if __name__ == "__main__":
    pgSqlConnOpts = " ".join(sys.argv[1:])  # Something like: "dbname=osm user=osm_user password=12345"

    bounds = [-1.0, -1.0, 1.0, 1.0]
    nodes = []
    ways = []
    relations = []

    loadDB(pgSqlConnOpts)

    selectedWay = -1
    selectedRelation = -1
    selectedNode = -1

    glutInit(sys.argv)
    glutInitDisplayMode(GLUT_RGBA | GLUT_DOUBLE)
    glutInitWindowSize(DEFAULT_WINDOW_SIZE_X, DEFAULT_WINDOW_SIZE_Y)
    glutInitWindowPosition(DEFAULT_WINDOW_POS_X, DEFAULT_WINDOW_POS_Y)
    win = glutCreateWindow(b"OSM Tentacle")

    fullscreenMode = False

    glutDisplayFunc(displayFunc)
    glutKeyboardFunc(keyboardFunc)
    glutSpecialFunc(specialFunc)

    glClearColor(0, 0, 0, 0)
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    #glEnable(GL_LINE_SMOOTH)
    #glHint(GL_LINE_SMOOTH_HINT, GL_DONT_CARE)

    glutMainLoop()
