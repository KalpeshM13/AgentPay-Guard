import asyncio
import json
import logging
import firebase_admin
from firebase_admin import credentials, firestore

from app.core.config import settings

logger = logging.getLogger(__name__)

db_client = None
_memory_store: dict[str, dict[str, dict]] = {}
_memory_counters: dict[str, int] = {}

def init_firebase():
    global db_client
    if firebase_admin._apps:
        try:
            db_client = firestore.client()
        except Exception:
            db_client = None
        return

    # Initialize SDK if credentials provided
    if settings.FIREBASE_CREDENTIALS:
        try:
            creds_dict = json.loads(settings.FIREBASE_CREDENTIALS)
            cred = credentials.Certificate(creds_dict)
            firebase_admin.initialize_app(cred)
            logger.info("Firebase initialized using environment variable credentials.")
            db_client = firestore.client()
        except Exception as e:
            logger.error(f"Failed to load Firebase credentials from env: {e}")
            db_client = None
    elif settings.FIREBASE_CREDENTIALS_PATH:
        try:
            cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
            firebase_admin.initialize_app(cred)
            logger.info(f"Firebase initialized using file credentials: {settings.FIREBASE_CREDENTIALS_PATH}")
            db_client = firestore.client()
        except Exception as e:
            logger.error(f"Failed to load Firebase credentials from file: {e}")
            db_client = None
    else:
        logger.info("No Firebase credentials specified. Using local memory database engine.")
        db_client = None

class FirebaseClient:
    def __init__(self):
        global db_client
        if db_client is None and not firebase_admin._apps:
            init_firebase()
        self.db = db_client

    async def get_next_id(self, collection_name: str) -> int:
        """Atomic counter for auto-incrementing integer IDs."""
        if self.db:
            counter_ref = self.db.collection("counters").document(collection_name)
            
            @firestore.transactional
            def tx_func(transaction, ref):
                snapshot = ref.get(transaction=transaction)
                current = snapshot.get("value") if snapshot.exists else 0
                new_val = current + 1
                transaction.set(ref, {"value": new_val})
                return new_val
                
            transaction = self.db.transaction()
            return await asyncio.to_thread(tx_func, transaction, counter_ref)
        else:
            global _memory_counters
            current = _memory_counters.get(collection_name, 0)
            new_val = current + 1
            _memory_counters[collection_name] = new_val
            return new_val

    async def get(self, collection: str, doc_id: str | int) -> dict | None:
        if self.db:
            ref = self.db.collection(collection).document(str(doc_id))
            doc = await asyncio.to_thread(ref.get)
            return doc.to_dict() if doc.exists else None
        else:
            doc = _memory_store.get(collection, {}).get(str(doc_id))
            return dict(doc) if doc is not None else None

    async def insert(self, collection: str, doc_id: str | int, data: dict) -> None:
        if self.db:
            ref = self.db.collection(collection).document(str(doc_id))
            await asyncio.to_thread(ref.set, data)
        else:
            _memory_store.setdefault(collection, {})[str(doc_id)] = dict(data)

    async def update(self, collection: str, doc_id: str | int, data: dict) -> None:
        if self.db:
            ref = self.db.collection(collection).document(str(doc_id))
            await asyncio.to_thread(ref.update, data)
        else:
            if str(doc_id) in _memory_store.get(collection, {}):
                _memory_store[collection][str(doc_id)].update(data)

    async def delete(self, collection: str, doc_id: str | int) -> None:
        if self.db:
            ref = self.db.collection(collection).document(str(doc_id))
            await asyncio.to_thread(ref.delete)
        else:
            if collection in _memory_store:
                _memory_store[collection].pop(str(doc_id), None)

    async def query(self, collection: str, filters: list[tuple[str, str, any]] = None, order_by: str = None, order_desc: bool = False, limit: int = None, offset: int = None) -> list[dict]:
        if self.db:
            from google.cloud.firestore_v1.base_query import FieldFilter
            ref = self.db.collection(collection)
            
            if filters:
                for field, op, val in filters:
                    ref = ref.where(filter=FieldFilter(field, op, val))
                    
            if order_by:
                direction = firestore.Query.DESCENDING if order_desc else firestore.Query.ASCENDING
                ref = ref.order_by(order_by, direction=direction)
                
            if offset is not None:
                ref = ref.offset(offset)
            if limit is not None:
                ref = ref.limit(limit)
                
            docs = await asyncio.to_thread(ref.get)
            return [doc.to_dict() for doc in docs]
        else:
            results = list(_memory_store.get(collection, {}).values())
            
            # Filter
            if filters:
                for field, op, val in filters:
                    def matches(doc, f=field, o=op, v=val):
                        item = doc.get(f)
                        if o in ("==", "=="):
                            return item == v
                        if o == "!=":
                            return item != v
                        if o == "in":
                            return item in v
                        if o == "array_contains":
                            return isinstance(item, list) and v in item
                        if o == ">":
                            return item is not None and item > v
                        if o == ">=":
                            return item is not None and item >= v
                        if o == "<":
                            return item is not None and item < v
                        if o == "<=":
                            return item is not None and item <= v
                        return True
                    results = [d for d in results if matches(d)]
            
            # Sort
            if order_by:
                results.sort(key=lambda d: d.get(order_by, 0), reverse=order_desc)
                
            # Offset & Limit
            if offset:
                results = results[offset:]
            if limit is not None:
                results = results[:limit]
                
            return [dict(d) for d in results]
