/** @odoo-module **/

import { Component, useRef, useState, EventBus } from "@odoo/owl";
import { useService, useBus } from "@web/core/utils/hooks";
import { renderToString } from "@web/core/utils/render";

import { PopupUploadFile } from "./components/popup_upload_file";
import { PopupDeleteFile } from "./components/popup_delete_file";

import { usePopover } from "@web/core/popover/popover_hook";
import { fuzzyLookup } from "@web/core/utils/search";

async function filter(arr, callback) {
    const fail = Symbol()
    return (await Promise.all(arr.map(async item => (await callback(item)) ? item : fail))).filter(i=>i!==fail)
}

export class DmsRenderer extends Component {
    static template = "of_dms_view.DmsRenderer";
    static components = {
        PopupUploadFile,
        PopupDeleteFile
    }

    setup() {
        this.state = useState({
            files: [],
            directories: [],
            directFiles: [],
            parentDirectory: {},
            preview: false,
            preview_real: false,
            preview_virtual: false,
            expanded: {},
            searchDirectories: [],
            isPartnerDirectory: false,
        })
        this.orm = useService("orm");
        this.currentDirectory = false;
        this.currentFile = false;
        // on ajoute également une liste des dossiers pour la parcourir plus facilement
        this.props.list = [];
        for (let d of this.pre_order_traversal()){
            this.props.list.push(d);
        }
        this.rootRef = useRef('root');
        this.panelDirectoriesRef = useRef('panel-directories');
        this.panelDirectoriesFilesRef = useRef('panel-directories-files');

        this.popover = usePopover();
        this.bus = new EventBus();

        useBus(this.bus, "refresh_directories_files", async () => {
            await this.load_directories_files(this.currentDirectory);
        });

        useBus(this.bus, "hide_preview", () => {
            this.state.preview = false;
        });
    }

    *pre_order_traversal(directory = this.props.records[0]) {
        yield directory;
        if (directory.childs) {
          for (let child of directory.childs) {
            yield* this.pre_order_traversal(child);
          }
        }
      }


    // Gestion des dossiers

    click_expand(record) {
        this.state.preview = false;
        this.currentDirectory = record;
        this.state.isPartnerDirectory = record.model == 'res.partner';
        if (this.state.expanded[record.id]){
            this.close_directory(record);
        } else {
            this.open_directory(record);
        }
    }

    click_directory(record) {
        this.state.preview = false;
        this.currentDirectory = record;
        this.state.isPartnerDirectory = record.model == 'res.partner';
        this.open_directory(record);
        this.load_directories_files(record);
    }

    open_directory(record){
        this.state.expanded[record.id] = true;
        // on ouvre aussi les parents de ce dossier
        if (record.parent_id){
            let parent_directory = this.props.list.find((directory) => directory.id == record.parent_id);
            if (parent_directory){
                this.open_parent_directory(parent_directory);
            }
        }
        if (record.model == 'res.partner') {
            // si on est sur une dossier partenaire on ouvre aussi les enfants
            let childs_directory = this.props.list.filter((directory) => directory.parent_id == record.id);

            for (let child_directory of childs_directory){
                this.state.expanded[child_directory.id] = true;
            }
        }
    }

    open_parent_directory(record){
        this.state.expanded[record.id] = true;
        // on ouvre aussi les parents de ce dossier
        if (record.parent_id){
            let parent_directory = this.props.list.find((directory) => directory.id == record.parent_id);
            if (parent_directory){
                this.open_parent_directory(parent_directory);
            }
        }
    }

    close_directory(record){
        this.state.expanded[record.id] = false;
        // on ferme aussi tous les enfants
        let childs_directory = this.props.list.filter((directory) => directory.parent_id == record.id);

        for (let directory of childs_directory){
            this.close_directory(directory);
        }
    }

    async load_parent_directory(record){
        this.state.parentDirectory =  await this.orm.call('dms.directory','get_parent_directory', [], {
            directory_id : record.id,
        });
    }

    async load_directories_files(record){
        this.allDirectories = await this.orm.call('dms.directory','get_directories', [], {
            directory_id : record.id,
        });
        this.allDirectFiles = await this.orm.call('dms.directory','get_direct_files', [], {
            directory_id : record.id,
        });
        this.allFiles = await this.orm.call('dms.directory','get_files', [], {
            directory_id : record.id,
        });
        this.state.directories = this.allDirectories;
        this.state.directFiles = this.allDirectFiles;
        this.state.files = this.allFiles;
        this.load_parent_directory(record);
    }

    async search_directories_files(evt){
        let search = $('#search_directories_files').val();
        this.load_parent_directory(this.currentDirectory);

        if (search){
            this.state.files = fuzzyLookup(search, this.allFiles, (record) => record.name);

            this.state.directories = await filter(this.allDirectories, async directory => {
                return await this.orm.call('dms.directory','filter_directory', [], {
                    directory_id : directory.id,
                    file_ids : this.state.files.map(f => f.id),
                })
            });
        }
        else {
            this.state.directories = this.allDirectories;
            this.state.files = this.allFiles;
        }
    }

    async search_directories(evt){
        let search = $(this.rootRef.el).find('#search_directories').val();
        if (search){
            let searchDirectories = fuzzyLookup(search, this.props.list,(record) => record.name);
            this.state.searchDirectories = searchDirectories.map((record) => record.id);
            // on va en plus ouvrir ces dossiers
            for (const record of searchDirectories){
                this.open_directory(record)
            }
        } else {
            this.state.searchDirectories = [];
        }
    }

    // fin gestion de dossiers

    // gestion des fichiers

