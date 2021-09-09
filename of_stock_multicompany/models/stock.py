# -*- coding: utf-8 -*-

from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo import models, fields, api, _, SUPERUSER_ID
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.exceptions import UserError


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    # A modifier car l'auto_init est appelé à chaques maj. Revenir à _auto_init_stock_multicompany.
    # @api.model_cr_context
    # def _auto_init(self):
    @api.model
    def _auto_init_stock_multicompany(self):
        stock_location_obj = self.env['stock.location']
        stock_quant_obj = self.env['stock.quant']
        stock_location_route_obj = self.env['stock.location.route']
        res_company_obj = self.env['res.company']

        # Pour les entrepôts
        for warehouse in self.with_context(active_test=False).search([]):
            company_id = res_company_obj.with_context(active_test=False).search(
                [('id','parent_of',warehouse.company_id.ids), ('parent_id','=',False)])
            warehouse.company_id = company_id.id

        # Pour les emplacements
        for location in stock_location_obj.with_context(active_test=False).search([('active','=',True)]):
            if location.usage == 'internal':
                company_id = res_company_obj.with_context(active_test=False).search(
                    [('id','parent_of',location.company_id.ids), ('parent_id','=',False)])
                location.company_id = company_id.id
            else:
                location.company_id = False

        # Pour les quants
        for quant in stock_quant_obj.with_context(active_test=False).search([]):
            company_id = res_company_obj.with_context(active_test=False).search(
                [('id','parent_of',quant.company_id.ids), ('parent_id','=',False)])
            quant.company_id = company_id.id

        # Pour les routes
        for location_route in stock_location_route_obj.with_context(active_test=False).search([]):
            location_route.company_id = False

        # cr = self._cr
        # cr.execute(
        #     "UPDATE stock_warehouse SET company_id = 1;"
        #     "UPDATE stock_location SET company_id = 1 WHERE usage = 'internal' AND active = True;"
        #     "UPDATE stock_location SET company_id = NULL WHERE usage != 'internal' AND active = True;"
        #     "UPDATE stock_location_route SET company_id = NULL;"
        #     "UPDATE stock_quant SET company_id = 1;")

        # return super(StockWarehouse, self)._auto_init()

    @api.model
    def _company_default_get_multicompany(self):
        res_company_obj = self.env['res.company']
        company_tmp = res_company_obj._company_default_get()

        company_id = res_company_obj.search([('id', 'parent_of', company_tmp.ids), ('parent_id', '=', False)])

        return company_id

    # On passe par _company_default_get_multicompany au lieu d'un create pour surcharger la création car company_id
    # ne passe jamais dans le create
    company_id = fields.Many2one(default=_company_default_get_multicompany)

    @api.multi
    def write(self, vals):
        if 'company_id' in vals:
            # On bloque tout le monde, sauf l'admin car nécessaire pour le _auto_init()
            if self.env.uid != SUPERUSER_ID:
                raise UserError(_("Vous ne pouvez pas modifier la société d'un entrepôt"))
        return super(StockWarehouse, self).write(vals)


class StockLocation(models.Model):
    _inherit = 'stock.location'

    @api.model
    def create(self, vals):
        if 'company_id' in vals:
            if vals['usage'] == 'internal':
                company_id = self.env['res.company'].search(
                    [('id','parent_of',[vals['company_id']]), ('parent_id','=',False)])
                vals['company_id'] = company_id.id
            else:
                vals['company_id'] = False
        return super(StockLocation, self).create(vals)

    @api.multi
    def write(self, vals):
        if 'company_id' in vals:
            # On bloque tout le monde, sauf l'admin car nécessaire pour le _auto_init()
            if self.env.uid != SUPERUSER_ID:
                raise UserError(_("Vous ne pouvez pas modifier la société d'un emplacement"))
        return super(StockLocation, self).write(vals)


class StockLocationRoute(models.Model):
    _inherit = 'stock.location.route'

    @api.model
    def create(self, vals):
        if vals.get('company_id', False):
            vals['company_id'] = False
        return super(StockLocationRoute, self).create(vals)

    @api.multi
    def write(self, vals):
        if 'company_id' in vals:
            # On bloque tout le monde, sauf l'admin car nécessaire pour le _auto_init()
            if self.env.uid != SUPERUSER_ID:
                raise UserError(_("Vous ne pouvez pas modifier la société d'une route"))
        return super(StockLocationRoute, self).write(vals)


