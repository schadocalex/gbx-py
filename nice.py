from src.nice.api import *

if __name__ == "__main__":
    item = AdvancedItem(
        author="schadocalex",
        name="MyItem",
        waypoint_type="None",
        icon_filepath=None,
        entities=[
            Mesh(
                loc=Loc((0, 0, 0), (1, 0, 0, 0)),
                mesh_filepath=r"C:\Users\schad\Documents\Trackmania\Items\NICE\Part1.Mesh.Gbx",
                # r"C:\Users\schad\Documents\Trackmania\Items\NICE\Part1.Shape.Gbx",
            ),
            Gate(
                loc=Loc((0, 0, 0), (1, 0, 0, 0)),
                shape_filepath=r"C:\Users\schad\Documents\Trackmania\Items\NICE\Part1.Shape.Gbx",
                gameplayId="ReactorBoost2",
            ),
        ],
    )

    item_bytes = item.generate()
    with open(r"C:\Users\schad\Documents\Trackmania\Items\nice.Item.Gbx", "wb") as f:
        f.write(item_bytes)
