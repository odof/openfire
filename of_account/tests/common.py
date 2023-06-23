# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.fields import Command
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('post_install', '-at_install', 'openfire_custom')
class TestOFAccountCommon(TransactionCase):
    def setUp(self):
        super().setUp()

    @classmethod
    def create_company(cls, values):
        return cls.env["res.company"].create(values)

    @classmethod
    def create_product(cls, values):
        values.update({'type': 'consu', 'invoice_policy': 'order'})
        product_template = cls.env["product.template"].create(values)
        return product_template.product_variant_id

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(
            context=dict(
                cls.env.context,
                tracking_disable=True,
            )
        )
        # Company and accounting data
        coa = cls.env.ref('l10n_fr.l10n_fr_pcg_chart_template')
        cls.company_fr = cls.create_company(
            {
                'name': "Openfire FR",
                'currency_id': cls.env.ref('base.EUR').id,
                'country_id': cls.env.ref('base.fr').id,
            }
        )
        cls.env.user.company_ids |= cls.company_fr
        cls.env.user.company_id = cls.company_fr.id
        coa.try_loading(company=cls.env.user.company_id)

        # Taxe data and fiscal position data
        cls.tax_base, cls.tax_5_5, cls.tax_10, cls.tax_20 = cls.env['account.tax'].create(
            [
                {
                    'name': 'Test base tax',
                    'type_tax_use': 'sale',
                    'price_include': False,
                    'amount': 5.5,
                    'company_id': cls.company_fr.id,
                },
                {
                    'name': 'Test 5.5% tax',
                    'type_tax_use': 'sale',
                    'price_include': False,
                    'amount': 5.5,
                    'company_id': cls.company_fr.id,
                },
                {
                    'name': 'Test 10.0% tax',
                    'type_tax_use': 'sale',
                    'price_include': False,
                    'amount': 10.0,
                    'company_id': cls.company_fr.id,
                },
                {
                    'name': 'Test 20.0% tax',
                    'type_tax_use': 'sale',
                    'price_include': False,
                    'amount': 20.0,
                    'company_id': cls.company_fr.id,
                },
            ]
        )

        cls.fiscal_pos_5_5, cls.fiscal_pos_10, cls.fiscal_pos_20 = cls.env['account.fiscal.position'].create(
            [
                {
                    'name': "Test Fiscal Position 5.5 %",
                    'auto_apply': True,
                    'country_id': cls.env.ref('base.fr').id,
                    'tax_ids': [Command.create({'tax_src_id': cls.tax_base.id, 'tax_dest_id': cls.tax_5_5.id})],
                },
                {
                    'name': "Test Fiscal Position 10.0 %",
                    'auto_apply': True,
                    'country_id': cls.env.ref('base.fr').id,
                    'tax_ids': [Command.create({'tax_src_id': cls.tax_base.id, 'tax_dest_id': cls.tax_10.id})],
                },
                {
                    'name': "Test Fiscal Position 20.0 %",
                    'auto_apply': True,
                    'country_id': cls.env.ref('base.fr').id,
                    'tax_ids': [Command.create({'tax_src_id': cls.tax_base.id, 'tax_dest_id': cls.tax_20.id})],
                },
            ]
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
