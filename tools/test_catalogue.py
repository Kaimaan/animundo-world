#!/usr/bin/env python3
"""tools/catalogue.py's food gaps (game decision 0061): every published tile's
food check, grouped by what's missing, and the animals that eat nothing.

tests/tiles/n_412_301.json (the taiga biome's plants, clover among them) has
no gaps; given its own plant picks without clover, the mountain hare and the
vole miss clover there, as on the real tiles near Helsinki. A live overlay
(tools/published_tiles.py) adds its animals to the tile before the check.

Usage: python3 tools/test_catalogue.py
"""
import copy
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, HERE)
import catalogue  # noqa: E402
import check_tile  # noqa: E402
import published_tiles  # noqa: E402

with open(os.path.join(ROOT, "tests", "tiles", "n_412_301.json"), encoding="utf-8") as f:
    GOOD = json.load(f)


def without_clover(t, tid):
    t = copy.deepcopy(t)
    t["id"] = tid
    t["plants"] = {"cover": [{"id": "bilberry", "density": 0.2}, {"id": "lingonberry", "density": 0.05}]}
    t["requires"]["plants"] = ["bilberry", "lingonberry"]
    return t


class FoodGapsTest(unittest.TestCase):
    def setUp(self):
        self.tiles, self.index = published_tiles.tiles, published_tiles.index
        published_tiles.index = lambda: {}

    def tearDown(self):
        published_tiles.tiles, published_tiles.index = self.tiles, self.index

    def section(self, tiles):
        published_tiles.tiles = lambda: tiles
        return "\n".join(catalogue.Catalogue().gaps_section())

    def test_biome_plants_have_clover(self):
        self.assertEqual(check_tile.tile_food(GOOD), {"gaps": {}, "eats_nothing": []})

    def test_tile_picks_without_clover_are_a_gap(self):
        food = check_tile.tile_food(without_clover(GOOD, "n_412_301"))
        self.assertEqual(food["gaps"]["mountain_hare"], {"diet": ["clover"], "hunts": []})
        self.assertEqual(food["gaps"]["vole"]["diet"], ["clover"])
        self.assertEqual(food["eats_nothing"], [])

    def test_grouped_by_what_is_missing(self):
        page = self.section({"n_412_301": without_clover(GOOD, "n_412_301"), "n_412_302": without_clover(GOOD, "n_412_302"),
                             "n_412_303": copy.deepcopy(GOOD)})
        row = next(line for line in page.splitlines() if line.startswith("| `clover`"))
        self.assertIn("Mountain hare (2)", row)
        self.assertIn("n_412_301, n_412_302", row)
        self.assertTrue(row.endswith("| 2 | 4 | n_412_301, n_412_302 |"), row)
        self.assertIn("### Eats nothing", page)
        self.assertIn("_None._", page)

    def test_eats_nothing_is_listed(self):
        food = check_tile.tile_food   # no real tile has one: the section from a made-up food check
        check_tile.tile_food = lambda t: {"gaps": {"mountain_hare": {"diet": ["grass", "clover"], "hunts": []}},
                                          "eats_nothing": ["mountain_hare"]}
        try:
            page = self.section({"n_412_301": GOOD})
        finally:
            check_tile.tile_food = food
        self.assertIn("| n_412_301 | Mountain hare |", page)
        self.assertNotIn("_None._", page)
        self.assertIn("| `grass` | Mountain hare (1) | 1 | 1 | n_412_301 |", page)

    def test_overlay_adds_its_animals(self):
        t = without_clover(GOOD, "n_412_301")
        t["species"] = {"playable": ["fox"], "prey": ["frog"], "predators": ["fox"]}
        published_tiles.join(t, {"playable": ["mountain_hare"], "prey": ["mountain_hare"], "tiles": ["n_412_301"]})
        self.assertEqual(t["species"]["playable"], ["mountain_hare", "fox"])
        self.assertIn("mountain_hare", t["requires"]["animals"])
        self.assertIn("mountain_hare", check_tile.tile_food(t)["gaps"])


if __name__ == "__main__":
    unittest.main()
