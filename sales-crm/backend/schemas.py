from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional, List
from datetime import datetime
from models import LeadStatus, SalesCycleStage, ProjectStatus


# ── Account ────────────────────────────────────────────────────────────────────

class AccountBase(BaseModel):
    name: str
    domain: Optional[str] = None
    industry: Optional[str] = None
    website: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    revenue: Optional[float] = None
    employees: Optional[int] = None
    notes: Optional[str] = None

class AccountCreate(AccountBase):
    pass

class AccountUpdate(AccountBase):
    name: Optional[str] = None

class AccountOut(AccountBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    class Config:
        from_attributes = True


# ── Contact ────────────────────────────────────────────────────────────────────

class ContactBase(BaseModel):
    first_name: str
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    job_title: Optional[str] = None
    department: Optional[str] = None
    linkedin_url: Optional[str] = None
    notes: Optional[str] = None

class ContactCreate(ContactBase):
    account_ids: Optional[List[int]] = []

class ContactUpdate(ContactBase):
    first_name: Optional[str] = None
    account_ids: Optional[List[int]] = None

class ContactOut(ContactBase):
    id: int
    linkedin_data: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    class Config:
        from_attributes = True


# ── Lead ───────────────────────────────────────────────────────────────────────

class LeadBase(BaseModel):
    title: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    source: Optional[str] = None
    status: Optional[LeadStatus] = LeadStatus.NEW
    score: Optional[int] = 0
    notes: Optional[str] = None

class LeadCreate(LeadBase):
    contact_id: Optional[int] = None
    account_id: Optional[int] = None

class LeadUpdate(LeadBase):
    title: Optional[str] = None
    status: Optional[LeadStatus] = None
    contact_id: Optional[int] = None
    account_id: Optional[int] = None

class LeadOut(LeadBase):
    id: int
    contact_id: Optional[int] = None
    account_id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    class Config:
        from_attributes = True


# ── Project ────────────────────────────────────────────────────────────────────

class ProjectBase(BaseModel):
    name: str
    description: Optional[str] = None
    status: Optional[ProjectStatus] = ProjectStatus.PROSPECT
    value: Optional[float] = None
    currency: Optional[str] = "USD"
    close_date: Optional[datetime] = None

class ProjectCreate(ProjectBase):
    account_id: Optional[int] = None
    lead_id: Optional[int] = None
    contact_ids: Optional[List[int]] = []

class ProjectUpdate(ProjectBase):
    name: Optional[str] = None
    account_id: Optional[int] = None
    lead_id: Optional[int] = None
    contact_ids: Optional[List[int]] = None

class ProjectOut(ProjectBase):
    id: int
    account_id: Optional[int] = None
    lead_id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    class Config:
        from_attributes = True


# ── Stakeholder ────────────────────────────────────────────────────────────────

class StakeholderBase(BaseModel):
    name: str
    role: Optional[str] = None
    email: Optional[str] = None
    linkedin_url: Optional[str] = None
    influence_level: Optional[str] = None
    sentiment: Optional[str] = None
    notes: Optional[str] = None

class StakeholderCreate(StakeholderBase):
    contact_id: Optional[int] = None
    account_id: Optional[int] = None
    lead_id: Optional[int] = None
    project_ids: Optional[List[int]] = []

class StakeholderUpdate(StakeholderBase):
    name: Optional[str] = None
    contact_id: Optional[int] = None
    account_id: Optional[int] = None
    lead_id: Optional[int] = None
    project_ids: Optional[List[int]] = None

class StakeholderOut(StakeholderBase):
    id: int
    linkedin_data: Optional[str] = None
    contact_id: Optional[int] = None
    account_id: Optional[int] = None
    lead_id: Optional[int] = None
    ai_summary: Optional[str] = None
    approach_recommendation: Optional[str] = None
    buying_signals: Optional[str] = None   # JSON list stored as text
    ai_enriched_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    class Config:
        from_attributes = True


# ── Sales Cycle ────────────────────────────────────────────────────────────────

class SalesCycleBase(BaseModel):
    stage: Optional[SalesCycleStage] = SalesCycleStage.PROSPECTING
    probability: Optional[float] = 0.0
    next_action: Optional[str] = None
    next_action_date: Optional[datetime] = None
    notes: Optional[str] = None

class SalesCycleCreate(SalesCycleBase):
    project_id: int

class SalesCycleUpdate(SalesCycleBase):
    stage: Optional[SalesCycleStage] = None

class SalesCycleOut(SalesCycleBase):
    id: int
    project_id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    class Config:
        from_attributes = True


# ── Activity ───────────────────────────────────────────────────────────────────

class ActivityOut(BaseModel):
    id: int
    type: Optional[str]
    title: Optional[str]
    description: Optional[str]
    from_stage: Optional[str]
    to_stage: Optional[str]
    created_at: Optional[datetime]
    sales_cycle_id: int
    class Config:
        from_attributes = True


# ── Email Thread ───────────────────────────────────────────────────────────────

class EmailThreadCreate(BaseModel):
    subject: Optional[str] = None
    from_email: str
    to_emails: Optional[str] = None
    cc_emails: Optional[str] = None
    body: Optional[str] = None
    received_at: Optional[datetime] = None
    raw_headers: Optional[str] = None

class EmailThreadOut(BaseModel):
    id: int
    subject: Optional[str]
    from_email: str
    to_emails: Optional[str]
    cc_emails: Optional[str]
    body: Optional[str]
    received_at: Optional[datetime]
    parsed_data: Optional[str]
    contact_id: Optional[int]
    project_id: Optional[int]
    created_at: Optional[datetime]
    class Config:
        from_attributes = True


# ── LinkedIn scrape request ────────────────────────────────────────────────────

class LinkedInScrapeRequest(BaseModel):
    linkedin_url: str
    entity_type: str   # "contact" | "stakeholder"
    entity_id: int


# ── Stage advance request ─────────────────────────────────────────────────────

class StageAdvanceRequest(BaseModel):
    new_stage: SalesCycleStage
    notes: Optional[str] = None
