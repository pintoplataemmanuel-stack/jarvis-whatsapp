from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class EvolutionKey(BaseModel):
    model_config = ConfigDict(extra="ignore")

    remote_jid: str | None = Field(default=None, alias="remoteJid")
    from_me: bool = Field(default=False, alias="fromMe")
    id: str | None = None


class EvolutionMessage(BaseModel):
    model_config = ConfigDict(extra="allow")

    conversation: str | None = None
    extended_text_message: dict[str, Any] | None = Field(default=None, alias="extendedTextMessage")
    audio_message: dict[str, Any] | None = Field(default=None, alias="audioMessage")
    ptt_message: dict[str, Any] | None = Field(default=None, alias="pttMessage")


class EvolutionData(BaseModel):
    model_config = ConfigDict(extra="ignore")

    key: EvolutionKey | None = None
    push_name: str | None = Field(default=None, alias="pushName")
    message: EvolutionMessage | None = None
    message_type: str | None = Field(default=None, alias="messageType")
    message_timestamp: str | int | None = Field(default=None, alias="messageTimestamp")


class EvolutionWebhookPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")

    event: str
    instance: str | None = None
    data: EvolutionData | None = None
