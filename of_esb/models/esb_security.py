# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ESBSecurity(models.Model):
    _name = 'esb.security'

    name = fields.Char()
    ttype = fields.Selection([('None', 'None'), ('Password', 'Password')], string="Type")
    user = fields.Char()
    password = fields.Char()
    user_id = fields.Many2one(comodel_name='res.users', string="Utilisateur associé", required=True)

    def authorize(self, args):
        if self.ttype == 'None':
            return self.user_id
        elif self.ttype == 'Password':
            user = args.get('user')
            password = args.get('password')
            if user == self.user and password == self.password:
                return self.user_id

        return False
