# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install', 'openfire_custom')
class TestOFBaseCommon(TransactionCase):
    def setUp(self):
        super().setUp()

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.env = cls.env(
            context=dict(
                cls.env.context,
                tracking_disable=True,
            )
        )

        # Company data
        cls.company_fr = cls.create_company(
            {
                'name': "Openfire FR",
                'currency_id': cls.env.ref('base.EUR').id,
                'country_id': cls.env.ref('base.fr').id,
                'account_fiscal_country_id': cls.env.ref('base.fr').id,
            }
        )

        # Customer data
        cls.customer_a = cls.env['res.partner'].create(
            {
                'name': "Partner A",
                'company_id': cls.company_fr.id,
                'customer_rank': 1,
            }
        )
        cls.supplier_a = cls.env['res.partner'].create(
            {
                'name': "Supplier A",
                'company_id': cls.company_fr.id,
                'supplier_rank': 1,
            }
        )
        cls.supplier_b = cls.env['res.partner'].create(
            {
                'name': "Supplier B",
                'company_id': cls.company_fr.id,
                'supplier_rank': 1,
            }
        )

    @classmethod
    def create_company(cls, values):
        return cls.env['res.company'].create(values)

    @classmethod
    def create_partner(cls, values):
        if 'company_id' not in values:
            values['company_id'] = cls.company_fr.id
        return cls.env['res.partner'].create(values)
