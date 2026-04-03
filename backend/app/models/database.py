from sqlalchemy import (
    Column, Integer, BigInteger, String, Float, Text, DateTime, ForeignKey,
    Index, func,
)
from sqlalchemy.orm import DeclarativeBase, relationship
from pgvector.sqlalchemy import Vector


class Base(DeclarativeBase):
    pass


class STE(Base):
    """Standard Trade Entity -- catalog item."""
    __tablename__ = "ste"

    id = Column(BigInteger, primary_key=True)
    name = Column(Text, nullable=False, index=True)
    category = Column(String(512), index=True)
    attributes = Column(Text)
    name_normalized = Column(Text)
    embedding = Column(Vector(312))
    popularity_score = Column(Float, default=0.0)

    __table_args__ = (
        Index("ix_ste_embedding", "embedding", postgresql_using="ivfflat"),
    )


class Contract(Base):
    __tablename__ = "contracts"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    purchase_name = Column(Text)
    contract_id = Column(String(128), index=True)
    ste_id = Column(BigInteger, ForeignKey("ste.id"), index=True)
    contract_date = Column(DateTime)
    contract_cost = Column(Float)
    customer_inn = Column(String(20), index=True)
    customer_name = Column(Text)
    customer_region = Column(String(256))
    supplier_inn = Column(String(20))
    supplier_name = Column(Text)
    supplier_region = Column(String(256))

    ste = relationship("STE")


class UserProfile(Base):
    """Accumulated user preferences built from contract history + behavior."""
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_inn = Column(String(20), unique=True, nullable=False, index=True)
    customer_name = Column(Text)
    region = Column(String(256))
    preferred_categories = Column(Text)  # JSON list
    profile_vector = Column(Vector(312))
    total_contracts = Column(Integer, default=0)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class InteractionLog(Base):
    """Behavioral signals: clicks, views, bounces."""
    __tablename__ = "interaction_logs"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    customer_inn = Column(String(20), nullable=False, index=True)
    ste_id = Column(BigInteger, ForeignKey("ste.id"), index=True)
    query_text = Column(Text)
    action = Column(String(32), nullable=False)  # click, view, bounce, add_to_compare, purchase
    dwell_time_ms = Column(Integer)
    created_at = Column(DateTime, server_default=func.now())

    ste = relationship("STE")
