import os
import io
import hashlib
from typing import Tuple

try:
    from minio import Minio
    from minio.error import S3Error
except ImportError:
    Minio = None
    S3Error = Exception

from app.core.config import settings


class StorageService:
    def __init__(self):
        self.endpoint = settings.S3_ENDPOINT
        self.bucket = settings.S3_BUCKET_NAME
        self.client = None
        if Minio is not None:
            try:
                self.client = Minio(
                    endpoint=self.endpoint,
                    access_key=settings.S3_ACCESS_KEY,
                    secret_key=settings.S3_SECRET_KEY,
                    secure=settings.S3_USE_SSL,
                )
            except Exception:
                self.client = None

        # Fallback local folder for storage if MinIO is not running
        self.local_dir = os.path.join(os.getcwd(), "data", "uploads")
        os.makedirs(self.local_dir, exist_ok=True)

    def _ensure_bucket(self):
        if self.client:
            try:
                if not self.client.bucket_exists(self.bucket):
                    self.client.make_bucket(self.bucket)
            except Exception:
                pass

    def upload_bytes(self, data: bytes, object_name: str, content_type: str = "image/jpeg") -> Tuple[str, str]:
        """
        Uploads bytes to MinIO (or fallback local directory).
        Returns: (object_name, sha256_hash)
        """
        sha256 = hashlib.sha256(data).hexdigest()
        
        # Try MinIO first if available
        if self.client:
            try:
                self._ensure_bucket()
                self.client.put_object(
                    bucket_name=self.bucket,
                    object_name=object_name,
                    data=io.BytesIO(data),
                    length=len(data),
                    content_type=content_type,
                )
                return object_name, sha256
            except Exception:
                pass  # Fall back to local file

        # Local fallback
        local_path = os.path.join(self.local_dir, object_name)
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        with open(local_path, "wb") as f:
            f.write(data)
        return object_name, sha256

    def get_bytes(self, object_name: str) -> bytes:
        """
        Retrieves bytes from MinIO or fallback local directory.
        """
        if self.client:
            try:
                response = self.client.get_object(self.bucket, object_name)
                try:
                    return response.read()
                finally:
                    response.close()
                    response.release_conn()
            except Exception:
                pass

        local_path = os.path.join(self.local_dir, object_name)
        if os.path.exists(local_path):
            with open(local_path, "rb") as f:
                return f.read()

        raise FileNotFoundError(f"Object {object_name} not found in storage.")


storage_service = StorageService()
