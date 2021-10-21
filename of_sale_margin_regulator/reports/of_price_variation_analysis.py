# -*- coding: utf-8 -*-

from odoo import fields, models, api, tools


class OFSaleMarginRegulator(models.Model):
    """Analyse des remises"""

    _name = 'of.price.variation.analysis'
    _auto = False
    _description = "Analyse des remises"
    _rec_name = 'id'

    order_id = fields.Many2one(comodel_name='sale.order', string=u"Commande", readonly=True)
    company_id = fields.Many2one(comodel_name='res.company', string=u"Société", readonly=True)
    company_type_id = fields.Many2one(comodel_name='of.res.company.type', string=u"Type de société", readonly=True)
    company_sector_id = fields.Many2one(comodel_name='of.res.company.sector', string=u"Secteur de société", readonly=True)
    company_sales_group_id = fields.Many2one(comodel_name='of.res.company.sales.group', string=u"Groupe Ventes de société", readonly=True)
    user_id = fields.Many2one(comodel_name='res.users', string=u"Vendeur", readonly=True)
    partner_id = fields.Many2one(comodel_name='res.partner', string=u"Partenaire", readonly=True)
    order_date = fields.Date(string=u"Date de commande", readonly=True)
    custom_confirmation_date = fields.Date(string=u"Date de confirmation", readonly=True)
    confirmation_date = fields.Date(string=u"Date d'enregistrement", readonly=True)
    invoice_date = fields.Date(string=u"Date de dernière facture", readonly=True)
    invoice_status = fields.Selection([
        ('upselling', u"Opportunité de montée en gamme"),
        ('invoiced', u"Entièrement facturé"),
        ('to invoice', u"À facturer"),
        ('no', u"Rien à facturer")
    ], string=u"État de facturation", readonly=True)
    product_id = fields.Many2one(comodel_name='product.product', string=u"Article")
    product_brand_id = fields.Many2one(comodel_name='of.product.brand', string=u"Marque de l'article")
    product_categ_id = fields.Many2one(comodel_name='product.category', string=u"Catégorie de l'article")

    presale_price = fields.Float(string=u"Prix de vente à la confirmation", readonly=True)
    presale_price_variation = fields.Float(string=u"Variation de prix à la confirmation", readonly=True)
    presale_margin = fields.Float(string=u"Marge à la confirmation (€)", readonly=True)
    presale_margin_variation = fields.Float(string=u"Variation de marge à la confirmation", readonly=True)
    presale_price_variation_rate = fields.Float(
        string=u"Taux de remise à la confirmation (%)", compute='_compute_presale_price_variation_rate',
        compute_sudo=True,
        readonly=True)

    sale_price = fields.Float(string=u"Prix de vente à l'enregistrement", readonly=True)
    sale_price_variation = fields.Float(string=u"Variation de prix à l'enregistrement", readonly=True)
    sale_margin = fields.Float(string=u"Marge à l'enregistrement (€)", readonly=True)
    sale_margin_variation = fields.Float(string=u"Variation de marge à l'enregistrement", readonly=True)
    sale_price_variation_rate = fields.Float(
        string=u"Taux de remise à l'enregistrement (%)", compute='_compute_sale_price_variation_rate',
        compute_sudo=True,
        readonly=True)

    @api.multi
    def _compute_presale_price_variation_rate(self):
        for rec in self:
            if (rec.presale_price + rec.presale_price_variation) != 0:
                rec.presale_price_variation_rate = \
                    100 * (- rec.presale_price_variation / (rec.presale_price - rec.presale_price_variation))
            else:
                rec.presale_price_variation_rate = 0

    @api.multi
    def _compute_sale_price_variation_rate(self):
        for rec in self:
            if (rec.sale_price + rec.sale_price_variation) != 0:
                rec.sale_price_variation_rate = \
                    100 * (- rec.sale_price_variation / (rec.sale_price - rec.sale_price_variation))
            else:
                rec.presale_price_variation_rate = 0

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        if 'presale_price' not in fields:
            fields.append('presale_price')
        if 'presale_price_variation' not in fields:
            fields.append('presale_price_variation')
        if 'presale_price_variation_rate' not in fields:
            fields.append('presale_price_variation_rate')
        if 'sale_price' not in fields:
            fields.append('sale_price')
        if 'sale_price_variation' not in fields:
            fields.append('sale_price_variation')
        if 'sale_price_variation_rate' not in fields:
            fields.append('sale_price_variation_rate')
        res = super(OFSaleMarginRegulator, self).read_group(
            domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
        for line in res:
            if 'presale_price_variation_rate' in fields:
                line['presale_price_variation_rate'] = 0
                if 'presale_price' in line and line['presale_price'] is not None \
                        and line.get('presale_price_variation', False) \
                        and (line['presale_price'] - line['presale_price_variation']) != 0:
                    line['presale_price_variation_rate'] = \
                        round(100.0 * (- line['presale_price_variation']) /
                              (line['presale_price'] - line['presale_price_variation']), 2)
                else:
                    line['presale_price_variation_rate'] = 0
            if 'sale_price_variation_rate' in fields:
                line['sale_price_variation_rate'] = 0
                if 'sale_price' in line and line['sale_price'] is not None \
                        and line.get('sale_price_variation', False) \
                        and (line['sale_price'] - line['sale_price_variation']) != 0:
                    line['sale_price_variation_rate'] = \
                        round(100.0 * (- line['sale_price_variation']) /
                              (line['sale_price'] - line['sale_price_variation']), 2)
                else:
                    line['presale_price_variation_rate'] = 0

        return res

    def init(self):
        tools.drop_view_if_exists(self._cr, 'of_price_variation_analysis')
        self._cr.execute("""
            CREATE VIEW of_price_variation_analysis AS (
                %s
                %s
                %s
            )""" % (self._select(),
                    self._from(),
                    self._where()))

    def _select(self):
        select_str = """
            SELECT      SOL.id                                                      AS id
            ,           SO.id                                                       AS order_id
            ,           SO.company_id
            ,           RC.of_company_type_id                                       AS company_type_id
            ,           RC.of_company_sector_id                                     AS company_sector_id
            ,           RC.of_company_sales_group_id                                AS company_sales_group_id
            ,           SO.user_id
            ,           SO.partner_id
            ,           SO.date_order::timestamp::date                              AS order_date
            ,           SO.of_custom_confirmation_date::timestamp::date             AS custom_confirmation_date
            ,           SO.confirmation_date::timestamp::date                       AS confirmation_date
            ,           SO.invoice_status
            ,           (   SELECT  MAX(AI2.date_invoice)
                            FROM    sale_order_line             SOL2
                            ,       sale_order_line_invoice_rel SOLIR2
                            ,       account_invoice_line        AIL2
                            ,       account_invoice             AI2
                            WHERE   SOL2.order_id               = SO.id
                            AND     SOLIR2.order_line_id        = SOL2.id
                            AND     AIL2.id                     = SOLIR2.invoice_line_id
                            AND     AI2.id                      = AIL2.invoice_id
                            AND     AI2.state                   IN ('open', 'paid')
                        )                                                           AS invoice_date
            ,           SOL.product_id
            ,           SOL.of_product_brand_id                                     AS product_brand_id
            ,           SOL.of_product_categ_id                                     AS product_categ_id
            ,           SOL.of_presale_price                                        AS presale_price
            ,           SOL.of_presale_price_variation                              AS presale_price_variation
            ,           SOL.of_presale_margin                                       AS presale_margin
            ,           SOL.of_sale_price                                           AS sale_price
            ,           SOL.of_sale_price_variation                                 AS sale_price_variation
            ,           SOL.of_sale_margin                                          AS sale_margin"""

        return select_str

    def _from(self):
        from_str = """
            FROM        sale_order                                                  SO
            ,           sale_order_line                                             SOL
            ,           res_company                                                 RC"""
        return from_str

    def _where(self):
        where_str = """
            WHERE       SO.state                                                    IN ('presale', 'sale', 'done', 'closed')
            AND         SOL.order_id                                                = SO.id
            AND         SO.company_id                                               = RC.id"""

        return where_str

