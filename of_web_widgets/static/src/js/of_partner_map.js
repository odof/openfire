/** @odoo-module */
import {standardFieldProps} from "@web/views/fields/standard_field_props";
import {registry} from "@web/core/registry";
import {Component, onWillStart, useRef, useEffect, onWillUnmount} from "@odoo/owl";
import {loadJS, loadCSS} from "@web/core/assets";
import {useService} from "@web/core/utils/hooks";

const DEFAULT_MAP_ROWS = 4;
const MAP_ROWS_HEIGHT_MULTIPLICATOR = 20;

export class OFPartnerMap extends Component {
    static template = "of_web_widgets.OFPartnerMap";
    static props = {
        ...standardFieldProps,
        mapRows: {type: Number, optional: true},
    };
    static supportedTypes = ["many2one"];
    static extractProps = ({attrs, field}) => {
        return {
            mapRows: attrs.options.map_rows,
        };
    };

    async loadPartners(partner_ids) {
        const partners = await this.orm.searchRead(
            "res.partner",
            [["id", "in", partner_ids]],
            ["id", "partner_latitude", "partner_longitude"]
        );
        await Promise.all(partners.map((partner) => this.loadPartner(partner)));
    }

    async loadPartner(partner) {
        this.partners.push(partner);
        this.fitbounds.push([partner.partner_latitude, partner.partner_longitude]);
        const partner_info = await this.orm.searchRead(
            "res.partner",
            [["id", "=", partner.id]],
            ["id", "display_name"]
        );
        if (partner_info) {
            this.partners_info[partner.id] = `${partner_info[0].display_name}`;
        } else {
            this.partners_info[partner.id] = "";
        }
    }

    addMarker(partner) {
        let marker = null;
        if (partner.icon) {
            marker = L.marker([partner.partner_latitude, partner.partner_longitude], {
                icon: partner.icon,
            }).addTo(this.leafletMap);
        } else {
            marker = L.marker([
                partner.partner_latitude,
                partner.partner_longitude,
            ]).addTo(this.leafletMap);
        }
        marker.bindTooltip(this.partners_info[partner.id]);
        this.markers.push(marker);
    }

    setup() {
        var self = this;
        this.orm = useService("orm");
        this.busService = this.env.services.bus_service;
        this.mapRows = this.props.mapRows ? this.props.mapRows : DEFAULT_MAP_ROWS;
        this.leafletMap = null;
        this.mapContainerRef = useRef("mapContainer");
        this.partner_id = this.props.value[0];
        this.fitbounds = [];
        this.partners = [];
        this.partners_info = {};
        this.markers = [];

        this.busService.addChannel("OFPartnerMap"); // subscribe to the channel OFPartnerMap to receive notifications
        this.busService.addEventListener(
            "notification",
            this.onBusNotification.bind(this)
        );

        onWillStart(async () => {
            Promise.all([
                loadJS(["/of_web_widgets/static/lib/leaflet/leaflet.js"]),
                loadCSS("/of_web_widgets/static/lib/leaflet/leaflet.css"),
            ]);
            await this.loadPartners([this.partner_id]);
        });

        onWillUnmount(this.onWillUnmount);

        useEffect(() => {
            $(this.mapContainerRef.el).height(
                MAP_ROWS_HEIGHT_MULTIPLICATOR * this.mapRows
            );
            $(this.mapContainerRef.el).width(
                $(this.mapContainerRef.el.parentElement.parentElement).width()
            );
            this.partners.forEach(function (partner) {
                if (!self.leafletMap) {
                    self.leafletMap = L.map(self.mapContainerRef.el).setView(
                        [partner.partner_latitude, partner.partner_longitude],
                        8
                    );
                    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
                        maxZoom: 19,
                        attribution:
                            '&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>',
                    }).addTo(self.leafletMap);
                }
                self.addMarker(partner);
            });
            if (this.fitbounds.length > 0) {
                // on affiche un niveau de zoom qui contient tous les markers
                this.leafletMap.fitBounds(this.fitbounds);
            }
        });
    }

    async onBusNotification({detail: notifications}) {
        let refresh = notifications.filter(
            (notification) => notification.payload.action == "refresh"
        );
        if (refresh.length > 0) {
            this.markers.map((marker) => {
                this.leafletMap.removeLayer(marker);
            });
            this.markers = [];
            this.partners = [];
            this.fitbounds = [];
            await this.loadPartners([this.partner_id]);
        }
    }

    onWillUnmount() {
        if (this.leafletMap) {
            this.leafletMap.remove();
        }
    }
}

registry.category("fields").add("of_partner_map", OFPartnerMap);
