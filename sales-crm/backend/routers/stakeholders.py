from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from models import Stakeholder, Project, Contact
from schemas import StakeholderCreate, StakeholderUpdate, StakeholderOut, LinkedInScrapeRequest

router = APIRouter(prefix="/stakeholders", tags=["Stakeholders"])


@router.get("/", response_model=List[StakeholderOut])
def list_stakeholders(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(Stakeholder).offset(skip).limit(limit).all()


@router.post("/", response_model=StakeholderOut, status_code=201)
def create_stakeholder(payload: StakeholderCreate, db: Session = Depends(get_db)):
    data = payload.model_dump(exclude={"project_ids"})
    stakeholder = Stakeholder(**data)

    if payload.project_ids:
        projects = db.query(Project).filter(Project.id.in_(payload.project_ids)).all()
        stakeholder.projects = projects

    db.add(stakeholder)
    db.commit()
    db.refresh(stakeholder)
    return stakeholder


@router.get("/{stakeholder_id}", response_model=StakeholderOut)
def get_stakeholder(stakeholder_id: int, db: Session = Depends(get_db)):
    s = db.query(Stakeholder).filter(Stakeholder.id == stakeholder_id).first()
    if not s:
        raise HTTPException(404, "Stakeholder not found")
    return s


@router.put("/{stakeholder_id}", response_model=StakeholderOut)
def update_stakeholder(stakeholder_id: int, payload: StakeholderUpdate,
                       db: Session = Depends(get_db)):
    s = db.query(Stakeholder).filter(Stakeholder.id == stakeholder_id).first()
    if not s:
        raise HTTPException(404, "Stakeholder not found")

    data = payload.model_dump(exclude={"project_ids"}, exclude_none=True)
    for k, v in data.items():
        setattr(s, k, v)

    if payload.project_ids is not None:
        projects = db.query(Project).filter(Project.id.in_(payload.project_ids)).all()
        s.projects = projects

    db.commit()
    db.refresh(s)
    return s


@router.delete("/{stakeholder_id}", status_code=204)
def delete_stakeholder(stakeholder_id: int, db: Session = Depends(get_db)):
    s = db.query(Stakeholder).filter(Stakeholder.id == stakeholder_id).first()
    if not s:
        raise HTTPException(404, "Stakeholder not found")
    db.delete(s)
    db.commit()


@router.post("/scan-linkedin", response_model=StakeholderOut)
async def scan_linkedin_for_stakeholder(req: LinkedInScrapeRequest,
                                        db: Session = Depends(get_db)):
    """
    Scrape a LinkedIn profile and attach the data to a stakeholder or contact.
    entity_type: 'stakeholder' | 'contact'
    """
    from services.linkedin_scraper import scrape_profile, profile_to_json

    profile = await scrape_profile(req.linkedin_url)
    profile_json = profile_to_json(profile)

    if req.entity_type == "stakeholder":
        entity = db.query(Stakeholder).filter(Stakeholder.id == req.entity_id).first()
        if not entity:
            raise HTTPException(404, "Stakeholder not found")
        entity.linkedin_data = profile_json
        entity.linkedin_url  = req.linkedin_url
        if not entity.name:
            entity.name = profile.get("full_name", "")
    elif req.entity_type == "contact":
        entity = db.query(Contact).filter(Contact.id == req.entity_id).first()
        if not entity:
            raise HTTPException(404, "Contact not found")
        entity.linkedin_data = profile_json
        entity.linkedin_url  = req.linkedin_url
        # Return a stakeholder representation – create one if missing
        stakeholder = entity.stakeholder
        if not stakeholder:
            stakeholder = Stakeholder(
                name=profile.get("full_name", f"{entity.first_name} {entity.last_name}"),
                email=entity.email,
                linkedin_url=req.linkedin_url,
                linkedin_data=profile_json,
                contact_id=entity.id,
            )
            db.add(stakeholder)
        else:
            stakeholder.linkedin_data = profile_json
        db.commit()
        db.refresh(stakeholder)
        return stakeholder
    else:
        raise HTTPException(400, "entity_type must be 'stakeholder' or 'contact'")

    db.commit()
    db.refresh(entity)
    return entity


@router.post("/identify-from-project/{project_id}", response_model=List[StakeholderOut])
def identify_stakeholders(project_id: int, db: Session = Depends(get_db)):
    """
    Auto-identify stakeholders for a project by inspecting linked contacts
    and email threads.
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(404, "Project not found")

    created = []
    seen_emails = {s.email for s in project.stakeholders if s.email}

    for contact in project.contacts:
        if contact.email in seen_emails:
            continue
        # Check if a stakeholder already exists for this contact
        existing = db.query(Stakeholder).filter(
            Stakeholder.contact_id == contact.id
        ).first()
        if existing:
            if existing not in project.stakeholders:
                project.stakeholders.append(existing)
            seen_emails.add(contact.email)
            continue

        stakeholder = Stakeholder(
            name=f"{contact.first_name} {contact.last_name or ''}".strip(),
            email=contact.email,
            role="unknown",
            influence_level="medium",
            sentiment="neutral",
            contact_id=contact.id,
        )
        stakeholder.projects.append(project)
        db.add(stakeholder)
        db.flush()
        seen_emails.add(contact.email)
        created.append(stakeholder)

    # Also scan email threads for this project
    for thread in project.email_threads:
        from services.email_parser import extract_all_participants
        import json as _json
        parsed = {}
        if thread.parsed_data:
            try:
                parsed = _json.loads(thread.parsed_data)
            except Exception:
                pass
        participants = extract_all_participants({
            "from_email": thread.from_email,
            "to_emails":  thread.to_emails,
            "cc_emails":  thread.cc_emails,
        })
        for email in participants:
            if email in seen_emails:
                continue
            stakeholder = Stakeholder(
                name=email.split("@")[0].replace(".", " ").title(),
                email=email,
                role="unknown",
                influence_level="low",
                sentiment="neutral",
            )
            stakeholder.projects.append(project)
            db.add(stakeholder)
            db.flush()
            seen_emails.add(email)
            created.append(stakeholder)

    db.commit()
    return created
