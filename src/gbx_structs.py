from functools import partial
import datetime
import string

import lzo
import src.mini_lzo
import zlib
import zipfile
import io

from construct import *
from src.my_construct import MyRepeatUntil

from src.gbx_enums import *

GbxCompressedBody = Struct("uncompressed_size" / Int32ul, "compressed_body" / Prefixed(Int32ul, GreedyBytes))


class CompressedLZ0(Tunnel):
    def _decode(self, raw_bytes, context, path):
        data = GbxCompressedBody.parse(raw_bytes)

        return lzo.decompress(data.compressed_body, False, data.uncompressed_size)

        # return mini_lzo.decompress(data.compressed_body, data.uncompressed_size)

    def _encode(self, raw_bytes, context, path):
        return GbxCompressedBody.build(
            Container(
                uncompressed_size=len(raw_bytes),
                # compressed_body=mini_lzo.compress(raw_bytes),
                compressed_body=lzo.compress(raw_bytes, 9, False),
            )
        )


class ACompressedZip(Adapter):
    def _decode(self, raw_bytes, context, path):
        self.buffer = io.BytesIO(raw_bytes)
        return zipfile.ZipFile(self.buffer, "a")

    def _encode(self, zip, context, path):
        return self.buffer.getvalue()


GbxCompressedZip = ACompressedZip(Prefixed(Int32ul, GreedyBytes))

import zlib

ini_data = None


class CompressedZlib2(Tunnel):
    def __init__(self, subcon):
        super().__init__(subcon)

    def _decode(self, data, context, path):
        global ini_data
        un = zlib.decompress(data)
        ini_data = un
        return un

    def _encode(self, data, context, path):
        from deep_compare import CompareVariables

        print(len(ini_data))
        print(len(data))

        with open("bytes1.txt", "wb") as f:
            f.write(ini_data)
        with open("bytes2.txt", "wb") as f:
            f.write(data)

        # for i in range(len(ini_data)):
        #     print(CompareVariables.compare(ini_data[i], data[i]))

        return zlib.compress(data, 9)


# TODO Adapter
# TODO manage rest
def CompressedZLib(subcon):
    return Struct(
        "uncompressedSize" / Int32ul,
        "content" / Prefixed(Int32ul, Compressed(subcon, "zlib", level=9)),
        # "content" / Prefixed(Int32ul, CompressedZlib2(subcon)),
        # "content" / Prefixed(Int32ul, GreedyBytes),
    )


def CompressedZLibBytes(subcon):
    return Struct(
        "uncompressedSize" / Int32ul,
        "content" / Prefixed(Int32ul, GreedyBytes),
    )


class EndWithFACADE01(Tunnel):
    def _decode(self, raw_bytes, context, path):
        if Int32ul.parse(raw_bytes[-4:]) != 0xFACADE01:
            print(" -- might be corrupted -- ")
        return raw_bytes

    def _encode(self, raw_bytes, context, path):
        return raw_bytes


GbxChunkId = Hex(Int32ul)

GbxString = PascalString(Int32ul, "utf-8")


def check_bool(obj, ctx):
    if obj == 0x01:
        return True
    if obj == 0x00:
        return False
    print("Not a bool!" + str(hex(obj)))
    return False


GbxBool = ExprAdapter(
    Int32ul,
    decoder=check_bool,
    encoder=lambda obj, ctx: 0x01 if obj else 0x00,
)
GbxBoolByte = ExprAdapter(
    Byte,
    decoder=check_bool,
    encoder=lambda obj, ctx: 0x01 if obj else 0x00,
)

GbxFloat = Float32l

GbxVec2 = Struct("x" / GbxFloat, "y" / GbxFloat)
GbxVec3 = Struct("x" / GbxFloat, "y" / GbxFloat, "z" / GbxFloat)
GbxVec4 = Struct("x" / GbxFloat, "y" / GbxFloat, "z" / GbxFloat, "w" / GbxFloat)
GbxQuat = GbxVec4
GbxTexPos = Struct("x" / Int16ul, "y" / Int16ul)
GbxInt3 = Struct("x" / Int32sl, "y" / Int32sl, "z" / Int32sl)
GbxInt3Byte = Struct("x" / Int8ul, "y" / Int8ul, "z" / Int8ul)
GbxPose3D = Struct(
    "x" / GbxFloat,
    "y" / GbxFloat,
    "z" / GbxFloat,
    "yaw" / GbxFloat,
    "pitch" / GbxFloat,
    "roll" / GbxFloat,
)
GbxLoc = Struct("pos" / GbxVec3, "rot" / GbxQuat)
GbxBox = Struct(
    "x1" / GbxFloat,
    "y1" / GbxFloat,
    "z1" / GbxFloat,
    "x2" / GbxFloat,
    "y2" / GbxFloat,
    "z2" / GbxFloat,
)
GbxBoxInt = Struct(
    "x1" / Int32sl,
    "y1" / Int32sl,
    "z1" / Int32sl,
    "x2" / Int32sl,
    "y2" / Int32sl,
    "z2" / Int32sl,
)
GbxColor = Struct("b" / Byte, "g" / Byte, "r" / Byte, "a" / Byte)
GbxPlugSurfaceMaterialId = Struct("physicsId" / GbxEPlugSurfacePhysicsId, "gameplayId" / GbxEPlugSurfaceGameplayId)

GbxBytesUntilFacade = Struct(
    "bytes_until_facade"
    / ExprAdapter(
        RepeatUntil(lambda x, lst, ctx: lst[-4:] == [0x01, 0xDE, 0xCA, 0xFA], Byte),
        lambda obj, ctx: bytes(obj[:-4]),
        lambda obj, ctx: GreedyBytes.build(obj + b"\x01\xDE\xCA\xFA"),
    ),
    Seek(-4, 1),
)


def tenb_to_float(x):
    if x >= 0x201:
        x -= 0x400
    return x / 0x1FF


def float_to_tenb(x):
    x = min(max(x, -1), 1)
    x = int(x * 0x1FF)
    if x < 0:
        x += 0x400
    return x


class AGbxDec3N(Adapter):
    def _decode(self, obj, ctx, path):
        return Container(
            x=tenb_to_float(obj & 0x3FF),
            y=tenb_to_float((obj >> 10) & 0x3FF),
            z=tenb_to_float((obj >> 20) & 0x3FF),
        )

    def _encode(self, obj, ctx, path):
        return float_to_tenb(obj.x) + (float_to_tenb(obj.y) << 10) + (float_to_tenb(obj.z) << 20)


GbxDec3N = AGbxDec3N(Int32ul)


class AGbxUDec4N(Adapter):
    def _decode(self, obj, ctx, path):
        return Container(
            x=((obj >> 0x10) & 0xFF) * 0.003921569,
            y=((obj >> 0x08) & 0xFF) * 0.003921569,
            z=((obj >> 0x00) & 0xFF) * 0.003921569,
            w=((obj >> 0x18) & 0xFF) * 0.003921569,
        )

    def _encode(self, obj, ctx, path):
        return (
            ((round(obj.x * 255.0) & 0xFF) << 0x10)
            + ((round(obj.y * 255.0) & 0xFF) << 0x08)
            + ((round(obj.z * 255.0) & 0xFF) << 0x00)
            + ((round(obj.w * 255.0) & 0xFF) << 0x18)
        )


GbxUDec4N = AGbxUDec4N(Int32ul)


def GbxDict(key, value):
    return PrefixedArray(Int32ul, Struct("key" / key, "value" / value))


GbxDictString = GbxDict(GbxString, GbxString)


GbxMat3x3 = Struct(
    "XX" / GbxFloat,
    "XY" / GbxFloat,
    "XZ" / GbxFloat,
    "YX" / GbxFloat,
    "YY" / GbxFloat,
    "YZ" / GbxFloat,
    "ZX" / GbxFloat,
    "ZY" / GbxFloat,
    "ZZ" / GbxFloat,
)
GbxIso4 = Struct(
    "XX" / GbxFloat,
    "XY" / GbxFloat,
    "XZ" / GbxFloat,
    "YX" / GbxFloat,
    "YY" / GbxFloat,
    "YZ" / GbxFloat,
    "ZX" / GbxFloat,
    "ZY" / GbxFloat,
    "ZZ" / GbxFloat,
    "TX" / GbxFloat,
    "TY" / GbxFloat,
    "TZ" / GbxFloat,
)

GbxInt3 = Struct("x" / Int32sl, "y" / Int32sl, "z" / Int32sl)


class AGbxFileTime(Adapter):
    EPOCH_START = datetime.datetime(1601, 1, 1)

    def _decode(self, file_time, context, path):
        delta = datetime.timedelta(microseconds=file_time / 10)
        date_time = self.EPOCH_START + delta
        return date_time

    def _encode(self, date_time, context, path):
        time_delta = date_time - self.EPOCH_START
        return int(time_delta / datetime.timedelta(microseconds=1)) * 10


GbxFileTime = AGbxFileTime(Int64ul)

GbxFileRef = Struct(
    "version" / Int8ul,  # 3
    "checksum" / Bytes(32),
    "filePath" / GbxString,
    "locatorUrl" / GbxString,
)

GbxCollectionIds = {
    0: "Desert Speed",
    1: "Snow Alpine",
    3: "Island",
    4: "Bay",
    7: "Basic",
    11: "Valley",
    26: "Stadium2020",
}


GbxFolders = Struct(
    "name" / GbxString,
    "folders" / LazyBound(lambda: PrefixedArray(Int32ul, GbxFolders)),
)


def need_version(this):
    if "lookbackstring" in this._root._params.gbx_data:
        return False
    else:
        this._root._params.gbx_data["lookbackstring"] = []
        return True


def need_string(this):
    flags = this.index >> 30
    idx = this.index & 0x3FFFFFFF
    return idx == 0 and flags != 0


def decode_lookbackstring(obj, ctx):
    flags = obj.index >> 30
    idx = obj.index & 0x3FFFFFFF

    if idx == 0x3FFFFFFF:
        match flags:
            case 2:
                return "Unassigned"
            case 3:
                return ""
    elif flags == 0:
        if idx not in GbxCollectionIds:
            print(f" -- Unknown collection id: {idx} -- ")
            return f"Unknown collection id: {idx}"
        return GbxCollectionIds[idx]
    elif idx == 0:
        ctx._root._params.gbx_data["lookbackstring"].append(obj.string)
        return obj.string
    elif idx <= len(ctx._root._params.gbx_data["lookbackstring"]):
        return ctx._root._params.gbx_data["lookbackstring"][idx - 1]
    else:
        print(f"<INVALID IDX: {idx-1}>")
        return f"<INVALID IDX: {idx-1}>"


def encode_lookbackstring(obj, ctx):
    idx = 0x40000000

    if obj == "Unassigned":
        idx = 0xBFFFFFFF
    elif obj == "":
        idx = 0xFFFFFFFF

    for key, value in GbxCollectionIds.items():
        if value == obj:
            idx = key
            break
    else:
        if "lookbackstring" in ctx._root._params.gbx_data:
            for key, value in enumerate(ctx._root._params.gbx_data["lookbackstring"]):
                if value == obj:
                    idx |= key + 1
                    break

    return Container(version=3, index=idx, string=obj)


class TGbxLookbackString(str):
    pass


GbxLookbackString = ExprAdapter(
    Struct(
        "version" / If(need_version, ExprValidator(Int32ul, obj_ == 3)),
        "index" / Int32ul,
        "string" / If(need_string, GbxString),
    ),
    lambda *args: TGbxLookbackString(decode_lookbackstring(*args)),
    encode_lookbackstring,
)


class GbxLookbackStringContext(Construct):
    def __init__(self, subcon):
        super().__init__()
        self.subcon = subcon

    def _parse(self, stream, context, path):
        old_ctx = context._root._params.gbx_data["lookbackstring"]
        context._root._params.gbx_data.pop("lookbackstring", None)

        res = self.subcon._parse(stream, context, path)

        context._root._params.gbx_data["lookbackstring"] = old_ctx

        return res

    def _build(self, obj, stream, context, path):
        old_ctx = context._root._params.gbx_data["lookbackstring"]
        context._root._params.gbx_data.pop("lookbackstring", None)

        res = self.subcon._build(obj, stream, context, path)

        context._root._params.gbx_data["lookbackstring"] = old_ctx

        return res

    def _sizeof(self, context, path):
        return self.subcon._sizeof(context, path)


GbxMeta = Struct(
    "id" / GbxLookbackString,
    "collection" / GbxLookbackString,
    "author" / GbxLookbackString,
)

GbxEmbeddedFile = Prefixed(Int32ul, GreedyBytes)


class GbxOptimizedInt(Construct):
    def __init__(self, size_func):
        super().__init__()
        self.size_func = size_func

    def get_struct(self, context):
        if callable(self.size_func):
            max_size = self.size_func(context)
        else:
            max_size = self.size_func

        if max_size < 2**8:
            struct = Int8ul
        elif max_size < 2**16:
            struct = Int16ul
        else:
            struct = Int32ul

        return struct

    def _parse(self, stream, context, path):
        struct = self.get_struct(context)

        return struct._parse(stream, context, path)

    def _build(self, obj, stream, context, path):
        struct = self.get_struct(context)

        return struct._build(obj, stream, context, path)

    def _sizeof(self, context, path):
        struct, length = self.get_struct(context)

        return struct._sizeof(context, path)


