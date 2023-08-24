def cactus(data):
    # author
    data.header.chunks.data[0].meta.id = ""
    data.header.chunks.data[0].meta.author = get_author_name()
    data.header.chunks.data[0].catalog_position = 1
    data.header.chunks.data[2] = bytes([0, 0, 0, 0, 0, 0, 0, 0])
    data.body[1].chunk.meta.id = ""
    data.body[1].chunk.meta.author = get_author_name()
    data.body[5].chunk.catalogPosition = 1

    # dont use hit shape, else won't load (maybe due to materials, todo explore)
    # data.nodes[2] = data2.nodes[2]
    # data.nodes[2].body.mesh = 5
    # data.nodes[2].body.collidable = True
    # data.nodes[2].body.collidableRef = None

    # change material to custom materials (for now)
    data.nodes[5].body[0].chunk.material_count = 2
    data.nodes[5].body[0].chunk.list_version_02 = None
    data.nodes[5].body[0].chunk.materialFolderName = "Stadium/Media/Material/"
    data.nodes[5].body[0].chunk.custom_materials = ListContainer(
        [
            Container(
                material_name="",
                material_user_inst=data.nodes[5].body[0].chunk.materials[0],
            ),
            Container(
                material_name="",
                material_user_inst=data.nodes[5].body[0].chunk.materials[1],
            ),
        ]
    )
    data.nodes[5].body[0].chunk.materials = None

    # change surf mats
    # data.nodes[6].body[0].chunk.materials[0].hasMaterial = True
    # data.nodes[6].body[0].chunk.materials[0].materialsId = (
    #     data.nodes[6].body[0].chunk.materialsIds[0]
    # )
    # data.nodes[6].body[0].chunk.materials[1].hasMaterial = True
    # data.nodes[6].body[0].chunk.materials[1].materialsId = (
    #     data.nodes[6].body[0].chunk.materialsIds[1]
    # )
    data.nodes[6].body[0].chunk.materials = ListContainer([])

    # bypass variants
    data.nodes[1].header.class_id = 0x2E027000
    data.nodes[1].body = ListContainer(
        [
            Container(
                chunk_id=0x2E027000,
                chunk=Container(
                    version=4,
                    static_object=2,
                ),
            ),
            Container(chunk_id=0xFACADE01),
        ]
    )

    # snap positions
    # data.nodes[4].body[1].chunk.content.flags = 32 + 1
    data.nodes[4].body[1].chunk.content.pivotPositions = ListContainer(
        [Container(x=0, y=0, z=0), Container(x=0, y=7, z=0)]
    )
    data.nodes[4].body[2].chunk.content.magnetLocs = ListContainer(
        [Container(x=0, y=7, z=0, yaw=0, pitch=-90, roll=0)]
    )

    return generate_node(data)


def update_090BB000(node):
    # change material to custom materials

    node.body[0].chunk.list_version_02 = None
    node.body[0].chunk.materialFolderName = "Stadium/Media/Material/"

    custom_materials = []
    for mat in node.body[0].chunk.materials:
        custom_materials.append(
            Container(
                material_name="",
                material_user_inst=mat,
            )
        )

    node.body[0].chunk.material_count = len(custom_materials)
    node.body[0].chunk.custom_materials = ListContainer(custom_materials)
    node.body[0].chunk.materials = None

    # remove lights
    node.body[0].chunk.lights = ListContainer([])


def update_0900C000(
    node, physics=None, gameplay=None, materialIndex=None, gameplayMainDir=None
):
    # remove native materials from surf
    node.body[0].chunk.materials = ListContainer([])

    for idx, materialId in enumerate(node.body[0].chunk.materialsIds):
        if materialIndex is None or materialIndex == idx:
            if physics is not None:
                materialId.physicsId = physics
            if gameplay is not None:
                materialId.gameplayId = gameplay

        for tri in node.body[0].chunk.surf.data.triangles:
            if materialIndex is None or materialIndex == tri.materialIndex:
                if physics is not None:
                    tri.materialId.physicsId = physics
                if gameplay is not None:
                    tri.materialId.gameplayId = gameplay

    if gameplayMainDir is not None:
        node.body[0].chunk.surf.u01 = gameplayMainDir


