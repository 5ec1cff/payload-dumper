from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class Extent(_message.Message):
    __slots__ = ("start_block", "num_blocks")
    START_BLOCK_FIELD_NUMBER: _ClassVar[int]
    NUM_BLOCKS_FIELD_NUMBER: _ClassVar[int]
    start_block: int
    num_blocks: int
    def __init__(self, start_block: _Optional[int] = ..., num_blocks: _Optional[int] = ...) -> None: ...

class Signatures(_message.Message):
    __slots__ = ("signatures",)
    class Signature(_message.Message):
        __slots__ = ("version", "data", "unpadded_signature_size")
        VERSION_FIELD_NUMBER: _ClassVar[int]
        DATA_FIELD_NUMBER: _ClassVar[int]
        UNPADDED_SIGNATURE_SIZE_FIELD_NUMBER: _ClassVar[int]
        version: int
        data: bytes
        unpadded_signature_size: int
        def __init__(self, version: _Optional[int] = ..., data: _Optional[bytes] = ..., unpadded_signature_size: _Optional[int] = ...) -> None: ...
    SIGNATURES_FIELD_NUMBER: _ClassVar[int]
    signatures: _containers.RepeatedCompositeFieldContainer[Signatures.Signature]
    def __init__(self, signatures: _Optional[_Iterable[_Union[Signatures.Signature, _Mapping]]] = ...) -> None: ...

class PartitionInfo(_message.Message):
    __slots__ = ("size", "hash")
    SIZE_FIELD_NUMBER: _ClassVar[int]
    HASH_FIELD_NUMBER: _ClassVar[int]
    size: int
    hash: bytes
    def __init__(self, size: _Optional[int] = ..., hash: _Optional[bytes] = ...) -> None: ...

