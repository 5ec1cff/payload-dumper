import struct
from . import mtio

zip_eocd_struct = b"<4s4H2LH"
zip_eocd_magic = b"PK\005\006"
zip_eocd_size = struct.calcsize(zip_eocd_struct)

zip64_eocd_locator_struct = "<4sLQL"
zip64_eocd_locator_magic = b"PK\x06\x07"
zip64_eocd_locator_size = struct.calcsize(zip64_eocd_locator_struct)

zip64_eocd_struct = "<4sQ2H2L4Q"
zip64_eocd_magic = b"PK\x06\x06"
zip64_eocd_size = struct.calcsize(zip64_eocd_struct)

zip_cdfh_struct = "<4s6H3L5H2L"
zip_cdfh_magic = b"PK\001\002"
zip_cdfh_size = struct.calcsize(zip_cdfh_struct)

zip_fh_struct = "<4s5H3L2H"
zip_fh_magic = b"PK\003\004"
zip_fh_size = struct.calcsize(zip_fh_struct)

ZIP_MAX_COMMENT = (1 << 16) - 1
ZIP_STORED = 0

def get_zip_stored_entry_offset(file: mtio.MTIOBase, name: str):
    sz = file.get_size()

    if sz < zip_eocd_size:
        raise ValueError('not enough length to contain EOCD!')

    eocd_off = None
    data = file.read(sz - zip_eocd_size, zip_eocd_size)
    if (len(data) == zip_eocd_size and
        data[0:4] == zip_eocd_magic and
        data[-2:] == b"\000\000"):
        eocd_off = sz - zip_eocd_size
    else:
        try_sz = ZIP_MAX_COMMENT + zip_eocd_size
        start = sz - try_sz
        if start < 0:
            start = 0
            try_sz = sz
        data = file.read(start, try_sz)
        assert len(data) == try_sz
        for length in range(1, try_sz - zip_eocd_size + 1):
            l, = struct.unpack('<H', data[-length-2:-length])
            if (l == length and
                data[-length-zip_eocd_size:-length-zip_eocd_size+4] == zip_eocd_magic):
                data = data[-length-zip_eocd_size:-length]
                eocd_off = sz - length - zip_eocd_size
                break

    if eocd_off is None:
        raise ValueError('not a zip!')

    endrec = struct.unpack(zip_eocd_struct, data)
    cd_num = endrec[4]
    cd_sz = endrec[5]
    cd_off = endrec[6]

    if not (cd_num == 0xffff or cd_sz == 0xffffffff or cd_off == 0xffffffff):
        #print(f'{cd_num=} {cd_sz=} {cd_off=}')
        is_zip64 = False
        pass
    else:
        #print('zip64')
        eocd64_locator_off = eocd_off - zip64_eocd_locator_size
        if eocd64_locator_off < 0:
            raise ValueError(f'unexpected eocd64_locator_off {eocd_off} - {zip64_eocd_locator_size}')
        data2 = file.read(eocd64_locator_off, zip64_eocd_locator_size)
        if data2[0:4] != zip64_eocd_locator_magic:
            raise ValueError(f'unexpected EOCD64Locator magic {data2[0:4]}, expected {zip64_eocd_locator_magic}')
        eocd64_locator = struct.unpack(zip64_eocd_locator_struct, data2)
        eocd64_off = eocd64_locator[2]
        data2 = file.read(eocd64_off, zip64_eocd_size)
        if data2[0:4] != zip64_eocd_magic:
            raise ValueError(f'unexpected EOCD64Locator magic {data2[0:4]}, expected {zip64_eocd_magic}')
        eocd64 = struct.unpack(zip64_eocd_struct, data2)
        cd_num = eocd64[7]
        cd_sz = eocd64[8]
        cd_off = eocd64[9]
        #print(f'{cd_num=} {cd_sz=} {cd_off=}')
        is_zip64 = True

    data = file.read(cd_off, cd_sz)
    i = 0
    p = 0

    name_utf8 = name.encode('utf-8')
    lfh_offset = None
    entry_size = None

    while i < cd_num and p < cd_sz:
        cd = data[p:p+zip_cdfh_size]
        if cd[0:4] != zip_cdfh_magic:
            raise ValueError(f'invalid cd magic at {i=} {p=} {cd[0:4]}, expected {zip_cdfh_magic}')
        cd = struct.unpack(zip_cdfh_struct, cd)
        #print(cd)
        file_name_length = cd[10]
        extra_field_length = cd[11]
        file_comment_length = cd[12]
        cd_ent_sz = zip_cdfh_size + file_name_length + extra_field_length + file_comment_length
        #print(data[p+sizeCentralDir:p+sizeCentralDir+file_name_length])
        file_name = data[p+zip_cdfh_size:p+zip_cdfh_size+file_name_length]
        #print(file_name)
        if file_name == name_utf8:
            compression_method = cd[4]
            file_compressed_size = cd[8]
            file_uncompressed_size = cd[9]
            file_lfh_off = cd[16]
            disk_number = cd[13]
            if is_zip64:
                ep = p + zip_cdfh_size + file_name_length
                ee = ep + extra_field_length
                while ee - ep >= 4:
                    header_id, field_size = struct.unpack('<HH', data[ep:ep+4])
                    if field_size + ep > ee:
                        raise ValueError(f'invalid extra field size {field_size} at {ep=} {ee=}')
                    # ZIP64 ext
                    if header_id == 1:
                        ext_data = data[ep+4:ep+4+field_size]
                        if file_uncompressed_size == 0xffffffff:
                            file_uncompressed_size, = struct.unpack('<Q', ext_data[:8])
                            ext_data = ext_data[8:]
                        if file_compressed_size == 0xffffffff:
                            file_compressed_size, = struct.unpack('<Q', ext_data[:8])
                            ext_data = ext_data[8:]
                        if file_lfh_off == 0xffffffff:
                            file_lfh_off, = struct.unpack('<Q', ext_data[:8])
                            ext_data = ext_data[8:]
                        if disk_number == 0xffff:
                            disk_number, = struct.unpack('<I', ext_data[:4])
                            ext_data = ext_data[4:]
                        if len(ext_data) != 0:
                            print('unconsumed ZIP64 ext?')
                    ep += field_size + 4
            #print(f'{i=} {p=} {file_name=} {compression_method=} {file_uncompressed_size=} {file_lfh_off=} {file_uncompressed_size=} {disk_number=}')
            if compression_method != ZIP_STORED:
                raise ValueError(f'target not stored: {compression_method=}')
            lfh_offset = file_lfh_off
            entry_size = file_uncompressed_size
            break
        p += cd_ent_sz
        i += 1

    if lfh_offset is None:
        raise ValueError(f'target not found: {name}')

    data = file.read(lfh_offset, zip_fh_size)
    if data[0:4] != zip_fh_magic:
        raise ValueError(f'unexpected file header magic at {lfh_offset}: {data[0:4]}, expected {zip_fh_magic}')

    file_header = struct.unpack(zip_fh_struct, data)
    file_name_length = file_header[9]
    extra_field_length = file_header[10]
    real_off = lfh_offset + zip_fh_size + file_name_length + extra_field_length

    return real_off, entry_size