class GbxOptimizedIntArray(Construct):
    def __init__(self, length_func=None, size_func=None):
        super().__init__()
        self.length_func = length_func
        self.size_func = size_func

    def get_struct(self, context):
        # if self.length_func is None:
        #     length = Int32ul._parse()
        # else:
        assert self.length_func is not None  # TODO

        if callable(self.length_func):
            length = self.length_func(context)
        else:
            length = self.length_func

        if self.size_func is not None and callable(self.size_func):
            max_size = self.size_func(context)
        else:
            max_size = length

        if max_size < 2**8:
            struct = Int8ul
        elif max_size < 2**16:
            struct = Int16ul
        else:
            struct = Int32ul

        return struct, length

    def _parse(self, stream, context, path):
        struct, length = self.get_struct(context)

        return struct[length]._parse(stream, context, path)

    def _build(self, obj, stream, context, path):
        struct, length = self.get_struct(context)

        return struct[length]._build(obj, stream, context, path)

    def _sizeof(self, context, path):
        struct, length = self.get_struct(context)

        return struct._sizeof(context, path) * length


body_chunks = {}

GbxNodesWithoutBody = set(
    [
        0x09144000,
        0x09145000,
        0x09159000,
        0x09178000,
        0x09179000,
        0x0917B000,
        0x09187000,
        0x2F074000,
        0x2F0BC000,
        0x2F086000,
        0x2F0CA000,
    ]
)


def print_next_chunk_id(obj, ctx):
    # print(f"Parsing... {obj}")
    return obj


def print_chunk_unknown(obj, ctx):
    print(f" -- Unknown chunk id: {hex(ctx._.chunk_id)}")
    return obj


def print_chunk_fail(obj, ctx):
    print(f" -- Parse chunk failed: {hex(ctx._.chunk_id)}")
    return obj


GbxBodyChunks = MyRepeatUntil(
    lambda obj, lst, ctx: obj is None or obj.chunk_id == 0xFACADE01,
    Select(
        Struct(
            "chunk_id" / GbxChunkId * print_next_chunk_id,
            StopIf(this.chunk_id == 0xFACADE01),
            "chunk"
            / Select(
                Struct(
                    "skippable" / Const(b"PIKS"),
                    "content"
                    / Prefixed(
                        Int32ul,
                        Switch(
                            this._.chunk_id,
                            body_chunks,
                            default=GreedyBytes,
                        ),
                    ),
                ),
                Switch(
                    this.chunk_id,
                    body_chunks,
                    default=Struct("unknown_chunk" / GbxBytesUntilFacade * print_chunk_unknown),
                ),
                Struct("chunk_parse_failed" / GreedyBytes * print_chunk_fail),
            ),
        ),
        Pass,
    ),
)


def print_chunk_unknown_noderef(obj, ctx):
    print(f" -- Unknown chunk in node ref, id: {hex(ctx._.header.class_id)}")
    return obj


GbxBody = IfThenElse(
    lambda this: this.header.class_id in GbxNodesWithoutBody,
    Switch(
        lambda this: this.header.class_id,
        body_chunks,
        default=Struct("unknown_chunk_in_node_ref" / GreedyBytes * print_chunk_unknown_noderef),
    ),
    GbxBodyChunks
    # EndWithFACADE01(GbxBodyChunks),
)


def need_node_body(this):
    if 1 <= this.index < len(this._root._params.nodes):
        if this._parsing:
            return this._root._params.nodes[this.index] is None
        elif this._building:
            return this.internal_node is not None
        else:
            raise Exception(f"Unknwon state")
    else:
        print(f"Unknown node ref index: {this.index}")


class TGbxNodeRef(int):
    pass


def get_noderef_offset(ctx):
    while ctx._:
        ctx = ctx._
        if "node_offset" in ctx:
            return ctx.node_offset
    return 0


class GbxNodeRefAdapter(Adapter):
    def _decode(self, obj, ctx, path):
        if obj.index == -1:
            return TGbxNodeRef(-1)

        # print(f"node_ref {obj.index}")
        if obj.internal_node is not None:
            # print(f"parsed {obj.index} {path}")
            ctx._root._params.nodes[obj.index] = obj.internal_node

        return TGbxNodeRef(obj.index)

    def _encode(self, obj, ctx, path):
        if obj == -1:
            return Container(index=-1)
        # elif type(obj) == int:
        #     print(f"reuse {obj}")
        #     return obj

        # print(
        #     f"node ref {obj} + {get_noderef_offset(ctx)} => {obj + get_noderef_offset(ctx)}"
        # )
        obj += get_noderef_offset(ctx)

        internal_node = None
        if ctx._root._params.nodes[obj] is not None:
            internal_node = ctx._root._params.nodes[obj]
            ctx._root._params.nodes[obj] = None

        return Container(index=obj, internal_node=internal_node)


GbxNodeRef = GbxNodeRefAdapter(
    Struct(
        "index" / Int32sl,
        StopIf(this.index == -1),
        "internal_node"
        / If(
            need_node_body,
            Struct(
                "header" / Struct("class_id" / GbxChunkId),
                "body" / GbxBody
                # / IfThenElse(
                #     lambda this: this.class_id in GbxNodesWithoutBody,
                #     Switch(
                #         this.class_id,
                #         body_chunks,
                #         default=Struct("unknown_chunk_in_node_ref" / GreedyBytes),
                #     ),
                #     GbxBody,  # TODO create new context for GbxBody? I think no
                # ),
            ),
        ),
    ),
)

GbxMaterial = Struct(
    "material_name" / GbxString,
    "material_user_inst" / If(lambda this: len(this.material_name) == 0, GbxNodeRef),
)


# Body Chunks

# 0301B CGameCtnCollectorList
body_chunks[0x0301B000] = Struct(
    "collectorStock"
    / PrefixedArray(
        Int32ul,
        Struct(
            "ident" / GbxMeta,
            "count" / Int32ul,
        ),
    ),
)

# 03036 CGameCtnBlockUnitInfo
body_chunks[0x03036000] = Struct(
    "placePylons" / Int32sl,
    "u01" / GbxBool,  # AcceptPylons?
    "u02" / GbxBool,
    "relativeOffset" / GbxInt3,
    "clips" / PrefixedArray(Int32ul, GbxNodeRef),  # pylons clips?
)
body_chunks[0x03036001] = Struct(
    "u01" / GbxNodeRef,  # Desert, Grass
    "u02" / Int32sl,
    "u03" / Int32sl,
)
body_chunks[0x03036002] = Struct(
    "u01" / Bytes(12),  # undergound?
)
body_chunks[0x03036004] = Struct(
    "u01" / Int32sl,
)
body_chunks[0x03036005] = Struct(
    "terrainModifierId" / GbxNodeRef,
)
body_chunks[0x03036007] = Struct(
    "u01" / GbxNodeRef[4],
)
body_chunks[0x0303600C] = Struct(
    "version" / Int32ul,
    "countClips"
    / ByteSwapped(  # little endian 32 bit
        BitStruct(
            Padding(14),
            "Bottom" / BitsInteger(3),
            "Top" / BitsInteger(3),
            "West" / BitsInteger(3),
            "South" / BitsInteger(3),
            "East" / BitsInteger(3),
            "North" / BitsInteger(3),
        )
    ),
    "clipsNorth" / Array(this.countClips.North, GbxNodeRef),  # CGameCtnBlockInfoClip
    "clipsEast" / Array(this.countClips.East, GbxNodeRef),  # CGameCtnBlockInfoClip
    "clipsSouth" / Array(this.countClips.South, GbxNodeRef),  # CGameCtnBlockInfoClip
    "clipsWest" / Array(this.countClips.West, GbxNodeRef),  # CGameCtnBlockInfoClip
    "clipsTop" / Array(this.countClips.Top, GbxNodeRef),  # CGameCtnBlockInfoClip
    "clipsBottom" / Array(this.countClips.Bottom, GbxNodeRef),  # CGameCtnBlockInfoClip
    "u01" / Int16sl,
    "u02" / Int16sl,
)

# 03043 CGameCtnChallenge

GbxBlockInstance = Struct(
    "name" / GbxLookbackString,
    "dir" / GbxECardinalDir,
    "coords" / GbxInt3Byte,
    "flags"
    / ByteSwapped(
        BitStruct(
            "u04" / BitsInteger(2),
            "isFree" / Flag,
            "isGhost" / Flag,
            "blockVariantIndex" / BitsInteger(6),
            "u03" / Flag,
            "isWaypoint" / Flag,
            "u02" / BitsInteger(4),
            "isSkinnable" / Flag,
            "u01" / Flag,
            "isClip" / Flag,
            "isGround" / Flag,
            "mobilVariantIndex" / BitsInteger(6),
            "mobilIndex" / BitsInteger(6),
        )
    ),
    "skinParams"
    / If(
        this.flags.isSkinnable,
        Struct(
            "author" / GbxLookbackString,
            "skin" / GbxNodeRef,
        ),
    ),
    "waypointParams" / If(this.flags.isWaypoint, GbxNodeRef),  # CGameWaypointSpecialProperty
    # TODO what's this?
    # coord -= (1, 0, 1); if version >= 6
    # coord -= (0, 1, 0); if free block
)

body_chunks[0x0304300D] = Struct(
    "playerModel" / GbxMeta,
)
body_chunks[0x03043011] = Struct(
    "blockStock" / GbxNodeRef,  # CGameCtnCollectorList
    "challengeParameters" / GbxNodeRef,  # CGameCtnChallengeParameters
    "kind" / GbxEMapKind,
)
body_chunks[0x0304301F] = Struct(
    "mapInfo" / GbxMeta,
    "mapName" / GbxString,
    "decoration" / GbxMeta,
    "size" / GbxInt3,
    "needUnlock" / GbxBool,
    "version" / Int32ul,  # 6, only if not 03043013
    "blocks" / PrefixedArray(Int32ul, GbxBlockInstance),
)
body_chunks[0x03043022] = Struct(
    "u01" / Int32sl,
)
body_chunks[0x03043024] = Struct(
    "customMusicPackDesc" / GbxFileRef,
)
body_chunks[0x03043025] = Struct(
    "mapCoordOrigin" / GbxVec2,
    "mapCoordTarget" / GbxVec2,
)
body_chunks[0x03043026] = Struct(
    "clipGlobal" / GbxNodeRef,
)
body_chunks[0x03043027] = Struct(
    "hasCustomCamThumbnail" / GbxBool,
    "customCamThumbnail"
    / If(
        this.hasCustomCamThumbnail,
        Struct(
            "u01" / Byte,
            "u02" / GbxVec3,
            "u03" / GbxVec3,
            "u04" / GbxVec3,
            "thumbnailPosition" / GbxVec3,
            "thumbnailFOV" / GbxFloat,
            "thumbnailNearClipPlane" / GbxFloat,
            "thumbnailFarClipPlane" / GbxFloat,
        ),
    ),
)
body_chunks[0x03043028] = Struct(
    *body_chunks[0x03043027].subcons,
    "comments" / GbxString,
)
body_chunks[0x0304302A] = Struct(
    "u01" / GbxBool,
)
body_chunks[0x03043048] = Struct(
    "version" / Int32ul,
    "u01" / Int32sl,
    "BakedBlocks" / PrefixedArray(Int32ul, GbxBlockInstance),
    "u02" / Int32sl,
    "BakedClipsAdditionalData"
    / PrefixedArray(
        Int32ul,
        Struct(
            "Clip1" / GbxMeta,
            "Clip2" / GbxMeta,
            "Clip3" / GbxMeta,
            "Clip4" / GbxMeta,
            "Coord" / GbxInt3Byte,
        ),
    ),
)
body_chunks[0x03043049] = Struct(
    "version" / Int32ul,
    "clipIntro" / GbxNodeRef,  # CGameCtnMediaClip
    "clipPodium" / GbxNodeRef,  # CGameCtnMediaClip
    "clipGroupInGame" / GbxNodeRef,  # CGameCtnMediaClipGroup
    "clipGroupEndRace" / GbxNodeRef,  # CGameCtnMediaClipGroup
    "clipAmbiance" / GbxNodeRef,  # CGameCtnMediaClip
    "triggerSize" / GbxInt3,  # dividor
)
SHmsLightMapCacheSmall = Struct(
    "version" / Int32ul,  # 8
    "lightmapFrames"
    / PrefixedArray(
        Int32ul,
        Struct(
            "frame1" / GbxEmbeddedFile,
            "frame2" / GbxEmbeddedFile,
            "frame3" / GbxEmbeddedFile,
        ),
    ),
    # TODO if lightmapFrames > 0
    "data"
    / If(
        lambda this: len(this.lightmapFrames) > 0,
        CompressedZLib(
            Struct(
                "body" / GbxLookbackStringContext(GbxBodyChunks),
                "rest" / GreedyBytes,
            )
        ),
    ),
)
body_chunks[0x03043054] = Struct(  # embedded objects
    "version" / Int32ul,
    "u01" / Int32sl,
    "embeddedData"
    / Prefixed(
        Int32ul,
        GbxLookbackStringContext(
            Struct(
                "filesMeta" / PrefixedArray(Int32ul, GbxMeta),
                "zip" / GbxCompressedZip,
                "Textures" / PrefixedArray(Int32ul, GbxString),
            )
        ),
    ),
)
body_chunks[0x0304305B] = Struct(
    "version" / Int32ul,
    "u01" / GbxBool,
    "u02" / GbxBool,
    "u03" / GbxBool,
    StopIf(lambda this: not this.u01),
    "lightmaps" / SHmsLightMapCacheSmall,
)

