import unittest

from domain.andon import AndonInputs, derive_andon_state


class AndonStateTests(unittest.TestCase):
    def test_idle_when_timer_not_running(self):
        state = derive_andon_state(
            AndonInputs(
                station_id="station-1",
                side="L",
                timer_running=False,
                enabled=True,
                manual_state="reset",
                pending_orders=2,
                urgent_orders=1,
                help_requested=False,
                help_idle=False,
                waiting_from_previous=False,
                waiting_from_previous_idle=False,
                ready_for_next=False,
            )
        )

        self.assertEqual(state.code, "R")

    def test_active_green_with_suffixes(self):
        state = derive_andon_state(
            AndonInputs(
                station_id="station-1",
                side="R",
                timer_running=True,
                enabled=True,
                manual_state="start",
                pending_orders=1,
                urgent_orders=0,
                help_requested=True,
                help_idle=False,
                waiting_from_previous=True,
                waiting_from_previous_idle=False,
                ready_for_next=True,
            )
        )

        self.assertEqual(state.code, "GgYbB")

    def test_manual_stop_forces_red_base(self):
        state = derive_andon_state(
            AndonInputs(
                station_id="station-1",
                side="L",
                timer_running=True,
                enabled=True,
                manual_state="stop",
                pending_orders=1,
                urgent_orders=0,
                help_requested=False,
                help_idle=False,
                waiting_from_previous=False,
                waiting_from_previous_idle=False,
                ready_for_next=False,
            )
        )

        self.assertEqual(state.code, "RB")

    def test_running_timer_with_no_active_flags_defaults_to_green(self):
        state = derive_andon_state(
            AndonInputs(
                station_id="station-1",
                side="R",
                timer_running=True,
                enabled=True,
                manual_state="reset",
                pending_orders=0,
                urgent_orders=0,
                help_requested=False,
                help_idle=False,
                waiting_from_previous=False,
                waiting_from_previous_idle=False,
                ready_for_next=False,
            )
        )

        self.assertEqual(state.code, "G")


if __name__ == "__main__":
    unittest.main()
