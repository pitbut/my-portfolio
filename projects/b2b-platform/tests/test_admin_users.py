from werkzeug.security import generate_password_hash

from app import db
from app.models import (
    CustomerProfile,
    Listing,
    ListingCategory,
    Material,
    MaterialListing,
    Order,
    OrderStatusHistory,
    Region,
    ServiceCategory,
    User,
)

from tests.conftest import register


def _login(client, email, password="password123"):
    client.post("/auth/login", data={"email": email, "password": password}, follow_redirects=True)


def _make_admin(client, email="admin@example.com", password="adminpass123"):
    admin = User(email=email, password_hash=generate_password_hash(password), role="admin", email_confirmed=True)
    db.session.add(admin)
    db.session.commit()
    return admin.id


def test_users_list_requires_admin(client):
    register(client, email="notadmin@example.com", role="customer")
    resp = client.get("/admin/users", follow_redirects=False)
    assert resp.status_code == 403


def test_users_list_shows_registered_users(client):
    register(client, email="listed@example.com", role="customer")
    client.get("/auth/logout")
    _make_admin(client)
    _login(client, "admin@example.com", "adminpass123")

    resp = client.get("/admin/users")
    assert resp.status_code == 200
    assert "listed@example.com".encode() in resp.data


def test_toggle_block_prevents_login(client):
    register(client, email="tobeblocked@example.com", password="password123", role="customer")
    client.get("/auth/logout")
    with client.application.app_context():
        target_id = User.query.filter_by(email="tobeblocked@example.com").first().id
    _make_admin(client)
    _login(client, "admin@example.com", "adminpass123")

    client.post(f"/admin/users/{target_id}/toggle-block", follow_redirects=True)
    with client.application.app_context():
        assert User.query.get(target_id).is_blocked is True
    client.get("/auth/logout")

    resp = client.post(
        "/auth/login", data={"email": "tobeblocked@example.com", "password": "password123"}, follow_redirects=True,
    )
    assert "заблокирован".encode() in resp.data


def test_cannot_block_or_delete_admin(client):
    admin_id = _make_admin(client)
    _login(client, "admin@example.com", "adminpass123")

    resp = client.post(f"/admin/users/{admin_id}/toggle-block", follow_redirects=True)
    assert "Нельзя заблокировать администратора".encode() in resp.data
    resp = client.post(f"/admin/users/{admin_id}/delete", follow_redirects=True)
    assert "Нельзя удалить администратора".encode() in resp.data
    with client.application.app_context():
        assert db.session.get(User, admin_id) is not None


def test_delete_empty_user_succeeds(client):
    register(client, email="empty@example.com", role="customer")
    client.get("/auth/logout")
    with client.application.app_context():
        target_id = User.query.filter_by(email="empty@example.com").first().id
    _make_admin(client)
    _login(client, "admin@example.com", "adminpass123")

    resp = client.post(f"/admin/users/{target_id}/delete", follow_redirects=True)
    assert "аккаунт удалён".encode() in resp.data
    with client.application.app_context():
        assert db.session.get(User, target_id) is None


def test_delete_user_with_own_profile_succeeds(client):
    """CustomerProfile каскадно удаляется вместе с User
    (cascade="all, delete-orphan"), так что одного заполненного профиля
    недостаточно, чтобы удаление отказало — проверяем этот случай отдельно
    от «настоящих» связанных данных ниже."""
    register(client, email="withprofile@example.com", role="customer")
    with client.application.app_context():
        from app.models import Region

        region_id = Region.query.first().id
    client.post(
        "/profile/customer",
        data={"kind": "company", "display_name": "Завод Б", "region_id": str(region_id), "address_text": "Ташкент"},
        follow_redirects=True,
    )
    client.get("/auth/logout")
    with client.application.app_context():
        target_id = User.query.filter_by(email="withprofile@example.com").first().id
        assert CustomerProfile.query.filter_by(user_id=target_id).first() is not None

    _make_admin(client)
    _login(client, "admin@example.com", "adminpass123")

    resp = client.post(f"/admin/users/{target_id}/delete", follow_redirects=True)
    assert "аккаунт удалён".encode() in resp.data
    with client.application.app_context():
        assert db.session.get(User, target_id) is None


