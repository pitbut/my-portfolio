import io

from app.models import Bid, EquipmentType, Material, Notification, Order, OrderMedia, Region, ServiceCategory, User

from tests.conftest import register


def _setup_customer(client, email="cust@example.com"):
    register(client, email=email, role="customer")
    with client.application.app_context():
        region_id = Region.query.first().id
    client.post(
        "/profile/customer",
        data={
            "kind": "company", "display_name": "Завод А", "region_id": str(region_id),
            "address_text": "Ташкент, промзона", "latitude": "41.30", "longitude": "69.25",
        },
        follow_redirects=True,
    )
    client.get("/auth/logout")
    return region_id


def _setup_executor(client, email, region_id, radius_km=200):
    register(client, email=email, role="executor")
    with client.application.app_context():
        equipment_type_id = EquipmentType.query.first().id
        service_id = ServiceCategory.query.first().id
        material_id = Material.query.first().id

    client.post(
        "/profile/executor",
        data={
            "org_type": "tsekh", "display_name": f"Цех {email}", "region_id": str(region_id),
            "address_text": "рядом", "latitude": "41.31", "longitude": "69.26",
            "service_radius_km": str(radius_km),
        },
        follow_redirects=True,
    )
    client.post(
        "/profile/executor/equipment/add",
        data={"equipment_type_id": str(equipment_type_id), "quantity": "1"},
        follow_redirects=True,
    )
    client.post(
        "/profile/executor/capabilities",
        data={
            "max_length_mm": "5000", "max_diameter_mm": "1000", "max_weight_kg": "2000",
            "service_category_ids": [str(service_id)], "material_ids": [str(material_id)],
        },
        follow_redirects=True,
    )
    client.get("/auth/logout")
    return service_id, material_id


def _login(client, email, password="password123"):
    client.post("/auth/login", data={"email": email, "password": password}, follow_redirects=True)


def _create_order(client, region_id, service_id, **overrides):
    data = {
        "title": "Токарная обточка вала", "description": "Нужно выточить вал 40 мм",
        "order_type": "manufacturing", "service_category_id": str(service_id),
        "region_id": str(region_id), "address_text": "Ташкент", "latitude": "41.30", "longitude": "69.25",
        "auction_hours": "48",
    }
    data.update(overrides)
    return client.post("/orders/new", data=data, follow_redirects=True)


def test_order_creation_requires_customer_profile(client):
    register(client, email="noprof@example.com", role="customer")
    with client.application.app_context():
        region_id = Region.query.first().id
        service_id = ServiceCategory.query.first().id
    resp = client.post(
        "/orders/new",
        data={"title": "x", "description": "y", "order_type": "repair", "service_category_id": str(service_id), "region_id": str(region_id)},
        follow_redirects=True,
    )
    assert "Сначала заполните профиль заказчика".encode() in resp.data
    with client.application.app_context():
        assert Order.query.count() == 0


def test_order_matches_suitable_executor_and_notifies(client):
    region_id = _setup_customer(client, "cust1@example.com")
    service_id, material_id = _setup_executor(client, "exec1@example.com", region_id)

    _login(client, "cust1@example.com")
    resp = _create_order(client, region_id, service_id, material_id=str(material_id))
    assert "Подобрано исполнителей: 1".encode() in resp.data

    with client.application.app_context():
        order = Order.query.first()
        assert order is not None
        assert len(order.matches) == 1
        executor_user = User.query.filter_by(email="exec1@example.com").first()
        notif = Notification.query.filter_by(user_id=executor_user.id, type="new_order_match").first()
        assert notif is not None


def test_dashboard_shows_all_open_orders_with_recommended_badge(client):
    region_id = _setup_customer(client, "cust6@example.com")
    service_id, material_id = _setup_executor(client, "matched@example.com", region_id)

    _login(client, "cust6@example.com")
    resp = _create_order(client, region_id, service_id, material_id=str(material_id))
    assert "Подобрано исполнителей: 1".encode() in resp.data
    client.get("/auth/logout")

    # исполнитель без заполненного профиля тоже должен видеть эту заявку в общей ленте,
    # просто без пометки «Рекомендуем»
    badge_html = '<span class="badge badge--ok">Рекомендуем</span>'
    register(client, email="bystander@example.com", role="executor")
    resp = client.get("/dashboard")
    assert "Токарная обточка вала".encode() in resp.data
    assert badge_html.encode() not in resp.data
    client.get("/auth/logout")

    _login(client, "matched@example.com")
    resp = client.get("/dashboard")
    assert "Токарная обточка вала".encode() in resp.data
    assert badge_html.encode() in resp.data


