"""Логика наполнения магазинов тестовыми товарами - вынесена отдельно,
чтобы её можно было вызвать автоматически при старте приложения
(на Render бесплатного тарифа нет доступа к Shell/One-off Jobs)."""
from models import db, Shop, Product, Review


def seed_if_empty():
    if Shop.query.count() > 0:
        return False  # уже наполнено, ничего не делаем

    techdom = Shop(name="TechDom", description="Магазин электроники (тестовый)")
    mebel = Shop(name="Mebel Test", description="Магазин мебели и декора (тестовый)")
    db.session.add_all([techdom, mebel])
    db.session.flush()

    techdom_products = [
        Product(shop_id=techdom.id, name="Роутер X1", category="электроника",
                price=250000, model_file="test_box.glb", shelf_x=-1.2,
                description="Роутер X1 — двухдиапазонный Wi-Fi роутер с зоной покрытия до 150 м2. "
                             "Тестовая карточка товара для проверки системы."),
        Product(shop_id=techdom.id, name="Колонка Sonic Ball", category="электроника",
                price=180000, model_file="test_sphere.glb", shelf_x=0,
                description="Портативная колонка Sonic Ball, 12 часов работы от батареи. "
                             "Тестовая карточка товара."),
        Product(shop_id=techdom.id, name="Повербанк Volt10", category="электроника",
                price=90000, model_file="test_cylinder.glb", shelf_x=1.2,
                description="Повербанк Volt10 на 10000 мАч, быстрая зарядка. Тестовая карточка."),
    ]

    mebel_products = [
        Product(shop_id=mebel.id, name="Табурет Ring", category="мебель",
                price=320000, model_file="test_torus.glb", shelf_x=-1.2,
                description="Табурет Ring в форме кольца, массив дерева. Тестовая карточка товара."),
        Product(shop_id=mebel.id, name="Лампа Cono", category="мебель",
                price=140000, model_file="test_cone.glb", shelf_x=0,
                description="Настольная лампа Cono, тёплый свет, регулировка яркости. Тестовая карточка."),
        Product(shop_id=mebel.id, name="Сувенир Ico", category="декор",
                price=45000, model_file="test_icosahedron.glb", shelf_x=1.2,
                description="Декоративный сувенир Ico ручной работы. Тестовая карточка товара."),
    ]

    db.session.add_all(techdom_products + mebel_products)
    db.session.flush()

    db.session.add_all([
        Review(target_type="shop", target_id=techdom.id, author="Алишер",
               rating=5, text="Быстро ответили, товар как на витрине."),
        Review(target_type="product", target_id=techdom_products[0].id, author="Дмитрий",
               rating=4, text="Роутер держит сигнал хорошо, но грелся первые дни."),
        Review(target_type="shop", target_id=mebel.id, author="Нигора",
               rating=5, text="Красивая мебель, продавец подробно всё показал в 3D."),
    ])

    db.session.commit()
    return True
