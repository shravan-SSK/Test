import json
from datetime import datetime, timezone
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


# ── LinkedIn scan + AI enrichment ──────────────────────────────────────────────

@router.post("/scan-linkedin", response_model=StakeholderOut)
async def scan_linkedin_for_stakeholder(req: LinkedInScrapeRequest,
                                        db: Session = Depends(get_db)):
    """
    1. Fetch the LinkedIn profile (real via RapidAPI or mock).
    2. Run Claude AI enrichment to auto-classify role, influence, sentiment,
       and generate a personalised approach recommendation.
    3. Persist everything back onto the Stakeholder or Contact record.
    """
    from services.linkedin_scraper import scrape_profile, profile_to_json
    from services.ai_enrichment import enrich_from_linkedin

    # Step 1 – fetch profile
    profile = await scrape_profile(req.linkedin_url)

    # Step 2 – AI enrichment
    insights = await enrich_from_linkedin(profile)

    profile_json  = profile_to_json(profile)
    signals_json  = json.dumps(insights.get("buying_signals", []))
    enriched_at   = datetime.now(timezone.utc)

    if req.entity_type == "stakeholder":
        entity = db.query(Stakeholder).filter(Stakeholder.id == req.entity_id).first()
        if not entity:
            raise HTTPException(404, "Stakeholder not found")

        entity.linkedin_url            = req.linkedin_url
        entity.linkedin_data           = profile_json
        entity.role                    = insights["role"]
        entity.influence_level         = insights["influence_level"]
        entity.sentiment               = insights["sentiment"]
        entity.ai_summary              = insights["ai_summary"]
        entity.approach_recommendation = insights["approach_recommendation"]
        entity.buying_signals          = signals_json
        entity.ai_enriched_at          = enriched_at
        if not entity.name or entity.name == "unknown":
            entity.name = profile.get("full_name", entity.name)

        db.commit()
        db.refresh(entity)
        return entity

    elif req.entity_type == "contact":
        contact = db.query(Contact).filter(Contact.id == req.entity_id).first()
        if not contact:
            raise HTTPException(404, "Contact not found")

        contact.linkedin_url  = req.linkedin_url
        contact.linkedin_data = profile_json

        # Create or update a linked Stakeholder record
        stakeholder = contact.stakeholder
        if not stakeholder:
            stakeholder = Stakeholder(contact_id=contact.id, email=contact.email)
            db.add(stakeholder)

        stakeholder.name                    = profile.get("full_name",
                                                f"{contact.first_name} {contact.last_name or ''}".strip())
        stakeholder.linkedin_url            = req.linkedin_url
        stakeholder.linkedin_data           = profile_json
        stakeholder.role                    = insights["role"]
        stakeholder.influence_level         = insights["influence_level"]
        stakeholder.sentiment               = insights["sentiment"]
        stakeholder.ai_summary              = insights["ai_summary"]
        stakeholder.approach_recommendation = insights["approach_recommendation"]
        stakeholder.buying_signals          = signals_json
        stakeholder.ai_enriched_at          = enriched_at

        # Inherit account / lead from any linked project
        if not stakeholder.account_id:
            for proj in contact.projects:
                if proj.account_id:
                    stakeholder.account_id = proj.account_id
                    break
        if not stakeholder.lead_id:
            for proj in contact.projects:
                if proj.lead_id:
                    stakeholder.lead_id = proj.lead_id
                    break

        db.commit()
        db.refresh(stakeholder)
        return stakeholder

    raise HTTPException(400, "entity_type must be 'stakeholder' or 'contact'")


# ── Auto-identify stakeholders from a project ─────────────────────────────────

@router.post("/identify-from-project/{project_id}", response_model=List[StakeholderOut])
def identify_stakeholders(project_id: int, db: Session = Depends(get_db)):
    """
    Auto-identify stakeholders for a project by scanning linked contacts and
    email threads. Newly created stakeholders are automatically mapped to the
    project's Account and Lead.
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(404, "Project not found")

    created = []
    seen_emails = {s.email for s in project.stakeholders if s.email}

    for contact in project.contacts:
        if contact.email in seen_emails:
            continue

        existing = db.query(Stakeholder).filter(
            Stakeholder.contact_id == contact.id
        ).first()
        if existing:
            if existing not in project.stakeholders:
                project.stakeholders.append(existing)
            # Backfill account/lead if missing
            if not existing.account_id and project.account_id:
                existing.account_id = project.account_id
            if not existing.lead_id and project.lead_id:
                existing.lead_id = project.lead_id
            seen_emails.add(contact.email)
            continue

        stakeholder = Stakeholder(
            name=f"{contact.first_name} {contact.last_name or ''}".strip(),
            email=contact.email,
            role="unknown",
            influence_level="medium",
            sentiment="neutral",
            contact_id=contact.id,
            account_id=project.account_id,
            lead_id=project.lead_id,
        )
        stakeholder.projects.append(project)
        db.add(stakeholder)
        db.flush()
        seen_emails.add(contact.email)
        created.append(stakeholder)

    # Also scan email threads for this project
    for thread in project.email_threads:
        from services.email_parser import extract_all_participants
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
                account_id=project.account_id,
                lead_id=project.lead_id,
            )
            stakeholder.projects.append(project)
            db.add(stakeholder)
            db.flush()
            seen_emails.add(email)
            created.append(stakeholder)

    db.commit()
    return created
