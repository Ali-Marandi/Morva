export declare class Evaluator {
    #private;
    window: object;
    documentCache: WeakMap<WeakKey, any>;
    check: boolean | undefined;
    noexcept: boolean | undefined;
    warn: boolean | undefined;
    matchOpts: {
        warn: boolean;
    } | undefined;
    node: object | undefined;
    pseudoElements: any[] | undefined;
    invalidate: boolean | undefined;
    constructor(window: object);
    setup(selector: string, node: object, opt?: {
        check?: boolean;
        noexcept?: boolean;
        warn?: boolean;
    }): object;
    onError: (e: Error, opt?: {
        noexcept?: boolean;
    }) => void;
    clearResults: (all?: boolean) => void;
    matchSelector: (ast: object, node: object, opt: object) => boolean;
    matchLeaves: (leaves: Array<object>, node: object, opt: object) => boolean;
    getFilterLeaves: (leaves: Array<object>) => Array<object>;
    evaluateShadowHost: (ast: object, node: object) => boolean;
    matchPseudoClassSelector: (ast: object, node: object, opt?: {
        forgive?: boolean;
        warn?: boolean;
    }) => Set<object> | boolean;
    createTreeWalker: (node: object, opt?: {
        force?: boolean;
        whatToShow?: number;
    }) => object;
    yieldCombinatorMatches(twig: object, node: object, opt?: {
        dir?: string;
    }): Generator<any, void, unknown>;
    yieldTraverseAllDescendants(baseNode: object, leaves: Array<object>, opt: object): Generator<any, void, unknown>;
    yieldFindDescendantNodes(leaves: Array<object>, baseNode: object, opt: object): Generator<any, void, unknown>;
}
