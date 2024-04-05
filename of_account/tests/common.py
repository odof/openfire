# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.fields import Command

from odoo.addons.of_product_brand.tests.common import TestOFProductCommon


class TestOFAccountCommon(TestOFProductCommon):
    @classmethod
    def _prepare_product_values(cls, values):
        if 'categ_id' not in values:
            values['categ_id'] = cls.product_category_a.id
        if 'standard_price' not in values:
            values['standard_price'] = 40
        if 'list_price' not in values:
            values['list_price'] = 100
        if 'type' not in values:
            values['type'] = 'consu'
        if 'weight' not in values:
            values['weight'] = 0.01
        if 'uom_id' not in values:
            values['uom_id'] = cls.env.ref('uom.product_uom_unit').id
        if 'uom_po_id' not in values:
            values['uom_po_id'] = cls.env.ref('uom.product_uom_unit').id
        if 'brand_id' not in values:
            values['brand_id'] = cls.product_brand_a.id
            values['default_code'] = f'{cls.product_brand_a.code}_' + values['default_code']
        if 'invoice_policy' not in values:
            values['invoice_policy'] = 'order'
        if 'expense_policy' not in values:
            values['expense_policy'] = 'cost'
        if 'taxes_id' not in values:
            values['taxes_id'] = [Command.set([cls.tax_base.id])]
        if 'supplier_taxes_id' not in values:
            values['supplier_taxes_id'] = [Command.set([])]
        return values

    @classmethod
    def create_product(cls, values):
        values = cls._prepare_product_values(values)
        product_template = cls.env['product.template'].create(values)
        return product_template.product_variant_id

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
        # Company and accounting data
        coa = cls.env.ref('l10n_fr.l10n_fr_pcg_chart_template')
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
        cls.company_fr.account_sale_tax_id = cls.tax_base

        cls.fiscal_pos_5_5, cls.fiscal_pos_10, cls.fiscal_pos_20 = cls.env['account.fiscal.position'].create(
            [
                {
                    'name': "Test Fiscal Position 5.5 %",
                    'auto_apply': True,
                    'country_id': cls.env.ref('base.fr').id,
                    'tax_ids': [Command.create({'tax_src_id': cls.tax_base.id, 'tax_dest_id': cls.tax_5_5.id})],
                    'company_id': cls.company_fr.id,
                },
                {
                    'name': "Test Fiscal Position 10.0 %",
                    'auto_apply': True,
                    'country_id': cls.env.ref('base.fr').id,
                    'tax_ids': [Command.create({'tax_src_id': cls.tax_base.id, 'tax_dest_id': cls.tax_10.id})],
                    'company_id': cls.company_fr.id,
                },
                {
                    'name': "Test Fiscal Position 20.0 %",
                    'auto_apply': True,
                    'country_id': cls.env.ref('base.fr').id,
                    'tax_ids': [Command.create({'tax_src_id': cls.tax_base.id, 'tax_dest_id': cls.tax_20.id})],
                    'company_id': cls.company_fr.id,
                },
            ]
        )

        # Price list data
        cls.default_pricelist = (
            cls.env['product.pricelist']
            .with_company(cls.company_fr)
            .create(
                {
                    'name': 'Default pricelist (EUR)',
                    'currency_id': cls.company_fr.currency_id.id,
                }
            )
        )

        # Product data
        cls.product_consu_a = cls.create_product(
            {
                'name': 'Product Consu A',
                'default_code': 'PCA_123',
                'standard_price': 40,
                'list_price': 100,
            }
        )
        cls.product_consu_b = cls.create_product(
            {
                'name': 'Product Consu B',
                'default_code': 'PCA_456',
                'standard_price': 19.99,
                'list_price': 29.99,
            }
        )

        # Journal data
        cls.journal_purchase = cls.env['account.journal'].search(
            [('type', '=', 'purchase'), ('company_id', '=', cls.company_fr.id)], limit=1
        )
        cls.journal_sale = cls.env['account.journal'].search(
            [('type', '=', 'sale'), ('company_id', '=', cls.company_fr.id)], limit=1
        )
        cls.journal_bank = cls.env['account.journal'].search(
            [('type', '=', 'bank'), ('company_id', '=', cls.company_fr.id)], limit=1
        )

        # User data
        cls.user_accountant = cls.env['res.users'].create(
            {
                'name': 'user_accountant',
                'login': 'user_accountant',
                'email': 'user_accountant@openfire.fr',
                'groups_id': [
                    Command.set(
                        [
                            cls.env.ref('account.group_account_manager').id,
                            cls.env.ref('base.group_partner_manager').id,
                            cls.env.ref('sales_team.group_sale_salesman').id,
                        ]
                    )
                ],
                'company_id': cls.company_fr.id,
            }
        )
