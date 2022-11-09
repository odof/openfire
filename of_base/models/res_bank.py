# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


# 1: imports of python lib
# 2:  imports of odoo
from odoo import models, api
from odoo.exceptions import ValidationError
# 3:  imports from odoo modules
# 4: local imports
# 5: Import of unknown third party lib
from schwifty import BIC


class ResBank(models.Model):
    _inherit = 'res.bank'

    @api.model
    def create(self, vals):
        if vals.get('bic'):
            try:
                BIC(vals['bic'])
            except Exception as e:
                raise ValidationError("Le code bic est incorrect")
        return super(ResBank, self).create(vals)

    @api.multi
    def write(self, vals):
        if vals.get('bic'):
            try:
                BIC(vals['bic'])
            except Exception as e:
                raise ValidationError("Le code bic est incorrect")
        return super(ResBank, self).write(vals)


class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'

    @api.model
    def check_condition_show_dialog(self, record_id, data):
        # If not data, there is no modification on the record. We don't need to verify in this case.
        if data and not data.get('bank_id', False) and (
                not record_id or ('bank_id' in data and self.browse(record_id).bank_id)):
            return True
        return False

    @api.model
    def dialog_type(self,):
        """
            :returns:
                False, False -> No dialog
                'confirm', "message" -> A confirmation dialog that won't save unless the user press OK
                'alert', "message" -> An alert dialog that will warn the user and still save
        """
        return 'confirm', u"Vous n'avez pas rempli le champ banque, et donc pas de code d'identification bancaire.\n" \
                          u"Êtes-vous sûr de vouloir continuer ?"
