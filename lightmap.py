import sys
from PySide6.QtWidgets import QApplication

from runtime_params import *
from gbx_editor import parse_node, generate_node, GbxEditorUi

if __name__ == "__main__3":
    import zlib

    with open("bytes.txt", "rb") as f:
        ini_bytes = f.read()
        uncompressed_bytes = zlib.decompress(ini_bytes)
        for level in range(10):
            compressed_bytes = zlib.compress(uncompressed_bytes, level=level)
            print(level)
            print(ini_bytes == compressed_bytes)
        print("====")
        print(ini_bytes)
        print("====")
        print(compressed_bytes)


if __name__ == "__main__2":
    from deep_compare import CompareVariables

    file = get_ud_tm2020_path("Maps/lm_concrete.Map.Gbx")
    file2 = get_ud_tm2020_path("Maps/lm_concrete_2.Map.Gbx")

    data, nb_nodes, raw_bytes = parse_node(file, True)
    data2, nb_nodes2, raw_bytes2 = parse_node(file2, True)

    print(CompareVariables.compare(data.body[34], data2.body[34]))

    win = GbxEditorUi(raw_bytes, data)
    win2 = GbxEditorUi(raw_bytes2, data2)

    app = QApplication.instance() or QApplication(sys.argv)
    app.exec()


