from pydantic import BaseModel

from app.models.push import DevicePlatform


class DeviceTokenRegister(BaseModel):
    platform: DevicePlatform
    token: str


class NotificationPreferencesOut(BaseModel):
    application_updates: bool
    deadlines: bool
    job_matches: bool
    scholarships: bool
    company_intelligence: bool
    preparation_reminders: bool

    model_config = {"from_attributes": True}


class NotificationPreferencesUpdate(BaseModel):
    application_updates: bool | None = None
    deadlines: bool | None = None
    job_matches: bool | None = None
    scholarships: bool | None = None
    company_intelligence: bool | None = None
    preparation_reminders: bool | None = None
