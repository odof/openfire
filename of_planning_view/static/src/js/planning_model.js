/** @odoo-module **/

import { patch } from '@web/core/utils/patch';
import { PlanningModel } from "@of_web_planning_view/js/planning_model";

patch(PlanningModel.prototype, '@of_planning_view/js/planning_model', {

    _getGroupedBy(metaData, searchParams) {
        let groupedBy = [...searchParams.groupBy];
        groupedBy = this._filterDateIngroupedBy(metaData, groupedBy);

        // Le champs of_gb_employee_id ne fonctionne pas avec la vue planning,
        // qui est de base déjà groupée par ressource
        for (const [i, value] of groupedBy.entries()) {
            if (value == 'of_gb_employee_id') {
                groupedBy[i] = 'of_resource_id';
            }
        }

        if (!groupedBy.length) {
            groupedBy = metaData.defaultGroupBy;
        }

        return groupedBy;
    }
});
