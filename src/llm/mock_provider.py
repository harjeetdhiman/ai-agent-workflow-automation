import re
from typing import Dict, Any, List
from difflib import SequenceMatcher
from src.schemas import WorkflowDefinition, WorkflowSelection
from src.llm.base import BaseLLMProvider

_STOPWORDS = {
    "a", "an", "the", "and", "or", "in", "on", "at", "to", "for", "with", "by",
    "is", "are", "was", "were", "be", "this", "that", "these", "those", "of",
    "from", "what", "which", "how", "who", "where", "can", "could", "please",
    "me", "my", "our", "all", "any", "some", "do", "does", "did", "show", "get",
    "find", "check", "run", "process"
}


def _stem(word: str) -> str:
    w = word.lower()
    for suffix in ["ing", "ies", "es", "ed", "s", "ure", "tion", "ment", "ance", "ence"]:
        if len(w) > len(suffix) + 2 and w.endswith(suffix):
            if suffix == "ies":
                return w[:-3] + "y"
            return w[:-len(suffix)]
    return w


def _tokenize(text: str) -> List[str]:
    words = re.findall(r"\b[a-zA-Z0-9_\-]+\b", (text or "").lower())
    tokens = []
    for w in words:
        if w not in _STOPWORDS and len(w) > 1:
            tokens.append(w)
            stemmed = _stem(w)
            if stemmed != w:
                tokens.append(stemmed)
    return tokens


