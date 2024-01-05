/** @odoo-module **/

import { SettingsFormCompiler } from "@web/webclient/settings_form_view/settings_form_compiler";
import { append, createElement } from "@web/core/utils/xml";
import { getModifier } from "@web/views/view_compiler";


const originalSetup = SettingsFormCompiler.prototype.setup;


function compileSettingsPage(el, params) {
    /** Copy of compileSettingsPage from @web/webclient/settings_form_view/settings_form_compiler
     * with the following changes:
     * - added management of a new attribute "data-force-icon" on div.app_settings_block
     *
     * This is needed to be able to force the icon of a module in the settings page.
     *
     * The icon should be placed in the module's static/description folder and should be a png file.
     **/
    const settingsPage = createElement("SettingsPage");
    settingsPage.setAttribute("slots", "{NoContentHelper:props.slots.NoContentHelper}");
    settingsPage.setAttribute("initialTab", "props.initialApp");
    settingsPage.setAttribute("t-slot-scope", "settings");

    //props
    const modules = [];

    for (const child of el.children) {
        if (child.nodeName === "div" && child.classList.value.includes("app_settings_block")) {
            params.module = {
                key: child.getAttribute("data-key"),
                string: child.getAttribute("string"),
                imgurl: getAppIconUrl(child.getAttribute("data-key"), child.getAttribute("data-force-icon")),
                isVisible: getModifier(child, "invisible"),
            };
            if (!child.classList.value.includes("o_not_app")) {
                modules.push(params.module);
                append(settingsPage, this.compileNode(child, params));
            }
        }
    }

    settingsPage.setAttribute("modules", JSON.stringify(modules));
    return settingsPage;
}


function getAppIconUrl(module, icon) {
    /** Take the icon from the module if it exists, otherwise use the default icon. **/
    if (icon) {
        return "/" + module + "/static/description/" + icon + ".png";
    }
    return module === "general_settings"
        ? "/base/static/description/settings.png"
        : "/" + module + "/static/description/icon.png";
}

SettingsFormCompiler.prototype.setup = function() {
    originalSetup.apply(this, arguments);

    /** Find the compiler for div.settings and replace it with our own. **/
    function modifyCompiler(compilers, selectorToModify, modificationCallback) {
        for (let i = 0; i < compilers.length; i++) {
            if (compilers[i].selector === selectorToModify) {
                modificationCallback(compilers[i]);
                break;
            }
        }
    }

    modifyCompiler(this.compilers, "div.settings", (compiler) => {
        compiler.fn = compileSettingsPage;
    });
};
