import io
import httpx


class HttpFile(io.RawIOBase):

    def seekable(self) -> bool:
        return True

    def readable(self) -> bool:
        return True

    def writable(self) -> bool:
        return False

    def _read_internal(self, buf: bytes) -> int:
        size = len(buf)
        end_pos = min(self.pos + size - 1, self.size - 1)
        size = end_pos - self.pos + 1
        headers = {"Range": f"bytes={self.pos}-{end_pos}"}
        n = 0
        with self.client.stream("GET", self.url, headers=headers) as r:
            if r.status_code != 206:
                raise io.UnsupportedOperation("Remote did not return partial content!")
            if self.progress_reporter is not None:
                self.progress_reporter(0, size)
            for chunk in r.iter_bytes(8192):
                buf[n : n + len(chunk)] = chunk
                n += len(chunk)
                if self.progress_reporter is not None:
                    self.progress_reporter(n, size)
            if self.progress_reporter is not None:
                self.progress_reporter(size, size)
            self.total_bytes += n
            self.pos += n
        assert n == size
        return n

    def readall(self) -> bytes:
        sz = self.size - self.pos
        buf = bytearray(sz)
        self._read_internal(buf)
        return buf

    def readinto(self, buffer) -> int:
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
            raise io.UnsupportedOperation(f"unsupported seek whence! {whence}")
        if new_pos < 0 or new_pos > self.size:
            raise ValueError(f"invalid position to seek: {new_pos} in size {self.size}")
        # print(f'seek: pos {self.pos} -> {new_pos}')
        self.pos = new_pos
        return new_pos

    def tell(self) -> int:
        return self.pos

from . import mtio


class HttpRangeFileMTIO(mtio.MTIOBase):
    def readable(self) -> bool:
        return True

    def writable(self) -> bool:
        return False

    def readinto1(self, off: int, sz: int, buf) -> int:
        if sz == 0:
            return 0

        end_pos = min(off + sz - 1, self.size - 1)
        expected_size = end_pos - off + 1
        received = 0

        retry_count = 0

        while received < expected_size:
            headers = {"Range": f"bytes={off+received}-{end_pos}"}
            try:
                with self.client.stream("GET", self.url, headers=headers) as r:
                    if r.status_code != 206:
                        raise io.UnsupportedOperation(f"Remote did not return partial content: {self.url} {r.status_code}")
                    for chunk in r.iter_bytes(8192):
                        buf[received : received + len(chunk)] = chunk
                        received += len(chunk)
            except httpx.ConnectTimeout as e:
                retry_count += 1
                print(f'connection timeout, {retry_count=} {e}')
                if retry_count >= self.max_retry:
                    raise e
        return received

    def readinto(self, off: int, size: int, ba) -> int:
        if self.closed():
            raise ValueError('closed!')

        return self.readinto1(off, size, ba)

    def read(self, off: int, size: int) -> bytes:
        if self.closed():
            raise ValueError('closed!')

        ba = bytearray(size)
        n = self.readinto1(off, size, ba)
        return ba[:n]

    def __init__(self, url: str, max_retry = 10):
        client = httpx.Client()
        self.url = url
        self.client = client
        self.max_retry = max_retry
        h = client.head(url)
        if h.headers.get("Accept-Ranges", "none") != "bytes":
            raise ValueError(f"Remote does not support ranges: {url} {h.status_code} {h.request.headers}")
        size = int(h.headers.get("Content-Length", 0))
        if size == 0:
            raise ValueError(f"Remote has no length: {url}")
        self.size = size

    def set_headers(self, headers):
        self.client.headers = headers

    def get_size(self) -> int:
        return self.size

    def set_size(self, size: int):
        raise NotImplementedError()

    def write(self, off: int, content: bytes) -> int:
        raise NotImplementedError()

    def close(self):
        self.client.close()

    def closed(self) -> bool:
        return self.client.is_closed

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()


if __name__ == "__main__":
    from ziputil import get_zip_stored_entry_offset
    hf = HttpRangeFileMTIO('OTA_LINK_TO_TEST')
    sz = hf.get_size()
    print(sz)
    off, esz = get_zip_stored_entry_offset(hf, 'payload.bin')
    print(f'got payload.bin {off=} {esz=}')
    #data = mio.read(sz - 4096, 4096)
    #with open('out.bin', 'wb') as f:
        #f.write(data)
    hf.close()