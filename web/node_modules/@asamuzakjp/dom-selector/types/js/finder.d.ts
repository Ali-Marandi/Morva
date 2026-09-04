import { Evaluator } from './evaluator.js';
export declare class Finder extends Evaluator {
    #private;
    setup(selector: string, node: object, opt?: {
        check?: boolean;
        noexcept?: boolean;
        warn?: boolean;
    }): object;
    find: (targetType: string) => Set<object> | object;
}
