from app.llm.base import LLMProvider, LLMRequest, LLMResponse
from app.llm.providers import OpenAICompatibleProvider
from app.llm.vast.templates import DRY_RUN_TEST_RESPONSE
from app.models.vast_session import VastSessionModel


class VastEphemeralProvider(LLMProvider):
    name = "vast_ephemeral"

    def __init__(self, session: VastSessionModel, dry_run: bool = True) -> None:
        self.session = session
        self.model = session.model
        self.dry_run = dry_run

    def generate(self, request: LLMRequest) -> LLMResponse:
        if self.dry_run:
            return LLMResponse(
                text=DRY_RUN_TEST_RESPONSE,
                provider=self.name,
                model=self.model,
            )
        if not self.session.public_endpoint_url:
            raise RuntimeError("Vast session endpoint is unavailable")
        provider = OpenAICompatibleProvider(
            self.session.public_endpoint_url.rstrip("/"),
            api_key="",
            model=self.model,
        )
        response = provider.generate(request)
        return LLMResponse(text=response.text, provider=self.name, model=response.model)
