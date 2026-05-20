from flask import Blueprint, g
from flask_restful import Api, Resource
from datetime import datetime, timedelta

from api.authorize import auth_required

presence_api = Blueprint('presence_api', __name__, url_prefix='/api')
_api = Api(presence_api)

# In-memory store: {user_id: {'uid': str, 'last_seen': datetime}}
_presence = {}
ACTIVE_WINDOW_SEC = 300  # 5 minutes


class Heartbeat(Resource):
    @auth_required()
    def post(self):
        u = g.current_user
        _presence[u.id] = {'uid': u._uid, 'last_seen': datetime.utcnow()}
        return {'status': 'ok'}, 200


class ActiveUsers(Resource):
    @auth_required()
    def get(self):
        cutoff = datetime.utcnow() - timedelta(seconds=ACTIVE_WINDOW_SEC)
        me = g.current_user.id
        active = [
            {'uid': data['uid']}
            for uid_key, data in _presence.items()
            if data['last_seen'] >= cutoff and uid_key != me
        ]
        return active, 200


_api.add_resource(Heartbeat, '/heartbeat')
_api.add_resource(ActiveUsers, '/active-users')
