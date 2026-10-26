# seine brand scene: a diamond-mesh net stretched across the frame with lime blocks, rendered in Cycles.
# blender -b --factory-startup -noaudio -P scripts/brand/net_scene.py -- --out <dir> --variant C|D --style teal [--name --w --h --samples --cam --tgt --lens --fstop --sheet]
import bpy, bmesh, math, random, sys, os
from mathutils import Vector

av = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
def opt(n, d): return av[av.index('--' + n) + 1] if '--' + n in av else d
OUT = opt('out', '.'); V = opt('variant', 'A'); NAME = opt('name', 'net_' + V)
W = int(opt('w', 800)); H = int(opt('h', 450)); SAMPLES = int(opt('samples', 32))
random.seed(4)
STYLE = opt('style', 'violet')
JIT = float(opt('jit', 0.035 if opt('variant', 'A') == 'C' else 0.0))
SHEET = float(opt('sheet', 1.0))
SKIP = {tuple(float(v) for v in t.split(',')) for t in opt('skip', '').split(';') if t}
STY = {
  # bg_bottom, bg_top, rope, block base, block emission(edge, body), view, rope emission
  'violet': dict(bg=('#12052E', '#7A48F0'), rope='#E2D8FF', block='#8FE000', edge=3.5, body=0.12, view='Standard', ropeglow=0.0, key=700, rim=600, rim_col=(0.75, 0.6, 1.0), exp=-0.3),
  'clay':   dict(bg=('#DCD6EA', '#F7F4FB'), rope='#FFFFFF', block='#9BE52A', edge=0.0, body=0.0, view='Standard', ropeglow=0.0, key=900, rim=300, rim_col=(1, 1, 1), exp=-1.4),
  'neon':   dict(bg=('#000000', '#0B0F0A'), rope='#AAFF00', block='#E9FFD0', edge=5, body=0.25, view='Standard', ropeglow=0.9, key=120, rim=150, rim_col=(0.6, 1.0, 0.4), exp=-0.3),
  'sunset': dict(bg=('#2A0B3D', '#FF7A59'), rope='#FFE3D6', block='#8FE000', edge=3.0, body=0.1, view='Standard', ropeglow=0.0, key=700, rim=700, rim_col=(1.0, 0.55, 0.4), exp=-0.4),
  'teal':   dict(bg=('#021A1E', '#1BA3A0'), rope='#DFFBF6', block='#8FE000', edge=3.5, body=0.12, view='Standard', ropeglow=0.0, key=700, rim=600, rim_col=(0.5, 1.0, 0.9), exp=-0.3),
}[STYLE]

def lin(h):
    h = h.lstrip('#'); c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple((v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4) for v in c) + (1.0,)

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = SAMPLES
sc.cycles.use_adaptive_sampling = True; sc.cycles.use_denoising = True
sc.render.resolution_x, sc.render.resolution_y = W, H; sc.cycles.filter_width = 1.6
sc.view_settings.view_transform = STY['view']; sc.view_settings.look = 'Medium High Contrast'; sc.view_settings.exposure = STY['exp']

def block_material(edge_glow=STY['edge'], body=STY['body']):
    m = bpy.data.materials.new('block'); m.use_nodes = True; nt = m.node_tree
    b = nt.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = lin(STY['block']); b.inputs['Roughness'].default_value = 0.25
    b.inputs['Coat Weight'].default_value = 0.4; b.inputs['Emission Color'].default_value = lin('#7FE000' if STYLE != 'neon' else '#D8FF9A')
    bev = nt.nodes.new('ShaderNodeBevel'); bev.inputs['Radius'].default_value = 0.06; bev.samples = 8
    geo = nt.nodes.new('ShaderNodeNewGeometry')
    dot = nt.nodes.new('ShaderNodeVectorMath'); dot.operation = 'DOT_PRODUCT'
    nt.links.new(bev.outputs['Normal'], dot.inputs[0]); nt.links.new(geo.outputs['Normal'], dot.inputs[1])
    edge = nt.nodes.new('ShaderNodeMapRange'); edge.inputs['From Min'].default_value = 0.985; edge.inputs['From Max'].default_value = 0.85
    nt.links.new(dot.outputs['Value'], edge.inputs['Value'])
    em = nt.nodes.new('ShaderNodeMath'); em.operation = 'MULTIPLY_ADD'; em.inputs[1].default_value = edge_glow; em.inputs[2].default_value = body
    nt.links.new(edge.outputs['Result'], em.inputs[0]); nt.links.new(em.outputs[0], b.inputs['Emission Strength'])
    return m
