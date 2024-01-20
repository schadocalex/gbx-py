import datetime
import io
from PIL import Image
from construct import Container

from ..parser import parse_file
from ..gbx_structs import NodeRef

Ctn = Container


def Vec3(x, y, z):
    return Ctn(x=x, y=y, z=z)


def new_skippable_bytes(raw_bytes):
    return Ctn(_skippable=True, _unknownChunkId=raw_bytes)


def new_struct(classId, body):
    return Ctn(classId=classId, body=body)


def new_ent(loc, model, params=None):
    return Ctn(
        model=model,
        rot=loc.as_quat(),
        pos=loc.as_pos(),
        params=Ctn(chunkId=-1, chunk=None) if params is None else params,
        u01=b"",
    )


def new_entities(ents):
    return new_struct(
        0x09145000,
        Ctn(
            version=11,
            updatedTime=datetime.datetime.now(),
            url="",
            u01=0,
            u02=0,
            Ents=ents,
        ),
    )


def new_icon_chunk(icon_filepath):
    try:
        im = Image.open(icon_filepath)
    except:
        im = Image.open("assets/default_icon.png")

    im = im.resize((64, 64))
    im = im.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    im = im.convert("RGBA")

    # apply premultiplied alpha
    for x in range(im.size[0]):
        for y in range(im.size[1]):
            r, g, b, a = im.getpixel((x, y))
            if a < 255:
                coeff = a / 255
                im.putpixel(
                    (x, y),
                    (
                        int(r * coeff),
                        int(g * coeff),
                        int(b * coeff),
                        a,
                    ),
                )
    # ensure at least one pixel has transparency
    r, g, b, a = im.getpixel((0, 0))
    if a == 255:
        im.putpixel((0, 0), (r, g, b, 254))

    im_bytes = io.BytesIO()
    im.save(
        im_bytes,
        "webp",
        lossless=True,
        quality=100,
        exact=True,
        method=4,
    )
    im.close()

    return Ctn(
        width=64,
        height=64,
        webp=True,
        data=Ctn(
            version=2,
            image=im_bytes.getvalue(),
        ),
    )


def new_header(author, file_name, icon_filepath):
    return Ctn(
        entries=[
            Ctn(id=0x2E001003, meta=Ctn(heavy=False)),
            Ctn(id=0x2E001004, meta=Ctn(heavy=True)),
            Ctn(id=0x2E001006, meta=Ctn(heavy=False)),
            Ctn(id=0x2E002000, meta=Ctn(heavy=False)),
            Ctn(id=0x2E002001, meta=Ctn(heavy=False)),
        ],
        data=[
            Ctn(
                meta=Ctn(id="", collection="Stadium2020", author=author),
                version=8,
                pageName="Items",
                u01="",
                flags=0x00000010,
                catalogPosition=1,
                fileName=file_name,
                prodState="Release",
            ),
            new_icon_chunk(icon_filepath),
            b"\x00\x00\x00\x00\x00\x00\x00\x00",
            Ctn(itemType="Ornament"),
            b"\x00\x00\x00\x00",
        ],
    )


def new_file(author, file_name, icon_filepath, body):
    return Ctn(
        version=6,
        bodyCompression="compressed",
        status="Release",
        classId=0x2E002000,
        header=new_header(author, file_name, icon_filepath),
        numNodes=0,
        referenceTable=Ctn(numExternalNodes=0, externalFolders=None, externalNodes=[]),
        body=body,
    )


def new_item_body(author, name, waypoint_type, entity, placement):
    return {
        0x2E001009: Ctn(pagePath="Items", hasIconFed=False, iconFed=None, u01=""),
        0x2E00100B: Ctn(author=Ctn(id="", collection="Stadium2020", author=author)),
        0x2E00100C: Ctn(name=name),
        0x2E00100D: Ctn(description="No Description"),
        0x2E001010: Ctn(version=3, u01=NodeRef(), skinDirectory="", u02=NodeRef()),
        0x2E001011: Ctn(
            version=1,
            isInternal=False,
            isAdvanced=False,
            catalogPosition=1,
            prodState="Release",
        ),
        0x2E001012: Ctn(version=0, u01=1, u02=0, u03=0),
        0x2E002008: Ctn(nadeoSkinFids=[NodeRef()] * 7),
        0x2E002009: Ctn(version=10, cameras=[]),
        0x2E00200C: Ctn(raceInterfaceFid=NodeRef()),
        0x2E002012: Ctn(
            groundPoint=Vec3(0, 0, 0),
            painterGroundMargin=0,
            orbitalCenterHeightFromGround=0,
            orbitalRadiusBase=-1,
            orbitalPreviewAngle=0.15,
        ),
        0x2E002015: Ctn(itemType="Ornament"),
        0x2E002019: Ctn(
            version=15,
            defaultWeaponName="",
            PhyModelCustom=NodeRef(),
            VisModelCustom=NodeRef(),
            u01=0,
            defaultCam="No",
            EntityModelEdition=NodeRef(),
            EntityModel=entity,
            vfxFile=NodeRef(),
            MaterialModifier=NodeRef(),
        ),
        0x2E00201A: Ctn(u01=NodeRef()),
        0x2E00201C: Ctn(version=5, defaultPlacement=placement),
        0x2E00201E: Ctn(version=7, archetypeRef="", u01=-1, u02="", baseItem=NodeRef()),
        0x2E00201F: Ctn(
            version=12,
            waypointType=waypoint_type,
            disableLightmap=False,
            u01=-1,
            u08=False,
            PodiumClipList=NodeRef(),
            IntroClipList=NodeRef(),
        ),
        0x2E002020: Ctn(version=3, iconFid="", u01=0),
        0x2E002025: new_skippable_bytes(b"\x00\x00\x00\x00\x00\x00\x00\x00"),
        0x2E002026: new_skippable_bytes(b"\x00\x00\x00\x00\x00\x00\x00\x00"),
        0x2E002027: new_skippable_bytes(b"\x00\x00\x00\x00\x00\x00\x00\x00"),
        0xFACADE01: None,
    }


def new_placement_node():
    return NodeRef(
        classId=0x2E020000,
        body={
            0x2E020000: Ctn(
                _skippable=True,
                version=0,
                flags=37,
                cubeCenter=Ctn(x=0, y=0, z=0),
                cubeSize=0,
                gridSnap_HStep=0,
                gridSnap_VStep=0,
                gridSnap_HOffset=0,
                gridSnap_VOffset=0,
                flyStep=0,
                flyOffset=0,
                pivotSnapDistance=0,
            ),
            0x2E020001: Ctn(
                _skippable=True,
                pivotPositions=[],
                pivotRotations=[],
            ),
            0x2E020003: Ctn(
                _skippable=True,
                version=3,
                subversion=10,
                u02="",
                u03=[],
                u04=0,
                u05=1,
                u06=[0, 0, 0, 1.0],
                patchLayouts=[],
                u07=[],
            ),
            0x2E020004: Ctn(
                _skippable=True,
                version=0,
                magnetLocs=[],
            ),
        },
    )


def extract_file(filepath, classId=None):
    data = parse_file(filepath)
    assert classId is None or data.classId == classId
    return NodeRef(data)


def extract_shape(filepath):
    data = parse_file(filepath)
    assert data.classId == 0x0900C000

    # remove useless skel
    data.body[0x0900C003].skel = NodeRef()

    return NodeRef(data)


def get_noderef(files_parsed, filepath, extract_fn=extract_file, *params):
    if filepath in files_parsed:
        return files_parsed[filepath]
    else:
        files_parsed[filepath] = extract_fn(filepath, *params)
        return files_parsed[filepath]
