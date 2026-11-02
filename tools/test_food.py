#!/usr/bin/env python3
"""Tests for tools/food.py: food worked out from what grows and lives there."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import food  # noqa: E402
import layers  # noqa: E402

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")


class EatsRuleTest(unittest.TestCase):
    """food/eats-cases.json: the cases every copy of the food rule runs (0061)."""

    def test_cases(self):
        cases = food.load(os.path.join(ROOT, "food", "eats-cases.json"))["cases"]
        for c in cases:
            args = (c["diet"], c["hunts"], set(c["food"]), set(c["prey_tags"]))
            self.assertEqual(food.eats_here(*args), c["eats"], c["name"])
            self.assertEqual(food.food_gaps(*args), c["gaps"], c["name"])


class FoodTest(unittest.TestCase):
    def made(self, rel):
        return food.derive(layers.resolve(food.load(os.path.join(ROOT, rel))))[0]

    def test_nuuksio_animals_all_eat_something(self):
        d = layers.resolve(food.load(os.path.join(ROOT, "regions", "fi_nuuksio.json")))
        made = set(food.derive(d)[0]) | {"nectar"}
        living = food.animals_of(d)
        for a in living:
            tags = {t for b in living if b != a for t in food.ANIMALS.get(b, {}).get("tags", []) or []}
            spec = food.ANIMALS[a]
            self.assertTrue(food.eats_here(spec.get("diet"), spec.get("hunts"), made, tags), f"{a} eats nothing in Nuuksio")

    def test_food_names_come_from_the_plants(self):
        made = self.made("regions/fi_nuuksio.json")
        self.assertIn("bilberries", made["berries"]["names"])
        self.assertIn("spruce seeds", made["seeds"]["names"])
        self.assertIn("birch bark", made["bark"]["names"])

    def test_sea_717_berries_are_rowan_not_bird_cherry(self):
        made = self.made("homes/sea_717.json")
        self.assertEqual(made["berries"]["names"], ["rowan berries"])

    def test_large_animals_leave_carrion(self):
        made = food.derive({"animals": {"playable": ["moose"]}})[0]
        self.assertEqual(made["carrion"]["names"], ["moose remains"])

    def test_no_water_no_water_bugs(self):
        made = food.derive({"habitat": "savanna", "terrain": {"edge": "none", "lakes": 0}})[0]
        self.assertNotIn("water_bugs", made)
        self.assertIn("insects", made)


if __name__ == "__main__":
    unittest.main()


class LayeredPlaceTest(unittest.TestCase):
    def test_nuuksio_resolves_to_its_land_style_and_plants(self):
        raw = food.load(os.path.join(ROOT, "regions", "fi_nuuksio.json"))
        r = layers.resolve(raw)
        self.assertNotIn("palette", raw)
        self.assertEqual(r["palette"], layers.land("boreal")["palette"])
        self.assertEqual([t["plant"] for t in r["trees"]["mix"]], ["norway_spruce", "scots_pine", "birch", "aspen", "rowan"])
        self.assertEqual(r["ground_cover"]["plants"][0]["model"], "bilberry")
        self.assertEqual(r["ground_cover"]["plants"][0]["food"], {"kind": "berries", "part": "berry"})
        self.assertIn("ground beetle", {f["kind"]: f for f in r["food"]}["insects"]["names"])