BLOCK = block_material()
ROPE = bpy.data.materials.new('rope'); ROPE.use_nodes = True
rb = ROPE.node_tree.nodes['Principled BSDF']; rb.inputs['Base Color'].default_value = lin(STY['rope'])
_rn = ROPE.node_tree
_nz = _rn.nodes.new('ShaderNodeTexNoise'); _nz.inputs['Scale'].default_value = 140.0; _nz.inputs['Detail'].default_value = 4.0
_bp = _rn.nodes.new('ShaderNodeBump'); _bp.inputs['Strength'].default_value = 0.35
_rn.links.new(_nz.outputs['Fac'], _bp.inputs['Height']); _rn.links.new(_bp.outputs['Normal'], rb.inputs['Normal'])
if STY['ropeglow']:
    rb.inputs['Emission Color'].default_value = lin(STY['rope']); rb.inputs['Emission Strength'].default_value = STY['ropeglow']; rb.inputs['Roughness'].default_value = 0.7; rb.inputs['Sheen Weight'].default_value = 0.6

def cube(loc, size, rot=(0.45, 0.35, 0.7)):
    bpy.ops.mesh.primitive_cube_add(size=size, location=loc, rotation=rot)
    c = bpy.context.object
    c.data.materials.append(BLOCK); return c

def net_sheet(w, h, nx, ny, bulges, sag=0.0, tilt=(0, 0, 0), loc=(0, 0, 0), rope=0.02):
    """Diamond-mesh sheet in the XZ plane (facing -Y). bulges: (x, z, depth, radius) pushed toward +Y."""
    bm = bmesh.new()
    vs = [[bm.verts.new(((i / nx - 0.5) * w, 0, (j / ny - 0.5) * h)) for j in range(ny + 1)] for i in range(nx + 1)]
    for i in range(nx):
        for j in range(ny):
            bm.faces.new((vs[i][j], vs[i + 1][j], vs[i + 1][j + 1], vs[i][j + 1]))
    orig = list(bm.edges)
    bmesh.ops.poke(bm, faces=list(bm.faces))
    bmesh.ops.dissolve_edges(bm, edges=[e for e in orig if e.is_valid and len(e.link_faces) == 2], use_verts=False)
    for v in bm.verts:
        x, z = v.co.x, v.co.z
        y = sag * (1 - (2 * x / w) ** 2) * 0.5
        for bx, bz, depth, rad in bulges:
            r2 = (x - bx) ** 2 + (z - bz) ** 2
            y += depth * math.exp(-r2 / (rad * rad))
            # pull cells toward the bulge centre so the mesh stretches around the block
            k = 0.18 * depth * math.exp(-r2 / (rad * rad * 2.2))
            v.co.x += (bx - x) * k * 0.15; v.co.z += (bz - z) * k * 0.15
        v.co.y = y + random.gauss(0, 0.004)
        v.co.x += random.gauss(0, JIT * w / nx); v.co.z += random.gauss(0, JIT * h / ny)
    me = bpy.data.meshes.new('net'); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new('net', me); sc.collection.objects.link(ob)
    wf = ob.modifiers.new('w', 'WIREFRAME'); wf.thickness = rope; wf.use_even_offset = True
    ob.data.materials.append(ROPE); ob.location = loc; ob.rotation_euler = tilt
    return ob

# background: violet water gradient + faint rays, bokeh specks
world = bpy.data.worlds.new('w'); sc.world = world; world.use_nodes = True; wn = world.node_tree
bgn = wn.nodes['Background']
tc = wn.nodes.new('ShaderNodeTexCoord'); sep = wn.nodes.new('ShaderNodeSeparateXYZ'); ramp = wn.nodes.new('ShaderNodeValToRGB')
wn.links.new(tc.outputs['Window'], sep.inputs[0]); wn.links.new(sep.outputs['Y'], ramp.inputs['Fac'])
ramp.color_ramp.elements[0].position = 0.0; ramp.color_ramp.elements[0].color = lin(STY['bg'][0])
ramp.color_ramp.elements[1].position = 1.0; ramp.color_ramp.elements[1].color = lin(STY['bg'][1])
wn.links.new(ramp.outputs['Color'], bgn.inputs['Color']); bgn.inputs['Strength'].default_value = 1.0

bpy.ops.object.light_add(type='AREA', location=(-3, -4, 5), rotation=(math.radians(50), 0, math.radians(-35)))
k = bpy.context.object; k.data.energy = STY['key']; k.data.size = 4; k.data.color = (0.92, 0.88, 1.0); k.visible_camera = False
bpy.ops.object.light_add(type='AREA', location=(3, 5, 3), rotation=(math.radians(-60), 0, math.radians(150)))
r = bpy.context.object; r.data.energy = STY['rim']; r.data.size = 3; r.data.color = STY['rim_col']; r.visible_camera = False

