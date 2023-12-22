from construct import Enum, Byte, Int32ul, Int32sl, BitsInteger

GbxEProdState = Enum(Byte, Aborted=0, GameBox=1, DevBuild=2, Release=3)
GbxEItemType = Enum(
    Int32ul,
    Undefined=0,
    Ornament=1,
    PickUp=2,
    Character=3,
    Vehicle=4,
    Spot=5,
    Cannon=6,
    Group=7,
    Decal=8,
    Turret=9,
    Wagon=10,
    Block=11,
    EntitySpawner=12,
    DeprecV=13,
    Procedural=14,
)
GbxEDefaultCam = Enum(
    Int32ul,
    No=0,
    Default=1,
    Free=2,
    Spectator=3,
    Behind=4,
    Close=5,
    Internal=6,
    Helico=7,
    FirstPerson=8,
    ThirdPerson=9,
    ThirdPersonTop=10,
    Iso=11,
    IsoFocus=12,
    Dia3=13,
    Board=14,
    MonoScreen=15,
    Rear=16,
    Debug=17,
    _1=18,
    _2=19,
    _3=20,
    Alt1=21,
    Orbital=22,
    Decals=23,
    Snap=24,
)
GbxELayerType = Enum(
    Int32ul,
    Geometry=0,
    Smooth=1,
    Translation=2,
    Rotation=3,
    Scale=4,
    Mirror=5,
    U07=6,
    U08=7,
    Subdivide=8,
    Chaos=9,
    U11=10,
    U12=11,
    Deformation=12,
    Cubes=13,
    Trigger=14,
    SpawnPosition=15,
)
GbxEWayPointType = Enum(Int32ul, Start=0, Finish=1, Checkpoint=2, No=3, StartFinish=4, Dispenser=5)
GbxETexAddress = Enum(Int32ul, Wrap=0, Mirror=1, Clamp=2, Border=3)
GbxESurfType = Enum(
    Int32sl,
    Sphere=0,
    Ellipsoid=1,
    Box=6,  # (Primitive)
    Mesh=7,
    VCylinder=8,  # (Primitive)
    MultiSphere=9,  # (Primitive)
    ConvexPolyhedron=10,
    Capsule=11,  # (Primitive)
    Circle=12,  #  (Non3d)
    Compound=13,
    SphereLocated=14,  # (Primitive)
    CompoundInstance=15,
    Cylinder=16,  # (Primitive)
    SphericalShell=17,
)
GbxEPlugSurfacePhysicsId = Enum(
    Byte,
    Concrete=0,
    Pavement=1,
    Grass=2,
    Ice=3,
    Metal=4,
    Sand=5,
    Dirt=6,
    Turbo_Deprecated=7,
    DirtRoad=8,
    Rubber=9,
    SlidingRubber=10,
    Test=11,
    Rock=12,
    Water=13,
    Wood=14,
    Danger=15,
    Asphalt=16,
    WetDirtRoad=17,
    WetAsphalt=18,
    WetPavement=19,
    WetGrass=20,
    Snow=21,
    ResonantMetal=22,
    GolfBall=23,
    GolfWall=24,
    GolfGround=25,
    Turbo2_Deprecated=26,
    Bumper_Deprecated=27,
    NotCollidable=28,
    FreeWheeling_Deprecated=29,
    TurboRoulette_Deprecated=30,
    WallJump=31,
    MetalTrans=32,
    Stone=33,
    Player=34,
    Trunk=35,
    TechLaser=36,
    SlidingWood=37,
    PlayerOnly=38,
    Tech=39,
    TechArmor=40,
    TechSafe=41,
    OffZone=42,
    Bullet=43,
    TechHook=44,
    TechGround=45,
    TechWall=46,
    TechArrow=47,
    TechHook2=48,
    Forest=49,
    Wheat=50,
    TechTarget=51,
    PavementStair=52,
    TechTeleport=53,
    Energy=54,
    TechMagnetic=55,
    TurboTechMagnetic_Deprecated=56,
    Turbo2TechMagnetic_Deprecated=57,
    TurboWood_Deprecated=58,
    Turbo2Wood_Deprecated=59,
    FreeWheelingTechMagnetic_Deprecated=60,
    FreeWheelingWood_Deprecated=61,
    TechSuperMagnetic=62,
    TechNucleus=63,
    TechMagneticAccel=64,
    MetalFence=65,
    TechGravityChange=66,
    TechGravityReset=67,
    RubberBand=68,
    Gravel=69,
    Hack_NoGrip_Deprecated=70,
    Bumper2_Deprecated=71,
    NoSteering_Deprecated=72,
    NoBrakes_Deprecated=73,
    RoadIce=74,
    RoadSynthetic=75,
    Green=76,
    Plastic=77,
    DevDebug=78,
    Free3=79,
    XXX_Null=80,
)

