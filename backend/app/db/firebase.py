import asyncio
import json
import logging
import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1.base_query import FieldFilter
from google.cloud.firestore import transactional

from app.core.config import settings

logger = logging.getLogger(__name__)

db_client = None

def init_firebase():
    global db_client
    if firebase_admin._apps:
        try:
            db_client = firestore.client()
        except Exception:
            pass
        return

    # Initialize SDK
    if settings.FIREBASE_CREDENTIALS:
        try:
            creds_dict = json.loads(settings.FIREBASE_CREDENTIALS)
            cred = credentials.Certificate(creds_dict)
            firebase_admin.initialize_app(cred)
            logger.info("Firebase initialized using environment variable credentials.")
        except Exception as e:
            logger.error(f"Failed to load Firebase credentials from env: {e}")
            raise e
    elif settings.FIREBASE_CREDENTIALS_PATH:
        try:
            cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
            firebase_admin.initialize_app(cred)
            logger.info(f"Firebase initialized using file credentials: {settings.FIREBASE_CREDENTIALS_PATH}")
        except Exception as e:
            logger.error(f"Failed to load Firebase credentials from file: {e}")
            raise e
    else:
        # Fallback to default application credentials
        try:
            firebase_admin.initialize_app()
            logger.info("Firebase initialized using application default credentials.")
        except Exception as e:
            logger.warning(f"Failed to initialize Firebase with defaults: {e}. Falling back to default app initialization.")
            try:
                firebase_admin.initialize_app()
            except Exception:
                pass

    try:
        db_client = firestore.client()
    except Exception as e:
        logger.error(f"Failed to get firestore client: {e}")
        db_client = None

class FirebaseClient:
    def __init__(self):
        global db_client
        if db_client is None:
            init_firebase()
        self.db = db_client

    async def get_next_id(self, collection_name: str) -> int:
        """Atomic counter for auto-incrementing integer IDs."""
        if not self.db:
            return 1
        
        counter_ref = self.db.collection("counters").document(collection_name)
        
        @transactional
        def tx_func(transaction, ref):
            snapshot = ref.get(transaction=transaction)
            if snapshot.exists:
                current = snapshot.get("value")
            else:
                current = 0
            new_val = current + 1
            transaction.set(ref, {"value": new_val})
            return new_val
            
        transaction = self.db.transaction()
        next_id = await asyncio.to_thread(tx_func, transaction, counter_ref)
        return next_id

    async def get(self, collection: str, doc_id: str | int) -> dict | None:
        if not self.db:
            return None
        ref = self.db.collection(collection).document(str(doc_id))
        doc = await asyncio.to_thread(ref.get)
        if doc.exists:
            return doc.to_dict()
        return None

    async def insert(self, collection: str, doc_id: str | int, data: dict) -> None:
        if not self.db:
            return
        ref = self.db.collection(collection).document(str(doc_id))
        await asyncio.to_thread(ref.set, data)

    async def update(self, collection: str, doc_id: str | int, data: dict) -> None:
        if not self.db:
            return
        ref = self.db.collection(collection).document(str(doc_id))
        await asyncio.to_thread(ref.update, data)

    async def delete(self, collection: str, doc_id: str | int) -> None:
        if not self.db:
            return
        ref = self.db.collection(collection).document(str(doc_id))
        await asyncio.to_thread(ref.delete)

    async def query(self, collection: str, filters: list[tuple[str, str, any]] = None, order_by: str = None, order_desc: bool = False, limit: int = None, offset: int = None) -> list[dict]:
        if not self.db:
            return []
        ref = self.db.collection(collection)
        
        # Apply filters
        if filters:
            for field, op, val in filters:
                ref = ref.where(filter=FieldFilter(field, op, val))
                
        # Apply ordering
        if order_by:
            direction = firestore.Query.DESCENDING if order_desc else firestore.Query.ASCENDING
            ref = ref.order_by(order_by, direction=direction)
            
        # Apply offset and limit
        if offset is not None:
            ref = ref.offset(offset)
        if limit is not None:
            ref = ref.limit(limit)
            
        docs = await asyncio.to_thread(ref.get)
        return [doc.to_dict() for doc in docs]
