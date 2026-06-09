import unittest
from unittest.mock import Mock, patch

try:
    from services.inventory_service import InventoryService
except ModuleNotFoundError as error:
    if error.name != "sqlalchemy":
        raise
    InventoryService = None


@unittest.skipIf(InventoryService is None, "backend service dependencies are not installed")
class LightweightSnapshotTests(unittest.TestCase):
    def test_orders_snapshot_avoids_station_payloads(self):
        service = InventoryService.__new__(InventoryService)
        service.assembly_type = "standard"
        service.get_active_orders = Mock(
            return_value=[
                {"order_id": "WS2_001", "station_id": "2", "urgent": True},
                {"order_id": "WS3_001", "station_id": "3", "urgent": False},
            ]
        )

        timer_service = Mock()
        timer_service.snapshot.return_value.to_dict.return_value = {"state": "running"}

        with patch("services.timer_service.TimerService.get_instance", return_value=timer_service):
            snapshot = service.get_orders_state_snapshot()

        self.assertEqual(snapshot["timer"], {"state": "running"})
        self.assertEqual(snapshot["orders"], service.get_active_orders.return_value)
        self.assertEqual(snapshot["stations"], [])
        self.assertEqual(snapshot["summary"]["active_orders"], 2)
        self.assertEqual(snapshot["summary"]["urgent_orders"], 1)

    def test_tablet_snapshot_limits_state_to_bound_station(self):
        service = InventoryService.__new__(InventoryService)
        service.assembly_type = "standard"
        service.get_station_state = Mock(
            return_value={
                "station_id": "2",
                "display_name": "Assembly 2",
                "active_orders": [
                    {"order_id": "WS2_001", "station_id": "2", "urgent": False}
                ],
            }
        )

        timer_service = Mock()
        timer_service.snapshot.return_value.to_dict.return_value = {"state": "paused"}

        with patch("services.timer_service.TimerService.get_instance", return_value=timer_service):
            snapshot = service.get_tablet_state_snapshot("2")

        self.assertEqual(snapshot["timer"], {"state": "paused"})
        self.assertEqual(snapshot["stations"], [service.get_station_state.return_value])
        self.assertEqual(snapshot["orders"], service.get_station_state.return_value["active_orders"])
        self.assertEqual(snapshot["summary"]["active_orders"], 1)
        service.get_station_state.assert_called_once_with("2")


if __name__ == "__main__":
    unittest.main()
