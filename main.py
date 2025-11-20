import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from typing import Any, Dict

from database import create_document
from schemas import Lead

import io
import tarfile

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
    return {"message": "Solar Leads API Running"}

@app.get("/api/hello")
def hello():
    return {"message": "Hello from the backend API!"}

@app.post("/api/leads")
def create_lead(lead: Lead) -> Dict[str, Any]:
    try:
        lead_id = create_document("lead", lead)
        return {"status": "ok", "id": lead_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    
    try:
        # Try to import database module
        from database import db
        
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            
            # Try to list collections to verify connectivity
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]  # Show first 10 collections
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
            
    except ImportError:
        response["database"] = "❌ Database module not found (run enable-database first)"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"
    
    # Check environment variables
    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
    
    return response


@app.get("/download-backend")
def download_backend_tar():
    """Stream a tar.gz archive of the backend project (excluding virtual/ephemeral files)."""
    buffer = io.BytesIO()

    excludes = {".git", "__pycache__", "logs", ".env", ".venv", "env", ".pytest_cache"}

    def _filter(ti: tarfile.TarInfo) -> tarfile.TarInfo | None:
        parts = ti.name.split(os.sep)
        if any(part in excludes for part in parts):
            return None
        # Prevent absolute paths
        ti.name = os.path.join("backend", ti.name)
        return ti

    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        for root, dirs, files in os.walk("."):
            # prune excluded directories during walk
            dirs[:] = [d for d in dirs if d not in excludes]
            for name in files:
                if name in excludes:
                    continue
                full_path = os.path.join(root, name)
                rel_path = os.path.relpath(full_path, ".")
                if any(seg in excludes for seg in rel_path.split(os.sep)):
                    continue
                ti = tar.gettarinfo(full_path, arcname=rel_path)
                if ti is None:
                    continue
                ti = _filter(ti)
                if ti is None:
                    continue
                with open(full_path, "rb") as f:
                    tar.addfile(ti, f)

    buffer.seek(0)
    headers = {"Content-Disposition": "attachment; filename=backend.tar.gz"}
    return StreamingResponse(buffer, media_type="application/gzip", headers=headers)


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
