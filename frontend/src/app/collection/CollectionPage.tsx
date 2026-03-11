"use client";

import { ChangeEvent, useEffect, useMemo, useRef, useState } from "react";
import { Loader2 } from "lucide-react";

import { Sidebar } from "@/components/navigation/Sidebar";
import { SimpleModal } from "@/app/mypage/components/SimpleModal";
import {
    DiaryDetail,
    DiaryListItem,
    DiaryPayload,
    createDiary,
    fetchDiary,
    fetchDiaries,
    DiaryPlaceSearchResult,
    updateDiary,
    uploadImageDataUrl,
} from "@/services/api";
import { CollectionHeader } from "./components/CollectionHeader";
import { DiaryEditorModal } from "./components/DiaryEditorModal";
import { DiaryGallery } from "./components/DiaryGallery";
import { DiaryLocationPickerModal } from "./components/DiaryLocationPickerModal";
import { EmptyDiaryState } from "./components/EmptyDiaryState";
import { EditorState } from "./types";
import { emptyEditorState, readFileAsDataUrl } from "./utils";

export function CollectionPage() {
    const uploadInputRef = useRef<HTMLInputElement | null>(null);
    const modalImageInputRef = useRef<HTMLInputElement | null>(null);
    // [Feature] 모달 열 때 에디터 스냅샷 (수정 여부 판단용)
    const initialEditorRef = useRef<string>("");

    const [diaries, setDiaries] = useState<DiaryListItem[]>([]);
    const [selectedDiaryId, setSelectedDiaryId] = useState<number | null>(null);
    const [editor, setEditor] = useState<EditorState>(emptyEditorState);
    const [query, setQuery] = useState("");
    const [loading, setLoading] = useState(true);
    const [detailLoading, setDetailLoading] = useState(false);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [isCloseConfirmOpen, setIsCloseConfirmOpen] = useState(false);
    const [isLocationPickerOpen, setIsLocationPickerOpen] = useState(false);
    // [Feature] 저장 확인 팝업 상태
    const [isSaveConfirmOpen, setIsSaveConfirmOpen] = useState(false);

    const loadDiaries = async (nextQuery = "") => {
        setLoading(true);
        setError(null);
        try {
            const items = await fetchDiaries(nextQuery.trim() ? { query: nextQuery.trim() } : undefined);
            setDiaries(Array.isArray(items) ? items : []);
        } catch {
            setError("일기 목록을 불러오지 못했습니다.");
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        let cancelled = false;

        const loadInitial = async () => {
            setLoading(true);
            setError(null);
            try {
                const diaryItems = await fetchDiaries();
                if (cancelled) return;
                setDiaries(Array.isArray(diaryItems) ? diaryItems : []);
            } catch {
                if (!cancelled) setError("일기장을 불러오지 못했습니다.");
            } finally {
                if (!cancelled) setLoading(false);
            }
        };

        void loadInitial();
        return () => {
            cancelled = true;
        };
    }, []);

    useEffect(() => {
        const timer = window.setTimeout(() => {
            void loadDiaries(query);
        }, 250);
        return () => window.clearTimeout(timer);
    }, [query]);

    const selectedDiarySummary = useMemo(
        () => diaries.find((item) => item.id === selectedDiaryId) ?? null,
        [diaries, selectedDiaryId]
    );

    const hydrateEditor = (detail: DiaryDetail) => {
        setEditor({
            id: detail.id,
            title: detail.title,
            content: detail.content,
            entry_date: detail.entry_date,
            cover_image_path: detail.cover_image_path ?? null,
            linked_places: detail.linked_places.map((place) => ({
                name: place.name ?? null,
                adress: place.adress ?? "",
                image_path: place.image_path ?? null,
                longitude: place.longitude ?? 0,
                latitude: place.latitude ?? 0,
                place_id: place.place_id ?? null,
                chat_place_id: place.chat_place_id ?? null,
            })).filter((place) => Boolean(place.adress)),
        });
    };

    const openCreateModal = (coverImagePath?: string | null) => {
        setSelectedDiaryId(null);
        setEditor({
            ...emptyEditorState(),
            cover_image_path: coverImagePath ?? null,
        });
        setError(null);
        setIsModalOpen(true);
        // [Feature] 초기 상태 스냅샷 저장
        initialEditorRef.current = JSON.stringify({ ...emptyEditorState(), cover_image_path: coverImagePath ?? null });
    };

    const openDiaryModal = async (diaryId: number) => {
        setSelectedDiaryId(diaryId);
        setIsModalOpen(true);
        setDetailLoading(true);
        setError(null);
        try {
            const detail = await fetchDiary(diaryId);
            hydrateEditor(detail);
            // [Feature] 기존 일기 초기 상태 스냅샷 저장
            initialEditorRef.current = JSON.stringify({ id: detail.id, title: detail.title, content: detail.content, entry_date: detail.entry_date, cover_image_path: detail.cover_image_path ?? null, linked_places: detail.linked_places });
        } catch {
            setError("일기 상세 정보를 불러오지 못했습니다.");
        } finally {
            setDetailLoading(false);
        }
    };

    const handleSelectImage = async (event: ChangeEvent<HTMLInputElement>, target: "create" | "replace") => {
        const file = event.target.files?.[0];
        if (!file) return;
        try {
            const dataUrl = await readFileAsDataUrl(file);
            if (target === "create" && !isModalOpen) {
                openCreateModal(dataUrl);
            } else {
                setEditor((prev) => ({ ...prev, cover_image_path: dataUrl }));
                setIsModalOpen(true);
            }
        } catch {
            setError("이미지를 읽지 못했습니다.");
        } finally {
            event.target.value = "";
        }
    };

    const buildPayload = async (): Promise<DiaryPayload> => {
        const uploadedCover = editor.cover_image_path
            ? await uploadImageDataUrl(editor.cover_image_path, "diary")
            : null;

        return {
            title: editor.title.trim(),
            content: editor.content.trim(),
            entry_date: editor.entry_date,
            cover_image_path: uploadedCover,
            linked_places: editor.linked_places,
        };
    };

    const handleSave = async () => {
        if (!editor.title.trim() || !editor.content.trim() || !editor.entry_date) {
            setError("제목, 날짜, 본문은 필수입니다.");
            return;
        }

        try {
            setSaving(true);
            setError(null);
            const payload = await buildPayload();
            const detail = editor.id === null
                ? await createDiary(payload)
                : await updateDiary(editor.id, payload);

            await loadDiaries(query);
            hydrateEditor(detail);
            setSelectedDiaryId(detail.id);
            // [Feature] 저장 성공 → 확인 팝업 표시 (모달은 팝업에서 닫음)
            setIsSaveConfirmOpen(true);
        } catch {
            setError("일기 저장에 실패했습니다.");
        } finally {
            setSaving(false);
        }
    };

    const handleRequestClose = () => {
        if (saving) return;
        // [Fix] 수정하지 않고 보기만 한 경우  바로 닫기 (Unsaved 팝업 없이)
        const isDirty = JSON.stringify(editor) !== initialEditorRef.current;
        if (!isDirty) {
            setIsModalOpen(false);
            setError(null);
            return;
        }
        setIsCloseConfirmOpen(true);
    };

    const handleConfirmClose = () => {
        setIsCloseConfirmOpen(false);
        setIsModalOpen(false);
        setError(null);
        if (selectedDiaryId === null) {
            setEditor(emptyEditorState());
        }
    };

    const handlePickLocation = (place: DiaryPlaceSearchResult) => {
        setEditor((prev) => ({
            ...prev,
            linked_places: [{
                name: place.name ?? null,
                adress: place.adress,
                latitude: place.latitude,
                longitude: place.longitude,
                image_path: null,
                place_id: null,
                chat_place_id: null,
            }],
        }));
        setIsLocationPickerOpen(false);
    };

    // [Feature] 저장 확인 팝업에서 "확인" 클릭 → Diary 모달 닫기
    const handleSaveConfirmClose = () => {
        setIsSaveConfirmOpen(false);
        setIsModalOpen(false);
        setError(null);
    };

    return (
        <div className="flex w-full min-h-screen flex-col bg-gray-100 p-3 sm:p-4 gap-4 lg:h-screen lg:flex-row lg:overflow-hidden">
            <div className="flex-none lg:h-full">
                <Sidebar />
            </div>

            <main className="flex min-w-0 flex-1 flex-col overflow-hidden rounded-lg bg-white p-4 sm:p-6 lg:h-full">
                <CollectionHeader
                    query={query}
                    onQueryChange={setQuery}
                    uploadInputRef={uploadInputRef}
                />
                <input
                    ref={uploadInputRef}
                    type="file"
                    accept="image/*"
                    className="hidden"
                    onChange={(event) => void handleSelectImage(event, "create")}
                />

                <div className="flex-1 overflow-y-auto">
                    {loading ? (
                        <div className="flex h-full items-center justify-center text-gray-400">
                            <Loader2 className="h-6 w-6 animate-spin" />
                        </div>
                    ) : diaries.length === 0 ? (
                        <EmptyDiaryState onCreate={() => openCreateModal()} />
                    ) : (
                        <DiaryGallery
                            diaries={diaries}
                            selectedDiaryId={selectedDiaryId}
                            onSelect={(diaryId) => void openDiaryModal(diaryId)}
                        />
                    )}
                </div>
            </main>

            <DiaryEditorModal
                isOpen={isModalOpen}
                detailLoading={detailLoading}
                saving={saving}
                error={error}
                editor={editor}
                selectedDiarySummary={selectedDiarySummary}
                modalImageInputRef={modalImageInputRef}
                onClose={handleRequestClose}
                onImageChange={(event) => void handleSelectImage(event, "replace")}
                onEditorChange={(updater) => setEditor(updater)}
                onOpenLocationPicker={() => setIsLocationPickerOpen(true)}
                onClearLinkedPlace={() => setEditor((prev) => ({ ...prev, linked_places: [] }))}
                onSave={() => void handleSave()}
            />
            <DiaryLocationPickerModal
                isOpen={isLocationPickerOpen}
                initialPlace={editor.linked_places[0] ?? null}
                onClose={() => setIsLocationPickerOpen(false)}
                onConfirm={handlePickLocation}
            />
            <SimpleModal
                open={isCloseConfirmOpen}
                title="Unsaved Diary"
                maxWidth="sm"
                onClose={() => setIsCloseConfirmOpen(false)}
            >
                <div className="space-y-4">
                    <p className="text-sm leading-6 text-gray-600">
                        지금 창을 닫으면, 내용이 저장되지 않습니다.
                        <br />
                        <span className="font-semibold text-gray-900">Save</span> 버튼을 눌러 내용을 저장해주세요.
                    </p>
                    <div className="flex justify-end gap-3">
                        <button
                            type="button"
                            onClick={() => setIsCloseConfirmOpen(false)}
                            className="rounded-full border border-gray-200 px-4 py-2 text-sm font-medium text-gray-600 transition hover:bg-gray-50"
                        >
                            back
                        </button>
                        <button
                            type="button"
                            onClick={handleConfirmClose}
                            className="rounded-full bg-black px-4 py-2 text-sm font-semibold text-white transition hover:bg-gray-800"
                        >
                            Close
                        </button>
                    </div>
                </div>
            </SimpleModal>

            {/* [Feature] Diary 저장 성공 확인 팝업 */}
            <SimpleModal
                open={isSaveConfirmOpen}
                title="Moment Saved"
                onClose={handleSaveConfirmClose}
                maxWidth="sm"
            >
                <div className="space-y-4">
                    <p className="text-sm leading-6 text-gray-600">
                        당신의 Moments가 저장되었습니다!
                    </p>
                    <div className="flex justify-end">
                        <button
                            type="button"
                            onClick={handleSaveConfirmClose}
                            className="rounded-full bg-black px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-gray-800"
                        >
                            확인
                        </button>
                    </div>
                </div>
            </SimpleModal>
        </div>
    );
}
