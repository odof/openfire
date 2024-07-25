/** @odoo-module */

import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { download } from "@web/core/network/download";
import { unique } from "@web/core/utils/arrays";
import { useService } from "@web/core/utils/hooks";
import { sprintf } from "@web/core/utils/strings";
import { ActionMenus } from "@web/search/action_menus/action_menus";
import { Layout } from "@web/search/layout";
import { session } from "@web/session";
import { useModel } from "@web/views/model";
import { standardViewProps } from "@web/views/standard_view_props";
import { useSetupView } from "@web/views/view_hook";
import { ViewButton } from "@web/views/view_button/view_button";
import { useViewButtons } from "@web/views/view_button/view_button_hook";
import { ExportDataDialog } from "@web/views/view_dialogs/export_data_dialog";
import { loadJS, loadCSS } from "@web/core/assets";

import { Component, onWillStart, useSubEnv, useEffect, useRef } from "@odoo/owl";

export class MapViewHeaderButton extends ViewButton {
    async onClick() {
        const { clickParams, map } = this.props;
        const resIds = await map.getResIds(true);
        clickParams.buttonContext = {
            active_domain: this.props.domain,
            active_ids: resIds,
            active_model: map.resModel,
        };

        this.env.onClickViewButton({
            clickParams,
            getResParams: () => ({
                context: map.context,
                evalContext: map.evalContext,
                resModel: map.resModel,
                resIds,
            }),
        });
    }
}
MapViewHeaderButton.props = [...ViewButton.props, "map", "domain"];

// -----------------------------------------------------------------------------

export class MapController extends Component {
    static template = `of_map_view.MapView`;
    static components = {
        ActionMenus,
        MapViewHeaderButton,
        Layout,
        ViewButton,
    };

    static props = {
        ...standardViewProps,
        allowSelectors: { type: Boolean, optional: true },
        editable: { type: Boolean, optional: true },
        onSelectionChanged: { type: Function, optional: true },
        showButtons: { type: Boolean, optional: true },
        Model: Function,
        Renderer: Function,
        buttonTemplate: String,
        archInfo: Object,
    };

    static defaultProps = {
        allowSelectors: true,
        createRecord: () => {},
        editable: true,
        selectRecord: () => {},
        showButtons: true,
    };

    setup() {
        this.actionService = useService("action");
        this.dialogService = useService("dialog");
        this.notificationService = useService("notification");
        this.userService = useService("user");
        this.rpc = useService("rpc");
        this.rootRef = useRef("root");

        this.archInfo = this.props.archInfo;
        this.editable = this.props.editable ? this.archInfo.editable : false;
        this.multiEdit = this.archInfo.multiEdit;
        this.activeActions = this.archInfo.activeActions;
        const { fields } = this.props;
        const { rootState } = this.props.state || {};
        this.model = useModel(this.props.Model, {
            resModel: this.props.resModel,
            fields,
            activeFields: this.archInfo.activeFields,
            fieldNodes: this.archInfo.fieldNodes,
            handleField: this.archInfo.handleField,
            viewMode: "map",
            limit: this.archInfo.limit || this.props.limit,
            countLimit: this.archInfo.countLimit,
            multiEdit: this.multiEdit,
            rootState,
        });

        this.optionalActiveFields = [];

        onWillStart(async () => {
            this.isExportEnable = await this.userService.hasGroup(
                "base.group_allow_export"
            );
            // Loading leaflet
            await Promise.all([
                await loadCSS("/of_web_widgets/static/lib/leaflet/leaflet.css"),
                await loadJS(["/of_web_widgets/static/lib/leaflet/leaflet.js"]),
            ]);
            // Loading awesome markers
            await Promise.all([
                await loadCSS(
                    "/of_web_widgets/static/lib/awesome-markers/leaflet.awesome-markers.css"
                ),
                await loadJS([
                    "/of_web_widgets/static/lib/awesome-markers/leaflet.awesome-markers.js",
                ]),
            ]);
        });

        this.archiveEnabled =
            "active" in fields
                ? !fields.active.readonly
                : "x_active" in fields
                ? !fields.x_active.readonly
                : false;
        useSubEnv({ model: this.model }); // do this in useModel?
        useViewButtons(this.model, this.rootRef, {
            beforeExecuteAction: this.beforeExecuteActionButton.bind(this),
            afterExecuteAction: this.afterExecuteActionButton.bind(this),
        });
        useSetupView({
            rootRef: this.rootRef,
            beforeLeave: async () => {
                const map = this.model.root;
                const { editedRecord } = map;
                if (editedRecord && !(await map.unselectRecord(true))) {
                    return false;
                }
            },
            beforeUnload: async (ev) => {
                const { editedRecord } = this.model.root;
                if (editedRecord) {
                    const isValid = await editedRecord.urgentSave();
                    if (!isValid) {
                        ev.preventDefault();
                        ev.returnValue = "Unsaved changes";
                    }
                }
            },
            getLocalState: () => {
                return {
                    rootState: this.model.root.exportState(),
                };
            },
            getOrderBy: () => {
                return this.model.root.orderBy;
            },
        });

        useEffect(
            () => {
                if (this.props.onSelectionChanged) {
                    const resIds = this.model.root.selection.map(
                        (record) => record.resId
                    );
                    this.props.onSelectionChanged(resIds);
                }
            },
            () => [this.model.root.selection.length]
        );
    }

