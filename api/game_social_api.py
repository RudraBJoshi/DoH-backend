from flask import Blueprint, request, g
from flask_restful import Api, Resource
from api.authorize import token_required
from model.game import Game
from model.game_score import GameScore
from model.game_comment import GameComment
from model.user import User
from __init__ import db

game_social_api = Blueprint('game_social_api', __name__, url_prefix='/api/game')
api = Api(game_social_api)


class GameSocialAPI:

    # ── Leaderboard ────────────────────────────────────────────────────────────

    class _ScoreSubmit(Resource):
        @token_required()
        def post(self, game_id):
            """Submit a play score for a game. Keeps only the player's best score."""
            user = g.current_user
            body = request.get_json(silent=True) or {}
            score  = int(body.get('score', 0))
            levels = int(body.get('levels_completed', 0))

            # Only keep the best score per player per game
            existing = GameScore.query.filter_by(game_id=game_id, user_id=user.id).first()
            if existing:
                if score > existing.score:
                    existing.score            = score
                    existing.levels_completed = levels
                    from datetime import datetime
                    existing.played_at = datetime.utcnow()
                    existing.save()
                return {'message': 'Score recorded', 'best': existing.score}, 200
            else:
                entry = GameScore(game_id=game_id, user_id=user.id,
                                  score=score, levels_completed=levels)
                entry.create()
                return {'message': 'Score recorded', 'best': score}, 200

    class _Leaderboard(Resource):
        def get(self, game_id):
            """Top 10 scores for a game (public, no auth needed)."""
            rows = (GameScore.query
                    .filter_by(game_id=game_id)
                    .order_by(GameScore.score.desc())
                    .limit(10).all())
            results = []
            for r in rows:
                user = User.query.get(r.user_id)
                results.append({
                    'rank':             len(results) + 1,
                    'player':           user.name if user else 'Unknown',
                    'score':            r.score,
                    'levels_completed': r.levels_completed,
                    'played_at':        r.played_at.isoformat() if r.played_at else None,
                })
            return {'leaderboard': results}, 200

    # ── Comments ───────────────────────────────────────────────────────────────

    class _CommentList(Resource):
        def get(self, game_id):
            """Get all comments for a game (public)."""
            comments = (GameComment.query
                        .filter_by(game_id=game_id)
                        .order_by(GameComment.posted_at.desc())
                        .all())
            results = []
            for c in comments:
                user = User.query.get(c.user_id)
                results.append({
                    'id':        c.id,
                    'player':    user.name if user else 'Unknown',
                    'body':      c.body,
                    'posted_at': c.posted_at.isoformat() if c.posted_at else None,
                })
            return {'comments': results}, 200

        @token_required()
        def post(self, game_id):
            """Post a comment on a game."""
            user = g.current_user
            body = (request.get_json(silent=True) or {}).get('body', '').strip()
            if not body:
                return {'message': 'Comment body is required'}, 400
            if len(body) > 500:
                return {'message': 'Comment must be 500 characters or fewer'}, 400
            comment = GameComment(game_id=game_id, user_id=user.id, body=body)
            comment.create()
            return {'message': 'Comment posted', 'id': comment.id}, 201

    class _CommentDelete(Resource):
        @token_required()
        def delete(self, game_id, comment_id):
            """Delete your own comment."""
            user = g.current_user
            comment = GameComment.query.filter_by(id=comment_id, game_id=game_id).first()
            if not comment:
                return {'message': 'Comment not found'}, 404
            if comment.user_id != user.id and getattr(user, 'role', '') != 'Admin':
                return {'message': 'Not your comment'}, 403
            comment.delete()
            return {'message': 'Comment deleted'}, 200


api.add_resource(GameSocialAPI._ScoreSubmit,  '/score/<int:game_id>')
api.add_resource(GameSocialAPI._Leaderboard,  '/leaderboard/<int:game_id>')
api.add_resource(GameSocialAPI._CommentList,  '/comments/<int:game_id>')
api.add_resource(GameSocialAPI._CommentDelete, '/comments/<int:game_id>/<int:comment_id>')
