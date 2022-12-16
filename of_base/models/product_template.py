# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # Recherche multi-mots
    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        args2 = []
        i = 0
        while i < len(args):
            if args[i] == '|' \
                    and isinstance(args[i + 1], (list)) and args[i + 1][0] == 'default_code' \
                    and isinstance(args[i + 2], (list)) and args[i + 2][0] == 'name' \
                    and args[i + 1][1] in ('like', 'ilike') \
                    and args[i + 1][2] == args[i + 2][2]:
                operator = args[i + 1][1]
                mots = args[i + 1][2].split()
                args2 += ['&'] * (len(mots) - 1)
                for mot in mots:
                    args2 += ['|', ('default_code', operator, mot), ('name', operator, mot)]
                i += 3
            else:
                args2.append(args[i])
                i += 1
        return super().search(args2, offset=offset, limit=limit, order=order, count=count)