def _post_listing(client, title="Токарный станок 1К62"):
    with client.application.app_context():
        category_id = ListingCategory.query.first().id
        region_id = Region.query.first().id
    client.post(
        "/marketplace/new",
        data={
            "listing_intent": "sell", "category_id": str(category_id), "title": title,
            "description": "Рабочее состояние", "condition": "used",
            "price": "15000000", "currency": "UZS", "region_id": str(region_id),
        },
        follow_redirects=True,
    )


def test_user_detail_shows_listings(client):
    register(client, email="seller@example.com", role="customer")
    _post_listing(client, title="Токарный станок 1К62")
    with client.application.app_context():
        seller_id = User.query.filter_by(email="seller@example.com").first().id
    client.get("/auth/logout")

    _make_admin(client)
    _login(client, "admin@example.com", "adminpass123")

    resp = client.get(f"/admin/users/{seller_id}")
    assert resp.status_code == 200
    assert "Токарный станок 1К62".encode() in resp.data


def test_admin_can_delete_specific_listing(client):
    register(client, email="seller2@example.com", role="customer")
    _post_listing(client, title="Фрезерный станок")
    with client.application.app_context():
        seller_id = User.query.filter_by(email="seller2@example.com").first().id
        listing_id = Listing.query.filter_by(author_id=seller_id).first().id
    client.get("/auth/logout")

    _make_admin(client)
    _login(client, "admin@example.com", "adminpass123")

    resp = client.post(f"/admin/users/{seller_id}/listings/{listing_id}/delete", follow_redirects=True)
    assert "удалено".encode() in resp.data
    with client.application.app_context():
        assert db.session.get(Listing, listing_id) is None
    with client.application.app_context():
        assert db.session.get(User, seller_id) is not None


def test_delete_user_with_listing_succeeds_and_removes_listing(client):
    """Объявления — это собственный контент пользователя, не история сделки
    между сторонами, поэтому удаление аккаунта должно сносить их
    автоматически, а не отказывать (в отличие от сообщений/заказов)."""
    register(client, email="seller3@example.com", role="customer")
    _post_listing(client, title="Сверлильный станок")
    with client.application.app_context():
        seller_id = User.query.filter_by(email="seller3@example.com").first().id
        listing_id = Listing.query.filter_by(author_id=seller_id).first().id
    client.get("/auth/logout")

    _make_admin(client)
    _login(client, "admin@example.com", "adminpass123")

    resp = client.post(f"/admin/users/{seller_id}/delete", follow_redirects=True)
    assert "аккаунт удалён".encode() in resp.data
    with client.application.app_context():
        assert db.session.get(User, seller_id) is None
        assert db.session.get(Listing, listing_id) is None


def _setup_customer_with_order(client, email, title):
    register(client, email=email, role="customer")
    with client.application.app_context():
        region_id = Region.query.first().id
        service_id = ServiceCategory.query.first().id
    client.post(
        "/profile/customer",
        data={"kind": "company", "display_name": "Завод В", "region_id": str(region_id), "address_text": "Ташкент"},
        follow_redirects=True,
    )
    client.post(
        "/orders/new",
        data={
            "title": title, "description": "Описание заявки",
            "order_type": "manufacturing", "service_category_id": str(service_id),
            "region_id": str(region_id), "address_text": "Ташкент", "auction_hours": "48",
        },
        follow_redirects=True,
    )
    client.get("/auth/logout")


def test_admin_can_view_and_delete_fresh_order(client):
    _setup_customer_with_order(client, "orderer1@example.com", "Токарная обточка вала")
    with client.application.app_context():
        orderer_id = User.query.filter_by(email="orderer1@example.com").first().id
        order_id = Order.query.filter_by(title="Токарная обточка вала").first().id

    _make_admin(client)
    _login(client, "admin@example.com", "adminpass123")

    resp = client.get(f"/admin/users/{orderer_id}")
    assert "Токарная обточка вала".encode() in resp.data

    resp = client.post(f"/admin/users/{orderer_id}/orders/{order_id}/delete", follow_redirects=True)
    assert "удалена".encode() in resp.data
    with client.application.app_context():
        assert db.session.get(Order, order_id) is None


