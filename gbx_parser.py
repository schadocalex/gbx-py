from functools import partial
import datetime

import lzo

from construct import (
    Struct,
    Const,
    Check,
    Padding,
    Byte,
    Bytes,
    Sequence,
    GreedyBytes,
    Int16sl,
    Int16ul,
    Int32ul,
    Int32sl,
    Int64ul,
    Float32l,
    ExprValidator,
    Adapter,
    ExprAdapter,
    Enum,
    Hex,
    If,
    Array,
    this,
    obj_,
    len_,
    Probe,
    Rebuild,
    FixedSized,
    Bitwise,
    BitsInteger,
    Flag,
    Container,
    Computed,
    Prefixed,
    PrefixedArray,
    Switch,
    If,
    IfThenElse,
    PascalString,
    LazyBound,
    BitStruct,
    BytesInteger,
    CompressedLZ4,
    GreedyRange,
    StopIf,
    Select,
    Pass,
    Optional,
    Tunnel,
    Seek,
    Peek,
    RepeatUntil,
)
from gbx_enums import (
    GbxEProdState,
    GbxEItemType,
    GbxEDefaultCam,
    GbxELayerType,
    GbxEWaypointType,
    GbxETexAddress,
    GbxESurfType,
    GbxEPlugSurfacePhysicsId,
    GbxEPlugSurfaceGameplayId,
    GbxEFillDir,
    GbxEFillAlign,
)

GbxCompressedBody = Struct(
    "uncompressed_size" / Int32ul, "compressed_body" / Prefixed(Int32ul, GreedyBytes)
)


class CompressedLZ0(Tunnel):
    def _decode(self, raw_bytes, context, path):
        data = GbxCompressedBody.parse(raw_bytes)
        return lzo.decompress(data.compressed_body, False, data.uncompressed_size)

    def _encode(self, raw_bytes, context, path):
        return GbxCompressedBody.build(
            Container(
                uncompressed_size=len(raw_bytes),
                compressed_body=lzo.compress(raw_bytes, 1, False),
            )
        )


GbxChunkId = Hex(Int32ul)

GbxString = PascalString(Int32ul, "utf-8")

GbxBool = ExprAdapter(
    Int32ul,
    decoder=lambda obj, ctx: obj == 0x01,
    encoder=lambda obj, ctx: 0x01 if obj else 0x00,
)
GbxBoolByte = ExprAdapter(
    Byte,
    decoder=lambda obj, ctx: obj == 0x01,
    encoder=lambda obj, ctx: 0x01 if obj else 0x00,
)

GbxFloat = Float32l

