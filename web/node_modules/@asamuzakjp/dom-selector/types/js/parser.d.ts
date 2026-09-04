export declare const unescapeSelector: (selector?: string) => string;
export declare const preprocess: (value: string) => string;
export declare const parseSelector: (sel: string, context?: string) => object;
export declare const walkAST: (ast?: object, toObject?: boolean, callback?: Function) => {
    branches: Array<object>;
    info: object;
};
export declare const compareASTNodes: (a: object, b: object) => number;
export declare const sortAST: (asts: Array<object>) => Array<object>;
export declare const parseAstName: (selector: string) => {
    prefix: string;
    localName: string;
};
export declare const extractSubjectsAst: (ast: object) => Array<{
    id: string | null;
    className: string | null;
    tag: string | null;
}>;
export { find as findAST, generate as generateCSS } from 'css-tree';
