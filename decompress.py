from gbx_parser import GbxStructWithoutBodyParsed

with open(
    "C:\\Users\\schad\\Documents\\Trackmania\\Items\\test_gbx1.Item.Gbx", "rb"
) as f:
    raw_bytes = f.read()

    gbx_data = {}
    nodes = []
    data = GbxStructWithoutBodyParsed.parse(raw_bytes, gbx_data=gbx_data, nodes=nodes)
    data.header.body_compressed = "uncompressed"
    GbxStructWithoutBodyParsed.build(data)
