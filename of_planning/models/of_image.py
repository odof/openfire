# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import fields, models


class OFImage(models.Model):
    _inherit = 'of.image'

    intervention_id = fields.Many2one(string="Intervention", comodel_name='calendar.event')
    intervention_date = fields.Datetime(string="Intervention date", related='intervention_id.start')
    intervention_status = fields.Selection(
        selection=[('before', "Before"), ('ongoing', "Ongoing"), ('after', "After")], string="Intervention state"
    )
