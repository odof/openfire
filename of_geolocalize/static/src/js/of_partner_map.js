/** @odoo-module */

import { OFPartnerMap } from "@of_web_widgets/js/of_partner_map";
import { registry } from "@web/core/registry";

export class OFMapGeolocalize extends OFPartnerMap {

    async loadPartners(partner_ids){
        const partners = await this.orm.searchRead("res.partner",[['id','in',partner_ids]],["id","partner_latitude","partner_longitude","parent_id","child_ids"]);
        await Promise.all(partners.map((partner)=>this.loadPartner(partner)));
    }

    async loadChildPartner(partner_id){
        const icon = L.icon({
            iconUrl: '/of_web_widgets/static/lib/leaflet/images/marker-icon-black.png',
            shadowUrl: '/of_web_widgets/static/lib/leaflet/images/marker-shadow.png',
            iconSize: [25, 41],
            iconAnchor: [12, 41],
            popupAnchor: [1, -34],
            tooltipAnchor: [16, -28],
            shadowSize: [41, 41]
        });
        await this.loadPartnerIcon(partner_id,icon);
    }

    async loadParentPartner(partner_id){
        const icon = L.icon({
            iconUrl: '/of_web_widgets/static/lib/leaflet/images/marker-icon-green.png',
            shadowUrl: '/of_web_widgets/static/lib/leaflet/images/marker-shadow.png',
            iconSize: [25, 41],
            iconAnchor: [12, 41],
            popupAnchor: [1, -34],
            tooltipAnchor: [16, -28],
            shadowSize: [41, 41]
        });
        await this.loadPartnerIcon(partner_id,icon);

    }

    async loadPartnerIcon(partner_id,icon){
        const partner = await this.orm.searchRead('res.partner',[['id','=',partner_id]],['id', 'display_name', 'of_precision','partner_latitude','partner_longitude']);
        if (partner.length>0){
            partner[0]['icon'] = icon;
            this.partners.push(partner[0]);
            this.fitbounds.push([partner[0].partner_latitude,partner[0].partner_longitude]);
            this.partners_info[partner[0].id] = `${partner[0].display_name}<br/>precision: ${partner[0].of_precision}`;
        }
    }

    async loadPartner(partner){
        this.partners.push(partner);
        this.fitbounds.push([partner.partner_latitude,partner.partner_longitude]);
        const partner_info = await this.orm.searchRead('res.partner',[['id','=',partner.id]],["id","display_name","of_precision"]);
        if (partner_info){
            this.partners_info[partner.id] = `${partner_info[0].display_name}<br/>precision: ${partner_info[0].of_precision}`;
        } else {
            this.partners_info[partner.id] = "";
        }

        // si le champs parent_id existe, on l'ajoute dans la liste des partners à afficher, en changeant l'icone
        if (partner.parent_id){
            await this.loadParentPartner(partner.parent_id[0]);
        }

        if (partner.child_ids){
            await Promise.all(partner.child_ids.map((partner_id)=>this.loadChildPartner(partner_id)));
        }

    }


}

registry.category("fields").add("of_geolocalize_map", OFMapGeolocalize);
