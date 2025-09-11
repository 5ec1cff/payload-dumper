import os
import sys

class MTIOBase:
    # read as much as size
    def read(self, off: int, size: int) -> bytes:
        pass

    def readinto(self, off: int, size: int, ba) -> int:
        pass

    def write(self, off: int, content: bytes) -> int:
        pass

    def get_size(self) -> int:
        pass

    def set_size(self, size: int):
        pass

    def readable(self) -> bool:
        pass

    def writable(self) -> bool:
        pass

    def close(self):
        pass

    def closed(self) -> bool:
        pass


USE_MMAP = False
if USE_MMAP:
    import mmap

    class MMapedFileMTIO(MTIOBase):
        def __init__(self, fileno, length, off, for_write: bool):
            prot = mmap.PROT_READ
            self.is_writable = False
            if for_write:
                prot |= mmap.PROT_WRITE
                self.is_writable = True
            self.mapped = mmap.mmap(fileno=fileno, length=length, offset=off, access=prot, flags=mmap.MAP_SHARED)

        def read(self, off: int, size: int) -> bytes:
            sz = self.mapped.size()
            if off < 0 or off >= sz:
                raise ValueError(f'invalid offset {off}')
            end = off + size
            if end > sz:
                end = sz
            return self.mapped[off:end]

        def readinto(self, off: int, size: int, ba) -> int:
            content = self.read(off, size)
            ba[:len(content)] = content
            return len(content)

        def write(self, off: int, content: bytes) -> int:
            sz = self.mapped.size()
            size = len(content)
            if off < 0 or off >= sz:
                raise ValueError(f'invalid offset {off}')
            end = off + size
            if end > sz:
                end = sz
            real_sz = end - off
            # TODO: expand?
            self.mapped[off:end] = content[:real_sz]
            return real_sz

        def get_size(self) -> int:
            return self.mapped.size()

        def set_size(self, size: int):
            self.mapped.resize(size)

        def readable(self) -> bool:
            return True

        def writable(self) -> bool:
            return self.is_writable

        def close(self):
            self.mapped.close()

        def closed(self) -> bool:
            return self.mapped.closed

if sys.platform == 'win32':
    USE_IO = True
else:
    USE_IO = False

if USE_IO:
    from threading import Lock

    def set_file_sparse(handle, is_sparse: bool):
        pass

    class FileMTFile(MTIOBase):
        def __init__(self, path, mode):
            self.f = open(path, mode + 'b')
            self.lock = Lock()

        def read(self, off: int, size: int) -> bytes:
            with self.lock:
                self.f.seek(off, os.SEEK_SET)
                return self.f.read(size)

        def readinto(self, off: int, size: int, ba) -> int:
            with self.lock:
                self.f.seek(off, os.SEEK_SET)
                return self.f.readinto(ba)

        def write(self, off: int, content: bytes) -> int:
            with self.lock:
                self.f.seek(off, os.SEEK_SET)
                return self.f.write(content)

        def get_size(self) -> int:
            return os.fstat(self.f.fileno()).st_size

        def set_size(self, size: int):
            os.ftruncate(self.f.fileno(), size)

        def readable(self) -> bool:
            return self.f.readable()

        def writable(self) -> bool:
            return self.f.writable()

        def close(self):
            self.f.close()

        def closed(self) -> bool:
            return self.f.closed
    MTFile = FileMTFile
else:
    if sys.platform == 'win32':
        from ._windows import WindowsMTFile, set_file_sparse
        MTFile = WindowsMTFile
    else:
        from ._unix import UnixMTFile, set_file_sparse
        MTFile = UnixMTFile

