import { createCacheKey, getCache, setCache } from "./cache.js";
import { isString } from "./common.js";
import { splitValue } from "./util.js";
import { SYN_COLOR_TYPE, SYN_FN_CALC, SYN_FN_LIGHT_DARK, SYN_FN_REL, SYN_FN_VAR, SYN_MIX, VAL_COMP, VAL_SPEC } from "./constant.js";
import { NAMED_COLORS, convertRgbToHex, resolveColorFunc, resolveColorMix, resolveColorValue } from "./color.js";
import { resolveRelativeColor } from "./relative-color.js";
import { cssCalc, resolveVar } from "./css-calc-var.js";
//#region src/js/resolve.ts
/**
* resolve
*/
var NAMESPACE = "resolve";
var RGB_TRANSPARENT = "rgba(0, 0, 0, 0)";
var REG_COLOR = new RegExp(`^(?:${SYN_COLOR_TYPE})$`);
var REG_FN_CALC = new RegExp(SYN_FN_CALC);
var REG_FN_COLOR = /^(?:(?:ok)?l(?:ab|ch)|color(?:-mix)?|hsla?|hwb|rgba?|var)\(/;
var REG_FN_LIGHT_DARK = new RegExp(SYN_FN_LIGHT_DARK);
var REG_FN_REL = new RegExp(SYN_FN_REL);
var REG_FN_VAR = new RegExp(SYN_FN_VAR);
var REG_MIX = new RegExp(SYN_MIX);
/**
* resolve color
* @param value - CSS color value
* @param opt - options
* @returns resolved color
*/
var resolveColor = (value, opt = {}) => {
	if (!isString(value)) throw new TypeError(`${value} is not a string.`);
	value = value.trim();
	const { colorScheme = "normal", currentColor = "", format = VAL_COMP, nullable = false } = opt;
	const cacheKey = createCacheKey({
		namespace: NAMESPACE,
		name: "resolve",
		value
	}, opt);
	const cachedResult = getCache(cacheKey);
	if (cachedResult !== false) return cachedResult.item;
	if (REG_FN_VAR.test(value)) {
		if (format === "specifiedValue") {
			setCache(cacheKey, value);
			return value;
		}
		const resolvedVar = resolveVar(value, opt);
		if (resolvedVar === null) {
			const res = format === "hex" || format === "hexAlpha" || nullable ? null : RGB_TRANSPARENT;
			setCache(cacheKey, res);
			return res;
		}
		value = resolvedVar;
	}
	if (opt.format !== format) opt.format = format;
	value = value.toLowerCase();
	if (REG_FN_LIGHT_DARK.test(value) && value.endsWith(")")) {
		const colorParts = value.replace(REG_FN_LIGHT_DARK, "").replace(/\)$/, "");
		const [light = "", dark = ""] = splitValue(colorParts, { delimiter: "," });
		if (light && dark) {
			if (format === "specifiedValue") {
				const lightColor = resolveColor(light, opt);
				const darkColor = resolveColor(dark, opt);
				const res = lightColor && darkColor ? `light-dark(${lightColor}, ${darkColor})` : "";
				setCache(cacheKey, res);
				return res;
			}
			const resolved = resolveColor(colorScheme === "dark" ? dark : light, opt);
			const res = resolved === null && !nullable ? RGB_TRANSPARENT : resolved;
			setCache(cacheKey, res);
			return res;
		}
		let invalidRes;
		if (format === "specifiedValue") invalidRes = "";
		else if (format === "hex" || format === "hexAlpha") invalidRes = null;
		else invalidRes = RGB_TRANSPARENT;
		setCache(cacheKey, invalidRes);
		return invalidRes;
	}
	if (REG_FN_REL.test(value)) {
		const resolvedRel = resolveRelativeColor(value, opt, resolveColor);
		if (format === "computedValue") {
			const res = resolvedRel === null && !nullable ? RGB_TRANSPARENT : resolvedRel;
			setCache(cacheKey, res);
			return res;
		}
		if (format === "specifiedValue") {
			const res = resolvedRel === null ? "" : resolvedRel;
			setCache(cacheKey, res);
			return res;
		}
		value = resolvedRel === null ? "" : resolvedRel;
	}
	if (REG_FN_CALC.test(value)) value = cssCalc(value, opt);
	let cs = "";
	let r = NaN;
	let g = NaN;
	let b = NaN;
	let alpha = NaN;
	if (value === "transparent") {
		let res;
		switch (format) {
			case VAL_SPEC:
				res = value;
				break;
			case "hex":
				res = null;
				break;
			case "hexAlpha":
				res = "#00000000";
				break;
			default: res = RGB_TRANSPARENT;
		}
		setCache(cacheKey, res);
		return res;
	}
	if (value === "currentcolor") {
		if (format === "specifiedValue") {
			setCache(cacheKey, value);
			return value;
		}
		if (currentColor) {
			let resolvedCurrent;
			if (currentColor.startsWith("color-mix(")) resolvedCurrent = resolveColorMix(currentColor, opt, resolveColor);
			else if (currentColor.startsWith("color(")) resolvedCurrent = resolveColorFunc(currentColor, opt);
			else resolvedCurrent = resolveColorValue(currentColor, opt);
			if (resolvedCurrent === null) {
				setCache(cacheKey, null);
				return null;
			}
			[cs, r, g, b, alpha] = resolvedCurrent;
		} else {
			const res = format === "computedValue" ? RGB_TRANSPARENT : value;
			if (format === "computedValue") {
				setCache(cacheKey, res);
				return res;
			}
		}
	} else if (format === "specifiedValue") {
		let res = "";
		if (value.startsWith("color-mix(")) {
			const mixRes = resolveColorMix(value, opt, resolveColor);
			res = mixRes ? mixRes : "";
		} else if (value.startsWith("color(")) {
			const funcRes = resolveColorFunc(value, opt);
			if (isString(funcRes)) res = funcRes;
			else if (Array.isArray(funcRes)) {
				const [scs, rr, gg, bb, aa] = funcRes;
				res = aa === 1 ? `color(${scs} ${rr} ${gg} ${bb})` : `color(${scs} ${rr} ${gg} ${bb} / ${aa})`;
			}
		} else {
			const rgb = resolveColorValue(value, opt);
			if (isString(rgb)) res = rgb;
			else if (Array.isArray(rgb)) {
				const [scs, rr, gg, bb, aa] = rgb;
				if (scs === "rgb") res = aa === 1 ? `${scs}(${rr}, ${gg}, ${bb})` : `${scs}a(${rr}, ${gg}, ${bb}, ${aa})`;
				else res = aa === 1 ? `${scs}(${rr} ${gg} ${bb})` : `${scs}(${rr} ${gg} ${bb} / ${aa})`;
			}
		}
		setCache(cacheKey, res);
		return res;
	} else if (value.startsWith("color-mix(")) {
		if (currentColor) value = value.replace(/currentcolor/g, currentColor);
		value = value.replace(/transparent/g, RGB_TRANSPARENT);
		const resolvedMix = resolveColorMix(value, opt, resolveColor);
		if (resolvedMix === null) {
			setCache(cacheKey, null);
			return null;
		}
		[cs, r, g, b, alpha] = resolvedMix;
	} else if (value.startsWith("color(")) {
		const resolvedFunc = resolveColorFunc(value, opt);
		if (resolvedFunc === null) {
			setCache(cacheKey, null);
			return null;
		}
		[cs, r, g, b, alpha] = resolvedFunc;
	} else if (value) {
		const resolvedVal = resolveColorValue(value, opt);
		if (resolvedVal === null) {
			setCache(cacheKey, null);
			return null;
		}
		[cs, r, g, b, alpha] = resolvedVal;
	}
	let finalRes = "";
	switch (format) {
		case "hex":
		case "hexAlpha":
			if (Number.isNaN(r) || Number.isNaN(g) || Number.isNaN(b) || Number.isNaN(alpha) || format === "hex" && alpha === 0) finalRes = null;
			else finalRes = convertRgbToHex([
				r,
				g,
				b,
				format === "hex" ? 1 : alpha
			]);
			break;
		default: if (cs === "rgb") finalRes = alpha === 1 ? `${cs}(${r}, ${g}, ${b})` : `${cs}a(${r}, ${g}, ${b}, ${alpha})`;
		else if ([
			"lab",
			"lch",
			"oklab",
			"oklch"
		].includes(cs)) finalRes = alpha === 1 ? `${cs}(${r} ${g} ${b})` : `${cs}(${r} ${g} ${b} / ${alpha})`;
		else finalRes = alpha === 1 ? `color(${cs} ${r} ${g} ${b})` : `color(${cs} ${r} ${g} ${b} / ${alpha})`;
	}
	setCache(cacheKey, finalRes);
	return finalRes;
};
/**
* resolve CSS color
* @param value - CSS color value. system colors are not supported
* @param opt - options
* @returns resolved value
*/
var resolve = (value, opt = {}) => {
	opt.nullable = false;
	return resolveColor(value, opt);
};
/**
* is color
* @param value - CSS value
* @param opt - options
* @returns result
*/
var isColor = (value, opt = {}) => {
	if (!isString(value)) return false;
	const str = value.toLowerCase().trim();
	if (!str) return false;
	if (/^[a-z]+$/.test(str)) return str === "currentcolor" || str === "transparent" || Object.hasOwn(NAMED_COLORS, str);
	if (REG_COLOR.test(str) || REG_MIX.test(str)) return true;
	if (REG_FN_COLOR.test(str)) {
		const colorOpt = {
			...opt,
			nullable: true
		};
		if (!colorOpt.format) colorOpt.format = VAL_SPEC;
		return !!resolveColor(str, colorOpt);
	}
	return false;
};
//#endregion
export { isColor, resolve, resolveColor };

//# sourceMappingURL=resolve.js.map