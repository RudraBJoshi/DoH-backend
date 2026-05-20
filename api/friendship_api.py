from flask import Blueprint, request, g
from flask_restful import Api, Resource
from sqlalchemy.exc import IntegrityError

from __init__ import db
from model.friendship import FriendRequest
from api.authorize import auth_required

friendship_api = Blueprint('friendship_api', __name__, url_prefix='/api/friend')
_api = Api(friendship_api)


class SendRequest(Resource):
    """POST /api/friend/request  {to_uid, to_name}"""
    @auth_required()
    def post(self):
        me = g.current_user
        body = request.get_json(silent=True) or {}
        to_uid  = str(body.get('to_uid',  '')).strip()
        to_name = str(body.get('to_name', '')).strip() or to_uid
        if not to_uid:
            return {'error': 'to_uid required'}, 400
        if to_uid == str(me._uid):
            return {'error': 'Cannot friend yourself'}, 400

        existing = FriendRequest.query.filter(
            ((FriendRequest.from_uid == str(me._uid)) & (FriendRequest.to_uid == to_uid)) |
            ((FriendRequest.from_uid == to_uid) & (FriendRequest.to_uid == str(me._uid)))
        ).first()
        if existing and existing.status == 'accepted':
            return {'error': 'Already friends'}, 409
        if existing and existing.status == 'pending':
            return {'error': 'Request already pending'}, 409

        req = FriendRequest(
            from_uid=str(me._uid),
            from_name=str(me._uid),
            to_uid=to_uid,
            to_name=to_name,
        )
        db.session.add(req)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            return {'error': 'Request already exists'}, 409
        return req.read(), 201


class IncomingRequests(Resource):
    """GET /api/friend/requests  — pending requests sent TO me"""
    @auth_required()
    def get(self):
        me = g.current_user
        reqs = FriendRequest.query.filter_by(
            to_uid=str(me._uid), status='pending'
        ).order_by(FriendRequest.created_at.desc()).all()
        return [r.read() for r in reqs], 200


class AcceptRequest(Resource):
    """POST /api/friend/accept  {request_id}"""
    @auth_required()
    def post(self):
        me = g.current_user
        body = request.get_json(silent=True) or {}
        req_id = body.get('request_id')
        req = FriendRequest.query.get(req_id)
        if not req or req.to_uid != str(me._uid):
            return {'error': 'Not found'}, 404
        req.status = 'accepted'
        db.session.commit()
        return req.read(), 200


class DeclineRequest(Resource):
    """POST /api/friend/decline  {request_id}"""
    @auth_required()
    def post(self):
        me = g.current_user
        body = request.get_json(silent=True) or {}
        req_id = body.get('request_id')
        req = FriendRequest.query.get(req_id)
        if not req or req.to_uid != str(me._uid):
            return {'error': 'Not found'}, 404
        req.status = 'declined'
        db.session.commit()
        return {'status': 'declined'}, 200


class FriendsList(Resource):
    """GET /api/friend/list  — all accepted friends"""
    @auth_required()
    def get(self):
        me = str(g.current_user._uid)
        rows = FriendRequest.query.filter(
            FriendRequest.status == 'accepted',
            (FriendRequest.from_uid == me) | (FriendRequest.to_uid == me)
        ).all()
        friends = []
        for r in rows:
            if r.from_uid == me:
                friends.append({'uid': r.to_uid})
            else:
                friends.append({'uid': r.from_uid})
        return friends, 200


_api.add_resource(SendRequest,      '/request')
_api.add_resource(IncomingRequests, '/requests')
_api.add_resource(AcceptRequest,    '/accept')
_api.add_resource(DeclineRequest,   '/decline')
_api.add_resource(FriendsList,      '/list')
