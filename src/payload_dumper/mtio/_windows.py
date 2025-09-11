import win32file
import win32con
import winioctlcon
import pywintypes
import winerror

from . import MTIOBase

def set_file_sparse(handle, is_sparse: bool):
    if is_sparse:
        buf = b'\1'
    else:
        buf = b'\0'
    win32file.DeviceIoControl(handle, winioctlcon.FSCTL_SET_SPARSE, buf, None, None)

class WindowsMTFile(MTIOBase):
    def __init__(self, path: str, mode: str):
        is_r = 'r' in mode
        is_w = 'w' in mode
        is_o = '+' in mode
        creation_disposition = win32con.OPEN_EXISTING
        if is_w:
            creation_disposition = win32con.CREATE_ALWAYS
        elif is_o:
            creation_disposition = win32con.OPEN_ALWAYS
        access_flags = 0
        if is_r:
            access_flags |= win32file.GENERIC_READ
        if is_w or is_o:
            access_flags |= win32file.GENERIC_WRITE
        share_mode = win32file.FILE_SHARE_READ | win32file.FILE_SHARE_WRITE | win32file.FILE_SHARE_DELETE
        self.handle = win32file.CreateFile(path, access_flags, share_mode, None, creation_disposition, 0, None)
        self.can_read = is_r
        self.can_write = is_w or is_o
        self.closed = False

    def close(self):
        self.handle.Close()
        self.closed = True

    def closed(self) -> bool:
        return self.closed

    def writable(self) -> bool:
        return self.can_write

    def readable(self) -> bool:
        return self.can_read

    # return 0 when read at eof
    def readinto1(self, off: int, size: int, ba) -> int:
        if size == 0:
            return 0

        mem = memoryview(ba)[:size]
        remain = size
        pos = 0
        overlapped = win32file.OVERLAPPED()

        while remain > 0:
            mem = mem[pos:]

            overlapped.Offset = off & 0xffffffff
            overlapped.OffsetHigh = off >> 32

            # https://github.com/mhammond/pywin32/blob/a84f673604fd1923d374b6e5d2cdbbf080260eb6/win32/src/win32file.i#L897-L933
            # if the readable size less than the requested size,
            # the result buffer will be truncated to real size only if not using overlapped
            # so we found another way to get the real length by GetOverlappedResult
            # https://github.com/mhammond/pywin32/blob/a84f673604fd1923d374b6e5d2cdbbf080260eb6/win32/test/test_win32pipe.py#L140
            # it seems for async io, but it works well on sync io

            # buffer = win32file.AllocateReadBuffer(size)
            # we can pass `size` directly
            try:
                win32file.ReadFile(self.handle, mem, overlapped)
            except pywintypes.error as exc:
                if exc.winerror == winerror.ERROR_HANDLE_EOF:
                    # EOF reached
                    break
                else:
                    raise exc
            n = win32file.GetOverlappedResult(self.handle, overlapped, True)
            # print('read', n, 'remain', remain, 'pos', pos, 'off', off)
            pos += n
            remain -= n
            off += n

        return pos

    def readinto(self, off: int, size: int, ba) -> int:
        if self.closed:
            raise ValueError('Closed!')

        if not self.can_read:
            raise ValueError('Can\'t read!')

        return self.readinto1(off, size, ba)

    def read(self, off: int, size: int) -> bytes:
        out = bytearray(size)
        sz = self.readinto1(off, size, out)
        return out[:sz]

    def write(self, off: int, content: bytes) -> int:
        if self.closed:
            raise ValueError('Closed!')

        if not self.can_write:
            raise ValueError('Can\'t write!')

        remain = len(content)
        mem = memoryview(content)
        pos = 0
        overlapped = win32file.OVERLAPPED()

        while remain > 0:
            mem = mem[pos:]
            overlapped.Offset = off & 0xffffffff
            overlapped.OffsetHigh = off >> 32
            rc, d = win32file.WriteFile(self.handle, mem, overlapped)
            pos += d
            off += d
            remain -= d
        return pos

    def get_size(self) -> int:
        return win32file.GetFileSize(self.handle)

    # not thread safe
    def set_size(self, size: int):
        win32file.SetFilePointer(self.handle, size, win32con.FILE_CURRENT)
        win32file.SetEndOfFile(self.handle)

    def set_sparse(self, is_sparse: bool):
        if self.closed:
            raise ValueError('Closed!')
        set_file_sparse(self.handle, is_sparse)
