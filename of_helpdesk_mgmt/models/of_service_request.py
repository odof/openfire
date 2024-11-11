# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class OFServiceRequest(models.Model):
    _inherit = "of.service.request"

    ticket_id = fields.Many2one(comodel_name="helpdesk.ticket", string="Ticket")
