from agent_cli.core.agent import Agent, DEFAULT_PERSONA
from agent_cli.core.sessions import SessionStore
from agent_cli.llm.provider import LLMProvider
from agent_cli.config import DEFAULT_MODEL


class AgentManager:
    """Manages Agent instances per session. One active agent at a time."""

    def __init__(self, provider: LLMProvider, store: SessionStore) -> None:
        self.provider = provider
        self.store = store
        self._agents: dict[str, Agent] = {}
        self._models: dict[str, str] = {}
        self._profiles: dict[str, str] = {}

    def get_or_create(
        self,
        session_id: str,
        persona: str = "",
        model: str = "",
        profile_content: str = "",
        invariants: list[str] | None = None,
    ) -> Agent:
        if session_id in self._agents:
            return self._agents[session_id]

        try:
            memory, stats, saved_model = self.store.load_session(session_id)
            agent = Agent(
                provider=self.provider,
                persona=persona or DEFAULT_PERSONA,
                model=model or saved_model or DEFAULT_MODEL,
                profile_content=profile_content,
                invariants=invariants,
            )
            agent.memory = memory
            agent.session_stats = stats
        except KeyError:
            agent = Agent(
                provider=self.provider,
                persona=persona or DEFAULT_PERSONA,
                model=model or DEFAULT_MODEL,
                profile_content=profile_content,
                invariants=invariants,
            )

        self._agents[session_id] = agent
        self._models[session_id] = agent.model
        self._profiles[session_id] = profile_content
        return agent

    def save(self, session_id: str) -> None:
        agent = self._agents.get(session_id)
        if not agent:
            return
        if not self.store.get_meta(session_id):
            return  # ephemeral session not in DB — skip
        self.store.save_session(
            session_id,
            agent.memory,
            agent.session_stats,
            model=agent.model,
            profile_name=self._profiles.get(session_id, ""),
        )

    def remove(self, session_id: str) -> None:
        self._agents.pop(session_id, None)
        self._models.pop(session_id, None)
        self._profiles.pop(session_id, None)
