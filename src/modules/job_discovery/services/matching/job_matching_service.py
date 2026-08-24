"""
Job matching service.

This service compares discovered jobs against a candidate profile.

Responsibilities:
    - Normalize job and candidate text.
    - Recognize Data Analyst and Business Analyst role families.
    - Normalize common technical skill aliases.
    - Match skills.
    - Apply candidate location priorities.
    - Match accepted work modes.
    - Evaluate experience requirements.
    - Apply exclusion rules.
    - Calculate transparent weighted scores.
    - Produce APPLY / SKIP decisions.

The matching layer does not handle:
    - browser automation,
    - authentication,
    - OTP,
    - CAPTCHA,
    - questionnaire completion,
    - application submission.

Those responsibilities belong to the application execution layer.
"""

from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Iterable

from src.modules.job_discovery.domain.entities.job_discovery import (
    DiscoveredJob,
)
from src.modules.job_discovery.domain.matching.job_matching import (
    CandidateJobProfile,
    JobMatchBreakdown,
    JobMatchResult,
)
from src.shared.config.constants import DecisionType
from src.shared.core.exceptions import ValidationError


class JobMatchingService:
    """
    Match discovered jobs against a candidate profile.

    Scoring is transparent and is stored in JobMatchBreakdown.

    Default scoring:
        title       = 35%
        skills      = 30%
        location    = 15%
        work mode   = 10%
        experience  = 10%

    The candidate profile controls the minimum score required
    for an APPLY decision.
    """

    TITLE_WEIGHT = 0.35
    SKILL_WEIGHT = 0.30
    LOCATION_WEIGHT = 0.15
    REMOTE_WEIGHT = 0.10
    EXPERIENCE_WEIGHT = 0.10

    # ------------------------------------------------------------------
    # Role taxonomy
    # ------------------------------------------------------------------

    DATA_ANALYST_ROLES: tuple[str, ...] = (
        "data analyst",
        "data analytics analyst",
        "data specialist",
        "business data analyst",
        "junior data analyst",
        "associate data analyst",
        "reporting analyst",
        "bi analyst",
        "business intelligence analyst",
        "analytics analyst",
        "analytics specialist",
        "data quality analyst",
        "data insights analyst",
        "data visualization analyst",
        "data management analyst",
        "data reporting analyst",
        "data integration analyst",
        "data governance analyst",
        "data operations analyst",
    )

    BUSINESS_ANALYST_ROLES: tuple[str, ...] = (
        "business analyst",
        "associate business analyst",
        "junior business analyst",
        "technical business analyst",
        "it business analyst",
        "business systems analyst",
        "business intelligence analyst",
        "product analyst",
        "operations analyst",
        "process analyst",
        "systems analyst",
    )

    # A role can be related to either family.
    # The lower number means higher candidate preference.
    ROLE_FAMILY_PRIORITY: dict[str, int] = {
        "data analyst": 1,
        "business analyst": 2,
    }

    # ------------------------------------------------------------------
    # Role aliases
    # ------------------------------------------------------------------

    _ROLE_ALIASES: dict[str, tuple[str, ...]] = {
        "data analyst": DATA_ANALYST_ROLES,
        "business analyst": BUSINESS_ANALYST_ROLES,
    }

    # ------------------------------------------------------------------
    # Skill aliases
    #
    # Keys are canonical skills.
    # Values contain common variations found in job descriptions.
    # ------------------------------------------------------------------

    _SKILL_ALIASES: dict[str, tuple[str, ...]] = {
        "sql": (
            "sql",
            "structured query language",
            "sql querying",
            "sql queries",
            "data querying",
            "querying",
        ),
        "mysql": (
            "mysql",
            "mysql database",
            "mysql workbench",
        ),
        "python": (
            "python",
            "python programming",
            "python scripting",
        ),
        "power bi": (
            "power bi",
            "powerbi",
            "microsoft power bi",
            "power bi desktop",
        ),
        "tableau": (
            "tableau",
            "tableau desktop",
            "tableau reporting",
        ),
        "excel": (
            "excel",
            "microsoft excel",
            "ms excel",
            "advanced excel",
        ),
        "jupyter": (
            "jupyter",
            "jupyter notebook",
            "jupyter notebooks",
        ),
        "anaconda": (
            "anaconda",
            "anaconda distribution",
        ),
        "stored procedures": (
            "stored procedure",
            "stored procedures",
            "sql stored procedures",
        ),
        "github": (
            "github",
            "git hub",
        ),
        "gitlab": (
            "gitlab",
            "git lab",
        ),
        "powershell": (
            "powershell",
            "power shell",
        ),
        "data visualization": (
            "data visualization",
            "data visualisation",
            "visualization",
            "visualisation",
        ),
        "data cleaning": (
            "data cleaning",
            "data cleansing",
            "data quality cleaning",
        ),
        "data preparation": (
            "data preparation",
            "data preprocessing",
            "data pre-processing",
            "data preparation and cleaning",
        ),
        "data wrangling": (
            "data wrangling",
            "data munging",
            "data transformation",
        ),
        "etl": (
            "etl",
            "extract transform load",
            "extract transform and load",
        ),
        "statistical analysis": (
            "statistical analysis",
            "statistics",
            "statistical modeling",
            "statistical modelling",
        ),
        "data interpretation": (
            "data interpretation",
            "interpreting data",
            "data insights",
        ),
        "dbms": (
            "dbms",
            "database management systems",
            "database management system",
        ),
        "jira": (
            "jira",
            "atlassian jira",
        ),
        "data querying and manipulation": (
            "data querying",
            "data manipulation",
            "querying and manipulation",
            "data query and manipulation",
        ),
        "dashboard creation": (
            "dashboard",
            "dashboards",
            "dashboard creation",
            "dashboard development",
            "reporting dashboards",
        ),
        "reporting": (
            "reporting",
            "reports",
            "report generation",
            "management reporting",
        ),
        "data storytelling": (
            "data storytelling",
            "data story",
            "storytelling with data",
        ),
        "business acumen": (
            "business acumen",
            "business understanding",
            "business knowledge",
        ),
        "data management": (
            "data management",
            "data governance",
            "data operations",
        ),
        "data extraction": (
            "data extraction",
            "extracting data",
            "data retrieval",
        ),
        "genai": (
            "genai",
            "generative ai",
            "generative artificial intelligence",
        ),
        "prompt engineering": (
            "prompt engineering",
            "prompt design",
            "prompting",
        ),
        "nlp": (
            "nlp",
            "natural language processing",
        ),
        "ai concepts": (
            "artificial intelligence",
            "ai concepts",
            "ai",
            "machine intelligence",
        ),
        "problem solving": (
            "problem solving",
            "problem-solving",
            "analytical problem solving",
        ),
        "critical thinking": (
            "critical thinking",
            "analytical thinking",
        ),
        "teamwork": (
            "teamwork",
            "team collaboration",
            "collaboration",
        ),
        "attention to detail": (
            "attention to detail",
            "detail oriented",
            "detail-oriented",
        ),
    }

    # ------------------------------------------------------------------
    # Location aliases and preference
    # ------------------------------------------------------------------

    _LOCATION_ALIASES: dict[str, tuple[str, ...]] = {
        "hyderabad": (
            "hyderabad",
            "secunderabad",
        ),
        "bengaluru": (
            "bengaluru",
            "bangalore",
            "bengalooru",
        ),
        "pune": (
            "pune",
        ),
        "mumbai": (
            "mumbai",
            "bombay",
        ),
        "chennai": (
            "chennai",
            "madras",
        ),
        "noida": (
            "noida",
        ),
        "gurugram": (
            "gurugram",
            "gurgaon",
        ),
    }

    _LOCATION_PRIORITY: dict[str, float] = {
        "hyderabad": 1.00,
        "bengaluru": 0.90,
        "pune": 0.80,
        "mumbai": 0.80,
        "chennai": 0.80,
        "noida": 0.80,
        "gurugram": 0.80,
    }

    _REMOTE_VALUES = {
        "remote",
        "hybrid",
        "onsite",
    }

    _STOP_WORDS = {
        "and",
        "or",
        "the",
        "a",
        "an",
        "of",
        "for",
        "in",
        "at",
        "to",
        "with",
        "on",
    }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def match(
        self,
        job: DiscoveredJob,
        profile: CandidateJobProfile,
    ) -> JobMatchResult:
        """
        Match one job against a candidate profile.
        """

        if job is None:
            raise ValidationError(
                "A discovered job is required."
            )

        if profile is None:
            raise ValidationError(
                "A candidate job profile is required."
            )

        title_score, matched_roles = self._score_title(
            job.title,
            profile.target_roles,
        )

        (
            skill_score,
            matched_skills,
            missing_required_skills,
        ) = self._score_skills(
            job,
            profile,
        )

        location_score = self._score_location(
            job,
            profile,
        )

        remote_score = self._score_remote(
            job,
            profile,
        )

        experience_score = self._score_experience(
            job,
            profile,
        )

        excluded_reasons = self._find_exclusions(
            job,
            profile,
        )

        role_priority = self._get_role_priority(
            job.title
        )

        breakdown = JobMatchBreakdown(
            title_score=title_score,
            skill_score=skill_score,
            location_score=location_score,
            remote_score=remote_score,
            experience_score=experience_score,
            matched_skills=tuple(
                matched_skills
            ),
            missing_required_skills=tuple(
                missing_required_skills
            ),
            matched_roles=tuple(
                matched_roles
            ),
            excluded_reasons=tuple(
                excluded_reasons
            ),
            metadata={
                "role_priority": role_priority,
                "role_family": self._get_role_family(
                    job.title
                ),
                "location_priority": self._get_location_priority(
                    job.location
                ),
                "job_location": job.location,
                "work_mode": self._get_work_mode(
                    job
                ),
            },
        )

        overall_score = self._calculate_overall_score(
            breakdown
        )

        decision, reason = self._make_decision(
            overall_score=overall_score,
            profile=profile,
            breakdown=breakdown,
        )

        return JobMatchResult(
            external_job_id=job.external_id,
            overall_score=overall_score,
            decision=decision,
            breakdown=breakdown,
            reason=reason,
            metadata={
                "match_threshold": profile.minimum_match_score,
                "role_family": self._get_role_family(
                    job.title
                ),
                "role_priority": role_priority,
                "location_priority": self._get_location_priority(
                    job.location
                ),
                "automatic_application_eligible": (
                    decision == DecisionType.APPLY.value
                ),
            },
        )

    def match_many(
        self,
        jobs: tuple[DiscoveredJob, ...]
        | list[DiscoveredJob],
        profile: CandidateJobProfile,
    ) -> tuple[JobMatchResult, ...]:
        """
        Match multiple jobs.
        """

        if profile is None:
            raise ValidationError(
                "A candidate job profile is required."
            )

        return tuple(
            self.match(
                job,
                profile,
            )
            for job in jobs
        )

    # ------------------------------------------------------------------
    # TITLE MATCHING
    # ------------------------------------------------------------------

    def _score_title(
        self,
        title: str,
        target_roles: tuple[str, ...],
    ) -> tuple[float, list[str]]:
        """
        Determine the strongest target-role match.

        Exact family aliases receive the strongest score.
        Fuzzy matching is used only as a secondary signal.
        """

        normalized_title = self._normalize_text(
            title
        )

        if not normalized_title:
            return 0.0, []

        role_scores: list[
            tuple[str, float, bool, int]
        ] = []

        for target_role in target_roles:
            normalized_role = self._normalize_text(
                target_role
            )

            if not normalized_role:
                continue

            aliases = self._ROLE_ALIASES.get(
                normalized_role,
                (normalized_role,),
            )

            family = self._get_role_family(
                normalized_role
            )

            family_priority = (
                self.ROLE_FAMILY_PRIORITY.get(
                    family,
                    99,
                )
            )

            best_score = 0.0
            exact_match = False

            for alias in aliases:
                normalized_alias = (
                    self._normalize_text(alias)
                )

                if not normalized_alias:
                    continue

                if self._role_phrase_matches(
                    normalized_title,
                    normalized_alias,
                ):
                    best_score = 1.0
                    exact_match = True
                    break

                similarity = SequenceMatcher(
                    None,
                    normalized_title,
                    normalized_alias,
                ).ratio()

                best_score = max(
                    best_score,
                    similarity,
                )

            role_scores.append(
                (
                    target_role,
                    best_score,
                    exact_match,
                    family_priority,
                )
            )

        if not role_scores:
            return 0.0, []

        exact_matches = [
            item
            for item in role_scores
            if item[2]
        ]

        if exact_matches:
            best = min(
                exact_matches,
                key=lambda item: (
                    item[3],
                    -item[1],
                ),
            )

            return (
                round(best[1], 4),
                [best[0]],
            )

        best = max(
            role_scores,
            key=lambda item: (
                item[1],
                -item[3],
            ),
        )

        if best[1] < 0.65:
            return round(best[1], 4), []

        return (
            round(best[1], 4),
            [best[0]],
        )

    # ------------------------------------------------------------------
    # SKILL MATCHING
    # ------------------------------------------------------------------

    def _score_skills(
        self,
        job: DiscoveredJob,
        profile: CandidateJobProfile,
    ) -> tuple[
        float,
        list[str],
        list[str],
    ]:
        job_text = self._build_job_text(
            job
        )

        required = self._canonicalize_skills(
            profile.required_skills
        )

        preferred = self._canonicalize_skills(
            profile.preferred_skills
        )

        matched_required: list[str] = []
        matched_preferred: list[str] = []

        for skill in required:
            if self._contains_skill(
                job_text,
                skill,
            ):
                matched_required.append(
                    skill
                )

        for skill in preferred:
            if self._contains_skill(
                job_text,
                skill,
            ):
                matched_preferred.append(
                    skill
                )

        total_relevant = (
            len(required)
            + len(preferred)
        )

        if total_relevant == 0:
            return 0.5, [], []

        matched_total = (
            len(matched_required)
            + len(matched_preferred)
        )

        score = (
            matched_total
            / total_relevant
        )

        missing_required = [
            skill
            for skill in required
            if skill not in matched_required
        ]

        return (
            round(score, 4),
            (
                matched_required
                + matched_preferred
            ),
            missing_required,
        )

    # ------------------------------------------------------------------
    # LOCATION
    # ------------------------------------------------------------------

    def _score_location(
        self,
        job: DiscoveredJob,
        profile: CandidateJobProfile,
    ) -> float:
        """
        Score location according to candidate preference.

        Hyderabad receives the highest preference.
        Other configured preferred cities receive their configured
        preference score.

        Remote jobs remain acceptable and are handled by work-mode
        scoring as well.
        """

        if not profile.preferred_locations:
            return 0.5

        job_location = self._normalize_text(
            job.location or ""
        )

        if not job_location:
            return 0.5

        best_score = 0.0

        for preferred in profile.preferred_locations:
            canonical = self._canonicalize_location(
                preferred
            )

            if canonical is None:
                continue

            aliases = self._LOCATION_ALIASES.get(
                canonical,
                (canonical,),
            )

            if any(
                alias in job_location
                for alias in aliases
            ):
                best_score = max(
                    best_score,
                    self._LOCATION_PRIORITY.get(
                        canonical,
                        0.70,
                    ),
                )

        if "remote" in job_location:
            best_score = max(
                best_score,
                0.85,
            )

        if "anywhere" in job_location:
            best_score = max(
                best_score,
                0.85,
            )

        return round(
            best_score,
            4,
        )

    # ------------------------------------------------------------------
    # REMOTE / WORK MODE
    # ------------------------------------------------------------------

    def _score_remote(
        self,
        job: DiscoveredJob,
        profile: CandidateJobProfile,
    ) -> float:
        """
        Work-mode compatibility.

        Remote, hybrid and onsite are all acceptable when configured
        by the candidate.
        """

        if not profile.preferred_remote_statuses:
            return 0.5

        job_remote = self._get_work_mode(
            job
        )

        if not job_remote:
            return 0.5

        preferred = {
            self._normalize_text(status)
            for status in (
                profile.preferred_remote_statuses
            )
        }

        if job_remote in preferred:
            return 1.0

        # Candidate has explicitly stated that all common work modes
        # are acceptable. Keep the job eligible rather than penalizing
        # it to zero.
        if self._all_work_modes_accepted(
            preferred
        ):
            return 1.0

        return 0.0

    # ------------------------------------------------------------------
    # EXPERIENCE
    # ------------------------------------------------------------------

    def _score_experience(
        self,
        job: DiscoveredJob,
        profile: CandidateJobProfile,
    ) -> float:
        if (
            profile.minimum_experience_years
            is None
            and profile.maximum_experience_years
            is None
        ):
            return 0.5

        description = self._normalize_text(
            job.description or ""
        )

        if not description:
            return 0.5

        required_years = (
            self._extract_year_requirement(
                description
            )
        )

        if required_years is None:
            return 0.5

        minimum = (
            profile.minimum_experience_years
        )

        maximum = (
            profile.maximum_experience_years
        )

        if (
            minimum is not None
            and required_years < minimum
        ):
            return 1.0

        if (
            maximum is not None
            and required_years > maximum
        ):
            return 0.0

        return 1.0

    # ------------------------------------------------------------------
    # EXCLUSIONS
    # ------------------------------------------------------------------

    def _find_exclusions(
        self,
        job: DiscoveredJob,
        profile: CandidateJobProfile,
    ) -> list[str]:
        reasons: list[str] = []

        normalized_title = self._normalize_text(
            job.title
        )

        normalized_company = (
            self._normalize_text(
                job.company_name
            )
        )

        for excluded_role in (
            profile.excluded_roles
        ):
            normalized_role = (
                self._normalize_text(
                    excluded_role
                )
            )

            if (
                normalized_role
                and normalized_role
                in normalized_title
            ):
                reasons.append(
                    f"Excluded role: "
                    f"{excluded_role}"
                )

        for excluded_company in (
            profile.excluded_companies
        ):
            normalized_company_name = (
                self._normalize_text(
                    excluded_company
                )
            )

            if (
                normalized_company_name
                and normalized_company_name
                in normalized_company
            ):
                reasons.append(
                    f"Excluded company: "
                    f"{excluded_company}"
                )

        return reasons

    # ------------------------------------------------------------------
    # SCORE
    # ------------------------------------------------------------------

    def _calculate_overall_score(
        self,
        breakdown: JobMatchBreakdown,
    ) -> float:
        score = (
            breakdown.title_score
            * self.TITLE_WEIGHT
            + breakdown.skill_score
            * self.SKILL_WEIGHT
            + breakdown.location_score
            * self.LOCATION_WEIGHT
            + breakdown.remote_score
            * self.REMOTE_WEIGHT
            + breakdown.experience_score
            * self.EXPERIENCE_WEIGHT
        )

        return round(
            max(
                0.0,
                min(
                    1.0,
                    score,
                ),
            ),
            4,
        )

    # ------------------------------------------------------------------
    # DECISION
    # ------------------------------------------------------------------

    def _make_decision(
        self,
        *,
        overall_score: float,
        profile: CandidateJobProfile,
        breakdown: JobMatchBreakdown,
    ) -> tuple[str, str]:
        """
        Produce APPLY / SKIP.

        Matching itself does not create MANUAL_REVIEW decisions.

        Authentication, OTP, CAPTCHA and other execution blockers
        are handled by the application execution layer.
        """

        if breakdown.excluded_reasons:
            return (
                DecisionType.SKIP.value,
                "; ".join(
                    breakdown.excluded_reasons
                ),
            )

        if (
            overall_score
            >= profile.minimum_match_score
        ):
            return (
                DecisionType.APPLY.value,
                (
                    f"Match score "
                    f"{overall_score:.0%} meets or "
                    f"exceeds the minimum threshold "
                    f"of "
                    f"{profile.minimum_match_score:.0%}."
                ),
            )

        if breakdown.missing_required_skills:
            return (
                DecisionType.SKIP.value,
                (
                    f"Match score "
                    f"{overall_score:.0%} is below the "
                    f"minimum threshold of "
                    f"{profile.minimum_match_score:.0%}; "
                    f"required skills not confirmed: "
                    + ", ".join(
                        breakdown.missing_required_skills
                    )
                ),
            )

        return (
            DecisionType.SKIP.value,
            (
                f"Match score "
                f"{overall_score:.0%} is below the "
                f"minimum threshold of "
                f"{profile.minimum_match_score:.0%}."
            ),
        )

    # ------------------------------------------------------------------
    # ROLE HELPERS
    # ------------------------------------------------------------------

    @classmethod
    def _get_role_family(
        cls,
        value: str,
    ) -> str | None:
        normalized = cls._normalize_text(
            value
        )

        for family, aliases in (
            cls._ROLE_ALIASES.items()
        ):
            for alias in aliases:
                normalized_alias = (
                    cls._normalize_text(alias)
                )

                if cls._role_phrase_matches(
                    normalized,
                    normalized_alias,
                ):
                    return family

        return None

    @classmethod
    def _get_role_priority(
        cls,
        title: str,
    ) -> int | None:
        family = cls._get_role_family(
            title
        )

        if family is None:
            return None

        return cls.ROLE_FAMILY_PRIORITY.get(
            family
        )

    @classmethod
    def _role_phrase_matches(
        cls,
        text: str,
        phrase: str,
    ) -> bool:
        if not text or not phrase:
            return False

        if phrase in text:
            return True

        pattern = (
            r"(?<![a-z0-9])"
            + re.escape(phrase)
            + r"(?![a-z0-9])"
        )

        return re.search(
            pattern,
            text,
        ) is not None

    # ------------------------------------------------------------------
    # LOCATION HELPERS
    # ------------------------------------------------------------------

    @classmethod
    def _canonicalize_location(
        cls,
        value: str,
    ) -> str | None:
        normalized = cls._normalize_text(
            value
        )

        if not normalized:
            return None

        for canonical, aliases in (
            cls._LOCATION_ALIASES.items()
        ):
            if any(
                alias in normalized
                for alias in aliases
            ):
                return canonical

        return normalized

    @classmethod
    def _get_location_priority(
        cls,
        location: str | None,
    ) -> float:
        if not location:
            return 0.5

        normalized = cls._normalize_text(
            location
        )

        if "remote" in normalized:
            return 0.85

        best = 0.0

        for canonical, aliases in (
            cls._LOCATION_ALIASES.items()
        ):
            if any(
                alias in normalized
                for alias in aliases
            ):
                best = max(
                    best,
                    cls._LOCATION_PRIORITY.get(
                        canonical,
                        0.70,
                    ),
                )

        return (
            round(best, 4)
            if best
            else 0.5
        )

    # ------------------------------------------------------------------
    # WORK-MODE HELPERS
    # ------------------------------------------------------------------

    @classmethod
    def _get_work_mode(
        cls,
        job: DiscoveredJob,
    ) -> str | None:
        if job.remote_status is not None:
            return cls._normalize_text(
                job.remote_status.value
            )

        location = cls._normalize_text(
            job.location or ""
        )

        description = cls._normalize_text(
            job.description or ""
        )

        combined = (
            f"{location} {description}"
        )

        if "hybrid" in combined:
            return "hybrid"

        if "remote" in combined:
            return "remote"

        if "on site" in combined:
            return "onsite"

        if "onsite" in combined:
            return "onsite"

        return None

    @classmethod
    def _all_work_modes_accepted(
        cls,
        preferred: set[str],
    ) -> bool:
        normalized = {
            value.replace(
                " ",
                "_",
            )
            for value in preferred
        }

        return {
            "remote",
            "hybrid",
            "onsite",
        }.issubset(normalized)

    # ------------------------------------------------------------------
    # TEXT HELPERS
    # ------------------------------------------------------------------

    @classmethod
    def _normalize_text(
        cls,
        value: str,
    ) -> str:
        value = (
            value
            .lower()
            .strip()
        )

        value = value.replace(
            "&",
            " and ",
        )

        value = value.replace(
            "/",
            " ",
        )

        value = re.sub(
            r"[^a-z0-9+#.\s-]",
            " ",
            value,
        )

        value = re.sub(
            r"\s+",
            " ",
            value,
        )

        return value.strip()

    @classmethod
    def _build_job_text(
        cls,
        job: DiscoveredJob,
    ) -> str:
        metadata_text = ""

        if job.metadata:
            metadata_text = " ".join(
                str(value)
                for value in job.metadata.values()
                if value is not None
            )

        return cls._normalize_text(
            " ".join(
                value
                for value in (
                    job.title,
                    job.company_name,
                    job.location or "",
                    job.description or "",
                    metadata_text,
                )
                if value
            )
        )

    # ------------------------------------------------------------------
    # SKILL HELPERS
    # ------------------------------------------------------------------

    @classmethod
    def _canonicalize_skill(
        cls,
        skill: str,
    ) -> str:
        normalized = cls._normalize_text(
            skill
        )

        if not normalized:
            return ""

        for canonical, aliases in (
            cls._SKILL_ALIASES.items()
        ):
            normalized_aliases = {
                cls._normalize_text(alias)
                for alias in aliases
            }

            if (
                normalized in normalized_aliases
            ):
                return canonical

        return normalized

    @classmethod
    def _canonicalize_skills(
        cls,
        values: Iterable[str],
    ) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()

        for value in values:
            canonical = cls._canonicalize_skill(
                value
            )

            if (
                canonical
                and canonical not in seen
            ):
                seen.add(canonical)
                result.append(canonical)

        return result

    @classmethod
    def _contains_skill(
        cls,
        job_text: str,
        skill: str,
    ) -> bool:
        canonical = cls._canonicalize_skill(
            skill
        )

        if not canonical:
            return False

        aliases = cls._SKILL_ALIASES.get(
            canonical,
            (canonical,),
        )

        for alias in aliases:
            normalized_alias = (
                cls._normalize_text(alias)
            )

            if not normalized_alias:
                continue

            if cls._role_phrase_matches(
                job_text,
                normalized_alias,
            ):
                return True

        tokens = [
            token
            for token in canonical.split()
            if token not in cls._STOP_WORDS
        ]

        if not tokens:
            return False

        return all(
            token in job_text
            for token in tokens
        )

    @classmethod
    def _unique_normalized(
        cls,
        values: tuple[str, ...],
    ) -> list[str]:
        return cls._canonicalize_skills(
            values
        )

    # ------------------------------------------------------------------
    # EXPERIENCE HELPERS
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_year_requirement(
        description: str,
    ) -> float | None:
        patterns = (
            r"(\d+(?:\.\d+)?)\s*\+?\s*years",
            r"(\d+(?:\.\d+)?)\s*\+?\s*yrs",
            r"minimum\s+of\s+(\d+(?:\.\d+)?)",
        )

        for pattern in patterns:
            match = re.search(
                pattern,
                description,
            )

            if match:
                return float(
                    match.group(1)
                )

        return None