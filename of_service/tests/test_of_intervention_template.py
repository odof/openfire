# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.addons.of_service.tests.common import TestOFServiceCommon


class TestPlanningInterventionTemplate(TestOFServiceCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.template1 = cls.env['of.planning.intervention.template'].create(
            {
                'name': 'Test Template 1',
                'code': 'TEST1',
                'type_id': False,
            }
        )
        cls.template2 = cls.env['of.planning.intervention.template'].create(
            {
                'name': 'Test Template 2',
                'code': 'TEST2',
                'type_id': cls.env.ref('of_service.of_service_request_type_maintenance').id,
            }
        )
        cls.template3 = cls.env['of.planning.intervention.template'].create(
            {
                'name': 'Test Template 3',
                'code': 'TEST3',
                'type_id': cls.env.ref('of_service.of_service_request_type_installation').id,
            }
        )

    def test_01_name_search(self):
        """Test the _name_search method"""

        # Search with type_id
        result = (
            self.env['of.planning.intervention.template']
            .with_context(of_search_by_type_id=self.env.ref('of_service.of_service_request_type_maintenance').id)
            .name_search(
                name='Test Template',
                args=[],
                operator='ilike',
                limit=None,
            )
        )
        self.assertEqual(result, [(self.template2.id, 'Test Template 2')])

        # Search without type_id
        result = (
            self.env['of.planning.intervention.template']
            .with_context(of_search_by_type_id=False)
            .name_search(name='Test Template', args=[], operator='ilike', limit=None)
        )
        expected_result = [
            (self.template1.id, 'Test Template 1'),
            (self.template2.id, 'Test Template 2'),
            (self.template3.id, 'Test Template 3'),
        ]
        self.assertEqual(result, expected_result)
