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
            code = "'%s%%0%si%s' %% partner.id" % (
                seq_fournisseur.prefix or '', seq_fournisseur.padding, seq_fournisseur.suffix or '')
            vals['of_code_fournisseur'] = "(%s, %s)" % (code, 'partner.name')
            seq_fournisseur.active = False
        if vals:
            companies = self.search([])
            companies.write(vals)
        return res

    of_client_id_ref = fields.Boolean(
        string=u'Réf. client automatique',
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
    def update_account(self):
        """
        Création / Mise à jour du compte de tiers des clients.
        """
        # Pas de création de compte de tiers pour les contacts, mais uniquement pour les vrais partenaires
        partners = self.mapped('commercial_partner_id')
        if not partners:
            return

        # On se place en sudo pour pouvoir générer les comptes, mais il faut forcer la société de l'utilisateur
        company = self.env.user.company_id
        self = self.sudo().with_context(force_company=company.id)
        partners = partners.with_context(force_company=company.id)

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
            if partner.customer and company.of_code_client:
                # Création du compte de tiers
                code, name = safe_eval(company.of_code_client, {'partner': partner, 'company': company})
                if (partner.property_account_receivable_id or default_account_receivable) == default_account_receivable:
                    account = ac_obj.search([('code', '=', code), ('company_id', '=', company.id)], limit=1)
                    if account:
                        data['property_account_receivable_id'] = account.id
                        account.name = code
                    else:
                        type_id = data_obj.get_object_reference('account', 'data_account_type_receivable')[1]
                        account_data = {
                            'internal_type': 'receivable',
                            'user_type_id': type_id,
                            'code': code,
                            'name': name,
                            'reconcile': True,
                            # Avec le module of_base_multicompany, il est utile de forcer la société à la même
                            # que celle du compte par défaut et non celle de l'utilisateur
                            # (compte au niveau de la société, pas du magasin)
                            'company_id': default_account_receivable.company_id.id
                        }
                        data['property_account_receivable_id'] = ac_obj.create(account_data)

            # Si est un fournisseur
            if partner.supplier and company.of_code_fournisseur:
                # Création du compte de tiers
                code, name = safe_eval(company.of_code_fournisseur, {'partner': partner, 'company': company})
                if (partner.property_account_payable_id or default_account_payable) == default_account_payable:
                    account = ac_obj.search([('code', '=', code), ('company_id', '=', company.id)], limit=1)
                    if account:
                        data['property_account_payable_id'] = account.id
                        account.name = code
                    else:
                        type_id = data_obj.get_object_reference('account', 'data_account_type_payable')[1]
                        account = {
                            'internal_type': 'payable',
                            'user_type_id': type_id,
                            'code': code,
                            'name': name,
                            'reconcile': True,
                            # Avec le module of_base_multicompany, il est utile de forcer la société à la même
                            # que celle du compte par défaut et non celle de l'utilisateur
                            # (compte au niveau de la société, pas du magasin)
                            'company_id': default_account_payable.company_id.id
                        }
                        data['property_account_payable_id'] = ac_obj.create(account)
            if data:
                partner.write(data)

    @api.model
    def create(self, vals):
        partner = super(ResPartner, self).create(vals)

        # Utilisation de l'id du partenaire comme référence client, si option configurée dans la société
        if partner.company_id.of_client_id_ref:
            if not partner.ref:
                partner.ref = str(partner.id)
        return partner

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
            cr.execute(
                "SELECT DISTINCT account_id FROM account_move_line WHERE account_id IN %s",
                (tuple(account_ids),))
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
        help=u"Affectation automatique de la partie variable du compte de tiers "
             u"dans la référence du partenaire nouvellement créé")


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    @api.model
    def create(self, vals):
        partner_id = vals.get('partner_id')
        if partner_id:
            inv_type = vals.get('type') or self.default_get(['type'])['type']
            field_name = (inv_type in ('out_invoice', 'out_refund')
                          and 'property_account_receivable_id'
                          or 'property_account_payable_id')
            partner = self.env['res.partner'].browse(partner_id)
            old_account = partner[field_name]
            if old_account.id == vals.get('account_id'):
                partner.update_account()
                vals['account_id'] = partner[field_name].id
        return super(AccountInvoice, self).create(vals)

    @api.onchange('partner_id', 'company_id')
    def _onchange_partner_id(self):
        if self.partner_id:
            self.partner_id.update_account()
        return super(AccountInvoice, self)._onchange_partner_id()


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    @api.depends('invoice_ids', 'payment_type', 'partner_type', 'partner_id')
    def _compute_destination_account_id(self):
        if not self .invoice_ids and self.payment_type != 'transfer' and self.partner_id:
            self.partner_id.update_account()
        return super(AccountPayment, self)._compute_destination_account_id()


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if self.partner_id:
            self.partner_id.update_account()
        return super(AccountMoveLine, self)._onchange_partner_id()
