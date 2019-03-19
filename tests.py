import pytest
from sanic import Sanic
import random
import json
from main import config_app
import config
from users import User

test_email = None
jwt = None
refresh_token = None


@pytest.yield_fixture
def app():
    config.app = Sanic("test_sanic_app")
    config_app()
    yield config.app


@pytest.fixture
def test_cli(loop, app, sanic_client):

    global test_email
    while test_email is None:
        i = random.randint(1, 10000)
        test_email = f"amichay.oren+{i}@gmail.com"
        if User.email_exists(test_email):
            test_email = None

    print(f"testing w/ email {test_email}")

    return loop.run_until_complete(sanic_client(app))


async def test_positive_register_(test_cli):
    data = {"email": test_email, "name": "me me me", "password": "testing123G"}
    resp = await test_cli.post("/users", data=json.dumps(data))
    resp_json = await resp.json()
    global jwt
    jwt = resp_json["jwt"]
    global refresh_token
    refresh_token = resp_json["refresh_token"]
    assert jwt is not None
    assert refresh_token is not None
    assert resp.status == 201


async def test_positive_login(test_cli):
    data = {"email": test_email, "password": "testing123G"}
    resp = await test_cli.post("/access-tokens", data=json.dumps(data))
    resp_json = await resp.json()
    global jwt
    jwt = resp_json["jwt"]
    global refresh_token
    refresh_token = resp_json["refresh_token"]
    assert jwt is not None
    assert refresh_token is not None
    assert resp.status == 201


async def test_negative_login_bad_password(test_cli):
    data = {"email": test_email, "password": "test123G"}
    resp = await test_cli.post("/access-tokens", data=json.dumps(data))
    assert resp.status == 401


async def test_negative_registeration_of_existing_user(test_cli):
    data = {"email": test_email, "name": "me me me", "password": "testing123G"}
    resp = await test_cli.post("/users", data=json.dumps(data))
    assert resp.status == 409


async def test_negative_registeration_missing_parameter(test_cli):
    data = {"email": test_email, "password": "testing123G"}
    resp = await test_cli.post("/users", data=json.dumps(data))
    assert resp.status == 400


async def test_positive_refresh_token(test_cli):
    global jwt
    global refresh_token
    data = {"refresh_token": refresh_token}
    headers = {"X-Access-Token": jwt}
    resp = await test_cli.post(
        "/access-tokens/refresh", headers=headers, data=json.dumps(data)
    )
    resp_json = await resp.json()
    jwt = resp_json["jwt"]
    assert jwt is not None
    assert resp.status == 200


async def test_positive_logout(test_cli):
    global jwt
    global refresh_token
    data = {"refresh_token": refresh_token}
    headers = {"X-Access-Token": jwt}
    resp = await test_cli.delete(
        "/access-tokens", headers=headers, data=json.dumps(data)
    )
    assert resp.status == 204


async def test_positive_logout_when_already_logout(test_cli):
    global jwt
    global refresh_token
    data = {"refresh_token": refresh_token}
    headers = {"X-Access-Token": jwt}
    resp = await test_cli.delete(
        "/access-tokens", headers=headers, data=json.dumps(data)
    )
    assert resp.status == 204


async def test_negative_refresh_token_missing_header(test_cli):
    global jwt
    global refresh_token
    data = {"refresh_token": refresh_token}
    resp = await test_cli.post("/access-tokens/refresh", data=json.dumps(data))
    assert resp.status == 400


async def test_negative_refresh_token_bad_refresh_token(test_cli):
    global jwt
    global refresh_token
    data = {"refresh_token": "1111"}
    headers = {"X-Access-Token": jwt}
    resp = await test_cli.post(
        "/access-tokens/refresh", headers=headers, data=json.dumps(data)
    )
    assert resp.status == 401


async def test_negative_logout_then_try_refresh(test_cli):
    # logout
    global jwt
    global refresh_token
    data = {"refresh_token": refresh_token}
    headers = {"X-Access-Token": jwt}
    await test_cli.delete("/access-tokens", headers=headers, data=json.dumps(data))

    # refresh
    data = {"refresh_token": refresh_token}
    headers = {"X-Access-Token": jwt}
    resp = await test_cli.post(
        "/access-tokens/refresh", headers=headers, data=json.dumps(data)
    )
    assert resp.status == 401


async def test_positive_me(test_cli):
    global jwt
    headers = {"X-Access-Token": jwt}
    resp = await test_cli.get("/me", headers=headers)
    assert resp.status == 200

    resp_json = await resp.json()

    assert resp_json["name"] == "me me me"
    assert resp_json["email"] == test_email


async def test_negative_me_missing_authentication(test_cli):
    global jwt
    resp = await test_cli.get("/me")
    assert resp.status == 400


async def exclude_test_negative_refresh_after_expire(test_cli):
    import asyncio

    # sleep for 11 minutes
    await asyncio.sleep(60 * 11)

    global jwt
    global refresh_token
    data = {"refresh_token": refresh_token}
    headers = {"X-Access-Token": jwt}
    resp = await test_cli.post(
        "/access-tokens/refresh", headers=headers, data=json.dumps(data)
    )
    assert resp.status == 401
