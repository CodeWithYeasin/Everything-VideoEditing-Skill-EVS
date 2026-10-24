import React from 'react';
import {AbsoluteFill, Easing, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {Background, Base, family, isBangla, useFonts, vmin} from './common';

const useOutro = (frames = 12) => {
	const frame = useCurrentFrame();
	const {durationInFrames} = useVideoConfig();
	return interpolate(frame, [durationInFrames - frames, durationInFrames], [1, 0], {
		extrapolateLeft: 'clamp',
		extrapolateRight: 'clamp',
	});
};

// ------------------------------------------------------------------ TitleCard
export type TitleCardProps = Base & {title: string; subtitle?: string; align?: 'center' | 'left'};
export const TitleCard: React.FC<TitleCardProps> = (p) => {
	useFonts();
	const frame = useCurrentFrame();
	const {fps, width, height} = useVideoConfig();
	const out = useOutro(10);
	const accent = p.accent || '#FFD400';
	const color = p.textColor || '#FFFFFF';
	const words = (p.title || '').split(' ');
	const big = vmin(width, height, isBangla(p.title) ? 0.11 : 0.13);
	const lineIn = spring({frame: frame - 6, fps, config: {damping: 200}});
	return (
		<AbsoluteFill style={{opacity: out}}>
			<Background bg={p.bg} accent={accent} />
			<AbsoluteFill
				style={{
					justifyContent: 'center',
					alignItems: p.align === 'left' ? 'flex-start' : 'center',
					padding: width * 0.08,
				}}
			>
				<div
					style={{
						fontFamily: family(p.title, p.font || 'Anton'),
						fontSize: big,
						lineHeight: 1.05,
						color,
						textTransform: isBangla(p.title) ? 'none' : 'uppercase',
						textAlign: p.align === 'left' ? 'left' : 'center',
						textShadow: '0 6px 30px rgba(0,0,0,0.45)',
						display: 'flex',
						flexWrap: 'wrap',
						justifyContent: p.align === 'left' ? 'flex-start' : 'center',
						gap: big * 0.25,
					}}
				>
					{words.map((w, i) => {
						const s = spring({frame: frame - i * 4, fps, config: {damping: 12, stiffness: 160}});
						return (
							<span
								key={i}
								style={{
									display: 'inline-block',
									transform: `translateY(${(1 - s) * big * 0.6}px) scale(${0.6 + 0.4 * s})`,
									opacity: Math.min(1, s * 1.5),
								}}
							>
								{w}
							</span>
						);
					})}
				</div>
				<div
					style={{
						height: Math.max(6, big * 0.07),
						width: `${lineIn * 22}%`,
						background: accent,
						borderRadius: 99,
						margin: `${big * 0.25}px 0`,
					}}
				/>
				{p.subtitle ? (
					<div
						style={{
							fontFamily: family(p.subtitle, 'Poppins'),
							fontWeight: 700,
							fontSize: big * 0.32,
							color,
							opacity: interpolate(frame, [12, 24], [0, 0.92], {extrapolateRight: 'clamp'}),
							letterSpacing: isBangla(p.subtitle) ? 0 : big * 0.02,
							textAlign: p.align === 'left' ? 'left' : 'center',
						}}
					>
						{p.subtitle}
					</div>
				) : null}
			</AbsoluteFill>
		</AbsoluteFill>
	);
};

// ------------------------------------------------------------------ LowerThird
export type LowerThirdProps = Base & {name: string; role?: string; side?: 'left' | 'right'};
export const LowerThird: React.FC<LowerThirdProps> = (p) => {
	useFonts();
	const frame = useCurrentFrame();
	const {fps, width, height, durationInFrames} = useVideoConfig();
	const accent = p.accent || '#FFD400';
	const s = spring({frame, fps, config: {damping: 18, stiffness: 140}});
	const e = spring({frame: frame - (durationInFrames - 14), fps, config: {damping: 200}});
	const x = (1 - s + e) * (p.side === 'right' ? 1 : -1) * width * 0.6;
	const size = vmin(width, height, 0.055);
	const right = p.side === 'right';
	return (
		<AbsoluteFill>
			<Background bg={p.bg} accent={accent} />
			<div
				style={{
					position: 'absolute',
					bottom: height * (height > width ? 0.2 : 0.12),
					[right ? 'right' : 'left']: width * 0.06,
					transform: `translateX(${x}px)`,
					display: 'flex',
					flexDirection: right ? 'row-reverse' : 'row',
					alignItems: 'stretch',
				}}
			>
				<div style={{width: size * 0.18, background: accent, borderRadius: 4}} />
				<div
					style={{
						background: 'rgba(12,12,16,0.82)',
						padding: `${size * 0.35}px ${size * 0.6}px`,
						borderRadius: 6,
						margin: right ? `0 ${size * 0.15}px 0 0` : `0 0 0 ${size * 0.15}px`,
						textAlign: right ? 'right' : 'left',
					}}
				>
					<div style={{fontFamily: family(p.name), fontWeight: 800, fontSize: size, color: p.textColor || '#fff', lineHeight: 1.15}}>
						{p.name}
					</div>
					{p.role ? (
						<div
							style={{
								fontFamily: family(p.role),
								fontWeight: 700,
								fontSize: size * 0.55,
								color: accent,
								opacity: interpolate(frame, [8, 18], [0, 1], {extrapolateRight: 'clamp'}),
							}}
						>
							{p.role}
						</div>
					) : null}
				</div>
			</div>
		</AbsoluteFill>
	);
};

// ------------------------------------------------------------------ CallToAction
export type CTAProps = Base & {text?: string; sub?: string; icon?: 'bell' | 'like' | 'none'};
export const CallToAction: React.FC<CTAProps> = (p) => {
	useFonts();
	const frame = useCurrentFrame();
	const {fps, width, height} = useVideoConfig();
	const out = useOutro(10);
	const accent = p.accent || '#FF0033';
	const size = vmin(width, height, 0.07);
	const s = spring({frame, fps, config: {damping: 11, stiffness: 170}});
	const pressed = interpolate(frame, [fps * 0.9, fps * 1.0, fps * 1.2], [1, 0.9, 1], {
		extrapolateLeft: 'clamp',
		extrapolateRight: 'clamp',
	});
	const done = frame > fps * 1.0;
	const text = p.text || 'SUBSCRIBE';
	return (
		<AbsoluteFill style={{justifyContent: 'center', alignItems: 'center', opacity: out}}>
			<Background bg={p.bg} accent={accent} />
			<div style={{transform: `scale(${s * pressed})`, display: 'flex', alignItems: 'center', gap: size * 0.4}}>
				<div
					style={{
						background: done ? '#2b2b2b' : accent,
						color: '#fff',
						fontFamily: family(text),
						fontWeight: 800,
						fontSize: size,
						padding: `${size * 0.35}px ${size * 0.8}px`,
						borderRadius: size * 0.3,
						boxShadow: '0 10px 40px rgba(0,0,0,0.45)',
						textTransform: isBangla(text) ? 'none' : 'uppercase',
					}}
				>
					{done && !isBangla(text) && text.toUpperCase() === 'SUBSCRIBE' ? 'SUBSCRIBED' : text}
				</div>
				{p.icon !== 'none' ? (
					<div
						style={{
							fontSize: size * 1.1,
							transform: `rotate(${done ? Math.sin(frame / 2) * 12 * Math.max(0, 1 - (frame - fps) / fps) : 0}deg)`,
							filter: 'drop-shadow(0 6px 18px rgba(0,0,0,0.5))',
						}}
					>
						<svg width={size * 1.1} height={size * 1.1} viewBox="0 0 24 24" fill="#fff">
							{p.icon === 'like' ? (
								<path d="M2 21h4V9H2v12zm20-11c0-1.1-.9-2-2-2h-6.3l1-4.6v-.3c0-.4-.2-.8-.4-1.1L13.2 1 6.6 7.6C6.2 8 6 8.5 6 9v10c0 1.1.9 2 2 2h9c.8 0 1.5-.5 1.8-1.2l3-7.1c.1-.2.2-.5.2-.7v-2z" />
							) : (
								<path d="M12 22c1.1 0 2-.9 2-2h-4c0 1.1.9 2 2 2zm6-6v-5c0-3.1-1.6-5.6-4.5-6.3V4c0-.8-.7-1.5-1.5-1.5S10.5 3.2 10.5 4v.7C7.6 5.4 6 7.9 6 11v5l-2 2v1h16v-1l-2-2z" />
							)}
						</svg>
					</div>
				) : null}
			</div>
			{p.sub ? (
				<div
					style={{
						marginTop: size * 0.5,
						fontFamily: family(p.sub),
						fontWeight: 700,
						fontSize: size * 0.45,
						color: '#fff',
						textShadow: '0 3px 12px rgba(0,0,0,0.7)',
						opacity: interpolate(frame, [10, 20], [0, 1], {extrapolateRight: 'clamp'}),
					}}
				>
					{p.sub}
				</div>
			) : null}
		</AbsoluteFill>
	);
};

// ------------------------------------------------------------------ EndCard
export type EndCardProps = Base & {title?: string; sub?: string; slots?: number};
export const EndCard: React.FC<EndCardProps> = (p) => {
	useFonts();
	const frame = useCurrentFrame();
	const {fps, width, height} = useVideoConfig();
	const accent = p.accent || '#FFD400';
	const size = vmin(width, height, 0.075);
	const title = p.title || 'Thanks for watching';
	const slots = p.slots ?? 2;
	const portrait = height > width;
	return (
		<AbsoluteFill style={{alignItems: 'center', justifyContent: 'center'}}>
			<Background bg={p.bg ?? 'gradient'} accent={accent} />
			<div
				style={{
					fontFamily: family(title, 'Anton'),
					fontSize: size,
					color: '#fff',
					textTransform: isBangla(title) ? 'none' : 'uppercase',
					transform: `translateY(${(1 - spring({frame, fps, config: {damping: 200}})) * 40}px)`,
					opacity: interpolate(frame, [0, 10], [0, 1], {extrapolateRight: 'clamp'}),
					textAlign: 'center',
				}}
			>
				{title}
			</div>
			{p.sub ? (
				<div style={{fontFamily: family(p.sub), fontWeight: 700, fontSize: size * 0.4, color: accent, marginTop: size * 0.2}}>
					{p.sub}
				</div>
			) : null}
			<div style={{display: 'flex', flexDirection: portrait ? 'column' : 'row', gap: size * 0.5, marginTop: size * 0.7}}>
				{Array.from({length: slots}).map((_, i) => {
					const s = spring({frame: frame - 8 - i * 5, fps, config: {damping: 14}});
					return (
						<div
							key={i}
							style={{
								width: (portrait ? width * 0.7 : width * 0.3),
								aspectRatio: '16 / 9',
								border: `${Math.max(3, size * 0.06)}px solid ${accent}`,
								borderRadius: size * 0.2,
								background: 'rgba(255,255,255,0.06)',
								transform: `scale(${s})`,
							}}
						/>
					);
				})}
			</div>
		</AbsoluteFill>
	);
};

// ------------------------------------------------------------------ KineticText
export type KineticProps = Base & {words: string[]; perWord?: number};
export const KineticText: React.FC<KineticProps> = (p) => {
	useFonts();
	const frame = useCurrentFrame();
	const {fps, width, height} = useVideoConfig();
	const per = Math.max(4, Math.round((p.perWord ?? 0.45) * fps));
	const i = Math.min(p.words.length - 1, Math.floor(frame / per));
	const local = frame - i * per;
	const w = p.words[i] || '';
	const s = spring({frame: local, fps, config: {damping: 10, stiffness: 220}});
	const size = vmin(width, height, isBangla(w) ? 0.15 : 0.18) * Math.min(1, 7 / Math.max(3, w.length));
	const accent = p.accent || '#FFD400';
	return (
		<AbsoluteFill style={{justifyContent: 'center', alignItems: 'center'}}>
			<Background bg={p.bg} accent={accent} />
			<div
				style={{
					fontFamily: family(w, p.font || 'Anton'),
					fontSize: size,
					color: i % 3 === 2 ? accent : p.textColor || '#fff',
					transform: `scale(${0.5 + 0.5 * s}) rotate(${(1 - s) * (i % 2 ? 6 : -6)}deg)`,
					textTransform: isBangla(w) ? 'none' : 'uppercase',
					textShadow: '0 8px 30px rgba(0,0,0,0.5)',
					WebkitTextStroke: isBangla(w) ? undefined : `${size * 0.02}px rgba(0,0,0,0.6)`,
				}}
			>
				{w}
			</div>
		</AbsoluteFill>
	);
};

// ------------------------------------------------------------------ StatCounter
export type StatProps = Base & {value: number; prefix?: string; suffix?: string; label?: string; decimals?: number};
export const StatCounter: React.FC<StatProps> = (p) => {
	useFonts();
	const frame = useCurrentFrame();
	const {fps, width, height} = useVideoConfig();
	const out = useOutro(10);
	const v = interpolate(frame, [0, fps * 1.4], [0, p.value], {
		extrapolateRight: 'clamp',
		easing: Easing.out(Easing.cubic),
	});
	const size = vmin(width, height, 0.2);
	const accent = p.accent || '#FFD400';
	return (
		<AbsoluteFill style={{justifyContent: 'center', alignItems: 'center', opacity: out}}>
			<Background bg={p.bg} accent={accent} />
			<div style={{fontFamily: "'Anton', sans-serif", fontSize: size, color: accent, textShadow: '0 8px 30px rgba(0,0,0,0.5)'}}>
				{p.prefix || ''}
				{v.toLocaleString('en-US', {maximumFractionDigits: p.decimals ?? 0, minimumFractionDigits: p.decimals ?? 0})}
				{p.suffix || ''}
			</div>
			{p.label ? (
				<div style={{fontFamily: family(p.label), fontWeight: 800, fontSize: size * 0.22, color: p.textColor || '#fff'}}>{p.label}</div>
			) : null}
		</AbsoluteFill>
	);
};

// ------------------------------------------------------------------ ProgressBar
export type ProgressProps = Base & {thickness?: number; position?: 'top' | 'bottom'};
export const ProgressBar: React.FC<ProgressProps> = (p) => {
	const frame = useCurrentFrame();
	const {durationInFrames, height} = useVideoConfig();
	const t = Math.max(4, p.thickness ?? height * 0.008);
	return (
		<AbsoluteFill>
			<div
				style={{
					position: 'absolute',
					[p.position === 'bottom' ? 'bottom' : 'top']: 0,
					left: 0,
					height: t,
					width: `${(frame / (durationInFrames - 1)) * 100}%`,
					background: p.accent || '#FFD400',
					boxShadow: `0 0 ${t * 2}px ${p.accent || '#FFD400'}`,
				}}
			/>
		</AbsoluteFill>
	);
};

// ------------------------------------------------------------------ Countdown
export type CountdownProps = Base & {from?: number};
export const Countdown: React.FC<CountdownProps> = (p) => {
	useFonts();
	const frame = useCurrentFrame();
	const {fps, width, height} = useVideoConfig();
	const from = p.from ?? 3;
	const n = from - Math.floor(frame / fps);
	const local = frame % fps;
	const s = spring({frame: local, fps, config: {damping: 9, stiffness: 200}});
	const size = vmin(width, height, 0.4);
	return (
		<AbsoluteFill style={{justifyContent: 'center', alignItems: 'center'}}>
			<Background bg={p.bg} accent={p.accent} />
			<div
				style={{
					fontFamily: "'Anton', sans-serif",
					fontSize: size,
					color: p.textColor || '#fff',
					transform: `scale(${1.6 - 0.6 * s})`,
					opacity: interpolate(local, [0, 4, fps - 6, fps], [0, 1, 1, 0]),
					textShadow: `0 0 40px ${p.accent || '#FFD400'}`,
				}}
			>
				{n > 0 ? n : 'GO!'}
			</div>
		</AbsoluteFill>
	);
};

// ------------------------------------------------------------------ Wordmark
// Animated name / channel intro: letters drop in, a light sweep and an underline grow.
export type WordmarkProps = Base & {text: string; subtitle?: string; size?: number};
export const Wordmark: React.FC<WordmarkProps> = (p) => {
	useFonts();
	const frame = useCurrentFrame();
	const {fps, width, height, durationInFrames} = useVideoConfig();
	const accent = p.accent || '#D97757';
	const text = p.text || 'Wordmark';
	const chars = Array.from(text);
	const fontSize = Math.min(height * (p.subtitle ? 0.36 : 0.5), (width * 0.92) / Math.max(4, chars.length * 0.56)) * (p.size ?? 1);
	const sweep = interpolate(frame, [fps * 0.9, fps * 1.9], [-0.3, 1.3], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
	const line = spring({frame: frame - Math.round(fps * 0.8), fps, config: {damping: 200}});
	const loopOut = interpolate(frame, [durationInFrames - 8, durationInFrames], [1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
	return (
		<AbsoluteFill style={{justifyContent: 'center', alignItems: 'center', opacity: loopOut}}>
			<Background bg={p.bg} accent={accent} />
			<div style={{position: 'relative', display: 'flex', fontFamily: family(text, p.font || 'Poppins'), fontWeight: 800, fontSize, color: accent, lineHeight: 1}}>
				{chars.map((c, i) => {
					const s = spring({frame: frame - i * 1.6, fps, config: {damping: 11, stiffness: 170}});
					return (
						<span key={i} style={{display: 'inline-block', whiteSpace: 'pre', transform: `translateY(${(1 - s) * -fontSize * 0.8}px)`, opacity: Math.min(1, s * 1.4)}}>
							{c}
						</span>
					);
				})}
				<div
					style={{
						position: 'absolute',
						inset: 0,
						background: `linear-gradient(100deg, transparent ${(sweep - 0.12) * 100}%, rgba(255,255,255,0.35) ${sweep * 100}%, transparent ${(sweep + 0.12) * 100}%)`,
						pointerEvents: 'none',
					}}
				/>
			</div>
			<div style={{height: Math.max(4, fontSize * 0.07), width: `${line * Math.min(80, chars.length * 4)}%`, background: accent, borderRadius: 99, marginTop: fontSize * 0.18, opacity: 0.9}} />
			{p.subtitle ? (
				<div style={{marginTop: fontSize * 0.22, fontFamily: family(p.subtitle, 'Poppins'), fontWeight: 700, fontSize: fontSize * 0.26, color: p.textColor || '#E8E6DC', opacity: interpolate(frame, [fps * 1.1, fps * 1.6], [0, 0.98], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}), letterSpacing: fontSize * 0.01}}>
					{p.subtitle}
				</div>
			) : null}
		</AbsoluteFill>
	);
};
