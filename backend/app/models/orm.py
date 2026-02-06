from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey, JSON, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.session import Base


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default="student")  # student|teacher|admin
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # 关系
    qa_logs = relationship("QALog", back_populates="user")
    events = relationship("Event", back_populates="user")
    alerts = relationship("Alert", back_populates="user")


class Course(Base):
    __tablename__ = "courses"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # 关系
    documents = relationship("Document", back_populates="course")
    chunks = relationship("Chunk", back_populates="course")
    knowledge_points = relationship("KnowledgePoint", back_populates="course")
    qa_logs = relationship("QALog", back_populates="course")
    events = relationship("Event", back_populates="course")
    alerts = relationship("Alert", back_populates="course")


class Document(Base):
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    file_name = Column(String(255), nullable=False)
    file_type = Column(String(20), nullable=False)
    storage_path = Column(String(500), nullable=False)
    status = Column(String(20), nullable=False, default="uploaded")  # uploaded|processing|ready|failed
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # 关系
    course = relationship("Course", back_populates="documents")
    chunks = relationship("Chunk", back_populates="document")


class Chunk(Base):
    __tablename__ = "chunks"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    chunk_text = Column(Text, nullable=False)
    meta_json = Column(JSON)  # {section, page, offset, title_path...}
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # 关系
    document = relationship("Document", back_populates="chunks")
    course = relationship("Course", back_populates="chunks")


class KnowledgePoint(Base):
    __tablename__ = "knowledge_points"
    
    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    tags_json = Column(JSON)
    
    # 关系
    course = relationship("Course", back_populates="knowledge_points")
    src_relations = relationship("KPRelation", foreign_keys="KPRelation.src_kp_id", back_populates="src_kp")
    dst_relations = relationship("KPRelation", foreign_keys="KPRelation.dst_kp_id", back_populates="dst_kp")


class KPRelation(Base):
    __tablename__ = "kp_relations"
    
    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    src_kp_id = Column(Integer, ForeignKey("knowledge_points.id"), nullable=False)
    dst_kp_id = Column(Integer, ForeignKey("knowledge_points.id"), nullable=False)
    relation_type = Column(String(20), nullable=False)  # prerequisite|related|contrast|example_of
    weight = Column(Float, default=1.0)
    
    # 关系
    src_kp = relationship("KnowledgePoint", foreign_keys=[src_kp_id], back_populates="src_relations")
    dst_kp = relationship("KnowledgePoint", foreign_keys=[dst_kp_id], back_populates="dst_relations")


class QALog(Base):
    __tablename__ = "qa_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    citations_json = Column(JSON)
    confidence = Column(Float, nullable=False)
    rating = Column(Integer)  # 1=like, -1=dislike, null=no rating
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # 关系
    user = relationship("User", back_populates="qa_logs")
    course = relationship("Course", back_populates="qa_logs")


class Event(Base):
    __tablename__ = "events"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    event_type = Column(String(50), nullable=False)
    payload_json = Column(JSON)
    ts = Column(DateTime(timezone=True), server_default=func.now())
    
    # 关系
    user = relationship("User", back_populates="events")
    course = relationship("Course", back_populates="events")


class Alert(Base):
    __tablename__ = "alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    level = Column(String(10), nullable=False)  # low|medium|high
    reason = Column(String(200), nullable=False)
    evidence_json = Column(JSON)
    status = Column(String(10), nullable=False, default="open")  # open|ack|closed
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # 关系
    user = relationship("User", back_populates="alerts")
    course = relationship("Course", back_populates="alerts")


class IngestTask(Base):
    __tablename__ = "ingest_tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(String(50), unique=True, index=True, nullable=False)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    status = Column(String(20), nullable=False, default="queued")  # queued|processing|done|failed
    progress = Column(Float, default=0.0)
    error_message = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())