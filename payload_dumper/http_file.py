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

    def readall(self) -> bytes:
        if self.pos >= self.size:
            raise ValueError('reached EOF!')
        end_pos = self.size - 1
        # print(f'read all!! {self.pos}-{end_pos}')
        headers = {'Range': f'bytes={self.pos}-{end_pos}'}
        r = self.client.get(self.url, headers=headers)
        self.pos = end_pos + 1
        content = r.read()
        self.total_bytes += len(content)
        return content

    def readinto(self, buffer) -> int | None:
        if self.pos >= self.size:
            raise ValueError('reached EOF!')
        end_pos = self.pos + len(buffer) - 1
        if end_pos >= self.size:
            end_pos = self.size - 1
        # print(f'read into from {self.pos}-{end_pos}')
        headers = {'Range': f'bytes={self.pos}-{end_pos}'}
        r = self.client.get(self.url, headers=headers)
        self.pos = end_pos + 1
        content = r.read()
        buffer[:len(content)] = content
        self.total_bytes += len(content)
        return len(content)

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

    def __init__(self, url: str):
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

    def close(self) -> None:
        self.client.close()

    def closed(self) -> bool:
        return self.client.is_closed


if __name__ == "__main__":
    import zipfile
    f = HttpFile('https://bkt-sgp-miui-ota-update-alisgp.oss-ap-southeast-1.aliyuncs.com/V14.0.27.0.TMRCNXM/miui_MARBLE_V14.0.27.0.TMRCNXM_07a1238ff9_13.0.zip')
    z = zipfile.ZipFile(f)
    print(z.namelist())
    print('read total:', f.total_bytes)
    pass
