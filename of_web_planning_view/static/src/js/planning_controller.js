/** @odoo-module **/

import { _lt, _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { Layout } from "@web/search/layout";
import { useModel } from "@web/views/model";
import { useSetupView } from "@web/views/view_hook";
import { standardViewProps } from "@web/views/standard_view_props";
import { FormViewDialog } from "@web/views/view_dialogs/form_view_dialog";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { Component, useRef } from "@odoo/owl";

const { DateTime } = luxon;

const SCALE_LABELS = {
    day: _lt("Day"),
    week: _lt("Week"),
};


export class PlanningController extends Component {
    static components = { Layout };
    static template = "of_web_planning_view.PlanningController";
    static props = {
        ...standardViewProps,
        Model: Function,
        Renderer: Function,
        buttonTemplate: String,
        modelParams: Object,
        scrollPosition: { type: Object, optional: true },
    };

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.dialogService = useService("dialog");

        this.model = useModel(this.props.Model, this.props.modelParams);

        useSetupView({
            rootRef: useRef("root"),
            getLocalState: () => {
                return { metaData: this.model.metaData };
            },
        });
    }

    get scaleLabels() {
        return SCALE_LABELS;
    }
    get className() {
        return this.props.className;
    }

    getTodayDay() {
        return DateTime.local().day;
    }

    onNextPeriodClicked() {
        this.model.setFocusDate("next");
    }

    onPreviousPeriodClicked() {
        this.model.setFocusDate("previous");
    }

    onTodayClicked() {
        this.model.setFocusDate();

        // Center the view on today
        if (this.model.scale.id == 'day') {
            const selectedItems = document.querySelectorAll(".o_planning_header_cell.o_planning_today");
            const selectedItem = selectedItems[Math.floor(selectedItems.length / 2)];
            if (selectedItem) {
                selectedItem.scrollIntoView({ behavior: "smooth", inline: "center" });
            }
        }
    }

    onScaleSwitched( scale ) {
        this.model.setScale(scale);
    }

    setUnaffectedRecords() {
        this.model.setUnaffectedRecords();
    }

    /**
     * @param {Record<string, any>} [context]
     */
    create(context) {
        const { createAction } = this.model.metaData;
        if (createAction) {
            this.actionService.doAction(createAction, {
                additionalContext: context,
                onClose: () => {
                    this.model.fetchData();
                },
            });
        } else {
            this.openDialog({ context });
        }
    }

    /**
     * Opens dialog to add/edit/view a record
     *
     * @param {Record<string, any>} props FormViewDialog props
     * @param {Record<string, any>} [options={}]
     */
    openDialog(props, options = {}) {
        const { canDelete, canEdit, resModel, formViewId: viewId } = this.model.metaData;

        const title = props.title || (props.resId ? _t("Open") : _t("Create"));

        let removeRecord;
        if (canDelete && props.resId) {
            removeRecord = () => {
                return new Promise((resolve) => {
                    this.dialogService.add(ConfirmationDialog, {
                        body: _t("Are you sure to delete this record?"),
                        confirm: async () => {
                            await this.orm.unlink(resModel, [props.resId]);
                            resolve();
                        },
                        cancel: () => {},
                    });
                });
            };
        }

        this.closeDialog = this.dialogService.add(
            FormViewDialog,
            {
                title,
                resModel,
                viewId,
                resId: props.resId,
                mode: canEdit ? "edit" : "readonly",
                context: props.context,
                removeRecord,
            },
            {
                ...options,
                onClose: () => {
                    this.closeDialog = null;
                    this.model.fetchData();
                },
            }
        );
    }

    onAddClicked() {
        const { scale, startDate, stopDate, focusDate } = this.model.metaData;
        const today = DateTime.local().startOf("day");
        let context;
        if (scale.id !== "day" && startDate <= today.endOf("day") && today <= stopDate) {
            let start = today;
            let stop;
            if (scale.id == "week") {
                start = today.set({ hours: 8, minutes: 0, seconds: 0 });
                stop = today.set({ hours: 17, minutes: 0, seconds: 0 });
            } else {
                stop = today.endOf(scale.interval);
            }
            context = this.model.getDialogContext({ start, stop, withDefault: true });
        } else {
            const start = focusDate.startOf(scale.id);
            const stop = focusDate.endOf(scale.id);
            context = this.model.getDialogContext({ start, stop, withDefault: true });
        }
        this.create(context);
    }
}
