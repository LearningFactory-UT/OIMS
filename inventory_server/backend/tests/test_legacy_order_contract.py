import unittest

from contracts.legacy_order import build_legacy_order_payload


class LegacyOrderContractTests(unittest.TestCase):
    def test_legacy_payload_uses_original_order_shape(self):
        order = {
            "order_id": "WS5_001",
            "station_id": "5",
            "side": "L",
            "urgent": True,
            "items_dict": {"Motor": 2, "Battery": 1},
        }

        self.assertEqual(
            build_legacy_order_payload(order),
            {
                "items": {"Motor": 2, "Battery": 1},
                "attributes": {
                    "ws_id": "5",
                    "operator_side": "L",
                    "urgent": True,
                    "order_id": "WS5_001",
                },
            },
        )


if __name__ == "__main__":
    unittest.main()