# 0304E CGameCtnBlockInfo
body_chunks[0x0304E00F] = Struct(
    "no_respawn" / GbxBool,
)
body_chunks[0x0304E013] = Struct(
    "icon_auto_use_ground" / GbxBool,
)
body_chunks[0x0304E017] = Struct(
    "u01" / GbxBool,
)
body_chunks[0x0304E020] = Struct(
    "version" / Int32ul,
    "char_phy_special_property" / GbxNodeRef,
    "u01" / If(this.version < 7, GbxNodeRef),
    StopIf(this.version < 2),
    "podium_info" / GbxNodeRef,  # CGamePodiumInfo
    StopIf(this.version < 3),
    "intro_info" / GbxNodeRef,  # CGamePodiumInfo
    StopIf(this.version < 4),
    "char_phy_special_property_customizable" / GbxBool,
    "u02" / If(this.version == 5, GbxBool),
    StopIf(this.version < 8),
    "u03" / GbxBool,
    "u04" / If(this.u03, Struct("u01" / GbxString, "u02" / GbxString)),
)
body_chunks[0x0304E023] = Struct(
    "variant_base_ground" / GbxBodyChunks,
    "variant_base_air" / GbxBodyChunks,
)
body_chunks[0x0304E026] = Struct("wayPointType" / GbxEWayPointType)
body_chunks[0x0304E027] = Struct(
    "listVersion" / ExprValidator(Int32ul, obj_ == 10),
    "additionalVariantsGround" / PrefixedArray(Int32ul, GbxNodeRef),  # CGameCtnBlockInfoVariantGround
)
body_chunks[0x0304E028] = Struct(
    "symmetricalBlockInfoId" / GbxLookbackString,
    "dir" / GbxEDirection,
)
body_chunks[0x0304E029] = Struct(
    "fogVolumeBox" / GbxNodeRef,  # CPlugFogVolumeBox
)
body_chunks[0x0304E02A] = Struct(
    "version" / Int32ul,
    "sound1" / GbxNodeRef,
    "sound2" / GbxNodeRef,
    "sound1Loc" / If(lambda this: this.version < 3 or this.sound1 > 0, GbxIso4),
    "sound2Loc" / If(lambda this: this.version < 3 or this.sound1 > 0, GbxIso4),
)
body_chunks[0x0304E02B] = Struct(
    "version" / Int32ul,
    "u01" / Int32sl,
)
body_chunks[0x0304E02C] = Struct(
    "version" / Int32ul,
    "additionalVariantsAir" / PrefixedArray(Int32ul, GbxNodeRef),  # CGameCtnBlockInfoVariantAir
)
body_chunks[0x0304E02F] = Struct(
    "version" / Int32ul,
    "isPillar" / GbxBoolByte,
    "pillarShapeMultiDir" / GbxEMultiDirByte,
    StopIf(this.version < 1),
    "u01" / Byte,
)
body_chunks[0x0304E031] = Struct(
    "rest" / GbxBytesUntilFacade,
)

# 03059 CGameCtnBlockSkin

body_chunks[0x03059000] = Struct("text" / GbxString, "u01" / GbxString)
body_chunks[0x03059001] = Struct("text" / GbxString, "packDesc" / GbxFileRef)
body_chunks[0x03059002] = Struct(
    "text" / GbxString,
    "packDesc" / GbxFileRef,
    "parentPackDesc" / GbxFileRef,
)
body_chunks[0x03059003] = Struct(
    "version" / Int32ul,
    "foregroundPackDesc" / GbxFileRef,
)

# 0305B CGameCtnChallengeParameters

body_chunks[0x0305B001] = Struct(
    "tip" / GbxString[4],
)
body_chunks[0x0305B004] = Struct(
    "bronzeTime" / Int32sl,  # TODO GbxTimeNullable
    "silverTime" / Int32sl,  # TODO GbxTimeNullable
    "goldTime" / Int32sl,  # TODO GbxTimeNullable
    "authorTime" / Int32sl,  # TODO GbxTimeNullable
    "u01" / Int32sl,
)
body_chunks[0x0305B008] = Struct(
    "timeLimit" / Int32sl,  # TODO GbxTimeNullable
    "authorScore" / Int32sl,
)
body_chunks[0x0305B00D] = Struct(
    "raceValidateGhost" / GbxNodeRef,  # CGameCtnGhost
)

# 0311D CGameCtnZoneGenealogy
body_chunks[0x0311D002] = Struct(
    "zoneIds" / PrefixedArray(Int32ul, GbxLookbackString),
    "currentIndex" / Int32ul,
    "dir" / GbxEDirection,
    "currentZoneId" / GbxLookbackString,
)

# 03120 CGameCtnAutoTerrain
body_chunks[0x03120001] = Struct(
    "offset" / GbxInt3,
    "genealogy" / GbxNodeRef,  # CGameCtnZoneGenealogy
)

# 03122 CGameCtnBlockInfoMobil
body_chunks[0x03122002] = Struct(
    "version" / Int32ul,
    "solid_decals"
    / PrefixedArray(
        Int32ul,
        Struct(
            "u01" / Int32sl,
            "rest" / GreedyBytes,
        ),
    ),
    "u01" / Int32ul,
)
body_chunks[0x03122003] = Struct(
    "version" / ExprValidator(Int32ul, obj_ >= 2),
    "u01" / Int32sl,
    StopIf(this.version < 1),
    "has_geom_transformation" / GbxBoolByte,
    "geom_transformation"
    / If(
        this.has_geom_transformation,
        Struct("translation" / GbxVec3, "rotation" / GbxVec3),
    ),
    StopIf(this.version < 2),
    "solid_fid" / GbxNodeRef,
    "u14" / If(this.version >= 14, GbxNodeRef),  # CPlugSolid
    StopIf(this.version < 3),
    "prefab_fid" / GbxNodeRef,  # CPlugPrefab
    StopIf(this.version < 4),
    "u12" / GbxNodeRef,
    StopIf(this.version < 6),
    "u13" / GbxNodeRef,
    StopIf(this.version < 7),
    "u15" / GbxNodeRef,
    StopIf(this.version < 9),
    "u16" / Int32sl,
    StopIf(this.version < 16),
    "u17" / Int32sl,
    StopIf(this.version < 17),
    "u18" / Int32sl,
    StopIf(this.version < 18),
    "u19" / Bytes(29),
    "u27" / PrefixedArray(Int32ul, GbxNodeRef),
    "u28" / Int32sl,
)
body_chunks[0x03122004] = Struct(
    "version" / Int32ul,
    "list_version" / ExprValidator(Int32sl, obj_ == 10),
    "dyna_links" / PrefixedArray(Int32ul, GbxNodeRef),  # CGameCtnBlockInfoMobilLink
)

# 0315B CGameCtnBlockInfoVariant
body_chunks[0x0315B002] = Struct("multi_dir" / GbxEMultiDir)
body_chunks[0x0315B003] = Struct(
    "version" / Int32ul,
    "symmetrical_variant_index" / Int32sl,
    "cardinal_dir" / If(this.version == 0, Int32ul),
    StopIf(this.version < 1),
    "cardinal_dir" / GbxECardinalDir,
    "variant_base_type" / GbxEVariantBaseType,
    StopIf(this.version < 2),
    "no_pillar_below_index" / Int8sl,
)
body_chunks[0x0315B004] = Struct("u01" / Int16sl)
body_chunks[0x0315B005] = Struct(
    "version" / Int32ul,
    "mobils" / PrefixedArray(Int32ul, PrefixedArray(Int32ul, GbxNodeRef)),  # CGameCtnBlockInfoMobil
    StopIf(this.version < 2),
    "u02" / Int32sl,
    "u03" / Int32sl,
    StopIf(this.version < 3),
    "u04" / Int32sl,
)
body_chunks[0x0315B006] = Struct(
    "version" / Int32ul,
    "u01" / If(this.version < 9, GbxNodeRef),
    "screenInteractionTriggerSolid" / GbxNodeRef,
    "waypointTriggerSolid" / GbxNodeRef,
    "u04" / If(this.version >= 11, GbxNodeRef),
    "u05" / If(this.version >= 11, GbxNodeRef),
    "u02" / If(this.version < 9, Int32sl),
    StopIf(this.version < 2),
    "gate" / GbxNodeRef,  # CGameGateModel
    StopIf(this.version < 3),
    "teleporter" / GbxNodeRef,  # CGameTeleporterModel
    StopIf(this.version < 5),
    "u03" / GbxNodeRef,
    StopIf(this.version < 6),
    "turbine" / GbxNodeRef,  # CGameTurbineModel
    StopIf(this.version < 7),
    "flockModel" / GbxNodeRef,  # CPlugFlockModel
    "flockEmmiter" / If(this.flockModel > 0, PrefixedArray(Int32ul, Struct("TODO" / GreedyBytes))),
    StopIf(this.version < 8),
    "spawnModel" / GbxNodeRef,  # CGameSpawnModel
    StopIf(this.version < 10),
    "entitySpawners" / PrefixedArray(Int32ul, GbxNodeRef),  # CPlugEntitySpawner
)
body_chunks[0x0315B007] = Struct(
    "version" / Int32ul,
    "probe" / GbxNodeRef,  # CPlugProbe
)
body_chunks[0x0315B008] = Struct(
    "version" / Int32ul,
    "blockUnitModels" / PrefixedArray(Int32ul, GbxNodeRef),  # CGameCtnBlockUnitInfo
    "u01" / Int32sl,
    "hasManualSymmetryH" / GbxBool,
    "hasManualSymmetryV" / GbxBool,
    "hasManualSymmetryD1" / GbxBool,
    "hasManualSymmetryD2" / GbxBool,
    "spawn"
    / IfThenElse(
        this.version < 2,
        Struct("spawnTrans" / GbxVec3, "spawnYaw" / GbxVec3, "spawnPitch" / GbxVec3),
        Struct(
            "spawnTrans" / GbxVec3,
            "u01" / GbxVec3,  # SpawnYaw, SpawnPitch, SpawnRoll
        ),
    ),
    "name" / GbxString,
)
body_chunks[0x0315B009] = Struct(
    "version" / Int32ul,
    "u01"
    / PrefixedArray(
        Int32ul,
        Struct(
            "u01" / GbxNodeRef,
            "u02" / Bytes(16),
        ),
    ),  # PlacedPillarParam
    StopIf(this.version < 1),
    "u02"
    / PrefixedArray(
        Int32ul,
        Struct(
            "u01" / GbxNodeRef,
            "u02" / Bytes(16),
            "u06" / Byte,
        ),
    ),  # ReplacedPillarParam
)
body_chunks[0x0315B00A] = Struct(
    "version" / ExprValidator(Int32ul, obj_ >= 3),
    "compoundModel" / GbxNodeRef,  # CGameObjectPhyCompoundModel
)
body_chunks[0x0315B00B] = Struct(
    "version" / Int32ul,
    "waterVolumes"
    / PrefixedArray(
        Int32ul,
        Struct(
            "chunks" / PrefixedArray(Int32ul, GbxBoxInt),
            "u01" / Int32sl,
            "chunksSize" / GbxBox,
            "waterType" / GbxLookbackString,
        ),
    ),  # WaterArchive
)
body_chunks[0x0315B00D] = Struct(
    "version" / Int32sl,
    "u01" / Int32sl,
)

# 0315C CGameCtnBlockInfoVariantGround
body_chunks[0x0315C001] = Struct(
    "version" / Int32ul,
    "listVersion" / ExprValidator(Int32ul, obj_ == 10),
    "autoTerrains" / PrefixedArray(Int32ul, GbxNodeRef),  # CGameCtnAutoTerrain
    "autoTerrainHeightOffset" / Int32sl,
    "autoTerrainPlaceType" / GbxEAutoTerrainPlaceType,
)

# 06022 LightMapCache
body_chunks[0x0602200B] = Struct(
    "mapT3s" / PrefixedArray(Int32ul, Int32sl),
)
body_chunks[0x0602200F] = Struct(
    "quality" / GbxELightMapCacheEQuality,
    "u01" / Int32sl,
)
body_chunks[0x06022013] = Struct(
    "u01" / GbxBool,
    "u02" / GbxBool,
    "u03" / GbxFileTime,
)
body_chunks[0x06022015] = Struct(
    "version" / Int32ul,  # 5
    "u01" / Bytes(8),
    "collection" / GbxLookbackString,
    "decoration" / GbxLookbackString,
    "u02" / Int32sl,
    "u03" / Int32sl,  # 0
    "timeOfDay" / Int32sl,
    "u04" / Int32sl,  # 0
    "u05" / Int32sl,
    "u06" / GbxString,
)
body_chunks[0x06022016] = Struct(
    "version" / GbxELightMapCacheEVersion,
)
body_chunks[0x06022017] = Struct(
    "decal2d" / Int32sl,
    "decal3d" / Int32sl,
)
body_chunks[0x06022018] = Struct(
    "u01" / GbxFileTime,
)
body_chunks[0x06022019] = Struct(
    "qualityVer" / GbxELightMapCacheEQualityVer,
)