class InstallOperation(_message.Message):
    __slots__ = ("type", "data_offset", "data_length", "src_extents", "src_length", "dst_extents", "dst_length", "data_sha256_hash", "src_sha256_hash")
    class Type(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        REPLACE: _ClassVar[InstallOperation.Type]
        REPLACE_BZ: _ClassVar[InstallOperation.Type]
        MOVE: _ClassVar[InstallOperation.Type]
        BSDIFF: _ClassVar[InstallOperation.Type]
        SOURCE_COPY: _ClassVar[InstallOperation.Type]
        SOURCE_BSDIFF: _ClassVar[InstallOperation.Type]
        REPLACE_XZ: _ClassVar[InstallOperation.Type]
        ZERO: _ClassVar[InstallOperation.Type]
        DISCARD: _ClassVar[InstallOperation.Type]
        BROTLI_BSDIFF: _ClassVar[InstallOperation.Type]
        PUFFDIFF: _ClassVar[InstallOperation.Type]
        ZUCCHINI: _ClassVar[InstallOperation.Type]
        LZ4DIFF_BSDIFF: _ClassVar[InstallOperation.Type]
        LZ4DIFF_PUFFDIFF: _ClassVar[InstallOperation.Type]
        ZSTD: _ClassVar[InstallOperation.Type]
    REPLACE: InstallOperation.Type
    REPLACE_BZ: InstallOperation.Type
    MOVE: InstallOperation.Type
    BSDIFF: InstallOperation.Type
    SOURCE_COPY: InstallOperation.Type
    SOURCE_BSDIFF: InstallOperation.Type
    REPLACE_XZ: InstallOperation.Type
    ZERO: InstallOperation.Type
    DISCARD: InstallOperation.Type
    BROTLI_BSDIFF: InstallOperation.Type
    PUFFDIFF: InstallOperation.Type
    ZUCCHINI: InstallOperation.Type
    LZ4DIFF_BSDIFF: InstallOperation.Type
    LZ4DIFF_PUFFDIFF: InstallOperation.Type
    ZSTD: InstallOperation.Type
    TYPE_FIELD_NUMBER: _ClassVar[int]
    DATA_OFFSET_FIELD_NUMBER: _ClassVar[int]
    DATA_LENGTH_FIELD_NUMBER: _ClassVar[int]
    SRC_EXTENTS_FIELD_NUMBER: _ClassVar[int]
    SRC_LENGTH_FIELD_NUMBER: _ClassVar[int]
    DST_EXTENTS_FIELD_NUMBER: _ClassVar[int]
    DST_LENGTH_FIELD_NUMBER: _ClassVar[int]
    DATA_SHA256_HASH_FIELD_NUMBER: _ClassVar[int]
    SRC_SHA256_HASH_FIELD_NUMBER: _ClassVar[int]
    type: InstallOperation.Type
    data_offset: int
    data_length: int
    src_extents: _containers.RepeatedCompositeFieldContainer[Extent]
    src_length: int
    dst_extents: _containers.RepeatedCompositeFieldContainer[Extent]
    dst_length: int
    data_sha256_hash: bytes
    src_sha256_hash: bytes
    def __init__(self, type: _Optional[_Union[InstallOperation.Type, str]] = ..., data_offset: _Optional[int] = ..., data_length: _Optional[int] = ..., src_extents: _Optional[_Iterable[_Union[Extent, _Mapping]]] = ..., src_length: _Optional[int] = ..., dst_extents: _Optional[_Iterable[_Union[Extent, _Mapping]]] = ..., dst_length: _Optional[int] = ..., data_sha256_hash: _Optional[bytes] = ..., src_sha256_hash: _Optional[bytes] = ...) -> None: ...

class CowMergeOperation(_message.Message):
    __slots__ = ("type", "src_extent", "dst_extent", "src_offset")
    class Type(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        COW_COPY: _ClassVar[CowMergeOperation.Type]
        COW_XOR: _ClassVar[CowMergeOperation.Type]
        COW_REPLACE: _ClassVar[CowMergeOperation.Type]
    COW_COPY: CowMergeOperation.Type
    COW_XOR: CowMergeOperation.Type
    COW_REPLACE: CowMergeOperation.Type
    TYPE_FIELD_NUMBER: _ClassVar[int]
    SRC_EXTENT_FIELD_NUMBER: _ClassVar[int]
    DST_EXTENT_FIELD_NUMBER: _ClassVar[int]
    SRC_OFFSET_FIELD_NUMBER: _ClassVar[int]
    type: CowMergeOperation.Type
    src_extent: Extent
    dst_extent: Extent
    src_offset: int
    def __init__(self, type: _Optional[_Union[CowMergeOperation.Type, str]] = ..., src_extent: _Optional[_Union[Extent, _Mapping]] = ..., dst_extent: _Optional[_Union[Extent, _Mapping]] = ..., src_offset: _Optional[int] = ...) -> None: ...

class PartitionUpdate(_message.Message):
    __slots__ = ("partition_name", "run_postinstall", "postinstall_path", "filesystem_type", "new_partition_signature", "old_partition_info", "new_partition_info", "operations", "postinstall_optional", "hash_tree_data_extent", "hash_tree_extent", "hash_tree_algorithm", "hash_tree_salt", "fec_data_extent", "fec_extent", "fec_roots", "version", "merge_operations", "estimate_cow_size", "estimate_op_count_max")
    PARTITION_NAME_FIELD_NUMBER: _ClassVar[int]
    RUN_POSTINSTALL_FIELD_NUMBER: _ClassVar[int]
    POSTINSTALL_PATH_FIELD_NUMBER: _ClassVar[int]
    FILESYSTEM_TYPE_FIELD_NUMBER: _ClassVar[int]
    NEW_PARTITION_SIGNATURE_FIELD_NUMBER: _ClassVar[int]
    OLD_PARTITION_INFO_FIELD_NUMBER: _ClassVar[int]
    NEW_PARTITION_INFO_FIELD_NUMBER: _ClassVar[int]
    OPERATIONS_FIELD_NUMBER: _ClassVar[int]
    POSTINSTALL_OPTIONAL_FIELD_NUMBER: _ClassVar[int]
    HASH_TREE_DATA_EXTENT_FIELD_NUMBER: _ClassVar[int]
    HASH_TREE_EXTENT_FIELD_NUMBER: _ClassVar[int]
    HASH_TREE_ALGORITHM_FIELD_NUMBER: _ClassVar[int]
    HASH_TREE_SALT_FIELD_NUMBER: _ClassVar[int]
    FEC_DATA_EXTENT_FIELD_NUMBER: _ClassVar[int]
    FEC_EXTENT_FIELD_NUMBER: _ClassVar[int]
    FEC_ROOTS_FIELD_NUMBER: _ClassVar[int]
    VERSION_FIELD_NUMBER: _ClassVar[int]
    MERGE_OPERATIONS_FIELD_NUMBER: _ClassVar[int]
    ESTIMATE_COW_SIZE_FIELD_NUMBER: _ClassVar[int]
    ESTIMATE_OP_COUNT_MAX_FIELD_NUMBER: _ClassVar[int]
    partition_name: str
    run_postinstall: bool
    postinstall_path: str
    filesystem_type: str
    new_partition_signature: _containers.RepeatedCompositeFieldContainer[Signatures.Signature]
    old_partition_info: PartitionInfo
    new_partition_info: PartitionInfo
    operations: _containers.RepeatedCompositeFieldContainer[InstallOperation]
    postinstall_optional: bool
    hash_tree_data_extent: Extent
    hash_tree_extent: Extent
    hash_tree_algorithm: str
    hash_tree_salt: bytes
    fec_data_extent: Extent
    fec_extent: Extent
    fec_roots: int
    version: str
    merge_operations: _containers.RepeatedCompositeFieldContainer[CowMergeOperation]
    estimate_cow_size: int
    estimate_op_count_max: int
    def __init__(self, partition_name: _Optional[str] = ..., run_postinstall: _Optional[bool] = ..., postinstall_path: _Optional[str] = ..., filesystem_type: _Optional[str] = ..., new_partition_signature: _Optional[_Iterable[_Union[Signatures.Signature, _Mapping]]] = ..., old_partition_info: _Optional[_Union[PartitionInfo, _Mapping]] = ..., new_partition_info: _Optional[_Union[PartitionInfo, _Mapping]] = ..., operations: _Optional[_Iterable[_Union[InstallOperation, _Mapping]]] = ..., postinstall_optional: _Optional[bool] = ..., hash_tree_data_extent: _Optional[_Union[Extent, _Mapping]] = ..., hash_tree_extent: _Optional[_Union[Extent, _Mapping]] = ..., hash_tree_algorithm: _Optional[str] = ..., hash_tree_salt: _Optional[bytes] = ..., fec_data_extent: _Optional[_Union[Extent, _Mapping]] = ..., fec_extent: _Optional[_Union[Extent, _Mapping]] = ..., fec_roots: _Optional[int] = ..., version: _Optional[str] = ..., merge_operations: _Optional[_Iterable[_Union[CowMergeOperation, _Mapping]]] = ..., estimate_cow_size: _Optional[int] = ..., estimate_op_count_max: _Optional[int] = ...) -> None: ...

class DynamicPartitionGroup(_message.Message):
    __slots__ = ("name", "size", "partition_names")
    NAME_FIELD_NUMBER: _ClassVar[int]
    SIZE_FIELD_NUMBER: _ClassVar[int]
    PARTITION_NAMES_FIELD_NUMBER: _ClassVar[int]
    name: str
    size: int
    partition_names: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, name: _Optional[str] = ..., size: _Optional[int] = ..., partition_names: _Optional[_Iterable[str]] = ...) -> None: ...

class VABCFeatureSet(_message.Message):
    __slots__ = ("threaded", "batch_writes")
    THREADED_FIELD_NUMBER: _ClassVar[int]
    BATCH_WRITES_FIELD_NUMBER: _ClassVar[int]
    threaded: bool
    batch_writes: bool
    def __init__(self, threaded: _Optional[bool] = ..., batch_writes: _Optional[bool] = ...) -> None: ...

class DynamicPartitionMetadata(_message.Message):
    __slots__ = ("groups", "snapshot_enabled", "vabc_enabled", "vabc_compression_param", "cow_version", "vabc_feature_set", "compression_factor")
    GROUPS_FIELD_NUMBER: _ClassVar[int]
    SNAPSHOT_ENABLED_FIELD_NUMBER: _ClassVar[int]
    VABC_ENABLED_FIELD_NUMBER: _ClassVar[int]
    VABC_COMPRESSION_PARAM_FIELD_NUMBER: _ClassVar[int]
    COW_VERSION_FIELD_NUMBER: _ClassVar[int]
    VABC_FEATURE_SET_FIELD_NUMBER: _ClassVar[int]
    COMPRESSION_FACTOR_FIELD_NUMBER: _ClassVar[int]
    groups: _containers.RepeatedCompositeFieldContainer[DynamicPartitionGroup]
    snapshot_enabled: bool
    vabc_enabled: bool
    vabc_compression_param: str
    cow_version: int
    vabc_feature_set: VABCFeatureSet
    compression_factor: int
    def __init__(self, groups: _Optional[_Iterable[_Union[DynamicPartitionGroup, _Mapping]]] = ..., snapshot_enabled: _Optional[bool] = ..., vabc_enabled: _Optional[bool] = ..., vabc_compression_param: _Optional[str] = ..., cow_version: _Optional[int] = ..., vabc_feature_set: _Optional[_Union[VABCFeatureSet, _Mapping]] = ..., compression_factor: _Optional[int] = ...) -> None: ...

class ApexInfo(_message.Message):
    __slots__ = ("package_name", "version", "is_compressed", "decompressed_size")
    PACKAGE_NAME_FIELD_NUMBER: _ClassVar[int]
    VERSION_FIELD_NUMBER: _ClassVar[int]
    IS_COMPRESSED_FIELD_NUMBER: _ClassVar[int]
    DECOMPRESSED_SIZE_FIELD_NUMBER: _ClassVar[int]
    package_name: str
    version: int
    is_compressed: bool
    decompressed_size: int
    def __init__(self, package_name: _Optional[str] = ..., version: _Optional[int] = ..., is_compressed: _Optional[bool] = ..., decompressed_size: _Optional[int] = ...) -> None: ...

class ApexMetadata(_message.Message):
    __slots__ = ("apex_info",)
    APEX_INFO_FIELD_NUMBER: _ClassVar[int]
    apex_info: _containers.RepeatedCompositeFieldContainer[ApexInfo]
    def __init__(self, apex_info: _Optional[_Iterable[_Union[ApexInfo, _Mapping]]] = ...) -> None: ...

class DeltaArchiveManifest(_message.Message):
    __slots__ = ("block_size", "signatures_offset", "signatures_size", "minor_version", "partitions", "max_timestamp", "dynamic_partition_metadata", "partial_update", "apex_info", "security_patch_level")
    BLOCK_SIZE_FIELD_NUMBER: _ClassVar[int]
    SIGNATURES_OFFSET_FIELD_NUMBER: _ClassVar[int]
    SIGNATURES_SIZE_FIELD_NUMBER: _ClassVar[int]
    MINOR_VERSION_FIELD_NUMBER: _ClassVar[int]
    PARTITIONS_FIELD_NUMBER: _ClassVar[int]
    MAX_TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    DYNAMIC_PARTITION_METADATA_FIELD_NUMBER: _ClassVar[int]
    PARTIAL_UPDATE_FIELD_NUMBER: _ClassVar[int]
    APEX_INFO_FIELD_NUMBER: _ClassVar[int]
    SECURITY_PATCH_LEVEL_FIELD_NUMBER: _ClassVar[int]
    block_size: int
    signatures_offset: int
    signatures_size: int
    minor_version: int
    partitions: _containers.RepeatedCompositeFieldContainer[PartitionUpdate]
    max_timestamp: int
    dynamic_partition_metadata: DynamicPartitionMetadata
    partial_update: bool
    apex_info: _containers.RepeatedCompositeFieldContainer[ApexInfo]
    security_patch_level: str
    def __init__(self, block_size: _Optional[int] = ..., signatures_offset: _Optional[int] = ..., signatures_size: _Optional[int] = ..., minor_version: _Optional[int] = ..., partitions: _Optional[_Iterable[_Union[PartitionUpdate, _Mapping]]] = ..., max_timestamp: _Optional[int] = ..., dynamic_partition_metadata: _Optional[_Union[DynamicPartitionMetadata, _Mapping]] = ..., partial_update: _Optional[bool] = ..., apex_info: _Optional[_Iterable[_Union[ApexInfo, _Mapping]]] = ..., security_patch_level: _Optional[str] = ...) -> None: ...
