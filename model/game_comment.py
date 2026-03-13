from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text
from datetime import datetime
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from __init__ import db


class GameComment(db.Model):
    """A comment left on a shared game."""
    __tablename__ = 'game_comments'

    id        = Column(Integer, primary_key=True)
    game_id   = Column(Integer, ForeignKey('games.id', ondelete='CASCADE'), nullable=False)
    user_id   = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    body      = Column(Text, nullable=False)
    posted_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id':        self.id,
            'game_id':   self.game_id,
            'user_id':   self.user_id,
            'body':      self.body,
            'posted_at': self.posted_at.isoformat() if self.posted_at else None,
        }

    def create(self):
        try:
            db.session.add(self)
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
