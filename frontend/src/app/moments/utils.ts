import { EditorState } from "./types";

export const todayString = () => new Date().toISOString().slice(0, 10);

export const emptyEditorState = (): EditorState => ({
  id: null,
  title: "",
  content: "",
  entry_date: todayString(),
  cover_image_path: null,
  linked_places: [],
});

export const readFileAsDataUrl = (file: File) =>
  new Promise<string>((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(typeof reader.result === "string" ? reader.result : "");
    reader.onerror = () => reject(new Error("file-read-failed"));
    reader.readAsDataURL(file);
  });
