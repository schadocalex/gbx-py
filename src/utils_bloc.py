import os

from construct import Container, ListContainer

from export_obj import export_ents, extract_meshes, export_obj, transform_final_pos


def extract_mobil(export_dir, file, data, mobil):
    for chunk in mobil.body:
        if chunk.chunkId == 0x03122003:
            print("\t\t\tprefab_fid: " + str(chunk.chunk.prefab_fid))
            if chunk.chunk.prefab_fid > 0:
                export_ents(export_dir, file, data.nodes[chunk.chunk.prefab_fid])
            else:
                print(chunk.chunk)


def extract_variant_chunk(result, export_dir, file, data, variant):
    for chunk in variant:
        if chunk.chunkId == 0x0315B003:
            print("\tsymmetrical_variant_index: " + str(chunk.chunk.symmetrical_variant_index))
            print("\tvariant_base_type: " + str(chunk.chunk.variant_base_type))
        if chunk.chunkId == 0x0315B005:
            for mobil_idx, mobil in enumerate(chunk.chunk.mobils):
                print("\tmobil")
                for sub_mobil_idx, sub_mobil in enumerate(mobil):
                    print("\t\tsub_mobil")
                    extract_mobil(
                        result,
                        export_dir + f"mobil{mobil_idx}/submobil{sub_mobil_idx}/",
                        file,
                        data,
                        data.nodes[sub_mobil],
                    )
        if chunk.chunkId == 0x0315B008:
            for block_unit_model_idx in chunk.chunk.blockUnitModels:
                print("\tblock_unit_model (contains clips): " + str(block_unit_model_idx))
                block_unit_model = data.nodes[block_unit_model_idx]
                print("\tblock_unit_model: " + str(block_unit_model))
                for chunk in block_unit_model.body:
                    if chunk.chunkId == 0x0303600C:
                        for clip in chunk.chunk.clipsNorth:
                            extract_block_meshes(data.nodes[clip].body[2].chunk.name, data.nodes[clip])
                        for clip in chunk.chunk.clipsEast:
                            extract_block_meshes(data.nodes[clip].body[2].chunk.name, data.nodes[clip])
                        for clip in chunk.chunk.clipsSouth:
                            extract_block_meshes(data.nodes[clip].body[2].chunk.name, data.nodes[clip])
                        for clip in chunk.chunk.clipsWest:
                            extract_block_meshes(data.nodes[clip].body[2].chunk.name, data.nodes[clip])
                        for clip in chunk.chunk.clipsTop:
                            extract_block_meshes(data.nodes[clip].body[2].chunk.name, data.nodes[clip])
                        for clip in chunk.chunk.clipsBottom:
                            extract_block_meshes(data.nodes[clip].body[2].chunk.name, data.nodes[clip])

        # if chunk.chunkId == 0x0315B009:
        #     for u01 in chunk.chunk.u01:
        #         print("\tu01: " + str(u01.u01))
        # if chunk.chunkId == 0x0315C001:
        #     for auto_terrain in chunk.chunk.autoTerrains:
        #         print("\tauto_terrain: " + str(auto_terrain))


def extract_block_meshes(file, data):
    for chunk in data.body:
        if chunk.chunkId == 0x0304E023:
            print("ground")
            extract_variant_chunk(
                f"./ExportObj/{file}/ground0/",
                file,
                data,
                chunk.chunk.variant_base_ground,
            )
            print("air")
            extract_variant_chunk(
                f"./ExportObj/{file}/air0/",
                file,
                data,
                chunk.chunk.variant_base_air,
            )

        if chunk.chunkId == 0x0304E027:
            for idx, additional_variant_ground in enumerate(chunk.chunk.additionalVariantsGround):
                print("additional_variant_ground: " + str(additional_variant_ground))
                extract_variant_chunk(
                    f"./ExportObj/{file}/ground{idx+1}/",
                    file,
                    data,
                    data.nodes[additional_variant_ground].body,
                )

        if chunk.chunkId == 0x0304E02C:
            for idx, additional_variant_air in enumerate(chunk.chunk.additionalVariantsAir):
                print("additional_variant_air: " + str(additional_variant_air))
                extract_variant_chunk(
                    f"./ExportObj/{file}/air{idx+1}/",
                    file,
                    data,
                    data.nodes[additional_variant_air].body,
                )


