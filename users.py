from marshmallow import (
    Schema,
    fields,
    post_load,
    validate,
    validates_schema,
    ValidationError,
)
from sqlalchemy.sql import text
import bcrypt
import dbhelper
from libgravatar import Gravatar

from sanic_jwt import exceptions


async def authenticate(request, *args, **kwargs):
    email = request.json.get("email", None)
    password = request.json.get("password", None)

    if not email or not password:
        raise exceptions.AuthenticationFailed("Missing username or password.")

    user = User.get_by_email(email)
    if user is None:
        raise exceptions.AuthenticationFailed("User not found.")

    if not user.password_matched(password):
        raise exceptions.AuthenticationFailed("Password is incorrect.")

    return user


class User(object):
    def __init__(self, name, email, password, *args, **kwargs):
        self.name = name
        self.email = email
        self.cleartext_passowrd = password
        self.hashed_password = bcrypt.hashpw(
            self.cleartext_passowrd.encode("utf-8"), bcrypt.gensalt()
        )

        for key, value in kwargs.items():
            self.key = value

    def to_dict(self):
        g = Gravatar(self.email)
        return {"email": self.email, "name": self.name, "avatar_url": g.get_image()}

    @classmethod
    def email_exists(cls, email):
        s = text("SELECT * FROM users WHERE email = :email AND expire_date is null")
        connection = dbhelper.engine.connect()

        rc = False if connection.execute(s, email=email).fetchone() is None else True
        connection.close()
        return rc

    def exists(self):
        s = text("SELECT * FROM users WHERE email = :email AND expire_date is null")
        connection = dbhelper.engine.connect()

        rc = (
            False
            if connection.execute(s, email=self.email).fetchone() is None
            else True
        )
        connection.close()
        return rc

    def password_matched(self, cleartext_password):
        newp = bcrypt.hashpw(
            cleartext_password.encode("utf-8"), self.cleartext_passowrd.encode("utf-8")
        )
        return self.cleartext_passowrd.encode("utf-8") == newp

    def register(self):
        connection = dbhelper.engine.connect()
        trans = connection.begin()
        try:
            s = text(
                "INSERT INTO users(name, email, hashed_password) VALUES(:name, :email, :password)"
            )
            connection.execute(
                s, email=self.email, name=self.name, password=self.hashed_password
            )
            trans.commit()
        except:
            trans.rollback()
            raise
        connection.close()

    @classmethod
    def get_by_email(cls, email):
        s = text(
            "SELECT name, email,hashed_password FROM users WHERE email = :email AND expire_date is null"
        )
        connection = dbhelper.engine.connect()
        rc = connection.execute(s, email=email).fetchone()
        if rc is not None:
            rc = User(rc[0], rc[1], rc[2].decode("utf-8"))

        connection.close()
        return rc


class UserSchema(Schema):
    name = fields.Str(required=True)
    email = fields.Email(required=True)
    password = fields.Str(
        required=True, load_only=True, validate=[validate.Length(min=8)]
    )

    @validates_schema
    def validate_password(self, data):
        if (
            data is not None
            and "password" in data
            and (
                not any(char.isdigit() for char in data["password"])
                or not any(char.islower() for char in data["password"])
                or not any(char.isupper() for char in data["password"])
            )
        ):
            raise ValidationError("password does not comply with basic requirements")

    @post_load
    def make_user(self, data):
        return User(**data)


class UserLoginSchema(Schema):
    email = fields.Email(required=True)
    password = fields.Str(required=True, load_only=True)

    @post_load
    def make_user(self, data):
        data["name"] = None
        return User(**data)
