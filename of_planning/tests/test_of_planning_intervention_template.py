# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo.tests.common import Form

from odoo.addons.of_planning.tests.common import TestOFPlanningCommon


class TestPlanningInterventionTemplate(TestOFPlanningCommon):
    def test_01_template_task_change(self):
        """Test that the template lines are recomputed when the task changes"""
        template = self.env['of.planning.intervention.template'].create(
            {
                'name': 'Test Template',
                'code': 'TEST',
                'type_id': self.env.ref('of_service.of_service_request_type_installation').id,
            }
        )
        with Form(template) as template_form:
            template_form.task_id = self.task_installation

        self.assertEqual(template.task_id, self.task_installation)
        self.assertEqual(template.line_ids[0].product_id, self.product_wood_stove)
        self.assertRecordValues(
            template.line_ids,
            [
                {
                    'product_id': self.product_wood_stove.id,
                    'price_unit': self.product_wood_stove.lst_price,
                    'qty': 1,
                    'name': f"{self.product_wood_stove.name}",
                },
            ],
        )
