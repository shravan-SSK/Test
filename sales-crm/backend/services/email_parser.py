"""
Email parsing service.
- Extracts sender/recipient emails from raw email headers or plain text threads.
- Auto-matches emails to existing Contacts, and creates Leads if no match found.
- Links threads to Projects based on domain or keyword matching.
"""

import re
import json
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from email import message_from_string
from email.utils import parseaddr, getaddresses

from sqlalchemy.orm import Session


EMAIL_RE = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")


def extract_emails_from_text(text: str) -> List[str]:
    """Return all email addresses found in arbitrary text."""
    return list(set(EMAIL_RE.findall(text or "")))


def parse_raw_email(raw: str) -> Dict:
    """Parse a full RFC-2822 email string into a structured dict."""
    msg = message_from_string(raw)

    def _decode(val):
        return val if val else ""

    from_name, from_email = parseaddr(_decode(msg.get("From", "")))
    to_pairs  = getaddresses([_decode(msg.get("To", ""))])
    cc_pairs  = getaddresses([_decode(msg.get("Cc", ""))])

    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                body = part.get_payload(decode=True).decode(errors="replace")
                break
    else:
        payload = msg.get_payload(decode=True)
        body = payload.decode(errors="replace") if payload else ""

    date_str = msg.get("Date", "")
    received_at = None
    if date_str:
        from email.utils import parsedate_to_datetime
        try:
            received_at = parsedate_to_datetime(date_str)
        except Exception:
            pass

    return {
        "subject":     _decode(msg.get("Subject", "")),
        "from_email":  from_email or from_name,
        "from_name":   from_name,
        "to_emails":   ",".join(e for _, e in to_pairs if e),
        "cc_emails":   ",".join(e for _, e in cc_pairs if e),
        "body":        body,
        "received_at": received_at,
        "raw_headers": str(msg.items()),
    }


def auto_map_thread(db: Session, thread_data: Dict) -> Tuple[Optional[int], Optional[int]]:
    """
    Given parsed thread data, return (contact_id, project_id) by:
    1. Looking up the from_email in contacts.
    2. Trying to find a project linked to the matched contact or account domain.
    Returns (None, None) if nothing matched.
    """
    from models import Contact, Project, Account

    contact_id = None
    project_id = None

    from_email = (thread_data.get("from_email") or "").lower().strip()
    if from_email:
        contact = db.query(Contact).filter(
            Contact.email == from_email
        ).first()
        if contact:
            contact_id = contact.id
            # Try to find an active project linked to this contact
            for proj in contact.projects:
                if proj.status.value in ("active", "prospect"):
                    project_id = proj.id
                    break

    # Fallback: match by domain in Accounts
    if not project_id and from_email and "@" in from_email:
        domain = from_email.split("@")[1]
        account = db.query(Account).filter(
            Account.domain == domain
        ).first()
        if account:
            for proj in account.projects:
                if proj.status.value in ("active", "prospect"):
                    project_id = proj.id
                    break

    return contact_id, project_id


def build_lead_from_thread(thread_data: Dict) -> Dict:
    """Extract lead fields from a parsed email thread."""
    from_email = thread_data.get("from_email", "")
    name_parts = (thread_data.get("from_name") or "").split()
    return {
        "title":      f"Lead from {from_email}",
        "first_name": name_parts[0] if name_parts else "",
        "last_name":  " ".join(name_parts[1:]) if len(name_parts) > 1 else "",
        "email":      from_email,
        "source":     "email",
    }


def extract_all_participants(thread_data: Dict) -> List[str]:
    """Return all unique email addresses involved in the thread."""
    emails = set()
    for field in ("from_email", "to_emails", "cc_emails"):
        val = thread_data.get(field, "") or ""
        for e in val.split(","):
            e = e.strip().lower()
            if EMAIL_RE.match(e):
                emails.add(e)
    return list(emails)
