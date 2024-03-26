import os
import json


FILENAME = "chekanshchiki_temp.json"

if 0 == 0:
    if FILENAME in os.walk(".."):
        os.remove(FILENAME)
    json_data = {"market": [0] * 100}
else:
    with open(FILENAME, "r", encoding="utf-8") as file:
        json_data = json.load(file)


with open(FILENAME, "w", encoding="utf-8") as file:
    json.dump(json_data, file, indent=4)
