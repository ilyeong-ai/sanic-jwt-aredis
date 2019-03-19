from sanic_jwt import Initialize
from aredis import StrictRedis
from users import authenticate
from user_routes import (
    LogInAndOut,
    Register,
    NameClaim,
    store_refresh_token,
    retrieve_refresh_token,
    retrieve_user,
    me_me_me,
)
from idea_routes import update_idea, create_idea, delete_idea, get_ideas
import config


def config_app():
    #
    # DB
    #
    from dbhelper import do_engine

    do_engine()

    #
    # REDIS (refresh_token cache)
    #
    config.redis_client = StrictRedis(host="127.0.0.1", port=6379, db=0)

    #
    # sanic_jwt configuration & setup
    #
    config.app.config.user_id = "email"
    my_views = (("users", Register), ("access-tokens", LogInAndOut))
    custom_claims = [NameClaim]
    Initialize(
        config.app,
        authenticate=authenticate,
        class_views=my_views,
        refresh_token_enabled=True,
        store_refresh_token=store_refresh_token,
        retrieve_refresh_token=retrieve_refresh_token,
        access_token_name="jwt",
        custom_claims=custom_claims,
        debug=True,
        path_to_retrieve_user="/me2",  # little hacky
        user_id="email",
        expiration_delta=60 * 10,
        url_prefix="",
        authorization_header="X-Access-Token",  # FYI - this is not the standard implementation
        authorization_header_prefix="",
        retrieve_user=retrieve_user,
        path_to_refresh="/access-tokens/refresh",
    )

    #
    # register Idea routes
    #
    config.app.add_route(update_idea, "/ideas/<id>", methods=["PUT"])
    config.app.add_route(delete_idea, "/ideas/<id>", methods=["DELETE"])
    config.app.add_route(create_idea, "/ideas", methods=["POST"])
    config.app.add_route(get_ideas, "/ideas", methods=["GET"])
    config.app.add_route(me_me_me, "/me", methods=["GET"])


if __name__ == "__main__":

    #
    # Get Ready!
    #
    config_app()

    #
    # Run Lola, Run!
    #
    config.app.run(host="0.0.0.0", port=8000)
