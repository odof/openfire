# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class OFImportMessage(models.Model):
    _name = 'of.import.message'
    _description = "Message from OpenImport journal"
    _rec_name = 'message'

    import_id = fields.Many2one(comodel_name='of.import', string="Import")
    type = fields.Selection(
        selection=[('error', "Error"), ('warning', "Warning"), ('info', "Info")], string="Type of message"
    )
    message = fields.Text(string="Message")