def divide_by_four(data, ctx):
    if (data % 4) != 0:
        print("Found a non-multiple of 4")
    return int(data / 4)


def mult_by_four(data, ctx):
    return int(data * 4)


GbxLightMapCacheMapping = Struct(
    "version" / Int32sl,  # 9
    "u01_size" / GbxInt3,
    "u02_lower_bounds" / GbxVec3,
    "u03_upper_bounds" / GbxVec3,
    "u04" / Int32sl,
    "count" / Int32ul,  # meshes
    "data1" / CompressedZLib(GbxFloat[this._.count]),
    "objBindings"
    / CompressedZLib(
        Struct(
            "meshIdx" / Int32ul,
            "objIdx" / ExprAdapter(Int16ul, divide_by_four, mult_by_four),
            "objGroupIdx" / Int16ul,
        )[this._.count]
    ),
    "positions" / CompressedZLib(GbxTexPos[this._.count]),  # position of the mesh uv in lightmap
    "sizes" / CompressedZLib(GbxTexPos[this._.count]),
    "u09" / Int32sl,
    "colorData" / CompressedZLib(PrefixedArray(Int32ul, PrefixedArray(Int32ul, Int8ul))),
    # first one: shadow brightness
)
body_chunks[0x0602201A] = Struct(
    "version" / Int32ul,  # 13
    "countSMap" / Int32ul,
    "u01" / Bytes(this.countSMap * 5 * 4),
    "ambSamples" / Int32sl,  # ambiant light
    "dirSamples" / Int32sl,  # direct light
    "pntSamples" / Int32sl,  # point light / lumière ponctuelle
    "sortMode" / GbxELightMapCacheESortMode,
    "allocMode" / GbxELightMapCacheEAllocMode,
    "u02" / Int32sl,
    "compressMode" / GbxELightMapCacheECompressMode,
    "u03" / Int32sl,
    "bump" / GbxELightMapCacheEBump,
    "maps"
    / PrefixedArray(
        Int32ul,
        Struct(
            "u00" / Int32sl,  # 0
            "ReplayTime" / Int32sl,
            "u01" / Bytes(4),
            "u02" / GbxVec4,
            "u03" / GbxBool,
            "u04" / Float16l[3],  # related to frame2?
            "u05" / GbxBool,
            "u06" / Int32sl,  # lod?
            "u07" / Int32sl,
            "u10" / GbxVec3,  # related to frame3?
            "u11" / Int32sl,
        ),
    ),
    "u04" / GbxBool,
    "spriteOriginYWasWronglyTop" / GbxBool,
    "mapping" / GbxLightMapCacheMapping,
    "gpuPlatform" / GbxELightMapCacheEPlugGpuPlatform,
    "allocatedTexelByMeter" / GbxFloat,
    "u08" / Int32sl,
    "u09" / Int32sl,
    "rest" / GreedyBytes,
)

# 09003 CPlugCrystal

GbxCrystal = Struct(
    "version" / Int32ul,  # 37
    "u06" / Int32sl,  # 4
    "u07" / Int32sl,  # 3
    "u08" / Int32sl,  # 4
    "u09" / GbxFloat,  # 64
    "u10" / Int32sl,  # 2
    "u11" / GbxFloat,  # 128
    "u12" / Int32sl,  # 1
    "u13" / GbxFloat,  # 192
    "u14" / Int32sl,  # 0 - SAnchorInfo array?
    "groups"
    / PrefixedArray(
        Int32ul,
        Struct(
            "u01" / Int32sl,
            "u02" / Byte,  # bool?
            "u03" / Int32sl,  # -1, nodref?
            "name" / GbxString,
            "u04" / Int32sl,  # -1, nodref?
            "u05" / PrefixedArray(Int32ul, Int32sl),
        ),
    ),
    "isEmbeddedCrystal" / GbxBoolByte,
    "u30" / Int32sl,  # 0
    "u31" / Int32sl,  # 0
    "embeddedCrystal"
    / Struct(
        "positions" / PrefixedArray(Int32ul, GbxVec3),
        "edgesCount" / Int32ul,
        "unfacedEdgesCount" / Int32ul,
        "unfacedEdges" / GbxOptimizedIntArray(this.unfacedEdgesCount * 2),
        "facesCount" / Int32ul,
        "uvs" / PrefixedArray(Int32ul, GbxVec2),
        "faceIndiciesCount" / Int32ul,
        "faceIndicies" / GbxOptimizedIntArray(this.faceIndiciesCount),
        "faces"
        / Array(
            this.facesCount,
            Struct(
                "vertCount" / Int8ul,
                "inds" / GbxOptimizedIntArray(this.vertCount + 3, lambda this: len(this._.positions)),
                "material_index" / GbxOptimizedInt(1),  # TODO
                "group_index" / GbxOptimizedInt(1),  # TODO
            ),
        ),
        "u22" / Int32sl,
    ),
)
GbxCrystal_Geometry = Struct(
    "crystal" / GbxCrystal,
    "u01" / PrefixedArray(Int32ul, Int32sl),
    "isVisible" / GbxBool,
    "isCollidable" / GbxBool,
)
GbxCrystal_Trigger = Struct("crystal" / GbxCrystal, "u01" / PrefixedArray(Int32ul, Int32sl))

body_chunks[0x09003003] = Struct(
    "version" / Int32ul,
    "materials" / PrefixedArray(Int32ul, GbxMaterial),
)
body_chunks[0x09003004] = Struct(
    "version" / Int32ul,
    "u01_size" / Int32ul,
    "u01" / Bytes(this.u01_size),
    "u02" / Bytes(4),
)
body_chunks[0x09003005] = Struct(
    "version" / Int32ul,
    "layer_count" / Rebuild(Int32ul, lambda this: len(this.layers)),
    "layers"
    / Array(
        this.layer_count,
        Struct(
            "type" / GbxELayerType,
            "version" / Int32ul,
            "u02" / GbxBool,
            "id" / GbxLookbackString,
            "name" / GbxString,
            "is_enabled" / If(this.version >= 1, GbxBool),
            "type_version" / Int32ul,
            "content"
            / Switch(
                this.type,
                {
                    GbxELayerType.Geometry: GbxCrystal_Geometry,
                    GbxELayerType.Trigger: GbxCrystal_Trigger,
                    GbxELayerType.Cubes: GreedyBytes,
                },
                GreedyBytes,
            ),
        ),
    ),
)
body_chunks[0x09003006] = Struct(
    "version" / Int32ul,
    "u01" / If(this.version == 0, PrefixedArray(Int32ul, GbxVec2)),
    StopIf(this.version < 1),
    "u02" / PrefixedArray(Int32ul, Int16sl[2]),
    StopIf(this.version < 2),
    "u03Count" / Int32ul,
    "u03" / GbxOptimizedIntArray(this.u03Count),
)
body_chunks[0x09003007] = Struct(
    "version" / Int32ul,
    "u01" / PrefixedArray(Int32ul, GbxFloat),
    "u02" / PrefixedArray(Int32ul, Int32sl),
)

# 09006 CPlugVisual
body_chunks[0x09006001] = Struct("u01" / GbxNodeRef)
body_chunks[0x09006004] = Struct("u01" / GbxNodeRef)
body_chunks[0x09006005] = Struct("sub_visuals" / PrefixedArray(Int32ul, GbxInt3))
body_chunks[0x09006009] = Struct("has_vertex_normals " / GbxBool)
body_chunks[0x0900600B] = Struct(
    "splits " / PrefixedArray(Int32ul, Struct("u01" / Int32sl, "u02" / Int32sl, "u03" / GbxBox))
)


# def convert_chunk_flags_to_flags(chunk_flags, ctx):
#     flags = 0
#     flags |= chunk_flags & 15
#     flags |= (chunk_flags << 1) & 0x20
#     flags |= (chunk_flags << 2) & 0x80
#     flags |= (chunk_flags << 2) & 0x100
#     flags |= (chunk_flags << 13) & 0x100000
#     flags |= (chunk_flags << 13) & 0x200000
#     flags |= (chunk_flags << 13) & 0x400000

#     return flags


# def convert_flags_to_chunk_flags(flags, ctx):
#     # TODO
#     chunk_flags = flags & 15  # bit0-4
#     chunk_flags |= (flags >> 1) & 0x10  # bit 5
#     chunk_flags |= (flags >> 2) & 0x20  # bit 7
#     chunk_flags |= (flags >> 2) & 0x40  # bit 8
#     chunk_flags |= (flags >> 13) & 0x80  # bit 20
#     chunk_flags |= (flags >> 13) & 0x100  # bit 21
#     chunk_flags |= (flags >> 13) & 0x200  # bit 22

#     return chunk_flags


body_chunks[0x0900600D] = Struct(
    "ChunkFlags"  # only on bits 0x7001af
    / ByteSwapped(
        BitStruct(
            Padding(9),
            "bit22" / Flag,
            "bit21" / Flag,  # vert_u04 stored as Dec4N?
            "bit20" / Flag,
            Padding(11),
            "bit8" / Flag,
            "bit7" / Flag,
            Padding(1),
            "HasVertexNormals" / Flag,
            "isIndexationStaticBit" / Flag,
            "isGeometryStaticBit" / Flag,
            "SkinIndexCount" / BitsInteger(3),  # max 4
        )
    ),
    "TexCoordCount" / Int32ul,
    "VertexCount" / Int32ul,
    "vertexStreams" / PrefixedArray(Int32ul, GbxNodeRef),
    "texCoords"
    / Array(
        this.TexCoordCount,
        Struct(
            # TODO recheck
            "version" / Int32ul,
            "count" / IfThenElse(this.version >= 3, Int32ul, Computed(this._.count)),
            "flags" / If(this.version >= 3, Int32ul),
            "tex_coords"
            / Array(
                this.count,
                Struct(
                    "uv" / GbxVec2,
                    "u01" / If(lambda this: 1 <= this._.version < 3, Int32sl),
                    "u02" / If(lambda this: this._.version == 2, Int32sl),
                ),
            ),
            "u01"
            / If(
                lambda this: this.flags,
                Array(lambda this: this.count * (this.flags & 0xFF), GbxFloat),
            ),
        ),
    ),
    "visualSkin"
    / If(
        lambda this: this.ChunkFlags.SkinIndexCount > 0,
        Struct(
            "u01" / GbxBool,
            "u02" / Int32sl,
            "u03" / If(this._.version >= 3, GbxBool),
            "u04" / If(this._.version >= 3, GbxBool),
            "u05"
            / If(
                this.u03,
                Array(lambda this: this._.VertexCount, GbxFloat[this._.ChunkFlags.SkinIndexCount]),  # or GbxVec3?
            ),
            "boneNames" / PrefixedArray(Int32ul, GbxLookbackString),
            StopIf(this._.version < 2),
            "boneIndices" / PrefixedArray(Int32ul, Int32sl),
        ),
    ),
    "u01" / GbxBox,
)
body_chunks[0x0900600E] = Struct(
    *body_chunks[0x0900600D].subcons,
    "bitmapElemToPacks" / PrefixedArray(Int32ul, Struct("u01" / Bytes(20))),
)
body_chunks[0x0900600F] = Struct(
    "version" / Int32ul,
    *body_chunks[0x0900600E].subcons,
    StopIf(this.version < 5),
    "u02" / PrefixedArray(Int32ul, Int16sl),
    StopIf(this.version < 6),
    "u03" / Int32ul,
    "ByteCount" / Int32ul,
    "u04" / If(this.ByteCount > 0, Bytes(this.ByteCount - 4)),
)
body_chunks[0x09006010] = Struct("version" / Int32ul, "morph_count" / ExprValidator(Int32ul, obj_ == 0))

# 0900C CPlugSurface

GbxSurfMesh = Struct(
    "version" / ExprValidator(Int32ul, obj_ == 7),
    "vertices" / PrefixedArray(Int32ul, GbxVec3),
    "triangles"
    / PrefixedArray(
        Int32ul,
        Struct(
            "face" / GbxInt3,
            "materialId" / GbxPlugSurfaceMaterialId,
            "materialIndex" / Int16sl,
        ),
    ),
)
GbxSurfConvexPolyhedron = Struct(
    "version" / Int32ul,
    "u01" / Int32sl,  # if != 0, other code
    "AABB" / GbxBox,  # 0x88
    "vertices" / PrefixedArray(Int32ul, GbxVec3),
    # "u01" / PrefixedArray(Int32ul, Int32sl),
    # "u02" / PrefixedArray(Int32ul, Int32sl[2]),
    "u05" / Int16sl,
)
body_chunks[0x0900C003] = Struct(
    "version" / Int32ul,
    "surf_version" / If(this.version >= 2, Int32ul),
    "surf"
    / Struct(
        "type" / GbxESurfType,
        "data"
        / Switch(
            this.type,
            {
                GbxESurfType.Mesh: GbxSurfMesh,
                # GbxESurfType.ConvexPolyhedron: GbxSurfConvexPolyhedron,
            },
            GbxBytesUntilFacade,
        ),
        "u01" / If(this._.surf_version >= 2, GbxVec3),  # mainDir? like for boost its dir?
    ),
    "materials"
    / PrefixedArray(
        Int32ul,
        Struct(
            "hasMaterial" / GbxBool,  # Rebuild(GbxBool, lambda this: this.material is not None),
            "material" / If(this.hasMaterial, GbxNodeRef),
            "materialId" / If(lambda this: not this.hasMaterial, GbxPlugSurfaceMaterialId),
        ),
    ),
    "u01" / If(lambda this: len(this.materials) > 0, Int32sl),  # TODO check condition
    "materialsIds" / PrefixedArray(Int32ul, GbxPlugSurfaceMaterialId),
    "skel" / If(this.version >= 1, GbxNodeRef),
)

