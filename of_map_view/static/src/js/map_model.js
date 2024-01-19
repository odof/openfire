/** @odoo-module */

import {Model} from "@web/views/model";

export class MapModel extends Model {
    setup(params, {}) {
        this.data = {
            partners: [],
            partnerIds: [],
        };
        this.metaData = {
            ...params,
        };
    }

    /**
     *
     * @param { Object } params
     */
    async load(params) {
        const metaData = {
            ...this.metaData,
            ...params,
        };
        this.data.partners = await this._fetchData(metaData);
        this.data.partnerIds = [];
        this.data.partners.records.map((record) => {
            this.data.partnerIds.push(record.id);
        });

        this.notify();
    }

    /**
     *
     * @param { Object } metaData
     * @returns
     */
    async _fetchData(metaData) {
        return this.orm.webSearchRead(
            metaData.resModel,
            metaData.domain,
            [
                "name",
                "partner_latitude",
                "partner_longitude",
                "of_precision",
                "city",
                "zip",
                "phone",
                "mobile",
                "id",
            ],
            {
                order: metaData.orderBy.join(" "),
                context: metaData.context,
            }
        );
    }
}
