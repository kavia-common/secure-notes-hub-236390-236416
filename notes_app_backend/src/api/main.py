from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.core.settings import get_settings
from src.api.routers.auth import router as auth_router
from src.api.routers.notes import router as notes_router
from src.api.routers.tags import router as tags_router

openapi_tags = [
    {"name": "health", "description": "Service health and diagnostics."},
    {"name": "auth", "description": "Email/password authentication and JWT issuance."},
    {"name": "notes", "description": "Secure CRUD and search for notes (per-user access control)."},
    {"name": "tags", "description": "Per-user tags for filtering notes."},
]

settings = get_settings()

app = FastAPI(
    title="Secure Notes Hub API",
    description=(
        "Backend API for a secure notes app.\n\n"
        "- JWT auth via email/password\n"
        "- Notes CRUD with autosave-friendly PATCH\n"
        "- Tag listing and note filtering\n"
        "- Strict access control: users can only access their own notes\n"
    ),
    version="1.0.0",
    openapi_tags=openapi_tags,
)

origins = [o.strip() for o in (settings.cors_allow_origins or "").split(",") if o.strip()]
if not origins:
    # Safe default for local dev; for deployments set CORS_ALLOW_ORIGINS to the frontend URL.
    origins = ["http://localhost:3000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(notes_router)
app.include_router(tags_router)


@app.get("/", tags=["health"], summary="Health check", operation_id="health_check")
def health_check():
    """
    Health check endpoint.

    Returns a simple payload to verify the API is running.
    """
    return {"message": "Healthy"}
