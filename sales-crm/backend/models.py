from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Float,
    ForeignKey, Enum, Boolean, Table
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from database import Base


# ── Enums ──────────────────────────────────────────────────────────────────────

class LeadStatus(str, enum.Enum):
    NEW = "new"
    CONTACTED = "contacted"
    QUALIFIED = "qualified"
    UNQUALIFIED = "unqualified"
    CONVERTED = "converted"

class SalesCycleStage(str, enum.Enum):
    PROSPECTING    = "prospecting"
    QUALIFICATION  = "qualification"
    NEEDS_ANALYSIS = "needs_analysis"
    VALUE_PROP     = "value_proposition"
    PROPOSAL       = "proposal"
    NEGOTIATION    = "negotiation"
    CLOSED_WON     = "closed_won"
    CLOSED_LOST    = "closed_lost"

class ProjectStatus(str, enum.Enum):
    ACTIVE   = "active"
    ON_HOLD  = "on_hold"
    CLOSED   = "closed"
    PROSPECT = "prospect"


# ── Association tables ─────────────────────────────────────────────────────────

contact_account_assoc = Table(
    "contact_account",
    Base.metadata,
    Column("contact_id", Integer, ForeignKey("contacts.id")),
    Column("account_id", Integer, ForeignKey("accounts.id")),
)

contact_project_assoc = Table(
    "contact_project",
    Base.metadata,
    Column("contact_id", Integer, ForeignKey("contacts.id")),
    Column("project_id", Integer, ForeignKey("projects.id")),
)

stakeholder_project_assoc = Table(
    "stakeholder_project",
    Base.metadata,
    Column("stakeholder_id", Integer, ForeignKey("stakeholders.id")),
    Column("project_id", Integer, ForeignKey("projects.id")),
)


# ── Core Models ────────────────────────────────────────────────────────────────

class Account(Base):
    __tablename__ = "accounts"

    id          = Column(Integer, primary_key=True, index=True)
    name        = Column(String(255), nullable=False, index=True)
    domain      = Column(String(255), index=True)
    industry    = Column(String(100))
    website     = Column(String(500))
    phone       = Column(String(50))
    address     = Column(Text)
    revenue     = Column(Float)
    employees   = Column(Integer)
    notes       = Column(Text)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())
    updated_at  = Column(DateTime(timezone=True), onupdate=func.now())

    contacts    = relationship("Contact", secondary=contact_account_assoc, back_populates="accounts")
    projects    = relationship("Project", back_populates="account")
    leads       = relationship("Lead", back_populates="account")


class Contact(Base):
    __tablename__ = "contacts"

    id             = Column(Integer, primary_key=True, index=True)
    first_name     = Column(String(100), nullable=False)
    last_name      = Column(String(100))
    email          = Column(String(255), unique=True, index=True)
    phone          = Column(String(50))
    job_title      = Column(String(255))
    department     = Column(String(100))
    linkedin_url   = Column(String(500))
    linkedin_data  = Column(Text)   # JSON blob from scrape
    notes          = Column(Text)
    created_at     = Column(DateTime(timezone=True), server_default=func.now())
    updated_at     = Column(DateTime(timezone=True), onupdate=func.now())

    accounts       = relationship("Account", secondary=contact_account_assoc, back_populates="contacts")
    projects       = relationship("Project", secondary=contact_project_assoc, back_populates="contacts")
    leads          = relationship("Lead", back_populates="contact")
    email_threads  = relationship("EmailThread", back_populates="contact")
    stakeholder    = relationship("Stakeholder", back_populates="contact", uselist=False)


class Lead(Base):
    __tablename__ = "leads"

    id          = Column(Integer, primary_key=True, index=True)
    title       = Column(String(255), nullable=False)
    first_name  = Column(String(100))
    last_name   = Column(String(100))
    email       = Column(String(255), index=True)
    phone       = Column(String(50))
    company     = Column(String(255))
    source      = Column(String(100))           # email / linkedin / manual / web
    status      = Column(Enum(LeadStatus), default=LeadStatus.NEW)
    score       = Column(Integer, default=0)    # 0-100
    notes       = Column(Text)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())
    updated_at  = Column(DateTime(timezone=True), onupdate=func.now())

    contact_id  = Column(Integer, ForeignKey("contacts.id"), nullable=True)
    account_id  = Column(Integer, ForeignKey("accounts.id"), nullable=True)

    contact     = relationship("Contact", back_populates="leads")
    account     = relationship("Account", back_populates="leads")
    project     = relationship("Project", back_populates="lead", uselist=False)


