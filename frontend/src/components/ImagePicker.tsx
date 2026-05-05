import { useState } from "react";

const MAX_PREVIEW_WIDTH = 1600;

type Props = {
  maxBytes: number;
  onChange: (value?: string) => void;
};

export function ImagePicker({ maxBytes, onChange }: Props) {
  const [preview, setPreview] = useState<string>();
  const [error, setError] = useState<string>();

  async function handleFile(file?: File) {
    setError(undefined);
    setPreview(undefined);
    onChange(undefined);
    if (!file) return;
    if (!["image/jpeg", "image/png", "image/webp"].includes(file.type)) {
      setError("Use a JPEG, PNG, or WebP image.");
      return;
    }
    try {
      const dataUrl = await downscaleImage(file);
      const byteSize = Math.ceil((dataUrl.length * 3) / 4);
      if (byteSize > maxBytes) {
        setError("That image is too large. Try a smaller photo.");
        return;
      }
      setPreview(dataUrl);
      onChange(dataUrl);
    } catch {
      setError("Could not read that image.");
    }
  }

  return (
    <div>
      <label className="block text-sm font-medium text-ink">Image</label>
      <input
        className="mt-2 block w-full rounded border border-ink/15 bg-white px-3 py-2 text-sm"
        type="file"
        accept="image/jpeg,image/png,image/webp"
        onChange={(event) => void handleFile(event.target.files?.[0])}
      />
      {error && <p className="mt-2 text-sm text-coral">{error}</p>}
      {preview && <img className="mt-3 max-h-64 rounded border border-ink/10 object-contain" src={preview} alt="Preview" />}
    </div>
  );
}

function downscaleImage(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(new Error("read failed"));
    reader.onload = () => {
      const image = new Image();
      image.onerror = () => reject(new Error("image failed"));
      image.onload = () => {
        const scale = Math.min(1, MAX_PREVIEW_WIDTH / image.width);
        const canvas = document.createElement("canvas");
        canvas.width = Math.max(1, Math.round(image.width * scale));
        canvas.height = Math.max(1, Math.round(image.height * scale));
        const context = canvas.getContext("2d");
        if (!context) {
          reject(new Error("canvas failed"));
          return;
        }
        context.fillStyle = "#ffffff";
        context.fillRect(0, 0, canvas.width, canvas.height);
        context.drawImage(image, 0, 0, canvas.width, canvas.height);
        resolve(canvas.toDataURL("image/jpeg", 0.86));
      };
      image.src = String(reader.result);
    };
    reader.readAsDataURL(file);
  });
}
