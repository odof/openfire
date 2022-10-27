# -*- coding: utf-8 -*-

from odoo import models, fields, api


class OFDatastorePurchase(models.Model):
    _name = 'of.datastore.purchase'
    _inherit = 'of.datastore.connector'
    _description = u"Connecteur d'achat"
    _rec_name = 'db_name'
    _order = 'db_name'

    active = fields.Boolean(string=u"Actif", default=True)
    partner_id = fields.Many2one(
        comodel_name='res.partner', string=u"Fournisseur",
        domain=[('supplier', '=', True), '|', ('is_company', '=', True), ('parent_id', '=', False)])
    # Utilisation d'un champ selection et non d'un booléen pour pouvoir facilement forcer la livraison directe
    # mais également pour permettre de repasser facilement à un état calculé.
    # Sélectionner oui/non va forcer la livraison directe. Vider le champ permet de repasser en calculé.
    dropshipping = fields.Selection(selection=[
        (1, "Oui"),
        (-1, "Non")
        ], string="Autorise la livraison directe", compute='_compute_dropshipping', inverse='_inverse_dropshipping',
        help=u"Peut être forcé en sélectionnant la valeur inverse de la valeur calculée. "
             u"Pour revenir à une valeur calculée, vider le champ")
    dropshipping_force = fields.Selection(selection=[
        (1, "Oui"),
        (-1, "Non")
        ], string="Autorise la livraison directe")
    child_ids = fields.One2many(
        comodel_name='of.datastore.purchase.company', inverse_name='parent_id', string=u"Liens sociétés")

    _sql_constraints = [
        ('db_name_uniq', 'unique (db_name)', u"Il existe déjà une connexion pour cette base")
    ]

    @api.model
    def default_get(self, fields_list):
        companies = self.env['res.company'].search([])
        res = super(OFDatastorePurchase, self).default_get(fields_list)
        res['child_ids'] = [(0, 0, {'company_id': company.id}) for company in companies]
        return res

    @api.depends('dropshipping_force', 'db_name', 'server_address', 'login', 'password', 'new_password')
    def _compute_dropshipping(self):
        for record in self:
            if record.dropshipping_force:
                record.dropshipping = record.dropshipping_force
            else:
                for field_name in ('db_name', 'server_address', 'login', 'password', 'new_password'):
                    if field_name == 'new_password' and record.password:
                        # Le nouveau mot de passe n'est obligatoire que s'il n'en existe pas déjà un
                        continue
                    if not record[field_name]:
                        break
                else:
                    client = record.of_datastore_connect()
                    if not isinstance(client, basestring):
                        ds_brand_obj = record.of_datastore_get_model(client, 'of.product.brand')
                        dropshipping = record.of_datastore_func(ds_brand_obj, 'dropshipping_allowed', [], [])
                        record.dropshipping = dropshipping and 1 or -1

    def _inverse_dropshipping(self):
        for record in self:
            record.dropshipping_force = record.dropshipping

    @api.multi
    def button_dummy(self):
        return True


class OFDatastorePurchaseCompany(models.Model):
    _name = 'of.datastore.purchase.company'

    @api.model_cr_context
    def _auto_init(self):
        cr = self._cr

        cr.execute("SELECT * FROM information_schema.tables WHERE table_name = '%s'" % (self._table,))
        exists = cr.fetchall()
        res = super(OFDatastorePurchaseCompany, self)._auto_init()
        if not exists:
            query = """
                INSERT INTO of_datastore_purchase_company (
                    create_uid
                ,   create_date
                ,   write_uid
                ,   write_date
                ,   parent_id
                ,   company_id
                ,   datastore_id
                )
                (
                    SELECT  1
                    ,       NOW()
                    ,       1
                    ,       NOW()
                    ,       id
                    ,       %s
                    ,       datastore_id
                    FROM    of_datastore_purchase
                )
            """
            cr.execute(query, (self.env.user.company_id.id,))
        return res

    parent_id = fields.Many2one(comodel_name='of.datastore.purchase', string="Connecteur", required=True)
    company_id = fields.Many2one(
        comodel_name='res.company', string=u"Société", required=True)
    datastore_id = fields.Char(string=u"Identifiant chez le fournisseur")