def screen(data):
    for node in data.nodes:
        if type(node) == Container:
            if node.header.class_id == 0x090BB000:
                update_090BB000(node)
            if node.header.class_id == 0x0900C000:
                update_0900C000(node)

    # author
    data.header.chunks.data[0].meta.id = ""
    data.header.chunks.data[0].meta.author = "schadocalex"
    data.header.chunks.data[0].catalog_position = 1
    data.header.chunks.data[3] = bytes([0, 0, 0, 0, 0, 0, 0, 0])

    if data.header.class_id == 0x2E002000:
        data.body[1].chunk.meta.id = ""
        data.body[1].chunk.meta.author = "schadocalex"
        data.body[5].chunk.catalogPosition = 1

    data.body[12].chunk.EntityModel = 2
    data.body[16].chunk.u08 = 0

    # data.header.chunks.data[2].fids[0].u01 = 0

    data.nodes[25].body[0].chunk.isUsingGameMaterial = True
    data.nodes[25].body[0].chunk.materialName = "Stadium\\Media\\Material\\Ad1x1Screen"
    data.nodes[25].body[0].chunk.link = "Stadium\\Media\\Material\\Ad1x1Screen"

    return generate_node(data)


def fogger(data):
    for node in data.nodes:
        if type(node) == Container:
            if node.header.class_id == 0x090BB000:
                update_090BB000(node)
            if node.header.class_id == 0x0900C000:
                update_0900C000(node)

    # author
    data.header.chunks.data[0].meta.id = ""
    data.header.chunks.data[0].meta.author = "schadocalex"
    data.header.chunks.data[0].catalog_position = 1
    data.header.chunks.data[2] = bytes([0, 0, 0, 0, 0, 0, 0, 0])

    if data.header.class_id == 0x2E002000:
        data.body[1].chunk.meta.id = ""
        data.body[1].chunk.meta.author = "schadocalex"
        data.body[5].chunk.catalogPosition = 1

    # bypass variants
    # data.nodes = data.nodes[1:]
    # data.nodes[0] = None
    # data.nodes[2].node_offset -= 1
    # data.nodes[3].node_offset -= 1
    data.body[12].chunk.EntityModel = 2

    # data.nodes[1].header.class_id = 0x2E027000
    # data.nodes[1].body = ListContainer(
    #     [
    #         Container(
    #             chunk_id=0x2E027000,
    #             chunk=Container(
    #                 version=4,
    #                 staticObject=4,
    #                 props=Container(
    #                     triggerArea=-1,
    #                     u01=Container(
    #                         XX=1,
    #                         XY=0,
    #                         XZ=0,
    #                         YX=0,
    #                         YY=1,
    #                         YZ=0,
    #                         ZX=0,
    #                         ZY=0,
    #                         ZZ=1,
    #                         TX=0,
    #                         TY=0,
    #                         TZ=0,
    #                     ),
    #                     emitterModel=-1,
    #                     actionModels=ListContainer([]),
    #                     u03=-1,
    #                     u04=ListContainer(["", "", "", "", ""]),
    #                     u05=Container(
    #                         XX=1,
    #                         XY=0,
    #                         XZ=0,
    #                         YX=0,
    #                         YY=1,
    #                         YZ=0,
    #                         ZX=0,
    #                         ZY=0,
    #                         ZZ=1,
    #                         TX=0,
    #                         TY=0,
    #                         TZ=0,
    #                     ),
    #                     u06=0,
    #                 ),
    #             ),
    #         ),
    #         Container(chunk_id=0xFACADE01),
    #     ]
    # )

    data.body[16].chunk.u08 = 0

    # data.nodes[16].body[1].chunk.SplashModel = -1
    # data.nodes[16].body[13].chunk.u02 = -1
    # data.nodes[16].body[13].chunk.u03 = -1

    # data.nodes[2].body.EntsCount = 1
    # data.nodes[2].body.Ents = data.nodes[2].body.Ents[:1]

    return generate_node(data)


