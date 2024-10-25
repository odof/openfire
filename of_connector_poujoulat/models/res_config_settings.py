# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    of_poujoulat_host = fields.Char(string="Server address", config_parameter="of.connector.poujoulat.host")
    of_poujoulat_redirect = fields.Char(
        string="Redirection url", config_parameter="of.connector.poujoulat.url_redirect"
    )
    of_poujoulat_brand_ids = fields.Many2many(
        comodel_name="of.product.brand",
        relation="res_config_connector_poujoulat_brands_rel",
        string="Brands",
        compute="_compute_of_poujoulat_brand_ids",
        inverse="_inverse_of_poujoulat_brand_ids",
    )
    of_poujoulat_brand_ids_str = fields.Char(
        string="Brands (string)",
        config_parameter="of.connector.poujoulat.brand_ids",
        help="Technical field to store M2M fields into a config parameter. As `config_parameters` does not accept m2m "
        "field, we store the fields with a comma separated string into a Char config field.",
    )
    of_poujoulat_partner_ids = fields.Many2many(
        comodel_name="res.partner",
        relation="res_config_connector_poujoulat_partners_rel",
        string="Suppliers",
        compute="_compute_of_poujoulat_partner_ids",
        inverse="_inverse_of_poujoulat_partner_ids",
    )
    of_poujoulat_partner_ids_str = fields.Char(
        string="Suppliers (string)",
        config_parameter="of.connector.poujoulat.partner_ids",
        help="Technical field to store M2M fields into a config parameter. As `config_parameters` does not accept m2m "
        "field, we store the fields with a comma separated string into a Char config field.",
    )

    @api.depends("of_poujoulat_brand_ids_str")
    def _compute_of_poujoulat_brand_ids(self):
        for setting in self:
            if setting.of_poujoulat_brand_ids_str:
                ids = setting.of_poujoulat_brand_ids_str.split(",")
                ids = [int(id) for id in ids if id.isdigit()]
                setting.of_poujoulat_brand_ids = self.env["of.product.brand"].search([("id", "in", ids)])
            else:
                setting.of_poujoulat_brand_ids = None

    def _inverse_of_poujoulat_brand_ids(self):
        for setting in self:
            if setting.of_poujoulat_brand_ids:
                setting.of_poujoulat_brand_ids_str = ",".join(
                    setting.of_poujoulat_brand_ids.mapped(lambda x: str(x.id))
                )
            else:
                setting.of_poujoulat_brand_ids_str = ""

    @api.depends("of_poujoulat_partner_ids_str")
    def _compute_of_poujoulat_partner_ids(self):
        for setting in self:
            if setting.of_poujoulat_partner_ids_str:
                ids = setting.of_poujoulat_partner_ids_str.split(",")
                ids = [int(id) for id in ids if id.isdigit()]
                setting.of_poujoulat_partner_ids = self.env["res.partner"].search([("id", "in", ids)])
            else:
                setting.of_poujoulat_partner_ids = None

    def _inverse_of_poujoulat_partner_ids(self):
        for setting in self:
            if setting.of_poujoulat_partner_ids:
                setting.of_poujoulat_partner_ids_str = ",".join(
                    setting.of_poujoulat_partner_ids.mapped(lambda x: str(x.id))
                )
            else:
                setting.of_poujoulat_partner_ids_str = ""

    def set_of_poujoulat_host(self):
        host = self.of_poujoulat_host
        if host and not host.endswith("/"):
            host = f"{host}/"

        self.env["ir.config_parameter"].sudo().set_param("of.connector.poujoulat.host", host)

    def get_of_poujoulat_host(self):
        return self.env["ir.config_parameter"].sudo().get_param("of.connector.poujoulat.host")
