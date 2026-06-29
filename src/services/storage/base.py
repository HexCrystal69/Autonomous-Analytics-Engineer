from abc import ABC, abstractmethod
from typing import BinaryIO

class BaseStorageProvider(ABC):
    @abstractmethod
    def save_file(self, file_content: BinaryIO, filename: str) -> str:
        """Saves file contents and returns the relative path or identifier."""
        pass

    @abstractmethod
    def read_file(self, file_path: str) -> bytes:
        """Reads and returns the file content as bytes."""
        pass

    @abstractmethod
    def delete_file(self, file_path: str) -> None:
        """Deletes the specified file."""
        pass

    @abstractmethod
    def exists(self, file_path: str) -> bool:
        """Returns True if the file exists, False otherwise."""
        pass
