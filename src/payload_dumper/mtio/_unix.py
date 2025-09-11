from . import MTIOBase
import os

# no-op
def set_file_sparse(handle, is_sparse: bool):
    pass

class UnixMTFile(MTIOBase):
    def __init__(self, path: str, mode: str):
        is_r = 'r' in mode
        is_w = 'w' in mode
        is_o = '+' in mode
        if is_w or is_o:
            if is_r:
                flags = os.O_RDWR | os.O_CREAT
            else:
                flags = os.O_WRONLY | os.O_CREAT
            if not is_o:
                flags |= os.O_TRUNC
        elif is_r:
            flags = os.O_RDONLY
        else:
            raise ValueError('mode')
        flags |= os.O_CLOEXEC
        self.fd = os.open(path, flags)
        self.can_read = is_r
        self.can_write = is_w or is_o
        self.closed = False

    def close(self):
        os.close(self.fd)
        self.closed = True

    def closed(self) -> bool:
        return self.closed

    def writable(self) -> bool:
        return self.can_write

    def readable(self) -> bool:
        return self.can_read

    # return 0 when read at eof
    def read(self, off: int, size: int) -> bytes:
        if self.closed:
            raise ValueError('Closed!')

        if not self.can_read:
            raise ValueError('Can\'t read!')

        if size == 0:
            return b''

        result = b''
        remain = size
        pos = 0

        while remain > 0:
            r = os.pread(self.fd, remain, off)
            n = len(r)
            if n == 0:
                break
            pos += n
            remain -= n
            off += n
            result += r

        return result

    def readinto(self, off: int, size: int, ba) -> int:
        r = self.read(off, size)
        ba[:len(r)] = r
        return len(r)

    def write(self, off: int, content: bytes) -> int:
        if self.closed:
            raise ValueError('Closed!')

        if not self.can_write:
            raise ValueError('Can\'t write!')

        remain = len(content)
        mem = memoryview(content)
        pos = 0

        while remain > 0:
            mem = mem[pos:]
            d = os.pwrite(self.fd, mem, off)
            pos += d
            off += d
            remain -= d
        return pos

    def get_size(self) -> int:
        if self.closed:
            raise ValueError('Closed!')
        return os.fstat(self.fd).st_size

    def set_size(self, size: int):
        if self.closed:
            raise ValueError('Closed!')
        os.ftruncate(self.fd, size)


    def set_sparse(self, is_sparse: bool):
        pass
