from pydantic import BaseModel


class OrderRead(BaseModel):
    id: int
    user_id: int
    from_address: str
    to_address: str
    status: str
    driver_id: int | None

    model_config = {"from_attributes": True}
