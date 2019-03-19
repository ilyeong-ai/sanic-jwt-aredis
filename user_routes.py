from sanic import response
from sanic.exceptions import (
    InvalidUsage,
    Forbidden,
    Unauthorized,
    add_status_code,
    SanicException,
)
from sanic_jwt import BaseEndpoint, Claim
from sanic_jwt.decorators import protected
from users import UserSchema, User, authenticate, UserLoginSchema
from jwt import decode, ExpiredSignatureError
import config


# my own extension for being HTTP compliant
@add_status_code(409)
class Conflict(SanicException):
    pass


async def store_refresh_token(user_id, refresh_token, *args, **kwargs):
    await config.redis_client.set(
        f"user_id{user_id}", refresh_token
    )  # no TTL for this basic implementation
    assert await config.redis_client.exists(f"user_id{user_id}") is True


async def delete_refresh_token(user_id, refresh_token, *args, **kwargs):
    key = f"user_id{user_id}"
    if await config.redis_client.exists(key):
        token = await config.redis_client.get(key)
        if token == refresh_token.encode("utf-8"):
            await config.redis_client.delete(key)


async def retrieve_refresh_token(request, user_id, *args, **kwargs):
    found_token = await config.redis_client.get(f"user_id{user_id}")
    return found_token


async def retrieve_user(request, payload, *args, **kwargs):
    if payload:
        email = payload.get("email", None)
        user = User.get_by_email(email)
        return user
    else:
        return None


class NameClaim(Claim):
    key = "name"

    def setup(self, payload, user):
        return user.name

    def verify(self, value):
        return True if value is not None else False


class Register(BaseEndpoint):
    async def post(self, request, *args, **kwargs):
        if request.json is not None:
            user, errors = UserSchema().load(request.json)
            if errors is not None and len(errors) > 0:
                raise InvalidUsage(errors)
            else:
                if not user.exists():
                    user.register()

                    jwt, output = await self.responses.get_access_token_output(
                        request, user, self.config, self.instance
                    )

                    refresh_token = await self.instance.auth.generate_refresh_token(
                        request, user
                    )
                    output.update({self.config.refresh_token_name: refresh_token})

                else:
                    raise Conflict("User already exists")
        else:
            raise InvalidUsage("Missing JSON body")

        return response.json({"jwt": jwt, "refresh_token": refresh_token}, status=201)


# sanic_jwt out-of-the-box me implementation wraps the JSON data for some reason,
# so had to write my own version (might contribute to sanic_jwt later)
@protected()
async def me_me_me(request, *args, **kwargs):
    jwt_token = request.headers.get(config.app.auth.config.authorization_header(), None)
    decoded = decode(
        jwt_token,
        config.app.auth.config.secret(),
        algorithms=config.app.auth.config.algorithm(),
    )
    if decoded is None or "name" not in decoded:
        raise Unauthorized("malformed token")

    user = User.get_by_email(decoded["email"])
    if user is None:
        raise Forbidden("malformed token")
    return response.json(UserSchema().dump(user).data)


class LogInAndOut(BaseEndpoint):
    async def post(self, request, *args, **kwargs):
        if request.json is not None:
            user, errors = UserLoginSchema().load(request.json)
            if errors is not None and len(errors) > 0:
                raise InvalidUsage(errors)
            else:
                if user.exists():
                    clear_password = user.cleartext_passowrd
                    user = user.get_by_email(user.email)
                    if not user.password_matched(clear_password):
                        raise Unauthorized(
                            "You are not allowed into the secret garden!"
                        )

                    jwt, output = await self.responses.get_access_token_output(
                        request, user, self.config, self.instance
                    )

                    refresh_token = await self.instance.auth.generate_refresh_token(
                        request, user
                    )
                    output.update({self.config.refresh_token_name: refresh_token})

                else:
                    raise InvalidUsage("User do not exists")
        else:
            raise InvalidUsage("Missing JSON body")

        return response.json({"jwt": jwt, "refresh_token": refresh_token}, status=201)

    # feels a bit like hacking the sanic_jwt, it makes sense to implement in
    # cookie's setup less headers.
    async def delete(self, request, *args, **kwargs):
        jwt_token = request.headers.get(
            config.app.auth.config.authorization_header(), None
        )
        if jwt_token is None:
            raise Forbidden("missing authentication")
        if request.json is None or "refresh_token" not in request.json:
            raise Forbidden("missing refresh_token")
        try:
            decoded = decode(
                jwt_token,
                config.app.auth.config.secret(),
                algorithms=config.app.auth.config.algorithm(),
            )
        except ExpiredSignatureError:
            raise Forbidden("token expired")

        if decoded is None or "name" not in decoded:
            raise Forbidden("malformed token")

        user = User.get_by_email(decoded["email"])
        if user is None:
            raise Forbidden("malformed token")

        await delete_refresh_token(user.email, request.json["refresh_token"])

        return response.json(None, status=204)