# 0902C CPlugVisual3D


def get_chunk_900600F(ctx):
    for chunk in ctx._._._array:
        if chunk.chunk_id == 0x900600F:
            return chunk.chunk


body_chunks[0x0902C002] = Struct("u01" / GbxNodeRef)
body_chunks[0x0902C004] = Struct(
    "flags" / Computed(lambda ctx: get_chunk_900600F(ctx).ChunkFlags),
    "readNormals" / Computed(lambda this: not this.flags.bit22 or this.flags.HasVertexNormals),
    "u02" / Computed(lambda this: not this.flags.bit22 or this.flags.bit8),
    "u03" / Computed(lambda this: this.flags.bit20),  # or CPlugVisualSprite
    "vertices"
    / IfThenElse(
        # TODO verify
        this.u01 and not this.u03 and not this.flags.bit21 and this.u02,
        Bytes(0x28)[lambda ctx: get_chunk_900600F(ctx).VertexCount],
        If(
            lambda ctx: len(get_chunk_900600F(ctx).vertexStreams) == 0,
            Array(
                lambda ctx: get_chunk_900600F(ctx).VertexCount,
                Struct(
                    "position" / GbxVec3,
                    "normal"
                    / If(
                        lambda this: this._.readNormals,
                        IfThenElse(
                            this._.u03,
                            GbxDec3N,
                            GbxVec3,
                        ),
                    ),
                    "u01"
                    / IfThenElse(
                        this._.u02,
                        IfThenElse(
                            this._.flags.bit21,
                            GbxUDec4N,
                            GbxVec4,
                        ),
                        Computed(Container(x=1.0, y=1.0, z=1.0, w=1.0)),
                    ),
                ),
            ),
        ),
    ),
    "tangentsU" / PrefixedArray(Int32ul, IfThenElse(this._.flags.bit20, GbxDec3N, GbxVec3)),
    "tangentsV" / PrefixedArray(Int32ul, IfThenElse(this._.flags.bit20, GbxDec3N, GbxVec3)),
)

# 0903A CPlugMaterialCustom

body_chunks[0x0903A004] = Struct(
    "u01" / PrefixedArray(Int32ul, Int32sl),
)
body_chunks[0x0903A00A] = Struct(
    "gpu_fxs"
    / PrefixedArray(
        Int32ul,
        Struct(
            "u01" / GbxLookbackString,
            "count1" / Int32sl,
            "count2" / Int32sl,
            "u02" / GbxBool,
            "u03" / Bytes(4)[this.count1][this.count2],
        ),
    ),
    "u01" / Bytes(4),
)
body_chunks[0x0903A00C] = Struct(
    "u01"
    / PrefixedArray(
        Int32ul,
        Struct(
            "name" / GbxLookbackString,
            "b01" / Bytes(4),
        ),
    ),
)
body_chunks[0x0903A012] = Struct(
    "u01" / Int32sl,
)
body_chunks[0x0903A013] = Struct(
    "version" / Int32ul,  # 0
    "textures"
    / PrefixedArray(
        Int32ul,
        Struct(
            "name" / GbxLookbackString,
            "u01" / Bytes(4),
            "textureNod" / GbxNodeRef,
            "u02" / Bytes(8),
        ),
    ),
)

# 09051 CPlugTreeGenerator
body_chunks[0x09051000] = Struct(
    "version" / Int32ul,
)

# 09056 CPlugVertexStream

body_chunks[0x09056000] = Struct(
    "version" / Int32ul,
    "num_vertices" / Int32sl,
    "u01" / Int32sl,
    "baseVertexStream" / GbxNodeRef,
    StopIf(lambda this: this.num_vertices == 0 or this.baseVertexStream != -1),
    "DataDecl"
    / PrefixedArray(
        Int32ul,
        Struct(
            "header"
            / ByteSwapped(
                BitStruct(
                    "u20" / BitsInteger(20),
                    "PtrOffset" / BitsInteger(10),
                    "u2" / BitsInteger(2),
                    "Space" / GbxEPlugVDclSpace,  # 4 bits
                    "Stride" / BitsInteger(10),
                    "Type" / GbxEPlugVDclType,  # 9 bits
                    "Name" / GbxEPlugVDcl,  # 9 bits
                )
            ),
            StopIf(this.header.PtrOffset == 0),
            "iDataDeclShared" / Int16ul,  # TODO check
            "Offset" / Int16ul,
        ),
    ),
    "compressFloat3InLocal3D" / GbxBool,  # always true for version > 0?
    "Data"
    / Array(
        lambda this: len(this.DataDecl),
        Switch(
            lambda this: "Dec3N"
            if this.DataDecl[this._index].header.Space == "Local3D"
            and this.DataDecl[this._index].header.Type == "Float3"
            and this.compressFloat3InLocal3D
            else this.DataDecl[this._index].header.Type,
            {
                "Float1": Float32l[this.num_vertices],
                "Float2": GbxVec2[this.num_vertices],
                "Float3": GbxVec3[this.num_vertices],
                "Float4": GbxVec4[this.num_vertices],
                "ColorD3D": GbxColor[this.num_vertices],
                "UByte4": Int8ul[4][this.num_vertices],
                "Short2": Int16sl[2][this.num_vertices],
                "Short4": Int16sl[4][this.num_vertices],
                "UByte4N": Bytes(4)[this.num_vertices],
                "Short2N": Bytes(4)[this.num_vertices],
                "Short4N": Bytes(8)[this.num_vertices],
                "UShort2N": Bytes(4)[this.num_vertices],
                "UShort4N": Bytes(8)[this.num_vertices],
                "UDec3": Bytes(4)[this.num_vertices],
                "Dec3N": GbxDec3N[this.num_vertices],
                "Half2": Int16sl[2][this.num_vertices],
                "Half4": Int16sl[4][this.num_vertices],
            },
        ),
    ),
)

# 09057 CPlugIndexBuffer

body_chunks[0x09057000] = Struct(
    "version" / Int32ul,
    "indices" / PrefixedArray(Int32ul, Int16ul),
)
body_chunks[0x09057001] = Struct(
    "flags" / Int32ul,  # TODO check if not 2 what that means
    "indices" / PrefixedArray(Int32ul, Int16sl),
)

# 0906A CPlugVisualIndexed

body_chunks[0x0906A001] = Struct(
    "has_index_buffer" / GbxBool,  # or array length ? or version ?
    "index_buffer" / If(this.has_index_buffer, GbxBodyChunks),
)

# 09079 CPlugMaterial
body_chunks[0x09079001] = Struct(
    "u01" / GbxNodeRef,  # CPlugMaterialFx
)
body_chunks[0x09079007] = Struct(
    "custom_material" / GbxNodeRef,  # CPlugMaterialCustom
)
body_chunks[0x09079010] = Struct(
    "u01" / GbxFloat,
)
body_chunks[0x09079011] = Struct(
    "u01" / PrefixedArray(Int32ul, GbxLookbackString),
)
body_chunks[0x09079012] = Struct(
    "version" / Int32sl,  # 2
    StopIf(this.version < 1),
    "u01" / GbxString,
    "u02" / GbxFileTime,
    "u03" / Bytes(4 * 8),
    "u04" / If(this.version >= 2, Bytes(4)),
)
body_chunks[0x09079013] = Struct(
    "u01" / PrefixedArray(Int32ul, GbxString),
)
body_chunks[0x09079015] = Struct(
    "version" / Int32ul,  # 7
    "baseMaterial" / GbxNodeRef,  # CPlugMaterial
    "u01"
    / IfThenElse(
        this.baseMaterial == -1,
        Struct(
            "u01" / Bytes(40),
        ),
        Struct(
            StopIf(this._.version < 6),
            "colorTargetTable" / PrefixedArray(Int32ul, GbxNodeRef),  # CPlugMaterialColorTargetTable
            StopIf(this._.version < 7),
            "waterArray" / GbxNodeRef,  # CPlugMaterialWaterArray
        ),
    ),
)
body_chunks[0x09079016] = Struct(
    "version" / Int32ul,
    "flags" / Bytes(4),
)  # 0
body_chunks[0x09079017] = Struct(
    "version" / Int32ul,  # 1
    StopIf(this.version < 1),
    "flags" / Bytes(4),
    "u01" / GbxVec2,
    "u02" / GbxString,
)
body_chunks[0x09079019] = Struct(
    "version" / Int32ul,  # 0
    StopIf(this.version < 1),
    "u01" / Int32sl,
    "flags" / If(this.u01 != 0, Bytes(4)),
)

# 09144 CPlugDynaObjectModel
body_chunks[0x09144000] = Struct(
    "version" / Int32ul,
    "IsStatic" / GbxBool,  # si c'est un dyna mais qui reste tjs statique
    "DynamizeOnSpawn" / GbxBool,
    "Mesh" / GbxNodeRef,
    "DynaShape" / GbxNodeRef,  # Boite de collision apres destruction, ne supporte pas mesh quelconque
    "StaticShape" / GbxNodeRef,  # Boite de collision avant destruction
    "DestructibleModel"
    / Struct(
        "BreakSpeedKmh" / If(this._.version > 1, GbxFloat),
        "Mass" / If(this._.version > 2, GbxFloat),
        "LightAliveDurationSc_Min" / If(this._.version > 4, GbxFloat),
        "LightAliveDurationSc_Max" / If(this._.version > 4, GbxFloat),
    ),
    # If version > 3
    "u01" / Int32sl,
    "u02" / Int32sl,
    "u03" / Byte,
    "u04" / Byte,
    "u05" / Int32sl,
    "u06" / Int32sl,
    # If version > 5
    "u07" / Byte,
    "u08" / Int32sl,
    "u09" / Int32sl,
    "LocAnim" / If(this.version > 6, GbxNodeRef),
    "u10" / If(this.version > 7, Int32sl),
    "LocAnimIsPhysical"
    / If(this.version > 9, GbxBool),  # LocAnim purement visuel ou pas. evitons les calculs physiques si pas necessaire
    "WaterModel" / GbxNodeRef,
)


def breakpoint(obj, ctx):
    return obj


def newPropSubEntityModel(obj, ctx):
    print(">>> newPropSubEntityModel")
    return obj


# 09145 CPlugPrefab
body_chunks[0x09145000] = Struct(
    "version" / Int32ul,
    "updatedTime" / GbxFileTime,
    "url" / GbxString,
    "u01" / Bytes(4),  # kind of timestamp?
    "EntsCount" / Rebuild(Int32ul, len_(this.Ents)),
    "u02" / Bytes(4),
    "Ents"
    / Array(
        this.EntsCount,
        Select(
            Struct(
                "model" / GbxNodeRef,
                "rot" / GbxQuat,
                "pos" / GbxVec3,
                "dynaParams"
                / Optional(  # NPlugDynaObjectModel_SInstanceParams
                    Struct(
                        "chunkId" / ExprValidator(Hex(Int32ul), obj_ == 0x2F0B6000),
                        "TextureId" / Int32sl,
                        "u01" / GbxFloat,
                        # "!! Attention reserve a de rares objets dont l\'animation conserve a peu pres la shadow (tube qui tourne sur lui meme /ex), cette shadow (vue au loin) ne sera pas animee !!"
                        "CastStaticShadow" / GbxBool,
                        "IsKinematic" / GbxBool,
                        "u04" / GbxFloat,
                        "u05" / GbxFloat,
                        "u06" / GbxFloat,
                    )
                ),
                "constraintParams"
                / Optional(  # NPlugDyna_SPrefabConstraintParams
                    Struct(
                        "chunkId" / ExprValidator(Hex(Int32ul), obj_ == 0x2F0C8000),
                        "Ent1" / Int32sl,
                        "Ent2" / Int32sl,
                        "Pos1" / GbxVec3,
                        "Pos2" / GbxVec3,
                    )
                ),
                "placementParams"
                / Optional(  # NPlugItemPlacement_SPlacement
                    Struct(
                        "chunkId" / ExprValidator(Hex(Int32ul), obj_ == 0x2F0A9000),
                        "version" / Int32ul,
                        "iLayout" / Int32sl,
                        "Options"
                        / PrefixedArray(
                            Int32ul,
                            Struct(  # NPlugItemPlacement_SPlacementOption 0x30166000
                                "RequiredTags" / GbxDictString,
                            ),
                        ),
                    ),
                ),
                "placementGroupParams"
                / Optional(  # NPlugItemPlacement_SPlacementGroup
                    Struct(
                        "chunkId" / ExprValidator(Hex(Int32ul), obj_ == 0x2F0D8000),
                        "version" / Int32ul,
                        "Placements"
                        / PrefixedArray(
                            Int32ul,
                            Struct(
                                "version" / Int32ul,
                                "iLayout" / Int32sl,
                                "Options"
                                / PrefixedArray(
                                    Int32ul,
                                    Struct(  # NPlugItemPlacement_SPlacementOption 0x30166000
                                        "RequiredTags" / GbxDictString,
                                    ),
                                ),
                            ),
                        ),
                        "u01" / PrefixedArray(Int32ul, Int16sl),
                        "u02" / PrefixedArray(Int32ul, GbxLoc),
                    ),
                ),
                "instanceParams"
                / Optional(  # NPlugStaticObjectModel_SInstanceParams
                    Struct(
                        "chunkId" / ExprValidator(Hex(Int32ul), obj_ == 0x2F0D9000),
                        "Phase01" / GbxFloat,
                    ),
                    # No LodGroupId when this is true? looks like it's a float
                ),
                "LodGroupId" / If(this.model >= 0, Int32sl),
                "name" / GbxString,
            ),
            GreedyBytes,
        ),
    ),
)


