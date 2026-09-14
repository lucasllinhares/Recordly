import fs from "node:fs/promises";
import path from "node:path";
import { app, ipcMain } from "electron";

/**
 * Config for the Recordly Share backend (see /web in this repo, deployed to
 * Vercel). Machine-local, never committed: read from env vars first, then
 * from a JSON file in the app's userData dir so it survives across runs
 * without hardcoding secrets into source.
 *
 *   { "apiUrl": "https://your-deployment.vercel.app", "apiToken": "..." }
 */
type ShareConfig = { apiUrl: string; apiToken: string | null };

function getConfigPath() {
	return path.join(app.getPath("userData"), "share-config.json");
}

async function loadShareConfig(): Promise<ShareConfig | null> {
	const envUrl = process.env.RECORDLY_SHARE_URL;
	const envToken = process.env.RECORDLY_SHARE_TOKEN ?? null;
	if (envUrl) {
		return { apiUrl: envUrl.replace(/\/+$/, ""), apiToken: envToken };
	}

	try {
		const raw = await fs.readFile(getConfigPath(), "utf-8");
		const parsed = JSON.parse(raw) as Partial<ShareConfig>;
		if (!parsed.apiUrl) return null;
		return {
			apiUrl: parsed.apiUrl.replace(/\/+$/, ""),
			apiToken: parsed.apiToken ?? null,
		};
	} catch {
		return null;
	}
}

export function registerShareHandlers() {
	ipcMain.handle("share:get-config", async () => {
		const config = await loadShareConfig();
		return { configured: Boolean(config), apiUrl: config?.apiUrl ?? null };
	});

	ipcMain.handle(
		"share:set-config",
		async (_, input: { apiUrl: string; apiToken?: string | null }) => {
			try {
				const config: ShareConfig = {
					apiUrl: input.apiUrl.replace(/\/+$/, ""),
					apiToken: input.apiToken || null,
				};
				await fs.mkdir(path.dirname(getConfigPath()), { recursive: true });
				await fs.writeFile(getConfigPath(), JSON.stringify(config, null, 2), "utf-8");
				return { success: true };
			} catch (error) {
				return { success: false, error: String(error) };
			}
		},
	);

	ipcMain.handle(
		"share:upload-recording",
		async (_, input: { filePath: string; title?: string | null }) => {
			const config = await loadShareConfig();
			if (!config) {
				return {
					success: false,
					needsConfig: true,
					error: "Share backend not configured yet.",
				};
			}

			try {
				const fileBuffer = await fs.readFile(input.filePath);
				const fileName = path.basename(input.filePath);
				const ext = path.extname(fileName).toLowerCase();
				const mimeType = ext === ".gif" ? "image/gif" : "video/mp4";

				const form = new FormData();
				form.append("file", new Blob([new Uint8Array(fileBuffer)], { type: mimeType }), fileName);
				if (input.title) form.append("title", input.title);

				const headers: Record<string, string> = {};
				if (config.apiToken) headers.Authorization = `Bearer ${config.apiToken}`;

				const response = await fetch(`${config.apiUrl}/api/upload`, {
					method: "POST",
					headers,
					body: form,
				});

				if (!response.ok) {
					const text = await response.text().catch(() => "");
					return {
						success: false,
						error: `Upload failed (${response.status}): ${text.slice(0, 300)}`,
					};
				}

				const data = (await response.json()) as { url: string; id: string };
				return { success: true, url: data.url };
			} catch (error) {
				return { success: false, error: String(error) };
			}
		},
	);
}
