import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import List, Optional
import requests

from schemas import Place, Guide, Event, Tour, Booking, PremiumContent
from database import create_document, get_documents, db

app = FastAPI(title="VisitPazar API", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "VisitPazar Backend is running"}

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
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = getattr(db, 'name', None) or "Unknown"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["connection_status"] = "Connected"
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️ Connected but Error: {str(e)[:80]}"
        else:
            response["database"] = "⚠️ Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:80]}"

    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
    return response

# --------------------------- WIKIPEDIA INTEGRATIONS ---------------------------
WIKI_SUMMARY_URL = "https://en.wikipedia.org/api/rest_v1/page/summary/{title}"
WIKI_SEARCH_URL = "https://en.wikipedia.org/w/api.php"


def fetch_wikipedia_summary(title: str) -> dict:
    try:
        # Try REST summary first (often includes thumbnail)
        r = requests.get(WIKI_SUMMARY_URL.format(title=title), timeout=6)
        if r.status_code == 200:
            data = r.json()
            return {
                "title": data.get("title"),
                "extract": data.get("extract"),
                "thumbnail": (data.get("thumbnail") or {}).get("source"),
                "content_urls": (data.get("content_urls") or {}).get("desktop", {}).get("page")
            }
        # Fallback to search
        params = {
            "action": "query",
            "format": "json",
            "prop": "pageimages|extracts",
            "exintro": 1,
            "explaintext": 1,
            "piprop": "thumbnail",
            "pithumbsize": 800,
            "titles": title,
        }
        r2 = requests.get(WIKI_SEARCH_URL, params=params, timeout=6)
        if r2.status_code == 200:
            j = r2.json()
            pages = j.get("query", {}).get("pages", {})
            for _, p in pages.items():
                return {
                    "title": p.get("title"),
                    "extract": p.get("extract"),
                    "thumbnail": (p.get("thumbnail") or {}).get("source"),
                    "content_urls": f"https://en.wikipedia.org/wiki/{p.get('title').replace(' ', '_')}" if p.get('title') else None
                }
        return {"title": title}
    except Exception:
        return {"title": title}

@app.get("/api/wiki/summary")
def wiki_summary(title: str):
    if not title:
        raise HTTPException(status_code=400, detail="title is required")
    return fetch_wikipedia_summary(title)

@app.get("/api/wiki/search")
def wiki_search(query: str, limit: int = 5):
    try:
        params = {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "srlimit": min(max(limit, 1), 10),
            "format": "json"
        }
        r = requests.get(WIKI_SEARCH_URL, params=params, timeout=6)
        r.raise_for_status()
        data = r.json().get("query", {}).get("search", [])
        return [{"title": i.get("title"), "snippet": i.get("snippet")} for i in data]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --------------------------- PLACES ---------------------------
@app.get("/api/places", response_model=List[Place])
def list_places(type: Optional[str] = None, recommended: Optional[bool] = None):
    try:
        query = {}
        if type:
            query["type"] = type
        if recommended is not None:
            query["is_recommended"] = recommended
        docs = get_documents("place", query, limit=100)
        cleaned = []
        for d in docs:
            d.pop("_id", None)
            cleaned.append(Place(**d))
        return cleaned
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/places")
def create_place(place: Place):
    try:
        data = place.model_dump()
        # If no images provided, try Wikipedia thumbnail by name
        if not data.get("images") and data.get("name"):
            wi = fetch_wikipedia_summary(data["name"]) or {}
            thumb = wi.get("thumbnail")
            if thumb:
                data["images"] = [thumb]
            # If description missing, use extract
            if not data.get("description") and wi.get("extract"):
                data["description"] = wi["extract"][:800]
        inserted_id = create_document("place", Place(**data))
        return {"id": inserted_id, "status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/recommended", response_model=List[Place])
def list_recommended():
    try:
        docs = get_documents("place", {"is_recommended": True}, limit=50)
        for d in docs:
            d.pop("_id", None)
        return [Place(**d) for d in docs]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --------------------------- GUIDES ---------------------------
@app.get("/api/guides", response_model=List[Guide])
def list_guides():
    try:
        docs = get_documents("guide", {}, limit=100)
        for d in docs:
            d.pop("_id", None)
        return [Guide(**d) for d in docs]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/guides")
def create_guide(guide: Guide):
    try:
        inserted_id = create_document("guide", guide)
        return {"id": inserted_id, "status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --------------------------- EVENTS ---------------------------
@app.get("/api/events", response_model=List[Event])
def list_events():
    try:
        docs = get_documents("event", {}, limit=100)
        for d in docs:
            d.pop("_id", None)
        return [Event(**d) for d in docs]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/events")
def create_event(event: Event):
    try:
        inserted_id = create_document("event", event)
        return {"id": inserted_id, "status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --------------------------- TOURS ---------------------------
@app.get("/api/tours", response_model=List[Tour])
def list_tours():
    try:
        docs = get_documents("tour", {}, limit=100)
        for d in docs:
            d.pop("_id", None)
        return [Tour(**d) for d in docs]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/tours")
def create_tour(tour: Tour):
    try:
        inserted_id = create_document("tour", tour)
        return {"id": inserted_id, "status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --------------------------- PREMIUM CONTENT ---------------------------
@app.get("/api/premium", response_model=List[PremiumContent])
def list_premium():
    try:
        docs = get_documents("premiumcontent", {"is_active": True}, limit=100)
        for d in docs:
            d.pop("_id", None)
        return [PremiumContent(**d) for d in docs]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/premium")
def create_premium(content: PremiumContent):
    try:
        inserted_id = create_document("premiumcontent", content)
        return {"id": inserted_id, "status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --------------------------- BOOKINGS ---------------------------
@app.post("/api/bookings")
def create_booking(booking: Booking):
    try:
        inserted_id = create_document("booking", booking)
        return {"id": inserted_id, "status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --------------------------- MONETIZATION PREVIEW ---------------------------
@app.get("/api/monetization")
def monetization_overview():
    return {
        "streams": [
            {"name": "Istaknuta mesta (sponzorisano)", "range_eur_per_month": "50-100", "example": "40 partnera => ~2.000€/mes"},
            {"name": "Provizija od rezervacija", "percent": 10},
            {"name": "Premium vodiči i AR ture", "price_eur": "1-3 po sadržaju"},
            {"name": "Sponzorisani događaji", "note": "Festivali, gradski projekti"}
        ]
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