def extract_mobil2(result, filename, data, mobil_model):
    mobil = {}
    for chunk in mobil_model.body:
        if chunk.chunkId == 0x03122003:
            print("\t\t\tprefab_fid: " + str(chunk.chunk.prefab_fid))

            if chunk.chunk.prefab_fid < 0:
                continue

            prefab = data.nodes[chunk.chunk.prefab_fid]
            all_meshes = extract_meshes(prefab, prefab, extracted_files=result["extracted_files"])

            mobil = {
                "meshes": [],
            }

            for idx2, (filepath, meshes, all_pos, all_rot) in enumerate(all_meshes):
                filepath = filepath.replace(result["base_folder"], "")

                if meshes is not None:
                    for idx, obj_params in enumerate(meshes):
                        export_folder = result["export_folder"] + filepath + "\\"
                        if not os.path.exists(export_folder):
                            os.makedirs(export_folder)
                        obj_filepath = export_folder + f"mesh{idx}_lod{obj_params[-1]}.obj"
                        export_obj(obj_filepath, *obj_params)

                pos, quat = transform_final_pos(all_pos, all_rot)
                mobil["meshes"].append({"path": filepath, "pos": pos, "rot": quat})

    return mobil


def extract_variant_chunk2(result, filename, data, variant_model):
    mobils = {}
    blocks_units = []
    variant = {
        "mobils": mobils,
        "blocks_units": blocks_units,
    }

    for chunk in variant_model:
        if chunk.chunkId == 0x0315B003:
            print("\tsymmetrical_variant_index: " + str(chunk.chunk.symmetrical_variant_index))
            print("\tvariant_base_type: " + str(chunk.chunk.variant_base_type))
        if chunk.chunkId == 0x0315B005:
            for mobil_idx, mobil in enumerate(chunk.chunk.mobils):
                print("\tmobil" + str(mobil_idx))
                for sub_mobil_idx, sub_mobil in enumerate(mobil):
                    print("\t\tsub_mobil" + str(sub_mobil_idx))
                    mobils[f"mobil{mobil_idx}_submobil{sub_mobil_idx}"] = extract_mobil2(
                        result,
                        filename,
                        data,
                        data.nodes[sub_mobil],
                    )
        if chunk.chunkId == 0x0315B008:
            for block_unit_model_idx in chunk.chunk.blockUnitModels:
                block_unit = {}
                blocks_units.append(block_unit)

                print("\tblock_unit_model (contains clips): " + str(block_unit_model_idx))
                block_unit_model = data.nodes[block_unit_model_idx]

                for chunk in block_unit_model.body:
                    if chunk.chunkId == 0x03036000:
                        pos = chunk.chunk.relativeOffset
                        block_unit["pos"] = (pos.x, pos.y, pos.z)
                    if chunk.chunkId == 0x0303600C:
                        for prop in ("clipsNorth", "clipsEast", "clipsSouth", "clipsWest", "clipsTop", "clipsBottom"):
                            block_unit[prop] = []
                            for clip in chunk.chunk[prop]:
                                block_unit[prop].append(data.nodes[clip].filepath.replace(result["base_folder"], ""))

        # if chunk.chunkId == 0x0315B009:
        #     for u01 in chunk.chunk.u01:
        #         print("\tu01: " + str(u01.u01))
        # if chunk.chunkId == 0x0315C001:
        #     for auto_terrain in chunk.chunk.autoTerrains:
        #         print("\tauto_terrain: " + str(auto_terrain))

    return variant


def extract_block_meshes2(result, filename, data):
    variants = {}
    block = {
        "id": filename,
        "variants": variants,
    }

    for chunk in data.body:
        if chunk.chunkId == 0x0304E023:
            print("ground")
            variants["ground0"] = extract_variant_chunk2(
                result,
                filename,
                data,
                chunk.chunk.variant_base_ground,
            )
            print("air")
            variants["air0"] = extract_variant_chunk2(
                result,
                filename,
                data,
                chunk.chunk.variant_base_air,
            )

        if chunk.chunkId == 0x0304E027:
            for idx, additional_variant_ground in enumerate(chunk.chunk.additionalVariantsGround):
                print("additional_variant_ground: " + str(additional_variant_ground))
                variants[f"ground{idx+1}"] = extract_variant_chunk2(
                    result,
                    filename,
                    data,
                    data.nodes[additional_variant_ground].body,
                )

        if chunk.chunkId == 0x0304E02C:
            for idx, additional_variant_air in enumerate(chunk.chunk.additionalVariantsAir):
                print("additional_variant_air: " + str(additional_variant_air))
                variants[f"air{idx+1}"] = extract_variant_chunk2(
                    result,
                    filename,
                    data,
                    data.nodes[additional_variant_air].body,
                )

    return block
