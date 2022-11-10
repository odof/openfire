# -*- coding: utf-8 -*-

from odoo import models, api, fields

class OfSaleApproRule(models.Model):
    _name = 'of.sale.appro.rule'
    _description = u"Règles d'approvisionnement intersociétés"

    company_src_id = fields.Many2one('res.company', string=u"Société fournisseur", required=True)
    # Ajouter des droits pour OfSaleApproRule relativement à la société de l'utilisateur courant
    company_id = fields.Many2one('res.company', string=u"Société cliente", required=True)
    user_src_id = fields.Many2one('res.users', string="Utilisateur fournisseur", required=True, help=u"Il s'agit de l'utilisateur qui sera utilisé pour créer la commande client pour la société fournisseur")
    name = fields.Char(string=u"Nom de la règle", required=True)
    marge_fournisseur = fields.Float(string="Marge fournisseur", required=True, default=5.00, help=u"Marge en %\nLe prix de vente de la société fournisseur correspond au prix d'achat de la société + la marge")

    @api.onchange('marge_fournisseur')
    def _onchange_marge(self):
        if self.marge_fournisseur < 0:
            self.marge_fournisseur = 0

    @api.multi
    def write(self, vals):
        if ('marge_fournisseur' in vals and vals['marge_fournisseur'] < 0) or self.marge_fournisseur < 0:
            vals['marge_fournisseur'] = 0
        return super(OfSaleApproRule, self).write(vals)

    @api.model
    def create(self, vals):
        return super(OfSaleApproRule, self).create(vals)

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    @api.multi
    def button_wizard_appro_intersocietes(self):
        if not self.move_lines:  # Si aucune ligne dans l'onglet demande initial du BL
            self.env['of.popup.wizard'].popup_return(u"Aucune ligne à approvisionner")

        wizard_inter_line_obj = self.env['of.appro.intersocietes.wizard.line']
        wizard_inter_obj = self.env['of.appro.intersocietes.wizard']
        rule_obj = self.env['of.sale.appro.rule']
        sale_order_obj = self.env['sale.order']
        lines = []

        # Récupération du sale_order pour prendre l'origine
        sale_order_name = self.group_id.name
        sale_order = sale_order_obj.search([('name', '=', sale_order_name)])

        # Récupération d'une règle et des entrepôts par défaut (utile pour la CC et CF)
        rule_ids = rule_obj.search([('company_id', '=', self.company_id.id)])
        if not rule_ids:
            return self.env['of.popup.wizard'].popup_return(u"Il n'y a aucune règle d'approvisionnement avec la société " + self.company_id.display_name + u" comme société cliente.")
        rule = [rule for rule in rule_ids][0] or False
        # Création du wizard en amont pour pouvoir lier les lignes au wizard
        wizard = wizard_inter_obj.create({'rule_id': rule and rule.id or False,
                                          'company_id': self.company_id.id,
                                          'date_planned': fields.Datetime.now(),
                                          'sale_order_origin_id': sale_order and sale_order.id or False})

        # Création des lignes
        for line in self.move_lines.filtered(lambda line: line.state == "confirmed"):
            product = line.product_id
            product_qty = line.product_uom_qty
            marge_ratio = 100.0 - rule.marge_fournisseur
            price_marge = marge_ratio and product.get_cost() * 100.0 / marge_ratio
            lines.append(wizard_inter_line_obj.create({
                'product_id': product.id,
                'product_uom_id': product.uom_id.id,
                'product_qty': product_qty,
                'price': product.get_cost(),
                'price_marge': price_marge,
                'wizard_id': wizard.id,
                'bl_line_id': line.id,
                }).id)

        # Renvoie la vue du wizard avec le wizard créé
        return {
            'type': 'ir.actions.act_window',
            'name': 'action_of_appro_intersocietes_wizard',
            'res_model': 'of.appro.intersocietes.wizard',
            'view_type': 'form',
            'view_mode': 'form',
            'res_id': wizard.id,
            'target': 'new',
            'context': str({'partner_id': self.partner_id.id})
        }
