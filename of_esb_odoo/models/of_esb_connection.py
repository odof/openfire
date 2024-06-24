# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


import odoorpc

from odoo import fields, models


class ESBConnection(models.Model):
    _inherit = 'of.esb.connection'

    ttype = fields.Selection(selection_add=[('odoo', 'Odoo')])
    odoo_server = fields.Char("Odoo Server")
    odoo_port = fields.Char('Odoo Port')
    odoo_base = fields.Char('Odoo Base')
    odoo_protocol = fields.Selection(
        [('jsonrpc', 'jsonrpc'), ('jsonrpc+ssl', 'jsonrpc+ssl')], default='jsonrpc+ssl', string='Odoo Protocol'
    )

    def connect(self):
        odoo_base = odoorpc.ODOO(self.odoo_server, port=self.odoo_port, protocol=self.odoo_protocol)
        odoo_base.login(self.odoo_base, self.security.user, self.security.password)
        return odoo_base

    def get_out_example(self):
        if self.ttype == 'odoo':
            return """
            result = [
                {
                    'model': 'res.partner',
                    'result' [
                        { 'id' : 1, 'name': 'test' },
                        { 'id' : 2, 'name': 'test2' },
                    ]
                },
            ]
            """
        else:
            return super().get_out_example()

    def get_in_example(self):
        if self.ttype == 'odoo':
            return """
            [
                {
                    'model': 'res.partner',
                    'fields' [ 'id', 'name' ],
                    'domain': [],
                    'limit': 0,
                    'offset': 0,
                },
            ]
            """
        else:
            return super().get_in_example()
