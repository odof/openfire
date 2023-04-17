# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import logging
from odoo import api, models

_logger = logging.getLogger('Hook.Tour')

# TODO: Remove me after the 10.0.3.0.0 version


class HookOFPlanningTour(models.Model):
    _inherit = 'of.planning.tournee'

    """Hook for OF Planning Tournee module for the 10.0.3.0.0 version"""
    @api.model
    def _get_hooks_data_request(self):
        return """SELECT
            OPT.id AS tour_id,
            OPI.id AS intervention_id,
            COALESCE(RP.geo_lat, HREMPADD.geo_lat) AS geo_lat,
            COALESCE(RP.geo_lng, HREMPADD.geo_lng) AS geo_lng,
            COALESCE(RP.city, HREMPADD.city) AS address_city,
            RP.of_secteur_tech_id AS secteur_tech_id
        FROM of_planning_tournee OPT
        JOIN of_planning_intervention_of_planning_tournee_rel OPTREL ON OPT.id = OPTREL.tournee_id
        JOIN of_planning_intervention OPI ON OPTREL.intervention_id = OPI.id
        LEFT JOIN res_partner RP ON OPI.address_id = RP.id
        LEFT JOIN hr_employee HREMP ON OPT.employee_id = HREMP.id
        LEFT JOIN res_partner HREMPADD ON HREMP.of_address_depart_id = HREMPADD.id
        WHERE
            %s
        ORDER BY OPT.id, OPI.date ASC""" % self._get_hooks_data_request_where()

    @api.model
    def _get_hooks_data_request_where(self):
        # Check if the column 'recurrency' exists in the table 'of_planning_intervention'
        # That column is bringed by the module 'of_planning_recurring'
        self._cr.execute(
            "SELECT EXISTS (SELECT 1 "
            "FROM information_schema.columns "
            "WHERE table_schema='public' AND table_name='of_planning_intervention' AND column_name='recurrency');")
        column_exists = self._cr.fetchone()[0]
        if column_exists:
            return """OPT.date >= current_date AND
            OPT.employee_id IS NOT NULL AND
            OPI.recurrency IS NOT TRUE
        """
        else:
            return """OPT.date >= current_date AND
                OPT.employee_id IS NOT NULL
            """

    @api.multi
    def _tour_update_hook(self, targeted_version='10.0.3.0.0'):
        """ Migrates tour data from the previous version of the module :
            - Compute the field 'name' for all tours
            - Compute the field 'weekday' for all tours
            - Compute the field 'start_address_id' and 'return_address_id' for all tours
            - Populate all tour lines
        """
        _logger.info("*" * 40)
        _logger.info("_tour_update_hook (version %s)" % targeted_version)
        _logger.info("*" * 40)
        module_self = self.env['ir.module.module'].search([('name', '=', 'of_planning_tournee')])
        _logger.info("module_self %s", module_self)
        _logger.info("module_self.latest_version %s", module_self.latest_version)
        actions_todo = module_self and module_self.latest_version < targeted_version or False
        if not actions_todo:
            _logger.info("No actions to do")
            return

        # Get all tours with a date and an employee to compute the name and the weekday of the tours
        self._cr.execute("SELECT id FROM of_planning_tournee OPT WHERE OPT.date IS NOT NULL")
        result = self._cr.fetchall()
        tours_with_date = self.with_context(prefetch_fields=False).browse([r[0] for r in result])
        _logger.info("* Force the computation of the weekday")
        tours_with_date._compute_date_weekday()
        _logger.info("* Populate lines for future interventions")

        # Get all data in SQL to avoid to load all the tours in memory and the use of filtered/search methods
        data_request = self._get_hooks_data_request()
        self._cr.execute(data_request)
        tours_data = self._cr.dictfetchall()
        data_by_tour = {}
        for data in tours_data:
            data_by_tour.setdefault(data['tour_id'], []).append(data)
        for tour_id, data in data_by_tour.iteritems():
            lines_values = []
            for idx, d in enumerate(data, 1):
                lines_values.append((0, 0, {
                    'sequence': idx,
                    'tour_id': tour_id,
                    'intervention_id': d['intervention_id'],
                    'geo_lat': d['geo_lat'],
                    'geo_lng': d['geo_lng'],
                    'address_city': d['address_city'],
                    'duration_one_way': False,
                    'distance_one_way': False
                }))
            tour = self.browse(tour_id)
            start_address = tour._get_start_address()
            return_address = tour._get_return_address()
            tour.with_context(skip_osrm_data_compute=True).write({
                'start_address_id': start_address.id,
                'return_address_id': return_address.id,
                'tour_line_ids': lines_values
            })
        # Transfert areas to the new field
        _logger.info("* Transfert areas to the new field")
        self._cr.execute('SELECT id, secteur_id FROM of_planning_tournee')
        tour_values = self._cr.fetchall()
        relation_values = [(tour_id, sector_id) for tour_id, sector_id in tour_values if sector_id]
        for tour_id, sector_id in relation_values:
            self._cr.execute('INSERT INTO tour_sector_rel (tour_id, sector_id) VALUES (%s, %s)', (tour_id, sector_id))
        # Adds others areas to the new M2M field
        sectors_by_tour = {}
        for tour_id, data in data_by_tour.iteritems():
            for d in data:
                if d['secteur_tech_id'] not in sectors_by_tour.get(tour_id, []) and d['secteur_tech_id']:
                    sectors_by_tour.setdefault(tour_id, []).append(d['secteur_tech_id'])
        for tour_id, sectors in sectors_by_tour.iteritems():
            for sector_id in sectors:
                self._cr.execute(
                    'INSERT INTO tour_sector_rel (tour_id, sector_id) VALUES (%s, %s)'
                    ' ON CONFLICT (tour_id, sector_id) DO NOTHING', (tour_id, sector_id))
        # Remove the old field 'secteur_id'
        _logger.info("* Remove the old field 'secteur_id'")
        self._cr.execute('ALTER TABLE of_planning_tournee DROP COLUMN secteur_id;')