def trigger2(data):
    for node in data.nodes:
        if type(node) == Container:
            # if node.header.class_id == 0x090BB000:
            #     update_090BB000(node)
            if node.header.class_id == 0x0900C000:
                update_0900C000(node, "Concrete", "Bouncy")

    data.nodes[7].body[0].chunk.surf.u01 = Container(x=0, y=0, z=10)

    # author
    # data.header.chunks.data[0].meta.id = ""
    # data.header.chunks.data[0].meta.author = get_author_name()
    # data.header.chunks.data[0].catalog_position = 1
    # data.header.chunks.data[2] = bytes([0, 0, 0, 0, 0, 0, 0, 0])

    # if data.header.class_id == 0x2E002000:
    #     data.body[1].chunk.meta.id = ""
    #     data.body[1].chunk.meta.author = get_author_name()
    #     data.body[5].chunk.catalogPosition = 1

    new_node_index = len(data.nodes)
    data.nodes.append(
        Container(
            header=Container(class_id=0x09179000),
            body=Container(
                version=1,
                surf=7,
            ),
        )
    )

    data.nodes[1] = Container(
        header=Container(class_id=0x09145000),
        body=Container(
            version=11,
            updatedTime=datetime.datetime.now(),
            url="",
            u01=b"\x00\x00\x00\x00",
            u02=b"\x00\x00\x00\x00",
            Ents=ListContainer(
                [
                    Container(
                        model=2,
                        rot=Container(x=0, y=0, z=0, w=1),
                        pos=Container(x=0, y=0, z=0),
                        dynaParams=None,
                        constraintParams=None,
                        placementParams=None,
                        LodGroupId=-1,
                        name="",
                    ),
                    Container(
                        model=new_node_index,
                        rot=Container(x=0, y=0, z=0, w=1),
                        pos=Container(x=0, y=0, z=0),
                        dynaParams=None,
                        constraintParams=None,
                        placementParams=None,
                        LodGroupId=-1,
                        name="",
                    ),
                ]
            ),
        ),
    )

    data.nodes[2].body.isMeshCollidable = False
    data.nodes[2].body.collidableShape = -1

    data.body[16].chunk.u08 = 0

    return generate_node(data)


def pivot(data):
    constraint_model_index = len(data.nodes)
    data.nodes.append(
        Container(
            header=Container(class_id=0x2F074000),
            body=Container(
                version=0,
                Type=0,
                Spring_Length=32.0,
                Spring_DampingRatio=1.0,
                Spring_FreqHz=1.0,
            ),
        )
    )

    dyna_node_index = len(data.nodes)
    for _ in range(2):
        data.nodes.append(
            Container(
                header=Container(class_id=0x09144000),
                body=Container(
                    version=13,
                    IsStatic=False,
                    DynamizeOnSpawn=True,
                    Mesh=3,
                    DynaShape=data.nodes[1].body[0].chunk.props.triggerArea,
                    StaticShape=data.nodes[1].body[0].chunk.props.triggerArea,
                    DestructibleModel=Container(
                        BreakSpeedKmh=100.0,
                        Mass=100.0,
                        LightAliveDurationSc_Min=5.0,
                        LightAliveDurationSc_Max=7.0,
                    ),
                    u01=1,
                    u02=1,
                    u03=4,  # probably enum
                    u04=0,
                    u05=1,
                    u06=10,
                    u07=0,
                    u08=0,
                    u09=0,
                    LocAnim=-1,
                    u10=0,
                    LocAnimIsPhysical=False,
                    WaterModel=-1,
                ),
            )
        )

    data.nodes[1] = Container(
        header=Container(class_id=0x09145000),
        body=Container(
            version=11,
            updatedTime=datetime.datetime.now(),
            url="",
            u01=b"\x00\x00\x00\x00",
            u02=b"\x00\x00\x00\x00",
            Ents=ListContainer(
                [
                    Container(
                        model=dyna_node_index,
                        rot=Container(x=0, y=0, z=0, w=1),
                        pos=Container(x=16, y=0, z=0),
                        dynaParams=Container(
                            chunkId=0x2F0B6000,
                            TextureId=2,
                            u01=1,
                            CastStaticShadow=False,
                            IsKinematic=False,
                            u04=-1,
                            u05=-1,
                            u06=-1,
                        ),
                        constraintParams=None,
                        placementParams=None,
                        LodGroupId=-1,
                        name="",
                    ),
                    Container(
                        model=dyna_node_index + 1,
                        rot=Container(x=0, y=0, z=0, w=1),
                        pos=Container(x=-16, y=0, z=0),
                        dynaParams=Container(
                            chunkId=0x2F0B6000,
                            TextureId=2,
                            u01=1,
                            CastStaticShadow=False,
                            IsKinematic=False,
                            u04=-1,
                            u05=-1,
                            u06=-1,
                        ),
                        constraintParams=None,
                        placementParams=None,
                        LodGroupId=-1,
                        name="",
                    ),
                    Container(
                        model=constraint_model_index,
                        rot=Container(x=0, y=0, z=0, w=1),
                        pos=Container(x=0, y=0, z=0),
                        constraintParams=Container(
                            chunkId=0x2F0C8000,
                            Ent1=0,
                            Ent2=1,
                            Pos1=Container(x=0, y=0, z=0),
                            Pos2=Container(x=0, y=0, z=0),
                        ),
                        dynaParams=None,
                        # constraintParams=None,
                        placementParams=None,
                        LodGroupId=-1,
                        name="",
                    ),
                ]
            ),
        ),
    )

    data.nodes[2].body.isMeshCollidable = False
    data.nodes[2].body.collidableShape = -1

    data.body[16].chunk.u08 = 0

    return generate_node(data)


