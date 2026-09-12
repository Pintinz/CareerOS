from pydantic import BaseModel


class ProfileOut(BaseModel):
    full_name: str | None = None
    profile_picture_url: str | None = None
    professional_title: str | None = None
    location: str | None = None
    years_of_experience: int | None = None
    highest_education: str | None = None
    field_of_study: str | None = None

    model_config = {"from_attributes": True}


class ProfileUpdate(BaseModel):
    full_name: str | None = None
    profile_picture_url: str | None = None
    professional_title: str | None = None
    location: str | None = None
    years_of_experience: int | None = None
    highest_education: str | None = None
    field_of_study: str | None = None