    async createRecord({ group } = {}) {
        const map = (group && group.map) || this.model.root;
        if (this.editable && !map.isGrouped) {
            if (!(map instanceof DynamicRecordmap)) {
                throw new Error("Map should be a DynamicRecordmap");
            }
            if (map.editedRecord) {
                await map.editedRecord.save();
            }
            if (!map.editedRecord) {
                await (group || map).createRecord({}, this.editable === "top");
            }
            this.render();
        } else {
            await this.props.createRecord();
        }
    }

    async openRecord(record) {
        if (this.archInfo.openAction) {
            this.actionService.doActionButton({
                name: this.archInfo.openAction.action,
                type: this.archInfo.openAction.type,
                resModel: record.resModel,
                resId: record.resId,
                resIds: record.resIds,
                context: record.context,
                onClose: async () => {
                    await record.model.root.load();
                    record.model.notify();
                },
            });
        } else {
            const activeIds = this.model.root.records.map(
                (datapoint) => datapoint.resId
            );
            this.props.selectRecord(record.resId, { activeIds });
        }
    }

    onClickCreate() {
        this.createRecord();
    }

    onClickDiscard() {
        const { editedRecord } = this.model.root;
        if (editedRecord.isVirtual) {
            this.model.root.removeRecord(editedRecord);
        } else {
            editedRecord.discard();
        }
    }

    onClickSave() {
        this.model.root.editedRecord.save();
    }

    onMouseDownDiscard(mouseDownEvent) {
        const map = this.model.root;
        map.blockUpdate = true;
        document.addEventmapener(
            "mouseup",
            (mouseUpEvent) => {
                if (mouseUpEvent.target !== mouseDownEvent.target) {
                    map.blockUpdate = false;
                    map.multiSave(map.editedRecord);
                }
            },
            { capture: true, once: true }
        );
    }

    getSelectedResIds() {
        return this.model.root.getResIds(true);
    }

    getActionMenuItems() {
        const { isM2MGrouped } = this.model.root;
        const otherActionItems = [];
        if (this.isExportEnable) {
            otherActionItems.push({
                key: "export",
                description: this.env._t("Export"),
                callback: () => this.onExportData(),
            });
        }
        if (this.archiveEnabled && !isM2MGrouped) {
            otherActionItems.push({
                key: "archive",
                description: this.env._t("Archive"),
                callback: () => {
                    const dialogProps = {
                        body: this.env._t(
                            "Are you sure that you want to archive all the selected records?"
                        ),
                        confirmLabel: this.env._t("Archive"),
                        confirm: () => {
                            this.toggleArchiveState(true);
                        },
                        cancel: () => {},
                    };
                    this.dialogService.add(ConfirmationDialog, dialogProps);
                },
            });
            otherActionItems.push({
                key: "unarchive",
                description: this.env._t("Unarchive"),
                callback: () => this.toggleArchiveState(false),
            });
        }
        if (this.activeActions.delete && !isM2MGrouped) {
            otherActionItems.push({
                key: "delete",
                description: this.env._t("Delete"),
                callback: () => this.onDeleteSelectedRecords(),
            });
        }
        return Object.assign({}, this.props.info.actionMenus, {
            other: otherActionItems,
        });
    }

    async onSelectDomain() {
        this.model.root.selectDomain(true);
        if (this.props.onSelectionChanged) {
            const resIds = await this.model.root.getResIds(true);
            this.props.onSelectionChanged(resIds);
        }
    }

    get className() {
        return this.props.className;
    }

    get nbSelected() {
        return this.model.root.selection.length;
    }

    get isPageSelected() {
        const { root } = this.model;
        return root.selection.length === root.records.length;
    }

    get isDomainSelected() {
        return this.model.root.isDomainSelected;
    }