GbxVec2 = Struct("x" / GbxFloat, "y" / GbxFloat)
GbxVec3 = Struct("x" / GbxFloat, "y" / GbxFloat, "z" / GbxFloat)
GbxInt3 = Struct("x" / Int32sl, "y" / Int32sl, "z" / Int32sl)
GbxBox = Struct(
    "x1" / GbxFloat,
    "y1" / GbxFloat,
    "z1" / GbxFloat,
    "x2" / GbxFloat,
    "y2" / GbxFloat,
    "z2" / GbxFloat,
)
GbxColor = Struct("r" / Byte, "g" / Byte, "b" / Byte, "a" / Byte)
GbxPlugSurfaceMaterialId = Struct(
    "physics_id" / GbxEPlugSurfacePhysicsId, "gameplay_id" / GbxEPlugSurfaceGameplayId
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


class AGbxVec3_10b(Adapter):
    def _decode(self, obj, ctx, path):
        return Container(
            x=tenb_to_float(obj & 0x3FF),
            y=tenb_to_float((obj >> 10) & 0x3FF),
            z=tenb_to_float((obj >> 20) & 0x3FF),
        )

    def _encode(self, obj, ctx, path):
        return (
            float_to_tenb(obj.x)
            + (float_to_tenb(obj.y) << 10)
            + (float_to_tenb(obj.z) << 20)
        )


GbxVec3Tenb = AGbxVec3_10b(Int32ul)

GbxDict = PrefixedArray(Int32ul, Struct("key" / GbxString, "value" / GbxString))

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


class GbxFileTime(Adapter):
    EPOCH_START = datetime.datetime(1601, 1, 1)

    def _decode(self, file_time, context, path):
        delta = datetime.timedelta(microseconds=file_time / 10)
        date_time = self.EPOCH_START + delta
        return date_time

    def _encode(self, date_time, context, path):
        time_delta = date_time - self.EPOCH_START
        return int(time_delta / datetime.timedelta(microseconds=1)) * 10


GbxCollectionIds = {
    0: "Desert Speed",
    1: "Snow Alpine",
    3: "Island",
    4: "Bay",
    7: "Basic",
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
            raise AttributeError(f"Unknown collection id: {idx}")
        return GbxCollectionIds[idx]
    elif idx == 0:
        ctx._root._params.gbx_data["lookbackstring"].append(obj.string)
        return obj.string
    else:
        return ctx._root._params.gbx_data["lookbackstring"][idx - 1]


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

GbxMeta = Struct(
    "id" / GbxLookbackString,
    "collection" / GbxLookbackString,
    "author" / GbxLookbackString,
)

BodyChunkId_to_struct = {}

GbxNodesWithoutBody = set([0x09159000, 0x2F0BC000, 0x09187000])

GbxBodyChunks = RepeatUntil(
    lambda obj, lst, ctx: obj is None or obj.chunk_id == 0xFACADE01,
    Select(
        Struct(
            "chunk_id" / GbxChunkId,
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
                            BodyChunkId_to_struct,
                            default=GreedyBytes,
                        ),
                    ),
                ),
                Switch(
                    this.chunk_id,
                    BodyChunkId_to_struct,
                    default=Struct("unknown_chunk" / GreedyBytes),
                ),
                Struct("chunk_parse_failed" / GreedyBytes),
            ),
        ),
        Pass,
    ),
)  # TODO create new context for GbxBody? I think no

GbxBody = IfThenElse(
    lambda this: this.header.class_id in GbxNodesWithoutBody,
    Switch(
        lambda this: this.header.class_id,
        BodyChunkId_to_struct,
        default=Struct("unknown_chunk_in_node_ref" / GreedyBytes),
    ),
    GbxBodyChunks,
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
        raise Exception(f"Unknwon node ref index: {this.index}")


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

        print(
            f"node ref {obj} + {get_noderef_offset(ctx)} => {obj + get_noderef_offset(ctx)}"
        )
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
                #         BodyChunkId_to_struct,
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

# 09003 CPlugCrystal
Chunk_09003003 = Struct(
    "version" / Int32ul,
    "materials" / PrefixedArray(Int32ul, GbxMaterial),
)
Chunk_09003005 = Struct(
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
                    GbxELayerType.Geometry: GreedyBytes,
                    GbxELayerType.Trigger: GreedyBytes,
                    GbxELayerType.Cubes: GreedyBytes,
                },
                GreedyBytes,
            ),
        ),
    ),
)

# 09006 CPlugVisual
Chunk_09006001 = Struct("u01" / GbxNodeRef)
Chunk_09006005 = Struct("sub_visuals" / PrefixedArray(Int32ul, GbxInt3))
Chunk_09006009 = Struct("has_vertex_normals " / GbxBool)
Chunk_0900600B = Struct(
    "splits "
    / PrefixedArray(Int32ul, Struct("u01" / Int32sl, "u02" / Int32sl, "u03" / GbxBox))
)
Chunk_0900600D = Struct(
    "flags" / Int32ul,
    "num_tex_coord_sets" / ExprValidator(Int32ul, obj_ == 0),
    "count" / Int32ul,
    "vertex_streams" / PrefixedArray(Int32ul, GbxNodeRef),
    "u01" / GbxBox,
)
Chunk_0900600E = Struct(
    *Chunk_0900600D.subcons,
    "bitmap_elem_to_packs" / PrefixedArray(Int32ul, Struct("u01" / Int32sl[5])),
)
Chunk_0900600F = Struct(
    "version" / Int32ul,
    *Chunk_0900600E.subcons,
    StopIf(this.version < 5),
    "u02" / PrefixedArray(Int32ul, Int16sl),
    StopIf(this.version < 6),
    "u03" / Int32ul,
    "u04" / ExprValidator(Int32ul, obj_ == 0),
)
Chunk_09006010 = Struct(
    "version" / Int32ul, "morph_count" / ExprValidator(Int32ul, obj_ == 0)
)

