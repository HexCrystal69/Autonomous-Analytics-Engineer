import os
import shutil
from typing import BinaryIO
from src.services.storage.base import BaseStorageProvider
from src.config import settings

class LocalStorageProvider(BaseStorageProvider):
    def __init__(self, storage_dir: str = settings.STORAGE_DIR):
        self.storage_dir = storage_dir
        os.makedirs(self.storage_dir, exist_ok=True)

    def save_file(self, file_content: BinaryIO, filename: str) -> str:
        # Generate a safe filename and store it
        # We can prepend a unique timestamp or directory path if required.
        # But to be safe, let's keep it robust and structure by dates or just direct names.
        target_path = os.path.join(self.storage_dir, filename)
        with open(target_path, "wb") as f:
            shutil.copyfileobj(file_content, f)
        return target_path

    def read_file(self, file_path: str) -> bytes:
        with open(file_path, "rb") as f:
            return f.read()

    def delete_file(self, file_path: str) -> None:
        if os.path.exists(file_path):
            os.remove(file_path)

    def exists(self, file_path: str) -> bool:
        return os.path.exists(file_path)