def test_admin_cannot_delete_order_with_status_history(client):
    """У заявки с историей статусов (спор/переход по стадиям) удаление честно
    откажет — эта история важна для другой стороны сделки и для арбитража."""
    _setup_customer_with_order(client, "orderer2@example.com", "Заказ со спором")
    with client.application.app_context():
        orderer_id = User.query.filter_by(email="orderer2@example.com").first().id
        order = Order.query.filter_by(title="Заказ со спором").first()
        db.session.add(OrderStatusHistory(order_id=order.id, to_status="published"))
        db.session.commit()
        order_id = order.id

    _make_admin(client)
    _login(client, "admin@example.com", "adminpass123")

    resp = client.post(f"/admin/users/{orderer_id}/orders/{order_id}/delete", follow_redirects=True)
    assert "не удалось удалить".encode() in resp.data
    with client.application.app_context():
        assert db.session.get(Order, order_id) is not None


def test_delete_user_with_messages_fails_gracefully(client):
    """Message.sender_id ссылается на users.id без каскада — удаление
    пользователя, который уже кому-то писал, должно честно отказать и
    предложить заблокировать вместо удаления, а не сломаться 500-й ошибкой."""
    register(client, email="chatty@example.com", role="customer")
    with client.application.app_context():
        chatty_id = User.query.filter_by(email="chatty@example.com").first().id
    client.get("/auth/logout")

    register(client, email="recipient@example.com", role="executor")
    with client.application.app_context():
        recipient_id = User.query.filter_by(email="recipient@example.com").first().id
    client.get("/auth/logout")

    _login(client, "chatty@example.com")
    client.post(f"/messages/u/{recipient_id}", data={"body": "Привет!"}, follow_redirects=True)
    client.get("/auth/logout")

    _make_admin(client)
    _login(client, "admin@example.com", "adminpass123")

    resp = client.post(f"/admin/users/{chatty_id}/delete", follow_redirects=True)
    assert "не удалось удалить".encode() in resp.data
    with client.application.app_context():
        assert db.session.get(User, chatty_id) is not None


