import fs from 'fs';
import path from 'path';
import { getPaths } from '../config.js';

function readJson(filePath, fallback) {
	try {
		return JSON.parse(fs.readFileSync(filePath, 'utf-8'));
	} catch {
		return fallback;
	}
}

function writeJson(filePath, data) {
	fs.mkdirSync(path.dirname(filePath), { recursive: true });
	fs.writeFileSync(filePath, JSON.stringify(data, null, 2));
}

export function getDbPaths() {
	const { DATA_DIR } = getPaths();
	return {
		creatorsPath: path.join(DATA_DIR, 'creators.json'),
		ordersPath: path.join(DATA_DIR, 'orders.json'),
		productsPath: path.join(DATA_DIR, 'products.json'),
	};
}

export function loadCreators() {
	const { creatorsPath } = getDbPaths();
	return readJson(creatorsPath, { creators: [] });
}

export function saveCreators(doc) {
	const { creatorsPath } = getDbPaths();
	writeJson(creatorsPath, doc);
}

export function upsertCreator({ twitch, stripeConnectId = '', autoPublish = true }) {
	const doc = loadCreators();
	const idx = doc.creators.findIndex((c) => c.twitch?.toLowerCase() === String(twitch).toLowerCase());
	const payload = {
		twitch: String(twitch),
		stripeConnectId: String(stripeConnectId || ''),
		autoPublish: Boolean(autoPublish),
		createdAt: new Date().toISOString(),
		updatedAt: new Date().toISOString(),
	};
	if (idx >= 0) {
		doc.creators[idx] = { ...doc.creators[idx], ...payload, createdAt: doc.creators[idx].createdAt, updatedAt: new Date().toISOString() };
	} else {
		doc.creators.push(payload);
	}
	saveCreators(doc);
	return payload;
}

export function findCreatorByTwitch(twitch) {
	const doc = loadCreators();
	return doc.creators.find((c) => c.twitch?.toLowerCase() === String(twitch).toLowerCase()) || null;
}

