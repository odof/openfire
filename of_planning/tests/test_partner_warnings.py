# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command

from odoo.addons.of_planning.tests.common import TestOFPlanningCommon


class TestOFPartnerWarning(TestOFPlanningCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner_with_warning = cls.env['res.partner'].create(
            {
                'name': 'Partner with warning',
                'of_is_intervention_warn': True,
                'invoice_warn_msg': 'This is a warning message',
            }
        )

    def test_01_no_partner_warning(self):
        event = self.env['calendar.event'].create(
            {
                'name': 'Test Intervention',
                'of_type': 'intervention',
                'of_partner_id': self.customer_a.id,
            }
        )
        res = event._onchange_partner_id_warning()
        self.assertEqual(res, None)

    def test_02_partner_warning(self):
        self._create_assert_calendar_event()

    def test_03_partner_blocking_warning(self):
        self.partner_with_warning.of_warn_block = True
        event = self._create_assert_calendar_event()
        self.assertEqual(event.of_partner_id, self.env['res.partner'].browse())

    def _create_assert_calendar_event(self):
        event = self.env['calendar.event'].create(
            {
                'name': 'Test Intervention',
                'of_type': 'intervention',
                'of_partner_id': self.partner_with_warning.id,
                'of_employee_ids': [Command.set([self.employee_tech_johnny.id])],
            }
        )
        res = event._onchange_partner_id_warning()
        self.assertEqual(res['warning']['message'], 'This is a warning message')
        return event
