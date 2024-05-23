/** @odoo-module **/

import { registry } from "@web/core/registry";
import { ListRenderer } from "@web/views/list/list_renderer";
import { X2ManyField } from "@web/views/fields/x2many/x2many_field";
import { Field } from "@web/views/fields/field";
import { TreeRecord } from "./tree_record";
import { PopupoverInfo, PopupoverDelete } from "./popupover";
import { makeContext } from "@web/core/context";
import { usePopover } from "@web/core/popover/popover_hook";
const { Component, useEffect, useRef, onWillUpdateProps, EventBus, useState } = owl;

export class OFSaleSectionLine extends Component {
    static template = "of_sale_layout_category.OFSaleSectionLine";
    static components = {
        Field,
        PopupoverInfo,
        PopupoverDelete
    }

    setup() {
        this.nbColumns = this.props.columns.length;
        this.section_column = this.props.columns.find((c) => c.name === "name");
        this.section_class = this.section_column.rawAttrs && this.section_column.rawAttrs.class;
        this.handle_column = this.props.columns.find((c) => c.name === "sequence");
        this.section_name_ref = useRef('section_name');
        this.popover = usePopover();
        this.bus = new EventBus();
        this.tableRef = this.__owl__.parent.component.tableRef;
        this.state = useState({
            'section_name': this.props.record.data.name,
            'active_layout_category': true,
        })

        useEffect(
            () => {
                this.state.active_layout_category = this.props.record.model.root.data.of_layout_category_active
            },
            () => [this.props.record.model.root.data.of_layout_category_active]
        )

        onWillUpdateProps(nextProps => {
            nextProps.list.records.sort(
                (r1, r2) =>
                r1.data.sequence - r2.data.sequence ||
                r1.data.of_position_node - r2.data.of_position_node
            );
        })
    }

    showPopup(ev, popover, options) {
        this.closePopover = this.popover.add(
            ev.currentTarget,
            popover, { bus: this.bus, record: this.props.record, options: options }, {
                position: 'top',
            }
        );
        this.bus.addEventListener('close-popover', this.closePopover);
    }

    getSectionColumn() {
        return this.section_column;
    }

    getSectionClass() {
        return this.section_class;
    }

    getHandleColumn() {
        return this.handle_column;
    }

    async onCellClicked(record) {
        this.props.list.editedRecord = record;
        await record.switchMode("edit");
    }

    focusToSection(record){
        let tr = this.tableRef.el.querySelector(`tr[data-id='${record.id}']`);
        let input = tr.querySelector("input");
        $(input).focus();
    }

    setDirty(isDirty) {
        this.lastIsDirty = isDirty;
    }

    async add(recordValue) {
        // D'abord on calcule sa position selon les autres possibles enfants du record auquel on ajoute celui ci
        let children = this.props.list.records.filter((record) => record.data.of_parent_node_id == this.props.record.data.of_node_id);

        let index = 0;
        if (children) {
            index = children.length;
        }

        let context = {
            'default_of_node_id': this.props.list.records.length + 1,
            'default_of_parent_node_id': this.props.record.data.of_node_id,
            'default_of_position_node': index,
        }
        let newRecord = await this.props.list.addNew({ mode: "edit", position: 'bottom', 'context': context });
        await newRecord.update(recordValue);
        await newRecord.model.notify();
        return newRecord;
    }

    async remove(datapointId) {
        await this.props.list.delete(datapointId);
        await this.props.record.model.notify();
    }

    sortAsc() {
        this.props.list.records.sort(
            (r1, r2) =>
            r1.data.sequence - r2.data.sequence ||
            r1.data.of_position_node - r2.data.of_position_node
        );
    }

    async resequence() {
        // Le principe ici c'est de générer à la volée le treeRecord suivant les données des records odoo
        // on utilise dans la class TreeRecord les champs of_node_id et of_parent_node_id pour créer
        // la hierarchie
        let treeRecord = new TreeRecord(this.props.list);

        for (let data of Object.entries(treeRecord.data)) {
            if (data[0] != "Root") {
                let record = this.props.list.records.find((record) => record.id == data[0]);
                if (record) {
                    await record.update(data[1]);
                } else {
                    console.log("Hmmm something went wrong in resequence");
                }
            }
        }
        this.sortAsc();
        await this.props.record.model.notify();
    }

