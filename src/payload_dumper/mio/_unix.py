from . import MIOBase

# no-op
def set_file_sparse(handle, is_sparse: bool):
    pass

# TODO: use pread / pwrite
class UnixMFile(MIOBase):
    def __init__(self, path: str, mode: str):
        pass

    def close(self):
        pass

    def closed(self) -> bool:
        pass

    def writable(self) -> bool:
        pass

    def readable(self) -> bool:
        pass

    # return 0 when read at eof
    def readinto1(self, off: int, size: int, ba) -> int:
        pass

    def readinto(self, off: int, size: int, ba) -> int:
        pass

    def read(self, off: int, size: int) -> bytes:
        pass

    def write(self, off: int, content: bytes) -> int:
        pass

    def get_size(self) -> int:
        pass

    # not thread safe
    def set_size(self, size: int):
        pass
