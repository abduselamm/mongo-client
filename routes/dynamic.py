from fastapi import APIRouter, Body, HTTPException, status, Response
from typing import List, Dict, Any, Union
from bson import ObjectId
from bson.errors import InvalidId
from database import db

router = APIRouter()

from datetime import datetime

def get_id_filter(id: str) -> dict:
    try:
        return {"_id": ObjectId(id)}
    except InvalidId:
        return {"_id": id}

def get_id_filters(id: str) -> list:
    """Return all plausible filter variants for a given id string."""
    filters = [{"_id": id}]  # string match always included
    try:
        filters.insert(0, {"_id": ObjectId(id)})  # prefer ObjectId
    except InvalidId:
        pass
    return filters

def map_document(document: Dict[str, Any]) -> Dict[str, Any]:
    def _map_types(val: Any) -> Any:
        if isinstance(val, dict):
            return {k: _map_types(v) for k, v in val.items()}
        elif isinstance(val, list):
            return [_map_types(item) for item in val]
        elif isinstance(val, datetime):
            iso_str = val.isoformat(timespec='milliseconds')
            if val.tzinfo is None:
                iso_str += 'Z'
            elif iso_str.endswith('+00:00'):
                iso_str = iso_str[:-6] + 'Z'
            return {"$date": iso_str}
        elif isinstance(val, ObjectId):
            return {"$oid": str(val)}
        return val

    if not document:
        return document
        
    mapped = _map_types(document)
    if "_id" in mapped:
        if isinstance(mapped["_id"], dict) and "$oid" in mapped["_id"]:
            mapped["_id"] = mapped["_id"]["$oid"]
        else:
            mapped["_id"] = str(mapped["_id"])
    return mapped

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

@router.get("/_sys/collections", response_description="List all collections", summary="List collections", response_model=List[str])
async def list_collections():
    """
    Retrieve a list of all existing collection names in the current database.
    """
    collections = await db.list_collection_names()
    return collections

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
async def list_documents(collection_name: str, skip: int = 0, limit: int = 0):
    """
    Retrieve documents in the collection.
    - skip: number of documents to skip (for pagination)
    - limit: max documents to return; 0 means no limit (return all)
    """
    cursor = db[collection_name].find().skip(skip)
    if limit > 0:
        cursor = cursor.limit(limit)
    documents = await cursor.to_list(length=None)
    return [map_document(doc) for doc in documents]

@router.post("/{collection_name}/query", response_description="Run filter query", summary="Run a query against a collection", response_model=List[Dict[str, Any]])
async def run_query(collection_name: str, query: Dict[str, Any] = Body(...)):
    """
    Run a MongoDB filter query against the specified collection and return matching documents.
    Accepts extended JSON filters and converts them.
    Limited to 1000 items to prevent massive result payloads payload.
    """
    parsed_query = parse_extended_json(query)
    cursor = db[collection_name].find(parsed_query)
    documents = await cursor.to_list(length=1000)
    return [map_document(doc) for doc in documents]


@router.get("/{collection_name}/{id}", response_description="Get a single document", summary="Get document by ID", response_model=Dict[str, Any])
async def show_document(collection_name: str, id: str):
    """
    Retrieve a specific document by its unique ID.
    Try to match ObjectId, falls back to string ID.
    """
    for filter_query in get_id_filters(id):
        if (doc := await db[collection_name].find_one(filter_query)) is not None:
            return map_document(doc)
    raise HTTPException(status_code=404, detail=f"Document {id} not found in {collection_name}")

@router.patch("/{collection_name}/{id}", response_description="Update a document", summary="Update document", response_model=Dict[str, Any])
async def update_document(collection_name: str, id: str, document: Dict[str, Any] = Body(...)):
    """
    Update an existing document by its ID.
    Accepts partial updates. Tries ObjectId and string _id variants so documents
    are found regardless of how the _id was stored.
    """
    # Exclude _id from update payload
    if "_id" in document:
        del document["_id"]

    parsed_document = parse_extended_json(document)

    matched_filter = None
    if len(parsed_document) >= 1:
        for filter_query in get_id_filters(id):
            update_result = await db[collection_name].update_one(filter_query, {"$set": parsed_document})
            if update_result.matched_count > 0:
                matched_filter = filter_query
                break
        if matched_filter is None:
            raise HTTPException(status_code=404, detail=f"Document {id} not found in {collection_name}")
    else:
        # Nothing to update — just resolve the filter used for returning the doc
        for filter_query in get_id_filters(id):
            if await db[collection_name].count_documents(filter_query, limit=1):
                matched_filter = filter_query
                break
        if matched_filter is None:
            raise HTTPException(status_code=404, detail=f"Document {id} not found in {collection_name}")

    if (doc := await db[collection_name].find_one(matched_filter)) is not None:
        return map_document(doc)

    raise HTTPException(status_code=404, detail=f"Document {id} not found in {collection_name}")

@router.delete("/{collection_name}/", response_description="Delete a collection", summary="Delete collection")
async def delete_collection(collection_name: str):
    """
    Drop a collection from the database.
    """
    await db[collection_name].drop()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@router.delete("/{collection_name}/documents", response_description="Delete all documents", summary="Delete all documents")
async def delete_all_documents(collection_name: str):
    """
    Delete all documents in a collection without dropping the collection itself.
    """
    delete_result = await db[collection_name].delete_many({})
    return {"deleted_count": delete_result.deleted_count}

@router.delete("/{collection_name}/{id}", response_description="Delete a document", summary="Delete document")
async def delete_document(collection_name: str, id: str):
    """
    Remove a document from the collection by its ID.
    """
    for filter_query in get_id_filters(id):
        delete_result = await db[collection_name].delete_one(filter_query)
        if delete_result.deleted_count == 1:
            return Response(status_code=status.HTTP_204_NO_CONTENT)

    raise HTTPException(status_code=404, detail=f"Document {id} not found in {collection_name}")