    click_file(record){
        this.state.preview = false;
        this.currentFile = record;
        if (record.is_virtual){
            this.preview_virtual(record);
        } else {
            this.preview_real(record);
        }
    }

    preview_virtual(record){
        this.state.preview = true;
        $(this.rootRef.el).find('.panel-preview-content').html("");
        $(this.rootRef.el).find('.panel-preview-content').load(record.content_url + " main");
        this.state.preview_virtual = true;
        this.state.preview_real = false;
    }

    preview_real(record){
        this.state.preview = true;
        $(this.rootRef.el).find('.panel-preview-content').html('<iframe src="' + record.content_url + '"/>');
        this.state.preview_virtual = false;
        this.state.preview_real = true;
    }

    click_upload_file(){
        if (!$('.form_upload').length) {
            this.showPopup($(this.rootRef.el).find('.btn-upload-file')[0], this.constructor.components.PopupUploadFile, { });
        }
    }

    showPopup(el, popover, options) {
        this.closePopover = this.popover.add(
            el,
            popover, { record: this.currentDirectory, options: { bus: this.bus }, currentFile: this.currentFile }, {}
        );
    }

    click_delete_file(record){
        // on vérifie déjà que le record est un fichier et est réel
        if (!record.is_directory && !record.is_virtual && !$('.form_delete').length){
            if (record.attachment_id) {
                this.showPopup($(this.rootRef.el).find('.btn-delete-file')[0], this.constructor.components.PopupDeleteFile, { });
            }
        }
    }

    click_fullscreen(){
        var content = $(this.rootRef.el).find('.panel-preview-content')
        if (content[0]) {
            content[0].requestFullscreen();
        }
    }

    // fin gestion des fichiers

    // gestion des resize panel

    click_resize_directories(evt){
        // On vérifie que c'est bien le clic gauche
        if (evt.button === 0) {
            // On désactive la sélection de texte qui peut parasiter le resizing
            $('.dms-renderer').css('user-select', 'none');
            $('.dms-renderer').css('-moz-user-select', 'none');
            $('.dms-renderer').css('-webkit-user-select', 'none');
            $('.dms-renderer').css('-ms-user-select', 'none');

            this.resizeDirectories = true;

            if (!this.panelDirectoriesRef.el.style.width) {
                this.panelDirectoriesRef.el.style.width = `${this.panelDirectoriesRef.el.offsetWidth}px`;
            }

            this.directoriesInitialX = evt.pageX;
            this.directoriesInitialWidth = this.panelDirectoriesRef.el.offsetWidth;

            // on a besoin aussi de la taille du panel directories-files pour le réduire ou agrandir selon
            if (!this.panelDirectoriesFilesRef.el.style.width) {
                this.panelDirectoriesFilesRef.el.style.width = `${this.panelDirectoriesFilesRef.el.offsetWidth}px`;
            }

            this.directoriesFilesInitialWidth = this.panelDirectoriesFilesRef.el.offsetWidth;
        }
    }

    click_resize_directories_files(evt){
        // On vérifie que c'est bien le clic gauche
        if (evt.button === 0) {
            this.resizeDirectoriesFiles = true;

            // On désactive le curseur sur le iframe pour ne pas perturber le resizing
            $('iframe').css('pointer-events', 'none');

            // On désactive la sélection de texte qui peut parasiter le resizing
            $('.dms-renderer').css('user-select', 'none');
            $('.dms-renderer').css('-moz-user-select', 'none');
            $('.dms-renderer').css('-webkit-user-select', 'none');
            $('.dms-renderer').css('-ms-user-select', 'none');

            if (!this.panelDirectoriesFilesRef.el.style.width) {
                this.panelDirectoriesFilesRef.el.style.width = `${this.panelDirectoriesFilesRef.el.offsetWidth}px`;
            }

            this.directoriesFilesInitialX = evt.pageX;
            this.directoriesFilesInitialWidth = this.panelDirectoriesFilesRef.el.offsetWidth;
        }
    }

    mousemove_resize_panel(evt){

        if (this.resizeDirectories){
            evt.preventDefault();
            evt.stopPropagation();
            const delta = evt.pageX - this.directoriesInitialX;
            const newWidth = this.directoriesInitialWidth + delta;
            this.panelDirectoriesRef.el.style.width = `${newWidth}px`;
            // en plus on réduit la taille du panel directories-files
            const newWidthDirectoriesFiles = this.directoriesFilesInitialWidth - delta;
            this.panelDirectoriesFilesRef.el.style.width = `${newWidthDirectoriesFiles}px`;

        }
        if (this.resizeDirectoriesFiles){
            evt.preventDefault();
            evt.stopPropagation();
            const delta = evt.pageX - this.directoriesFilesInitialX;
            const newWidth = this.directoriesFilesInitialWidth + delta;
            this.panelDirectoriesFilesRef.el.style.width = `${newWidth}px`;
        }
    }

    mouseup_resize_directories(evt){
        this.resizeDirectories = false;

        $('.dms-renderer').css('user-select', '');
        $('.dms-renderer').css('-moz-user-select', '');
        $('.dms-renderer').css('-webkit-user-select', '');
        $('.dms-renderer').css('-ms-user-select', '');
    }

    mouseup_resize_directories_files(evt){
        this.resizeDirectoriesFiles = false;
        $('iframe').css('pointer-events', '');

        $('.dms-renderer').css('user-select', '');
        $('.dms-renderer').css('-moz-user-select', '');
        $('.dms-renderer').css('-webkit-user-select', '');
        $('.dms-renderer').css('-ms-user-select', '');
    }

    // fin gestion des resize panel

}
