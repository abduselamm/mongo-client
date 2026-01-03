from fastapi import APIRouter, Body, HTTPException, status, Response
from typing import List, Dict, Any, Union
from bson import ObjectId
from bson.errors import InvalidId
from database import db

router = APIRouter()

def get_id_filter(id: str) -> dict:
    try:
        return {"_id": ObjectId(id)}
    except InvalidId:
        return {"_id": id}

def map_document(document: Dict[str, Any]) -> Dict[str, Any]:
    if document and "_id" in document:
        document["_id"] = str(document["_id"])
    return document

from datetime import datetime

def parse_extended_json(data: Any) -> Any:
    """
    Recursively parse MongoDB Extended JSON formats to native BSON types.
    Handles:
    - {"$oid": "..."} -> ObjectId("...")
    - {"$date": "..."} -> datetime
    - {"$date": {"$numberLong": "..."}} -> datetime from timestamp
    """
    if isinstance(data, dict):
        if "$oid" in data and len(data) == 1:
            try:
                return ObjectId(data["$oid"])
            except InvalidId:
                return data["$oid"] # Fallback or error?
        
        if "$date" in data and len(data) == 1:
            date_val = data["$date"]
            if isinstance(date_val, dict) and "$numberLong" in date_val:
                # Timestamp in milliseconds
                try:
                    ts = int(date_val["$numberLong"])
                    # Python datetime min year is 1. Handle out of range.
                    return datetime.fromtimestamp(ts / 1000.0)
                except (ValueError, OSError, OverflowError):
                    # Fallback for dates out of Python's range (e.g. year 0 or negative years)
                    # We return the timestamp as integer so it's stored safely, 
                    # or we could clamp to datetime.min. Storing as int preserves the value.
                    return int(date_val["$numberLong"])

            if isinstance(date_val, str):
                 # ISO format string
                 try:
                     return datetime.fromisoformat(date_val.replace("Z", "+00:00"))
                 except ValueError:
                     pass
            return date_val

        return {k: parse_extended_json(v) for k, v in data.items()}
    
    if isinstance(data, list):
        return [parse_extended_json(item) for item in data]
    
    return data

@router.post("/{collection_name}/", response_description="Add new document(s)", summary="Create document(s) dynamically", response_model=Union[Dict[str, Any], List[Dict[str, Any]]])
async def create_document(collection_name: str, document: Union[Dict[str, Any], List[Dict[str, Any]]] = Body(...)):
    """
    Create new document(s) in the specified collection.
    Accepts a single JSON object or a list of JSON objects.
    Automatically converts Extended JSON formats (like "$oid", "$date") to BSON.
    """
    # Parse Extended JSON
    parsed_document = parse_extended_json(document)

    if isinstance(parsed_document, list):
        if not parsed_document:
            raise HTTPException(status_code=400, detail="Empty list provided")
        
        result = await db[collection_name].insert_many(parsed_document)
        
        # Fetch inserted documents
        inserted_ids = result.inserted_ids
        created_docs = await db[collection_name].find({"_id": {"$in": inserted_ids}}).to_list(len(inserted_ids))
        return [map_document(doc) for doc in created_docs]

    # Single document
    new_doc = await db[collection_name].insert_one(parsed_document)
    created_doc = await db[collection_name].find_one({"_id": new_doc.inserted_id})
    return map_document(created_doc)

@router.get("/{collection_name}/", response_description="List all documents", summary="List documents", response_model=List[Dict[str, Any]])
async def list_documents(collection_name: str):
    """
    Retrieve a list of all documents in the collection (capped at 1000).
    """
    documents = await db[collection_name].find().to_list(1000)
    return [map_document(doc) for doc in documents]

@router.get("/{collection_name}/{id}", response_description="Get a single document", summary="Get document by ID", response_model=Dict[str, Any])
async def show_document(collection_name: str, id: str):
    """
    Retrieve a specific document by its unique ID.
    Try to match ObjectId, falls back to string ID.
    """
    filter_query = get_id_filter(id)
    if (doc := await db[collection_name].find_one(filter_query)) is not None:
        return map_document(doc)
    raise HTTPException(status_code=404, detail=f"Document {id} not found in {collection_name}")

@router.patch("/{collection_name}/{id}", response_description="Update a document", summary="Update document", response_model=Dict[str, Any])
async def update_document(collection_name: str, id: str, document: Dict[str, Any] = Body(...)):
    """
    Update an existing document by its ID.
    Accepts partial updates.
    """
    filter_query = get_id_filter(id)
    
    # Exclude _id from update payload
    if "_id" in document:
        del document["_id"]

    if len(document) >= 1:
        update_result = await db[collection_name].update_one(filter_query, {"$set": document})
        if update_result.matched_count == 0:
             raise HTTPException(status_code=404, detail=f"Document {id} not found in {collection_name}")

    if (doc := await db[collection_name].find_one(filter_query)) is not None:
        return map_document(doc)
    
    raise HTTPException(status_code=404, detail=f"Document {id} not found in {collection_name}")

@router.delete("/{collection_name}/{id}", response_description="Delete a document", summary="Delete document")
async def delete_document(collection_name: str, id: str):
    """
    Remove a document from the collection by its ID.
    """
    filter_query = get_id_filter(id)
    delete_result = await db[collection_name].delete_one(filter_query)

    if delete_result.deleted_count == 1:
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    raise HTTPException(status_code=404, detail=f"Document {id} not found in {collection_name}")
