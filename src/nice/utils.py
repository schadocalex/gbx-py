import datetime
import io

from PIL import Image

from construct import Container, ListContainer

from src.parser import parse_file

Ctn = Container
List = ListContainer


def Vec3(x, y, z):
    return Ctn(x=x, y=y, z=z)


def new_chunk(chunkId, content):
    return Ctn(chunkId=chunkId, chunk=content)


def new_skippable_chunk(chunkId, content):
    return Ctn(chunkId=chunkId, skippable=b"PIKS", chunk=content)


def new_body(*chunks):
    return List([*chunks, Ctn(chunkId=0xFACADE01)])


def new_struct(classId, body):
    return Ctn(classId=classId, body=body)


def new_node(classId, *chunks):
    return Ctn(classId=classId, body=new_body(*chunks))


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
        entries=List(
            [
                Ctn(id=0x2E001003, meta=Ctn(heavy=False)),
                Ctn(id=0x2E001004, meta=Ctn(heavy=True)),
                Ctn(id=0x2E001006, meta=Ctn(heavy=False, size=8)),
                Ctn(id=0x2E002000, meta=Ctn(heavy=False)),
                Ctn(id=0x2E002001, meta=Ctn(heavy=False, size=4)),
            ]
        ),
        data=List(
            [
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
            ]
        ),
    )


def new_file(author, file_name, icon_filepath, body, nodes):
    return Ctn(
        version=6,
        bodyCompression="compressed",
        u01_R_or_E=b"R",
        classId=0x2E002000,
        numNodes=0,
        header=new_header(author, file_name, icon_filepath),
        referenceTable=Ctn(numExternalNodes=0, externalFolders=None, externalNodes=List([])),
        body=body,
        nodes=nodes,
    )


def new_item_body(author, name, waypoint_type, entity_refidx, placement_refidx):
    return new_body(
        new_chunk(0x2E001009, Ctn(pagePath="Items", hasIconFed=False, iconFed=None, u01="")),
        new_chunk(0x2E00100B, Ctn(author=Ctn(id="", collection="Stadium2020", author=author))),
        new_chunk(0x2E00100C, Ctn(name=name)),
        new_chunk(0x2E00100D, Ctn(description="No Description")),
        new_chunk(0x2E001010, Ctn(version=3, u01=-1, skinDirectory="", u02=-1)),
        new_chunk(
            0x2E001011, Ctn(version=1, isInternal=False, isAdvanced=False, catalogPosition=1, prodState="Release")
        ),
        new_chunk(0x2E001012, Ctn(version=0, u01=1, u02=0, u03=0)),
        new_chunk(0x2E002008, Ctn(nadeoSkinFids=List([-1] * 7))),
        new_chunk(0x2E002009, Ctn(version=10, cameras=List([]))),
        new_chunk(0x2E00200C, Ctn(raceInterfaceFid=-1)),
        new_chunk(
            0x2E002012,
            Ctn(
                groundPoint=Vec3(0, 0, 0),
                painterGroundMargin=0,
                orbitalCenterHeightFromGround=0,
                orbitalRadiusBase=-1,
                orbitalPreviewAngle=0.15,
            ),
        ),
        new_chunk(0x2E002015, Ctn(itemType="Ornament")),
        new_chunk(
            0x2E002019,
            Ctn(
                version=15,
                defaultWeaponName="",
                PhyModelCustom=-1,
                VisModelCustom=-1,
                u01=0,
                defaultCam="No",
                EntityModelEdition=-1,
                EntityModel=entity_refidx,
                vfxFile=-1,
                MaterialModifier=-1,
            ),
        ),
        new_chunk(0x2E00201A, Ctn(u01=-1)),
        new_chunk(0x2E00201C, Ctn(version=5, defaultPlacement=placement_refidx)),
        new_chunk(0x2E00201E, Ctn(version=7, archetypeRef="", u01=-1, u02="", baseItem=-1)),
        new_chunk(
            0x2E00201F,
            Ctn(
                version=12,
                waypointType=waypoint_type,
                disableLightmap=False,
                u01=-1,
                u08=False,
                PodiumClipList=-1,
                IntroClipList=-1,
            ),
        ),
        new_chunk(0x2E002020, Ctn(version=3, iconFid="", u01=0)),
        new_skippable_chunk(0x2E002025, b"\x00\x00\x00\x00\x00\x00\x00\x00"),
        new_skippable_chunk(0x2E002026, b"\x00\x00\x00\x00\x00\x00\x00\x00"),
        new_skippable_chunk(0x2E002027, b"\x00\x00\x00\x00\x00\x00\x00\x00"),
    )


def new_composed_model(ents):
    return new_struct(
        0x09145000,
        Ctn(
            version=11,
            updatedTime=datetime.datetime.now(),
            url="",
            u01=0,
            u02=0,
            Ents=List(ents),
        ),
    )


def new_placement_nodes(nodes):
    refidx = len(nodes)
    nodes += [
        Ctn(
            classId=0x2E020000,
            node_offset=refidx,
            body=new_body(
                Ctn(
                    chunkId=0x2E020000,
                    skippable=b"PIKS",
                    chunk=Ctn(
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
                ),
                Ctn(
                    chunkId=0x2E020001,
                    skippable=b"PIKS",
                    chunk=Ctn(
                        pivotPositions=List([]),
                        pivotRotations=List([]),
                    ),
                ),
                Ctn(
                    chunkId=0x2E020003,
                    skippable=b"PIKS",
                    chunk=Ctn(
                        version=3,
                        subversion=10,
                        u02="",
                        u03=List([]),
                        u04=0,
                        u05=1,
                        u06=List([0, 0, 0, 1.0]),
                        patchLayouts=List([]),
                        u07=List([]),
                    ),
                ),
                Ctn(
                    chunkId=0x2E020004,
                    skippable=b"PIKS",
                    chunk=Ctn(
                        version=0,
                        magnetLocs=List([]),
                    ),
                ),
            ),
        )
    ]

    return refidx


def extract_file(nodes, filepath, classId=None):
    data, nb_nodes, raw_bytes = parse_file(filepath)
    if classId is not None:
        assert data.classId == classId

    refidx = len(nodes)

    nodes.append(Ctn(classId=data.classId, body=data.body, node_offset=refidx))
    nodes += data.nodes[1:]

    return refidx


def extract_shape(nodes, filepath):
    data, nb_nodes, raw_bytes = parse_file(filepath)
    assert data.classId == 0x0900C000

    refidx = len(nodes)
    data.body[0].chunk.skel = -1  # remove useless skel
    nodes.append(Ctn(classId=data.classId, body=data.body))

    return refidx


def get_refidx(nodes, files_refidx, filepath, extract_fn=extract_file, *params):
    if filepath in files_refidx:
        return files_refidx[filepath]
    else:
        files_refidx[filepath] = extract_fn(nodes, filepath, *params)
        return files_refidx[filepath]
