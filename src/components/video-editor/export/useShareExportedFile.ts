import { useCallback, useState } from "react";
import { toast } from "sonner";

type ShareState =
	| { status: "idle" }
	| { status: "uploading" }
	| { status: "done"; url: string }
	| { status: "error"; message: string };

export function useShareExportedFile() {
	const [shareState, setShareState] = useState<ShareState>({ status: "idle" });

	const ensureConfigured = useCallback(async () => {
		const config = await window.electronAPI.getShareConfig();
		if (config.configured) return true;

		const apiUrl = window.prompt(
			"URL do backend de compartilhamento (ex: https://recordly-share.vercel.app)",
		);
		if (!apiUrl) return false;

		const apiToken = window.prompt(
			"Token de upload (UPLOAD_SECRET configurado no backend, opcional)",
		);

		const result = await window.electronAPI.setShareConfig({
			apiUrl,
			apiToken: apiToken || null,
		});
		if (!result.success) {
			toast.error(result.error || "Failed to save share configuration");
			return false;
		}
		return true;
	}, []);

	const shareExportedFile = useCallback(
		async (filePath: string, title?: string | null) => {
			const configured = await ensureConfigured();
			if (!configured) return;

			setShareState({ status: "uploading" });
			const result = await window.electronAPI.uploadRecording(filePath, title ?? null);

			if (result.success && result.url) {
				setShareState({ status: "done", url: result.url });
				try {
					await navigator.clipboard.writeText(result.url);
					toast.success("Link copiado para a área de transferência!");
				} catch {
					toast.success("Link gerado!");
				}
				return;
			}

			const message = result.error || "Failed to upload recording";
			setShareState({ status: "error", message });
			toast.error(message);
		},
		[ensureConfigured],
	);

	const resetShareState = useCallback(() => setShareState({ status: "idle" }), []);

	return { shareState, shareExportedFile, resetShareState };
}
