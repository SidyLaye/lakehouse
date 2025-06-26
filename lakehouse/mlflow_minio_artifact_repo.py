from mlflow.store.artifact.artifact_repo import ArtifactRepository
from mlflow.store.artifact.artifact_repository_registry import _artifact_repository_registry
from mlflow.entities.file_info import FileInfo             
from minio import Minio
import os
import posixpath                                        
import tempfile
import shutil

class MinioArtifactRepository(ArtifactRepository):
    def __init__(self, artifact_uri):
        super().__init__(artifact_uri)
        # URI : minio://bucket/prefix
        _, rest = artifact_uri.split("://", 1)
        parts = rest.split("/", 1)
        self.bucket = parts[0]
        self.prefix = parts[1] if len(parts) > 1 else ""
        endpoint = os.getenv("MINIO_ENDPOINT", "localhost:9000")
        access = os.getenv("MINIO_ROOT_USER", "minioadmin")
        secret = os.getenv("MINIO_ROOT_PASSWORD", "minioadmin")
        self.client = Minio(endpoint, access_key=access, secret_key=secret, secure=False)
        if not self.client.bucket_exists(self.bucket):
            self.client.make_bucket(self.bucket)

    def log_artifacts(self, local_dir, artifact_path=None):
        base_prefix = self.prefix.rstrip("/")
        if artifact_path:
            base_prefix = f"{base_prefix}/{artifact_path}".lstrip("/")
        for root, _, files in os.walk(local_dir):
            for fname in files:
                local_path = os.path.join(root, fname)
                rel_path = os.path.relpath(local_path, local_dir)
                object_name = f"{base_prefix}/{rel_path}".lstrip("/")
                self.client.fput_object(self.bucket, object_name, local_path)

    def list_artifacts(self, path=None):
        base = self.prefix.rstrip("/")
        if path:
            base = posixpath.join(base, path.lstrip("/"))
        if base and not base.endswith("/"):
            base += "/"
        objects = self.client.list_objects(self.bucket, prefix=base, recursive=True)

        seen = set()
        results = []
        for obj in objects:
            rel = obj.object_name[len(base):]
            parts = rel.split("/", 1)
            name = parts[0]
            is_dir = len(parts) > 1
            if name in seen:
                continue
            seen.add(name)
            fpath = posixpath.join(path or "", name)
            size = obj.size if not is_dir else None
            results.append(FileInfo(path=fpath, is_dir=is_dir, file_size=size))
        return results

    def download_artifacts(self, artifact_path, dst_path):
        if dst_path is None:
            dst_path = tempfile.mkdtemp()

        prefix = f"{self.prefix}/{artifact_path}" if artifact_path else self.prefix
        prefix = prefix.lstrip("/")

        os.makedirs(dst_path, exist_ok=True)
        for obj in self.client.list_objects(self.bucket, prefix=prefix, recursive=True):
            key = obj.object_name
            rel_path = key[len(prefix):].lstrip("/")
            local_file = os.path.join(dst_path, rel_path)
            os.makedirs(os.path.dirname(local_file), exist_ok=True)

            resp = self.client.get_object(self.bucket, key)
            with open(local_file, "wb") as f:
                for chunk in resp.stream(32 * 1024):
                    f.write(chunk)
            resp.close()
            resp.release_conn()

        mlmodel_path = os.path.join(dst_path, "MLmodel")
        if not os.path.exists(mlmodel_path):
            for root, _, files in os.walk(dst_path):
                if "MLmodel" in files:
                    shutil.move(os.path.join(root, "MLmodel"), mlmodel_path)
                    break

        return dst_path

_artifact_repository_registry.register(
    "minio",
    MinioArtifactRepository
)
