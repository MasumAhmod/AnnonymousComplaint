from sqlalchemy import Column, Integer, String, Text, Enum, ForeignKey, TIMESTAMP, func
from sqlalchemy.orm import relationship

from backend.database import Base


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(150), nullable=False)
    authority_email = Column(String(255), nullable=False)

    complaints = relationship("Complaint", back_populates="category")


class Complaint(Base):
    __tablename__ = "complaints"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    tracking_id = Column(String(20), unique=True, nullable=False, index=True)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False, index=True)
    description = Column(Text, nullable=False)
    status = Column(
        Enum("Pending", "Working on it", "Solved", name="complaint_status"),
        nullable=False,
        default="Pending",
        server_default="Pending"
    )
    created_at = Column(
        TIMESTAMP,
        nullable=True,
        server_default=func.current_timestamp()
    )
    updated_at = Column(
        TIMESTAMP,
        nullable=True,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp()
    )

    category = relationship("Category", back_populates="complaints")