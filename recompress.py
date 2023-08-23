# pyinstaller.exe --onefile --paths=./ recompress.py

import sys

from gbx_parser import GbxStructWithoutBodyParsed

if __name__ == "__main__":
    file_path = sys.argv[1]

    with open(file_path, "rb") as f:
        raw_bytes = f.read()

        gbx_data = {}
        nodes = []
        data = GbxStructWithoutBodyParsed.parse(
            raw_bytes, gbx_data=gbx_data, nodes=nodes, filename=file_path
        )

        gbx_data = {}
        # compression
        data.header.body_compression = "compressed"
        new_bytes = GbxStructWithoutBodyParsed.build(
            data, gbx_data=gbx_data, nodes=nodes
        )

        elems = file_path.split(".")
        elems[-3] += "_recompressed"
        file_path2 = ".".join(elems)
        with open(file_path2, "wb") as f:
            f.write(new_bytes)
