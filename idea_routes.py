from sanic import response
from sanic_jwt.decorators import protected
from sanic_jwt import BaseEndpoint
from sanic.exceptions import InvalidUsage
from ideas import IdeaSchema, Idea


@protected()
async def create_idea(request, *args, **kwargs):
    if request.json is not None:
        idea, errors = IdeaSchema().load(request.json)
        if errors is not None and len(errors) > 0:
            raise InvalidUsage(errors)
        else:
            id = idea.save()
            idea = Idea.load_by_id(id)
    else:
        raise InvalidUsage("Missing JSON body")

    return response.json(IdeaSchema().dump(idea).data, status=201)


@protected()
async def update_idea(request, id, *args, **kwargs):
    if request.json is not None:
        idea, errors = IdeaSchema().load(request.json)
        if errors is not None and len(errors) > 0:
            raise InvalidUsage(errors)
        else:
            idea.id = id

            if not idea.exists():
                raise InvalidUsage("idea does not exist")
            idea.update()
            idea = Idea.load_by_id(id)
    else:
        raise InvalidUsage("Missing JSON body")

    return response.json(IdeaSchema().dump(idea).data, status=200)


@protected()
async def delete_idea(request, id, *args, **kwargs):
    idea = Idea.load_by_id(id)

    if idea is not None:
        idea.delete()

    return response.json(None, status=204)


@protected()
async def get_ideas(request, *args, **kwargs):
    rc = []
    if (
        request.args is not None
        and "page" in request.args
        and int(request.args["page"][0]) > 0
    ):
        page = int(request.args["page"][0])
        ideas = Idea.load_by_page(page)
        rc = [IdeaSchema().dump(idea).data for idea in ideas]

    return response.json(rc, status=200)
