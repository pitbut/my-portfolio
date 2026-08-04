def test_add_review_to_sacred_source(client, app):
    with app.app_context():
        from app.models import SacredSource

        source_id = SacredSource.query.filter_by(slug="test-source").first().id

    resp = client.post(
        f"/reviews/sacred_source/{source_id}",
        data={"rating": "5", "body": "Прекрасное место.", "author_name": "Аня"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert "Прекрасное место.".encode() in resp.data
    assert "Аня".encode() in resp.data


def test_add_review_to_equipment(client, app):
    with app.app_context():
        from app.models import Equipment

        item_id = Equipment.query.filter_by(slug="test-filter").first().id

    resp = client.post(
        f"/reviews/equipment/{item_id}",
        data={"rating": "4", "body": "Хорошо фильтрует.", "author_name": ""},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert "Хорошо фильтрует.".encode() in resp.data
    assert "Аноним".encode() in resp.data


def test_review_requires_body(client, app):
    with app.app_context():
        from app.models import Equipment

        item_id = Equipment.query.filter_by(slug="test-filter").first().id

    resp = client.post(
        f"/reviews/equipment/{item_id}",
        data={"rating": "4", "body": ""},
        follow_redirects=True,
    )
    assert "Напишите текст отзыва".encode() in resp.data


def test_review_requires_valid_rating(client, app):
    with app.app_context():
        from app.models import Equipment

        item_id = Equipment.query.filter_by(slug="test-filter").first().id

    resp = client.post(
        f"/reviews/equipment/{item_id}",
        data={"rating": "9", "body": "Текст отзыва."},
        follow_redirects=True,
    )
    assert "Выберите оценку".encode() in resp.data

    with app.app_context():
        from app.models import Review

        assert Review.query.filter_by(target_type="equipment", target_id=item_id).count() == 0


def test_review_honeypot_blocks_silently(client, app):
    with app.app_context():
        from app.models import Equipment

        item_id = Equipment.query.filter_by(slug="test-filter").first().id

    resp = client.post(
        f"/reviews/equipment/{item_id}",
        data={"rating": "5", "body": "Спам-отзыв.", "website": "http://spam.example"},
        follow_redirects=True,
    )
    assert resp.status_code == 200

    with app.app_context():
        from app.models import Review

        assert Review.query.filter_by(target_type="equipment", target_id=item_id).count() == 0


def test_review_unknown_target_type_404(client):
    resp = client.post("/reviews/not_a_type/1", data={"rating": "5", "body": "test"})
    assert resp.status_code == 404


def test_review_unknown_target_id_404(client):
    resp = client.post("/reviews/equipment/999999", data={"rating": "5", "body": "test"})
    assert resp.status_code == 404


def test_average_rating_shown_on_detail_page(client, app):
    with app.app_context():
        from app.models import Equipment

        item_id = Equipment.query.filter_by(slug="test-filter").first().id

    client.post(f"/reviews/equipment/{item_id}", data={"rating": "4", "body": "Отзыв 1."})
    client.post(f"/reviews/equipment/{item_id}", data={"rating": "2", "body": "Отзыв 2."})

    resp = client.get("/equipment/test-filter")
    assert "3.0".encode() in resp.data
