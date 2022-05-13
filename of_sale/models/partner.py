# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.model
    def _auto_init(self):
        module_self = self.env['ir.module.module'].search([('name', '=', 'of_sale')])
        partner_sale_warn_ids = []
        partner_sale_block_ids = []
        if module_self:
            # installed_version est trompeur, il contient la version en cours d'installation
            # on utilise donc latest version à la place
            version = module_self.latest_version
            if version < '10.0.2':
                cr = self.env.cr
                cr.execute("SELECT id FROM res_partner WHERE sale_warn != 'no-message'")
                # cr.execute n'accepte pas les listes en paramètre
                partner_sale_warn_ids = tuple([row[0] for row in cr.fetchall()])
                cr.execute("SELECT id FROM res_partner WHERE sale_warn = 'block'")
                partner_sale_block_ids = tuple([row[0] for row in cr.fetchall()])
        super(ResPartner, self)._auto_init()
        if partner_sale_warn_ids:
            cr.execute("UPDATE res_partner SET of_is_sale_warn = 't' WHERE id in %s", (partner_sale_warn_ids,))
            cr.execute("UPDATE res_partner SET of_is_warn = 't' WHERE id in %s", (partner_sale_warn_ids,))
            cr.execute(
                "UPDATE res_partner SET invoice_warn_msg = sale_warn_msg "
                "WHERE (invoice_warn_msg IS NULL OR invoice_warn_msg = '') and id in %s",
                (partner_sale_warn_ids,))
        if partner_sale_block_ids:
            cr.execute("UPDATE res_partner SET of_warn_block = 't' WHERE id in %s", (partner_sale_block_ids,))

    # invoice_warn et invoice_warn_msg sont désormais partagés entre factures, ventes et interventions
    sale_warn = fields.Selection(related='invoice_warn', readonly=True)
    sale_warn_msg = fields.Text(related='invoice_warn_msg', readonly=True)
    of_is_sale_warn = fields.Boolean(string=u"Avertissement ventes")
    of_invoice_policy = fields.Selection(
        [('order', u'Quantités commandées'), ('delivery', u'Quantités livrées')],
        string="Politique de facturation")

    @api.depends('of_is_sale_warn')
    def _compute_of_is_warn(self):
        has_warn = self.filtered('of_is_sale_warn')
        # `has_warn.of_is_warn = True` ne fonctionne pas car expected singleton
        for partner in has_warn:
            partner.of_is_warn = True
        partners_left = self - has_warn
        super(ResPartner, partners_left)._compute_of_is_warn()
