"""Structured prompt assembly for the chat agent loop."""

from __future__ import annotations

import hashlib
from typing import Any

from deeptutor.capabilities.protocol import PromptBlock
from deeptutor.core.context import UnifiedContext
from deeptutor.services.prompt.language import append_language_directive

# Per-session L3 content hash cache for delta injection.
# Avoids re-injecting unchanged L3 memory across turns within the same session.
_l3_content_cache: dict[str, str] = {}


class ChatPromptAssembler:
    """Build system prompts from explicit, category-named blocks."""

    def __init__(self, *, prompts: dict[str, Any], language: str) -> None:
        self.prompts = prompts
        self.language = "zh" if language.lower().startswith("zh") else "en"

    def system_prompt(
        self,
        *,
        context: UnifiedContext,
        tool_manifest: str,
        kb_note: str = "",
        deferred_tools_manifest: str = "",
        notebook_manifest: str = "",
        workspace_note: str = "",
        capability_blocks: list[PromptBlock] | None = None,
        include_tool_manifest: bool = True,
        include_volatile_blocks: bool = True,
    ) -> str:
        blocks = self.blocks(
            context=context,
            tool_manifest=tool_manifest,
            kb_note=kb_note,
            deferred_tools_manifest=deferred_tools_manifest,
            notebook_manifest=notebook_manifest,
            workspace_note=workspace_note,
            capability_blocks=capability_blocks,
            include_tool_manifest=include_tool_manifest,
            include_volatile_blocks=include_volatile_blocks,
        )
        joined = "\n\n---\n\n".join(
            f"## {block.name}\n{block.content.strip()}" for block in blocks if block.content.strip()
        )
        return append_language_directive(joined, self.language)

    def blocks(
        self,
        *,
        context: UnifiedContext,
        tool_manifest: str,
        kb_note: str = "",
        deferred_tools_manifest: str = "",
        notebook_manifest: str = "",
        workspace_note: str = "",
        capability_blocks: list[PromptBlock] | None = None,
        include_tool_manifest: bool = True,
        include_volatile_blocks: bool = True,
    ) -> list[PromptBlock]:
        blocks: list[PromptBlock] = [
            PromptBlock("general", self._general_block(context)),
            PromptBlock("runtime_policy", self._t("runtime_policy")),
            PromptBlock("loop", self._t("loop.system")),
        ]
        # Capability playbooks sit high so they frame the whole turn when active;
        # empty blocks are omitted by ``system_prompt``'s join.
        blocks.extend(capability_blocks or [])
        if context.persona_context:
            blocks.append(PromptBlock("persona_style", context.persona_context))
        partner_policy = self._partner_turn_policy(context)
        if partner_policy:
            blocks.append(PromptBlock("partner_turn_policy", partner_policy))
        if context.memory_context:
            mem_hash = hashlib.sha256(context.memory_context.encode()).hexdigest()
            session_id = context.session_id or "default"
            prev_hash = _l3_content_cache.get(session_id)
            if prev_hash != mem_hash:
                # Relevance gate: skip memory injection when user message has
                # negligible keyword overlap with L3 content.
                if self._is_memory_relevant(context.memory_context, context.user_message):
                    blocks.append(PromptBlock("memory", context.memory_context))
                _l3_content_cache[session_id] = mem_hash
        # Volatile blocks 8-13: tools, skills, sources, extended_tools, notebooks, workspace
        # Skipped in later rounds when prefixed content is already cached by the LLM.
        if not include_volatile_blocks:
            return blocks
        if include_tool_manifest:
            tools = tool_manifest or self._fallback_empty_tool_list()
            if kb_note:
                tools = f"{kb_note}\n\n{tools}"
            blocks.append(PromptBlock("tools", tools))
        elif kb_note:
            blocks.append(PromptBlock("knowledge_base_note", kb_note))
        if context.skills_manifest:
            blocks.append(PromptBlock("skills", context.skills_manifest))
        if context.source_manifest:
            blocks.append(PromptBlock("sources", context.source_manifest))
        if deferred_tools_manifest:
            blocks.append(PromptBlock("extended_tools", deferred_tools_manifest))
        if notebook_manifest:
            blocks.append(PromptBlock("notebooks", notebook_manifest))
        if workspace_note:
            blocks.append(PromptBlock("workspace", workspace_note))
        return blocks

    @staticmethod
    def _is_memory_relevant(memory_content: str, user_message: str) -> bool:
        """Return True if L3 memory has meaningful keyword overlap with the user message.

        Simple token-set intersection: only skip memory when there is virtually
        no shared vocabulary between the user query and the accumulated memory.
        This is intentionally lenient — it only gates truly orthogonal pairings
        (e.g. "solve 2x=4" vs memory full of biology notes).
        """
        if not user_message.strip():
            return True
        mem_tokens = set(memory_content.lower().split())
        msg_tokens = set(user_message.lower().split())
        if not msg_tokens:
            return True
        overlap = mem_tokens & msg_tokens
        ratio = len(overlap) / len(msg_tokens)
        return ratio >= 0.05

    def _general_block(self, context: UnifiedContext) -> str:
        """Product identity, or the partner identity when one is present.

        Partner turns carry ``metadata["agent_identity"]`` (user-given name +
        description); their identity comes from that and the Soul block, so
        the "You are DeepTutor" general is swapped for ``general_partner``.
        Chat turns carry no identity and render the general block unchanged.
        """
        identity = context.metadata.get("agent_identity")
        name = ""
        if isinstance(identity, dict):
            name = str(identity.get("name") or "").strip()
        if not name:
            return self._t("general")
        content = self._t(
            "general_partner",
            default='You are a companion created by the user. The name the user gave you is "{name}".',
        ).format(name=name)
        description = str(identity.get("description") or "").strip()
        if description:
            description_line = self._t(
                "general_partner_description",
                default="The user's description of you: {description}",
            ).format(description=description)
            content = f"{content}\n{description_line}"
        return content

    def _partner_turn_policy(self, context: UnifiedContext) -> str:
        identity = context.metadata.get("agent_identity")
        if not isinstance(identity, dict):
            return ""
        if not str(identity.get("name") or "").strip():
            return ""
        return self._t("partner_turn_policy", default="")

    def user_message(
        self,
        *,
        context: UnifiedContext,
        kb_seed: str = "",
    ) -> str:
        template = self._t("loop.user", default="{user_message}")
        try:
            content = template.format(user_message=context.user_message)
        except (KeyError, IndexError, ValueError):
            content = context.user_message
        if kb_seed:
            content = f"{content}\n\n{kb_seed}"
        return content

    def finish_exhausted_instruction(self) -> str:
        return self._t(
            "loop.finish_exhausted",
            default=(
                "The round budget ran out before every gap was closed. Stop "
                "calling tools and answer now with what you have, noting "
                "briefly what remains uncertain."
            ),
        )

    def _fallback_empty_tool_list(self) -> str:
        return "- 无" if self.language == "zh" else "- none"

    def _t(self, key: str, default: str = "") -> str:
        value: Any = self.prompts
        for part in key.split("."):
            if not isinstance(value, dict) or part not in value:
                return default
            value = value[part]
        return value if isinstance(value, str) else default


__all__ = ["ChatPromptAssembler", "PromptBlock"]
