
/** @odoo-module **/

import { usePopover } from "@web/core/popover/popover_hook";
import { _t } from "@web/core/l10n/translation";
import { useOwnedDialogs, useService } from "@web/core/utils/hooks";
import { useState, onWillUpdateProps } from "@odoo/owl";

import { patch } from '@web/core/utils/patch';
import { CalendarFilterPanel } from "@web/views/calendar/filter_panel/calendar_filter_panel";

patch(CalendarFilterPanel.prototype, '@of_planning/js/calendar_filter_panel', {

    setup() {
        this.state = useState({
            collapsed: {},
            fieldRev: 1,
        });
        this.addDialog = useOwnedDialogs();
        this.orm = useService("orm");
        this.popover = usePopover();
        this.removePopover = null;

        // On récupère le type de vue (event, intervention) pour les calendar.event
        // Undefined pour les autres modèles
        this.context = this.env.searchModel._context;
        this.type = this.context.default_of_type;

        onWillUpdateProps(this.updateLabels);

        this.updateLabels();
    },

    updateLabels() {
        // On modifie le nom du filtre Participants par Techniciens
        if (this.type == 'intervention') {
            this.props.model.data.filterSections.partner_ids.label = _t("Operators");
        }
    },

    async loadSource(section, request) {
        const resModel = this.props.model.fields[section.fieldName].relation;
        var domain = [
            ["id", "not in", section.filters.filter((f) => f.type !== "all").map((f) => f.value)],
        ];

        // Dans le cas où on est sur les interventions, on restreint aux employés
        if (this.type == 'intervention') {
            this.props.model.data.filterSections.partner_ids.label = _t("Operators");
            const partnerIds = await this.orm.call('calendar.event', "get_employee_ids", []);
            domain = domain.concat([["id", "in", partnerIds]]);
        }

        const records = await this.orm.call(resModel, "name_search", [], {
            name: request,
            operator: "ilike",
            args: domain,
            limit: 8,
            context: {},
        });

        const options = records.map((result) => ({
            value: result[0],
            label: result[1],
        }));

        if (records.length > 7) {
            options.push({
                label: _t("Search More..."),
                action: () => this.onSearchMore(section, resModel, domain, request),
            });
        }

        if (records.length === 0) {
            options.push({
                label: _t("No records"),
                classList: "o_m2o_no_result",
                unselectable: true,
            });
        }

        return options;
    }
});
