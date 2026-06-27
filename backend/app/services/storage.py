from pathlib import Path

import boto3

from app.core.config import get_settings


class StorageService:
    def __init__(self) -> None:
        self.settings = get_settings()

    def upload(self, local_path: Path, object_key: str) -> str:
        if self.settings.storage_backend == "s3":
            client = self._s3_client()
            self._ensure_bucket(client)
            client.upload_file(str(local_path), self.settings.s3_bucket, object_key)
            return f"s3://{self.settings.s3_bucket}/{object_key}"
        return str(local_path)

    def download_to_path(self, storage_path: str, local_path: Path) -> Path:
        if storage_path.startswith("s3://"):
            bucket, key = storage_path.removeprefix("s3://").split("/", 1)
            local_path.parent.mkdir(parents=True, exist_ok=True)
            self._s3_client().download_file(bucket, key, str(local_path))
            return local_path
        return Path(storage_path)

    def delete(self, storage_path: str) -> None:
        if storage_path.startswith("s3://"):
            bucket, key = storage_path.removeprefix("s3://").split("/", 1)
            self._s3_client().delete_object(Bucket=bucket, Key=key)
        else:
            Path(storage_path).unlink(missing_ok=True)

    def _s3_client(self):
        return boto3.client(
            "s3",
            endpoint_url=self.settings.s3_endpoint_url,
            aws_access_key_id=self.settings.s3_access_key_id,
            aws_secret_access_key=self.settings.s3_secret_access_key,
            region_name=self.settings.s3_region,
        )

    def _ensure_bucket(self, client) -> None:
        buckets = client.list_buckets().get("Buckets", [])
        if any(bucket["Name"] == self.settings.s3_bucket for bucket in buckets):
            return
        client.create_bucket(Bucket=self.settings.s3_bucket)
