# -*- coding: utf-8 -*-

from odoo import models, api, fields, SUPERUSER_ID
from odoo.exceptions import UserError


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    of_is_current_user_admin = fields.Boolean(
        string=u"L'utilisateur courant est l'admin", compute='_compute_of_is_current_user_admin')

    @api.depends('type')
    def _compute_of_is_current_user_admin(self):
        for journal in self:
            journal.of_is_current_user_admin = self._uid == SUPERUSER_ID

    @api.onchange('type')
    def _onchange_type(self):
        self.update_posted = self.type in ('purchase', 'general')

    @api.multi
    def of_check_edit_updateable(self, vals):
        u"""
        Vérifie si les valeurs reçues pour de la modification/création de journal sont cohérentes pour les droits
        d'étition des écritures comptables.
        :param vals: valeurs à modifier/ajouter dans le journal.
        :return: 2 éléments :
            - message d'erreur le cas échéant,
            - dictionnaire des valeurs devant remplacer celles de vals.
        """
        if self._uid == SUPERUSER_ID:
            # L'admin a tous les droits. Pas d'erreur, on laisse les paramètres choisis.
            return False, {}
        if vals.get('update_posted'):
            # Modification manuelle de l'utilisateur.
            # Normalement, un readonly empêche de faire n'importe quoi.
            # Les tests suivants permettent d'éviter qu'un utilisateur passe outre ce readonly.
            if 'type' in vals:
                error = vals['type'] in ('sale', 'bank', 'cash')
            else:
                error = self.filtered(lambda o: o.type in ('sale', 'bank', 'cash'))

            if error:
                return u"Vous ne pouvez pas autoriser la modification des écritures comptables sur un journal " \
                       u"de ce type", {}
        elif 'type' in vals:
            # Lors du changement de type d'un journal, le champ update_posted peut être à vrai
            #   et ne pas réussir à passer à faux car le champ est devenu readonly.
            # On s'assure donc de forcer cette valeur
            if vals['type'] in ('sale', 'bank', 'cash'):
                return "", {'update_posted': False}
        return "", {}

    @api.model
    def create(self, vals):
        error, data = self.of_check_edit_updateable(vals)
        if error:
            raise UserError(error)
        vals.update(data)
        return super(AccountJournal, self).create(vals)

    @api.multi
    def write(self, vals):
        error, data = self.of_check_edit_updateable(vals)
        if error:
            raise UserError(error)
        vals.update(data)
        return super(AccountJournal, self).write(vals)

    @api.model
    def remove_update_posted_from_journals(self, journal_types=[]):
        journals = self.search([('type', 'in', journal_types), ('update_posted', '=', True)])
        if journals:
            journals.write({'update_posted': False})
