import logging
import re
import base64
from struct import pack

from hydrogram.file_id import FileId
from pymongo import MongoClient, TEXT
from pymongo.errors import DuplicateKeyError

from info import USE_CAPTION_FILTER, DATABASE_URL, DATABASE_NAME, MAX_BTN

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────
# ⚙️ MONGODB CONNECTION (POOL OPTIMIZED)
# ─────────────────────────────────────────
client = MongoClient(
    DATABASE_URL,
    maxPoolSize=50,
    minPoolSize=10,
    maxIdleTimeMS=45000
)
db = client[DATABASE_NAME]

primary = db["Primary"]
cloud   = db["Cloud"]
archive = db["Archive"]

COLLECTIONS = {
    "primary": primary,
    "cloud": cloud,
    "archive": archive
}

# ─────────────────────────────────────────
# ⚡ INDEXES (ABSOLUTE MUST)
# ─────────────────────────────────────────
def ensure_indexes():
    for name, col in COLLECTIONS.items():
        col.create_index(
            [("file_name", TEXT), ("caption", TEXT)],
            name=f"{name}_text"
        )

ensure_indexes()

# ─────────────────────────────────────────
# 🧠 FAST NORMALIZER (NO CPU COST)
# ─────────────────────────────────────────
REPLACEMENTS = str.maketrans({
    "0": "o", "1": "i", "3": "e",
    "4": "a", "5": "s", "7": "t"
})

def normalize_query(q: str) -> str:
    q = q.lower().translate(REPLACEMENTS)
    q = re.sub(r"[^a-z0-9\s]", " ", q)
    return re.sub(r"\s+", " ", q).strip()

def prefix_query(q: str) -> str:
    return " ".join(w[:4] for w in q.split() if len(w) >= 3)

# ─────────────────────────────────────────
# 📊 DB STATS (FAST)
# ─────────────────────────────────────────
def db_count_documents():
    p = primary.estimated_document_count()
    c = cloud.estimated_document_count()
    a = archive.estimated_document_count()
    return {
        "primary": p,
        "cloud": c,
        "archive": a,
        "total": p + c + a
    }

# ─────────────────────────────────────────
# 💾 SAVE FILE (FAST & SAFE)
# ─────────────────────────────────────────
async def save_file(media, collection_type="primary"):
    file_id = unpack_new_file_id(media.file_id)

    doc = {
        "_id": file_id,
        "file_name": re.sub(r"@\w+", "", media.file_name or "").strip(),
        "caption": re.sub(r"@\w+", "", media.caption or "").strip(),
        "file_size": media.file_size
    }

    col = COLLECTIONS.get(collection_type, primary)

    try:
        col.insert_one(doc)
        return "suc"
    except DuplicateKeyError:
        return "dup"

# ─────────────────────────────────────────
# 🔍 ULTRA FAST SEARCH CORE
# ─────────────────────────────────────────
def _text_filter(q):
    return {"$text": {"$search": q}}

def _search(col, q, offset, limit):
    cursor = (
        col.find(
            _text_filter(q),
            {
                "file_name": 1,
                "file_size": 1,
                "caption": 1,
                "score": {"$meta": "textScore"}
            }
        )
        .sort([("score", {"$meta": "textScore"})])
        .skip(offset)
        .limit(limit)
    )
    docs = list(cursor)
    count = col.count_documents(_text_filter(q))
    return docs, count

# ─────────────────────────────────────────
# 🚀 PUBLIC SEARCH API (ULTRA FAST)
# ─────────────────────────────────────────
async def get_search_results(
    query,
    max_results=MAX_BTN,
    offset=0,
    lang=None,
    collection_type="primary"
):
    query = normalize_query(query)
    prefix = prefix_query(query)

    results = []
    total = 0

    # Select collections
    if collection_type in COLLECTIONS:
        cols = [COLLECTIONS[collection_type]]
    else:
        cols = [primary, cloud, archive]

    # 1️⃣ TEXT SEARCH (MAIN)
    for col in cols:
        need = max_results - len(results)
        if need <= 0:
            break

        docs, cnt = _search(col, query, offset, need)
        results.extend(docs)
        total += cnt

    # 2️⃣ PREFIX FALLBACK (ONLY IF EMPTY)
    if not results and prefix:
        for col in cols:
            docs, cnt = _search(col, prefix, 0, max_results)
            results.extend(docs)
            total += cnt
            if results:
                break

    # 3️⃣ LANG FILTER (VERY SMALL LOOP)
    if lang:
        lang = lang.lower()
        results = [f for f in results if lang in f["file_name"].lower()]
        total = len(results)

    next_offset = offset + max_results
    if next_offset >= total:
        next_offset = ""

    return results, next_offset, total

