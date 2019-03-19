from decimal import Decimal
from statistics import mean
from marshmallow import Schema, fields, post_load, validate
from sqlalchemy.sql import text
import secrets
import dbhelper
import datetime
import time


class Idea(object):
    def __init__(
        self,
        content,
        impact,
        ease,
        confidence,
        idea_id=None,
        modified_at=None,
        created_at=None,
    ):

        self.content = content
        self.impact = impact
        self.ease = ease
        self.confidence = confidence
        self.average_score = round(
            Decimal(mean([self.impact, self.ease, self.confidence])), 1
        )
        self.id = idea_id
        self.modified_at = modified_at
        self.created_at = created_at

    def exists(self):
        s = text("SELECT * FROM ideas WHERE id = :id")
        connection = dbhelper.engine.connect()

        rc = False if connection.execute(s, id=self.id).fetchone() is None else True
        connection.close()
        return rc

    def save(self):
        self.id = secrets.token_urlsafe(8)
        while self.exists():
            self.id = secrets.token_urlsafe(8)

        connection = dbhelper.engine.connect()
        trans = connection.begin()
        try:
            s = text(
                "INSERT INTO ideas(id, content, impact, ease, confidence) "
                "VALUES(:id, :content, :impact, :ease, :confidence)"
            )
            connection.execute(
                s,
                id=self.id,
                content=self.content,
                impact=self.impact,
                ease=self.ease,
                confidence=self.confidence,
            )
            trans.commit()
        except:
            trans.rollback()
            raise
        connection.close()

        return self.id

    def update(self):
        connection = dbhelper.engine.connect()
        trans = connection.begin()
        self.modified_at = datetime.datetime.now().timestamp()
        try:
            s = text(
                "UPDATE ideas "
                "SET content=:content, impact=:impact, ease=:ease, confidence=:confidence, modified_at=:modified_at "
                "WHERE id=:id"
            )
            connection.execute(
                s,
                id=self.id,
                content=self.content,
                impact=self.impact,
                ease=self.ease,
                confidence=self.confidence,
                modified_at=self.modified_at,
            )
            trans.commit()
        except:
            trans.rollback()
            raise
        connection.close()

    def delete(self):
        connection = dbhelper.engine.connect()
        trans = connection.begin()
        self.modified_at = datetime.datetime.now().timestamp()
        try:
            s = text("DELETE FROM ideas WHERE id=:id")
            connection.execute(s, id=self.id)
            trans.commit()
        except:
            trans.rollback()
            raise
        connection.close()

    @classmethod
    def load_by_id(cls, idea_id):
        s = text(
            "SELECT id, content ,impact, ease, confidence, created_at  "
            "FROM ideas WHERE id = :id"
        )
        connection = dbhelper.engine.connect()
        rc = connection.execute(s, id=idea_id).fetchone()
        if rc is not None:
            stamp = datetime.datetime.strptime(rc[5], "%Y-%m-%d %H:%M:%S")
            created_at = time.mktime(stamp.timetuple())
            rc = Idea(rc[1], rc[2], rc[3], rc[4], idea_id=rc[0], created_at=created_at)

        connection.close()
        return rc

    @classmethod
    def load_by_page(cls, page):

        s = text(
            "SELECT id, content ,impact, ease, confidence, created_at  "
            "FROM ideas ORDER BY (impact + ease + confidence)/3 desc LIMIT 10 OFFSET :offset"
        )
        connection = dbhelper.engine.connect()
        q_result = connection.execute(s, offset=10 * (page - 1)).fetchall()

        rc = []
        if q_result is not None:
            for row in q_result:
                stamp = datetime.datetime.strptime(row[5], "%Y-%m-%d %H:%M:%S")
                created_at = time.mktime(stamp.timetuple())
                rc.append(
                    Idea(
                        row[1],
                        row[2],
                        row[3],
                        row[4],
                        idea_id=row[0],
                        created_at=created_at,
                    )
                )

        return rc


class IdeaSchema(Schema):
    content = fields.Str(required=True, validate=[validate.Length(max=255, min=1)])
    impact = fields.Integer(required=True, validate=[validate.Range(min=1, max=10)])
    ease = fields.Integer(required=True, validate=[validate.Range(min=1, max=10)])
    confidence = fields.Integer(required=True, validate=[validate.Range(min=1, max=10)])
    id = fields.Str(dump_only=True)
    average_score = fields.Float(dump_only=True)
    created_at = fields.Integer(dump_only=True)

    @post_load
    def make_idea(self, data):
        return Idea(**data)
