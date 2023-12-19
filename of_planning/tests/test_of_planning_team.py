# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import datetime

import pytz

from odoo.addons.of_planning.tests.common import TestOFPlanningCommon


class TestOfPlanningTeam(TestOFPlanningCommon):
    def test_compute_tz_offset(self):
        """Test that the tz_offset is correctly computed"""
        team = self.env['of.planning.team'].create({'name': 'Team 1', 'tz': 'Europe/Paris'})
        team._compute_tz_offset()
        self.assertEqual(team.tz_offset, datetime.now(pytz.timezone('Europe/Paris')).strftime('%z'))