def test_order_payment_methods_saved_and_displayed(client):
    region_id = _setup_customer(client, "custpm@example.com")
    with client.application.app_context():
        service_id = ServiceCategory.query.first().id

    _login(client, "custpm@example.com")
    _create_order(client, region_id, service_id, payment_methods=["cash", "click"])

    with client.application.app_context():
        order = Order.query.first()
        assert order.payment_methods == "cash,click"
        order_id = order.id

    resp = client.get(f"/orders/{order_id}")
    assert "Наличные".encode() in resp.data
    assert "Click".encode() in resp.data


def test_order_excludes_executor_without_service_match(client):
    region_id = _setup_customer(client, "cust2@example.com")
    # исполнитель без техвозможностей вообще (не завершал онбординг)
    register(client, email="exec2@example.com", role="executor")
    client.get("/auth/logout")

    _login(client, "cust2@example.com")
    with client.application.app_context():
        service_id = ServiceCategory.query.first().id
    resp = _create_order(client, region_id, service_id)
    assert "Подходящих исполнителей пока не нашлось".encode() in resp.data


def test_unmatched_executor_still_gets_plain_broadcast_notification(client):
    """Лента открыта всем (см. executor_dashboard) — значит и уведомление о
    новой заявке должен получить каждый исполнитель, просто без пометки
    «Рекомендуем», которая идёт только тем, кого выбрал автоподбор."""
    region_id = _setup_customer(client, "cust7@example.com")
    service_id, material_id = _setup_executor(client, "matched2@example.com", region_id)

    register(client, "unmatched@example.com", role="executor")
    with client.application.app_context():
        unmatched_id = User.query.filter_by(email="unmatched@example.com").first().id
    client.get("/auth/logout")

    _login(client, "cust7@example.com")
    _create_order(client, region_id, service_id, material_id=str(material_id))

    with client.application.app_context():
        matched_notif = Notification.query.filter_by(type="new_order_match").first()
        assert matched_notif is not None
        assert "Рекомендуем" in matched_notif.title

        broadcast_notif = Notification.query.filter_by(user_id=unmatched_id, type="new_order_broadcast").first()
        assert broadcast_notif is not None
        assert "Рекомендуем" not in broadcast_notif.title


def test_new_executor_profile_matches_already_open_orders(client):
    """run_matching() при публикации заказа матчит только уже существующих
    подходящих исполнителей. Если исполнитель заполнил профиль ПОЗЖЕ, чем
    заказ уже опубликован, он не должен остаться незамеченным навсегда —
    завершение профиля должно подобрать ему уже открытые заказы задним числом."""
    region_id = _setup_customer(client, "cust3@example.com")
    with client.application.app_context():
        service_id = ServiceCategory.query.first().id
        material_id = Material.query.first().id

    _login(client, "cust3@example.com")
    resp = _create_order(client, region_id, service_id, material_id=str(material_id))
    assert "Подходящих исполнителей пока не нашлось".encode() in resp.data
    client.get("/auth/logout")

    register(client, email="exec3@example.com", role="executor")
    with client.application.app_context():
        equipment_type_id = EquipmentType.query.first().id
    client.post(
        "/profile/executor",
        data={
            "org_type": "tsekh", "display_name": "Цех exec3@example.com", "region_id": str(region_id),
            "address_text": "рядом", "latitude": "41.31", "longitude": "69.26", "service_radius_km": "200",
        },
        follow_redirects=True,
    )
    client.post(
        "/profile/executor/equipment/add",
        data={"equipment_type_id": str(equipment_type_id), "quantity": "1"},
        follow_redirects=True,
    )
    resp = client.post(
        "/profile/executor/capabilities",
        data={
            "max_length_mm": "5000", "max_diameter_mm": "1000", "max_weight_kg": "2000",
            "service_category_ids": [str(service_id)], "material_ids": [str(material_id)],
        },
        follow_redirects=True,
    )
    assert "Подобрано уже открытых заказов: 1".encode() in resp.data

    with client.application.app_context():
        order = Order.query.first()
        assert len(order.matches) == 1


def test_order_excludes_executor_outside_service_radius(client):
    region_id = _setup_customer(client, "cust3@example.com")
    service_id, _ = _setup_executor(client, "exec3@example.com", region_id, radius_km=1)
    # исполнитель в 1 км радиусе, но координаты заказа далеко (другая точка)
    _login(client, "cust3@example.com")
    resp = _create_order(client, region_id, service_id, latitude="55.75", longitude="37.61")  # Москва, для примера расстояния
    assert "Подходящих исполнителей пока не нашлось".encode() in resp.data