    get nbTotal() {
        const map = this.model.root;
        return map.isGrouped ? map.nbTotalRecords : map.count;
    }

    onOptionalFieldsChanged(optionalActiveFields) {
        this.optionalActiveFields = optionalActiveFields;
    }

    get defaultExportList() {
        return unique(
            this.props.archInfo.columns
                .filter((col) => col.type === "field")
                .filter((col) => !col.optional || this.optionalActiveFields[col.name])
                .map((col) => this.props.fields[col.name])
                .filter((field) => field.exportable !== false)
        );
    }

    get display() {
        if (!this.env.isSmall) {
            return this.props.display;
        }
        const { controlPanel } = this.props.display;
        return {
            ...this.props.display,
            controlPanel: {
                ...controlPanel,
                "bottom-right": !this.nbSelected,
            },
        };
    }

    async downloadExport(fields, import_compat, format) {
        let ids = false;
        if (!this.isDomainSelected) {
            const resIds = await this.getSelectedResIds();
            ids = resIds.length > 0 && resIds;
        }
        const exportedFields = fields.map((field) => ({
            name: field.name || field.id,
            label: field.label || field.string,
            store: field.store,
            type: field.field_type || field.type,
        }));
        if (import_compat) {
            exportedFields.unshift({ name: "id", label: this.env._t("External ID") });
        }
        await download({
            data: {
                data: JSON.stringify({
                    import_compat,
                    context: this.props.context,
                    domain: this.model.root.domain,
                    fields: exportedFields,
                    ids,
                    model: this.model.root.resModel,
                }),
            },
            url: `/web/export/${format}`,
        });
    }

    async getExportedFields(model, import_compat, parentParams) {
        return await this.rpc("/web/export/get_fields", {
            ...parentParams,
            model,
            import_compat,
        });
    }

    /**
     * Opens the Export Dialog
     *
     * @private
     */
    async onExportData() {
        const dialogProps = {
            context: this.props.context,
            defaultExportList: this.defaultExportList,
            download: this.downloadExport.bind(this),
            getExportedFields: this.getExportedFields.bind(this),
            root: this.model.root,
        };
        this.dialogService.add(ExportDataDialog, dialogProps);
    }
    /**
     * Export Records in a xls file
     *
     * @private
     */
    async onDirectExportData() {
        await this.downloadExport(this.defaultExportList, false, "xlsx");
    }
    /**
     * Called when clicking on 'Archive' or 'Unarchive' in the sidebar.
     *
     * @private
     * @param {boolean} archive
     * @returns {Promise}
     */
    async toggleArchiveState(archive) {
        let resIds;
        const { isDomainSelected } = this.model.root;
        const total = this.model.root.count;
        if (archive) {
            resIds = await this.model.root.archive(true);
        } else {
            resIds = await this.model.root.unarchive(true);
        }
        if (
            isDomainSelected &&
            resIds.length === session.active_ids_limit &&
            resIds.length < total
        ) {
            this.notificationService.add(
                sprintf(
                    this.env._t(
                        "Of the %d records selected, only the first %d have been archived/unarchived."
                    ),
                    resIds.length,
                    total
                ),
                { title: this.env._t("Warning") }
            );
        }
    }

    get deleteConfirmationDialogProps() {
        const { root } = this.model;
        const body =
            root.isDomainSelected || root.selection.length > 1
                ? this.env._t("Are you sure you want to delete these records?")
                : this.env._t("Are you sure you want to delete this record?");
        return {
            body,
            confirm: async () => {
                const total = root.count;
                const resIds = await this.model.root.deleteRecords();
                this.model.notify();
                if (
                    root.isDomainSelected &&
                    resIds.length === session.active_ids_limit &&
                    resIds.length < total
                ) {
                    this.notificationService.add(
                        sprintf(
                            this.env._t(
                                `Only the first %s records have been deleted (out of %s selected)`
                            ),
                            resIds.length,
                            total
                        ),
                        { title: this.env._t("Warning") }
                    );
                }
            },
            cancel: () => {},
        };
    }

    async onDeleteSelectedRecords() {
        this.dialogService.add(ConfirmationDialog, this.deleteConfirmationDialogProps);
    }

    discardSelection() {
        this.model.root.records.forEach((record) => {
            record.toggleSelection(false);
        });
    }

    async beforeExecuteActionButton(clickParams) {
        if (clickParams.special !== "cancel" && this.model.root.editedRecord) {
            return this.model.root.editedRecord.save();
        }
    }

    async afterExecuteActionButton(clickParams) {}
}
