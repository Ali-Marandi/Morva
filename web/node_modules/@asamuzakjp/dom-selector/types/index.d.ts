/*!
 * DOM Selector - A CSS selector engine.
 * @license MIT
 * @copyright asamuzaK (Kazz)
 * @see {@link https://github.com/asamuzaK/domSelector/blob/main/LICENSE}
 */
export type CheckResult = {
    match: boolean;
    pseudoElement: string | null;
    ast: object | null;
};
export declare class DOMSelector {
    #private;
    constructor(window: Window, document: Document, opt?: object);
    clear: (clearAll?: boolean) => void;
    extractSubjects: (selector: string, caseSensitive?: boolean) => Array<{
        id: string | null;
        className: string | null;
        tag: string | null;
    }>;
    supports: (selector: string) => boolean;
    check: (selector: string, node: Element, opt?: object) => CheckResult;
    matches: (selector: string, node: Element, opt?: object) => boolean;
    closest: (selector: string, node: Element, opt?: object) => Element | null;
    querySelector: (selector: string, node: Document | DocumentFragment | Element, opt?: object) => Element | null;
    querySelectorAll: (selector: string, node: Document | DocumentFragment | Element, opt?: object) => Array<Element>;
}
