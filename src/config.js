import fs from 'fs';
import path from 'path';
import yaml from 'yaml';

const ROOT_DIR = path.resolve('.');
const CONFIG_DIR = path.join(ROOT_DIR, 'config');
const DATA_DIR = path.join(ROOT_DIR, 'data');
const ASSETS_DIR = path.join(ROOT_DIR, 'assets');

export function ensureProjectDirsExist() {
	const directoriesToEnsure = [CONFIG_DIR, DATA_DIR, ASSETS_DIR, path.join(ASSETS_DIR, 'designs')];
	directoriesToEnsure.forEach((directoryPath) => {
		if (!fs.existsSync(directoryPath)) {
			fs.mkdirSync(directoryPath, { recursive: true });
		}
	});
}

export function getPaths() {
	return { ROOT_DIR, CONFIG_DIR, DATA_DIR, ASSETS_DIR };
}

export function readChannelsConfig() {
	const { CONFIG_DIR } = getPaths();
	const configFilePath = path.join(CONFIG_DIR, 'channels.yaml');
	if (!fs.existsSync(configFilePath)) {
		return { youtubeChannels: [] };
	}
	const raw = fs.readFileSync(configFilePath, 'utf-8');
	const parsed = yaml.parse(raw) || {};
	return {
		youtubeChannels: Array.isArray(parsed.youtubeChannels) ? parsed.youtubeChannels : [],
	};
}

export function getEnv() {
	return {
		port: Number(process.env.PORT || 8787),
		baseUrl: process.env.BASE_URL || 'http://localhost:8787',
	};
}

