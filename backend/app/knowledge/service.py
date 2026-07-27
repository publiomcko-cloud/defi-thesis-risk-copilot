from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256
from pathlib import PurePath
import re
from uuid import uuid4

from fastapi import HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.auth.schemas import UserContext
from app.auth.service import record_audit_event
from app.core.config import get_settings
from app.knowledge.access import (
    can_manage_knowledge_source,
    create_knowledge_source,
    get_visible_knowledge_source,
    list_visible_knowledge_sources,
)
from app.knowledge.schemas import (
    KnowledgeDocumentResponse,
    KnowledgeDocumentVersionResponse,
    KnowledgeSourceCreateRequest,
    KnowledgeSourceResponse,
    KnowledgeSourceUpdateRequest,
)
from app.models.knowledge import (
    KnowledgeDocumentModel,
    KnowledgeDocumentVersionModel,
    KnowledgeSourceModel,
)
from app.storage.base import StorageConfigurationError, StorageError
from app.storage.factory import create_private_object_storage
from app.storage.keys import build_version_object_key


_ALLOWED_UPLOADS = {
    "text/plain": {".txt"},
    "text/markdown": {".md", ".markdown"},
    "text/html": {".htm", ".html"},
    "application/pdf": {".pdf"},
}
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def create_source(
    db: Session,
    actor: UserContext,
    request: KnowledgeSourceCreateRequest,
) -> KnowledgeSourceResponse:
    source = create_knowledge_source(
        db,
        actor,
        visibility=request.visibility,
        title=request.title,
        source_type=request.source_type,
        organization_id=request.organization_id,
        source_uri=request.source_uri,
        canonical_uri=request.canonical_uri,
        protocol=request.protocol,
        chain=request.chain,
    )
    record_audit_event(
        db,
        actor.id,
        "knowledge.source_created",
        "knowledge_source",
        source.id,
        {"visibility": source.visibility, "source_type": source.source_type},
        commit=False,
    )
    db.commit()
    db.refresh(source)
    return knowledge_source_response(source)


def list_sources(db: Session, actor: UserContext) -> list[KnowledgeSourceResponse]:
    return [knowledge_source_response(source) for source in list_visible_knowledge_sources(db, actor)]


def get_source(db: Session, actor: UserContext, source_id: str) -> KnowledgeSourceResponse:
    return knowledge_source_response(get_visible_knowledge_source(db, actor, source_id))


def update_source(
    db: Session,
    actor: UserContext,
    source_id: str,
    request: KnowledgeSourceUpdateRequest,
) -> KnowledgeSourceResponse:
    source = _get_manageable_source(db, actor, source_id)
    if request.title is not None:
        source.title = request.title.strip()
    if request.protocol is not None:
        source.protocol = request.protocol.strip().lower()
    if request.chain is not None:
        source.chain = request.chain.strip().lower()
    if request.trust_state is not None:
        source.trust_state = request.trust_state
        if request.trust_state == "approved_for_rag":
            source.approved_by_user_id = actor.id
            source.approved_at = datetime.now(UTC)
        else:
            source.approved_by_user_id = None
            source.approved_at = None
    source.updated_at = datetime.now(UTC)
    record_audit_event(
        db,
        actor.id,
        "knowledge.source_updated",
        "knowledge_source",
        source.id,
        {"trust_state": source.trust_state},
        commit=False,
    )
    db.commit()
    db.refresh(source)
    return knowledge_source_response(source)


def delete_source(
    db: Session,
    actor: UserContext,
    source_id: str,
) -> KnowledgeSourceResponse:
    source = _get_manageable_source(db, actor, source_id)
    now = datetime.now(UTC)
    _tombstone_source(db, source, now)
    record_audit_event(
        db,
        actor.id,
        "knowledge.source_deleted",
        "knowledge_source",
        source.id,
        {"visibility": source.visibility},
        commit=False,
    )
    db.commit()
    db.refresh(source)
    return knowledge_source_response(source)


