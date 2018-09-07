# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.tools.safe_eval import safe_eval

class ResCompany(models.Model):
    _inherit = "res.company"

    @api.model_cr_context
    def _auto_init(self):
        xml_obj = self.env['ir.model.data']
        sequence_obj = self.env['ir.sequence']
        res = super(ResCompany, self)._auto_init()
        vals = {}
        seq_client = sequence_obj.browse(xml_obj.search([('name', 'like', 'sequence_customer_account')]).res_id)
        if seq_client and seq_client.active:
            code = "'%s%%0%si%s' %% partner.id" % (seq_client.prefix or '', seq_client.padding, seq_client.suffix or '')
            vals['of_code_client'] = "(%s, %s)" % (code, 'partner.name')
            seq_client.active = False
        seq_fournisseur = sequence_obj.browse(xml_obj.search([('name', 'like', 'sequence_supplier_account')]).res_id)
        if seq_fournisseur and seq_fournisseur.active:
            code = "'%s%%0%si%s' %% partner.id" % (seq_fournisseur.prefix or '', seq_fournisseur.padding, seq_fournisseur.suffix or '')
            vals['of_code_fournisseur'] = "(%s, %s)" % (code, 'partner.name')
            seq_fournisseur.active = False
        if vals:
            companies = self.search([])
            companies.write(vals)
        return res

    of_client_id_ref = fields.Boolean('Réf. client automatique',
                                      help=u"Lors de la création d'un nouveau partenaire, si cette case est cochée, "
                                           u"la référence client prendra par défaut le n° de compte comptable du partenaire.")
    of_code_client = fields.Char('Code client', default="('411%05i' % partner.id, partner.name)")
    of_code_fournisseur = fields.Char('Code fournisseur', default="('401%05i' % partner.id, partner.name)")

    @api.multi
    def set_of_code_client_defaults(self):
        return self.env['ir.values'].sudo().set_default('res.company', '', self.pdf_adresse_nom_parent)

class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.multi
    def _update_account(self):
        """
        Création / Mise à jour du compte de tiers des clients.
        """
        # Ce verrou est normalement inutile car les appels _update_account() se font après les appels super() dans create et write
        if self._context.get('of_no_update_partner_account'):
            return
        self = self.with_context(of_no_update_partner_account=True)

        # Pas de création de compte de tiers pour les contacts, mais uniquement pour les vrais partenaires
        partners = self.search([('id', 'in', self._ids), '|', ('is_company', '=', True), ('parent_id', '=', False)])
        if not partners:
            return

        data_obj = self.env['ir.model.data']
        ac_obj = self.env['account.account']

        default_account_receivable = self.env['ir.property'].get('property_account_receivable_id', self._name)
        default_account_payable = self.env['ir.property'].get('property_account_payable_id', self._name)

        if not (default_account_payable and default_account_receivable):
            # La comptabilité de la société n'est pas configurée
            return

        for partner in partners:
            data = {}
            # Si est un client
            if partner.customer and self.company_id.of_code_client:
                # Création du compte de tiers
                code, name = safe_eval(self.company_id.of_code_client, {'partner': partner})
                if (partner.property_account_receivable_id or default_account_receivable) == default_account_receivable:
                    type_id = data_obj.get_object_reference('account', 'data_account_type_receivable')[1]
                    account_data = {
                        'internal_type': 'receivable',
                        'user_type_id': type_id,
                        'code': code,
                        'name': name,
                        'reconcile': True,
                        # Avec le module of_base_multicompany, il est utile de forcer la société à la même que celle du compte par défaut
                        # et non celle de l'utilisateur (compte au niveau de la société, pas du magasin)
                        'company_id': default_account_receivable.company_id.id
                    }
                    data['property_account_receivable_id'] = ac_obj.create(account_data)
                elif partner.property_account_receivable_id.name != name:
                    # Mise à jour du libellé du compte de tiers
                    partner.property_account_receivable_id.name = name

            # Si est un fournisseur
            if partner.supplier and self.company_id.of_code_fournisseur:
                # Création du compte de tiers
                code, name = safe_eval(self.company_id.of_code_fournisseur, {'partner': partner})
                if (partner.property_account_payable_id or default_account_payable) == default_account_payable:
                    type_id = data_obj.get_object_reference('account', 'data_account_type_payable')[1]
                    account = {
                        'internal_type': 'payable',
                        'user_type_id': type_id,
                        'code': code,
                        'name': name,
                        'reconcile': True,
                        # Avec le module of_base_multicompany, il est utile de forcer la société à la même que celle du compte par défaut
                        # et non celle de l'utilisateur (compte au niveau de la société, pas du magasin)
                        'company_id': default_account_payable.company_id.id
                    }
                    data['property_account_payable_id'] = ac_obj.create(account)
                elif partner.property_account_payable_id.name != name:
                    # Mise à jour du libellé du compte de tiers
                    partner.property_account_payable_id.name = name

            if data:
                partner.write(data)

    @api.model
    def create(self, vals):
        partner = super(ResPartner, self).create(vals)

        # Utilisation de l'id du partenaire comme référence client, si option configurée dans la société
        if partner.company_id.of_client_id_ref:
            if not partner.ref:
                partner.ref = str(partner.id)

        # Création des comptes comptables clients/fournisseurs
        partner._update_account()
        return partner

    @api.multi
    def write(self, vals):
        super(ResPartner, self).write(vals)
        self._update_account()
        return True

    @api.multi
    def unlink(self):
        # Suppression des comptes de tiers a la suppression du partenaire.
        # En cas de multi-société, seuls les comptes de la société courante de l'utilisateur sont supprimés
        cr = self._cr
        account_obj = self.env['account.account']
        default_account_receivable = self.env['ir.property'].get('property_account_receivable_id', self._name)
        default_account_payable = self.env['ir.property'].get('property_account_payable_id', self._name)

        account_ids = [account.id
                       for partner in self
                       for account in (partner.property_account_receivable_id, partner.property_account_payable_id)
                       if account not in (default_account_receivable, default_account_payable)]

        super(ResPartner, self).unlink()

        account_ids = set(account_ids)

        # On ne supprime pas les comptes ayant des écritures
        if account_ids:
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

    of_code_client = fields.Char(related='company_id.of_code_client', string='Code client')
    of_code_fournisseur = fields.Char(related='company_id.of_code_fournisseur', string='Code fournisseur')
    of_client_id_ref = fields.Boolean(
        related='company_id.of_client_id_ref', string=u"Utiliser les comptes de tiers comme références clients *",
        help=u"Affectation automatique de la partie variable du compte de tiers dans la référence du partenaire nouvellement créé")
