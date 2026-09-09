from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from backend.database.connection import Base

class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    company_name = Column(String, nullable=False)
    contact_name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    phone = Column(String, nullable=True)
    industry = Column(String, nullable=True)
    plan = Column(String, nullable=True)  # e.g., 'FREE', 'PRO', 'ENTERPRISE'
    status = Column(String, default="ACTIVE")  # 'ACTIVE', 'INACTIVE', 'SUSPENDED'
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)

    # Relationships
    users = relationship("User", back_populates="client", cascade="all, delete-orphan")
    datasets = relationship("Dataset", back_populates="client", cascade="all, delete-orphan")
    reports = relationship("Report", back_populates="client", cascade="all, delete-orphan")

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False)  # 'ADMIN', 'CLIENT'
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)

    # Relationships
    client = relationship("Client", back_populates="users")

class Dataset(Base):
    __tablename__ = "datasets"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    filename = Column(String, nullable=False)
    table_name = Column(String, unique=True, nullable=False)  # SQLite table name
    row_count = Column(Integer, default=0)
    col_count = Column(Integer, default=0)
    status = Column(String, default="ACTIVE")  # 'ACTIVE', 'ERROR'
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    client = relationship("Client", back_populates="datasets")
    reports = relationship("Report", back_populates="dataset", cascade="all, delete-orphan")

class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False)
    dataset_id = Column(Integer, ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    report_type = Column(String, nullable=False)  # 'PDF', 'CSV', 'HTML', etc.
    status = Column(String, default="COMPLETED")
    created_at = Column(DateTime, default=datetime.utcnow)
    content = Column(Text, nullable=True)  # Store JSON or markdown content

    # Relationships
    client = relationship("Client", back_populates="reports")
    dataset = relationship("Dataset", back_populates="reports")