async def create_document_upload(
    db: Session,
    actor: UserContext,
    source_id: str,
    upload: UploadFile,
    checksum: str | None,
) -> KnowledgeDocumentResponse:
    source = _get_manageable_source(db, actor, source_id)
    filename, media_type, content, content_checksum = await _read_and_validate_upload(upload, checksum)
    storage = _configured_storage()
    now = datetime.now(UTC)
    document = KnowledgeDocumentModel(
        id=f"kdoc_{uuid4().hex[:12]}",
        knowledge_source_id=source.id,
        filename=filename,
        media_type=media_type,
        status="upload_pending",
        created_at=now,
        updated_at=now,
    )
    version = KnowledgeDocumentVersionModel(
        id=f"kver_{uuid4().hex[:12]}",
        document_id=document.id,
        version_number=1,
        storage_key="pending",
        checksum=content_checksum,
        size_bytes=len(content),
        status="pending_upload",
        created_at=now,
    )
    version.storage_key = build_version_object_key(source, document, version)
    await _store_document_version(
        db,
        actor,
        source,
        document,
        version,
        storage,
        content,
        "knowledge.document_uploaded",
    )
    return knowledge_document_response(document, [version])


async def create_document_version_upload(
    db: Session,
    actor: UserContext,
    document_id: str,
    upload: UploadFile,
    checksum: str | None,
) -> KnowledgeDocumentResponse:
    document, source = _get_manageable_document(db, actor, document_id, lock=True)
    filename, media_type, content, content_checksum = await _read_and_validate_upload(upload, checksum)
    if filename != document.filename or media_type != document.media_type:
        raise HTTPException(
            status_code=422,
            detail="Document version filename and media type must match the original document",
        )
    storage = _configured_storage()
    next_number = (
        db.execute(
            select(func.max(KnowledgeDocumentVersionModel.version_number)).where(
                KnowledgeDocumentVersionModel.document_id == document.id
            )
        ).scalar_one()
        or 0
    ) + 1
    now = datetime.now(UTC)
    version = KnowledgeDocumentVersionModel(
        id=f"kver_{uuid4().hex[:12]}",
        document_id=document.id,
        version_number=next_number,
        storage_key="pending",
        checksum=content_checksum,
        size_bytes=len(content),
        status="pending_upload",
        created_at=now,
    )
    version.storage_key = build_version_object_key(source, document, version)
    await _store_document_version(
        db,
        actor,
        source,
        document,
        version,
        storage,
        content,
        "knowledge.document_version_uploaded",
    )
    return knowledge_document_response(document, _document_versions(db, document.id))


def get_document(
    db: Session,
    actor: UserContext,
    document_id: str,
) -> KnowledgeDocumentResponse:
    document, _ = _get_visible_document(db, actor, document_id)
    return knowledge_document_response(document, _document_versions(db, document.id))


def delete_document(
    db: Session,
    actor: UserContext,
    document_id: str,
) -> KnowledgeDocumentResponse:
    document, source = _get_manageable_document(db, actor, document_id, lock=True)
    now = datetime.now(UTC)
    _tombstone_document(db, document, now)
    record_audit_event(
        db,
        actor.id,
        "knowledge.document_deleted",
        "knowledge_document",
        document.id,
        {"knowledge_source_id": source.id},
        commit=False,
    )
    db.commit()
    db.refresh(document)
    return knowledge_document_response(document, _document_versions(db, document.id))


def tombstone_knowledge_for_account(db: Session, user_id: str, *, now: datetime) -> int:
    sources = db.execute(
        select(KnowledgeSourceModel)
        .where(KnowledgeSourceModel.owner_user_id == user_id)
        .where(KnowledgeSourceModel.visibility == "private")
        .where(KnowledgeSourceModel.deleted_at.is_(None))
    ).scalars().all()
    for source in sources:
        _tombstone_source(db, source, now)
    return len(sources)


def tombstone_knowledge_for_organization(db: Session, organization_id: str, *, now: datetime) -> int:
    sources = db.execute(
        select(KnowledgeSourceModel)
        .where(KnowledgeSourceModel.organization_id == organization_id)
        .where(KnowledgeSourceModel.deleted_at.is_(None))
    ).scalars().all()
    for source in sources:
        _tombstone_source(db, source, now)
    return len(sources)


