# -*- coding: utf-8 -*-

from odoo import models, fields


class MassMailing(models.Model):
    _inherit = 'mail.mass_mailing'

    def update_opt_out(self, email, res_ids, value):
        """
        Fonction surchargée suite au changements OF pour champs rgpd
        Le champ créé par OF est l'inverse du champ opt_out
        :param email: champ texte
        :param res_ids: Liste d'ids
        :param value: Booléen
        :return:
        """
        model = self.env[self.mailing_model].with_context(active_test=False)
        if 'of_accord_communication' in model._fields:
            email_fname = 'email_from'
            if 'email' in model._fields:
                email_fname = 'email'
            records = model.search([('id', 'in', res_ids), (email_fname, 'ilike', email)])
            if value:
                records.write({'of_accord_communication': not value})
            else:
                records.write({'of_accord_communication': not value,
                               'of_date_accord_communication': fields.Date.today(),
                               'of_preuve_accord_communication': u"Accord donné par mail"})
        else:
            super(MassMailing, self).update_opt_out(email, res_ids, value)
