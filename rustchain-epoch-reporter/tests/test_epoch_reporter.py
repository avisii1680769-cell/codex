import os
import tempfile
import unittest

import epoch_reporter as er


class EpochReporterTests(unittest.TestCase):
    def test_epoch_id(self):
        self.assertEqual(er.epoch_id({"epoch": 12}), "12")
        self.assertEqual(er.epoch_id({"current_epoch": "abc"}), "abc")

    def test_build_message(self):
        miners = [
            {"miner": "g4", "device_family": "PowerPC", "antiquity_multiplier": 2.5},
            {"miner": "m1", "device_family": "x86", "antiquity_multiplier": 1.0},
        ]
        msg = er.build_message({"epoch": 5, "reward": 1.5}, miners, "https://explorer")
        self.assertIn("Epoch 5 Complete", msg)
        self.assertIn("Active miners: 2", msg)
        self.assertIn("g4 (2.5x)", msg)

    def test_dedup_db(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "state.db")
            con = er.init_db(path)
            self.assertFalse(er.was_posted(con, "7"))
            er.mark_posted(con, "7")
            self.assertTrue(er.was_posted(con, "7"))
            con.close()

    def test_normalize_miners(self):
        self.assertEqual(er.normalize_miners(["a"])[0]["miner"], "a")
        self.assertEqual(er.normalize_miners({"miners": [{"miner": "b"}]})[0]["miner"], "b")


if __name__ == "__main__":
    unittest.main()
