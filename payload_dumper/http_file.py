import io
import os

import httpx


class HttpFile(io.RawIOBase):

    def seekable(self) -> bool:
        return True

    def readable(self) -> bool:
        return True

    def writable(self) -> bool:
        return False

    def _read_internal(self, buf: bytes):
        size = len(buf)
        end_pos = self.pos + size - 1
        if self.pos >= self.size:
            raise ValueError('reached EOF!')
        headers = {'Range': f'bytes={self.pos}-{end_pos}'}
        with self.client.stream('GET', self.url, headers=headers) as r:
            if r.status_code != 206:
                raise io.UnsupportedOperation('Remote did not return partial content!')
            if self.progress_reporter is not None:
                self.progress_reporter(0, size)
            n = 0
            for chunk in r.iter_bytes(8192):
                buf[n:n+len(chunk)] = chunk
                n += len(chunk)
                if self.progress_reporter is not None:
                    self.progress_reporter(n, size)
            if self.progress_reporter is not None:
                self.progress_reporter(size, size)
            self.total_bytes += n
        self.pos += size
        return size

    def readall(self) -> bytes:
        sz = self.size - self.pos
        buf = bytearray(sz)
        self._read_internal(buf)
        return buf

    def readinto(self, buffer) -> int | None:
        # print(f'read into from {self.pos}-{end_pos}')
        return self._read_internal(buffer)

    def seek(self, offset: int, whence: int = os.SEEK_SET) -> int:
        # print(f'seek to {offset} whence {whence}')
        if whence == os.SEEK_SET:
            new_pos = offset
        elif whence == os.SEEK_CUR:
            new_pos = self.pos + offset
        elif whence == os.SEEK_END:
            new_pos = self.size + offset
        else:
            raise io.UnsupportedOperation(f'unsupported seek whence! {whence}')
        if new_pos < 0 or new_pos > self.size:
            raise ValueError(f'invalid position to seek: {new_pos} in size {self.size}')
        # print(f'seek: pos {self.pos} -> {new_pos}')
        self.pos = new_pos
        return new_pos

    def tell(self) -> int:
        return self.pos

    def __init__(self, url: str, progress_reporter = None):
        client = httpx.Client()
        self.url = url
        self.client = client
        h = client.head(url)
        if h.headers.get("Accept-Ranges", "none") != "bytes":
            raise ValueError('remote does not support ranges!')
        size = int(h.headers.get('Content-Length', 0))
        if size == 0:
            raise ValueError('remote has no length!')
        self.size = size
        self.pos = 0
        self.total_bytes = 0
        self.progress_reporter = progress_reporter

    def close(self) -> None:
        self.client.close()

    def closed(self) -> bool:
        return self.client.is_closed


if __name__ == "__main__":
    import zipfile
    f = HttpFile('https://dl.google.com/dl/android/aosp/shiba-ota-ap1a.240505.005-1ab58b6a.zip')
    f.seek(0, os.SEEK_END)
    print('file size:', f.tell())
    f.seek(0, os.SEEK_SET)
    z = zipfile.ZipFile(f)
    print(z.namelist())
    for name in z.namelist():
        with z.open(name) as payload:
            print(name, 'compress type:', payload._compress_type)
    print('total read:', f.total_bytes)
    pass
