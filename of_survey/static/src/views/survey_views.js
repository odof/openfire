/** @odoo-module **/

import { registry } from '@web/core/registry';
import { ListRenderer } from "@web/views/list/list_renderer";
import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";
import { listView } from '@web/views/list/list_view';
import { kanbanView } from '@web/views/kanban/kanban_view';
import { useService } from "@web/core/utils/hooks";

const { useEffect, useRef } = owl;

export function useOFSurveyLoadSampleHook(selector) {
    const rootRef = useRef("root");
    const actionService = useService("action");
    const orm = useService('orm');
    let isLoadingSample = false;
    /**
     * Load and show the sample survey related to the clicked element,
     * when there is no survey to display.
     * We currently have 3 different samples to load:
     * - Sample Feedback Form
     * - Sample Certification
     * - Sample Live Presentation
     */
    const loadSample = async (method) => {
        // Prevent loading multiple samples if double clicked
        isLoadingSample = true;
        const action = await orm.call('of.survey.survey', method);
        actionService.doAction(action);
    };
    useEffect(
        (elems) => {
            if (!elems || !elems.length) {
                return;
            }
            const handler = (ev) => {
                if (!isLoadingSample) {
                    const surveyMethod = ev.currentTarget.closest('.o_survey_sample_container').getAttribute('action');
                    loadSample(surveyMethod);
                }
            }
            for (const elem of elems) {
                elem.addEventListener('click', handler);
            }
            return () => {
                for (const elem of elems) {
                    elem.removeEventListener('click', handler);
                }
            };
        },
        () => [rootRef.el && rootRef.el.querySelectorAll(selector)]
    );
};

export class OFSurveyListRenderer extends ListRenderer {
    setup() {
        super.setup();

        if (this.canCreate) {
            useOFSurveyLoadSampleHook('.o_survey_load_sample');
        }
    }
};

registry.category('views').add('of_survey_view_tree', {
    ...listView,
    Renderer: OFSurveyListRenderer,
});

export class OFSurveyKanbanRenderer extends KanbanRenderer {
    setup() {
        super.setup();
        this.canCreate = this.props.archInfo.activeActions.create;
        if (this.canCreate) {
            useOFSurveyLoadSampleHook('.o_survey_load_sample');
        }
    }
};

registry.category('views').add('of_survey_view_kanban', {
    ...kanbanView,
    Renderer: OFSurveyKanbanRenderer,
});

