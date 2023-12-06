# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command, api, fields, models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    of_display_name = fields.Text(string="Display name for reports", compute='_compute_of_display_name')
    of_product_attachment_domain_ids = fields.One2many(
        comodel_name='ir.attachment',
        string="Product attachments domain",
        compute='_compute_of_product_attachment_domain_ids',
    )
    of_product_attachment_ids = fields.Many2many(
        comodel_name='ir.attachment',
        string="Product attachments",
        compute='_compute_of_product_attachment_ids',
        readonly=False,
        store=True,
        domain="[('id', 'in', of_product_attachment_domain_ids)]",
    )

    def _compute_of_display_name(self):
        # Inhiber l'affichage de la référence
        display_ref = self.company_id.pdf_product_reference
        for line in self:
            name = line.with_context(lang=line.order_id.partner_id.lang, partner=line.order_id.partner_id.id).name
            if not display_ref and name.startswith("["):
                splitted = name.split("]")
                if len(splitted) > 1:
                    splitted.pop(0)
                    name = ']'.join(splitted).strip()
            line.of_display_name = name

    @api.depends('product_id')
    def _compute_of_product_attachment_domain_ids(self):
        if self.env.user.has_group('of_sale_report_setting.group_of_sale_report_print_attachment'):
            for line in self:
                product_ids = self.env['product.product'].search(
                    [('product_tmpl_id', '=', line.product_template_id.id)]
                )
                domain = [
                    '&',
                    ('mimetype', '=', 'application/pdf'),
                    '|',
                    '&',
                    ('res_model', '=', 'product.template'),
                    ('res_id', '=', line.product_template_id.id),
                    '&',
                    ('res_model', '=', 'product.product'),
                    ('res_id', 'in', product_ids.ids),
                ]
                attachments = self.env['ir.attachment'].search(domain)
                line.of_product_attachment_domain_ids = attachments
        else:
            for line in self:
                line.of_product_attachment_domain_ids = False

    @api.depends('product_id')
    def _compute_of_product_attachment_ids(self):
        if self.env.user.has_group('of_sale_report_setting.group_of_sale_report_print_attachment'):
            for line in self:
                attachment_ids = self.env['ir.attachment'].search(
                    [('id', 'in', line.of_product_attachment_domain_ids.ids)]
                )
                line.of_product_attachment_ids = [Command.set(attachment_ids.ids)]
        else:
            for line in self:
                line.of_product_attachment_ids = False
