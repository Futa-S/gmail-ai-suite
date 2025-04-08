from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from api.database import Base

class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, index=True)
    sentence = Column(String, nullable=False)
    difficulty = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
