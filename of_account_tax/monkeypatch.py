# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command, models

from odoo.addons.account.models.chart_template import AccountChartTemplate


# We are 🐒-patching the following methods :
#    - account.chart.template._load_template() : added the creation of account mappings on taxes
#    - account.chart.template.generate_fiscal_position() : changed the creation of fiscal positions to add the default
#       taxes on the fiscal position.
class OfAccountTaxHooks(models.AbstractModel):
    '''When you use monkey patching, the code is executed when the module
    is in the addons_path of the Odoo server, even is the module is not
    installed ! In order to avoid the side-effects it can create,
    we create an AbstractModel inside the module and we test the
    availability of this Model in the code of the monkey patching below.
    '''

    _name = 'of.account.tax.hooks.installed'
    __doc__ = "This model is used to test if the module is installed and avoid monkey patching side-effects."


_load_template_origin = AccountChartTemplate._load_template
generate_fiscal_position_origin = AccountChartTemplate.generate_fiscal_position


def _load_template(self, company, code_digits=None, account_ref=None, taxes_ref=None):
    """Override of the original method to add the creation of account mappings on taxes."""
    if self.env.get('of.account.tax.hooks.installed') is None:
        return _load_template_origin(self, company, code_digits, account_ref, taxes_ref)

    self.ensure_one()
    if account_ref is None:
        account_ref = {}
    if taxes_ref is None:
        taxes_ref = {}
    if not code_digits:
        code_digits = self.code_digits

    # Generate taxes from templates.
    generated_tax_res = self.with_context(active_test=False).tax_template_ids._generate_tax(company)
    taxes_ref.update(generated_tax_res['tax_template_to_tax'])

    # Generating Accounts from templates.
    account_template_ref = self.generate_account(taxes_ref, account_ref, code_digits, company)
    account_ref.update(account_template_ref)

    # Generate account groups, from template
    self.generate_account_groups(company)

    # OF : Writing tax values after creation of taxes and accounts
    for key, value in taxes_ref.items():
        if key.of_account_ids:
            value.write(
                {
                    'of_account_ids': [
                        Command.create(
                            {
                                'account_src_id': account_template_ref[t.account_src_id].id,
                                'account_dest_id': account_template_ref[t.account_dest_id].id,
                            }
                        )
                        for t in key.of_account_ids
                    ]
                }
            )
    # End OF : Writing tax values after creation of taxes and accounts

    # writing account values after creation of accounts
    for tax, value in generated_tax_res['account_dict']['account.tax'].items():
        if value['cash_basis_transition_account_id']:
            tax.cash_basis_transition_account_id = account_ref.get(value['cash_basis_transition_account_id'])

    for repartition_line, value in generated_tax_res['account_dict']['account.tax.repartition.line'].items():
        if value['account_id']:
            repartition_line.account_id = account_ref.get(value['account_id'])

    # Set the company accounts
    self._load_company_accounts(account_ref, company)

    # Create Journals - Only done for root chart template
    if not self.parent_id:
        self.generate_journals(account_ref, company)

    # generate properties function
    self.generate_properties(account_ref, company)

    # Generate Fiscal Position , Fiscal Position Accounts and Fiscal Position Taxes from templates
    self.generate_fiscal_position(taxes_ref, account_ref, company)

    # Generate account operation template templates
    self.generate_account_reconcile_model(taxes_ref, account_ref, company)

    return account_ref, taxes_ref


def generate_fiscal_position(self, tax_template_ref, acc_template_ref, company):
    """Override of the original method to change the creation of fiscal positions.
    We changed the method definition to add the tax_template_ref parameter to add default taxes on fiscal positions.
    """
    if self.env.get('of.account.tax.hooks.installed') is None:
        return generate_fiscal_position_origin(self, tax_template_ref, acc_template_ref, company)

    self.ensure_one()
    positions = self.env['account.fiscal.position.template'].search([('chart_template_id', '=', self.id)])

    # first create fiscal positions in batch
    template_vals = []
    for position in positions:
        # OF : Adding the tax_template_ref parameter
        fp_vals = self.with_context(tax_template_ref=tax_template_ref)._get_fp_vals(company, position)
        # End OF : Adding the tax_template_ref parameter
        template_vals.append((position, fp_vals))
    fps = self._create_records_with_xmlid('account.fiscal.position', template_vals, company)

    # then create fiscal position taxes and accounts
    tax_template_vals = []
    account_template_vals = []
    for position, fp in zip(positions, fps):
        for tax in position.tax_ids:
            tax_template_vals.append(
                (
                    tax,
                    {
                        'tax_src_id': tax_template_ref[tax.tax_src_id].id,
                        'tax_dest_id': tax.tax_dest_id and tax_template_ref[tax.tax_dest_id].id or False,
                        'position_id': fp.id,
                    },
                )
            )
        for acc in position.account_ids:
            account_template_vals.append(
                (
                    acc,
                    {
                        'account_src_id': acc_template_ref[acc.account_src_id].id,
                        'account_dest_id': acc_template_ref[acc.account_dest_id].id,
                        'position_id': fp.id,
                    },
                )
            )
    self._create_records_with_xmlid('account.fiscal.position.tax', tax_template_vals, company)
    self._create_records_with_xmlid('account.fiscal.position.account', account_template_vals, company)

    return True


AccountChartTemplate._load_template = _load_template
AccountChartTemplate.generate_fiscal_position = generate_fiscal_position
