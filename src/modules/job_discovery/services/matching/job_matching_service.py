"""
Job matching service.

This service compares discovered jobs against a candidate profile.

Responsibilities:
    - Normalize job and candidate text.
    - Match role/title variations.
    - Match skills.
    - Match locations.
    - Match remote preferences.
    - Apply exclusion rules.
    - Calculate transparent weighted scores.
    - Produce APPLY / SKIP / MANUAL_REVIEW decisions.

The service is portal-independent.
"""

from __future__ import annotations

import re
from difflib import SequenceMatcher

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

    All scoring is transparent and stored in JobMatchBreakdown.
    """

    TITLE_WEIGHT = 0.35
    SKILL_WEIGHT = 0.30
    LOCATION_WEIGHT = 0.15
    REMOTE_WEIGHT = 0.10
    EXPERIENCE_WEIGHT = 0.10

    MANUAL_REVIEW_MARGIN = 0.10

    # Canonical role -> accepted role variations.
    _ROLE_ALIASES: dict[str, tuple[str, ...]] = {
        "data analyst": (
            "data analyst",
            "business data analyst",
            "associate data analyst",
            "data reporting analyst",
            "data & reporting analyst",
            "data analytics analyst",
            "analytics analyst",
            "reporting analyst",
            "bi analyst",
        ),
        "business analyst": (
            "business analyst",
            "associate business analyst",
            "business systems analyst",
            "business data analyst",
            "business intelligence analyst",
            "process analyst",
        ),
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
    }

    def match(
        self,
        job: DiscoveredJob,
        profile: CandidateJobProfile,
    ) -> JobMatchResult:
        """
        Match one job against the candidate profile.
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
            self.match(job, profile)
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

        Exact/alias matches take priority over fuzzy matches.
        Only the strongest role is returned.
        """

        normalized_title = self._normalize_text(
            title
        )

        if not normalized_title:
            return 0.0, []

        role_scores: list[tuple[str, float, bool]] = []

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

            best_score = 0.0
            exact_match = False

            for alias in aliases:
                normalized_alias = (
                    self._normalize_text(alias)
                )

                if not normalized_alias:
                    continue

                if normalized_alias in normalized_title:
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
                )
            )

        if not role_scores:
            return 0.0, []

        # Exact alias match always wins.
        exact_matches = [
            item
            for item in role_scores
            if item[2]
        ]

        if exact_matches:
            best = max(
                exact_matches,
                key=lambda item: item[1],
            )

            return round(best[1], 4), [best[0]]

        # Otherwise select only the strongest fuzzy match.
        best = max(
            role_scores,
            key=lambda item: item[1],
        )

        if best[1] < 0.65:
            return round(best[1], 4), []

        return round(best[1], 4), [best[0]]

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
        job_text = self._build_job_text(job)

        required = self._unique_normalized(
            profile.required_skills
        )

        preferred = self._unique_normalized(
            profile.preferred_skills
        )

        matched_required: list[str] = []
        matched_preferred: list[str] = []

        for skill in required:
            if self._contains_skill(
                job_text,
                skill,
            ):
                matched_required.append(skill)

        for skill in preferred:
            if self._contains_skill(
                job_text,
                skill,
            ):
                matched_preferred.append(skill)

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

        score = matched_total / total_relevant

        missing_required = [
            skill
            for skill in required
            if skill not in matched_required
        ]

        return (
            round(score, 4),
            matched_required
            + matched_preferred,
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
        if not profile.preferred_locations:
            return 0.5

        job_location = self._normalize_text(
            job.location or ""
        )

        if not job_location:
            return 0.0

        for location in profile.preferred_locations:
            normalized_location = (
                self._normalize_text(location)
            )

            if (
                normalized_location
                and normalized_location
                in job_location
            ):
                return 1.0

        return 0.0

    # ------------------------------------------------------------------
    # REMOTE
    # ------------------------------------------------------------------

    def _score_remote(
        self,
        job: DiscoveredJob,
        profile: CandidateJobProfile,
    ) -> float:
        if not profile.preferred_remote_statuses:
            return 0.5

        if job.remote_status is not None:
            job_remote = job.remote_status.value
        else:
            location = self._normalize_text(
                job.location or ""
            )

            if "remote" in location:
                job_remote = "remote"
            elif "hybrid" in location:
                job_remote = "hybrid"
            elif "onsite" in location:
                job_remote = "onsite"
            else:
                return 0.5

        preferred = {
            self._normalize_text(status)
            for status in (
                profile.preferred_remote_statuses
            )
        }

        return (
            1.0
            if job_remote in preferred
            else 0.0
        )

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
            max(0.0, min(1.0, score)),
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
        Produce the final matching decision.

        Exclusions always win.

        Missing required skills cause MANUAL_REVIEW when the
        overall job match is otherwise reasonably strong. This
        prevents potentially valuable jobs from being silently
        discarded because a portal exposed incomplete data.
        """

        if breakdown.excluded_reasons:
            return (
                DecisionType.SKIP.value,
                "; ".join(
                    breakdown.excluded_reasons
                ),
            )

        if (
            breakdown.missing_required_skills
            and overall_score
            >= profile.minimum_match_score
            - self.MANUAL_REVIEW_MARGIN
        ):
            return (
                DecisionType.MANUAL_REVIEW.value,
                (
                    "Strong or borderline match, "
                    "but required skills were not "
                    "confirmed: "
                    + ", ".join(
                        breakdown.missing_required_skills
                    )
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
                    f"{overall_score:.0%} meets the "
                    f"minimum threshold of "
                    f"{profile.minimum_match_score:.0%}."
                ),
            )

        if (
            overall_score
            >= profile.minimum_match_score
            - self.MANUAL_REVIEW_MARGIN
        ):
            return (
                DecisionType.MANUAL_REVIEW.value,
                (
                    f"Match score "
                    f"{overall_score:.0%} is close to "
                    f"the minimum threshold of "
                    f"{profile.minimum_match_score:.0%}."
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
    # TEXT HELPERS
    # ------------------------------------------------------------------

    @classmethod
    def _normalize_text(
        cls,
        value: str,
    ) -> str:
        value = value.lower().strip()

        value = value.replace(
            "&",
            " and ",
        )

        value = re.sub(
            r"[^a-z0-9+#.\s]",
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
        return cls._normalize_text(
            " ".join(
                value
                for value in (
                    job.title,
                    job.company_name,
                    job.description or "",
                )
                if value
            )
        )

    @classmethod
    def _contains_skill(
        cls,
        job_text: str,
        skill: str,
    ) -> bool:
        normalized_skill = (
            cls._normalize_text(skill)
        )

        if not normalized_skill:
            return False

        if normalized_skill in job_text:
            return True

        tokens = [
            token
            for token in normalized_skill.split()
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
        result: list[str] = []
        seen: set[str] = set()

        for value in values:
            normalized = cls._normalize_text(
                value
            )

            if (
                normalized
                and normalized not in seen
            ):
                seen.add(normalized)
                result.append(normalized)

        return result

    @staticmethod
    def _extract_year_requirement(
        description: str,
    ) -> float | None:
        patterns = (
            r"(\d+(?:\.\d+)?)\s*\+?\s*years",
            r"(\d+(?:\.\d+)?)\s*\+?\s*yrs",
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