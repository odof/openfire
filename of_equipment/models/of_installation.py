# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class OFInstallation(models.Model):
    _name = "of.installation"
    _description = "Installation"

    name = fields.Char(string="Nom", required=True)
    customer_id = fields.Many2one(comodel_name="res.partner", string="Client")
    site_address_id = fields.Many2one(comodel_name="res.partner", string="Site d'installation")
    company_id = fields.Many2one(comodel_name="res.company", string="Société")
    installer_id = fields.Many2one(comodel_name="res.partner", string="Installateur")
    equipment_ids = fields.One2many(comodel_name="of.equipment", inverse_name="installation_id", string="Équipements")
