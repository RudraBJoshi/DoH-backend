from flask import Blueprint, jsonify
from flask_restful import Api, Resource
from flask_login import current_user
from datetime import datetime, timedelta

presence_api = Blueprint('presence_api', __name__, url_prefix='/api')
_api = Api(presence_api)

# In-memory store: {user_id: {'uid': str, 'last_seen': datetime}}
_presence = {}
ACTIVE_WINDOW_SEC = 300  # 5 minutes


class Heartbeat(Resource):
    def post(self):
        if not current_user.is_authenticated:
            return {'error': 'Unauthorized'}, 401
        _presence[current_user.id] = {
            'uid': current_user._uid,
            'last_seen': datetime.utcnow()
        }
        return {'status': 'ok'}, 200


class ActiveUsers(Resource):
    def get(self):
        if not current_user.is_authenticated:
            return {'error': 'Unauthorized'}, 401
        cutoff = datetime.utcnow() - timedelta(seconds=ACTIVE_WINDOW_SEC)
        active = [
            {'uid': data['uid']}
            for uid_key, data in _presence.items()
            if data['last_seen'] >= cutoff and uid_key != current_user.id
        ]
        return active, 200


_api.add_resource(Heartbeat, '/heartbeat')
_api.add_resource(ActiveUsers, '/active-users')
