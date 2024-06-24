# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


import odoorpc

from odoo import fields, models


class ESBConnection(models.Model):
    _inherit = "of.esb.connection"

    ttype = fields.Selection(selection_add=[("odoo", "Odoo")])
    odoo_server = fields.Char()
    odoo_port = fields.Char()
    odoo_base = fields.Char()
    odoo_protocol = fields.Selection(
        selection=[("jsonrpc", "jsonrpc"), ("jsonrpc+ssl", "jsonrpc+ssl")],
        default="jsonrpc+ssl",
    )
    odoo_company_id = fields.Integer(string="Company ID")

    def connect_odoo(self):
        odoo_base = odoorpc.ODOO(self.odoo_server, port=self.odoo_port, protocol=self.odoo_protocol)
        odoo_base.login(self.odoo_base, self.security.user, self.security.password)
        return odoo_base

    def get_out_example_odoo(self):
        return """
        result = [
            {
                "model": "res.partner",
                "result": [
                    { "id" : 1, "name": "test" },
                    { "id" : 2, "name": "test2" },
                ]
            },
        ]
            """

    def get_in_example_odoo(self):
        return """
        [
            {
                "model": "res.partner",
                "fields": [ "id", "name" ],
                "domain": [],
                "limit": 0,
                "offset": 0,
            },
        ]
        """
