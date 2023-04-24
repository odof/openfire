# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models

from odoo.addons.base.models.res_partner import WARNING_HELP


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # invoice_warn and invoice_warn_msg are now shared between invoices, sales and interventions
    of_is_account_warn = fields.Boolean(string="Invoices warning")  # TODO: move me to `of_account` when is migrated
    of_is_warn = fields.Boolean(  # TODO: move me to `of_account` when its migrated
        string="Warning on at least one object", compute='_compute_of_is_warn', store=True
    )
    invoice_warn = fields.Selection(  # TODO: move me to `of_account` when its migrated
        help="Warning type", compute='_compute_invoice_warn', store=True
    )
    of_warn_block = fields.Boolean(string="Blocking")  # TODO: Move me to `of_account` when is migrated
    sale_warn = fields.Selection(related='invoice_warn', help=WARNING_HELP, readonly=True)
    sale_warn_msg = fields.Text(related='invoice_warn_msg', readonly=True)
    of_is_sale_warn = fields.Boolean(string="Sales warning")
    of_invoice_policy = fields.Selection(
        selection=[('order', "Ordered quantities"), ('delivery', "Delivered quantities")],
        string="Invoicing policy",
    )

    # TODO: Move me to `of_account` when is migrated
    # @api.depends('of_is_account_warn')  # TODO: uncomment me when `of_account` is migrated
    @api.depends('of_is_account_warn', 'of_is_sale_warn')  # TODO: delete me when `of_account` is migrated
    def _compute_of_is_warn(self):
        """This function should be inherited in childs module"""
        # TODO: Delete this part and uncomment the function corresponding function in `of_sale` when `of_account`
        # is migrated
        has_warn = self.filtered('of_is_sale_warn')
        for partner in has_warn:
            partner.of_is_warn = True
        partners_left = self - has_warn
        # End of : TODO Delete this part and uncomment the function below when `of_account` is migrated
        # has_warn = self.filtered('of_is_account_warn')  # TODO: uncomment me when `of_account` is migrated
        has_warn = partners_left.filtered('of_is_account_warn')  # TODO: delete me when `of_account` is migrated
        for partner in has_warn:
            partner.of_is_warn = True
        # no_warn = self - has_warn  # TODO: uncomment me when `of_account` is migrated
        no_warn = partners_left - has_warn  # TODO: delete me when `of_account` is migrated
        for partner in no_warn:
            partner.of_is_warn = False

    # End of : TODO: Move me to `of_account` when is migrated

    # TODO: Move me to `of_account` when its migrated
    @api.depends('of_warn_block', 'of_is_warn')
    def _compute_invoice_warn(self):
        """Keep this field up to date so that the existing in `account` and `sale` modules continues to work"""
        has_warn = self.filtered('of_is_warn')
        no_warn = self - has_warn
        for partner in no_warn:
            partner.invoice_warn = 'no-message'
        for partner in has_warn:
            partner.invoice_warn = 'block' if partner.of_warn_block else 'warning'

    # End of TODO: Move me to `of_account` is migrated

    # TODO: Uncomment me and when `of_account` is migrated
    # @api.depends('of_is_sale_warn')
    # def _compute_of_is_warn(self):
    #     has_warn = self.filtered('of_is_sale_warn')
    #     for partner in has_warn:
    #         partner.of_is_warn = True
    #     partners_left = self - has_warn
    #     super(ResPartner, partners_left)._compute_of_is_warn()
    # End of TODO: Uncomment me and when `of_account` is migrated
