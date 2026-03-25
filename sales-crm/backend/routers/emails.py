from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from models import EmailThread, Contact, Lead
from schemas import EmailThreadCreate, EmailThreadOut

router = APIRouter(prefix="/emails", tags=["Emails"])


@router.get("/", response_model=List[EmailThreadOut])
def list_threads(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(EmailThread).offset(skip).limit(limit).all()


@router.post("/ingest", response_model=EmailThreadOut, status_code=201)
def ingest_email(payload: EmailThreadCreate, db: Session = Depends(get_db)):
    """
    Ingest a parsed email.  The service will:
    1. Auto-map from_email to an existing Contact.
    2. Auto-link to an active Project via the Contact or Account domain.
    3. If no Contact exists, create a Lead from the email.
    4. Store extracted participants as parsed_data JSON.
    """
    import json
    from services.email_parser import auto_map_thread, build_lead_from_thread, extract_all_participants

    thread_data = payload.model_dump()
    contact_id, project_id = auto_map_thread(db, thread_data)

    # Build a Lead if no contact matched
    if not contact_id and payload.from_email:
        existing_lead = db.query(Lead).filter(Lead.email == payload.from_email).first()
        if not existing_lead:
            lead_fields = build_lead_from_thread(thread_data)
            new_lead = Lead(**lead_fields)
            db.add(new_lead)
            db.flush()

    participants = extract_all_participants(thread_data)
    parsed_data  = json.dumps({"participants": participants})

    thread = EmailThread(
        subject=payload.subject,
        from_email=payload.from_email,
        to_emails=payload.to_emails,
        cc_emails=payload.cc_emails,
        body=payload.body,
        received_at=payload.received_at,
        raw_headers=payload.raw_headers,
        parsed_data=parsed_data,
        contact_id=contact_id,
        project_id=project_id,
    )
    db.add(thread)
    db.commit()
    db.refresh(thread)
    return thread


@router.post("/ingest-raw", response_model=EmailThreadOut, status_code=201)
def ingest_raw_email(raw_body: str, db: Session = Depends(get_db)):
    """
    Ingest a full RFC-2822 raw email string.
    """
    from services.email_parser import parse_raw_email
    from schemas import EmailThreadCreate

    parsed = parse_raw_email(raw_body)
    payload = EmailThreadCreate(**parsed)
    return ingest_email(payload, db)


@router.get("/{thread_id}", response_model=EmailThreadOut)
def get_thread(thread_id: int, db: Session = Depends(get_db)):
    thread = db.query(EmailThread).filter(EmailThread.id == thread_id).first()
    if not thread:
        raise HTTPException(404, "Thread not found")
    return thread


@router.delete("/{thread_id}", status_code=204)
def delete_thread(thread_id: int, db: Session = Depends(get_db)):
    thread = db.query(EmailThread).filter(EmailThread.id == thread_id).first()
    if not thread:
        raise HTTPException(404, "Thread not found")
    db.delete(thread)
    db.commit()