def _get_manageable_source(db: Session, actor: UserContext, source_id: str) -> KnowledgeSourceModel:
    source = get_visible_knowledge_source(db, actor, source_id)
    if not can_manage_knowledge_source(db, actor, source):
        raise HTTPException(status_code=403, detail="Knowledge source manager role required")
    return source


def _get_visible_document(
    db: Session,
    actor: UserContext,
    document_id: str,
    *,
    lock: bool = False,
) -> tuple[KnowledgeDocumentModel, KnowledgeSourceModel]:
    statement = select(KnowledgeDocumentModel, KnowledgeSourceModel).join(
        KnowledgeSourceModel,
        KnowledgeSourceModel.id == KnowledgeDocumentModel.knowledge_source_id,
    ).where(KnowledgeDocumentModel.id == document_id).where(KnowledgeDocumentModel.deleted_at.is_(None))
    if lock:
        statement = statement.with_for_update()
    row = db.execute(statement).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Knowledge document not found")
    document, source = row
    get_visible_knowledge_source(db, actor, source.id)
    return document, source


def _get_manageable_document(
    db: Session,
    actor: UserContext,
    document_id: str,
    *,
    lock: bool = False,
) -> tuple[KnowledgeDocumentModel, KnowledgeSourceModel]:
    document, source = _get_visible_document(db, actor, document_id, lock=lock)
    if not can_manage_knowledge_source(db, actor, source):
        raise HTTPException(status_code=403, detail="Knowledge source manager role required")
    return document, source


async def _read_and_validate_upload(
    upload: UploadFile,
    expected_checksum: str | None,
) -> tuple[str, str, bytes, str]:
    settings = get_settings()
    filename = _validate_filename(upload.filename)
    media_type = (upload.content_type or "").lower().split(";", 1)[0].strip()
    extensions = _ALLOWED_UPLOADS.get(media_type)
    if extensions is None or PurePath(filename).suffix.lower() not in extensions:
        raise HTTPException(status_code=422, detail="Knowledge upload media type is not allowed")
    if expected_checksum is not None and not _SHA256.fullmatch(expected_checksum.lower()):
        raise HTTPException(status_code=422, detail="Knowledge upload checksum is invalid")
    content = bytearray()
    while True:
        chunk = await upload.read(settings.knowledge_upload_chunk_bytes)
        if not chunk:
            break
        if len(content) + len(chunk) > settings.knowledge_upload_max_bytes:
            raise HTTPException(status_code=413, detail="Knowledge upload exceeds the allowed size")
        content.extend(chunk)
    if not content:
        raise HTTPException(status_code=422, detail="Knowledge upload is empty")
    content_bytes = bytes(content)
    if media_type == "application/pdf" and not content_bytes.startswith(b"%PDF-"):
        raise HTTPException(status_code=422, detail="Knowledge upload does not match its PDF media type")
    if media_type.startswith("text/") and b"\x00" in content_bytes:
        raise HTTPException(status_code=422, detail="Knowledge text upload contains binary content")
    actual_checksum = sha256(content_bytes).hexdigest()
    if expected_checksum is not None and actual_checksum != expected_checksum.lower():
        raise HTTPException(status_code=422, detail="Knowledge upload checksum does not match content")
    return filename, media_type, content_bytes, actual_checksum


def _validate_filename(value: str | None) -> str:
    if not value or len(value) > 255 or "\x00" in value or "/" in value or "\\" in value:
        raise HTTPException(status_code=422, detail="Knowledge upload filename is invalid")
    filename = value.strip()
    if not filename or filename in {".", ".."} or filename != PurePath(filename).name:
        raise HTTPException(status_code=422, detail="Knowledge upload filename is invalid")
    return filename


def _configured_storage():
    try:
        return create_private_object_storage()
    except StorageConfigurationError as exc:
        raise HTTPException(status_code=503, detail="Private knowledge storage is unavailable") from exc


