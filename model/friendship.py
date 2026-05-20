from datetime import datetime
from __init__ import db


class FriendRequest(db.Model):
    __tablename__ = 'friend_requests'

    id         = db.Column(db.Integer, primary_key=True)
    from_uid   = db.Column(db.String(255), nullable=False)
    from_name  = db.Column(db.String(255), nullable=False)
    to_uid     = db.Column(db.String(255), nullable=False)
    to_name    = db.Column(db.String(255), nullable=False)
    status     = db.Column(db.String(20), default='pending')  # pending | accepted | declined
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Prevent duplicate pending requests between the same pair
    __table_args__ = (
        db.UniqueConstraint('from_uid', 'to_uid', name='uq_friend_pair'),
    )

    def read(self):
        return {
            'id':        self.id,
            'from_uid':  self.from_uid,
            'from_name': self.from_name,
            'to_uid':    self.to_uid,
            'to_name':   self.to_name,
            'status':    self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
