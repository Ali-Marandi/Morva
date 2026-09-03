export declare const matchPseudoElementSelector: (astName: string, astType: string, { forgive, globalObject, warn }?: {
    forgive?: boolean;
    globalObject?: object;
    warn?: boolean;
}) => void;
export declare const matchDirectionPseudoClass: (ast: object, node: object, dirCache?: WeakMap<any, any>) => boolean;
export declare const matchLanguagePseudoClass: (ast: object, node: object, langCache?: WeakMap<any, any>) => boolean;
export declare const matchCheckedPseudoClass: (node: object) => boolean;
export declare const matchLinkPseudoClass: (node: object) => boolean;
export declare const matchOpenPseudoClass: (node: object) => boolean;
export declare const matchPlaceholderShownPseudoClass: (node: object, keys: Set<string>) => boolean;
export declare const matchRangePseudoClass: (astName: string, node: object, keys: Set<string>) => boolean;
export declare const matchReadOnlyPseudoClass: (astName: string, node: object) => boolean;
export declare const matchRequiredPseudoClass: (astName: string, node: object, keys: Set<string>) => boolean;
export declare const matchAttributeSelector: (ast: object, node: object, { check, forgive, globalObject }?: {
    check?: boolean;
    forgive?: boolean;
    globalObject?: object;
}) => boolean;
export declare const matchTypeSelector: (ast: object, node: object, { check, forgive, globalObject }?: {
    check?: boolean;
    forgive?: boolean;
    globalObject?: object;
}) => boolean;