# ─────────────────────────────────────────
# 🗑 DELETE FILES (IMPROVED)
# ─────────────────────────────────────────
async def delete_files(query, collection_type="all"):
    """
    Delete files from database
    
    Args:
        query: File name to search (use "*" for all files)
        collection_type: "primary", "cloud", "archive", or "all"
    
    Returns:
        Number of deleted files
    """
    deleted = 0
    
    # Special case: Delete ALL files
    if query == "*":
        for name, col in COLLECTIONS.items():
            if collection_type != "all" and name != collection_type:
                continue
            result = col.delete_many({})
            deleted += result.deleted_count
            logger.info(f"Deleted {result.deleted_count} files from {name}")
        return deleted
    
    # Normal case: Delete by query
    query = normalize_query(query)
    flt = _text_filter(query)

    for name, col in COLLECTIONS.items():
        if collection_type != "all" and name != collection_type:
            continue
        result = col.delete_many(flt)
        deleted += result.deleted_count
        logger.info(f"Deleted {result.deleted_count} files matching '{query}' from {name}")

    return deleted

# ─────────────────────────────────────────
# 📂 FILE DETAILS
# ─────────────────────────────────────────
async def get_file_details(file_id):
    for col in COLLECTIONS.values():
        doc = col.find_one({"_id": file_id})
        if doc:
            return doc
    return None

# ─────────────────────────────────────────
# 🔁 MOVE FILES (SAFE)
# ─────────────────────────────────────────
async def move_files(query, from_collection, to_collection):
    """
    Move files from one collection to another
    
    Args:
        query: Search query to find files
        from_collection: Source collection ("primary", "cloud", or "archive")
        to_collection: Destination collection ("primary", "cloud", or "archive")
    
    Returns:
        Number of moved files
    """
    query = normalize_query(query)
    src = COLLECTIONS.get(from_collection)
    dst = COLLECTIONS.get(to_collection)
    
    if not src or not dst:
        logger.error(f"Invalid collection names: {from_collection} -> {to_collection}")
        return 0

    moved = 0
    for doc in src.find(_text_filter(query)):
        try:
            dst.insert_one(doc)
        except DuplicateKeyError:
            logger.warning(f"File {doc['_id']} already exists in {to_collection}")
            pass
        src.delete_one({"_id": doc["_id"]})
        moved += 1

    logger.info(f"Moved {moved} files from {from_collection} to {to_collection}")
    return moved

# ─────────────────────────────────────────
# 📋 GET ALL FILES FROM COLLECTION
# ─────────────────────────────────────────
async def get_all_files(collection_type="primary", limit=100, skip=0):
    """
    Get all files from a specific collection
    
    Args:
        collection_type: "primary", "cloud", or "archive"
        limit: Number of files to return
        skip: Number of files to skip (for pagination)
    
    Returns:
        List of file documents
    """
    col = COLLECTIONS.get(collection_type, primary)
    files = list(col.find().skip(skip).limit(limit))
    return files

# ─────────────────────────────────────────
# 🔐 FILE ID UTILS
# ─────────────────────────────────────────
def encode_file_id(s: bytes) -> str:
    r, n = b"", 0
    for i in s + bytes([22, 4]):
        if i == 0:
            n += 1
        else:
            if n:
                r += b"\x00" + bytes([n])
                n = 0
            r += bytes([i])
    return base64.urlsafe_b64encode(r).decode().rstrip("=")

def unpack_new_file_id(new_file_id):
    d = FileId.decode(new_file_id)
    return encode_file_id(pack(
        "<iiqq",
        int(d.file_type),
        d.dc_id,
        d.media_id,
        d.access_hash
    ))