    /* Gestion des produits */

    async addProduct(evt) {
        let recordValue = { 'of_parent_node_id': this.props.record.data.of_node_id };
        let record = await this.add(recordValue);
        await this.resequence();
    }

    /* Fin gestion des produits */

    /* Gestion des sections */

    async addSection(evt) {
        let recordValue = { 'display_type': 'line_section', 'name': 'Section', 'of_parent_node_id': this.props.record.data.of_node_id };
        let record = await this.add(recordValue);
        await this.resequence();
        this.focusToSection(record);
    }

    async duplicate(evt) {
        // Le principe c'est de générer le treeRecord, pour récupérer la liste des enfants
        // de la section à dupliquer et de faire un simple add sur chacun des enfants
        // on va chercher les enfants (même of_node_parent_id dans les records)
        let children = this.props.list.records.filter((record) => record.data.of_parent_node_id == this.props.record.data.of_node_id);

        // D'abord, on duplique le node en cours, c'est un add avec des différences
        let recordValue = this.props.record.data;
        recordValue['of_node_id'] = this.props.list.records.length + 1;
        recordValue['of_parent_node_id'] = this.props.record.data.of_parent_node_id;
        let newRecord = await this.add(recordValue);


        if (children.length > 0) {
            await this.duplicateRecursive(newRecord, children);
        }
        // A la fin on lance un resequence pour calculer la séquence et le nom des sections
        await this.resequence();
    }

    async duplicateRecursive(parentRecord, children) {
        for (const child of children){
            // on va chercher les enfants (même of_node_parent_id dans les records)
            let childs = this.props.list.records.filter((record) => record.data.of_parent_node_id == child.data.of_node_id);
            // on duplique le child
            let recordValue = child.data;
            recordValue['of_node_id'] = this.props.list.records.length + 1;
            recordValue['of_parent_node_id'] = parentRecord.data.of_node_id;
            let newRecord = await this.add(recordValue);
            // on les duplique récursivement s'il y en a
            if (childs.length > 0) {
                await this.duplicateRecursive(newRecord, childs);
            }
        };
    }

    deleteAsk(evt) {
        var options = { line: this, record: this.props.record };
        this.showPopup(evt, this.constructor.components.PopupoverDelete, options);
    }

    async delete(evt) {
        // le principe c'est de générer le treeRecord, pour récupérer la liste des enfants
        // de la section à supprimer et de faire un simple remove sur chacun des enfants
        let treeRecord = new TreeRecord(this.props.list);
        let node = treeRecord.find(this.props.record.id);
        for (let child of Object.entries(treeRecord.allChildren(node))) {
            if (child[0] != "Root") {
                await this.remove(child[0]);
            }
        }
        // on finit par supprimer le node restant
        await this.remove(this.props.record.id);

        // A la fin on lance un resequence pour calculer la sequence et le nom des sections
        await this.resequence();
    }

    /* Fin gestion des sections */

    /* Actions sur les sections */

    async moveUp(evt) {
        // L'idée ici c'est de remonter le record en cours d'un niveau
        // C'est à dire qu'on va lui donner le parent de son parent comme parent
        let parentCurrentRecord = this.props.list.records.find((record) => record.data.of_node_id == this.props.record.data.of_parent_node_id);
        let parent_node_id = 0; // valeur par défaut, c'est la racine des records
        if (parentCurrentRecord) {
            parent_node_id = parentCurrentRecord.data.of_parent_node_id;
        }
        // on place ce record en dernier des enfants du record parent
        let index = 0;
        if (parentCurrentRecord) {
            let children = this.props.list.records.find((record) => record.data.of_node_id == parentCurrentRecord.data.of_parent_node_id);
            if (children) {
                index = children.length;
            }
        }
        await this.props.record.update({
            'of_parent_node_id': parent_node_id,
            'of_position_node': index
        })

        this.props.record.model.notify();
        // A la fin on lance un resequence pour calculer la sequence et le nom des sections
        await this.resequence();
    }