def test_full_bid_and_assignment_flow(client):
    region_id = _setup_customer(client, "cust4@example.com")
    service_id, _ = _setup_executor(client, "execa@example.com", region_id)
    _setup_executor(client, "execb@example.com", region_id)

    _login(client, "cust4@example.com")
    _create_order(client, region_id, service_id)
    with client.application.app_context():
        order_id = Order.query.first().id
    client.get("/auth/logout")

    _login(client, "execa@example.com")
    resp = client.post(
        f"/orders/{order_id}/bid",
        data={"price": "500000", "currency": "UZS", "lead_time_days": "5", "comment": "Сделаем быстро"},
        follow_redirects=True,
    )
    assert "Ставка отправлена".encode() in resp.data
    client.get("/auth/logout")

    _login(client, "execb@example.com")
    resp = client.post(
        f"/orders/{order_id}/bid",
        data={"price": "400000", "currency": "UZS", "lead_time_days": "4"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    client.get("/auth/logout")

    with client.application.app_context():
        execA_user = User.query.filter_by(email="execa@example.com").first()
        outbid_notif = Notification.query.filter_by(user_id=execA_user.id, type="outbid").first()
        assert outbid_notif is not None, "execA должен получить уведомление, что его обошли по цене"

    _login(client, "cust4@example.com")
    with client.application.app_context():
        order = Order.query.get(order_id)
        winning_bid = [b for b in order.bids if b.executor.user.email == "execb@example.com"][0]
        bid_id = winning_bid.id

    resp = client.post(f"/orders/{order_id}/assign/{bid_id}", follow_redirects=True)
    assert "Исполнитель выбран".encode() in resp.data

    with client.application.app_context():
        order = Order.query.get(order_id)
        assert order.status == "assigned"
        assert order.assignment.bid_id == bid_id
        losing_bid = [b for b in order.bids if b.id != bid_id][0]
        assert losing_bid.status == "rejected"
    client.get("/auth/logout")

    _login(client, "execb@example.com")
    resp = client.post(f"/orders/{order_id}/start", follow_redirects=True)
    assert "в работе".encode() in resp.data
    client.get("/auth/logout")

    _login(client, "cust4@example.com")
    resp = client.post(f"/orders/{order_id}/complete", follow_redirects=True)
    assert "завершён".encode() in resp.data
    with client.application.app_context():
        order = Order.query.get(order_id)
        assert order.status == "completed"


def test_customer_can_cancel_accidental_assignment(client):
    """Случайный клик по «Выбрать» не должен быть необратимым, пока
    исполнитель ещё не начал работу — заказчику нужна кнопка «Отменить»."""
    region_id = _setup_customer(client, "cust8@example.com")
    service_id, _ = _setup_executor(client, "execx@example.com", region_id)
    _setup_executor(client, "execy@example.com", region_id)

    _login(client, "cust8@example.com")
    _create_order(client, region_id, service_id)
    with client.application.app_context():
        order_id = Order.query.first().id
    client.get("/auth/logout")

    _login(client, "execx@example.com")
    client.post(
        f"/orders/{order_id}/bid",
        data={"price": "500000", "currency": "UZS", "lead_time_days": "5"},
        follow_redirects=True,
    )
    client.get("/auth/logout")

    _login(client, "execy@example.com")
    client.post(
        f"/orders/{order_id}/bid",
        data={"price": "400000", "currency": "UZS", "lead_time_days": "4"},
        follow_redirects=True,
    )
    client.get("/auth/logout")

    _login(client, "cust8@example.com")
    with client.application.app_context():
        order = Order.query.get(order_id)
        bid_id = order.bids[0].id
    client.post(f"/orders/{order_id}/assign/{bid_id}", follow_redirects=True)

    resp = client.post(f"/orders/{order_id}/cancel-assignment", follow_redirects=True)
    assert "Выбор исполнителя отменён".encode() in resp.data

    with client.application.app_context():
        order = Order.query.get(order_id)
        assert order.status == "published"
        assert order.assignment is None
        assert all(b.status == "active" for b in order.bids)

    # можно выбрать заново
    resp = client.post(f"/orders/{order_id}/assign/{bid_id}", follow_redirects=True)
    assert "Исполнитель выбран".encode() in resp.data


def test_cannot_cancel_assignment_after_work_started(client):
    region_id = _setup_customer(client, "cust9@example.com")
    service_id, _ = _setup_executor(client, "execz@example.com", region_id)

    _login(client, "cust9@example.com")
    _create_order(client, region_id, service_id)
    with client.application.app_context():
        order_id = Order.query.first().id
    client.get("/auth/logout")

    _login(client, "execz@example.com")
    client.post(
        f"/orders/{order_id}/bid",
        data={"price": "500000", "currency": "UZS", "lead_time_days": "5"},
        follow_redirects=True,
    )
    client.get("/auth/logout")

    _login(client, "cust9@example.com")
    with client.application.app_context():
        bid_id = Order.query.get(order_id).bids[0].id
    client.post(f"/orders/{order_id}/assign/{bid_id}", follow_redirects=True)
    client.get("/auth/logout")

    _login(client, "execz@example.com")
    client.post(f"/orders/{order_id}/start", follow_redirects=True)
    client.get("/auth/logout")

    _login(client, "cust9@example.com")
    resp = client.post(f"/orders/{order_id}/cancel-assignment", follow_redirects=True)
    assert "уже нельзя".encode() in resp.data
    with client.application.app_context():
        assert Order.query.get(order_id).status == "in_progress"


def test_any_executor_can_view_order_but_needs_complete_profile_to_bid(client):
    """Лента заказов открытая: любой исполнитель может открыть любую заявку
    (не только «рекомендованную» подбором) — но чтобы делать ставки, профиль
    всё равно должен быть полностью заполнен (см. чек-лист /profile/executor)."""
    region_id = _setup_customer(client, "cust5@example.com")
    service_id, _ = _setup_executor(client, "execC@example.com", region_id)
    _login(client, "cust5@example.com")
    _create_order(client, region_id, service_id)
    with client.application.app_context():
        order_id = Order.query.first().id
    client.get("/auth/logout")

    register(client, email="outsider@example.com", role="executor")
    resp = client.get(f"/orders/{order_id}")
    assert resp.status_code == 200

    resp = client.post(
        f"/orders/{order_id}/bid",
        data={"price": "100000", "currency": "UZS", "lead_time_days": "3"},
        follow_redirects=True,
    )
    assert "полностью заполните профиль".encode() in resp.data
    with client.application.app_context():
        assert Bid.query.filter_by(order_id=order_id).count() == 0


def test_customer_can_attach_file_to_order_and_download_it(client):
    """Заявка может быть нестандартной (не всё описывается формой), поэтому
    заказчику даём приложить произвольный файл (PDF/архив), не только
    фото/чертёж-картинку — хранится на диске сервера, не через ImgBB."""
    region_id = _setup_customer(client, "filecust@example.com")
    with client.application.app_context():
        service_id = ServiceCategory.query.first().id

    _login(client, "filecust@example.com")
    _create_order(
        client, region_id, service_id, title="Заявка с файлом",
        attachment=(io.BytesIO(b"%PDF-1.4 fake pdf content"), "chertezh.pdf"),
    )

    with client.application.app_context():
        order = Order.query.filter_by(title="Заявка с файлом").first()
        media = OrderMedia.query.filter_by(order_id=order.id, media_type="file").first()
        assert media is not None
        download_url = media.file_url

    resp = client.get(download_url)
    assert resp.status_code == 200
    assert resp.data == b"%PDF-1.4 fake pdf content"
    assert "chertezh.pdf" in resp.headers.get("Content-Disposition", "")


def test_order_attachment_rejects_disallowed_extension(client):
    region_id = _setup_customer(client, "badfile@example.com")
    with client.application.app_context():
        service_id = ServiceCategory.query.first().id

    _login(client, "badfile@example.com")
    resp = _create_order(
        client, region_id, service_id, title="Заявка с плохим файлом",
        attachment=(io.BytesIO(b"MZ fake exe"), "virus.exe"),
    )
    assert "Недопустимый тип файла".encode() in resp.data
    with client.application.app_context():
        order = Order.query.filter_by(title="Заявка с плохим файлом").first()
        assert order is not None
        assert OrderMedia.query.filter_by(order_id=order.id, media_type="file").first() is None


def test_order_attachment_download_forbidden_for_unrelated_customer(client):
    region_id = _setup_customer(client, "ownercust@example.com")
    with client.application.app_context():
        service_id = ServiceCategory.query.first().id

    _login(client, "ownercust@example.com")
    _create_order(
        client, region_id, service_id, title="Приватная заявка с файлом",
        attachment=(io.BytesIO(b"file bytes"), "spec.pdf"),
    )
    client.get("/auth/logout")

    with client.application.app_context():
        order = Order.query.filter_by(title="Приватная заявка с файлом").first()
        media = OrderMedia.query.filter_by(order_id=order.id, media_type="file").first()
        download_url = media.file_url

    _setup_customer(client, "strangercust@example.com")
    _login(client, "strangercust@example.com")
    resp = client.get(download_url)
    assert resp.status_code == 403