class InventoryLine(models.Model):
    _inherit = 'stock.inventory.line'

    def _get_quants(self):
        domain = [('company_id', 'parent_of', self.company_id.id),
                  ('location_id', '=', self.location_id.id),
                  ('lot_id', '=', self.prod_lot_id.id),
                  ('product_id', '=', self.product_id.id),
                  ('owner_id', '=', self.partner_id.id),
                  ('package_id', '=', self.package_id.id)]
        if self.env['ir.values'].get_default('stock.config.settings', 'of_forcer_date_inventaire'):
            domain.append(('in_date', '<=', self.inventory_id.date))
        return self.env['stock.quant'].search(domain)


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    def _quants_get_reservation_domain(self, move, pack_operation_id=False, lot_id=False, company_id=False,
                                       initial_domain=None):
        force_date = self._context.get('force_date_done', False)
        if force_date:
            initial_domain = (initial_domain or [('qty', '>', 0.0)]) + [('in_date', '<=', force_date)]

        initial_domain = initial_domain if initial_domain is not None else [('qty', '>', 0.0)]
        domain = initial_domain + [('product_id', '=', move.product_id.id)]

        if pack_operation_id:
            pack_operation = self.env['stock.pack.operation'].browse(pack_operation_id)
            domain += [('location_id', '=', pack_operation.location_id.id)]
            if pack_operation.owner_id:
                domain += [('owner_id', '=', pack_operation.owner_id.id)]
            if pack_operation.package_id and not pack_operation.product_id:
                domain += [('package_id', 'child_of', pack_operation.package_id.id)]
            elif pack_operation.package_id and pack_operation.product_id:
                domain += [('package_id', '=', pack_operation.package_id.id)]
            else:
                domain += [('package_id', '=', False)]
        else:
            domain += [('location_id', 'child_of', move.location_id.id)]
            if move.restrict_partner_id:
                domain += [('owner_id', '=', move.restrict_partner_id.id)]

        if company_id:
            domain += [('company_id', 'parent_of', company_id)]
        else:
            domain += [('company_id', 'parent_of', move.company_id.id)]

        return domain


    # Dev repris d'HCL, à garder ?
    #
    # @api.model
    # def create(self, values):
    #     if 'company_id' in values:
    #         company = self.env['res.company'].browse(values['company_id'])
    #         if company and company.of_is_shop and company.parent_id:
    #             values['company_id'] = company.parent_id.id
    #     return super(StockQuant, self).create(values)

    @api.model
    def create(self, vals):
        if 'company_id' in vals:
            company_id = self.env['res.company'].search(
                [('id','parent_of',[vals['company_id']]), ('parent_id','=',False)])
            vals['company_id'] = company_id.id
        return super(StockQuant, self).create(vals)

    @api.multi
    def write(self, vals):
        if 'company_id' in vals:
            # On bloque tout le monde, sauf l'admin car nécessaire pour le _auto_init()
            if self.env.uid != SUPERUSER_ID:
                raise UserError(_("Vous ne pouvez pas modifier la société d'un quant"))
        return super(StockQuant, self).write(vals)

class ProcurementOrder(models.Model):
    _inherit = 'procurement.order'

    def _get_stock_move_values(self):
        ''' Returns a dictionary of values that will be used to create a stock move from a procurement.
        This function assumes that the given procurement has a rule (action == 'move') set on it.

        :param procurement: browse record
        :rtype: dictionary
        '''
        group_id = False
        if self.rule_id.group_propagation_option == 'propagate':
            group_id = self.group_id.id
        elif self.rule_id.group_propagation_option == 'fixed':
            group_id = self.rule_id.group_id.id
        date_expected = (datetime.strptime(self.date_planned, DEFAULT_SERVER_DATETIME_FORMAT) -
                         relativedelta(days=self.rule_id.delay or 0)).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        # it is possible that we've already got some move done, so check for the done qty and create
        # a new move with the correct qty
        qty_done = sum(self.move_ids.filtered(lambda move: move.state == 'done').mapped('product_uom_qty'))
        qty_left = max(self.product_qty - qty_done, 0)
        return {
            'name': self.name[:2000],
            'company_id': self.company_id.id,
            'product_id': self.product_id.id,
            'product_uom': self.product_uom.id,
            'product_uom_qty': qty_left,
            'partner_id': self.rule_id.partner_address_id.id or (self.group_id and self.group_id.partner_id.id) or
                False,
            'location_id': self.rule_id.location_src_id.id,
            'location_dest_id': self.location_id.id,
            'move_dest_id': self.move_dest_id and self.move_dest_id.id or False,
            'procurement_id': self.id,
            'rule_id': self.rule_id.id,
            'procure_method': self.rule_id.procure_method,
            'origin': self.origin,
            'picking_type_id': self.rule_id.picking_type_id.id,
            'group_id': group_id,
            'route_ids': [(4, route.id) for route in self.route_ids],
            'warehouse_id': self.rule_id.propagate_warehouse_id.id or self.rule_id.warehouse_id.id,
            'date': date_expected,
            'date_expected': date_expected,
            'propagate': self.rule_id.propagate,
            'priority': self.priority,
        }


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    @api.multi
    def write(self, vals):
        res = super(StockPicking, self).write(vals)
        # On modifie l'entrepôt des mouvements si le type de préparation change
        after_vals = {}
        if vals.get('picking_type_id'):
            picking_type = self.env['stock.picking.type'].browse(vals['picking_type_id'])
            if picking_type and picking_type.default_location_src_id:
                after_vals['warehouse_id'] = picking_type.warehouse_id.id
        if after_vals:
            self.mapped('move_lines').filtered(lambda move: not move.scrapped).write(after_vals)
        return res
