/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import {
    onWillUnmount,
    useComponent,
    onWillRender,
    onWillStart,
    toRaw,
    useEffect,
    useExternalListener,
    useState,
} from "@odoo/owl";
import { xml } from "@odoo/owl";
import { shallowEqual } from "@web/core/utils/arrays";



/**
 * Creates a version of the function where only the last call between two
 * animation frames is executed before the browser's next repaint. This
 * effectively throttles the function to the display's refresh rate.
 * NB: The first call is always called immediately (leading edge).
 *
 * @template {Function} T
 * @param {T} func the function to throttle
 * @returns {T & { cancel: () => void }} the throttled function
 */
export function throttleForAnimation(func) {
    let handle = null;
    const calls = new Set();
    const funcName = func.name ? `${func.name} (throttleForAnimation)` : "throttleForAnimation";
    const pending = () => {
        if (calls.size) {
            handle = browser.requestAnimationFrame(pending);
            const { args, resolve } = [...calls].pop();
            calls.clear();
            Promise.resolve(func.apply(this, args)).then(resolve);
        } else {
            handle = null;
        }
    };
    return Object.assign(
        {
            /** @type {any} */
            [funcName](...args) {
                return new Promise((resolve) => {
                    const isNew = handle === null;
                    if (isNew) {
                        handle = browser.requestAnimationFrame(pending);
                        Promise.resolve(func.apply(this, args)).then(resolve);
                    } else {
                        calls.add({ args, resolve });
                    }
                });
            },
        }[funcName],
        {
            cancel() {
                browser.cancelAnimationFrame(handle);
                calls.clear();
                handle = null;
            },
        }
    );
}

// ----------------------------------- HOOKS -----------------------------------

/**
 * Hook that returns a throttled for animation version of the given function,
 * and cancels the potential pending execution on willUnmount.
 * @see throttleForAnimation
 * @template {Function} T
 * @param {T} func the function to throttle
 * @returns {T & { cancel: () => void }} the throttled function
 */
export function useThrottleForAnimation(func) {
    const component = useComponent();
    const throttledForAnimation = throttleForAnimation(func.bind(component));
    onWillUnmount(() => throttledForAnimation.cancel());
    return throttledForAnimation;
}


/**
 * Calculates the displayed items in a virtual list.
 *
 * Requirements:
 *  - the scrollable area has a fixed height
 *  - the items are rendered with a proper offset inside the scrollable area.
 *    This can be achieved e.g. with a css grid or an absolute positioning.
 *
 * @template T
 * @param {VirtualHookParams<T>} params
 * @returns {ReturnType<useState<T>>}
 */
export function useVirtual({ getItems, scrollableRef, initialScroll, getItemHeight }) {
    const computeVirtualItems = () => {
        const { items, scroll } = current;

        const yStart = scroll.top - window.innerHeight;
        const yEnd = scroll.top + 2 * window.innerHeight;

        let [startIndex, endIndex] = [0, 0];
        let currentTop = 0;

        for (const item of items) {
            const height = getItemHeight(item);
            if (currentTop + height < yStart) {
                startIndex++;
                endIndex++;
            } else if (currentTop + height <= yEnd + height) {
                endIndex++;
            } else {
                break;
            }
            currentTop += height;
        }

        const prevItems = toRaw(virtualItems);
        const newItems = items.slice(startIndex, endIndex);

        if (!shallowEqual(prevItems, newItems)) {
            virtualItems.length = 0;
            virtualItems.push(...newItems);
        }
    };

    const current = {
        items: getItems(),
        scroll: { top: 0, ...initialScroll },
    };

    const virtualItems = useState([]);

    onWillStart(computeVirtualItems);
    onWillRender(() => {
        const previousItems = current.items;
        current.items = getItems();
        if (!shallowEqual(previousItems, current.items)) {
            computeVirtualItems();
        }
    });
    const throttledCompute = useThrottleForAnimation(computeVirtualItems);
    const scrollListener = (/** @type {Event & { target: Element }} */ ev) => {
        current.scroll.top = ev.target.scrollTop;
        throttledCompute();
    };
    useExternalListener(window, "resize", throttledCompute);
    useEffect(
        (el) => {
            if (el) {
                el.addEventListener("scroll", scrollListener);
                return () => el.removeEventListener("scroll", scrollListener);
            }
        },
        () => [scrollableRef.el]
    );

    return virtualItems;
}

let templateCache = Object.create(null);
/**
 * @param {typeof ViewCompiler} ViewCompiler
 * @param {string} key
 * @param {Record<string, Element>} templates
 * @param {Record<string, any>} [params]
 * @returns {Record<string, string>}
 */
export function useViewCompiler(ViewCompiler, templates, params) {
    const compiledTemplates = {};
    let compiler;
    for (const tname in templates) {
        const key = templates[tname].outerHTML;
        if (!templateCache[key]) {
            compiler = compiler || new ViewCompiler(templates);
            templateCache[key] = xml`${compiler.compile(tname, params).outerHTML}`;
        }
        compiledTemplates[tname] = templateCache[key];
    }
    return compiledTemplates;
}