async def _store_document_version(
    db: Session,
    actor: UserContext,
    source: KnowledgeSourceModel,
    document: KnowledgeDocumentModel,
    version: KnowledgeDocumentVersionModel,
    storage,
    content: bytes,
    audit_action: str,
) -> None:
    object_written = False
    try:
        db.add_all([document, version])
        await run_in_threadpool(
            storage.put_create_only,
            key=version.storage_key,
            content=content,
            content_type=document.media_type,
            expected_checksum=version.checksum,
        )
        object_written = True
        document.status = "uploaded"
        document.updated_at = datetime.now(UTC)
        version.status = "uploaded"
        record_audit_event(
            db,
            actor.id,
            audit_action,
            "knowledge_document_version",
            version.id,
            {
                "knowledge_source_id": source.id,
                "document_id": document.id,
                "version_number": version.version_number,
                "size_bytes": version.size_bytes,
                "media_type": document.media_type,
            },
            commit=False,
        )
        db.commit()
        db.refresh(document)
        db.refresh(version)
    except StorageError as exc:
        db.rollback()
        raise HTTPException(status_code=503, detail="Private knowledge storage upload failed") from exc
    except SQLAlchemyError as exc:
        db.rollback()
        if object_written:
            try:
                await run_in_threadpool(storage.delete, key=version.storage_key)
            except StorageError:
                pass
        raise HTTPException(status_code=503, detail="Knowledge upload could not be committed") from exc


def _document_versions(db: Session, document_id: str) -> list[KnowledgeDocumentVersionModel]:
    return db.execute(
        select(KnowledgeDocumentVersionModel)
        .where(KnowledgeDocumentVersionModel.document_id == document_id)
        .order_by(KnowledgeDocumentVersionModel.version_number.desc())
    ).scalars().all()


def _tombstone_source(db: Session, source: KnowledgeSourceModel, now: datetime) -> None:
    source.status = "deleted"
    source.deleted_at = now
    source.updated_at = now
    documents = db.execute(
        select(KnowledgeDocumentModel).where(KnowledgeDocumentModel.knowledge_source_id == source.id)
    ).scalars().all()
    for document in documents:
        _tombstone_document(db, document, now)


def _tombstone_document(db: Session, document: KnowledgeDocumentModel, now: datetime) -> None:
    document.status = "deleted"
    document.deleted_at = now
    document.updated_at = now
    versions = db.execute(
        select(KnowledgeDocumentVersionModel).where(
            KnowledgeDocumentVersionModel.document_id == document.id
        )
    ).scalars().all()
    for version in versions:
        version.status = "deleted"
        version.deleted_at = now


def knowledge_source_response(source: KnowledgeSourceModel) -> KnowledgeSourceResponse:
    return KnowledgeSourceResponse(
        id=source.id,
        owner_user_id=source.owner_user_id,
        organization_id=source.organization_id,
        visibility=source.visibility,
        source_type=source.source_type,
        source_uri=source.source_uri,
        canonical_uri=source.canonical_uri,
        title=source.title,
        protocol=source.protocol,
        chain=source.chain,
        status=source.status,
        trust_state=source.trust_state,
        approved_by_user_id=source.approved_by_user_id,
        approved_at=source.approved_at,
        created_at=source.created_at,
        updated_at=source.updated_at,
        deleted_at=source.deleted_at,
    )


def knowledge_document_version_response(
    version: KnowledgeDocumentVersionModel,
) -> KnowledgeDocumentVersionResponse:
    return KnowledgeDocumentVersionResponse(
        id=version.id,
        version_number=version.version_number,
        checksum=version.checksum,
        size_bytes=version.size_bytes,
        status=version.status,
        parser_version=version.parser_version,
        chunker_version=version.chunker_version,
        embedding_model=version.embedding_model,
        embedding_dimensions=version.embedding_dimensions,
        created_at=version.created_at,
        superseded_at=version.superseded_at,
        deleted_at=version.deleted_at,
    )


def knowledge_document_response(
    document: KnowledgeDocumentModel,
    versions: list[KnowledgeDocumentVersionModel],
) -> KnowledgeDocumentResponse:
    return KnowledgeDocumentResponse(
        id=document.id,
        knowledge_source_id=document.knowledge_source_id,
        current_version_id=document.current_version_id,
        filename=document.filename,
        media_type=document.media_type,
        status=document.status,
        created_at=document.created_at,
        updated_at=document.updated_at,
        deleted_at=document.deleted_at,
        versions=[knowledge_document_version_response(version) for version in versions],
    )
