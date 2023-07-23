    
    
    file = "sample_pierrot/LightMapCache.Gbx"
    file = get_ud_tm2020_path("Maps/pierrot/KtarKmtar2.Map.Gbx")
    file = get_ud_tm2020_path("Maps/lm5.Map.Gbx")
    # file = get_ud_tm2020_path("Maps/lm_concrete.Map.Gbx")
    # file = "sample_concrete/LightMapCache.Gbx"
    file = get_ud_tm2020_path("Maps/lm6.Map.Gbx")
    file = "sample_concrete/LightMapCache.Gbx"

    data, nb_nodes, raw_bytes = parse_node(file, True, need_ui=True)
    print(f"total nodes: {nb_nodes}")

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

    # with open("export_webp/f01.webp", "wb") as webp_file:
    #     webp_file.write(data.body[34].chunk.content.lightmaps.lightmapFrames[0].frame1)
    # with open("export_webp/f02.webp", "wb") as webp_file:
    #     webp_file.write(data.body[34].chunk.content.lightmaps.lightmapFrames[0].frame2)
    # with open("export_webp/f03.webp", "wb") as webp_file:
    #     webp_file.write(data.body[34].chunk.content.lightmaps.lightmapFrames[0].frame3)
    # with open("export_webp/f11.webp", "wb") as webp_file:
    #     webp_file.write(data.body[34].chunk.content.lightmaps.lightmapFrames[1].frame1)
    # with open("export_webp/f21.webp", "wb") as webp_file:
    #     webp_file.write(data.body[34].chunk.content.lightmaps.lightmapFrames[2].frame1)