def check(obj, ctx):
    if obj:
        pass
    print(obj)
    return obj


# 09159 CPlugStaticObjectModel
body_chunks[0x09159000] = Select(
    Struct(
        "version" / Int32sl,
        "mesh" / GbxNodeRef,
        "isMeshCollidable" / GbxBoolByte,
        "collidableShape" / If(lambda this: not this.isMeshCollidable, GbxNodeRef),
    )
)

# 0915C CPlugFxSystem
GbxEFxSystemNodeType = Enum(
    Int32sl,
    No=-1,
    Parallel=0,
    Condition=1,
    SubFxSystem=2,
    UpdateVar=3,
    ParticleEmitter=4,
    SoundEmitter=5,
)

PlugFxSystemNodes = {}

#  Meta::CPlugFxSystemNode 0x2F0C1000
body_chunks[0x2F0C1000] = Struct(
    "type" / GbxEFxSystemNodeType,
    "node" / Switch(this.type, PlugFxSystemNodes),
)
#  Meta::CPlugFxSystemNode_Parallel 0x2F0C2000
PlugFxSystemNodes["Parallel"] = body_chunks[0x2F0C2000] = Struct(
    "name" / GbxLookbackString,
    "Children" / PrefixedArray(Int32ul, body_chunks[0x2F0C1000]),
)
#  Meta::CPlugFxSystemNode_Condition 0x2F0C3000
PlugFxSystemNodes["Condition"] = body_chunks[0x2F0C3000] = Struct(
    "name" / GbxLookbackString,
    "ConditionExpr" / GbxString,
    "Child" / body_chunks[0x2F0C1000],
)
#  Meta::CPlugFxSystemNode_SubFxSystem 0x2F0C5000
PlugFxSystemNodes["SubFxSystem"] = body_chunks[0x2F0C5000] = Struct(
    "name" / GbxLookbackString,
    "FxSystem" / body_chunks[0x2F0C1000],
)
#  Meta::CPlugFxSystemNode_UpdateVar 0x2F0C6000
PlugFxSystemNodes["UpdateVar"] = body_chunks[0x2F0C6000] = Struct(
    "name" / GbxLookbackString,
    "VarName" / GbxLookbackString,
    "ResetToDefaultIfInactive" / GbxBool,
    "UpdateVarExpr" / GbxString,
)
#  Meta::CPlugFxSystemNode_ParticleEmitter 0x2F0C4000
PlugFxSystemNodes["ParticleEmitter"] = body_chunks[0x2F0C4000] = Struct(
    # if version < 5 osef
    "name" / GbxLookbackString,
    "Model" / GbxNodeRef,  # CPlugParticleEmitterModel
    "JointName" / GbxLookbackString,
    "LocalOffsetExpr" / GbxString,
    "WorldOffsetExpr" / GbxString,
    "LinearVelInWExpr" / GbxString,
    "SpawnFreqModifierExpr" / GbxString,
    "ScaleExpr" / GbxString,
    "LAmbientExpr" / GbxString,
    "UpExpr" / GbxString,
    "DOVExpr" / GbxString,
    "OpacityExpr" / GbxString,
    "WaterTopExpr" / GbxString,
    "DOVAndUpAreLocalSpace" / GbxBool,
    "LinearHue01" / GbxString,
    "HueLightness" / GbxString,
)
#  Meta::CPlugFxSystemNode_SoundEmitter 0x2F0C7000
PlugFxSystemNodes["SoundEmitter"] = body_chunks[0x2F0C7000] = Struct(
    "name" / GbxLookbackString,
    "Model" / GbxNodeRef,  # CPlugSoundSurface
    "JointName" / GbxString,
    "PlayOnce" / GbxBool,
    "VolumeExpr" / GbxString,
    "VolumeExpr" / GbxString,
    "FadeOffDuration" / Int32sl,  # In seconds. If PlayOnce, 0 = the sound is not cut.
    "PitchExpr" / GbxString,
    "AudioGroupHandleExpr" / GbxString,
    "AudioBalanceGroup" / Int32sl,
    "Surface"
    / If(
        this.Model >= 0,
        Struct(
            "SurfaceIdExpr" / GbxString,
            "SpeedKmhExpr" / GbxString,
            "SkidIntensityExpr" / GbxString,
            "SkidSpeedKmhExpr" / GbxString,
        ),
    ),
)

body_chunks[0x0915C000] = Struct(
    "version" / Int32sl,
    "SystemNodesVersion" / Int32sl,  # 8
    "rootNode" / body_chunks[0x2F0C1000],
    "ContextClassId" / Int32sl,  # GbxLookbackString?
    "ExtraContextClassId" / Int32sl,  # GbxLookbackString?
    "VarsCount" / Int32ul,
    "VarsVersion" / Int32ul,  # 55
    "Vars"
    / Array(
        this.VarsCount,
        # SPlugGraphVar TODO
        Struct(
            "u01" / GbxLookbackString,
            "u02" / Byte,
            # TODO
        ),
    ),
)

# 0915D CPlugGameSkinAndFolder
body_chunks[0x0915D000] = Struct("Remapping" / GbxNodeRef, "RemapFolder" / GbxString)
body_chunks[0x0915D001] = Struct("name" / GbxLookbackString)


# 09178 NPlugTrigger_SWaypoint

body_chunks[0x09178000] = Struct(
    "version" / Int32ul,  # 1
    "Type" / GbxEWayPointType,
    "TriggerShape" / GbxNodeRef,
    "NoRespawn" / GbxBool,
)

# 09179 NPlugTrigger_SSpecial
body_chunks[0x09179000] = Struct(
    "version" / Int32ul,
    "surf" / GbxNodeRef,
)

# 0917A CPlugSpawnModel
body_chunks[0x0917A000] = Struct(
    "version" / Int32ul,
    "Loc" / GbxIso4,
    "TorqueX" / GbxFloat,
    "TorqueDuration" / Int32ul,
    "DefaultGravitySpawn" / GbxVec3,
    "u01" / Int32sl,
)

# 0917B CPlugEditorHelper
body_chunks[0x0917B000] = Struct(
    "version" / Int32ul,
    "helper" / GbxNodeRef,
    Probe(),
)

# 09187 NPlugItemPlacement_SClass
body_chunks[0x09187000] = Struct(
    "version" / Int32ul,
    "size_group" / GbxLookbackString,
    "compatible_groups_ids" / PrefixedArray(Int32ul, GbxLookbackString),
    "always_up" / GbxBool,
    "align_to_interior" / GbxBool,
    "align_to_world_dir" / GbxBool,
    "world_dir" / GbxVec3,
    "patch_layouts"
    / PrefixedArray(
        Int32ul,
        Struct(
            "item_count" / Int32ul,
            "item_spacing" / GbxFloat,
            "fill_align" / GbxEFillAlign,
            "fill_dir" / GbxEFillDir,
            "normed_pos" / GbxFloat,
            "u04" / GbxFloat,  # DistFromNormedPos?
            "only_on_groups" / PrefixedArray(Int32ul, GbxLookbackString),
            "altitude" / GbxFloat,
            "u06" / GbxFloat,  # FillBorderOffset?
        ),
    ),
    "group_cur_patch_layouts" / PrefixedArray(Int32ul, Int32sl),
)

# 09189 CPlugMediaClipList
body_chunks[0x09189000] = Struct(
    "u01" / Int32ul,
    "MediaClipFids" / PrefixedArray(Int32ul, GbxNodeRef),
)

# 090B2 CPlugParticleEmitterSubModel
body_chunks[0x090B202D] = Struct(
    "u01" / Bytes(61),
)
body_chunks[0x090B202E] = Struct(
    "u01" / Int32sl,
    "SplashModel" / GbxNodeRef,  # CPlugParticleSplashModel
)
body_chunks[0x090B202F] = Struct(
    "u01" / Bytes(76),
)
body_chunks[0x090B2030] = Struct(
    "u01" / Bytes(16),
)
body_chunks[0x090B2031] = Struct(
    "u01" / Bytes(164),
)
body_chunks[0x090B2032] = Struct(
    "u01" / Bytes(36),
)
body_chunks[0x090B2033] = Struct(
    "u01" / Bytes(293),
)
body_chunks[0x090B2034] = Struct(
    "u01" / Bytes(97),
)
body_chunks[0x090B2035] = Struct(
    "u01" / Bytes(4),
)
body_chunks[0x090B2036] = Struct(
    "u01" / Bytes(16),
)
body_chunks[0x090B2037] = Struct(
    "u01" / Bytes(100),
)
body_chunks[0x090B2038] = Struct(
    "u01" / Bytes(12),
)
body_chunks[0x090B2039] = Struct(
    "u01" / Bytes(48),
)
body_chunks[0x090B203A] = Struct(
    "u01" / Int32sl,
    "u02" / GbxNodeRef,  # CPlugParticleGpuSpawn
    "u03" / GbxNodeRef,  # CPlugParticleGpuModel
)
body_chunks[0x090B203B] = Struct(
    "u01" / Bytes(48),
)

# 090B3 CPlugParticleEmitterModel

body_chunks[0x090B3000] = Struct(
    "listVersion" / Int32ul,
    "ParticleEmitterSubModels" / PrefixedArray(Int32ul, GbxNodeRef),
    # "rest" / GreedyBytes,
)

# 090BA CPlugSkel

body_chunks[0x090BA000] = Struct(
    "version" / ExprValidator(Int32ul, obj_ >= 12),
    "name" / GbxLookbackString,
    "joints"
    / PrefixedArray(
        Int16sl,
        Struct(
            "name" / GbxLookbackString,
            "parentIndex" / Int16sl,
            "globalJointPos" / If(this._._.version < 15, GbxQuat),  # todo check
            "globalJointRot" / If(this._._.version < 15, GbxVec3),  # todo check
            StopIf(this._._.version < 1),
            "localLoc" / GbxIso4,  # rot + pos from parent?
        ),
    ),
    StopIf(this.version < 2),
    "hasU03" / GbxBool,
    "u03"
    / If(
        this.hasU03,
        Struct(
            "u01"
            / PrefixedArray(
                Int32ul,
                Struct(
                    "bone0" / Int16sl,
                    "bone1" / Int16sl,
                    "bone2" / Int16sl,
                ),
            ),
            "u02"
            / PrefixedArray(
                Int32ul,
                Struct(
                    "u01" / Int32sl,
                    "u02" / Int32sl,
                    "u03" / Int32sl,
                    "u04" / Int32sl,
                ),
            ),
            "u03" / PrefixedArray(Int32ul, Int32sl),
            "u05" / Int16sl,
            "u06" / Int16sl,
        ),
    ),
    StopIf(this.version < 6),
    "sockets"
    / PrefixedArray(
        Int32ul,
        Struct(
            "name" / GbxLookbackString,
            "u01" / Int16sl,
            "u02" / GbxIso4,
        ),
    ),
    StopIf(this.version < 9),
    "hasU04" / GbxBool,
    "u04"
    / If(
        this.hasU04,
        Struct(
            "u01" / PrefixedArray(Int32ul, GbxLookbackString),
            "u02_SPlugSkelGlobalTargetInfo" / PrefixedArray(Int32ul, Int32sl),
            "u03_SPlugSkelGlobalTargetInfo" / PrefixedArray(Int32ul, Int32sl),
            "u04" / PrefixedArray(Int32ul, GbxQuat),
        ),
    ),
    StopIf(this.version < 10),
    "u05_SPlugSkelGlobalTargetInfo" / If(this.version <= 15, PrefixedArray(Int32ul, Int32ul)),
    "u06" / If(this.version > 15, PrefixedArray(Int32ul, Int8ul)),
    "rotationOrder" / If(this.version > 13, PrefixedArray(Int32ul, GbxERotationOrder)),
    "u11" / If(this.version == 14, Int32sl),
    "cElem_0" / If(this.version == 14, Int32sl),  # = 0 ?
    "u10_func_rotation_order" / If(this.version >= 19, PrefixedArray(Int32ul, Int8ul)),  # enum?
    StopIf(this.version < 17),
    "cLod" / Int8ul,
    "u08" / PrefixedArray(Int32ul, GbxFloat),
)

# 090BB CPlugSolid2Model

