# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import json
import logging
import uuid

from odoo import fields, models

logger = logging.getLogger(__name__)


class ESBService(models.Model):
    _name = 'of.esb.service'

    name = fields.Char()
    code = fields.Text()
    exec_active = fields.Boolean(string="Active", default=True)
    ttype = fields.Selection([('user', 'user'), ('system', 'system')], string="Type", default="user")
    uuid = fields.Char(default=lambda r: uuid.uuid4())

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
            exec(self.code, {'args': args, 'self': self, 'logger': logger, 'json': json})
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

    def get_data(self, args):
        in_data = json.loads(args.in_data)
        if ttype := in_data.get('type'):
            if hasattr(self, f'get_data_{ttype}'):
                logger.info(f"Méthode trouvée : get_data_{ttype}")
                return getattr(self, f'get_data_{ttype}')(args)
        logger.info(f"Méthode non trouvée : get_data_{ttype}")
        return []

    def set_data(self, args):
        in_data = json.loads(args.in_data)
        if ttype := in_data.get('type'):
            if hasattr(self, f'set_data_{ttype}'):
                return getattr(self, f'set_data_{ttype}')(args)
        logger.info(f"Méthode non trouvée : set_data_{ttype}")
        return []

    def preview(self, connection, data):
        ttype = connection.ttype
        if hasattr(self, f'preview_{ttype}'):
            return getattr(self, f'preview_{ttype}')(connection, data)
        logger.info(f"Méthode non trouvée : preview_{ttype}")
        return "Aucune preview"
