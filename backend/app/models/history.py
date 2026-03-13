from sqlalchemy import Column, String, Text, ForeignKey, JSON, Integer
from sqlalchemy.orm import relationship
from app.core.database import Base

class History(Base):
    __tablename__ = "history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    filename = Column(String, nullable=False)
    image_base64 = Column(Text, nullable=False)
    gemini_data = Column(JSON, nullable=True)
    converted_data = Column(JSON, nullable=True)

    user = relationship("User", back_populates="histories")
