# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.addons.of_planning_tour.tests.common import TestOFPlanningTourCommon


class TestOFPlanningTask(TestOFPlanningTourCommon):
    def setUp(self):
        super().setUp()

    def test_01_get_minimal_task_duration(self):
        """Check that the minimal task duration is correct."""
        task_obj = self.env['of.planning.task']
        self.task_sweeping.unlink()
        self.task_installation.unlink()

        self.assertEqual(task_obj._get_minimal_task_duration(), 0)

        self.task_1 = task_obj.create(
            {
                'name': 'Task 1',
                'duration': 1,
            }
        )

        self.assertEqual(task_obj._get_minimal_task_duration(), 1)

        self.task_2 = task_obj.create(
            {
                'name': 'Task 2',
                'duration': 2,
            }
        )

        self.assertEqual(task_obj._get_minimal_task_duration(), 1)

        self.task_1.duration = 3

        self.assertEqual(task_obj._get_minimal_task_duration(), 2)

        self.task_2.unlink()

        self.assertEqual(task_obj._get_minimal_task_duration(), 3)
