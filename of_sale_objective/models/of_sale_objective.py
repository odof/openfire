# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models

DEFAULT_YEARS_RANGE = '2020;2031'


class OFSaleObjective(models.Model):
    """Monthly sales objective"""

    @api.model
    def _get_default_years_range(self):
        range_str = (
            self.env['ir.config_parameter'].sudo().get_param('of_sale_objective.years_range', DEFAULT_YEARS_RANGE)
        )
        if (
            ';' not in range_str
            or len(range_str.split(';')) != 2
            or not range_str.split(';')[0].isdigit()
            or not range_str.split(';')[1].isdigit()
        ):
            range_str = DEFAULT_YEARS_RANGE
        range_start, range_stop = range_str.split(';')
        return [(str(i), str(i)) for i in range(int(range_start), int(range_stop) + 1)]

    _name = 'of.sale.objective'
    _description = __doc__
    _order = 'year desc, month desc'

    company_id = fields.Many2one(comodel_name='res.company', string="Shop", required=True)
    month = fields.Selection(
        selection=[
            ('01', "January"),
            ('02', "February"),
            ('03', "March"),
            ('04', "April"),
            ('05', "May"),
            ('06', "June"),
            ('07', "July"),
            ('08', "August"),
            ('09', "September"),
            ('10', "October"),
            ('11', "November"),
            ('12', "December"),
        ],
        required=True,
    )
    year = fields.Selection(selection=lambda self: self._get_default_years_range(), required=True)
    objective_line_ids = fields.One2many(
        comodel_name='of.sale.objective.line', inverse_name='objective_id', string="Objective lines"
    )
    objective_date = fields.Date(string="Date")

    def name_get(self):
        return [(obj.id, f'{obj.company_id.name} - {obj.month} {obj.year}') for obj in self]
