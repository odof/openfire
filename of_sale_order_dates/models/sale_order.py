# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    of_requested_week = fields.Char(string="Requested week", compute='_compute_of_requested_week')

    @api.depends('commitment_date', 'expected_date')
    def _compute_of_requested_week(self):
        for order in self:
            requested_date = order.commitment_date or order.expected_date
            if requested_date:
                requested_date_dt = fields.Datetime.to_datetime(requested_date)
                tz_requested_date = fields.Datetime.context_timestamp(order, requested_date_dt)
                order.of_requested_week = "%s - S%02d" % (
                    tz_requested_date.year,
                    tz_requested_date.date().isocalendar()[1],
                )
            else:
                order.of_requested_week = ""

    def pdf_requested_week(self):
        # Pour éviter de créer un module intermédiaire entre of_sale_external et of_sale_order_dates,
        # on teste la présence d'un champ créé dans of_sale_external
        if 'of_report_template_id' in self.env['sale.order']._fields and self.of_report_template_id:
            return self.of_report_template_id.pdf_requested_week
        else:
            return self.env['ir.config_parameter'].sudo().get_param('of.sale.order.dates.pdf_requested_week')