GbxEPlugSurfaceGameplayId = Enum(
    Byte,
    No=0,
    Turbo=1,
    Turbo2=2,
    TurboRoulette=3,
    FreeWheeling=4,
    NoGrip=5,
    NoSteering=6,
    ForceAcceleration=7,
    Reset=8,
    SlowMotion=9,
    Bumper=10,
    Bumper2=11,
    ReactorBoost_Legacy=12,
    Fragile=13,
    ReactorBoost2_Legacy=14,
    Bouncy=15,
    NoBrakes=16,
    Cruise=17,
    ReactorBoost_Oriented=18,
    ReactorBoost2_Oriented=19,
    VehicleTransform_CarSnow=20,
    VehicleTransform_Reset=21,
)
GbxEFillDir = Enum(Int32ul, U=0, V=1)
GbxEFillAlign = Enum(Int32ul, Center=0, Begin=1, End=2)
GbxEMultiDir = Enum(
    Int32ul,
    SameDir=0,
    SymmetricalDirs=1,
    AllDir=2,
    OpposedDirOnly=3,
    PerpendicularDirsOnly=4,
    NextDirOnly=5,
    PreviousDirOnly=6,
)
GbxEMultiDirByte = Enum(
    Byte,
    SameDir=0,
    SymmetricalDirs=1,
    AllDir=2,
    OpposedDirOnly=3,
    PerpendicularDirsOnly=4,
    NextDirOnly=5,
    PreviousDirOnly=6,
)
GbxECardinalDir = Enum(Byte, North=0, East=1, South=2, West=3)
GbxEVariantBaseType = Enum(Byte, Inherit=0, No=1, Conductor=2, Generator=3)
GbxEAutoTerrainPlaceType = Enum(Int32ul, Auto=0, Force=1, DoNotPlace=2, DoNotDestroy=3)
GbxEDirection = Enum(Int32ul, North=0, East=1, South=2, West=3)
GbxEAxis = Enum(Byte, X=0, Y=1, Z=2)
GbxEAxis32 = Enum(Int32ul, X=0, Y=1, Z=2)
GbxEAnimEase = Enum(
    Byte,
    Constant=0,
    Linear=1,
    QuadIn=2,
    QuadOut=3,
    QuadInOut=4,
    CubicIn=5,
    CubicOut=6,
    CubicInOut=7,
    QuartIn=8,
    QuartOut=9,
    QuartInOut=10,
    QuintIn=11,
    QuintOut=12,
    QuintInOut=13,
    SineIn=14,
    SineOut=15,
    SineInOut=16,
    ExpIn=17,
    ExpOut=18,
    ExpInOut=19,
    CircIn=20,
    CircOut=21,
    CircInOut=22,
    BackIn=23,
    BackOut=24,
    BackInOut=25,
    ElasticIn=26,
    ElasticOut=27,
    ElasticInOut=28,
    ElasticIn2=29,
    ElasticOut2=30,
    ElasticInOut2=31,
    BounceIn=32,
    BounceOut=33,
    BounceInOut=34,
)
GbxEShaderTcType = Enum(Int32ul, No=0, TransSubTexture=1)
GbxEMapKind = Enum(
    Int32ul,
    EndMarker=0,
    Campaign=1,
    Puzzle=2,
    Retro=3,
    TimeAttack=4,
    Rounds=5,
    InProgress=6,
    Campaign_7=7,
    Multi=8,
    Solo=9,
    Site=10,
    SoloNadeo=11,
    MultiNadeo=12,
)
GbxEMapKindInHeader = Enum(
    Byte,
    EndMarker=0,
    Campaign=1,
    Puzzle=2,
    Retro=3,
    TimeAttack=4,
    Rounds=5,
    InProgress=6,
    Campaign_7=7,
    Multi=8,
    Solo=9,
    Site=10,
    SoloNadeo=11,
    MultiNadeo=12,
)
GbxELightMapCacheEQuality = Enum(Int32ul, VFast=0, Fast=1, Default=2, High=3, Ultra=4)
GbxELightMapCacheEVersion = Enum(
    Int32ul,
    Invalid=0,
    _2011_07_19_Beta1=1,
    _2011_07_21_Beta1=2,
    _2011_07_26_Beta1d=3,
    _2011_08_04_Beta2a=4,
    _2011_08_08_Beta3a=5,
    _2014_03_14_Update3_Storm=6,
    _2017_03_07_ManiaPlanet4=7,
    _2020_03_25_Beta1=8,
)
GbxELightMapCacheEQualityVer = Enum(
    Int32ul,
    UltraMapperUnalignWith1k=0,
    BounceShadowFiltered=1,
    TinyAlloc_16b=2,
    ShadowCube_GeomToEyeLengthBias=3,
    BlockLight_WrongRotations=4,
    R11G11B10F_No_BounceFactor=5,
    HBasis_LQ_SignSqrt_BIntensScales=6,
    ProbeGrid_HdrScaleAmbient=7,
    ModelSplit2_GmPackReal2_V0=8,
    ShadowLQ=9,
    UnmappedBlock_FullCovering=10,
    StadiumColorisableBounces=11,
    Item_Prefab_MultiMesh=12,
    Current=13,
)
GbxELightMapCacheESortMode = Enum(Int32ul, No=0, HDiagCenter=1)
GbxELightMapCacheEAllocMode = Enum(Int32ul, _64_2=0, _64_2PUseFree=1, BestSizePUseFree=2)
GbxELightMapCacheECompressMode = Enum(Int32ul, Ldr_DXT1=0, sRGB_Hyper_DXT1=1, Hyper_sRGB_DXT1=2, Scale_sRGB_DXT1=3)
GbxELightMapCacheEBump = Enum(Int32ul, TxTyTz=0, TxTyTz_Intens=1, No=2, HBasis_Color=3, HBasis_Intens=4)
GbxELightMapCacheEPlugGpuPlatform = Enum(Int32ul, _00=0, D3D11=1, pf3=2, pf4=3, pf5=4, pf6=5)
GbxEPlugVDcl = Enum(
    BitsInteger(9),
    Position=0,
    Position1=1,
    TgtRotation=2,
    BlendWeight=3,
    BlendIndices=4,
    Normal=5,
    Normal1=6,
    PointSize=7,
    Color0=8,
    Color1=9,
    TexCoord0=10,
    TexCoord1=11,
    TexCoord2=12,
    TexCoord3=13,
    TexCoord4=14,
    TexCoord5=15,
    TexCoord6=16,
    TexCoord7=17,
    TangentU=18,
    TangentU1=19,
    TangentV=20,
    TangentV1=21,
    Color2=22,
)
GbxPlugVDclTypes = [2, 2, 0, 0, 5, 2, 2, 0, 4, 4, 1, 1, 1, 1, 1, 1, 1, 1, 2, 2, 2, 2, 4]  # ?
GbxEPlugVDclSpace = Enum(BitsInteger(4), Global3D=0, Local3D=1, Global2D=2, Local2D=3)
GbxPlugVDclSpaces = [0, 0, 2, 2, 2, 1, 1, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 1, 1, 1, 1, 2]
GbxEPlugVDclType = Enum(
    BitsInteger(9),
    Float1=0,
    Float2=1,
    Float3=2,
    Float4=3,
    ColorD3D=4,
    UByte4=5,
    Short2=6,
    Short4=7,
    UByte4N=8,
    Short2N=9,
    Short4N=10,
    UShort2N=11,
    UShort4N=12,
    UDec3=13,
    Dec3N=14,
    Half2=15,
    Half4=16,
)
GbxPlugVDclTypeBytes = [4, 8, 0xC, 0x10, 4, 4, 4, 8, 4, 4, 8, 4, 8, 4, 4, 4, 8]
GbxPlugVDclTypeComps = [1, 2, 3, 4, 4, 4, 2, 4, 4, 2, 4, 2, 4, 3, 3, 2, 4]
GbxEPlugSolidVisCstType = Enum(Int32ul, No=0, Static=1, Dynamic=2, TmCar=3, SmBody=4)
GbxERotationOrder = Enum(Byte, XYZ=0, XZY=1, YXZ=2, YZX=3, ZXY=4, ZYX=5)
