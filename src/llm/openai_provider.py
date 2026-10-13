import json
import logging
from typing import Dict, Optional
from openai import OpenAI
from src.schemas import WorkflowDefinition, WorkflowSelection
from src.llm.base import BaseLLMProvider
from src.llm.mock_provider import MockLLMProvider
from src.config import OPENAI_API_KEY, OPENAI_MODEL, LLM_TEMPERATURE

logger = logging.getLogger(__name__)


class OpenAIProvider(BaseLLMProvider):
    """
    Live LLM Provider using OpenAI API with structured output / JSON mode.
    Falls back gracefully to MockLLMProvider if API connection fails or key is missing.
    """

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or OPENAI_API_KEY
        self.model = model or OPENAI_MODEL
        self.client = OpenAI(api_key=self.api_key) if self.api_key else None
        self.mock_fallback = MockLLMProvider()

    def route_request(
        self,
        user_request: str,
        available_workflows: Dict[str, WorkflowDefinition]
    ) -> WorkflowSelection:
        if not self.client:
            logger.info("OpenAI API key not set; using deterministic mock provider for routing.")
            return self.mock_fallback.route_request(user_request, available_workflows)

        # Prepare summary of available workflows for system prompt
        wf_summaries = []
        for wf_id, wf in available_workflows.items():
            wf_summaries.append(
                f"- ID: {wf_id} | Name: {wf.workflow_name} | Trigger: {wf.trigger} | Inputs: {wf.inputs}"
            )
        workflows_text = "\n".join(wf_summaries)

        system_prompt = (
            "You are an AI Workflow Router for an enterprise automation platform. "
            "Your job is to inspect the user's natural language request and select the exact workflow ID "
            "from the registered list below.\n\n"
            "REGISTERED WORKFLOWS:\n"
            f"{workflows_text}\n\n"
            "Return a strictly valid JSON object with the following fields:\n"
            "{\n"
            '  "workflow_id": "WF001" or null if no match or unsupported,\n'
            '  "workflow_name": "Exact Name" or null,\n'
            '  "confidence": float between 0.0 and 1.0,\n'
            '  "reasoning": "Clear explanation of match",\n'
            '  "extracted_params": {key: value},\n'
            '  "is_ambiguous": boolean,\n'
            '  "clarification_prompt": "string if ambiguous or missing"\n'
            "}\n"
            "Do NOT invent workflow IDs. Only use IDs from the registered list."
        )

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                temperature=LLM_TEMPERATURE,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"User Request: {user_request}"}
                ]
            )
            raw_content = response.choices[0].message.content or "{}"
            parsed = json.loads(raw_content)

            wf_id = parsed.get("workflow_id")
            if wf_id and wf_id not in available_workflows:
                logger.warning(f"LLM proposed invalid workflow ID '{wf_id}'. Falling back.")
                wf_id = None

            return WorkflowSelection(
                workflow_id=wf_id,
                workflow_name=available_workflows[wf_id].workflow_name if wf_id else None,
                confidence=float(parsed.get("confidence", 0.8)),
                reasoning=str(parsed.get("reasoning", "Identified by OpenAI model.")),
                extracted_params=dict(parsed.get("extracted_params", {})),
                is_ambiguous=bool(parsed.get("is_ambiguous", False)),
                clarification_prompt=parsed.get("clarification_prompt")
            )
        except Exception as e:
            logger.warning(f"OpenAI routing failed with error: {e}. Falling back to deterministic router.")
            return self.mock_fallback.route_request(user_request, available_workflows)

    def generate_text(self, prompt: str, system_prompt: str = "") -> str:
        if not self.client:
            return self.mock_fallback.generate_text(prompt, system_prompt)

        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            response = self.client.chat.completions.create(
                model=self.model,
                temperature=LLM_TEMPERATURE,
                messages=messages
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            logger.warning(f"OpenAI text generation failed: {e}. Falling back to mock generator.")
            return self.mock_fallback.generate_text(prompt, system_prompt)
