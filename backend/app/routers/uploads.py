"""Upload router.

Endpoints for file uploads (quest proof photos, screenshots).
"""

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from fastapi.responses import FileResponse

from app.config import settings
from app.core.dependencies import get_current_user

router = APIRouter(prefix="/uploads", tags=["Uploads"])

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


def _get_upload_dir() -> Path:
    """Get or create the upload directory."""
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)
    return upload_dir


@router.post("/proof", status_code=status.HTTP_201_CREATED)
async def upload_proof(
    file: UploadFile,
    current_user=Depends(get_current_user),
):
    """Upload a proof image for a quest.

    Returns the URL path to access the uploaded file.
    """
    # Validate content type
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not allowed. Allowed: {', '.join(ALLOWED_TYPES)}",
        )

    # Read and validate size
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size: {MAX_FILE_SIZE // (1024 * 1024)} MB",
        )

    # Generate unique filename
    ext = Path(file.filename or "image.jpg").suffix or ".jpg"
    filename = f"{uuid.uuid4()}{ext}"

    # Save file
    upload_dir = _get_upload_dir()
    file_path = upload_dir / filename
    file_path.write_bytes(content)

    return {
        "filename": filename,
        "url": f"/api/v1/uploads/files/{filename}",
        "size": len(content),
        "content_type": file.content_type,
    }


@router.get("/files/{filename}")
async def get_uploaded_file(
    filename: str,
    current_user=Depends(get_current_user),
):
    """Serve an uploaded file."""
    # Prevent path traversal
    if "/" in filename or "\\" in filename or ".." in filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid filename",
        )

    upload_dir = _get_upload_dir()
    file_path = upload_dir / filename

    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found",
        )

    return FileResponse(file_path)
