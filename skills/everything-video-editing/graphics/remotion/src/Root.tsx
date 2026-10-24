import React from 'react';
import {CalculateMetadataFunction, Composition} from 'remotion';
import {
	CallToAction,
	Countdown,
	EndCard,
	KineticText,
	LowerThird,
	ProgressBar,
	StatCounter,
	TitleCard,
	Wordmark,
} from './comps';
import type {Base} from './common';
import {BeforeAfter, EndSlate, FeatureCallout, LogoReveal, OfferBadge, SocialFollow} from './ovc';

// width/height/fps/duration come from the props, so one composition fits any canvas.
const meta: CalculateMetadataFunction<Base> = ({props}) => {
	const fps = props.fps ?? 30;
	return {
		width: props.width ?? 1920,
		height: props.height ?? 1080,
		fps,
		durationInFrames: Math.max(1, Math.round((props.duration ?? 3) * fps)),
	};
};

const C = (id: string, component: React.FC<any>, defaultProps: Record<string, unknown>) => (
	<Composition
		key={id}
		id={id}
		component={component}
		width={1920}
		height={1080}
		fps={30}
		durationInFrames={90}
		defaultProps={defaultProps}
		calculateMetadata={meta}
	/>
);

export const Root: React.FC = () => (
	<>
		{C('TitleCard', TitleCard, {title: 'Your Big Title', subtitle: 'A short subtitle', accent: '#FFD400', bg: 'transparent', duration: 3})}
		{C('LowerThird', LowerThird, {name: 'Name Surname', role: 'Role / Channel', accent: '#FFD400', bg: 'transparent', duration: 5})}
		{C('CallToAction', CallToAction, {text: 'SUBSCRIBE', sub: 'for more videos', icon: 'bell', accent: '#FF0033', bg: 'transparent', duration: 3})}
		{C('EndCard', EndCard, {title: 'Thanks for watching', sub: '@yourchannel', slots: 2, accent: '#FFD400', duration: 8})}
		{C('KineticText', KineticText, {words: ['THIS', 'WILL', 'CHANGE', 'EVERYTHING'], perWord: 0.4, bg: 'transparent', duration: 1.8})}
		{C('StatCounter', StatCounter, {value: 10000, suffix: '+', label: 'Happy users', bg: 'transparent', duration: 3})}
		{C('ProgressBar', ProgressBar, {accent: '#FFD400', bg: 'transparent', duration: 30})}
		{C('Countdown', Countdown, {from: 3, bg: 'transparent', duration: 4})}
		{C('Wordmark', Wordmark, {text: 'Everything-videoEditing', subtitle: 'one prompt, finished video', accent: '#D97757', bg: '#141413', duration: 4})}
		{C('LogoReveal', LogoReveal, {name: 'BRAND', tagline: 'Your tagline here', accent: '#FFB703', duration: 3})}
		{C('EndSlate', EndSlate, {tagline: 'Taste the difference', cta: 'Order now', website: 'brand.com', accent: '#FFB703', duration: 4})}
		{C('OfferBadge', OfferBadge, {label: '50% OFF', price: '৳499', oldPrice: '৳999', position: 'top-right', bg: 'transparent', duration: 3})}
		{C('BeforeAfter', BeforeAfter, {before: '', after: '', duration: 4})}
		{C('FeatureCallout', FeatureCallout, {items: [{text: 'Feature one', x: 0.4, y: 0.4}], bg: 'transparent', duration: 4})}
		{C('SocialFollow', SocialFollow, {title: 'Follow us', handles: [{platform: 'youtube', handle: '@channel'}], bg: 'transparent', duration: 3})}
	</>
);
