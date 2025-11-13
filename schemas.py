"""
Database Schemas

Define your MongoDB collection schemas here using Pydantic models.
These schemas are used for data validation in your application.

Each Pydantic model represents a collection in your database.
Model name is converted to lowercase for the collection name:
- User -> "user" collection
- Product -> "product" collection
- BlogPost -> "blogs" collection
"""

from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime

# Core tracker schemas

class Item(BaseModel):
    """
    Items to track
    Collection name: "item"
    """
    title: str = Field(..., min_length=1, max_length=200, description="Short title")
    description: Optional[str] = Field(None, max_length=2000, description="Detailed notes")
    status: Literal["Open", "In Progress", "Done"] = Field("Open", description="Workflow status")
    due_date: Optional[datetime] = Field(None, description="Optional due date")
    tags: Optional[list[str]] = Field(default_factory=list, description="Optional tags")

class Activity(BaseModel):
    """
    Activity history for items
    Collection name: "activity"
    """
    item_id: str = Field(..., description="Related item id as string")
    action: Literal["created", "updated", "status_changed", "deleted"] = Field(...)
    detail: Optional[str] = Field(None, description="Human readable description")

# Example schemas (kept for reference, not used by app)
class User(BaseModel):
    name: str
    email: str
    address: str
    age: Optional[int] = None
    is_active: bool = True

class Product(BaseModel):
    title: str
    description: Optional[str] = None
    price: float
    category: str
    in_stock: bool = True
