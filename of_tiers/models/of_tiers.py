# -*- encoding: utf-8 -*-

from odoo import models, fields, api

class resCompany(models.Model):
    _inherit = "res.company"

    of_client_id_ref = fields.Boolean('Réf. client automatique',
                                      help=u"Lors de la création d'un nouveau partenaire, si cette case est cochée, "
                                           u"la référence client prendra par défaut le n° de compte comptable du partenaire.")

class resPartner(models.Model):
    _inherit = 'res.partner'

    @api.multi
    def _update_account(self):
        """
        Création / Mise à jour du compte de tiers des clients.
        """
        data_obj = self.env['ir.model.data']
        ac_obj = self.env['account.account']

        sequence_receivable = data_obj.get_object('of_tiers', 'sequence_customer_account')
        sequence_payable = data_obj.get_object('of_tiers', 'sequence_supplier_account')

        default_account_receivable = self.env['ir.property'].get('property_account_receivable_id', self._name)
        default_account_payable = self.env['ir.property'].get('property_account_payable_id', self._name)

        for partner in self:
            data = {}
            # Si est un client
            if partner.customer:
                if partner.property_account_receivable_id == default_account_receivable:
                    type_id = data_obj.get_object_reference('account', 'data_account_type_receivable')[1]
                    account_data = {
                        'internal_type': 'receivable',
                        'user_type_id': type_id,
                        'code': sequence_receivable.get_next_char(partner.id),
                        'name': partner.name,
                        'reconcile': True,
                    }
                    data['property_account_receivable_id'] = ac_obj.create(account_data)
                elif partner.property_account_receivable_id.name != partner.name:
                    partner.property_account_receivable_id.name = partner.name

            # Si est un fournisseur
            if partner.supplier:
                if partner.property_account_payable_id == default_account_payable:
                    type_id = data_obj.get_object_reference('account', 'data_account_type_payable')[1]
                    account = {
                        'internal_type': 'payable',
                        'user_type_id': type_id,
                        'code': sequence_payable.get_next_char(partner.id),
                        'name': partner.name,
                        'reconcile': True,
                    }
                    data['property_account_payable_id'] = ac_obj.create(account)
                elif partner.property_account_payable_id.name != partner.name:
                    partner.property_account_payable_id.name = partner.name

            if data:
                partner.write(data)

    @api.model
    def create(self, vals):
        partner = super(resPartner, self).create(vals)

        # Utilisation de l'id du partenaire comme référence client, si option configurée dans la société
        if partner.company_id.of_client_id_ref:
            if not partner.ref:
                partner.ref = str(partner.id)

        # Création des comptes comptables clients/fournisseurs
        partner._update_account()
        return partner

    @api.multi
    def write(self, vals):
        super(resPartner, self).write(vals)
        self._update_account()
        return True

    @api.multi
    def unlink(self):
        cr = self._cr
        account_obj = self.env['account.account']
        default_account_receivable = self.env['ir.property'].get('property_account_receivable_id', self._name)
        default_account_payable = self.env['ir.property'].get('property_account_payable_id', self._name)

        account_ids = [account.id
                       for partner in self
                       for account in (partner.property_account_receivable_id, partner.property_account_payable_id)
                       if account not in (default_account_receivable, default_account_payable)]

        super(resPartner, self).unlink()

        account_ids = set(account_ids)

        # On ne supprime pas les comptes ayant des écritures
        cr.execute("SELECT DISTINCT account_id FROM account_move_line WHERE account_id IN %s", (tuple(account_ids),))
        used_account_ids = cr.fetchall()
        if used_account_ids:
            account_ids -= set(zip(*used_account_ids)[0])

        # On ne supprime pas les comptes liés à d'autres partenaires
        for account_id in account_ids.copy():
            cr.execute("SELECT id FROM ir_property WHERE value_reference = 'account.account,%s' LIMIT 1" % account_id)
            if cr.fetchall():
                account_ids.remove(account_id)

        if account_ids:
            account_obj.browse(account_ids).unlink()
        return True

class AccountConfigSettings(models.TransientModel):
    _inherit = 'account.config.settings'

    of_client_id_ref = fields.Boolean(related='company_id.of_client_id_ref', string="Utiliser les comptes de tiers comme références clients *",
                                      help=u"Affectation automatique de la partie variable du compte de tiers dans la référence du partenaire nouvellement créé")
