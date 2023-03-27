# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class OfCompanyMultiLogos(models.Model):
    _name = 'of.company.multi.logos'
    _description = "Contains secondary company logos"
    _inherit = ['image.mixin']

    @api.model
    def _get_default_company(self):
        return self.env.user.company_id

    company_ids = fields.Many2many(
        comodel_name='res.company', relation='res_company_of_logo_rel', column1='logo_id', column2='company_id',
        string="Companies", required=True, default=lambda self: self._get_default_company())
    logo = fields.Binary(related='image_1920', string="Company Logo", readonly=False, required=True)
    name = fields.Char(string="Label", required=True)
    color = fields.Integer(string="Color Index")
    description = fields.Text(string="Description", translate=True)
    logo_position = fields.Selection(selection=[
        ('footer', 'Footer'),
        ('footer_right_corner', 'Footer right corner'),
        ('footer_left_corner', 'Footer left corner')], string="Type", default='footer')
    is_displayed_in_docs = fields.Boolean(string="Posted in documents", default=True)
