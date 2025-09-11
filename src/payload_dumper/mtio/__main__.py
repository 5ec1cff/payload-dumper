from . import MTFile

if __name__ == '__main__':
    def main():
        f = MTFile('xx.txt', 'r+')
        f.set_sparse(True)
        f.set_size(100)
        print('sz', f.get_size())
        #f.set_size(100)
        d = f.write(0, b'xxxxxxxxxxxxxx')
        print(d)
        d = f.read(0, 400000)
        print('read', len(d), d)
        print('sz', f.get_size())
        #f.set_sparse(True)
        f.close()

        return d
    main()