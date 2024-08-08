# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import json
import logging

from odoo import fields, models

logger = logging.getLogger(__name__)


class ESBService(models.Model):
    _name = 'esb.service'

    name = fields.Char()
    code = fields.Text()
    exec_active = fields.Boolean(string="Active", default=True)
    ttype = fields.Selection([('user', 'user'), ('system', 'system')], string="Type", default="user")

    def execute_with_delay(self, args={}):
        if self.exec_active:
            # on regarde si dans args.in_data, il y a un user_id
            # si oui, on l'utilise pour lancer l'action, sinon on prends le user courant
            data = json.loads(args.in_data)
            if user_id := data.get('user_id'):
                user = self.env['res.users'].browse(user_id)
                res = self.with_user(user).with_delay().execute(args)
            else:
                res = self.with_delay().execute(args)

            return res

        else:
            return {'error': 'this service is not active'}

    def execute(self, args={}):
        if self.code and self.exec_active:
            exec(self.code, {'args': args, 'self': self})
            res = {}
            for field in args._fields:
                res[field] = args[field]
            return res

        elif not self.exec_active:
            return {'error': 'this service is not active'}
        else:
            return {'error': 'Code is empty'}

    def unlink(self):
        # on ne peut pas supprimer un service system, juste les "user"
        return super(ESBService, self.filtered(lambda r: r.ttype == "user")).unlink()
