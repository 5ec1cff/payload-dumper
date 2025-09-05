import sys


class MIOBase:
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

# TODO: on unix, use pread / pwrite
if sys.platform == 'win32':
    from ._windows import WindowsMFile
    MFile = WindowsMFile
else:
    from ._unix import UnixMFile
    MFile = UnixMFile


if __name__ == '__main__':
    def main():
        f = MFile('xx.txt', 'r+')
        f.set_sparse(True)
        f.set_size(100)
        print('sz', f.get_size())
        #f.set_size(100)
        d = f.write(0, b'xxxxxxxxxxxxxx')
        print(d)
        d = f.read(25578, 400000)
        print('read', len(d))
        print('sz', f.get_size())
        #f.set_sparse(True)
        f.close()

        return d
    main()