SPECK = bpy.data.materials.new('speck'); SPECK.use_nodes = True
sb = SPECK.node_tree.nodes['Principled BSDF']; sb.inputs['Emission Color'].default_value = lin('#D8C8FF'); sb.inputs['Emission Strength'].default_value = 0.0 if STYLE == 'clay' else 2.0
for i in range(70):
    bpy.ops.mesh.primitive_ico_sphere_add(radius=random.uniform(0.01, 0.035), location=(random.uniform(-9, 9), random.uniform(-3, 9), random.uniform(-5, 5)), subdivisions=1)
    bpy.context.object.data.materials.append(SPECK)

# ---------- variants ----------
if V == 'A':   # block pressing into a taut net stretched across the frame
    net_sheet(16, 9, 88, 50, [(0.6, 0.0, 1.1, 1.1)], sag=0.4, loc=(0, 0.2, 0))
    cube((0.6, 0.15, 0.0), 1.25)
    for x, z, s in ((-3.6, 1.2, 0.35), (-2.4, -1.6, 0.25), (3.8, 1.8, 0.3), (4.6, -1.2, 0.22), (-5.2, 0.2, 0.28)):
        net_sheet  # small blocks resting on the far side of the net
        cube((x, 0.45, z), s, rot=(random.random(), random.random(), random.random()))
    cam_loc, tgt, lens, focus = (-1.2, -7.5, 0.6), (0.4, 0.4, 0.0), 40, 7.6
elif V == 'B':  # net sharp in the foreground, glowing block just behind it
    net_sheet(9, 5.2, 70, 40, [], sag=0.0, loc=(0, -2.2, 0), rope=0.016)
    cube((0.9, 0.4, -0.1), 1.4)
    for x, z, s in ((-2.5, 0.9, 0.3), (-1.4, -1.1, 0.24), (3.1, 1.3, 0.28)):
        cube((x, 1.6, z), s, rot=(random.random(), random.random(), random.random()))
    cam_loc, tgt, lens, focus = (-0.6, -6.5, 0.3), (0.6, 0.4, 0.0), 50, 4.3
elif V == 'C':  # net running diagonally across the frame, blocks caught in it, hero block in front
    net_sheet(20 * SHEET, 7 * SHEET, int(100 * SHEET), int(36 * SHEET), [(-2.0, 0.4, 0.22, 0.45), (1.2, -0.6, 0.2, 0.4), (3.4, 0.8, 0.18, 0.35)], sag=0.8,
              tilt=(0, math.radians(-24), math.radians(-12)), loc=(0, 0.6, 0))
    for x, y, z, s in ((-2.0, 0.9, 0.5, 0.45), (1.1, 0.9, -0.5, 0.42), (3.2, 0.9, 1.0, 0.36)):
        cube((x, y, z), s, rot=(random.random(), random.random(), random.random()))
    for x, y, z, sz in ((-4.6, 0.9, -0.6, 0.3), (5.2, 0.9, -0.2, 0.28), (-0.3, 0.9, 1.6, 0.26), (2.3, 0.9, 2.1, 0.22)):
        if (x, z) in SKIP: continue
        cube((x, y, z), sz, rot=(random.random(), random.random(), random.random()))
    cube((-1.0, -2.2, -0.9), 1.1)
    cam_loc, tgt, lens, focus = (-0.8, -7.6, 0.2), (0.0, 0.2, 0.0), 35, 5.6
else:  # D: macro, a block pushing through one cell
    net_sheet(6 * SHEET, 3.4 * SHEET, int(22 * SHEET), int(12 * SHEET), [(0.0, 0.0, -0.9, 0.7)], sag=0.0, loc=(0, 0, 0), rope=0.035)
    cube((0.0, -0.35, 0.0), 0.9, rot=(0.6, 0.2, 0.785))
    cube((-2.4, 0.9, 1.1), 0.22, rot=(0.8, 0.1, 0.5))       # one more beyond the net
    cam_loc, tgt, lens, focus = (-1.4, -4.2, 0.6), (0.0, 0.0, 0.0), 45, 4.3

if opt('cam', ''): cam_loc = tuple(float(x) for x in opt('cam', '').split(','))
if opt('tgt', ''): tgt = tuple(float(x) for x in opt('tgt', '').split(','))
lens = float(opt('lens', lens)); focus = float(opt('focus', focus))
bpy.ops.object.empty_add(location=tgt); target = bpy.context.object
bpy.ops.object.camera_add(location=cam_loc); cam = bpy.context.object; cam.data.lens = lens; sc.camera = cam
c = cam.constraints.new('TRACK_TO'); c.target = target; c.track_axis = 'TRACK_NEGATIVE_Z'; c.up_axis = 'UP_Y'
cam.data.dof.use_dof = True; cam.data.dof.focus_distance = focus; cam.data.dof.aperture_fstop = float(opt('fstop', 2.0))

os.makedirs(OUT, exist_ok=True)
sc.render.filepath = os.path.join(OUT, NAME + '.png')
bpy.ops.render.render(write_still=True)
print('WROTE', sc.render.filepath)
