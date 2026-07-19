import uuid
from sqlalchemy import Column, String, Float, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

def generate_uuid():
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=generate_uuid, index=True)
    username = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)

    # Relationship to items added by this user
    items = relationship("InventoryItem", back_populates="added_by")

class InventoryItem(Base):
    __tablename__ = "inventory_items"

    id = Column(String, primary_key=True, default=generate_uuid, index=True)
    name = Column(String, nullable=False, index=True)
    date = Column(String, nullable=False)  # Format: YYYY-MM-DD
    type = Column(String, nullable=False, index=True)  # e.g., Gem, Mineral
    weight = Column(String, nullable=False)  # e.g., "1.5 ct", "10.2g"
    cost = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    photo_name = Column(String, nullable=True)
    custom_id = Column(String, nullable=True)

    # Ownership association
    added_by_id = Column(String, ForeignKey("users.id"), nullable=False)
    added_by = relationship("User", back_populates="items")
