import { extractDashedIdent, resolveLengthInPixels, splitValue } from "./js/util.js";
import { isColor, resolve } from "./js/resolve.js";
import { cssCalc, cssVar } from "./js/css-calc-var.js";
import { isGradient, resolveGradient } from "./js/css-gradient.js";
import { convert } from "./js/convert.js";
//#region src/index.ts
/*!
* CSS color - Resolve, parse, convert CSS color.
* @license MIT
* @copyright asamuzaK (Kazz)
* @see {@link https://github.com/asamuzaK/cssColor/blob/main/LICENSE}
*/
var utils = {
	cssCalc,
	cssVar,
	extractDashedIdent,
	isColor,
	isGradient,
	resolveGradient,
	resolveLengthInPixels,
	splitValue
};
//#endregion
export { convert, resolve, utils };

//# sourceMappingURL=index.js.map