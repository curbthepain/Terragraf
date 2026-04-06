"""
query/engine.py — Structured query engine for native tabs.

Resolves user queries against routes, headers, and skills.
No LLM — pure route matching and skill dispatch.
"""

import time
from dataclasses import dataclass, field
from pathlib import Path

from .parser import IntentParser, Intent


SCAFFOLD_DIR = Path(__file__).resolve().parent.parent
SKILLS_DIR = SCAFFOLD_DIR / "skills"


@dataclass
class RouteMatch:
    """A single route match with source and score."""
    concept: str = ""
    path: str = ""
    description: str = ""
    source_file: str = ""   # e.g. "structure.route" or "router.route"
    score: float = 0.0      # 0.0–1.0, higher = better match


@dataclass
class HeaderMatch:
    """A matched header module."""
    module_name: str = ""
    source_file: str = ""   # e.g. "project.h"
    tags: list[str] = field(default_factory=list)
    exports: list[str] = field(default_factory=list)
    score: float = 0.0


@dataclass
class QueryResult:
    """Full result of a query resolution."""
    intent: Intent = field(default_factory=Intent)
    skill_match: tuple | None = None   # (skill_name, manifest) or None
    route_matches: list[RouteMatch] = field(default_factory=list)
    header_matches: list[HeaderMatch] = field(default_factory=list)
    executed: bool = False
    output: str = ""
    error: str = ""
    timestamp: float = field(default_factory=time.time)


class QueryEngine:
    """
    Resolves user queries through scaffold routes, headers, and skills.

    Pipeline:
      1. Parse intent via IntentParser
      2. Match against skills/router.route (skill dispatch)
      3. Match against all loaded routes in ScaffoldState
      4. Match against header modules
      5. Track consultation in session.context
    """

    def __init__(self, scaffold_state):
        self._state = scaffold_state
        self._parser = IntentParser()

    def query(self, text: str, session=None) -> QueryResult:
        """Resolve a text query. Optionally tracks context in session."""
        intent = self._parser.parse(text)

        if not intent.raw:
            return QueryResult(intent=intent)

        # Build search terms from verb + target
        search_terms = []
        if intent.target:
            search_terms.append(intent.target.lower())
        if intent.verb and intent.target:
            search_terms.append(f"{intent.verb} {intent.target}".lower())
        if intent.verb and not intent.target:
            search_terms.append(intent.verb.lower())

        # 1. Skill matching via router.route
        skill_match = self._match_skill(search_terms)

        # 2. Route matching across all .route files
        route_matches = self._match_routes(search_terms)

        # 3. Header matching
        header_matches = self._match_headers(search_terms)

        # Track context
        if session is not None:
            for rm in route_matches:
                src = f"routes/{rm.source_file}"
                if src not in session.context.routes_consulted:
                    session.context.routes_consulted.append(src)
            for hm in header_matches:
                src = f"headers/{hm.source_file}"
                if src not in session.context.headers_read:
                    session.context.headers_read.append(src)

        result = QueryResult(
            intent=intent,
            skill_match=skill_match,
            route_matches=sorted(route_matches, key=lambda r: r.score, reverse=True),
            header_matches=sorted(header_matches, key=lambda h: h.score, reverse=True),
        )

        # Append to session history
        if session is not None and hasattr(session, "query_history"):
            session.query_history.append(result)

        return result

    def execute_skill(self, result: QueryResult, args=None) -> QueryResult:
        """Execute the matched skill and update the result."""
        if not result.skill_match:
            result.error = "No skill matched"
            return result

        from skills.runner import run_skill_capture

        name = result.skill_match[0]
        rc, stdout, stderr = run_skill_capture(name, args)
        result.executed = True
        result.output = stdout
        if rc != 0:
            result.error = stderr or f"Skill exited with code {rc}"
        return result

    # ── Private matchers ─────────────────────────────────────────────

    def _match_skill(self, search_terms: list[str]) -> tuple | None:
        """Match against skills/router.route entries, then skill manifests."""
        from skills.runner import match_skill
        for term in search_terms:
            result = match_skill(term)
            if result:
                return result
        return None

    def _match_routes(self, search_terms: list[str]) -> list[RouteMatch]:
        """Match against all loaded routes in ScaffoldState."""
        matches = []
        seen = set()

        for filename, entries in self._state.routes.items():
            for entry in entries:
                for term in search_terms:
                    score = self._score_match(term, entry.concept, entry.path, entry.description)
                    if score > 0:
                        key = (filename, entry.concept, entry.path)
                        if key not in seen:
                            seen.add(key)
                            matches.append(RouteMatch(
                                concept=entry.concept,
                                path=entry.path,
                                description=entry.description,
                                source_file=filename,
                                score=score,
                            ))
        return matches

    def _match_headers(self, search_terms: list[str]) -> list[HeaderMatch]:
        """Match against header modules."""
        matches = []
        seen = set()

        for filename, data in self._state.headers.items():
            for module in data.get("modules", []):
                for term in search_terms:
                    score = self._score_header(term, module)
                    if score > 0:
                        key = (filename, module["name"])
                        if key not in seen:
                            seen.add(key)
                            matches.append(HeaderMatch(
                                module_name=module["name"],
                                source_file=filename,
                                tags=module.get("tags", []),
                                exports=module.get("exports", []),
                                score=score,
                            ))
        return matches

    @staticmethod
    def best_score(result: QueryResult) -> float:
        """Return the highest score among route and header matches. 0.0 if none."""
        scores = [rm.score for rm in result.route_matches] + \
                 [hm.score for hm in result.header_matches]
        if result.skill_match:
            scores.append(1.0)
        return max(scores, default=0.0)

    def needs_llm_fallback(self, result: QueryResult) -> bool:
        """True when QueryEngine result is below the LLM fallback threshold."""
        from llm.base import LLM_FALLBACK_THRESHOLD
        return self.best_score(result) < LLM_FALLBACK_THRESHOLD

    @staticmethod
    def _score_match(term: str, concept: str, path: str, description: str) -> float:
        """Score a route match. Returns 0.0 if no match."""
        term = term.lower()
        concept_l = concept.lower()
        path_l = path.lower()
        desc_l = description.lower()

        # Exact concept match
        if term == concept_l:
            return 1.0
        # Concept contains term
        if term in concept_l:
            return 0.8
        # Term contains concept (broader query)
        if concept_l in term and len(concept_l) > 2:
            return 0.6
        # Path match
        if term in path_l:
            return 0.5
        # Description match
        if term in desc_l:
            return 0.3
        return 0.0

    @staticmethod
    def _score_header(term: str, module: dict) -> float:
        """Score a header module match. Returns 0.0 if no match."""
        term = term.lower()
        name = module.get("name", "").lower()
        tags = [t.lower() for t in module.get("tags", [])]
        exports = [e.lower() for e in module.get("exports", [])]

        # Exact name match
        if term == name:
            return 1.0
        # Name contains term
        if term in name:
            return 0.8
        # Tag match
        if term in tags:
            return 0.7
        # Export match
        for exp in exports:
            if term in exp:
                return 0.5
        return 0.0
