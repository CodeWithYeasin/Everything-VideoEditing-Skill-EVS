import React from 'react';
import {AbsoluteFill, continueRender, delayRender, staticFile} from 'remotion';

// Local files passed in props are copied to public/media by remotion_gfx.py.
export const media = (src?: string) =>
	!src ? undefined : /^(https?:|data:)/.test(src) ? src : staticFile(src.replace(/^\/+/, ''));

export type Base = {
	width?: number;
	height?: number;
	fps?: number;
	duration?: number; // seconds
	bg?: string; // 'transparent' | '#hex' | 'gradient'
	accent?: string;
	textColor?: string;
	font?: string; // family name; Bangla text switches to Hind Siliguri automatically
};

const FONTS: [string, string, string][] = [
	['Anton', 'Anton-Regular.ttf', '400'],
	['Poppins', 'Poppins-Bold.ttf', '700'],
	['Poppins', 'Poppins-ExtraBold.ttf', '800'],
	['Hind Siliguri', 'HindSiliguri-Bold.ttf', '700'],
	['Noto Sans Bengali', 'NotoSansBengali.ttf', '100 900'],
];

let loaded = false;
export const useFonts = () => {
	if (loaded || typeof document === 'undefined') return;
	loaded = true;
	const handle = delayRender('fonts');
	const css = FONTS.map(
		([fam, file, weight]) =>
			`@font-face{font-family:'${fam}';src:url('${staticFile('fonts/' + file)}') format('truetype');font-weight:${weight};font-display:block;}`,
	).join('\n');
	const style = document.createElement('style');
	style.innerHTML = css;
	document.head.appendChild(style);
	Promise.all(FONTS.map(([fam, , w]) => document.fonts.load(`${w.split(' ')[0]} 40px '${fam}'`)))
		.catch(() => undefined)
		.finally(() => continueRender(handle));
};

export const isBangla = (s: string) => /[ঀ-৿]/.test(s || '');

export const family = (text: string, wanted?: string) =>
	isBangla(text) ? "'Hind Siliguri', 'Noto Sans Bengali', sans-serif" : `'${wanted || 'Poppins'}', 'Hind Siliguri', sans-serif`;

export const Background: React.FC<{bg?: string; accent?: string}> = ({bg, accent}) => {
	if (!bg || bg === 'transparent') return null;
	if (bg === 'gradient') {
		return (
			<AbsoluteFill
				style={{background: `radial-gradient(120% 120% at 20% 10%, ${accent || '#6C5CE7'} 0%, #111018 60%, #050507 100%)`}}
			/>
		);
	}
	return <AbsoluteFill style={{background: bg}} />;
};

export const vmin = (w: number, h: number, f: number) => Math.min(w, h) * f;