    async moveDown(evt) {
        // L'idée ici c'est de descendre le record d'un niveau
        // C'est à dire qu'il va devenir l'enfant de son frère précédent (uniquement si c'est une section)
        let brothers = this.props.list.records.filter((record) => record.data.of_parent_node_id == this.props.record.data.of_parent_node_id && record.data.display_type == "line_section");
        let indexRecord = brothers.indexOf(this.props.record);
        if (indexRecord > 0) {
            let previousRecord = brothers[indexRecord - 1];
            // on le place à la fin des enfants possibles de ce previousRecord
            let index = 0;
            let children = this.props.list.records.filter((record) => record.data.of_parent_node_id == previousRecord.data.of_node_id);
            if (children) {
                index = children.length;
            }
            await this.props.record.update({
                'of_parent_node_id': previousRecord.data.of_node_id,
                'of_position_node': index
            })
            this.props.record.model.notify();

            // A la fin on lance un resequence pour calculer la sequence et le nom des sections
            await this.resequence();
        }
    }

    /* Fin des actions sur les sections */
}

export class OFSaleSectionListRenderer extends ListRenderer {
    static template = "of_sale_layout_category.OFSaleSectionListRenderer";
    static recordRowTemplate = "of_sale_layout_category.SaleListRenderer.RecordRow";
    static components = {
        Section: OFSaleSectionLine,
        ...ListRenderer.components,
    }
    setup() {
        super.setup();
        this.titleField = "name";
        this.titleFields = ["name", "of_section_name"];
    }

    isSectionOrNote(record = null) {
        record = record || this.record;
        return ['line_section', 'line_note'].includes(record.data.display_type);
    }

    isSection(record = null) {
        record = record || this.record;
        return 'line_section' == record.data.display_type;
    }

    isNote(record = null) {
        record = record || this.record;
        return 'line_note' == record.data.display_type;
    }

    getRowClass(record) {
        const existingClasses = super.getRowClass(record);
        return `${existingClasses} o_is_${record.data.display_type} brighter-${record.data.of_level}`;

    }

    getColumns(record) {
        const columns = super.getColumns(record);
        if (this.isNote(record)) {
            return this.getNoteColumns(columns);
        }
        return columns;
    }

    getNoteColumns(columns) {
        const noteCols = columns.filter((col) => col.widget === "handle" || col.type === "field" && col.name === "name");
        return noteCols.map((col) => {
            if (col.name === "name") {
                return { ...col, colspan: columns.length - noteCols.length + 1 };
            } else {
                return { ...col };
            }
        });
    }

    sortAsc() {
        this.props.list.records.sort(
            (r1, r2) =>
            r1.data.sequence - r2.data.sequence ||
            r1.data.of_position_node - r2.data.of_position_node
        );
    }

    async resequence() {
        // Le principe ici c'est de générer à la volée le treeRecord suivant les données des records odoo
        // on utilise dans la class TreeRecord les champs of_node_id et of_parent_node_id pour créer
        // la hierarchie
        // TODO : il pourrait être intéressant de trouver comment mettre d'un coup tous les records à jour
        // sans le faite un par un, on gagnerait en rapidité
        let treeRecord = new TreeRecord(this.props.list);

        for (let data of Object.entries(treeRecord.data)) {
            if (data[0] != "Root") {
                let record = this.props.list.records.find((record) => record.id == data[0]);
                if (record) {
                    await record.update(data[1]);
                } else {
                    console.log("Hmmm something went wrong in resequence");
                }
            }
        }
        this.sortAsc();
    }