def rotator2(data):
    for node in data.nodes:
        if type(node) == Container:
            if node.header.class_id == 0x090BB000:
                update_090BB000(node)
            if node.header.class_id == 0x0900C000:
                update_0900C000(node)

    # author
    # data.header.chunks.data[0].meta.id = ""
    # data.header.chunks.data[0].meta.author = get_author_name()
    # data.header.chunks.data[0].catalog_position = 1
    # data.header.chunks.data[2] = bytes([0, 0, 0, 0, 0, 0, 0, 0])

    # if data.header.class_id == 0x2E002000:
    #     data.body[1].chunk.meta.id = ""
    #     data.body[1].chunk.meta.author = get_author_name()
    #     data.body[5].chunk.catalogPosition = 1

    data.body[15].chunk.baseItem = -1
    # data.body[12].chunk.MaterialModifier = -1
    data.nodes = data.nodes[:54]

    # data.nodes[6].body.rest = data2.body.rest

    return generate_node(data)


def jump(data):
    for node in data.nodes:
        if type(node) == Container:
            if node.header.class_id == 0x0900C000:
                update_0900C000(node, "NotCollidable", "ReactorBoost_Oriented")

    data.nodes[7].body[0].chunk.surf.u01 = Container(x=0, y=1, z=0)
    data.nodes[2].body.isMeshCollidable = False
    data.nodes[2].body.collidableShape = -1

    return generate_node(data)


