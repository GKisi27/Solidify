from sqlalchemy import Column, String, Text, ForeignKey, JSON, Integer, Enum
import enum
from sqlalchemy.orm import relationship
from app.core.database import Base

class HistoryType(str, enum.Enum):
    convert_to_3d = "convert_to_3d"
    cost_estimation = "cost_estimation"

class History(Base):
    __tablename__ = "history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    type = Column(Enum(HistoryType, native_enum=False, length=50), nullable=False)  
    filename = Column(String, nullable=False)
    doc_url = Column(String, nullable=True)
    image_base64 = Column(Text, nullable=False)                 
    gemini_data = Column(JSON, nullable=True)
    converted_data = Column(JSON, nullable=True)

    user = relationship("User", back_populates="histories")
