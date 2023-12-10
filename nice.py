from src.nice.api import *

if __name__ == "__main__":
    item = AdvancedItem(
        author="schadocalex",
        name="MyItem",
        waypoint_type="None",
        icon_filepath=None,
        entities=[
            Mesh(
                loc=Loc(
                    (4.860170841217041, -12.169404029846191, 7.0),
                    (0.652657151222229, -0.013293812982738018, -0.16387097537517548, -0.7396000623703003),
                ),
                mesh_filepath=r"C:\Users\schad\Documents\Trackmania\Items\NICE\Part1.Mesh.Gbx",
                # r"C:\Users\schad\Documents\Trackmania\Items\NICE\Part1.Shape.Gbx",
            ),
            Mesh(
                loc=Loc(
                    (-5.0, 0, 2.0),
                    (0.5866422057151794, -0.6842648386955261, -0.4183301031589508, 0.11239420622587204),
                ),
                mesh_filepath=r"C:\Users\schad\Documents\Trackmania\Items\NICE\Part2.Mesh.Gbx",
                # r"C:\Users\schad\Documents\Trackmania\Items\NICE\Part1.Shape.Gbx",
            ),
            # Gate(
            #     loc=Loc((0, 0, 0), (1, 0, 0, 0)),
            #     shape_filepath=r"C:\Users\schad\Documents\Trackmania\Items\NICE\Part1.Shape.Gbx",
            #     gameplayId="ReactorBoost2",
            # ),
        ],
    )

    item_bytes = item.generate()
    with open(r"C:\Users\schad\Documents\Trackmania\Items\nice.Item.Gbx", "wb") as f:
        f.write(item_bytes)
