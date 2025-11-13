import os
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from bson import ObjectId

from database import db, create_document, get_documents
from schemas import Item, Activity

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Tracking API running"}

@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    import os
    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"

    return response

# Utility to convert Mongo document to JSON-safe dict

def serialize_doc(doc):
    if not doc:
        return doc
    doc = dict(doc)
    _id = doc.get("_id")
    if isinstance(_id, ObjectId):
        doc["id"] = str(_id)
        del doc["_id"]
    # Convert datetime fields to isoformat
    for k, v in list(doc.items()):
        if isinstance(v, datetime):
            doc[k] = v.isoformat()
    return doc

# Request models for updates
class UpdateItem(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    due_date: Optional[datetime] = None
    tags: Optional[List[str]] = None

@app.post("/api/items")
def create_item(item: Item):
    try:
        inserted_id = create_document("item", item)
        # log activity
        create_document("activity", Activity(item_id=inserted_id, action="created", detail=f"Item '{item.title}' created"))
        doc = db["item"].find_one({"_id": ObjectId(inserted_id)})
        return serialize_doc(doc)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/items")
def list_items(q: Optional[str] = None, status: Optional[str] = None):
    filter_q = {}
    if q:
        filter_q["title"] = {"$regex": q, "$options": "i"}
    if status:
        filter_q["status"] = status
    try:
        docs = get_documents("item", filter_q)
        return [serialize_doc(d) for d in docs]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/items/{item_id}")
def get_item(item_id: str):
    try:
        doc = db["item"].find_one({"_id": ObjectId(item_id)})
        if not doc:
            raise HTTPException(status_code=404, detail="Item not found")
        return serialize_doc(doc)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.patch("/api/items/{item_id}")
def update_item(item_id: str, update: UpdateItem):
    try:
        payload = {k: v for k, v in update.model_dump(exclude_unset=True).items()}
        if not payload:
            return {"updated": False}
        payload["updated_at"] = datetime.utcnow()
        res = db["item"].update_one({"_id": ObjectId(item_id)}, {"$set": payload})
        if res.matched_count == 0:
            raise HTTPException(status_code=404, detail="Item not found")
        # log activity
        create_document("activity", Activity(item_id=item_id, action="updated", detail=f"Item updated: {list(payload.keys())}"))
        doc = db["item"].find_one({"_id": ObjectId(item_id)})
        return serialize_doc(doc)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/items/{item_id}")
def delete_item(item_id: str):
    try:
        res = db["item"].delete_one({"_id": ObjectId(item_id)})
        if res.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Item not found")
        create_document("activity", Activity(item_id=item_id, action="deleted", detail="Item deleted"))
        return {"deleted": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/items/{item_id}/activity")
def get_activity(item_id: str):
    try:
        docs = get_documents("activity", {"item_id": item_id})
        return [serialize_doc(d) for d in docs]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
