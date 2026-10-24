import React from 'react';
import {AbsoluteFill, Easing, Img, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {Background, Base, family, isBangla, media, useFonts, vmin} from './common';

const clamp = {extrapolateLeft: 'clamp' as const, extrapolateRight: 'clamp' as const};

const useOut = (frames = 10) => {
	const frame = useCurrentFrame();
	const {durationInFrames} = useVideoConfig();
	return interpolate(frame, [durationInFrames - frames, durationInFrames], [1, 0], clamp);
};

// ------------------------------------------------------------------ LogoReveal
export type LogoRevealProps = Base & {logo?: string; name?: string; tagline?: string};
export const LogoReveal: React.FC<LogoRevealProps> = (p) => {
	useFonts();
	const frame = useCurrentFrame();
	const {fps, width, height} = useVideoConfig();
	const accent = p.accent || '#FFB703';
	const size = vmin(width, height, 0.38);
	const s = spring({frame, fps, config: {damping: 12, stiffness: 120}});
	const shine = interpolate(frame, [fps * 0.5, fps * 1.2], [-1.2, 1.2], clamp);
	const ring = spring({frame: frame - 4, fps, config: {damping: 200}});
	const tag = p.tagline || '';
	return (
		<AbsoluteFill style={{justifyContent: 'center', alignItems: 'center', opacity: useOut(8)}}>
			<Background bg={p.bg ?? 'gradient'} accent={accent} />
			<div
				style={{
					position: 'absolute',
					width: size * 1.5,
					height: size * 1.5,
					borderRadius: '50%',
					border: `${Math.max(3, size * 0.02)}px solid ${accent}`,
					transform: `scale(${0.4 + ring * 0.8})`,
					opacity: 1 - ring * 0.85,
				}}
			/>
			<div style={{position: 'relative', transform: `scale(${s})`, overflow: 'hidden'}}>
				{p.logo ? (
					<Img src={media(p.logo)} style={{maxWidth: size * 1.6, maxHeight: size, objectFit: 'contain', display: 'block'}} />
				) : (
					<div style={{fontFamily: family(p.name || 'BRAND', 'Anton'), fontSize: size * 0.45, color: p.textColor || '#fff'}}>
						{p.name || 'BRAND'}
					</div>
				)}
				<div
					style={{
						position: 'absolute',
						inset: 0,
						background: 'linear-gradient(100deg, transparent 35%, rgba(255,255,255,0.3) 50%, transparent 65%)',
						transform: `translateX(${shine * 100}%)`,
					}}
				/>
			</div>
			{tag ? (
				<div
					style={{
						marginTop: size * 0.18,
						fontFamily: family(tag),
						fontWeight: 700,
						fontSize: size * 0.13,
						letterSpacing: isBangla(tag) ? 0 : size * 0.01,
						color: p.textColor || '#fff',
						opacity: interpolate(frame, [fps * 0.6, fps * 1.0], [0, 1], clamp),
						transform: `translateY(${interpolate(frame, [fps * 0.6, fps * 1.0], [20, 0], clamp)}px)`,
					}}
				>
					{tag}
				</div>
			) : null}
		</AbsoluteFill>
	);
};

// ------------------------------------------------------------------ EndSlate (packshot)
export type EndSlateProps = Base & {
	logo?: string;
	product?: string;
	tagline?: string;
	cta?: string;
	website?: string;
	phone?: string;
	handle?: string;
	disclaimer?: string;
};
export const EndSlate: React.FC<EndSlateProps> = (p) => {
	useFonts();
	const frame = useCurrentFrame();
	const {fps, width, height} = useVideoConfig();
	const accent = p.accent || '#FFB703';
	const portrait = height > width * 1.1;
	const u = vmin(width, height, 0.1);
	const prod = spring({frame, fps, config: {damping: 14, stiffness: 110}});
	const logoIn = spring({frame: frame - 6, fps, config: {damping: 200}});
	const ctaIn = spring({frame: frame - 14, fps, config: {damping: 11, stiffness: 160}});
	const info = [p.website, p.phone, p.handle].filter(Boolean) as string[];
	return (
		<AbsoluteFill style={{opacity: useOut(6)}}>
			<Background bg={p.bg ?? 'gradient'} accent={accent} />
			<AbsoluteFill
				style={{
					flexDirection: portrait ? 'column' : 'row',
					alignItems: 'center',
					justifyContent: 'center',
					gap: u * 0.8,
					padding: u,
				}}
			>
				{p.product ? (
					<Img
						src={media(p.product)}
						style={{
							maxWidth: portrait ? width * 0.7 : width * 0.4,
							maxHeight: portrait ? height * 0.38 : height * 0.7,
							objectFit: 'contain',
							transform: `translateY(${(1 - prod) * u * 2}px) scale(${0.85 + 0.15 * prod})`,
							opacity: prod,
							filter: 'drop-shadow(0 20px 40px rgba(0,0,0,0.45))',
						}}
					/>
				) : null}
				<div style={{display: 'flex', flexDirection: 'column', alignItems: portrait || !p.product ? 'center' : 'flex-start', gap: u * 0.3}}>
					{p.logo ? (
						<Img src={media(p.logo)} style={{maxWidth: u * 4.5, maxHeight: u * 1.6, objectFit: 'contain', opacity: logoIn}} />
					) : null}
					{p.tagline ? (
						<div
							style={{
								fontFamily: family(p.tagline, 'Anton'),
								fontSize: u * 0.62,
								color: p.textColor || '#fff',
								textAlign: portrait || !p.product ? 'center' : 'left',
								opacity: logoIn,
								textTransform: isBangla(p.tagline) ? 'none' : 'uppercase',
								lineHeight: 1.1,
							}}
						>
							{p.tagline}
						</div>
					) : null}
					{p.cta ? (
						<div
							style={{
								marginTop: u * 0.2,
								background: accent,
								color: '#111',
								fontFamily: family(p.cta),
								fontWeight: 800,
								fontSize: u * 0.42,
								padding: `${u * 0.18}px ${u * 0.5}px`,
								borderRadius: u * 0.2,
								transform: `scale(${ctaIn})`,
								textTransform: isBangla(p.cta) ? 'none' : 'uppercase',
							}}
						>
							{p.cta}
						</div>
					) : null}
					{info.length ? (
						<div
							style={{
								marginTop: u * 0.15,
								fontFamily: family(info.join(' '), 'Poppins'),
								fontWeight: 700,
								fontSize: u * 0.3,
								color: p.textColor || '#fff',
								opacity: interpolate(frame, [18, 28], [0, 0.95], clamp),
								textAlign: portrait || !p.product ? 'center' : 'left',
							}}
						>
							{info.join('   •   ')}
						</div>
					) : null}
					{p.disclaimer ? (
						<div
							style={{
								marginTop: u * 0.25,
								fontFamily: family(p.disclaimer, 'Poppins'),
								fontSize: u * 0.2,
								color: p.textColor || '#fff',
								opacity: 0.75,
								textAlign: portrait || !p.product ? 'center' : 'left',
							}}
						>
							{p.disclaimer}
						</div>
					) : null}
				</div>
			</AbsoluteFill>
		</AbsoluteFill>
	);
};

// ------------------------------------------------------------------ OfferBadge
export type OfferBadgeProps = Base & {
	label?: string;
	price?: string;
	oldPrice?: string;
	position?: 'top-right' | 'top-left' | 'bottom-right' | 'bottom-left' | 'center';
	scale?: number;
};
const burst = (n: number, r1: number, r2: number) =>
	Array.from({length: n * 2})
		.map((_, i) => {
			const a = (Math.PI * i) / n;
			const r = i % 2 ? r2 : r1;
			return `${50 + r * Math.cos(a)},${50 + r * Math.sin(a)}`;
		})
		.join(' ');
export const OfferBadge: React.FC<OfferBadgeProps> = (p) => {
	useFonts();
	const frame = useCurrentFrame();
	const {fps, width, height} = useVideoConfig();
	const accent = p.accent || '#E63946';
	const d = vmin(width, height, 0.34) * (p.scale ?? 1);
	const s = spring({frame, fps, config: {damping: 9, stiffness: 180}});
	const wob = Math.sin(frame / 6) * 3 * Math.min(1, frame / fps);
	const pos = p.position || 'top-right';
	const m = vmin(width, height, 0.08);
	const style: React.CSSProperties = {position: 'absolute', width: d, height: d};
	if (pos === 'center') Object.assign(style, {left: (width - d) / 2, top: (height - d) / 2});
	if (pos.includes('top')) style.top = height > width ? height * 0.16 : m;
	if (pos.includes('bottom')) style.bottom = height > width ? height * 0.37 : m;
	if (pos.includes('right')) style.right = m;
	if (pos.includes('left')) style.left = m;
	const label = p.label || 'OFFER';
	return (
		<AbsoluteFill style={{opacity: useOut(6)}}>
			<Background bg={p.bg} accent={accent} />
			<div style={{...style, transform: `scale(${s}) rotate(${-12 + wob}deg)`}}>
				<svg viewBox="0 0 100 100" width={d} height={d} style={{position: 'absolute', inset: 0, filter: 'drop-shadow(0 8px 16px rgba(0,0,0,0.4))'}}>
					<polygon points={burst(14, 49, 41)} fill={accent} />
					<circle cx="50" cy="50" r="38" fill="none" stroke="rgba(255,255,255,0.6)" strokeWidth="1.2" strokeDasharray="3 2" />
				</svg>
				<div
					style={{
						position: 'absolute',
						inset: 0,
						display: 'flex',
						flexDirection: 'column',
						alignItems: 'center',
						justifyContent: 'center',
						color: p.textColor || '#fff',
						textAlign: 'center',
						lineHeight: 1,
					}}
				>
					<div style={{fontFamily: family(label, 'Anton'), fontSize: d * (label.length > 8 ? 0.13 : 0.17), textTransform: isBangla(label) ? 'none' : 'uppercase'}}>
						{label}
					</div>
					{p.oldPrice ? (
						<div style={{fontFamily: family(p.oldPrice, 'Poppins'), fontWeight: 700, fontSize: d * 0.1, textDecoration: 'line-through', opacity: 0.8, marginTop: d * 0.03}}>
							{p.oldPrice}
						</div>
					) : null}
					{p.price ? (
						<div style={{fontFamily: family(p.price, 'Anton'), fontSize: d * 0.2, marginTop: d * 0.02}}>{p.price}</div>
					) : null}
				</div>
			</div>
		</AbsoluteFill>
	);
};

// ------------------------------------------------------------------ BeforeAfter
export type BeforeAfterProps = Base & {before: string; after: string; beforeLabel?: string; afterLabel?: string};
export const BeforeAfter: React.FC<BeforeAfterProps> = (p) => {
	useFonts();
	const frame = useCurrentFrame();
	const {fps, width, height, durationInFrames} = useVideoConfig();
	const accent = p.accent || '#FFB703';
	const x = interpolate(frame, [fps * 0.4, durationInFrames * 0.55], [1, 0.5], {
		...clamp,
		easing: Easing.inOut(Easing.cubic),
	});
	const pos = interpolate(frame, [durationInFrames * 0.6, durationInFrames * 0.85], [0.5, 0], {
		...clamp,
		easing: Easing.inOut(Easing.cubic),
	});
	const split = frame < durationInFrames * 0.6 ? x : pos;
	const u = vmin(width, height, 0.05);
	const label = (t: string, side: 'l' | 'r') => (
		<div
			style={{
				position: 'absolute',
				top: height > width ? height * 0.16 : u,
				[side === 'l' ? 'left' : 'right']: u,
				background: 'rgba(0,0,0,0.6)',
				color: '#fff',
				padding: `${u * 0.25}px ${u * 0.6}px`,
				borderRadius: u * 0.3,
				fontFamily: family(t),
				fontWeight: 800,
				fontSize: u * 0.8,
			}}
		>
			{t}
		</div>
	);
	return (
		<AbsoluteFill style={{background: '#000'}}>
			<Img src={media(p.after)} style={{width, height, objectFit: 'cover', position: 'absolute'}} />
			<div style={{position: 'absolute', inset: 0, clipPath: `inset(0 ${(1 - split) * 100}% 0 0)`}}>
				<Img src={media(p.before)} style={{width, height, objectFit: 'cover'}} />
			</div>
			<div style={{position: 'absolute', top: 0, bottom: 0, left: split * width - 3, width: 6, background: accent, boxShadow: `0 0 20px ${accent}`}} />
			{label(p.beforeLabel || 'BEFORE', 'l')}
			{label(p.afterLabel || 'AFTER', 'r')}
		</AbsoluteFill>
	);
};

// ------------------------------------------------------------------ FeatureCallout
export type CalloutItem = {text: string; x: number; y: number; side?: 'left' | 'right'};
export type FeatureCalloutProps = Base & {items: CalloutItem[]};
export const FeatureCallout: React.FC<FeatureCalloutProps> = (p) => {
	useFonts();
	const frame = useCurrentFrame();
	const {fps, width, height} = useVideoConfig();
	const accent = p.accent || '#FFB703';
	const u = vmin(width, height, 0.05);
	return (
		<AbsoluteFill style={{opacity: useOut(8)}}>
			<Background bg={p.bg} accent={accent} />
			{(p.items || []).map((it, i) => {
				const t0 = i * Math.round(fps * 0.5);
				const s = spring({frame: frame - t0, fps, config: {damping: 14}});
				const side = it.side || (it.x > 0.5 ? 'left' : 'right');
				const len = u * 3.2 * s;
				const cx = it.x * width;
				const cy = it.y * height;
				const pulse = 1 + 0.25 * Math.sin((frame - t0) / 5);
				return (
					<React.Fragment key={i}>
						<div style={{position: 'absolute', left: cx - u * 0.35, top: cy - u * 0.35, width: u * 0.7, height: u * 0.7, borderRadius: '50%', background: accent, transform: `scale(${s * pulse})`, boxShadow: `0 0 ${u}px ${accent}`}} />
						<div style={{position: 'absolute', top: cy - 2, height: 4, width: len, background: accent, left: side === 'right' ? cx : cx - len}} />
						<div
							style={{
								position: 'absolute',
								top: cy - u * 0.75,
								[side === 'right' ? 'left' : 'right']: side === 'right' ? cx + u * 3.3 : width - cx + u * 3.3,
								background: 'rgba(10,10,14,0.85)',
								borderLeft: side === 'right' ? `${u * 0.15}px solid ${accent}` : undefined,
								borderRight: side === 'left' ? `${u * 0.15}px solid ${accent}` : undefined,
								color: p.textColor || '#fff',
								padding: `${u * 0.3}px ${u * 0.5}px`,
								fontFamily: family(it.text),
								fontWeight: 800,
								fontSize: u * 0.75,
								opacity: interpolate(frame - t0, [6, 14], [0, 1], clamp),
								whiteSpace: 'nowrap',
							}}
						>
							{it.text}
						</div>
					</React.Fragment>
				);
			})}
		</AbsoluteFill>
	);
};

// ------------------------------------------------------------------ SocialFollow
export type SocialFollowProps = Base & {title?: string; handles: {platform: string; handle: string}[]};
const BADGE: Record<string, [string, string]> = {
	youtube: ['YT', '#FF0033'],
	instagram: ['IG', '#C13584'],
	facebook: ['FB', '#1877F2'],
	tiktok: ['TT', '#111111'],
	x: ['X', '#111111'],
	linkedin: ['in', '#0A66C2'],
	website: ['WWW', '#444444'],
};
export const SocialFollow: React.FC<SocialFollowProps> = (p) => {
	useFonts();
	const frame = useCurrentFrame();
	const {fps, width, height} = useVideoConfig();
	const u = vmin(width, height, 0.06);
	const title = p.title || 'Follow';
	return (
		<AbsoluteFill style={{justifyContent: 'center', alignItems: 'center', opacity: useOut(8)}}>
			<Background bg={p.bg} accent={p.accent} />
			<div style={{fontFamily: family(title, 'Anton'), fontSize: u * 1.3, color: p.textColor || '#fff', marginBottom: u * 0.6, textShadow: '0 4px 20px rgba(0,0,0,0.5)', textTransform: isBangla(title) ? 'none' : 'uppercase'}}>
				{title}
			</div>
			<div style={{display: 'flex', flexDirection: 'column', gap: u * 0.45}}>
				{(p.handles || []).map((h, i) => {
					const s = spring({frame: frame - 4 - i * 5, fps, config: {damping: 13}});
					const [txt, col] = BADGE[h.platform] || [h.platform.slice(0, 2).toUpperCase(), p.accent || '#444'];
					return (
						<div key={i} style={{display: 'flex', alignItems: 'center', gap: u * 0.5, transform: `translateX(${(1 - s) * -width * 0.5}px)`, opacity: s}}>
							<div style={{width: u * 1.5, height: u * 1.5, borderRadius: u * 0.4, background: col, color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: "'Poppins'", fontWeight: 800, fontSize: u * 0.55}}>
								{txt}
							</div>
							<div style={{fontFamily: family(h.handle, 'Poppins'), fontWeight: 800, fontSize: u * 0.8, color: p.textColor || '#fff', textShadow: '0 3px 12px rgba(0,0,0,0.6)'}}>
								{h.handle}
							</div>
						</div>
					);
				})}
			</div>
		</AbsoluteFill>
	);
};