if __name__ == "__main__":
    file = get_ud_tm2020_path("Maps/lm6.Map.Gbx")
    file = get_ud_tm2020_path("Maps/lm_concrete.Map.Gbx")

    data, nb_nodes, raw_bytes = parse_node(file, True)
    win = GbxEditorUi(raw_bytes, data)

    # from PIL import Image

    # with Image.open("lm_samples/export_webp/f01.webp") as im:
    #     print(im.format, im.size, im.mode)
    #     for y in range(im.size[1]):
    #         for x in range(im.size[0]):
    #             im.putpixel((x, y), (255, 0, 0))

    #     im.save(
    #         "lm_samples/export_webp/f01_after.webp",
    #         "webp",
    #         lossless=True,
    #         quality=100,
    #         exact=True,
    #         method=4,
    #     )

    # with Image.open("lm_samples/export_webp/f02.webp") as im:
    #     print(im.format, im.size, im.mode)
    #     for y in range(im.size[1]):
    #         for x in range(im.size[0]):
    #             im.putpixel((x, y), (10, 10, 10))

    #     im.save(
    #         "lm_samples/export_webp/f02_after.webp",
    #         "webp",
    #         lossless=True,
    #         quality=100,
    #         exact=True,
    #         method=4,
    #     )

    # with open("lm_samples/export_webp/f01_after.webp", "rb") as new_im:
    #     im_bytes = new_im.read()
    #     data.body[34].chunk.content.lightmaps.lightmapFrames[0].frame1 = im_bytes
    #     data.body[34].chunk.content.lightmaps.lightmapFrames[1].frame1 = im_bytes
    # with open("lm_samples/export_webp/f02_after.webp", "rb") as new_im:
    #     im_bytes = new_im.read()
    #     data.body[34].chunk.content.lightmaps.lightmapFrames[0].frame2 = im_bytes

    # with open("lm_samples/export_webp/f03_after.webp", "rb") as new_im:
    #     im_bytes = new_im.read()
    #     data.body[34].chunk.content.lightmaps.lightmapFrames[0].frame3 = im_bytes

    # import random

    # mapping = (
    #     data.body[34].chunk.content.lightmaps.data.content.body[8].chunk.content.mapping
    # )
    # color0 = mapping.colorData.content[1]
    # for i in range(100, 244):  # len(color0)):
    #     color0[i] = 255

    # bytes3, win3 = generate_node(data)

    # with open(
    #     get_ud_tm2020_path("Maps/refact/lm6.Map.Gbx"),
    #     "wb",
    # ) as f:
    #     f.write(bytes3)

    # with open("data.txt", "w") as file:
    #     for st in data.body[8].chunk.content.mapping.binding.content:
    #         file.write(str(st.u01) + "\t" + str(st.u02.x) + "\t" + str(st.u02.y) + "\n")

    # from PIL import Image, ImageDraw

    # with Image.open("export_webp/f02.webp") as im:
    #     ratio = 0.5
    #     im = im.resize((2048 * ratio, 2048 * ratio))
    #     draw = ImageDraw.Draw(im)
    #     for idx, pt in enumerate(data.body[8].chunk.content.mapping.positions.content):
    #         other = data.body[8].chunk.content.mapping.objBindings.content[idx]
    #         size = data.body[8].chunk.content.mapping.sizes.content[idx]
    #         pos = (pt.x * ratio, pt.y * ratio)
    #         pos2 = (pt.x * ratio + size.x * ratio, pt.y * ratio + size.y * ratio)
    #         txt = f"{other.objIdx_x4/4}.{other.islandIdx}"
    #         # txt = f"{other2.x} {other2.y}"
    #         # txt = str(idx)
    #         # draw.point(pos, fill="red")
    #         draw.rectangle([pos, pos2], outline="red")
    #         draw.text(pos, txt, fill="red")

    #     im.show()
    #     im.save("lm.png")

    # with Image.open("sample4/LightMap0_HSH1.webp") as im:
    #     im_flipped = im.transpose(method=Image.Transpose.FLIP_TOP_BOTTOM)
    #     draw = ImageDraw.Draw(im_flipped)
    #     for idx, pt in enumerate(data.body[8].chunk.content.mapping.positions.content):
    #         pos = (pt.x, pt.y)
    #         other = data.body[8].chunk.content.mapping.data2.content[idx]
    #         txt = f"{other.u01} {other.u02.x}"
    #         draw.point(pos, fill="red")
    #         draw.text(pos, txt, fill="red")

    #     im_flipped.show()
    #     im_flipped.save("lm.png")

    with open("lm_samples/export_webp_concrete/f01.webp", "wb") as webp_file:
        webp_file.write(data.body[34].chunk.content.lightmaps.lightmapFrames[0].frame1)
    with open("lm_samples/export_webp_concrete/f02.webp", "wb") as webp_file:
        webp_file.write(data.body[34].chunk.content.lightmaps.lightmapFrames[0].frame2)
    with open("lm_samples/export_webp_concrete/f03.webp", "wb") as webp_file:
        webp_file.write(data.body[34].chunk.content.lightmaps.lightmapFrames[0].frame3)
    with open("lm_samples/export_webp_concrete/f11.webp", "wb") as webp_file:
        webp_file.write(data.body[34].chunk.content.lightmaps.lightmapFrames[1].frame1)
    # with open("lm_samples/export_webp_concrete/f21.webp", "wb") as webp_file:
    #     webp_file.write(data.body[34].chunk.content.lightmaps.lightmapFrames[2].frame1)

    app = QApplication.instance() or QApplication(sys.argv)
    app.exec()

    # with Image.open("lm_samples/export_webp/f03.webp") as im:
    #     print(im.format, im.size, im.mode)
    #     # for y in range(im.size[1]):
    #     #     for x in range(im.size[0]):
    #     #         im.putpixel((x, y), (200, 200, 200))

    #     im.save(
    #         "lm_samples/export_webp/f03_after.webp",
    #         "webp",
    #         lossless=True,
    #         quality=90,
    #         exact=True,
    #         method=4,
    #     )

    #     # with open("lm_samples/export_webp/f03.webp", "rb") as new_im:
    #     #     im_bytes = new_im.read()

    #     # for lossless in [False, True]:
    #     #     for exact in [False, True]:
    #     #         for quality in range(50, 101):
    #     #             for method in range(7):
    #     #                 im.save(
    #     #                     "lm_samples/export_webp/f03_after.webp",
    #     #                     "webp",
    #     #                     lossless=lossless,
    #     #                     quality=quality,
    #     #                     exact=True,
    #     #                     method=method,
    #     #                 )
    #     #                 with open(
    #     #                     "lm_samples/export_webp/f03_after.webp", "rb"
    #     #                 ) as new_im:
    #     #                     im_bytes2 = new_im.read()
    #     #                     if len(im_bytes) == len(im_bytes2):
    #     #                         print(lossless)
    #     #                         print(quality)
    #     #                         print(exact)
    #     #                         print(method)
    #     # print("end")
