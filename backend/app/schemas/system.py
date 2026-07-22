from pydantic import BaseModel


class PublicSystemConfigResponse(BaseModel):
    registration_enabled: bool
