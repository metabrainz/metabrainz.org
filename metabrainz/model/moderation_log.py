
from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, Text, func
from sqlalchemy.orm import relationship
from sqlalchemy.orm.attributes import Mapped

from metabrainz.model import db


class ModerationLog(db.Model):
    __tablename__ = "moderation_log"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    moderator_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    action = Column(Enum("block", "unblock", "comment", "verify_email", "delete", "edit_username", name="moderation_action_type"), nullable=False)
    reason = Column(Text(), nullable=False)
    timestamp = Column(DateTime(timezone=True), default=func.now())

    user: Mapped["User"] = relationship("User", foreign_keys=[user_id], back_populates="moderation_logs")
    moderator: Mapped["User"] = relationship("User", foreign_keys=[moderator_id], back_populates="moderator_actions")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "moderator_id": self.moderator_id,
            "moderator_name": self.moderator.name,
            "action": self.action,
            "reason": self.reason,
            "timestamp": self.timestamp.isoformat()
        }