def mesh_anim(data):
    data.nodes[4].body[1].chunk.sub_visuals = ListContainer(
        [Container(x=x * 54, y=0, z=144) for x in range(9)]
    )
    data.nodes[4].body[8].chunk.index_buffer[0].chunk.indices = ListContainer(
        data.nodes[4].body[8].chunk.index_buffer[0].chunk.indices[:144]
    )

    dyna_node_index = len(data.nodes)
    data.nodes.append(
        Container(
            header=Container(class_id=0x09144000),
            body=Container(
                version=13,
                IsStatic=False,
                DynamizeOnSpawn=False,
                Mesh=3,
                DynaShape=-1,
                StaticShape=-1,
                DestructibleModel=Container(
                    BreakSpeedKmh=100.0,
                    Mass=100.0,
                    LightAliveDurationSc_Min=5.0,
                    LightAliveDurationSc_Max=7.0,
                ),
                u01=1,
                u02=1,
                u03=4,  # probably enum
                u04=0,
                u05=1,
                u06=10,
                u07=0,
                u08=0,
                u09=0,
                LocAnim=-1,
                u10=0,
                LocAnimIsPhysical=False,
                WaterModel=-1,
            ),
        )
    )

    data.nodes[1] = Container(
        header=Container(class_id=0x09145000),
        body=Container(
            version=11,
            updatedTime=datetime.datetime.now(),
            url="",
            u01=b"\x00\x00\x00\x00",
            u02=b"\x00\x00\x00\x00",
            Ents=ListContainer(
                [
                    Container(
                        model=2,
                        rot=Container(x=0, y=0, z=0, w=1),
                        pos=Container(x=0, y=0, z=0),
                        dynaParams=None,
                        LodGroupId=-1,
                        name="",
                    ),
                    Container(
                        model=dyna_node_index,
                        rot=Container(x=0, y=0, z=0, w=1),
                        pos=Container(x=0, y=0, z=0),
                        dynaParams=Container(
                            chunkId=0x2F0B6000,
                            TextureId=2,
                            u01=8.0,
                            CastStaticShadow=False,
                            IsKinematic=False,
                            u04=16.0,
                            u05=0.0,
                            u06=1.0,
                        ),
                        LodGroupId=-1,
                        name="",
                    ),
                ]
            ),
        ),
    )

    data.body[16].chunk.u08 = 0
    return data


