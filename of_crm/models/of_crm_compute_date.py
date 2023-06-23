# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class OFCRMComputeDate(models.Model):
    """This model is used to compute a date for an activity linked to a model. It allows specifying a field
    that will be used to compute the date. If the field is empty, the date will be computed from the current date."""

    _name = 'of.crm.compute.date'
    _description_ = __doc__
    _order = 'sequence'

    name = fields.Char(required=True)
    res_model = fields.Char(string="Model")
    res_field = fields.Char(string="Field", required=True)
    use_today_date = fields.Boolean(string="Use today's date")
    sequence = fields.Integer()

    @api.onchange('use_today_date')
    def _onchange_use_today_date(self):
        """Simple helper to avoid user error when changing the field"""
        if self.use_today_date:
            self.res_field = 'today_date'

    def compute_value(self, record):
        if self.res_model:
            return record[self.res_field]
        if self.res_field == 'today_date':
            return fields.Date.today()
