"""Agentic chat capability."""

from __future__ import annotations

from deeptutor.agents.chat.agentic_pipeline import CHAT_OPTIONAL_TOOLS, AgenticChatPipeline
from deeptutor.core.capability_protocol import BaseCapability, CapabilityManifest
from deeptutor.core.context import UnifiedContext
from deeptutor.core.stream_bus import StreamBus
from deeptutor.runtime.request_contracts import get_capability_request_schema
from deeptutor.services.config.capabilities_settings import get_chat_params
from deeptutor.services.llm.config import get_llm_config, set_scoped_llm_config


class ChatCapability(BaseCapability):
    manifest = CapabilityManifest(
        name="chat",
        description=(
            "Agentic chat: an exploring agent loop with tools, followed by "
            "a respond stage that streams the answer."
        ),
        stages=["exploring", "responding"],
        tools_used=CHAT_OPTIONAL_TOOLS,
        cli_aliases=["chat"],
        request_schema=get_capability_request_schema("chat"),
    )

    async def run(self, context: UnifiedContext, stream: StreamBus) -> None:
        # Per-capability model override from agents.yaml
        params = get_chat_params()
        cap_model = params.get("model")
        if cap_model:
            scoped = get_llm_config().model_copy({"model": cap_model})
            set_scoped_llm_config(scoped)

        pipeline = AgenticChatPipeline(language=context.language)
        await pipeline.run(context, stream)
