# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    @api.model_cr_context
    def _auto_init(self):
        cr = self._cr
        cr.execute(
            "SELECT * FROM information_schema.columns "
            "WHERE table_name = %s AND column_name = 'of_default_warehouse_id'", (self._table,))
        need_init = not cr.fetchall()

        super(ResCompany, self)._auto_init()

        if need_init:
            cr.execute("SELECT company_id, partner_id, id FROM stock_warehouse")
            # Dictionnaire {company_id: [partner_id, warehouse_id]}
            company_warehouses_dict = {}
            for row in cr.fetchall():
                company_warehouses_dict.setdefault(row[0], []).append(row[1:])

            cr.execute("SELECT id, parent_id, partner_id FROM res_company")
            # Dictionnaire {company_id: [parent_id, partner_id]}
            company_vals_dict = {}
            for row in cr.fetchall():
                company_vals_dict[row[0]] = row[1:]
            for company_id in company_vals_dict:
                warehouse_id = False
                wh_company_id = -1
                addresses = []
                while True:
                    if wh_company_id == -1:
                        wh_company_id = company_id
                    elif wh_company_id:
                        wh_company_id = company_vals_dict[wh_company_id][0]
                    else:
                        # Aucun entrepôt trouvé. Ce cas ne devrait pas se produire
                        break
                    if wh_company_id:
                        addresses.append(company_vals_dict[wh_company_id][1])
                    else:
                        addresses.append(None)
                    comp_wh = company_warehouses_dict.get(wh_company_id)
                    if not comp_wh:
                        continue

                    # Au moins un entrepôt est trouvé. On sélectionne le plus pertinent.
                    if len(comp_wh) == 1:
                        warehouse_id = comp_wh[0][1]
                        break
                    for address_id in addresses:
                        for wh_data in comp_wh:
                            if wh_data[0] == address_id:
                                warehouse_id = wh_data[1]
                                break
                        if warehouse_id:
                            break
                    else:
                        warehouse_id = comp_wh[0][1]
                    break
                if warehouse_id:
                    cr.execute(
                        "UPDATE res_company SET of_default_warehouse_id = %s WHERE id = %s",
                        (warehouse_id, company_id)
                    )

    of_default_warehouse_id = fields.Many2one('stock.warehouse', string=u"Entrepôt par défaut", required=True)
    of_is_stock_owner = fields.Boolean(
        string=u"Est le propriétaire du stock",
        help=u"ATTENTION, ce paramètre n'est utile qu'en vue d'installer le module 'of_stock_multicompany'."
             u"Il permet de définir la société comme propriétaire du stock de toutes ses sociétés enfant, "
             u"c'est à dire que chaque société enfant pourra partager son stock avec ses sociétés soeurs.")
