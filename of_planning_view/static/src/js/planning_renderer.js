/** @odoo-module **/

import { patch } from '@web/core/utils/patch';
import { PlanningRenderer } from "@of_web_planning_view/js/planning_renderer";

patch(PlanningRenderer.prototype, '@of_planning_view/js/planning_renderer', {
    getSecondaryTextForPill (pill) {
        return  pill.record.of_task_id ? pill.record.of_task_id[1] : "";
    }
});
