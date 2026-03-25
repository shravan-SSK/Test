from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from models import Account, Contact, Lead, Project, Stakeholder
from schemas import AccountCreate, AccountUpdate, AccountOut, ContactOut, LeadOut, ProjectOut, StakeholderOut

router = APIRouter(prefix="/accounts", tags=["Accounts"])


# ── CRUD ───────────────────────────────────────────────────────────────────────

@router.get("/", response_model=List[AccountOut])
def list_accounts(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(Account).offset(skip).limit(limit).all()


@router.post("/", response_model=AccountOut, status_code=201)
def create_account(payload: AccountCreate, db: Session = Depends(get_db)):
    account = Account(**payload.model_dump())
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


@router.get("/{account_id}", response_model=AccountOut)
def get_account(account_id: int, db: Session = Depends(get_db)):
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(404, "Account not found")
    return account


@router.put("/{account_id}", response_model=AccountOut)
def update_account(account_id: int, payload: AccountUpdate, db: Session = Depends(get_db)):
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(404, "Account not found")
    for k, v in payload.model_dump(exclude_none=True).items():
        setattr(account, k, v)
    db.commit()
    db.refresh(account)
    return account


@router.delete("/{account_id}", status_code=204)
def delete_account(account_id: int, db: Session = Depends(get_db)):
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(404, "Account not found")
    db.delete(account)
    db.commit()


# ── Relationship: list related entities ────────────────────────────────────────

@router.get("/{account_id}/contacts", response_model=List[ContactOut])
def get_account_contacts(account_id: int, db: Session = Depends(get_db)):
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(404, "Account not found")
    return account.contacts


@router.get("/{account_id}/leads", response_model=List[LeadOut])
def get_account_leads(account_id: int, db: Session = Depends(get_db)):
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(404, "Account not found")
    return account.leads


@router.get("/{account_id}/projects", response_model=List[ProjectOut])
def get_account_projects(account_id: int, db: Session = Depends(get_db)):
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(404, "Account not found")
    return account.projects


@router.get("/{account_id}/stakeholders", response_model=List[StakeholderOut])
def get_account_stakeholders(account_id: int, db: Session = Depends(get_db)):
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(404, "Account not found")
    return account.stakeholders


# ── Relationship: link / unlink contacts ──────────────────────────────────────

@router.post("/{account_id}/link/contact/{contact_id}", status_code=200)
def link_contact(account_id: int, contact_id: int, db: Session = Depends(get_db)):
    account = db.query(Account).filter(Account.id == account_id).first()
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not account or not contact:
        raise HTTPException(404, "Account or Contact not found")
    if contact not in account.contacts:
        account.contacts.append(contact)
    db.commit()
    return {"linked": True}


@router.delete("/{account_id}/unlink/contact/{contact_id}", status_code=200)
def unlink_contact(account_id: int, contact_id: int, db: Session = Depends(get_db)):
    account = db.query(Account).filter(Account.id == account_id).first()
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not account or not contact:
        raise HTTPException(404, "Account or Contact not found")
    if contact in account.contacts:
        account.contacts.remove(contact)
    db.commit()
    return {"unlinked": True}
