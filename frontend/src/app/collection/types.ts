import { DiaryLinkedPlaceInput } from "@/services/api";

export type LinkedPlaceDraft = DiaryLinkedPlaceInput;

export type EditorState = {
  id: number | null;
  title: string;
  content: string;
  entry_date: string;
  cover_image_path: string | null;
  linked_places: LinkedPlaceDraft[];
};
