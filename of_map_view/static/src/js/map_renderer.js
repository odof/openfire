/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { Domain } from "@web/core/domain";
import { useBus, useService } from "@web/core/utils/hooks";
import { useBounceButton } from "@web/views/view_hook";
import { localization } from "@web/core/l10n/localization";
import { ListPopupMap } from "@of_web_widgets/components/popup";
import { renderToString } from "@web/core/utils/render";

import {
    Component,
    onMounted,
    useExternalListener,
    useRef,
    useEffect,
    onWillUnmount,
} from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";

export class MapRenderer extends Component {
    static template = "of_map_view.MapRenderer";
    static LONG_TOUCH_THRESHOLD = 400;

    static components = {
        ListPopupMap,
    };

    static props = [
        "activeActions?",
        "map",
        "archInfo",
        "openRecord",
        "onAdd?",
        "cycleOnTab?",
        "allowSelectors?",
        "editable?",
        "noContentHelp?",
        "nestedKeyOptionalFieldsData?",
        "readonly?",
        "onOptionalFieldsChanged?",
    ];

    static defaultProps = {
        hasSelectors: true,
        cycleOnTab: true,
    };

    setup() {
        this.uiService = useService("ui");
        this.notificationService = useService("notification");
        this.keyOptionalFields = this.createKeyOptionalFields();
        useExternalListener(document, "click", this.onGlobalClick.bind(this));

        this.longTouchTimer = null;
        this.touchStartMs = 0;

        /**
         * When resizing, it's possible that the pointer is not above the resize
         * handle (by some few pixel difference). During this scenario, click event
         * will be triggered on the column title which will reorder the column.
         * Column resize that triggers a reorder is not a good UX and we prevent this
         * using the following state variables: `resizing` and `preventReorder` which
         * are set during the column's click (onClickSortColumn), mouseup
         * (onColumnTitleMouseUp) and onStartResize events.
         */
        this.resizing = false;
        this.preventReorder = false;

        this.creates = this.props.archInfo.creates.length
            ? this.props.archInfo.creates
            : [{ type: "create", string: this.env._t("Add a line") }];

        this.archInfo = this.props.archInfo;
        this.activeRowId = null;
        this.model = this.props.map.model;
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.mapContainerRef = useRef("mapContainer");
        this.popups = {};
        this.map = false;
        this.records = [];
        this.markers = {};

        onWillUnmount(this.onWillUnmount);
        onMounted(() => {
            this.activeElement = this.uiService.activeElement;
        });
        this.rootRef = useRef("root");
        this.resequencePromise = Promise.resolve();

        if (this.env.searchModel) {
            useBus(this.env.searchModel, "focus-view", () => {
                if (this.props.map.model.useSampleModel) {
                    return;
                }

                const nextTh = this.tableRef.el.querySelector("thead th");
                const toFocus = getElementToFocus(nextTh);
                this.focus(toFocus);
                this.tableRef.el
                    .querySelector("tbody")
                    .classList.add("o_keyboard_navigation");
            });
        }

        useBounceButton(this.rootRef, () => {
            return this.showNoContentHelper;
        });

        useEffect(
            () => {
                const { latitudeField, longitudeField } = this.props.archInfo;

                if (!this.map) {
                    this.map = L.map(this.mapContainerRef.el).setView(
                        [48.056, -2.818],
                        8
                    );
                    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
                        center: [39.73, -104.99],
                        attribution:
                            '&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>',
                    }).addTo(this.map);

                    let arrayOfMarkers = [];
                    this.records.map((record) => {
                        if (record.data[latitudeField] && record.data[longitudeField]) {
                            arrayOfMarkers.push([
                                record.data[latitudeField],
                                record.data[longitudeField],
                            ]);
                        }
                    });

                    if (arrayOfMarkers.length) {
                        const bounds = new L.LatLngBounds(arrayOfMarkers);
                        this.map.fitBounds(bounds);
                    }
                }

                this.updateMap();
            },
            () => [this.model.root.records]
        );
        useExternalListener(window, "resize", () => {});
        this.isRTL = localization.direction === "rtl";
    }

    switchView(record_id) {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "Contact",
            views: [[false, "form"]],
            res_model: this.props.map.resModel,
            res_id: record_id,
        });
    }

    onClickMarker(record) {
        this.popups[record.id].toggle();
        record.selected = !record.selected;
        record.model.trigger("update");
    }

    onMouseOverMarker(record) {
        this.popups[record.id].highlight();
    }

    onMouseOutMarker(record) {
        this.popups[record.id].lowlight();
    }

    updateMap() {
        const { latitudeField, longitudeField } = this.props.archInfo;

        this.removeMarkers();
        this.closePopups();
        this.removePopups();
        let arrayOfMarkers = [];
        this.model.root.records.map((record) => {
            if (record.data[latitudeField] && record.data[longitudeField]) {
                this.addMarker(record);
                arrayOfMarkers.push([
                    record.data[latitudeField],
                    record.data[longitudeField],
                ]);
            }
        });

        if (arrayOfMarkers.length) {
            var bounds = new L.LatLngBounds(arrayOfMarkers);
            this.map.fitBounds(bounds);
        }
    }

    removeMarkers() {
        const self = this;
        Object.keys(this.markers).forEach(function (key, index) {
            self.map.removeLayer(self.markers[key]);
        });
        this.markers = {};
    }

    addMarker(record) {
        const { latitudeField, longitudeField, colorField } = this.props.archInfo;

        let markerLocation = new L.LatLng(
            record.data[latitudeField],
            record.data[longitudeField]
        );

        let marker = new L.Marker(markerLocation, {
            icon: L.AwesomeMarkers.icon({
                icon: "circle",
                markerColor: record.data[colorField] || "blue",
            }),
        });

        // Ajout du tooltip
        const tooltip = L.tooltip({ offset: [15, -25] })
            .setLatLng([record.data[latitudeField], record.data[longitudeField]])
            .setContent(this.getTooltip(record));

        marker.bindTooltip(tooltip);

        this.markers[record.id] = marker;
        this.map.addLayer(marker);

        marker.on({
            mouseup: this.onClickMarker.bind(this, record),
            tooltipopen: this.onMouseOverMarker.bind(this, record),
            tooltipclose: this.onMouseOutMarker.bind(this, record),
        });
    }

    removePopups() {
        this.popups = {};
    }

    closePopups() {
        for (let index = 0; index < Object.keys(this.popups).length; index++) {
            this.popups[Object.keys(this.popups)[index]].state.show = false;
        }
    }

    getTooltip(record) {
        const { tooltipView } = this.props.archInfo;
        return renderToString(tooltipView, { record: record.data });
    }

    /* On supprime la carte au changement de page/vue */
    onWillUnmount() {
        if (this.map) {
            this.map.remove();
        }
    }

    displaySaveNotification() {
        this.notificationService.add(
            this.env._t('Please click on the "save" button first'),
            {
                type: "danger",
            }
        );
    }

    get hasSelectors() {
        return this.props.allowSelectors;
    }

    add(params) {
        if (this.canCreate) {
            this.props.onAdd(params);
        }
    }

    get activeActions() {
        return this.props.activeActions || {};
    }

    /**
     * No records, no groups.
     */
    get isEmpty() {
        return !this.props.map.records.length;
    }

    get fields() {
        return this.props.map.fields;
    }

    createKeyOptionalFields() {
        let keyParts = {
            fields: this.props.map.fieldNames,
            model: this.props.map.resModel,
            viewMode: "map",
            viewId: this.env.config.viewId,
        };

        if (this.props.nestedKeyOptionalFieldsData) {
            keyParts = Object.assign(keyParts, {
                model: this.props.nestedKeyOptionalFieldsData.model,
                viewMode: this.props.nestedKeyOptionalFieldsData.viewMode,
                relationalField: this.props.nestedKeyOptionalFieldsData.field,
                subViewType: "map",
            });
        }

        const parts = ["model", "viewMode", "viewId", "relationalField", "subViewType"];
        const viewIdentifier = ["optional_fields"];
        parts.forEach((partName) => {
            if (partName in keyParts) {
                viewIdentifier.push(keyParts[partName]);
            }
        });
        keyParts.fields
            .sort((left, right) => (left < right ? -1 : 1))
            .forEach((fieldName) => {
                return viewIdentifier.push(fieldName);
            });
        return viewIdentifier.join(",");
    }

    get displayOptionalFields() {
        return this.getOptionalFields.length;
    }

    evalModifier(modifier, record) {
        return !!(modifier && new Domain(modifier).contains(record.evalContext));
    }

    get canCreate() {
        return "link" in this.activeActions
            ? this.activeActions.link
            : this.activeActions.create;
    }

    get isX2Many() {
        return this.activeActions.type !== "view";
    }

    async onDeleteRecord(record) {
        this.keepColumnWidths = true;
        const { editedRecord } = this.props.map;
        if (editedRecord && editedRecord !== record) {
            const unselected = await this.props.map.unselectRecord(true);
            if (!unselected) {
                return;
            }
        }
        if (this.activeActions.onDelete) {
            this.activeActions.onDelete(record);
        }
    }

    async onCreateAction(context) {
        // TO DISCUSS: is it a use case for owl `batched()` ?
        if (this.createProm) {
            return;
        }
        this.add({ context });
        this.createProm = Promise.resolve();
        this.createProm.then(() => {
            this.lastCreatingAction = true;
        });
        await this.createProm;
        this.createProm = null;
    }

    setDirty(isDirty) {
        this.lastIsDirty = isDirty;
    }

    saveOptionalActiveFields() {
        browser.localStorage.setItem(
            this.keyOptionalFields,
            Object.keys(this.optionalActiveFields).filter(
                (fieldName) => this.optionalActiveFields[fieldName]
            )
        );
    }

    get showNoContentHelper() {
        const { model } = this.props.map;
        return this.props.noContentHelp && (model.useSampleModel || !model.hasData());
    }

    get canSelectRecord() {
        return !this.props.map.editedRecord && !this.props.map.model.useSampleModel;
    }

    toggleSelection() {
        const { map } = this.props;
        if (!this.canSelectRecord) {
            return;
        }
        if (map.selection.length === map.records.length) {
            map.records.forEach((record) => {
                record.toggleSelection(false);
                map.selectDomain(false);
            });
        } else {
            map.records.forEach((record) => {
                record.toggleSelection(true);
            });
        }
    }

    toggleRecordSelection(record) {
        if (!this.canSelectRecord) {
            return;
        }
        record.toggleSelection();
        this.props.map.selectDomain(false);
    }

    onGlobalClick(ev) {
        if (!this.props.map.editedRecord) {
            return; // there's no row in edition
        }

        this.tableRef.el
            .querySelector("tbody")
            .classList.remove("o_keyboard_navigation");

        const { target } = ev;
        if (this.tableRef.el.contains(target) && target.closest(".o_data_row")) {
            // ignore clicks inside the table that are originating from a record row
            // as they are handled directly by the renderer.
            return;
        }
        if (this.activeElement !== this.uiService.activeElement) {
            return;
        }
        // Legacy DatePicker
        if (target.closest(".daterangepicker")) {
            return;
        }
        // Legacy autocomplete
        if (ev.target.closest(".ui-autocomplete")) {
            return;
        }
        this.props.map.unselectRecord(true);
    }

    get isDebugMode() {
        return Boolean(odoo.debug);
    }

    resetLongTouchTimer() {
        if (this.longTouchTimer) {
            browser.clearTimeout(this.longTouchTimer);
            this.longTouchTimer = null;
        }
    }

    ignoreEventInSelectionMode(ev) {
        const { map } = this.props;
        if (this.env.isSmall && map.selection && map.selection.length) {
            // in selection mode, only selection is allowed.
            ev.stopPropagation();
            ev.preventDefault();
        }
    }

    onClickCapture(record, ev) {
        const { map } = this.props;
        if (this.env.isSmall && map.selection && map.selection.length) {
            ev.stopPropagation();
            ev.preventDefault();
            this.toggleRecordSelection(record);
        }
    }
}
