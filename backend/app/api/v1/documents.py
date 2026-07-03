"""Document endpoints.

Uploading (creating a document, or a new version of one) requires
repository ADMIN+, matching the create-requires-parent-ADMIN pattern used
throughout the tenancy hierarchy (docs/03-database.md section 6). Reading
requires VIEWER+; delete/restore require ADMIN+.
"""

import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, File, Request, UploadFile
from fastapi.responses import StreamingResponse

from app.api.document_deps import DocumentAccess, get_document_service, require_document_role
from app.api.tenancy_deps import require_repository_role
from app.core.exceptions import AppError
from app.core.task_queue import enqueue_finalize_upload
from app.models.membership import MemberRole
from app.models.repository import RepositoryMember
from app.schemas.common import SuccessResponse
from app.schemas.document import DocumentRead, DocumentVersionRead, DownloadResponse
from app.services.document_service import DocumentService

router = APIRouter(tags=["documents"])


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", str(uuid.uuid4()))


class _NoFilenameError(AppError):
    status_code = 400
    code = "VALIDATION_ERROR"


@router.post(
    "/repositories/{repository_id}/documents", response_model=SuccessResponse[DocumentRead]
)
async def upload_document(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    membership: RepositoryMember = Depends(require_repository_role(MemberRole.ADMIN)),
    service: DocumentService = Depends(get_document_service),
) -> SuccessResponse[DocumentRead]:
    if not file.filename:
        raise _NoFilenameError("Uploaded file must have a filename.")

    content = await file.read()
    document = await service.upload(
        repository_id=membership.repository_id,
        uploader_id=membership.user_id,
        filename=file.filename,
        content_type=file.content_type or "application/octet-stream",
        content=content,
    )
    # Scheduled via BackgroundTasks (runs after the response, i.e. after
    # `get_db`'s commit) rather than called from the service — see
    # app/services/document_service.py for why enqueueing any earlier is
    # a real race with the worker.
    background_tasks.add_task(enqueue_finalize_upload, str(document.id))
    return SuccessResponse(
        data=DocumentRead.model_validate(document), request_id=_request_id(request)
    )


@router.get(
    "/repositories/{repository_id}/documents", response_model=SuccessResponse[list[DocumentRead]]
)
async def list_documents(
    request: Request,
    membership: RepositoryMember = Depends(require_repository_role(MemberRole.VIEWER)),
    service: DocumentService = Depends(get_document_service),
) -> SuccessResponse[list[DocumentRead]]:
    documents = await service.list_by_repository(membership.repository_id)
    return SuccessResponse(
        data=[DocumentRead.model_validate(d) for d in documents], request_id=_request_id(request)
    )


@router.get("/documents/{document_id}", response_model=SuccessResponse[DocumentRead])
async def get_document(
    request: Request,
    access: DocumentAccess = Depends(require_document_role(MemberRole.VIEWER)),
) -> SuccessResponse[DocumentRead]:
    return SuccessResponse(
        data=DocumentRead.model_validate(access.document), request_id=_request_id(request)
    )


@router.get(
    "/documents/{document_id}/versions", response_model=SuccessResponse[list[DocumentVersionRead]]
)
async def list_document_versions(
    request: Request,
    access: DocumentAccess = Depends(require_document_role(MemberRole.VIEWER)),
    service: DocumentService = Depends(get_document_service),
) -> SuccessResponse[list[DocumentVersionRead]]:
    versions = await service.list_versions(access.document.id)
    return SuccessResponse(
        data=[DocumentVersionRead.model_validate(v) for v in versions],
        request_id=_request_id(request),
    )


@router.post("/documents/{document_id}/versions", response_model=SuccessResponse[DocumentRead])
async def upload_document_version(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    access: DocumentAccess = Depends(require_document_role(MemberRole.ADMIN)),
    service: DocumentService = Depends(get_document_service),
) -> SuccessResponse[DocumentRead]:
    if not file.filename:
        raise _NoFilenameError("Uploaded file must have a filename.")

    content = await file.read()
    updated = await service.create_new_version(
        access.document,
        actor_id=access.membership.user_id,
        filename=file.filename,
        content_type=file.content_type or "application/octet-stream",
        content=content,
    )
    background_tasks.add_task(enqueue_finalize_upload, str(updated.id))
    return SuccessResponse(
        data=DocumentRead.model_validate(updated), request_id=_request_id(request)
    )


@router.delete("/documents/{document_id}", response_model=SuccessResponse[dict])
async def delete_document(
    request: Request,
    access: DocumentAccess = Depends(require_document_role(MemberRole.ADMIN)),
    service: DocumentService = Depends(get_document_service),
) -> SuccessResponse[dict]:
    await service.soft_delete(access.document, actor_id=access.membership.user_id)
    return SuccessResponse(data={"deleted": True}, request_id=_request_id(request))


@router.post("/documents/{document_id}/restore", response_model=SuccessResponse[DocumentRead])
async def restore_document(
    request: Request,
    access: DocumentAccess = Depends(require_document_role(MemberRole.ADMIN, include_deleted=True)),
    service: DocumentService = Depends(get_document_service),
) -> SuccessResponse[DocumentRead]:
    restored = await service.restore(access.document, actor_id=access.membership.user_id)
    return SuccessResponse(
        data=DocumentRead.model_validate(restored), request_id=_request_id(request)
    )


@router.get("/documents/{document_id}/download")
async def download_document(
    request: Request,
    access: DocumentAccess = Depends(require_document_role(MemberRole.VIEWER)),
    service: DocumentService = Depends(get_document_service),
):
    url = service.download_url(access.document)
    if url is not None:
        return SuccessResponse(
            data=DownloadResponse(url=url, stream_via_backend=False),
            request_id=_request_id(request),
        )

    stream = service.download_stream(access.document)
    return StreamingResponse(
        stream,
        media_type=access.document.mime_type,
        headers={"Content-Disposition": f'attachment; filename="{access.document.filename}"'},
    )