class MockLLMProvider(BaseLLMProvider):
    """
    Generic, zero-cost semantic intent router and parameter extractor.
    Operates dynamically across all workflows in the loaded registry using
    token overlap and fuzzy sequence matching without any hardcoded workflow IDs.
    """

    def route_request(
        self,
        user_request: str,
        available_workflows: Dict[str, WorkflowDefinition]
    ) -> WorkflowSelection:
        query = (user_request or "").strip().lower()
        if not query:
            return WorkflowSelection(
                workflow_id=None,
                workflow_name=None,
                confidence=0.0,
                reasoning="Empty request received.",
                is_ambiguous=False
            )

        # Ambiguity check for ultra-generic short phrases
        generic_ambiguous = ["check status", "show report", "process data", "analyze", "run process"]
        if query in generic_ambiguous:
            names = [wf.workflow_name for wf in list(available_workflows.values())[:3]]
            return WorkflowSelection(
                workflow_id=None,
                workflow_name=None,
                confidence=0.30,
                reasoning="Request is too broad and could match multiple workflows.",
                is_ambiguous=True,
                clarification_prompt=f"Could you specify which workflow you would like to run? Examples: {', '.join(names)}"
            )

        q_tokens = set(_tokenize(query))
        scores: Dict[str, float] = {}
        matches_info: Dict[str, str] = {}

        for wf_id, wf in available_workflows.items():
            test_ex = " ".join(getattr(wf, "test_examples", []))
            corpus = f"{wf.workflow_name} {wf.trigger} {wf.inputs} {wf.steps_raw} {wf.expected_output} {test_ex}".lower()
            c_tokens = set(_tokenize(corpus))

            # Token overlap score
            overlap = len(q_tokens.intersection(c_tokens))
            overlap_score = overlap / max(len(q_tokens), 1)

            # Strict guard against out-of-scope queries (e.g. pizza, flights)
            if len(q_tokens) >= 3 and overlap < 2 and overlap_score < 0.30:
                continue

            # Sequence similarity against trigger and name
            sim_name = SequenceMatcher(None, query, wf.workflow_name.lower()).ratio()
            sim_trig = SequenceMatcher(None, query, wf.trigger.lower()).ratio()

            # Exact phrase match boost
            phrase_boost = 0.0
            if wf.workflow_name.lower() in query:
                phrase_boost += 0.35
            elif overlap >= 2 and any(phrase in query for phrase in _tokenize(wf.trigger)):
                phrase_boost += 0.20

            total_score = (overlap_score * 0.5) + (max(sim_name, sim_trig) * 0.3) + phrase_boost
            scores[wf_id] = total_score
            matches_info[wf_id] = f"Matched {overlap} keywords against trigger: '{wf.trigger[:40]}...'"

        if not scores:
            return WorkflowSelection(
                workflow_id=None,
                workflow_name=None,
                confidence=0.0,
                reasoning="No workflows registered in system."
            )

        sorted_wfs = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        top_id, top_score = sorted_wfs[0]

        # Minimum confidence threshold for unsupported / out-of-scope queries
        if top_score < 0.20:
            return WorkflowSelection(
                workflow_id=None,
                workflow_name=None,
                confidence=round(top_score, 2),
                reasoning="No matching workflow could be identified for this query.",
                is_ambiguous=False
            )

        # Ambiguity threshold if top 2 are nearly identical and score is mediocre
        if len(sorted_wfs) > 1:
            second_id, second_score = sorted_wfs[1]
            if top_score < 0.60 and (top_score - second_score) < 0.05:
                wf1 = available_workflows[top_id].workflow_name
                wf2 = available_workflows[second_id].workflow_name
                return WorkflowSelection(
                    workflow_id=None,
                    workflow_name=None,
                    confidence=round(top_score, 2),
                    reasoning=f"Query matches both '{wf1}' and '{wf2}' with similar confidence.",
                    is_ambiguous=True,
                    clarification_prompt=f"Did you mean {wf1} or {wf2}?"
                )

        selected_wf = available_workflows[top_id]
        extracted = self._extract_parameters(query, user_request)

        # Confidence mapped to 0.75 - 0.98 range for identified matches
        conf = min(0.98, max(0.75, round(top_score + 0.3, 2)))

        return WorkflowSelection(
            workflow_id=top_id,
            workflow_name=selected_wf.workflow_name,
            confidence=conf,
            reasoning=matches_info.get(top_id, f"Matched trigger condition for {selected_wf.workflow_name}"),
            extracted_params=extracted
        )

    def _extract_parameters(self, query: str, raw_text: str) -> Dict[str, Any]:
        """Extracts common entities, numbers, percentages, thresholds, and IDs."""
        params: Dict[str, Any] = {}

        # Percentage variance/threshold
        pct_m = re.search(r"(\d+(?:\.\d+)?)\s*%", query)
        if pct_m:
            val = float(pct_m.group(1))
            params["percentage"] = val
            params["variance_threshold"] = val / 100.0 if val > 1 else val
            params["threshold"] = val

        # Numbers / integers
        num_m = re.search(r"\b(\d+)\b", query)
        if num_m and "threshold" not in params:
            params["threshold"] = int(num_m.group(1))

        # Identifiers (e.g. ORD-1001, SKU-101, etc.)
        id_m = re.search(r"\b([A-Z]{3,4}-\d{3,5})\b", raw_text)
        if id_m:
            params["identifier"] = id_m.group(1)
            params["id"] = id_m.group(1)
            params["order_id"] = id_m.group(1)

        # Defaults for campaign brief queries
        if any(w in query for w in ["campaign", "brief", "collection"]):
            params.setdefault("campaign_goal", "Promote new collection launch")
            params.setdefault("dates", "Q4 2026")
            params.setdefault("target_audience", "Retail consumers")

        # Emails
        email_m = re.search(r"\b([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,})\b", raw_text)
        if email_m:
            params["email"] = email_m.group(1)
            params["identifier"] = email_m.group(1)

        # Key-value pairs like category: Furniture, role: Developer, etc.
        kv_pairs = re.findall(r"([a-zA-Z_]+)\s*:\s*([^,\n;]+)", raw_text)
        for k, v in kv_pairs:
            params[k.strip().lower()] = v.strip()

        return params

    def generate_text(self, prompt: str, system_prompt: str = "") -> str:
        """Deterministic mock text generation."""
        return f"Structured synthetic output based on prompt: {prompt[:80]}..."