body_chunks[0x090BB000] = Struct(
    "version" / Int32ul,
    "u01" / GbxLookbackString,
    "shaded_geoms"
    / PrefixedArray(
        Int32ul,
        Struct(
            "visual_index" / Int32sl,
            "material_index" / Int32sl,
            "u01" / Int32sl,  # unused, -1
            StopIf(this._._.version < 1),
            "lod" / Int32sl,
            StopIf(this._._.version < 32),
            "u02" / Int32sl,
        ),
    ),
    "list_version_01" / If(this.version >= 6, ExprValidator(Int32ul, obj_ == 10)),
    "visuals" / If(this.version >= 6, PrefixedArray(Int32ul, GbxNodeRef)),
    "materials_names" / PrefixedArray(Int32ul, GbxLookbackString),
    "material_count" / IfThenElse(this.version >= 29, Int32ul, Computed(lambda this: 0)),
    "list_version_02" / If(this.material_count == 0, ExprValidator(Int32ul, obj_ == 10)),
    "materials" / If(this.material_count == 0, PrefixedArray(Int32ul, GbxNodeRef)),
    "skel" / GbxNodeRef,
    StopIf(this.version < 1),
    "lodDistances" / PrefixedArray(Int32ul, Float32l),  # lod distance?
    StopIf(this.version < 2),
    "VisCstType" / GbxEPlugSolidVisCstType,
    StopIf(this.version < 3),
    "hasPreLightGen" / GbxBool,
    "PreLightGen"
    / If(
        this.hasPreLightGen,
        Struct(
            "version" / Int32ul,  # 1
            "u01" / Int32sl,
            "lightmapSize" / Float32l,  # lightmap size in meters
            "u03" / GbxBool,
            "u04" / Float32l[4],
            "u05_u10" / Int32sl[6],
            "u14" / PrefixedArray(Int32ul, GbxBox),
            "uv_groups" / PrefixedArray(Int32ul, Float32l[5]),  # TODO
        ),
    ),
    StopIf(this.version < 4),
    "updatedTime" / GbxFileTime,
    StopIf(this.version < 5),
    "ImportString" / GbxString,
    StopIf(this.version < 7),
    "materialFolderName" / GbxString,
    "u09" / If(this.version >= 19, GbxString),
    StopIf(this.version < 8),
    "lights"
    / PrefixedArray(
        Int32ul,
        Struct(
            "name" / GbxLookbackString,
            "u02" / GbxBool,
            "u03" / If(this.u02, GbxNodeRef),  # CPlugLight
            "u04" / If(lambda this: not this.u02, GbxString),
            "u05" / GbxIso4,
            "u06" / Bytes(12),  # 6*4bytes
            "u12" / If(this._._.version >= 26, Bytes(12)),  # 3*4bytes, [1] and [2] = 0 if version < 26
            "u15" / GbxBool,
            "u16" / If(this.u15, Bytes(12)),  # 3*4bytes
        ),
    ),
    "material_insts_lt_v16" / If(this.version < 16, PrefixedArray(Int32ul, GbxNodeRef)),
    StopIf(this.version < 10),
    "lightUserModels" / PrefixedArray(Int32ul, GbxNodeRef),
    "light_insts" / PrefixedArray(Int32ul, Struct("model_index" / Int32ul, "socket_index" / Int32ul)),
    StopIf(this.version < 11),
    "damage_zone" / Int32sl,
    StopIf(this.version < 12),
    "flags" / Int32ul,
    # if version < 28, flags are adjusted, TODO?
    # flags &= 0xfffffbff
    StopIf(this.version < 13),
    "u12" / Int32sl,
    StopIf(this.version < 14),
    "creation_cmd" / GbxString,
    StopIf(this.version < 15),
    "material_count_lt_v29" / If(this.version < 29, Int32ul),
    "u14" / If(this.version >= 30, Int32sl),  # material_count?
    "custom_materials"
    / Array(
        lambda this: this.material_count if this.version >= 29 else this.material_count_lt_v29,
        GbxMaterial,
    ),
    StopIf(this.version < 17),
    "u15_bonesBoxes" / If(this.version < 21, PrefixedArray(Int32ul, GbxBox)),
    StopIf(this.version < 20),
    "bonesNames" / PrefixedArray(Int32ul, GbxLookbackString),
    StopIf(this.version < 22),
    "u17" / PrefixedArray(Int32ul, Int32sl),
    StopIf(this.version < 23),
    "u18" / ExprValidator(PrefixedArray(Int32ul, Pass), lambda obj, ctx: len(obj) == 0),  # TODO
    "u19" / PrefixedArray(Int32ul, Int32sl),
    StopIf(this.version < 24),
    "u20" / Bytes(4),
    StopIf(this.version < 25),
    "icon" / GbxNodeRef,  # CPlugFileImg
    "u22" / GbxVec2,
    StopIf(this.version < 27),
    "u24" / GbxLookbackString,
    StopIf(this.version < 31),
    "u25" / PrefixedArray(Int32ul, Bytes(8)),
    StopIf(this.version < 33),
    "cst_0" / If(this.version == 33, ExprValidator(Int32ul, obj_ == 0)),
    "u26" / PrefixedArray(Int32ul, Int32sl[5]),
)
# body_chunks[0x090BB002] = Struct(
#     "img" / Prefixed(Int32ul, GreedyBytes),
#     "u01" / Bytes(60),
# )

# 090F4 CPlugGameSkin
body_chunks[0x090F4003] = Struct("u01" / GbxString, "u02" / GbxString)
body_chunks[0x090F4005] = Struct(
    "version" / Int8ul,
    "relativeSkinDirectory" / GbxString,
    "u02" / GbxString,
    "u03" / GbxString,
    "fids"
    / PrefixedArray(
        Int8ul,
        Struct(
            "classId" / GbxChunkId,
            "type" / GbxString,
            "filePath" / GbxString,
            "u01" / Int32sl,
        ),
    ),
    "u04" / Bytes(16),
    # StopIf(this.version < 5),
    # "u04" / GbxString,
    # StopIf(this.version < 6),
    # "u05" / Bytes(4),
    # StopIf(this.version < 7),
    # "u06" / Bytes(4),
)

# 090FD CPlugMaterialUserInst
body_chunks[0x090FD000] = Struct(
    "version" / Int32ul,  # 11
    "isUsingGameMaterial" / If(this.version >= 11, GbxBoolByte),
    "materialName" / GbxLookbackString,
    "model" / GbxLookbackString,
    "baseTexture" / GbxString,  # baseMaterial?
    "surfacePhysicId" / GbxEPlugSurfacePhysicsId,
    "surfaceGameplayId" / If(this.version >= 10, GbxEPlugSurfaceGameplayId),
    StopIf(this.version < 1),
    "link"
    / IfThenElse(
        lambda this: (9 <= this.version < 11) or this.isUsingGameMaterial,
        GbxString,  # LinkFull
        GbxLookbackString,  # Link
    ),
    StopIf(this.version < 2),
    "csts"
    / PrefixedArray(
        Int32ul,
        Struct(
            "u01" / GbxLookbackString,
            "u02" / GbxLookbackString,
            "u03" / Int32sl,
        ),
    ),
    "color" / PrefixedArray(Int32ul, Int32sl),  # GbxVec2?
    StopIf(this.version < 3),
    "uvAnim"
    / PrefixedArray(
        Int32ul,
        Struct(
            "u01" / GbxLookbackString,
            "u02" / GbxLookbackString,
            "u03" / Float32l,
            "u04" / Int64ul,
            "u05" / If(this._._.version >= 5, GbxLookbackString),
        ),
    ),
    StopIf(this.version < 4),
    "u07" / PrefixedArray(Int32ul, GbxLookbackString),
    StopIf(this.version < 6),
    "userTextures"
    / PrefixedArray(
        Int32ul,
        Struct(
            "u01" / Int32sl,  # enum
            "textureName" / GbxString,  # LinkFull?
        ),
    ),
    StopIf(this.version < 7),
    "hidingGroup" / GbxLookbackString,
)
body_chunks[0x090FD001] = Struct(
    "version" / ExprValidator(Int32ul, obj_ >= 3),
    "u01" / GbxNodeRef,
    "tiling_u" / GbxETexAddress,
    "tiling_v" / GbxETexAddress,
    "texture_size" / Float32l,
    StopIf(this.version < 4),
    "u02" / Int32sl,
    StopIf(this.version < 5),
    "is_natural" / GbxBool,
)
body_chunks[0x090FD002] = Struct(
    "version" / Int32ul,
    "u01" / Int32sl,
)

# 09128 CPlugRoadChunk
body_chunks[0x09128000] = Struct(
    "version" / Int32ul,
    "u01" / Bytes(12),
    "u02" / PrefixedArray(Int32ul, GbxBox),
    "u03" / GbxVec3,
    "u04" / Bytes(15),
    "u05" / GbxLookbackString,
    "u06" / Bytes(13),
    "u07" / GbxVec3,
)

# 2E001 CGameCtnCollector
body_chunks[0x2E001009] = Struct(
    "page_path" / GbxString,
    "has_icon_fed" / GbxBool,
    "icon_fed" / If(this.has_icon_fed, GbxNodeRef),
    "u01" / GbxLookbackString,
)
body_chunks[0x2E00100B] = Struct("author" / GbxMeta)
body_chunks[0x2E00100C] = Struct("name" / GbxString)
body_chunks[0x2E00100D] = Struct("description" / GbxString)
body_chunks[0x2E00100E] = Struct(
    "icon_use_auto_render" / GbxBool,
    "icon_quarter_rotation_y" / Int32sl,
)
body_chunks[0x2E001010] = Struct(
    "version" / Int32ul,
    "u01" / GbxNodeRef,
    "skin_directory" / GbxString,
    "u02" / If(lambda this: this.version >= 2 and len(this.skin_directory) == 0, GbxNodeRef),
)
body_chunks[0x2E001011] = Struct(
    "version" / Int32ul,
    "is_internal" / GbxBool,
    "is_advanced" / GbxBool,
    "catalogPosition" / Int32sl,
    "prod_state" / If(this.version >= 1, GbxEProdState),
)
body_chunks[0x2E001012] = Struct(
    "version" / Int32ul,  # 0
    "u01" / Int32sl,  # 0x8c
    "u02" / Int32sl,  # 0x12
    "u03" / Int32sl,  # 0x94
)

# 2E002 CGameItemModel
body_chunks[0x2E002008] = Struct("nadeo_skin_fids" / PrefixedArray(Int32ul, GbxNodeRef)) * "Nadeo skin fids"
body_chunks[0x2E002009] = Struct("version" / Int32ul, "cameras" / PrefixedArray(Int32ul, GbxNodeRef) * "Cameras")
body_chunks[0x2E00200C] = Struct("race_interface_fid" / GbxNodeRef) * "Race Interface Id"
body_chunks[0x2E002012] = Struct(
    "ground_point" / GbxVec3,
    "painter_ground_margin" / GbxFloat,
    "orbitalCenterHeightFromGround" / GbxFloat,
    "orbitalRadiusBase" / GbxFloat,
    "orbitalPreviewAngle" / GbxFloat,
)
body_chunks[0x2E002015] = Struct("itemType" / GbxEItemType)
body_chunks[0x2E002019] = Struct(
    "version" / Int32ul,
    # "phy_model_custom" # TODO
    # "vis_model_custom" # TODO
    StopIf(this.version < 3),
    "default_weapon_name" / GbxLookbackString,
    StopIf(this.version < 4),
    "PhyModelCustom" / GbxNodeRef,
    StopIf(this.version < 5),
    "VisModelCustom" / GbxNodeRef,
    StopIf(this.version < 6),
    "u01" / Int32ul,  # actions?
    StopIf(this.version < 7),
    "default_cam" / GbxEDefaultCam,
    StopIf(this.version < 8),
    "EntityModelEdition" / GbxNodeRef,
    "EntityModel" / GbxNodeRef,
    StopIf(this.version < 13),
    "vfxFile" / GbxNodeRef,
    StopIf(this.version < 15),
    "MaterialModifier" / If(this.EntityModel >= 0, GbxNodeRef),
)
body_chunks[0x2E00201A] = Struct("u01" / GbxNodeRef)
body_chunks[0x2E00201C] = Struct(
    "version" / ExprValidator(Int32ul, obj_ == 5),
    "default_placement" / GbxNodeRef,
    # "u01" / Int32sl[5], ???
)
body_chunks[0x2E00201E] = Struct(
    "version" / ExprValidator(Int32ul, obj_ >= 3),
    "archetype_ref" / GbxString,
    "u01" / If(lambda this: len(this.archetype_ref) == 0, Int32sl),
    StopIf(this.version < 5),
    "u02" / GbxString,
    StopIf(this.version < 6),
    "baseItem" / GbxNodeRef,
)
body_chunks[0x2E00201F] = Struct(
    "version" / ExprValidator(Int32ul, obj_ >= 10),
    "waypointType" / GbxEWayPointType,
    "disableLightmap" / GbxBool,
    "u01" / Int32sl,
    StopIf(this.version < 11),
    "u08" / Byte,
    StopIf(this.version < 12),
    "PodiumClipList" / GbxNodeRef,  # Podium only?
    "IntroClipList" / GbxNodeRef,
)
body_chunks[0x2E002020] = Struct(
    "version" / ExprValidator(Int32ul, obj_ >= 3),
    "iconFid" / GbxString,
    "u01" / Byte,
)

# 2E009 CGameWaypointSpecialProperty
body_chunks[0x2E009000] = Struct(
    "version" / Int32ul,  # 2
    "tag" / GbxString,
    "order" / Int32sl,
)

