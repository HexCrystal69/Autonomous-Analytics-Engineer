import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Uuid
from sqlalchemy.orm import relationship, synonym
from datetime import datetime
from src.database import Base

class DatasetCatalog(Base):
    __tablename__ = "dataset_catalogs"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    dataset_id = Column(Uuid, ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False)
    data_owner = Column(String, nullable=True)
    sensitivity_level = Column(String, default="PUBLIC", nullable=False) # PUBLIC, INTERNAL, RESTRICTED, CONFIDENTIAL
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    columns = relationship("ColumnCatalog", back_populates="catalog", cascade="all, delete-orphan")

from sqlalchemy.ext.hybrid import hybrid_property

class ColumnCatalog(Base):
    __tablename__ = "column_catalogs"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    dataset_catalog_id = Column(Uuid, ForeignKey("dataset_catalogs.id", ondelete="CASCADE"), nullable=False)
    column_name = Column(String, nullable=False)
    inferred_semantic_type = Column(String, default="QUANTITY", nullable=False) # IDENTIFIER, PII, FINANCIAL, GEOGRAPHY, TEMPORAL, QUANTITY
    pii_classification = Column(String, default="NONE", nullable=False) # NONE, EMAIL, PHONE, NAME, ADDRESS, IP
    business_meaning = Column(String, nullable=True)

    catalog = relationship("DatasetCatalog", back_populates="columns")

    @hybrid_property
    def semantic_type(self):
        return self.inferred_semantic_type

    @semantic_type.setter
    def semantic_type(self, value):
        self.inferred_semantic_type = value

    def __init__(self, **kwargs):
        if "semantic_type" in kwargs:
            kwargs["inferred_semantic_type"] = kwargs.pop("semantic_type")
        super().__init__(**kwargs)




class BusinessGlossary(Base):
    __tablename__ = "business_glossaries"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    term = Column(String, unique=True, nullable=False)
    description = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
