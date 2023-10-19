from odoo import fields, models


class OFRapportOpenflamWizard(models.TransientModel):
    _name = 'of.rapport.openflam.wizard'
    _description = 'Rapport Openflam'

    file_name = fields.Char("Nom du fichier")
    file = fields.Binary("file")
    company_ids = fields.Many2many('res.company', string="Sociétés")
    user_company_id = fields.Many2one('res.company')
    date = fields.Date("Date de création", default=fields.Date.today())
    report_model = fields.Selection([("todo", "todo")], string="Modèle de rapport", required=True)
    period_n = fields.Many2one('date.range', string="Période")
    period_n1 = fields.Many2one('date.range', string="Période")
    product_ids = fields.Many2many('product.template', string="Articles")
    partner_ids = fields.Many2many('res.partner', string="Clients")
    category_ids = fields.Many2many('product.category', string="Catégories d'articles")
    stats_partner = fields.Boolean(string="Stats/articles/clients", default=True)
    stats_product = fields.Boolean(string=u"Stats/clients/catégories d'articles", default=True)
    filtre_client = fields.Boolean(string="Filtre par client")
    filtre_article = fields.Boolean(string="Filtre par article")

    debut_n = fields.Date(string="Début")
    fin_n = fields.Date(string="Fin")
    debut_n1 = fields.Date(string="Début")
    fin_n1 = fields.Date(string="Fin")
    type_filtre_date = fields.Selection(
        [("period", "Périodes"), ("date", "Dates")], string="Type de filtre", default="period"
    )
    brand_ids = fields.Many2many('of.product.brand', string="Marques")
    stats_brand = fields.Boolean(string="Stats/marques/clients", default=True)
    etiquette_ids = fields.Many2many('res.partner.category', string="Étiquettes clients")

    def button_print(self):
        pass