    sortStart({ element }) {
        const table = this.tableRef.el;
        // on va chercher les éléments qui ont le même parent, pour changer la couleur
        let elementData = $(element).data();
        let currentRecord = this.props.list.records.find((record) => record.id == elementData.id);

        // on ne le fait que si c'est une section que l'on bouge
        if (currentRecord.data.display_type == "line_section") {
            let brothers = this.props.list.records.filter((record) => record.data.of_parent_node_id == currentRecord.data.of_parent_node_id);
            brothers.map((record) => {
                let elements = $(table).find('tr[data-id="' + record.id + '"]');
                elements.each(function(index) {
                    elements[index].classList.add("o_dragged_section");
                });
            })
        }
        super.sortStart({ element });
    }

    sortStop({ element }) {
        const table = this.tableRef.el;
        let elements = $(table).find(".o_dragged_section");
        elements.each((index) => {
            elements[index].classList.remove("o_dragged_section");
        });
        super.sortStop({ element });
    }

    async sortDrop(dataRowId, { element, previous }) {
        await super.sortDrop(dataRowId, { element, previous });
        // On doit vérifier deux cas, soit l'élément déplacé est une section
        // Soit c'est un article/note
        // Si c'est une section, on modifie la of_position_node et une resequence pour la placer au bon endroit
        // sinon, on modifie le of_parent_node_id de l'élément pour lui donner celui de son prédécesseur
        let record = this.props.list.records.find((record) => record.id == dataRowId);
        if (record.data.display_type == 'line_section') {
            // on récupère l'ordre des enfants
            let brothers = this.props.list.records.filter((r) => r.data.of_parent_node_id == record.data.of_parent_node_id);
            await Promise.all(brothers.map(async (r, index) => {
                await r.update({ 'of_position_node': index });
            }));
            await this.resequence();
        } else {
            let indexRecord = this.props.list.records.indexOf(record);
            if (indexRecord == 0) {
                await record.update({
                    'of_parent_node_id': 0, // le parent est forcément la racine
                    'of_position_node': this.props.list.records.length
                })
            } else {
                // Il faut prendre le record d'avant qui est une section
                let previousSectionRecords = this.props.list.records.filter((record) => record.data.display_type == 'line_section');
                let previousSectionRecord = false;
                previousSectionRecords.map((r) => {
                    if (r.data.sequence < record.data.sequence) {
                        previousSectionRecord = r;
                    }
                })
                let index = 0;
                let of_node_id = 0;
                if (previousSectionRecord) {
                    of_node_id = previousSectionRecord.data.of_node_id
                }

                let children = this.props.list.records.filter((record) => record.data.of_parent_node_id == of_node_id);
                if (children) {
                    index = children.length;
                }
                await record.update({
                    'of_parent_node_id': of_node_id,
                    'of_position_node': index,
                })
            }
        }
    }
}

export class OFSaleSectionOne2Many extends X2ManyField {
    static additionalClasses = ['o_field_one2many'];
    static components = {
        ...X2ManyField.components,
        ListRenderer: OFSaleSectionListRenderer,
    };

    onAdd({ context, editable } = {}) {
        // on extrait le contexte pour avoir un dictionnaire
        context = makeContext([context]);
        if (context.default_display_type && context.default_display_type == 'line_section') {
            context['default_of_node_id'] = this.list.records.length + 1;
            context['default_of_parent_node_id'] = 0;
            context['default_of_section_name'] = this.list.records.filter((record) => record.data.of_parent_node_id == 0 && record.data.display_type == 'line_section').length + 1;
            context['default_sequence'] = this.list.records.length + 1;
            context['default_name'] = 'Section';
            context['default_of_position_node'] = this.list.records.filter((record) => record.data.of_parent_node_id == 0).length;
            context['default_of_level'] = 0;
        }
        // Si on ajoute un produit et qu'il existe déjà au moins une section, on doit mettre
        // le produit dans la section la plus profonde
        if (!context.default_display_type) {
            let sections = this.list.records.filter((record) => record.data.display_type == 'line_section');
            if (sections.length > 0){
                context['default_of_parent_node_id'] = sections.slice(-1)[0].data.of_node_id;
            }
        }
        return super.onAdd({ context, editable });
    }
}

registry.category("fields").add("of_sale_section_one2many", OFSaleSectionOne2Many);