# 0900C CPlugSurface

GbxSurfMesh = Struct(
    "version" / ExprValidator(Int32ul, obj_ == 7),
    "vertices" / PrefixedArray(Int32ul, GbxVec3),
    "triangles" / PrefixedArray(Int32ul, Sequence(GbxInt3, Int32sl)),
)
Chunk_0900C003 = Struct(
    "version" / Int32ul,
    "surf_version" / If(this.version >= 2, Int32ul),
    "surf"
    / Struct(
        "type" / GbxESurfType,
        "data" / Switch(this.type, {GbxESurfType.Mesh: GbxSurfMesh}),
        "u01" / If(this._.surf_version >= 2, GbxVec3),
    ),
    "materials"
    / PrefixedArray(
        Int32ul,
        Struct(
            "has_material" / Rebuild(GbxBool, lambda this: this.material is not None),
            "material" / If(this.has_material, GbxNodeRef),
        ),
    ),
    "u01" / If(lambda this: len(this.materials) > 0, Int32sl),  # TODO check condition
    "materials_ids" / PrefixedArray(Int32ul, GbxPlugSurfaceMaterialId),
    "skel" / If(this.version >= 1, GbxNodeRef),
)

# 0902C CPlugVisual3D

Chunk_0902C002 = Struct("u01" / GbxNodeRef)
Chunk_0902C004 = Struct(
    "nb_tangents1" / ExprValidator(Int32ul, obj_ == 0),
    "nb_tangents2" / ExprValidator(Int32ul, obj_ == 0),
)

# 0903A CPlugMaterialCustom

Chunk_0903A004 = Struct("u01" / PrefixedArray(Int32ul, Int32sl))
Chunk_0903A00A = Struct(
    "gpu_fxs"
    / PrefixedArray(
        Int32ul,
        Struct(
            "u01" / GbxLookbackString,
            "count1" / Int32sl,
            "count2" / Int32sl,
            "u02" / GbxBool,
            "u03" / Float32l[this.count1][this.count2],
        ),
    )
)

# 09056 CPlugVertexStream

GbxEVertexStreamType = Enum(Byte, Vec3B=0x1C, Vec2=0x02, Color=0x08)
Chunk_09056000 = Struct(
    "version" / Int32ul,
    "num_vertices" / Int32sl,
    "u01" / Int32sl,
    "u02" / GbxNodeRef,
    StopIf(lambda this: this.num_vertices == 0 or this.u02 != -1),
    "header"
    / Struct(
        "nb" / Int32ul,
        "u01" / Bytes(4),
        "u02" / Hex(Int32sl),
        "entries"
        / Array(
            this.nb - 1,
            Struct(
                "u01" / Byte,
                "type" / GbxEVertexStreamType,
                "u02" / Byte,
                "u03" / Hex(Byte),
                "u04" / Hex(Int32sl),
                "u05" / Hex(Int32sl),
            ),
        ),
    ),
    "u03" / GbxBool,
    "vertices_coords" / GbxVec3[this.num_vertices],
    "normals" / GbxVec3Tenb[this.num_vertices],
    "others"
    / Switch(
        lambda this: this.header.u01[2],
        {
            0x60: Struct(
                "uv0" / GbxVec2[this._.num_vertices],
            ),
            0x80: Struct(
                "uv0" / GbxVec2[this._.num_vertices],
                "t1" / GbxVec3Tenb[this._.num_vertices],
                "t2" / GbxVec3Tenb[this._.num_vertices],
            ),
            0x90: Struct(
                "color" / GbxColor[this._.num_vertices],
                "uv0" / GbxVec2[this._.num_vertices],
                "t1" / GbxVec3Tenb[this._.num_vertices],
                "t2" / GbxVec3Tenb[this._.num_vertices],
            ),
            0xA0: Struct(
                "uv0" / GbxVec2[this._.num_vertices],
                "uv1" / GbxVec2[this._.num_vertices],
                "t1" / GbxVec3Tenb[this._.num_vertices],
                "t2" / GbxVec3Tenb[this._.num_vertices],
            ),
            0xB0: Struct(
                "color" / GbxColor[this._.num_vertices],
                "uv0" / GbxVec2[this._.num_vertices],
                "uv1" / GbxVec2[this._.num_vertices],
                "t1" / GbxVec3Tenb[this._.num_vertices],
                "t2" / GbxVec3Tenb[this._.num_vertices],
            ),
        },
    ),
)

