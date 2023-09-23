from src.nice.api import *

if __name__ == "__main__":
    item = AdvancedItem(
        author="schadocalex",
        name="MyItem",
        waypoint_type="None",
        icon_filepath=None,
        entities=[
            Mesh(r"C:\Users\schad\Documents\Trackmania\Items\NICE\Part1.Mesh.Gbx"),
        ],
    )

    item_bytes = item.generate()
    with open(r"C:\Users\schad\Documents\Trackmania\Items\nice.Item.Gbx", "wb") as f:
        f.write(item_bytes)
