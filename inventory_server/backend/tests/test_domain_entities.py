import unittest
from datetime import datetime

from domain.entities import Order


class DomainEntityTests(unittest.TestCase):
    def test_order_serialization_exposes_station_identity(self):
        order = Order(
            order_id="WS5_001",
            station_id="station-5",
            station_display_name="WS-05",
            side="L",
            creation_time=datetime(2026, 4, 2, 10, 0, 0),
            urgent=True,
            items_dict={"Motor": 2},
            source="web_workstation",
        )

        payload = order.to_dict()

        self.assertEqual(payload["station_id"], "station-5")
        self.assertEqual(payload["original_ws_id"], "station-5")
        self.assertEqual(payload["ws_id"], "station-5")
        self.assertEqual(payload["display_name"], "WS-05")
        self.assertEqual(payload["items_dict"], {"Motor": 2})


if __name__ == "__main__":
    unittest.main()