# 09057 CPlugIndexBuffer

Chunk_09057001 = Struct(
    "flags" / Int32ul,
    # "rest" / GreedyBytes,
    "indices" / PrefixedArray(Int32ul, Int16sl),
)

# 0906A CPlugVisualIndexed

Chunk_0906A001 = Struct(
    "has_index_buffer" / GbxBool,  # or array length ? or version ?
    "index_buffer" / If(this.has_index_buffer, GbxBodyChunks),
)

# 09079 CPlugMaterial
Chunk_09079001 = Struct(
    "u01" / GbxNodeRef,
)
Chunk_09079007 = Struct(
    "custom_material" / GbxNodeRef,
)

# 09159 CPlugStaticObjectModel
Chunk_09159000 = (
    Struct(
        "u01" / Int32sl,
        "mesh" / GbxNodeRef,
        "collidable" / GbxBoolByte,
        "collidable_ref"
        / If(
            lambda this: not this.collidable, GbxNodeRef
        ),  # HitShape, what is it? TODO
        StopIf(lambda this: not this.collidable and this.collidable_ref != -1),
        "trigger_area" / GbxNodeRef,  # CPlugSurface
        # "ustruct"
        # / If(
        #     True,
        # Struct(
        "u04" / GbxIso4,
        "u05" / Int32sl,  # -1
        "u06" / Int32sl,  # 0
        "u07" / Int32sl,  # -1
        "u08" / Int32sl,
        "u09" / Int32sl,
        "u10" / Int32sl,
        "u11" / Int32sl,
        "u12" / Int32sl,
        "u13" / GbxIso4,
        "u14" / Int32sl,
        #     ),
        # ),
    )
    * "Static Object Model"
)

