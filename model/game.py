from sqlalchemy import Column, String, Integer, ForeignKey, Text, DateTime
from datetime import datetime
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from __init__ import db
from model.user import User


class Game(db.Model):
    __tablename__ = 'games'

    id         = Column(Integer, primary_key=True)
    user_id    = Column(Integer, ForeignKey('users.id'), unique=True, nullable=False)
    game_data  = Column(Text, nullable=False)           # full JSON blob
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __init__(self, user_id, game_data):
        self.user_id   = user_id
        self.game_data = game_data
        self.updated_at = datetime.utcnow()

    def to_dict(self):
        return {
            'user_id':    self.user_id,
            'game_data':  self.game_data,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
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
