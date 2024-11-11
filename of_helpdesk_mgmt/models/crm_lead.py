# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class CrmLead(models.Model):
    _inherit = "crm.lead"

    of_ticket_id = fields.Many2one(comodel_name="helpdesk.ticket", string="Ticket")
