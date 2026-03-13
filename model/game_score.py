from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from datetime import datetime
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from __init__ import db


class GameScore(db.Model):
    """Leaderboard entry: one row per player per game (best score kept)."""
    __tablename__ = 'game_scores'

    id         = Column(Integer, primary_key=True)
    game_id    = Column(Integer, ForeignKey('games.id', ondelete='CASCADE'), nullable=False)
    user_id    = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    score      = Column(Integer, nullable=False, default=0)   # stars collected
    levels_completed = Column(Integer, nullable=False, default=0)
    played_at  = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id':               self.id,
            'game_id':          self.game_id,
            'user_id':          self.user_id,
            'score':            self.score,
            'levels_completed': self.levels_completed,
            'played_at':        self.played_at.isoformat() if self.played_at else None,
        }

    def create(self):
        try:
            db.session.add(self)
            db.session.commit()
            return self
        except Exception:
            db.session.rollback()
            return None

    def save(self):
        try:
            db.session.commit()
            return self
        except Exception:
            db.session.rollback()
            return None

    def delete(self):
        try:
            db.session.delete(self)
            db.session.commit()
            return True
        except Exception:
            db.session.rollback()
            return False