# 09187 NPlugItemPlacement_SClass
Chunk_09187000 = Struct(
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

# 090BB CPlugSolid2Model
Chunk_090BB000 = (
    Struct(
        "version" / Int32ul,
        "u01" / GbxLookbackString,
        "shaded_geoms"
        / PrefixedArray(
            Int32ul,
            Struct(
                "visual_index" / Int32sl,
                "material_index" / Int32sl,
                "u01" / Int32sl,
                StopIf(this._._.version < 1),
                "lod" / Int32sl,
                StopIf(this._._.version < 32),
                "u02" / Int32sl,
            ),
        ),
        "list_version_01" / If(this.version >= 6, ExprValidator(Int32ul, obj_ == 10)),
        "visuals" / If(this.version >= 6, PrefixedArray(Int32ul, GbxNodeRef)),
        "materials_names" / PrefixedArray(Int32ul, GbxLookbackString),
        "material_count" / If(this.version >= 29, Int32ul),
        "list_version_02"
        / If(this.material_count == 0, ExprValidator(Int32ul, obj_ == 10)),
        "materials" / If(this.material_count == 0, PrefixedArray(Int32ul, GbxNodeRef)),
        "skel" / GbxNodeRef,
        StopIf(this.version < 1),
        "u04" / PrefixedArray(Int32ul, Float32l),  # lod distance?
        StopIf(this.version < 2),
        "vis_cst_type" / Int32sl,  # 1 - static
        StopIf(this.version < 3),
        "has_pre_light_gen" / GbxBool,  # or array length?
        "pre_ligh_gen"
        / If(
            this.has_pre_light_gen,
            Struct(
                "version" / Int32ul,
                "u01" / Int32sl,
                "u02" / Float32l,
                "u03" / Int32sl,
                "u04" / Float32l[4],
                "u05" / Int16sl[8],
                "u06" / Int32sl,
                "u07" / Int32sl,
                "u08" / PrefixedArray(Int32ul, GbxBox),
                "uv_groups" / PrefixedArray(Int32ul, Pass),  # TODO
            ),
        ),
        StopIf(this.version < 4),
        "file_time" / GbxFileTime(Int64ul),
        StopIf(this.version < 5),
        "u03" / GbxString,
        StopIf(this.version < 7),
        "material_folder_name" / GbxString,
        "u09" / If(this.version >= 19, GbxString),
        StopIf(this.version < 8),
        "lights" / PrefixedArray(Int32ul, Pass),  # TODO
        "material_insts_lt_v16"
        / If(this.version < 16, PrefixedArray(Int32ul, Pass)),  # TODO
        StopIf(this.version < 10),
        "light_user_models" / PrefixedArray(Int32ul, Pass),  # TODO
        "light_insts"
        / PrefixedArray(
            Int32ul, Struct("model_index" / Int32ul, "socket_index" / Int32ul)
        ),
        StopIf(this.version < 11),
        "damage_zone" / Int32sl,
        StopIf(this.version < 12),
        "flags" / Int32ul,
        # if version < 28, flags are adjusted, TODO?
        StopIf(this.version < 13),
        "u12" / Int32sl,
        StopIf(this.version < 14),
        "creation_cmd" / GbxString,
        StopIf(this.version < 15),
        "material_count_<v29" / If(this.version < 29, Int32ul),
        "u14" / If(this.version >= 30, Int32ul),  # material_count?
        "custom_materials"
        / Array(
            lambda this: this.material_count
            if this.version >= 29
            else this.material_count_lt_v29,
            GbxMaterial,
        ),
        StopIf(this.version < 17),
        "u15" / If(this.version < 21, PrefixedArray(Int32ul, GbxBox)),
        StopIf(this.version < 20),
        "u16" / PrefixedArray(Int32ul, GbxLookbackString),
        StopIf(this.version < 22),
        "u17" / PrefixedArray(Int32ul, Int32sl),
        StopIf(this.version < 23),
        "u18"
        / ExprValidator(
            PrefixedArray(Int32ul, Pass), lambda obj, ctx: len(obj) == 0
        ),  # TODO
        "u19" / PrefixedArray(Int32ul, Int32sl),
        StopIf(this.version < 24),
        "u20" / Int32sl,
        StopIf(this.version < 25),
        "u21" / GbxNodeRef,
        "u22" / GbxVec2,
        StopIf(this.version < 27),
        "u24" / GbxLookbackString,
        StopIf(this.version < 31),
        "u25"
        / ExprValidator(
            PrefixedArray(Int32ul, Pass), lambda obj, ctx: len(obj) == 0
        ),  # TODO
        StopIf(this.version < 33),
        "cst_0" / If(this.version == 33, ExprValidator(Int32ul, obj_ == 0)),
        "u26" / PrefixedArray(Int32ul, Int32sl[5]),
    )
    * "Solid2 Model"
)

# 090FD CPlugMaterialUserInst
Chunk_090FD000 = Struct(
    "version" / Int32ul,
    "is_using_game_material" / If(this.version >= 11, GbxBoolByte),
    "material_name" / GbxLookbackString,
    "model" / GbxLookbackString,
    "base_texture" / GbxString,
    "surface_physic_id" / GbxEPlugSurfacePhysicsId,
    "surface_gameplay_id" / If(this.version >= 10, GbxEPlugSurfaceGameplayId),
    StopIf(this.version < 1),
    "link"
    / IfThenElse(
        lambda this: (9 <= this.version < 11) or this.is_using_game_material,
        GbxString,
        GbxLookbackString,
    ),
    StopIf(this.version < 2),
    "csts"
    / PrefixedArray(
        Int32ul,
        Struct("u01" / GbxLookbackString, "u02" / GbxLookbackString, "u03" / Int32sl),
    ),
    "color" / PrefixedArray(Int32ul, Int32sl),
    StopIf(this.version < 3),
    "uv_anim"
    / PrefixedArray(
        Int32ul,
        Struct(
            "u01" / GbxLookbackString,
            "u02" / GbxLookbackString,
            "u03" / Bytes(4),
            "u04" / Int64ul,
            "u05" / If(this._._.version >= 5, GbxLookbackString),
        ),
    ),
    StopIf(this.version < 4),
    "u07" / PrefixedArray(Int32ul, GbxLookbackString),
    StopIf(this.version < 6),
    "user_textures"
    / PrefixedArray(Int32ul, Struct("u01" / Int32sl, "texture" / GbxString)),
    StopIf(this.version < 7),
    "hiding_group" / GbxLookbackString,
)
Chunk_090FD001 = Struct(
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
Chunk_090FD002 = Struct(
    "version" / Int32ul,
    "u01" / Int32sl,
)

# 2E001 CGameCtnCollector
Chunk_2E001009 = (
    Struct(
        "page_path" / GbxString,
        "has_icon_fed" / GbxBool,
        "icon_fed" / If(this.has_icon_fed, Pass),
        "u01" / GbxLookbackString,
    )
    * "Icon"
)
Chunk_2E00100B = Struct("meta" / GbxMeta) * "Author"
Chunk_2E00100C = Struct("string" / GbxString) * "Collector name"
Chunk_2E00100D = Struct("description" / GbxString) * "Description"
Chunk_2E00100E = (
    Struct("icon_use_auto_render" / GbxBool, "icon_quarter_rotation_y" / Int32sl)
    * "Icon render"
)
Chunk_2E001010 = Struct(
    "version" / Int32ul,
    "u01" / GbxNodeRef,
    "skin_directory" / GbxString,
    "u02"
    / If(lambda this: this.version >= 2 and len(this.skin_directory) == 0, GbxNodeRef),
)
Chunk_2E001011 = Struct(
    "version" / Int32ul,
    "is_internal" / GbxBool,
    "is_advanced" / GbxBool,
    "catalog_position" / Int32ul,
    "prod_state" / If(this.version >= 1, GbxEProdState),
)
Chunk_2E001012 = Struct("u01" / Int32ul[4])

# 2E002 CGameItemModel
Chunk_2E002008 = (
    Struct("nadeo_skin_fids" / PrefixedArray(Int32ul, GbxNodeRef)) * "Nadeo skin fids"
)
Chunk_2E002009 = Struct(
    "version" / Int32ul, "cameras" / PrefixedArray(Int32ul, GbxNodeRef) * "Cameras"
)
Chunk_2E00200C = Struct("race_interface_fid" / GbxNodeRef) * "Race Interface Id"
Chunk_2E002012 = Struct(
    "ground_point" / GbxVec3,
    "painter_ground_margin" / GbxFloat,
    "orbitalCenterHeightFromGround" / GbxFloat,
    "orbitalRadiusBase" / GbxFloat,
    "orbitalPreviewAngle" / GbxFloat,
)
Chunk_2E002015 = Struct("object_info_type" / GbxEItemType) * "Item type"
Chunk_2E002019 = (
    Struct(
        "version" / Int32ul,
        # "phy_model_custom" # TODO
        # "vis_model_custom" # TODO
        StopIf(this.version < 3),
        "default_weapon_name" / GbxLookbackString,
        StopIf(this.version < 4),
        "phy_model_custom" / GbxNodeRef,
        StopIf(this.version < 5),
        "vis_model_custom" / GbxNodeRef,
        StopIf(this.version < 6),
        "u01" / Int32ul,  # actions?
        StopIf(this.version < 7),
        "default_cam" / GbxEDefaultCam,
        StopIf(this.version < 8),
        "entity_model_edition" / GbxNodeRef,
        "entity_model" / GbxNodeRef,
        StopIf(this.version < 13),
        "u02" / GbxNodeRef,
        StopIf(this.version < 15),
        "u03" / GbxNodeRef,
    )
    * "Model"
)
Chunk_2E00201A = Struct("u01" / GbxNodeRef)
Chunk_2E00201C = Struct(
    "version" / ExprValidator(Int32ul, obj_ == 5),
    "default_placement" / GbxNodeRef,
    # "u01" / Int32sl[5], ???
)
Chunk_2E00201E = Struct(
    "version" / ExprValidator(Int32ul, obj_ >= 3),
    "archetype_ref" / GbxString,
    "u01" / If(lambda this: len(this.archetype_ref) == 0, Int32sl),
    StopIf(this.version < 5),
    "u02" / GbxString,
    StopIf(this.version < 6),
    "u03" / Int32sl,
)
Chunk_2E00201F = Struct(
    "version" / ExprValidator(Int32ul, obj_ >= 10),
    "waypoint_type" / GbxEWaypointType,
    "disable_lightmap" / GbxBool,
    "u01" / Int32sl,
    StopIf(this.version < 11),
    "u02" / Byte,
    StopIf(this.version < 12),
    "u03" / Int32sl,
    "u04" / Int32sl,
)
Chunk_2E002020 = Struct(
    "version" / ExprValidator(Int32ul, obj_ >= 3),
    "icon_fid" / GbxString,
    "u01" / Byte,
)

# 2E020 CGameItemPlacementParam
Chunk_2E020000 = Struct(
    "version" / Int32ul,
    "flags" / Int16ul,
    "cube_center" / GbxVec3,
    "cube_size" / Float32l,
    "grid_snap_h_step" / Float32l,
    "grid_snap_v_step" / Float32l,
    "grid_snap_h_offset" / Float32l,
    "grid_snap_v_offset" / Float32l,
    "fly_v_step" / Float32l,
    "fly_v_offset" / Float32l,
    "pivot_snap_distance" / Float32l,
)
Chunk_2E020005 = Struct("item_placement" / GbxNodeRef)

# 2E026 CGameCommonItemEntityModelEdition
Chunk_2E026000 = Struct(
    "version" / Int32ul,
    "item_type" / GbxEItemType,
    "mesh_crystal" / GbxNodeRef,
    "rest" / GreedyBytes,
)

# 2E027 CGameCommonItemEntityModel
Chunk_2E027000 = Struct(
    "version" / ExprValidator(Int32ul, obj_ >= 4), "static_object" / GbxNodeRef
)

# 2F0BC ???
Chunk_2F0BC000 = Struct(
    "version" / Int32ul,
    "variants"
    / PrefixedArray(
        Int32ul, Struct("props" / GbxDict, "node" / GbxNodeRef, "u01" / Int32sl)
    ),
)

BodyChunkId_to_struct.update(
    {
        # 09003
        0x09003003: Chunk_09003003,
        0x09003005: Chunk_09003005,
        # 09006
        0x09006001: Chunk_09006001,
        0x09006005: Chunk_09006005,
        0x09006009: Chunk_09006009,
        0x0900600B: Chunk_0900600B,
        0x0900600F: Chunk_0900600F,
        0x09006010: Chunk_09006010,
        # 0900C
        0x0900C003: Chunk_0900C003,
        # 0902C
        0x0902C002: Chunk_0902C002,
        0x0902C004: Chunk_0902C004,
        # 0903A
        0x0903A004: Chunk_0903A004,
        0x0903A00A: Chunk_0903A00A,
        # 09056
        0x09056000: Chunk_09056000,
        # 09057
        0x09057001: Chunk_09057001,
        # 0906A
        0x0906A001: Chunk_0906A001,
        # 09079
        0x09079001: Chunk_09079001,
        0x09079007: Chunk_09079007,
        # 090BB
        0x090BB000: Chunk_090BB000,
        # 090FD
        0x090FD000: Chunk_090FD000,
        0x090FD001: Chunk_090FD001,
        0x090FD002: Chunk_090FD002,
        # 09159
        0x09159000: Chunk_09159000,
        # 09187
        0x09187000: Chunk_09187000,
        # 2E001
        0x2E001009: Chunk_2E001009,
        0x2E00100B: Chunk_2E00100B,
        0x2E00100C: Chunk_2E00100C,
        0x2E00100D: Chunk_2E00100D,
        0x2E00100E: Chunk_2E00100E,
        0x2E001010: Chunk_2E001010,
        0x2E001011: Chunk_2E001011,
        0x2E001012: Chunk_2E001012,
        # 2E002
        0x2E002008: Chunk_2E002008,
        0x2E002009: Chunk_2E002009,
        0x2E00200C: Chunk_2E00200C,
        0x2E002012: Chunk_2E002012,
        0x2E002015: Chunk_2E002015,
        0x2E002019: Chunk_2E002019,
        0x2E00201A: Chunk_2E00201A,
        0x2E00201C: Chunk_2E00201C,
        0x2E00201E: Chunk_2E00201E,
        0x2E00201F: Chunk_2E00201F,
        0x2E002020: Chunk_2E002020,
        # 2E020
        0x2E020000: Chunk_2E020000,
        0x2E020005: Chunk_2E020005,
        # 2E026
        0x2E026000: Chunk_2E026000,
        # 2E027
        0x2E027000: Chunk_2E027000,
        # 2F0BC
        0x2F0BC000: Chunk_2F0BC000,
    }
)


# Headers chunks

Chunk_2E001003 = Struct(
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

Chunk_2E001004 = Struct(
    "width_and_webp"
    / Rebuild(Int16ul, lambda this: this.width + (0x8000 if this.webp else 0x0000)),
    "width" / Computed(this.width_and_webp & 0x7FFF),
    "height_and_webp"
    / Rebuild(Int16ul, lambda this: this.height + (0x8000 if this.webp else 0x0000)),
    "height" / Computed(this.height_and_webp & 0x7FFF),
    "webp"
    / Computed(
        lambda this: (this.width_and_webp & 0x8000)
        == (this.height_and_webp & 0x8000)
        == 0x8000
    ),
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

HeaderChunkId_to_struct = {
    0x2E001003: Chunk_2E001003,
    0x2E001004: Chunk_2E001004,
}


def set_nodes_array(obj, ctx):
    ctx._root._params.nodes += [None] * obj
    return obj


def get_nodes_array(obj, ctx):
    return len(ctx._root._params.nodes)


def load_external_nodes(obj, ctx):
    ctx._root._params.nodes[obj.node_index] = "TODO"

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
            Const(b"R"),  # or E?
            "class_id" / GbxChunkId,
            "chunks"
            / Prefixed(
                Int32ul,
                Select(
                    Struct(
                        "entries"
                        / PrefixedArray(
                            Int32ul,
                            Struct(
                                "id" / GbxChunkId,
                                "_size_and_heavy"
                                / Rebuild(
                                    Int32ul,
                                    lambda this: len(
                                        HeaderChunkId_to_struct.get(
                                            this.id, GreedyBytes
                                        ).build(
                                            this._._.data[this._index],
                                            gbx_data={},
                                        )
                                    )
                                    + (0x80000000 if this.heavy else 0x00),
                                ),
                                "size" / Computed(this._size_and_heavy & 0x7FFFFFFF),
                                "heavy"
                                / Computed(
                                    (this._size_and_heavy & 0x80000000) == 0x80000000
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
                                        HeaderChunkId_to_struct,
                                        default=Bytes(
                                            lambda this: this.entries[this._index].size
                                        ),
                                    ),
                                    Struct(
                                        "parse_header_chunk_failed"
                                        / Bytes(
                                            lambda this: this._.entries[
                                                this._index
                                            ].size
                                        )
                                    ),
                                ),
                                reset_lookbackstring,
                                reset_lookbackstring,
                            ),
                        ),
                    ),
                    Pass,
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
                        "folder_index"
                        / If(
                            lambda this: not this.flags.is_ref_resource_index, Int32ul
                        ),
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
