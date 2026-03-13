from flask import Blueprint, request, g
from flask_restful import Api, Resource
from api.authorize import token_required
from model.game import Game
from __init__ import db

game_api = Blueprint('game_api', __name__, url_prefix='/api/game')
api = Api(game_api)


class GameAPI:
    class _Save(Resource):
        @token_required()
        def post(self):
            """Save (or overwrite) the authenticated user's game."""
            user = g.current_user
            body = request.get_json(silent=True)
            if not body or 'game_data' not in body:
                return {'message': 'game_data is required'}, 400

            import json
            # Accept either a string or a dict for game_data
            raw = body['game_data']
            game_data_str = raw if isinstance(raw, str) else json.dumps(raw)

            record = Game.query.filter_by(user_id=user.id).first()
            if record:
                record.game_data = game_data_str
                from datetime import datetime
                record.updated_at = datetime.utcnow()
                record.save()
            else:
                record = Game(user_id=user.id, game_data=game_data_str)
                record.create()

            return {'message': 'Game saved', 'updated_at': record.updated_at.isoformat()}, 200

    class _Load(Resource):
        @token_required()
        def get(self):
            """Load the authenticated user's saved game."""
            user = g.current_user
            record = Game.query.filter_by(user_id=user.id).first()
            if not record:
                return {'message': 'No saved game found'}, 404
            return {'game_data': record.game_data,
                    'updated_at': record.updated_at.isoformat() if record.updated_at else None}, 200


api.add_resource(GameAPI._Save, '/save')
api.add_resource(GameAPI._Load, '/load')