class Project(Base):
    __tablename__ = "projects"

    id           = Column(Integer, primary_key=True, index=True)
    name         = Column(String(255), nullable=False)
    description  = Column(Text)
    status       = Column(Enum(ProjectStatus), default=ProjectStatus.PROSPECT)
    value        = Column(Float)
    currency     = Column(String(10), default="USD")
    close_date   = Column(DateTime(timezone=True))
    created_at   = Column(DateTime(timezone=True), server_default=func.now())
    updated_at   = Column(DateTime(timezone=True), onupdate=func.now())

    account_id   = Column(Integer, ForeignKey("accounts.id"), nullable=True)
    lead_id      = Column(Integer, ForeignKey("leads.id"), nullable=True)

    account      = relationship("Account", back_populates="projects")
    lead         = relationship("Lead", back_populates="project")
    contacts     = relationship("Contact", secondary=contact_project_assoc, back_populates="projects")
    stakeholders = relationship("Stakeholder", secondary=stakeholder_project_assoc, back_populates="projects")
    sales_cycle  = relationship("SalesCycle", back_populates="project", uselist=False)
    email_threads = relationship("EmailThread", back_populates="project")


class Stakeholder(Base):
    __tablename__ = "stakeholders"

    id              = Column(Integer, primary_key=True, index=True)
    name            = Column(String(255), nullable=False)
    role            = Column(String(100))       # decision-maker / influencer / user / champion
    email           = Column(String(255), index=True)
    linkedin_url    = Column(String(500))
    linkedin_data   = Column(Text)              # JSON scraped profile
    influence_level = Column(String(50))        # high / medium / low
    sentiment       = Column(String(50))        # positive / neutral / negative
    notes           = Column(Text)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())
    updated_at      = Column(DateTime(timezone=True), onupdate=func.now())

    contact_id      = Column(Integer, ForeignKey("contacts.id"), nullable=True)
    contact         = relationship("Contact", back_populates="stakeholder")
    projects        = relationship("Project", secondary=stakeholder_project_assoc, back_populates="stakeholders")


class SalesCycle(Base):
    __tablename__ = "sales_cycles"

    id           = Column(Integer, primary_key=True, index=True)
    stage        = Column(Enum(SalesCycleStage), default=SalesCycleStage.PROSPECTING)
    probability  = Column(Float, default=0.0)   # 0-100
    next_action  = Column(Text)
    next_action_date = Column(DateTime(timezone=True))
    notes        = Column(Text)
    created_at   = Column(DateTime(timezone=True), server_default=func.now())
    updated_at   = Column(DateTime(timezone=True), onupdate=func.now())

    project_id   = Column(Integer, ForeignKey("projects.id"), unique=True)
    project      = relationship("Project", back_populates="sales_cycle")
    activities   = relationship("Activity", back_populates="sales_cycle")


class Activity(Base):
    __tablename__ = "activities"

    id              = Column(Integer, primary_key=True, index=True)
    type            = Column(String(50))   # email / call / meeting / note / stage_change
    title           = Column(String(255))
    description     = Column(Text)
    from_stage      = Column(String(50), nullable=True)
    to_stage        = Column(String(50), nullable=True)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())

    sales_cycle_id  = Column(Integer, ForeignKey("sales_cycles.id"))
    sales_cycle     = relationship("SalesCycle", back_populates="activities")


class EmailThread(Base):
    __tablename__ = "email_threads"

    id           = Column(Integer, primary_key=True, index=True)
    subject      = Column(String(500))
    from_email   = Column(String(255))
    to_emails    = Column(Text)      # comma-separated
    cc_emails    = Column(Text)
    body         = Column(Text)
    received_at  = Column(DateTime(timezone=True))
    raw_headers  = Column(Text)
    parsed_data  = Column(Text)      # JSON: extracted entities
    created_at   = Column(DateTime(timezone=True), server_default=func.now())

    contact_id   = Column(Integer, ForeignKey("contacts.id"), nullable=True)
    project_id   = Column(Integer, ForeignKey("projects.id"), nullable=True)

    contact      = relationship("Contact", back_populates="email_threads")
    project      = relationship("Project", back_populates="email_threads")
