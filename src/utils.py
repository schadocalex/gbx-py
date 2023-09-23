import datetime

from construct import Container, ListContainer


def update_surf(node, physicsId=None, gameplayId=None, materialIndex=None, gameplayMainDir=None):
    # remove native materials from surf
    node.body[0].chunk.materials = ListContainer([])

    for idx, materialId in enumerate(node.body[0].chunk.materialsIds):
        if materialIndex is None or materialIndex == idx:
            if physicsId is not None:
                materialId.physicsId = physicsId
            if gameplayId is not None:
                materialId.gameplayId = gameplayId

        for tri in node.body[0].chunk.surf.data.triangles:
            if materialIndex is None or materialIndex == tri.materialIndex:
                if physicsId is not None:
                    tri.materialId.physicsId = physicsId
                if gameplayId is not None:
                    tri.materialId.gameplayId = gameplayId

    if gameplayMainDir is not None:
        node.body[0].chunk.surf.u01 = gameplayMainDir


def update_all_surf(data, *surfParams, **surfParamsKw):
    for node in data.nodes:
        if type(node) == Container:
            if node.classId == 0x0900C000:
                update_surf(node, *surfParams, **surfParamsKw)


def animate(
    data,
    transAxis,
    transMin,
    transMax,
    transFn,
    rotAxis,
    rotMin,
    rotMax,
    rotFn,
    surfParams=None,
    meshAtStart=False,
):
    if surfParams is not None:
        update_all_surf(data, *surfParams)

    dyna_node_index = len(data.nodes)
    data.nodes.append(
        Container(
            classId=0x09144000,
            body=Container(
                version=13,
                IsStatic=False,
                DynamizeOnSpawn=False,
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

    kinematic_node_index = len(data.nodes)
    data.nodes.append(
        Container(
            classId=0x2F0CA000,
            body=Container(
                version=0,
                subVersion=3,
                TransAnimFunc=Container(
                    TimeIsDuration=True,
                    SubFuncs=ListContainer([Container(ease=fn[0], reverse=fn[1], duration=fn[2]) for fn in transFn]),
                ),
                RotAnimFunc=Container(
                    TimeIsDuration=True,
                    SubFuncs=ListContainer([Container(ease=fn[0], reverse=fn[1], duration=fn[2]) for fn in rotFn]),
                ),
                ShaderTcType="No",
                ShaderTcVersion=0,
                ShaderTcAnimFunc=ListContainer(
                    []
                    # [Container(duration=1000, u01=0), Container(duration=1000, u01=1)]
                ),
                ShaderTcData_TransSub=None,
                # Container(
                #     NbSubTexture=5,
                #     NbSubTexturePerLine=1,
                #     NbSubTexturePerColumn=8,
                #     TopToBottom=False,
                # ),
                TransAxis=transAxis,
                TransMin=transMin,
                TransMax=transMax,
                RotAxis=rotAxis,
                AngleMinDeg=rotMin,
                AngleMaxDeg=rotMax,
            ),
        ),
    )

    data.nodes[1] = Container(
        classId=0x09145000,
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
                        pos=Container(x=0, y=0, z=0),
                        dynaParams=Container(
                            chunkId=0x2F0B6000,
                            TextureId=2,
                            u01=1,
                            CastStaticShadow=False,
                            IsKinematic=True,
                            u04=-1,
                            u05=-1,
                            u06=-1,
                        ),
                        LodGroupId=-1,
                        name="",
                    ),
                    Container(
                        model=kinematic_node_index,
                        rot=Container(x=0, y=0, z=0, w=1),
                        pos=Container(x=0, y=0, z=0),
                        constraintParams=Container(
                            chunkId=0x2F0C8000,
                            Ent1=1,
                            Ent2=-1,
                            Pos1=Container(x=0, y=0, z=0),
                            Pos2=Container(x=0, y=0, z=0),
                        ),
                        LodGroupId=-1,
                        name="",
                    ),
                ]
            ),
        ),
    )

    if meshAtStart:
        data.nodes[1].body.Ents.append(
            Container(
                model=2,
                rot=Container(x=0, y=0, z=0, w=1),
                pos=Container(x=0, y=0, z=0),
                constraintParams=None,
                LodGroupId=-1,
                name="",
            )
        )

    data.body[16].chunk.u08 = 0

    return data
