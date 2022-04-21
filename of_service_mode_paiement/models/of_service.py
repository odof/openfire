# -*- coding: utf-8 -*-

from odoo import models, fields, api


class OfService(models.Model):
    _inherit = 'of.service'

    validite_sepa = fields.Selection(
        selection=[("non_verifie", u"Non vérifiée"), ("non_valide", u"Non valide"), ("valide", u"Valide")],
        string=u"Validité du SEPA", readonly=True, required=True, default="non_verifie")
    date_verification_sepa = fields.Date(string=u'Date de vérification', readonly=True)
    paiements_non_lettres_count = fields.Integer(string=u"Nombre de paiement non lettré", compute='_compute_paiements')
    paiements_ids = fields.One2many(
        comodel_name='account.payment', string=u"Nombre de paiement", compute='_compute_paiements')
    paiements_count = fields.Integer(string=u"Nombre de paiement", compute='_compute_paiements')
    prelevements_ids = fields.One2many(
        comodel_name='of.paiement.edi', string=u"Prélèvements", compute='_compute_prelevements')
    prelevements_count = fields.Integer(string=u"Nombre de prélèvement", compute='_compute_prelevements')
    deadline_count = fields.Integer(string=u"Nombre d'échéance")

    payment_term_id = fields.Many2one(comodel_name='account.payment.term', string=u"Conditions de règlement")
    montant_dernier_prelevement = fields.Float(
        string=u"Montant du dernier prélèvement", compute='_compute_prelevements')
    date_dernier_prelevement = fields.Date(string=u"Date du dernier prélèvement")
    date_previsionnelle_prochaine_facture = fields.Date(string=u"Date prévisionnelle de prochaine facture")

    def _compute_paiements(self):
        paiements_ids = self.env['account.payment'].search([('service_ids', 'in', self.ids)])
        self.paiements_ids = paiements_ids
        self.paiements_count = len(paiements_ids)
        self.paiements_non_lettres_count = len(paiements_ids.filtered(lambda paiement: paiement.state != 'reconciled'))

    def _compute_prelevements(self):
        edi_service_line_ids = self.env['of.paiement.edi.service.line'].search([('service_id', '=', self.id)])
        prelevements_ids = self.env['of.paiement.edi']\
            .search([('edi_service_line_ids', 'in', edi_service_line_ids.ids)]).sorted('date_remise')
        if prelevements_ids:
            self.prelevements_ids = prelevements_ids
            self.prelevements_count = len(prelevements_ids)
            self.montant_dernier_prelevement = sum(
                prelevements_ids[0].edi_line_ids.mapped('montant_prelevement')) or 0.0
            self.date_dernier_prelevement = prelevements_ids[0].date_remise

    @api.multi
    def action_view_paiements(self):
        if self.ensure_one():
            return {
                'name': u"Paiements",
                'view_mode': 'tree,kanban,form',
                'res_model': 'account.payment',
                'res_id': self.paiements_ids.ids,
                'domain': "[('id', 'in', %s)]" % self.paiements_ids.ids,
                'type': 'ir.actions.act_window',
            }

    @api.multi
    def action_view_prelevements(self):
        if self.ensure_one():
            return {
                'name': u"Prélèvements SEPA",
                'view_mode': 'tree,kanban,form',
                'res_model': 'of.paiement.edi',
                'res_id': self.prelevements_ids.ids,
                'domain': "[('id', 'in', %s)]" % self.prelevements_ids.ids,
                'type': 'ir.actions.act_window',
            }

    @api.multi
    def verification_validite_sepa(self):
        """Action appelée pour vérifier la validité du SEPA"""
        for invoice in self:
            # On check également le commercial_partner_id car les comptes bancaires
            # peuvent être définis chez ce partenaire
            if any(bank.verification_validite() for bank in invoice.partner_id.bank_ids) \
                    or any(bank.verification_validite() for bank in invoice.partner_id.commercial_partner_id.bank_ids):
                invoice.validite_sepa = 'valide'
            else:
                invoice.validite_sepa = 'non_valide'
            invoice.date_verification_sepa = fields.Date.today()
        return True
