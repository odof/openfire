# -*- coding:utf-8 -*-

from odoo import fields, models

class OFAccountFrFec(models.TransientModel):
    _inherit = 'account.fr.fec'

    where_clause_create_date = fields.Boolean(default=True)  # Surcharge champ parent pour prendre la date de création
