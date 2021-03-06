from tassaron_flask_template.main import create_app, init_app
from tassaron_flask_template.main.plugins import db
from tassaron_flask_template.shop.inventory_models import Product, ProductCategory
import tempfile
import os
from flask import json, jsonify
import pytest


@pytest.fixture
def client():
    app = create_app()
    db_fd, db_path = tempfile.mkstemp()
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite+pysqlite:///" + db_path
    app = init_app(app)
    with app.app_context():
        db.create_all()
        db.session.add(
            ProductCategory(
                name="Food",
            )
        )
        db.session.add(
            Product(
                name="Potato",
                price=1.0,
                description="Tuber from the ground",
                image="potato.jpg",
                stock=1,
                category_id=1,
            )
        )
        db.session.commit()
        client = app.test_client()
        yield client
    os.close(db_fd)
    os.unlink(db_path)


def test_add_to_cart_api_success(client):
    resp = client.post(
        "/cart/add",
        data=json.dumps({"id": 1, "quantity": 1}),
        content_type='application/json',
    )
    assert resp.status_code == 200
    data = json.loads(resp.get_data(as_text=True))
    assert data["success"] == True


def test_add_to_cart_api_nonexistent(client):
    resp = client.post(
        "/cart/add",
        data=json.dumps({"id": 2, "quantity": 1}),
        content_type='application/json',
    )
    assert resp.status_code == 200
    data = json.loads(resp.get_data(as_text=True))
    assert data["success"] == False


def test_add_to_cart_api_failed_outofstock(client):
    db.session.add(
        Product(
            name="Potato",
            price=1.0,
            description="Tuber from the ground",
            image="potato.jpg",
            stock=0,
            category_id=1,
        )
    )
    resp = client.post(
        "/cart/add",
        data=json.dumps({"id": 2, "quantity": 1}),
        content_type='application/json',
    )
    assert resp.status_code == 200
    data = json.loads(resp.get_data(as_text=True))
    assert data["success"] == False


def test_add_to_cart_api_baddata(client):
    resp = client.post(
        "/cart/add",
        data=json.dumps({"id": "a", "quantity": 1}),
        content_type='application/json',
    )
    assert resp.status_code == 400
    data = json.loads(resp.get_data(as_text=True))
    assert data["success"] == False
    resp = client.post(
        "/cart/add",
        data=json.dumps({"wrong": 1}),
        content_type='application/json',
    )
    assert resp.status_code == 400
    data = json.loads(resp.get_data(as_text=True))
    assert data["success"] == False