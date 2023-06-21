# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.model
    def _auto_init(self):
        super(ResPartner, self)._auto_init()
        module_self = self.env['ir.module.module'].search([('name', '=', 'of_account')])
        if module_self:
            # installed_version est trompeur, il contient la version en cours d'installation
            # on utilise donc latest version à la place
            version = module_self.latest_version
            if version < '10.0.2':
                cr = self.env.cr
                cr.execute("UPDATE res_partner SET of_is_account_warn = 't' WHERE invoice_warn != 'no-message'")
                cr.execute("UPDATE res_partner SET of_is_warn = 't' WHERE invoice_warn != 'no-message'")
                cr.execute("UPDATE res_partner SET of_warn_block = 't' WHERE invoice_warn = 'block'")

    of_is_account_warn = fields.Boolean(string=u"Avertissement factures")
    # pour savoir si afficher of_warn_block et invoice_warn_msg
    of_is_warn = fields.Boolean(
        string=u"Avertissement sur au moins un objet", compute='_compute_of_is_warn', store=True)
    of_warn_block = fields.Boolean(string=u"Bloquant")
    # invoice_warn et invoice_warn_msg sont désormais partagés entre factures, ventes et interventions
    invoice_warn = fields.Selection(help=u"Type d'avertissement", compute='_compute_invoice_warn', store=True)
    invoice_warn_msg = fields.Text(
        string=u"Message", help=u"Message qui sera affiché comme avertissement si ce partenaire est sélectionné")

    @api.onchange('parent_id', 'property_account_receivable_id')
    def _onchange_property_account_receivable_id(self):
        # Si la compte client est modifié
        if self.property_account_receivable_id:
            # On vérifie si l'ancien avait des écritures
            origin_move_line_ids = self.env['account.move.line'].search(
                [('account_id', '=', self._origin.property_account_receivable_id.id)])
            if origin_move_line_ids:
                return {
                    'warning': {
                        'title': _('Warning'),
                        'message': _(u"Si vous sauvegardez, vous allez modifier un compte comptable qui contient"
                                     u"des écritures. Si vous êtes sûr(e) de vous, vous pouvez continuer, "
                                     u"sinon veuillez ne pas sauvegarder et annuler.")
                    }
                }

    @api.depends('of_is_account_warn')
    def _compute_of_is_warn(self):
        # fonction héritée dans of_sale et of_sale_planning
        has_warn = self.filtered('of_is_account_warn')
        # `has_warn.of_is_warn = True` ne fonctionne pas car expected singleton
        for partner in has_warn:
            partner.of_is_warn = True
        no_warn = self - has_warn
        for partner in no_warn:
            partner.of_is_warn = False

    @api.depends('of_warn_block', 'of_is_warn')
    def _compute_invoice_warn(self):
        # maintenir ce champ à jour pour que l'existant dans account et sale continue de fonctionner
        has_warn = self.filtered('of_is_warn')
        no_warn = self - has_warn
        for partner in no_warn:
            partner.invoice_warn = 'no-message'
        for partner in has_warn:
            if partner.of_warn_block:
                partner.invoice_warn = 'block'
            else:
                partner.invoice_warn = 'warning'
