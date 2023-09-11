import os

from construct import Container, ListContainer

from export_obj import export_ents


def extract_mobil(export_dir, file, data, mobil):
    for chunk in mobil.body:
        if chunk.chunk_id == 0x03122003:
            print("\t\t\tprefab_fid: " + str(chunk.chunk.prefab_fid))
            if chunk.chunk.prefab_fid > 0:
                export_ents(export_dir, file, data.nodes[chunk.chunk.prefab_fid])
            else:
                print(chunk.chunk)


def extract_variant_chunk(export_dir, file, data, variant):
    for chunk in variant:
        if chunk.chunk_id == 0x0315B003:
            print("\tsymmetrical_variant_index: " + str(chunk.chunk.symmetrical_variant_index))
            print("\tvariant_base_type: " + str(chunk.chunk.variant_base_type))
        if chunk.chunk_id == 0x0315B005:
            for mobil_idx, mobil in enumerate(chunk.chunk.mobils):
                print("\tmobil")
                for sub_mobil_idx, sub_mobil in enumerate(mobil):
                    print("\t\tsub_mobil")
                    extract_mobil(
                        export_dir + f"mobil{mobil_idx}/submobil{sub_mobil_idx}/",
                        file,
                        data,
                        data.nodes[sub_mobil],
                    )
        # if chunk.chunk_id == 0x0315B008:
        #     for block_unit_model_idx in chunk.chunk.blockUnitModels:
        #         print("\tblock_unit_model (contains clips): " + str(block_unit_model_idx))
        #         block_unit_model = data.nodes[block_unit_model_idx]
        #         for chunk in block_unit_model.body:
        #             if chunk.chunk_id == 0x0303600C:
        #                 for clip in chunk.chunk.clipsNorth:
        #                     extract_block_meshes(data.nodes[clip].body[2].chunk.string, data.nodes[clip])
        #                 for clip in chunk.chunk.clipsEast:
        #                     extract_block_meshes(data.nodes[clip].body[2].chunk.string, data.nodes[clip])
        #                 for clip in chunk.chunk.clipsSouth:
        #                     extract_block_meshes(data.nodes[clip].body[2].chunk.string, data.nodes[clip])
        #                 for clip in chunk.chunk.clipsWest:
        #                     extract_block_meshes(data.nodes[clip].body[2].chunk.string, data.nodes[clip])
        #                 for clip in chunk.chunk.clipsTop:
        #                     extract_block_meshes(data.nodes[clip].body[2].chunk.string, data.nodes[clip])
        #                 for clip in chunk.chunk.clipsBottom:
        #                     extract_block_meshes(data.nodes[clip].body[2].chunk.string, data.nodes[clip])

        # if chunk.chunk_id == 0x0315B009:
        #     for u01 in chunk.chunk.u01:
        #         print("\tu01: " + str(u01.u01))
        # if chunk.chunk_id == 0x0315C001:
        #     for auto_terrain in chunk.chunk.autoTerrains:
        #         print("\tauto_terrain: " + str(auto_terrain))


def extract_block_meshes(file, data):
    for chunk in data.body:
        if chunk is None:
            continue
        if chunk.chunk_id == 0x0304E023:
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

        if chunk.chunk_id == 0x0304E027:
            for idx, additional_variant_ground in enumerate(chunk.chunk.additionalVariantsGround):
                print("additional_variant_ground: " + str(additional_variant_ground))
                extract_variant_chunk(
                    f"./ExportObj/{file}/ground{idx+1}/",
                    file,
                    data,
                    data.nodes[additional_variant_ground].body,
                )

        if chunk.chunk_id == 0x0304E02C:
            for idx, additional_variant_air in enumerate(chunk.chunk.additionalVariantsAir):
                print("additional_variant_air: " + str(additional_variant_air))
                extract_variant_chunk(
                    f"./ExportObj/{file}/air{idx+1}/",
                    file,
                    data,
                    data.nodes[additional_variant_air].body,
                )
