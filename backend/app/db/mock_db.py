import json
import asyncio
from pathlib import Path

from app.core.config import PROJECT_ROOT

class LocalDBClient:
    """A local JSON-based mock for FirebaseClient to bypass Quota Exhausted errors."""
    def __init__(self):
        self.db_file = PROJECT_ROOT / "data" / "local_db.json"
        self.data = {}
        self._load()

    def _load(self):
        if self.db_file.exists():
            with open(self.db_file, "r", encoding="utf-8") as f:
                try:
                    self.data = json.load(f)
                except Exception:
                    self.data = {}
        else:
            self.data = {}

    def _save(self):
        self.db_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.db_file, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2)

    async def get_next_id(self, collection_name: str) -> int:
        if "counters" not in self.data:
            self.data["counters"] = {}
        if collection_name not in self.data["counters"]:
            self.data["counters"][collection_name] = {"value": 0}
        
        self.data["counters"][collection_name]["value"] += 1
        self._save()
        return self.data["counters"][collection_name]["value"]

    async def get(self, collection: str, doc_id: str | int) -> dict | None:
        return self.data.get(collection, {}).get(str(doc_id))

    async def insert(self, collection: str, doc_id: str | int, data: dict) -> None:
        if collection not in self.data:
            self.data[collection] = {}
        
        # Serialize datetime objects if present
        safe_data = {}
        for k, v in data.items():
            if hasattr(v, "isoformat"):
                safe_data[k] = v.isoformat()
            else:
                safe_data[k] = v
                
        self.data[collection][str(doc_id)] = safe_data
        self._save()

    async def update(self, collection: str, doc_id: str | int, data: dict) -> None:
        if collection not in self.data:
            self.data[collection] = {}
        if str(doc_id) not in self.data[collection]:
            self.data[collection][str(doc_id)] = {}
            
        safe_data = {}
        for k, v in data.items():
            if hasattr(v, "isoformat"):
                safe_data[k] = v.isoformat()
            else:
                safe_data[k] = v
                
        self.data[collection][str(doc_id)].update(safe_data)
        self._save()

    async def delete(self, collection: str, doc_id: str | int) -> None:
        if collection in self.data and str(doc_id) in self.data[collection]:
            del self.data[collection][str(doc_id)]
            self._save()

    async def query(self, collection: str, filters: list[tuple[str, str, any]] = None, order_by: str = None, order_desc: bool = False, limit: int = None, offset: int = None) -> list[dict]:
        docs = list(self.data.get(collection, {}).values())
        if filters:
            for field, op, val in filters:
                if op == "==":
                    docs = [d for d in docs if d.get(field) == val]
                elif op == ">":
                    docs = [d for d in docs if d.get(field, "") > val]
                elif op == "<":
                    docs = [d for d in docs if d.get(field, "") < val]
                elif op == ">=":
                    docs = [d for d in docs if d.get(field, "") >= val]
                elif op == "<=":
                    docs = [d for d in docs if d.get(field, "") <= val]
                elif op == "in":
                    docs = [d for d in docs if d.get(field) in val]
                    
        if order_by:
            docs.sort(key=lambda x: x.get(order_by, ""), reverse=order_desc)
            
        if offset is not None:
            docs = docs[offset:]
        if limit is not None:
            docs = docs[:limit]
            
        return docs