# 2E020 CGameItemPlacementParam

body_chunks[0x2E020000] = Struct(
    "version" / Int32ul,
    "flags" / Int16ul,
    "cubeCenter" / GbxVec3,
    "cubeSize" / Float32l,
    "gridSnap_HStep" / Float32l,
    "gridSnap_VStep" / Float32l,
    "gridSnap_HOffset" / Float32l,
    "gridSnap_VOffset" / Float32l,
    "flyStep" / Float32l,
    "flyOffset" / Float32l,
    "pivotSnapDistance" / Float32l,
)
body_chunks[0x2E020001] = Struct(
    "pivotPositions" / PrefixedArray(Int32ul, GbxVec3),
    "pivotRotations" / PrefixedArray(Int32ul, GbxQuat),
)


def check_0(obj, ctx):
    if obj != b"\x00\x00\x00\x00":
        print(f"body_chunks[0x2E020004] first array not empty {obj}")
    return obj


body_chunks[0x2E020004] = Struct(
    "u01" / Bytes(4) * check_0,  # 0
    "magnetLocs" / PrefixedArray(Int32ul, GbxPose3D),
)
body_chunks[0x2E020005] = Struct("item_placement" / GbxNodeRef)

# 2E025 CGameBlockItem

body_chunks[0x2E025000] = Struct(
    "version" / Int32ul,
    "ArchetypeBlockInfoId" / GbxLookbackString,
    "ArchetypeBlockInfoCollectionId" / GbxLookbackString,
    "CustomizedVariants" / GbxDict(Int32ul, GbxNodeRef),
    "u01" / GbxBoolByte,
)
body_chunks[0x2E025003] = Struct(
    "version" / Int32ul,  # 0
    "u01" / Array(lambda this: len(this._._._._array[0].chunk.CustomizedVariants), GbxBoolByte),
)


# 2E026 CGameCommonItemEntityModelEdition

body_chunks[0x2E026000] = Struct(
    "version" / Int32ul,
    "itemType" / ExprValidator(GbxEItemType, obj_ == "Ornament"),
    "meshCrystal" / GbxNodeRef,
    "u01" / GbxString,
    "u02" / GbxNodeRef,  # if U01 is empty probably
    "u03" / ExprValidator(Int32ul, obj_ == 0),  # CPlugFileImg array
    "u04" / ExprValidator(Int32ul, obj_ == 0),  # SSpriteParam array
    "u05" / GbxNodeRef,
    "u06" / GbxNodeRef,
    "u07" / ExprValidator(Int32ul, obj_ == 0),  # SPlugLightBallStateSimple array
    "u08_u14" / GbxString[7],
    "u15" / GbxIso4,
    "u16" / GbxBool,
    "u21" / If(lambda this: not this.u16, GbxNodeRef),
    "u17" / GbxBool,
    "u18" / If(lambda this: this.u17, Int32sl),
    "u19" / If(lambda this: this.u17, GbxIso4),
    "u20" / Int32sl,
    StopIf(this.version < 1),
    "inventoryName" / GbxString,
    "inventoryDescription" / GbxString,
    "inventoryItemClass" / Int32sl,
    "inventoryOccupation" / Int32sl,
    StopIf(this.version < 6),
    "u22" / GbxNodeRef,
)

# 2E027 CGameCommonItemEntityModel
body_chunks[0x2E027000] = Struct(
    "version" / ExprValidator(Int32ul, obj_ >= 4),
    "staticObject" / GbxNodeRef,
    StopIf(this.version < 2),
    "props"
    / Struct(
        "triggerArea" / GbxNodeRef,  # CPlugSurface
        "spawnLoc" / GbxIso4,
        "emitterModel" / GbxNodeRef,  # CPlugParticleEmitterModel
        "actionModels" / PrefixedArray(Int32ul, GbxNodeRef),  # CGameCtnPlaygroundActionModel
        "u03" / GbxNodeRef,  # unused?
        "u04" / Array(5, GbxString),
        "u05" / GbxIso4,
        "u06" / Int32sl,
    ),
    StopIf(this.version < 5),
    "u07" / GbxBoolByte,
)

# NPlugDyna_SConstraintModel 2F074000
body_chunks[0x2F074000] = Struct(
    "version" / Int32sl,
    "Type" / Int32sl,
    "Spring_Length" / GbxFloat,
    "Spring_DampingRatio" / GbxFloat,
    "Spring_FreqHz" / GbxFloat,
)

# 2F086 VegetTreeModel
body_chunks[0x2F086000] = Struct(
    "u01" / Bytes(4 * 4),  # version + lod 4 2 1?, number of things?
    "u02"  # parts?
    / PrefixedArray(
        Int32ul,
        Struct(
            "texture_d" / GbxNodeRef,
            "texture_n" / GbxNodeRef,
            "texture_r" / GbxNodeRef,
            "image_d" / GbxNodeRef,
            "image_n" / GbxNodeRef,
            "image_r" / GbxNodeRef,
            "u01" / GbxNodeRef[3],
            "u02" / GbxBoolByte,
        ),
    ),
    "u03" / PrefixedArray(Int32ul, GbxLookbackString),
    "u04" / Bytes(6),
    # "mesh1" / GbxNodeRef,
    # "u05" / Bytes(3),
    # "mesh2" / GbxNodeRef,
    # "u06" / Bytes(3),
    # "mesh3" / GbxNodeRef,
    # "u07" / Bytes(7),
    # "mesh4" / GbxNodeRef,
    # "u08" / Bytes(3),
    # "mesh5" / GbxNodeRef,
    # "u09" / Bytes(3),
    # "mesh6" / GbxNodeRef,
    "rest" / GreedyBytes,
)

# 2F0BC NPlugItem_SVariantList
body_chunks[0x2F0BC000] = Struct(
    "version" / Int32ul,
    "variants"
    / PrefixedArray(
        Int32ul,
        Struct(
            "Tags" / GbxDictString,
            "EntityModel" / GbxNodeRef,
            "HiddenInManualCycle" / GbxBool,
        ),
    ),
)

# 2F0CA KinematicConstraint
GbxSubAnimFunc = Struct(
    "ease" / GbxEAnimEase,
    "reverse" / GbxBoolByte,
    "duration" / Int32ul,
)
GbxAnimFunc = Struct(
    "TimeIsDuration" / GbxBool,
    "SubFuncs" / PrefixedArray(Int32ul, GbxSubAnimFunc),
)
body_chunks[0x2F0CA000] = Struct(
    "version" / Int32sl,
    "subVersion" / Int32sl,
    "TransAnimFunc" / GbxAnimFunc,
    "RotAnimFunc" / GbxAnimFunc,
    "ShaderTcType" / GbxEShaderTcType,
    "ShaderTcVersion" / Int32sl,
    "ShaderTcAnimFunc"
    / PrefixedArray(
        Int32ul,
        Struct(
            "Duration" / Int32ul,
            "TextureId" / Int32sl,
        ),
    ),
    "ShaderTcData_TransSub"
    / If(
        this.ShaderTcType == 1,
        Struct(
            "NbSubTexture" / Int32ul,
            "NbSubTexturePerLine" / Int32ul,
            "NbSubTexturePerColumn" / Int32ul,
            "TopToBottom" / GbxBool,
        ),
    ),
    "TransAxis" / GbxEAxis,
    "TransMin" / GbxFloat,
    "TransMax" / GbxFloat,
    "RotAxis" / GbxEAxis,
    "AngleMinDeg" / GbxFloat,
    "AngleMaxDeg" / GbxFloat,
)

body_chunks.update(
    {
        # 090C
        0x090B5000: Bytes(160),
        0x090C5000: Bytes(84),
        0x090C6000: Bytes(284),
    }
)

# Headers chunks

header_chunks = {}

header_chunks[0x2E002000] = Struct("itemType" / GbxEItemType)

header_chunks[0x2E001003] = Struct(
    "meta" / GbxMeta,
    "version" / ExprValidator(Int32sl, obj_ >= 7),
    "page_name" / GbxString,
    StopIf(this.version < 3),
    "u01" / GbxLookbackString,
    "flags" / Hex(Int32sl),
    "catalog_position" / Int16sl,
    "file_name" / GbxString,
    StopIf(this.version < 8),
    "prod_state" / Enum(Byte, Aborted=0, GameBox=1, DevBuild=2, Release=3),
)

header_chunks[0x2E001004] = Struct(
    "width_and_webp" / Rebuild(Int16ul, lambda this: this.width + (0x8000 if this.webp else 0x0000)),
    "width" / Computed(this.width_and_webp & 0x7FFF),
    "height_and_webp" / Rebuild(Int16ul, lambda this: this.height + (0x8000 if this.webp else 0x0000)),
    "height" / Computed(this.height_and_webp & 0x7FFF),
    "webp" / Computed(lambda this: (this.width_and_webp & 0x8000) == (this.height_and_webp & 0x8000) == 0x8000),
    "data"
    / IfThenElse(
        this.webp,
        Struct("version" / Int16ul, "image" / Prefixed(Int32ul, GreedyBytes)),
        Array(
            lambda this: this.width * this.height,
            GbxColor,
        ),
    ),
)

header_chunks[0x090F4005] = body_chunks[0x090F4005]


def set_nodes_array(obj, ctx):
    ctx._root._params.nodes += [None] * obj
    return obj


def get_nodes_array(obj, ctx):
    return len(ctx._root._params.nodes)


def load_external_nodes(obj, ctx):
    ctx._root._params.nodes[obj.node_index] = obj.ref

    return obj


def reset_lookbackstring(obj, ctx):
    ctx._root._params.gbx_data.pop("lookbackstring", None)
    return obj


def create_gbx_struct(gbx_body):
    return Struct(
        "header"
        / Struct(
            Const(b"GBX"),
            "version" / ExprValidator(Int16ul, obj_ == 6),
            Const(b"BU"),
            "body_compression" / Enum(Byte, compressed=ord("C"), uncompressed=ord("U")),
            "u01_R_or_E" / Bytes(1),
            "class_id" / GbxChunkId,
            "chunks"
            / Select(
                Struct("size" / ExprValidator(Int32ul, obj_ == 0)),
                Struct(
                    "corrupted_size" / ExprAdapter(Int32ul, lambda obj, ctx: obj, lambda obj, ctx: 0),
                    "nb_nodes"
                    / ExprValidator(
                        Peek(Int32ul[2]),
                        lambda obj, ctx: obj[0] < 1000 and obj[1] < 1000,
                    ),
                ),  # fix corrupted chunk size
                Prefixed(
                    Int32ul,
                    Struct(
                        "entries"
                        / PrefixedArray(
                            Int32ul,
                            Struct(
                                "id" / GbxChunkId,
                                "meta"
                                / ByteSwapped(
                                    BitStruct(
                                        "heavy" / Flag,
                                        "size"
                                        / Rebuild(
                                            BitsInteger(31),
                                            lambda this: len(
                                                header_chunks[this._.id].build(
                                                    this._._._.data[this._index],
                                                    gbx_data={},
                                                )
                                            )
                                            if this._.id in header_chunks
                                            else this.size,
                                        ),
                                    )
                                ),
                            ),
                        ),
                        "data"
                        / Array(
                            lambda this: len(this.entries),
                            ExprAdapter(
                                Select(
                                    Switch(
                                        lambda this: this.entries[this._index].id,
                                        header_chunks,
                                        default=Bytes(lambda this: this.entries[this._index].meta.size),
                                    ),
                                    Struct(
                                        "parse_header_chunk_failed"
                                        / Bytes(lambda this: this._.entries[this._index].meta.size)
                                    ),
                                ),
                                reset_lookbackstring,
                                reset_lookbackstring,
                            ),
                        ),
                    ),
                ),
            ),
            "num_nodes" / ExprAdapter(Int32ul, set_nodes_array, get_nodes_array),
        ),
        "reference_table"
        / Struct(
            "num_external_nodes" / Int32ul,
            "external_folders"
            / If(
                this.num_external_nodes > 0,
                Struct(
                    "ancestor_level" / Int32ul,
                    "folders" / PrefixedArray(Int32ul, GbxFolders),
                ),
            ),
            "external_nodes"
            / Array(
                this.num_external_nodes,
                ExprAdapter(
                    Struct(
                        "flags"
                        / BitStruct(
                            "u01" / Hex(BytesInteger(29)),
                            "is_ref_resource_index" / Flag,
                            "u02" / Hex(BytesInteger(2)),
                        ),
                        "ref"
                        / IfThenElse(
                            this.flags.is_ref_resource_index,
                            "resource_index" / Int32ul,
                            "filename" / GbxString,
                        ),
                        "node_index" / Int32ul,
                        "use_file" / GbxBool,
                        "folder_index" / If(lambda this: not this.flags.is_ref_resource_index, Int32ul),
                    ),
                    load_external_nodes,
                    lambda obj, _: obj,
                ),
            ),
        ),
        "body"
        / IfThenElse(
            this.header.body_compression == "compressed",
            CompressedLZ0(gbx_body),
            gbx_body,
        ),
        "rest" / GreedyBytes,
    )


GbxStruct = create_gbx_struct(GbxBody)
GbxStructWithoutBodyParsed = create_gbx_struct(GreedyBytes)
