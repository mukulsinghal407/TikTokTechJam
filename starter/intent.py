from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from ollama import chat

from starter.helper.config import SYSTEM_PROMPT,MODEL   
from starter.helper.dataclasses import TurnClassification, TokenUsage


@dataclass
class IntentTracker:
    attributes: dict[str, str] = field(default_factory= lambda: {
        "category": "",
        "material": "",
        "color": "",
        "size": "", #only numbers are allowed no text or symbols
        "style": "",
        "brand": "",
        "budget": "", #only numbers are allowed no text or symbols
        "feature": "",
        "use_case": ""
    })
    model: str = MODEL
    usage_history: list[TokenUsage] = field(default_factory=list)
    conversation_history: list[str] = field(default_factory=list)

    @property
    def total_prompt_tokens(self) -> int:
        return sum(u.prompt_tokens for u in self.usage_history)
 
    @property
    def total_completion_tokens(self) -> int:
        return sum(u.completion_tokens for u in self.usage_history)
 
    @property
    def total_tokens(self) -> int:
        return sum(u.total_tokens for u in self.usage_history)


    def update(self, user_message: str) -> TurnClassification:
        user_payload = json.dumps(
            {"current_attributes": self.attributes, "user_message": user_message, "conversation_history": self.conversation_history},
            ensure_ascii=False,
        )
        response = chat(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_payload},
            ],
            format=TurnClassification.model_json_schema(),
            options={"temperature": 0},
        )
        self.usage_history.append(TokenUsage(
            prompt_tokens=response.prompt_eval_count or 0,
            completion_tokens=response.eval_count or 0,
        ))
        result = TurnClassification.model_validate_json(response.message.content)
        
        self.attributes.update(result.all_updated_attributes)
        self.conversation_history.append(user_message)
        return result