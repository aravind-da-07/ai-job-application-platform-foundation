"""
Fixed, non-secret, non-environment-specific constants.

Anything that could plausibly change per environment belongs in
`settings.py` instead. This file holds true constants: enums of values
that are part of the domain model itself.
"""

from __future__ import annotations

from enum import Enum


class ApplicationStatus(str, Enum):
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    SUBMITTED = "submitted"
    FAILED = "failed"
    MANUAL_REVIEW_REQUIRED = "manual_review_required"
    AUTHENTICATION_REQUIRED = "authentication_required"
    CAPTCHA_DETECTED = "captcha_detected"
    SKIPPED = "skipped"
    DUPLICATE = "duplicate"


class ApplicationResult(str, Enum):
    YES = "YES"
    NO = "NO"
    PENDING = "PENDING"


class DecisionType(str, Enum):
    APPLY = "apply"
    SKIP = "skip"
    MANUAL_REVIEW = "manual_review"


class EmploymentType(str, Enum):
    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    CONTRACT = "contract"
    INTERNSHIP = "internship"
    FREELANCE = "freelance"


class RemoteStatus(str, Enum):
    REMOTE = "remote"
    HYBRID = "hybrid"
    ONSITE = "onsite"


class ResumeVersionType(str, Enum):
    ORIGINAL = "original"
    ATS_OPTIMIZED = "ats_optimized"
    COMPANY_TAILORED = "company_tailored"
    ROLE_TAILORED = "role_tailored"


class JobSourceType(str, Enum):
    LINKEDIN = "linkedin"
    INDEED = "indeed"
    NAUKRI = "naukri"
    FOUNDIT = "foundit"
    WELLFOUND = "wellfound"
    GREENHOUSE = "greenhouse"
    LEVER = "lever"
    ASHBY = "ashby"
    WORKDAY = "workday"
    ORACLE_CAREERS = "oracle_careers"
    SUCCESSFACTORS = "successfactors"
    COMPANY_CAREERS = "company_careers"
    REMOTEOK = "remoteok"
    WE_WORK_REMOTELY = "we_work_remotely"


class EventType(str, Enum):
    RESUME_UPLOADED = "resume_uploaded"
    CANDIDATE_UPDATED = "candidate_updated"
    JOB_DISCOVERED = "job_discovered"
    JOB_MATCHED = "job_matched"
    RESUME_TAILORED = "resume_tailored"
    APPLICATION_QUEUED = "application_queued"
    APPLICATION_SUBMITTED = "application_submitted"
    APPLICATION_FAILED = "application_failed"
    AUTHENTICATION_REQUIRED = "authentication_required"
    CAPTCHA_DETECTED = "captcha_detected"
    INTERVIEW_RECEIVED = "interview_received"
    NOTIFICATION_SENT = "notification_sent"
    DASHBOARD_UPDATED = "dashboard_updated"


# Supabase Storage bucket sub-paths
STORAGE_PATH_RESUMES = "resumes"
STORAGE_PATH_COVER_LETTERS = "cover-letters"
STORAGE_PATH_ATTACHMENTS = "attachments"
STORAGE_PATH_REPORTS = "reports"
STORAGE_PATH_SCREENSHOTS = "screenshots"
STORAGE_PATH_LOGS = "logs"

SUPPORTED_RESUME_FORMATS = (".pdf", ".docx", ".txt")
