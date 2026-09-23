from enum import Enum

from fastapi import FastAPI, HTTPException, status
from sqlmodel import Field, SQLModel, Session, create_engine, select


# =========================================================
# STATUS ENUM
# =========================================================

class ItemStatus(str, Enum):
    LOST = "Lost"
    FOUND = "Found"
    RETURNED = "Returned"


# =========================================================
# DATABASE MODEL
# =========================================================

class Item(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)

    title: str
    description: str
    category: str
    location: str
    reported_by: str
    status: ItemStatus


# =========================================================
# INPUT / REQUEST MODEL
# =========================================================

class ItemCreate(SQLModel):
    title: str = Field(min_length=1)
    description: str = Field(min_length=5)
    category: str = Field(min_length=1)
    location: str = Field(min_length=1)
    reported_by: str = Field(min_length=1)
    status: ItemStatus


# =========================================================
# DATABASE CONFIGURATION
# =========================================================

DATABASE_URL = "sqlite:///./database.db"

engine = create_engine(
    DATABASE_URL,
    echo=True,
    connect_args={"check_same_thread": False}
)


# =========================================================
# FASTAPI APPLICATION
# =========================================================

app = FastAPI(
    title="Campus Lost & Found API",
    description="REST API for managing lost and found items on campus",
    version="1.0.0"
)


# =========================================================
# CREATE DATABASE TABLES ON STARTUP
# =========================================================

@app.on_event("startup")
def create_tables():
    SQLModel.metadata.create_all(engine)


# =========================================================
# POST /items
# Create a new lost/found item
# =========================================================

@app.post(
    "/items",
    response_model=Item,
    status_code=status.HTTP_201_CREATED
)
def create_item(item: ItemCreate):

    with Session(engine) as session:

        # Convert request model into database model
        db_item = Item.model_validate(item)

        session.add(db_item)
        session.commit()
        session.refresh(db_item)

        return db_item


# =========================================================
# GET /items
# Return all items
# =========================================================

@app.get(
    "/items",
    response_model=list[Item]
)
def get_items():

    with Session(engine) as session:

        statement = select(Item)

        items = session.exec(statement).all()

        return items


# =========================================================
# GET /items/{item_id}
# Return a specific item
# =========================================================

@app.get(
    "/items/{item_id}",
    response_model=Item
)
def get_item(item_id: int):

    with Session(engine) as session:

        item = session.get(Item, item_id)

        if item is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Item not found"
            )

        return item


# =========================================================
# PUT /items/{item_id}
# Update an existing item
# =========================================================

@app.put(
    "/items/{item_id}",
    response_model=Item
)
def update_item(
    item_id: int,
    updated_item: ItemCreate
):

    with Session(engine) as session:

        existing_item = session.get(Item, item_id)

        if existing_item is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Item not found"
            )

        existing_item.title = updated_item.title
        existing_item.description = updated_item.description
        existing_item.category = updated_item.category
        existing_item.location = updated_item.location
        existing_item.reported_by = updated_item.reported_by
        existing_item.status = updated_item.status

        session.add(existing_item)
        session.commit()
        session.refresh(existing_item)

        return existing_item


# =========================================================
# DELETE /items/{item_id}
# Delete an item
# =========================================================

@app.delete(
    "/items/{item_id}"
)
def delete_item(item_id: int):

    with Session(engine) as session:

        item = session.get(Item, item_id)

        if item is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Item not found"
            )

        session.delete(item)
        session.commit()

        return {
            "message": "Item deleted successfully",
            "id": item_id
        }


# =========================================================
# GET /items/status/{status}
# Filter items by status
# =========================================================

@app.get(
    "/items/status/{status}",
    response_model=list[Item]
)
def get_items_by_status(status: ItemStatus):

    with Session(engine) as session:

        statement = select(Item).where(
            Item.status == status
        )

        items = session.exec(statement).all()

        return items


# =========================================================
# GET /items/category/{category}
# Filter items by category
# =========================================================

@app.get(
    "/items/category/{category}",
    response_model=list[Item]
)
def get_items_by_category(category: str):

    with Session(engine) as session:

        statement = select(Item).where(
            Item.category == category
        )

        items = session.exec(statement).all()

        return items