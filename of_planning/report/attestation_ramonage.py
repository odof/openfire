# -*- coding: utf-8 -*-

from odoo.report import report_sxw
from datetime import datetime

class attestation_ramonage(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(attestation_ramonage, self).__init__(cr, uid, name, context)
        self.localcontext.update({
            'get_client_info'   : self.get_client_info,
            'format_date'       : self.format_date,
            'get_price_ttc'     : self.get_price_ttc,
        })

    def format_date(self, date=False):
        if date:
            date = str(date)
            return datetime.strptime(date[:10], '%Y-%m-%d').strftime("%d/%m/%Y")
        else:
            return False

    def get_client_info(self, intervention):
        # nom, adresse, adresse suite, cp, ville
        info = ''
        if intervention.address_id:
            info += intervention.address_id.name or ''
            info += "\n" + intervention.address_id.contact_address or ''
        info = info.strip('\n')
        return info

    def get_price_ttc(self, intervention):
        """
        Retourne le prix ttc de pose au format texte.
        """
#         if not intervention.address_id:
#             return ''
#         part = intervention.address_id
#
#         partner = intervention.partner_id
#         address = intervention.address_id
#         pf = self.env['account.fiscal.position'].get_fiscal_position(partner, delivery_id=address)
#         if not pf:
#             return ''
#         pricelist_id = part.property_product_pricelist.id
#         product = intervention.tache_id.product_id
#         context = {
#             'uom' : product.uos_id.id,
#             'date': intervention.date,
#         }
#         price = self.env['product.pricelist'].price_get(self.cr, self.uid, [pricelist_id],
#                 product.id, 1.0, part.id, context)[pricelist_id]
        result = ''

        # Code copié depuis account.invoice.line.set_tax()
#         taxes = product.taxes_id
#         company_id = intervention.company_id or self.env.user.company_id
#         taxes = taxes.filtered(lambda r: r.company_id == company_id)
#
#         if price:
#
#             taxes = pf.map_tax(taxes, self.product_id, self.invoice_id.partner_id)
#             taxes = taxes.compute_all(price, product=product, partner=address)
#
#             result = taxes['total_excluded'] + taxes['taxes'] if taxes else price
#
#             # Fonctionalite du module of_sales, mais on s'evite ici de recopier le fichier attestation_ramonage en entier
#             if getattr(intervention.tache_id, 'arrondi') and round(abs(round(result)-result)-.01) == 0:
#                 result = round(result)
        return result

report_sxw.report_sxw(
    'report.of_planning.attestation_ramonage',
    'of.planning.intervention',
    'addons/of_planning/report/attestation_ramonage.rml',
    parser=attestation_ramonage
)