if __name__ == "__main__":
    file = get_extract_mp4_path("GameData/Items/Valley/Trains/Loco.Item.Gbx")
    file = get_extract_mp4_path("GameData/Valley/Media/Mesh/Loco.Mesh.gbx")

    file = get_ud_tm2020_path("Items/CustomRotatingTube.Item.Gbx")

    file = get_ud_tm2020_path("Maps/lm_concrete.Map.Gbx")

    data, nb_nodes, raw_bytes = parse_node(file, True, need_ui=True)
    win = GbxEditorUi(raw_bytes, data)

    # from export_obj import export_ents

    # export_ents("./ExportObj/", file, data)

    # from utils_bloc import extract_block_meshes

    # extract_block_meshes(os.path.basename(file), data)

    if False:
        file2 = get_extract_tm2020_path(
            "GameData/Stadium/Items/ObstacleTurnstile4mSimpleOscillateLevel0.Item.Gbx"
        )
        file2 = get_extract_tm2020_path(
            "GameData/Stadium/Media/Modifier/ItemObstacleDiscontinuous/AnimTurnstileLevel0.KinematicConstraint.Gbx"
        )
        file2 = get_extract_tm2020_path(
            "GameData/Stadium/Media/Modifier/ItemObstacle/AnimPusher4mLevel2.KinematicConstraint.Gbx"
        )
        file2 = get_extract_tm2020_path(
            "GameData/Stadium/Items/ObstaclePusher4mLevel0.Item.Gbx"
        )
        file2 = get_extract_tm2020_path(
            "GameData/Stadium256/Media/Material/WarpCeiling.Material.Gbx"
        )
        file2 = get_extract_tm2020_path(
            "GameData/Stadium/Media/Material/RoadDirt.Material.Gbx"
        )
        file2 = get_ud_tm2020_path("Materials/test_mat.Mat.Gbx")
        file2 = get_ud_tm2020_path("Items/glass_blocs/Slope/bkp/GP-S-7.Item.Gbx")

        data2, nb_nodes2, raw_bytes2 = parse_node(file2, True, need_ui=True)
        win2 = GbxEditorUi(raw_bytes2, data2)

    # bytes3, win3 = cactus(data)
    # bytes3, win3 = rotator(data)
    # bytes3, win3 = trigger(data)
    # bytes3, win3 = trigger2(data)
    # bytes3, win3 = rotator2(data)
    # bytes3, win3 = rotator3(data)
    # bytes3, win3 = exp_move(data)
    # bytes3, win3 = fogger(data)
    # bytes3, win3 = screen(data)
    # bytes3, win3 = pivot(data)
    # data = mesh_anim(data)
    # bytes3, win3 = generate_node(data, True)

    # with open(
    #     get_ud_tm2020_path(
    #         "Items/Export/" + os.path.basename(file).replace(".Item", ".Item")
    #     ),
    #     "wb",
    # ) as f:
    #     f.write(bytes3)

    # with open("result2.csv", "w") as f:
    #     import glob

    #     already_written = set()

    #     for filename in glob.glob(
    #         # get_extract_tm2020_path("GameData/Stadium/Items/*.Item.Gbx",)
    #         get_ud_tm2020_path("Items/**/*.Item.Gbx",)
    #         recursive=True,
    #     ):
    #         try:
    #             data, nb_nodes, win2 = parse_node(filename, True, need_ui=False)
    #         except:
    #             continue

    #         # f.write(f"{data.body[16].chunk.u02}\n")
    #         # f.flush()

    # for node in data.nodes:
    #     if node and node.header.class_id == 0x09145000:
    #         obj_chunk = node.nodes[node.nodes[node.body.u02].body.mesh].body[0].chunk
    #         for i, geom in enumerate(obj_chunk.shaded_geoms):
    #             export_dir = (
    #                 get_ud_tm2020_path("Items/ExportObj/")
    #             )
    #             idx = obj_chunk.visuals[geom.visual_index]
    #             vertices = node.nodes[idx + 1].body[0].chunk.vertices_coords
    #             normals = node.nodes[idx + 1].body[0].chunk.normals
    #             uv0 = node.nodes[idx + 1].body[0].chunk.others.uv0
    #             indices = node.nodes[idx].body[8].chunk.index_buffer[0].chunk.indices
    #             obj_filepath = (
    #                 export_dir
    #                 + os.path.basename(file).split(".")[0]
    #                 + f"_lod{geom.lod}_{node.node_offset}_{idx}.obj"
    #             )
    #             mat_idx = obj_chunk.materials[geom.material_index]
    #             mat = node.nodes[mat_idx].body[0].chunk.material_name
    #             print(obj_filepath)
    #             export_obj(obj_filepath, vertices, normals, uv0, indices, mat)

    # Export surf
    # export_dir = get_ud_tm2020_path("Items/")
    # surf_class = data.nodes[6]
    # surf_chunk = surf_class.body[0].chunk
    # vertices = surf_chunk.surf.data.vertices
    # mats = [
    #     surf_class.nodes[m.material].body[0].chunk.material_name
    #     for m in surf_chunk.materials
    # ]
    # faces = []
    # for tri in surf_chunk.surf.data.triangles:
    #     assert tri.materialIndex >= 0
    #     while tri.materialIndex >= len(faces):
    #         faces.append([])
    #     faces[tri.materialIndex].append(tri.face)
    # start_index = 0
    # for i in range(len(faces)):
    #     obj_filepath = export_dir + os.path.basename(file).split(".")[0] + f"_{i}.obj"
    #     export_obj2(
    #         obj_filepath,
    #         vertices,
    #         faces[i],
    #         mats[i],
    #     )
    #     start_index += len(faces[i])

    # Export obj animation (flag)
    # export_dir = get_ud_tm2020_path("Items/")
    # vertices = [v.pos for v in data.nodes[3].body[7].chunk.vertices]
    # normals = [v.vert_u02 for v in data.nodes[3].body[7].chunk.vertices]
    # uv0 = [v.uv for v in data.nodes[3].body[4].chunk.tex_coord_sets[0].tex_coords]
    # indices = data.nodes[3].body[8].chunk.index_buffer[0].chunk.indices
    # sub_visuals = data.nodes[3].body[1].chunk.sub_visuals
    # for i, vis in enumerate(sub_visuals):
    #     start_index = vis.x
    #     if i == len(sub_visuals) - 1:
    #         end_index = len(vertices)
    #     else:
    #         end_index = sub_visuals[i + 1].x
    #     obj_filepath = (
    #         export_dir + os.path.basename(file).split(".")[0] + f"_lod4_{i}.obj"
    #     )
    #     export_obj(
    #         obj_filepath,
    #         vertices[start_index:end_index],
    #         normals[start_index:end_index],
    #         uv0[start_index:end_index],
    #         indices,
    #         "ItemFlag",
    #     )

    app = QApplication.instance() or QApplication(sys.argv)
    app.exec()