def test_admin_can_view_and_fix_user_contacts(client):
    """Админ должен видеть телефон/адрес зарегистрировавшегося пользователя
    прямо в карточке и иметь возможность поправить анкету, если данные
    введены неверно (см. жалобу пользователя — контактов не было видно и
    нечем было их исправить)."""
    register(client, email="fixme@example.com", role="customer")
    with client.application.app_context():
        region_id = Region.query.first().id
    client.post(
        "/profile/customer",
        data={
            "kind": "individual", "display_name": "Иван", "region_id": str(region_id),
            "address_text": "Старый адрес", "phone": "+998900000000",
        },
        follow_redirects=True,
    )
    client.get("/auth/logout")
    with client.application.app_context():
        target_id = User.query.filter_by(email="fixme@example.com").first().id
    _make_admin(client)
    _login(client, "admin@example.com", "adminpass123")

    resp = client.get(f"/admin/users/{target_id}")
    assert resp.status_code == 200
    assert "+998900000000".encode() in resp.data
    assert "Старый адрес".encode() in resp.data

    resp = client.get(f"/admin/users/{target_id}/profile/edit")
    assert resp.status_code == 200
    assert "Старый адрес".encode() in resp.data

    resp = client.post(
        f"/admin/users/{target_id}/profile/edit",
        data={
            "display_name": "Иван", "phone": "+998901234567", "region_id": str(region_id),
            "address_text": "Новый адрес",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    with client.application.app_context():
        updated = db.session.get(User, target_id)
        assert updated.phone == "+998901234567"
        assert updated.customer_profile.address_text == "Новый адрес"


def test_admin_can_edit_order(client):
    """Заявку тоже можно поправить, а не только удалить — например, если
    заказчик опечатался в названии или описании."""
    _setup_customer_with_order(client, "orderfix@example.com", "Токарная обточка вала")
    with client.application.app_context():
        orderer_id = User.query.filter_by(email="orderfix@example.com").first().id
        order_id = Order.query.filter_by(title="Токарная обточка вала").first().id
        region_id = Region.query.first().id
        service_id = ServiceCategory.query.first().id

    _make_admin(client)
    _login(client, "admin@example.com", "adminpass123")

    resp = client.get(f"/admin/users/{orderer_id}/orders/{order_id}/edit")
    assert resp.status_code == 200
    assert "Токарная обточка вала".encode() in resp.data

    resp = client.post(
        f"/admin/users/{orderer_id}/orders/{order_id}/edit",
        data={
            "title": "Токарная обточка вала (испр.)", "description": "Исправленное описание",
            "order_type": "manufacturing", "service_category_id": str(service_id),
            "region_id": str(region_id),
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    with client.application.app_context():
        updated_order = db.session.get(Order, order_id)
        assert updated_order.title == "Токарная обточка вала (испр.)"
        assert updated_order.description == "Исправленное описание"


def test_admin_can_edit_listing(client):
    register(client, email="sellerfix@example.com", role="customer")
    _post_listing(client, title="Токарный станок для правки")
    with client.application.app_context():
        seller_id = User.query.filter_by(email="sellerfix@example.com").first().id
        listing_id = Listing.query.filter_by(author_id=seller_id).first().id
        category_id = ListingCategory.query.first().id
        region_id = Region.query.first().id
    client.get("/auth/logout")

    _make_admin(client)
    _login(client, "admin@example.com", "adminpass123")

    resp = client.get(f"/admin/users/{seller_id}/listings/{listing_id}/edit")
    assert resp.status_code == 200
    assert "Токарный станок для правки".encode() in resp.data

    resp = client.post(
        f"/admin/users/{seller_id}/listings/{listing_id}/edit",
        data={
            "listing_intent": "sell", "category_id": str(category_id),
            "title": "Токарный станок (испр.)", "description": "Исправленное описание",
            "condition": "used", "price": "16000000", "currency": "UZS", "region_id": str(region_id),
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    with client.application.app_context():
        updated_listing = db.session.get(Listing, listing_id)
        assert updated_listing.title == "Токарный станок (испр.)"
        assert updated_listing.description == "Исправленное описание"


def test_admin_can_edit_material_listing(client):
    register(client, email="materialseller@example.com", role="customer")
    with client.application.app_context():
        material_id = Material.query.first().id
        region_id = Region.query.first().id
    client.post(
        "/materials/new",
        data={
            "listing_intent": "sell", "material_id": str(material_id), "title": "Лист металла",
            "description": "Остатки со склада", "quantity": "500", "unit": "kg",
            "price": "9000000", "currency": "UZS", "region_id": str(region_id),
        },
        follow_redirects=True,
    )
    with client.application.app_context():
        seller_id = User.query.filter_by(email="materialseller@example.com").first().id
        listing_id = MaterialListing.query.filter_by(author_id=seller_id).first().id
    client.get("/auth/logout")

    _make_admin(client)
    _login(client, "admin@example.com", "adminpass123")

    resp = client.get(f"/admin/users/{seller_id}/material-listings/{listing_id}/edit")
    assert resp.status_code == 200
    assert "Лист металла".encode() in resp.data

    resp = client.post(
        f"/admin/users/{seller_id}/material-listings/{listing_id}/edit",
        data={
            "listing_intent": "sell", "material_id": str(material_id),
            "title": "Лист металла (испр.)", "description": "Исправленное описание",
            "quantity": "500", "unit": "kg", "price": "9000000", "currency": "UZS", "region_id": str(region_id),
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    with client.application.app_context():
        updated_listing = db.session.get(MaterialListing, listing_id)
        assert updated_listing.title == "Лист металла (испр.)"
        assert updated_listing.description == "Исправленное описание"


def test_admin_own_orders_page_is_always_empty(client):
    """Регресс-документация бага: у админа нет CustomerProfile, поэтому
    orders.my_orders («мои заявки») всегда пуст — админ должен видеть
    ленту через отдельную admin.orders_list, а не эту страницу."""
    _setup_customer_with_order(client, "notforadmin@example.com", "Заявка не для ленты админа")

    _make_admin(client)
    _login(client, "admin@example.com", "adminpass123")

    resp = client.get("/orders")
    assert resp.status_code == 200
    assert "Заявка не для ленты админа".encode() not in resp.data


def test_admin_orders_feed_shows_all_platform_orders(client):
    _setup_customer_with_order(client, "feedcustomer@example.com", "Токарная деталь для ленты")

    _make_admin(client)
    _login(client, "admin@example.com", "adminpass123")

    resp = client.get("/admin/orders")
    assert resp.status_code == 200
    assert "Токарная деталь для ленты".encode() in resp.data
    assert "feedcustomer@example.com".encode() in resp.data


def test_admin_stats_page_shows_page_view_counts(client):
    from app.models import PageView

    with client.application.app_context():
        before = PageView.query.count()

    client.get("/")
    client.get("/")

    with client.application.app_context():
        assert PageView.query.count() >= before + 2

    _make_admin(client)
    _login(client, "admin@example.com", "adminpass123")

    resp = client.get("/admin/stats")
    assert resp.status_code == 200
    assert "Статистика посещений".encode() in resp.data
