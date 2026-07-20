from pydantic import BaseModel, Field
from typing import Optional

# -----------------
# User Schemas
# -----------------
class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)

class UserCreate(UserBase):
    password: str = Field(..., min_length=6)
    is_admin: Optional[bool] = False

class UserResponse(UserBase):
    id: str
    is_admin: bool

    class Config:
        from_attributes = True

class UserUpdate(BaseModel):
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    password: Optional[str] = Field(None, min_length=6)
    is_admin: Optional[bool] = None

class PasswordChangeRequest(BaseModel):
    current_password: str = Field(..., min_length=6)
    new_password: str = Field(..., min_length=6)

# -----------------
# Auth / Token Schemas
# -----------------
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

# -----------------
# Inventory Item Schemas
# -----------------
class InventoryItemBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")  # YYYY-MM-DD
    type: str = Field(..., min_length=1, max_length=50)
    weight: str = Field(..., min_length=1, max_length=50)
    cost: float = Field(..., ge=0.0)
    price: float = Field(..., ge=0.0)
    custom_id: Optional[str] = None

class InventoryItemCreate(InventoryItemBase):
    pass

class InventoryItemResponse(InventoryItemBase):
    id: str
    photo_name: Optional[str] = None
    added_by_id: str
    added_by: UserResponse

    class Config:
        from_attributes = True

# -----------------
# System Config Schemas
# -----------------
class SystemConfigResponse(BaseModel):
    key: str
    value: str

    class Config:
        from_attributes = True

class SystemConfigUpdate(BaseModel):
    value: str

