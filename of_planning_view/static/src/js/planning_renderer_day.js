/** @odoo-module **/

import { patch } from '@web/core/utils/patch';
import { deserializeDateTime, serializeDateTime } from "@web/core/l10n/dates";
import { PlanningDayRenderer } from "@of_web_planning_view/js/planning_renderer_day";

patch(PlanningDayRenderer.prototype, '@of_planning_view/js/planning_renderer_day', {

    async onCreate({ rowId, columnIndex }) {
        // Adjusted to take the first column of an hour
        const columnIndexAdjusted = columnIndex - (columnIndex % 12)
        // use `this`here because we gonna get called from `PlanningWeekRenderer` or `PlanningDayRenderer`
        let { start, stop } = this.getColumnStartStop(columnIndexAdjusted);

        if (this.model.metaData.groupedBy[0] === 'of_resource_id') {
            // If there are interventions, we search for the real start, which is the last intervention stop
            const real_start = await this.model.orm.call('calendar.event', 'get_real_start', [
                eval(rowId)[0]['of_resource_id'][0],
                serializeDateTime(start),
                serializeDateTime(stop)
            ]);
            start = deserializeDateTime(real_start)
        }
        const context = await this.model.getDialogContext({
            rowId,
            start,
            stop,
            withDefault: true,
        });
        this.props.create(context);
    },

});
