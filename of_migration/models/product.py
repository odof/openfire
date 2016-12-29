# -*- coding: utf-8 -*-

from openerp import models, api
from main import MAGIC_COLUMNS_VALUES, MAGIC_COLUMNS_TABLES

class import_product(models.AbstractModel):
    _inherit = "of.migration"

    @api.model
    def import_product_uom_categ(self):
        self.model_data_mapping('product_uom_categ_61', 'product.uom.categ')

    def import_product_uom(self):
        self.model_data_mapping('product_uom_61', 'product.uom')

        cr = self._cr
        cr.execute("SELECT last_value FROM product_uom_id_seq")
        last_id = cr.fetchone()[0]

        # Association des product_uom_61 aux nouveaux product_uom 9.0
        cr.execute("UPDATE product_uom_61 SET id_90 = nextval('product_uom_id_seq') WHERE id_90 IS NULL")

        fields_90 = ['category_id', 'name', 'rounding', 'active', 'factor', 'uom_type']

        values = {field: "tab."+field for field in fields_90}
        values.update({
            'id'         : 'tab.id_90',
            'category_id': 'categ.id_90',
        })
        values.update(MAGIC_COLUMNS_VALUES)

        where_clause = "tab.id_90 > %s" % last_id

        tables = [
            ('tab', 'product_uom_61', False, False, False),
            ('categ', 'product_uom_categ_61', 'id', 'tab', 'category_id'),
        ] + MAGIC_COLUMNS_TABLES

        self.insert_values('product.uom', values, tables, where_clause=where_clause)

    @api.model
    def import_product_category(self):
        cr = self._cr

        # Suppression de tous les articles existants
        self.env['product.product'].search([]).unlink()
        cr.execute("SELECT setval('product_product_id_seq', 1, 'f')")
        cr.execute("SELECT setval('product_template_id_seq', 1, 'f')")

        # Suppression de toutes les catégories de produits existantes
        self.env['product.category'].search([]).unlink()

        # Association des product_uom_61 aux nouveaux product_uom 9.0
        cr.execute("UPDATE product_category_61 SET id_90 = id")

        # Copie des catégories en v9.0
        fields_90 = ['name', 'sequence', 'type', 'parent_left', 'parent_right']

        values = {field: "tab."+field for field in fields_90}
        values['id'] = 'tab.id_90'
        values.update(MAGIC_COLUMNS_VALUES)

        tables = [
            ('tab', 'product_category_61', False, False, False)
        ] + MAGIC_COLUMNS_TABLES

        self.insert_values('product.category', values, tables)

        # parent_id
        cr.execute("UPDATE product_category AS c90 \n"
                   "SET parent_id = c61.parent_id\n"
                   "FROM product_category_61 AS c61\n"
                   "WHERE c90.id = c61.id")

        cr.execute("SELECT setval('product_category_id_seq', max(id)) FROM product_category")

    @api.model
    def import_product_template(self):
        cr = self._cr

        # Pour la migration on considère qu'un product_template ne doit avoir qu'un product_product
        cr.execute("SELECT product_tmpl_id, count(*) FROM product_product_61 GROUP BY product_tmpl_id HAVING count(*) > 1 LIMIT 1")
        row = cr.fetchone()
        if row and row[1] > 1:
            raise ValueError(u"Product_template id = %s nombre de produits = %s" % tuple(row))

        # Vérification que tous les product_template ont un product_product associé
        cr.execute("SELECT count(*) FROM product_product_61")
        nb_p = cr.fetchone()
        cr.execute("SELECT count(*) FROM product_template_61")
        nb_t = cr.fetchone()
        if nb_p != nb_t:
            raise ValueError(u"Nombre de product_template = %s ; Nombre de product_product = %s" % (nb_t, nb_p))

        # Association des product_template_61 aux nouveaux product_template 9.0
        cr.execute("UPDATE product_template_61 SET id_90 = nextval('product_template_id_seq')")

        # Création des template

        fields_90 = ['uom_id', 'categ_id', 'uom_po_id', 'company_id', 'color', 'track_service', 'purchase_method', 'invoice_policy',
                     'tracking', 'warranty', 'list_price', 'weight', 'description_purchase', 'sale_ok', 'product_manager', 'state',
                     'description_sale', 'description', 'volume', 'rental', 'name', 'type', 'sale_delay', 'purchase_ok']

        values = {field: "tab."+field for field in fields_90}
        values.update({
            'id'             : "tab.id_90",
            'uom_id'         : "uom.id_90",
            'categ_id'       : "categ.id_90",
            'uom_po_id'      : "uom_po.id_90",
            'company_id'     : "comp.id_90",
            'color'          : "0", # On pourrait chercher le color du product_product en 6.1, mais il n'est jamais utilisé
            'track_service'  : "'manual'",
            'purchase_method': "'receive'",
            'invoice_policy' : "'order'",
            'tracking'       : "'none'",
        })
        values.update(MAGIC_COLUMNS_VALUES)

        tables = [
            ('tab', 'product_template_61', False, False, False),
            ('uom', 'product_uom_61', 'id', 'tab', 'uom_id'),
            ('categ', 'product_category_61', 'id', 'tab', 'categ_id'),
            ('uom_po', 'product_uom_61', 'id', 'tab', 'uom_po_id'),
            ('comp', 'res_company_61', 'id', 'tab', 'company_id')
        ] + MAGIC_COLUMNS_TABLES

        self.insert_values('product.template', values, tables)

    def import_product_product(self):
        cr = self._cr

        # Association des product_product_61 aux nouveaux product_product 9.0
        cr.execute("UPDATE product_product_61 SET id_90 = nextval('product_product_id_seq')")

        # Création des product
        fields_90 = ['product_tmpl_id', 'weight', 'volume', 'default_code', 'name_template', 'barcode', 'active']

        values = {field: "tab."+field for field in fields_90}
        values.update({
            'id'             : 'tab.id_90',
            'product_tmpl_id': 'tmpl.id_90',
            'weight'         : 'tmpl.weight',
            'volume'         : 'tmpl.volume',
            'barcode'        : 'tab.ean13',
        })
        values.update(MAGIC_COLUMNS_VALUES)

        tables = [
            ('tab', 'product_product_61', False, False, False),
            ('tmpl', 'product_template_61', 'id', 'tab', 'product_tmpl_id'),
        ] + MAGIC_COLUMNS_TABLES

        self.insert_values('product.product', values, tables)

        # En v9 le champ active existe aussi dans product_template
        cr.execute("UPDATE product_template AS t\n"
                   "SET active=p.active\n"
                   "FROM product_product AS p\n"
                   "WHERE p.product_tmpl_id = t.id")

        # N.B. Le champ standard_price du product_template en 6.1 est devenu fields.property de product_product en 9.0
        # Ce champ n'a pas besoin d'être migré (probablement en raison de la redondance avec list_price)

    @api.model
    def import_product_supplierinfo(self):
        cr = self._cr

        # Association des product_product_61 aux nouveaux product_product 9.0
        cr.execute("UPDATE product_supplierinfo_61 SET id_90 = nextval('product_supplierinfo_id_seq')")

        fields_90 = ['name', 'product_tmpl_id', 'price', 'currency_id', 'company_id',
                     'qty', 'sequence', 'delay', 'min_qty', 'product_code', 'product_name']

        values = {field: "tab."+field for field in fields_90}
        values.update({
            'id'             : 'tab.id_90',
            'name'           : 'partner.id_90',
            'product_tmpl_id': 'tmpl.id_90',
            'price'          : 'tmpl.list_price',
            'currency_id'    : '1', # Monnaie Euro
            'company_id'     : 'comp.id_90',
        })
        values.update(MAGIC_COLUMNS_VALUES)

        tables = [
            ('tab', 'product_supplierinfo_61', False, False, False),
            ('tmpl', 'product_template_61', 'id', 'tab', 'product_id'),
            ('partner', 'res_partner_61', 'id', 'tab', 'name'),
            ('comp', 'res_company_61', 'id', 'tab', 'company_id'),
        ] + MAGIC_COLUMNS_TABLES

        self.insert_values('product.supplierinfo', values, tables)

    @api.model
    def import_product_pricelist(self):
        self.model_data_mapping('product_pricelist_61', 'product.pricelist')

    @api.model
    def import_module_product(self):
        return (
            'product_uom_categ',
            'product_uom',
            'product_category',
            'product_template',
            'product_product',
            'product_supplierinfo',
            'product_pricelist',
            #@todo: product_pricelist_item
        )
