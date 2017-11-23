# -*- coding: utf-8 -*-

from odoo import models, fields, api

class OFSaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.model
    def _init_field_date_delivered(self):
        # /!\ intervention_ids défini dans of_planning
        #print 'HAHAHAHAHAHAHAHAHAHAHAHAH\n\n\n'
        for order in self.search([]):
            lines_services = order.order_line.filtered(lambda line: line.product_id.type == 'service')
            lines_autres = order.order_line - lines_services
            lines_services_delivered  = lines_services.filtered(lambda line: line.qty_delivered != 0)
            lines_autres_delivered = self.env['sale.order.line']
            for line in lines_autres:
                moves = line.procurement_ids.mapped('move_ids')
                if moves and all([move.state == 'done' for move in moves]):  # la ligne est entièrement livrée
#                    line.of_date_delivered = moves.get_max_date_done()
                    line.of_date_delivered = fields.Date.from_string(max(moves.mapped('date')))
                    lines_autres_delivered |= line
                else:  # ne rien faire
                    continue
            if len(lines_autres_delivered) > 0:  # au moins une ligne qui n'est pas un service a été entièrement livrée
                max_date = max(lines_autres_delivered.mapped('of_date_delivered')) #lines_autres_delivered.get_max_date_delivered()
                lines_services_delivered.write({'of_date_delivered': max_date})
                #for line in lines_services_delivered:
                #    line.of_date_delivered = max_date
            else:  # aucune ligne qui n'est pas un service a été entièrement livrée
                planning_obj = self.env.get('of.planning')
                planning = planning_obj and planning_obj.search([('order_id', '=', order.id),
                                                                 ('state', 'in', ('confirm', 'done')),
                                                                 ('date_deadline', '&lt;', fields.Date.today())],
                                                                order="date_deadline DESC", limit=1)
                if planning:
                    lines_services_delivered.write({'of_date_delivered': planning[0].date_deadline})
                else:
                    for line in lines_services_delivered:
                        line.of_date_delivered = line.write_date
        return
