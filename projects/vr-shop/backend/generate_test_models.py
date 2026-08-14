"""
Генератор простых тестовых 3D-моделей (GLB) для проверки системы,
пока нет реальных моделей товаров. Каждая модель — примитив с цветом.
"""
import trimesh
import numpy as np
import os

OUT_DIR = os.path.join(os.path.dirname(__file__), "static", "models")
os.makedirs(OUT_DIR, exist_ok=True)


def colorize(mesh, rgba):
    mesh.visual.vertex_colors = np.tile(rgba, (mesh.vertices.shape[0], 1))
    return mesh


def save(mesh, name):
    path = os.path.join(OUT_DIR, f"{name}.glb")
    mesh.export(path, file_type="glb")
    print("saved", path)


# box -> "роутер"
box = colorize(trimesh.creation.box(extents=[0.4, 0.15, 0.25]), [60, 90, 200, 255])
save(box, "test_box")

# sphere -> "колонка"
sphere = colorize(trimesh.creation.icosphere(radius=0.18, subdivisions=3), [220, 60, 60, 255])
save(sphere, "test_sphere")

# cylinder -> "повербанк"
cyl = colorize(trimesh.creation.cylinder(radius=0.08, height=0.35), [90, 200, 120, 255])
save(cyl, "test_cylinder")

# torus -> "табурет/кольцо"
torus = colorize(trimesh.creation.torus(major_radius=0.2, minor_radius=0.06), [200, 160, 40, 255])
save(torus, "test_torus")

# cone -> "лампа"
cone = colorize(trimesh.creation.cone(radius=0.18, height=0.35), [180, 90, 200, 255])
save(cone, "test_cone")

# icosahedron -> "сувенир"
ico = colorize(trimesh.creation.icosahedron(), [40, 180, 190, 255])
ico.apply_scale(0.15)
save(ico, "test_icosahedron")

print("Готово: сгенерировано 6 тестовых моделей в", OUT_DIR)
