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
            """Save (upsert by name) a named game for the authenticated user."""
            user = g.current_user
            body = request.get_json(silent=True)
            if not body or 'game_data' not in body:
                return {'message': 'game_data is required'}, 400
            name = (body.get('name') or '').strip()
            if not name:
                return {'message': 'Game name is required'}, 400

            import json
            raw = body['game_data']
            game_data_str = raw if isinstance(raw, str) else json.dumps(raw)

            # If a game with this name already belongs to the user, overwrite it
            record = Game.query.filter_by(user_id=user.id, name=name).first()
            if record:
                record.game_data = game_data_str
                from datetime import datetime
                record.updated_at = datetime.utcnow()
                record.save()
            else:
                record = Game(user_id=user.id, name=name, game_data=game_data_str)
                record.create()

            return {'message': 'Game saved', 'id': record.id,
                    'updated_at': record.updated_at.isoformat()}, 200

    class _List(Resource):
        @token_required()
        def get(self):
            """Return all saved games for the authenticated user (no game_data, just metadata)."""
            user = g.current_user
            records = (Game.query
                       .filter_by(user_id=user.id)
                       .order_by(Game.updated_at.desc())
                       .all())
            return {'games': [
                {'id': r.id, 'name': r.name,
                 'updated_at': r.updated_at.isoformat() if r.updated_at else None}
                for r in records
            ]}, 200

    class _Load(Resource):
        @token_required()
        def get(self, game_id):
            """Load a specific game by id (must belong to the authenticated user)."""
            user = g.current_user
            record = Game.query.filter_by(id=game_id, user_id=user.id).first()
            if not record:
                return {'message': 'Game not found'}, 404
            return {'id': record.id, 'name': record.name,
                    'game_data': record.game_data,
                    'updated_at': record.updated_at.isoformat() if record.updated_at else None}, 200

    class _Delete(Resource):
        @token_required()
        def delete(self, game_id):
            """Delete a specific game by id (must belong to the authenticated user)."""
            user = g.current_user
            record = Game.query.filter_by(id=game_id, user_id=user.id).first()
            if not record:
                return {'message': 'Game not found'}, 404
            record.delete()
            return {'message': 'Game deleted'}, 200


api.add_resource(GameAPI._Save,   '/save')
api.add_resource(GameAPI._List,   '/list')
api.add_resource(GameAPI._Load,   '/load/<int:game_id>')
api.add_resource(GameAPI._Delete, '/delete/<int:game_id>')
