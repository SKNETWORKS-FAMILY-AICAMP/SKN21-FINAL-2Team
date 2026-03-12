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
    deleteDiary,
    updateDiary,
    uploadImageDataUrl,
} from "@/services/api";
import { MomentsHeader } from "./components/MomentsHeader";
import { DiaryEditorModal } from "./components/DiaryEditorModal";
import { DiaryGallery } from "./components/DiaryGallery";
import { DiaryLocationPickerModal } from "./components/DiaryLocationPickerModal";
import { EmptyDiaryState } from "./components/EmptyDiaryState";
import { EditorState } from "./types";
import { emptyEditorState, readExifGps, readFileAsDataUrl } from "./utils";

export function MomentsPage() {
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
    const [isEditMode, setIsEditMode] = useState(false);
    const [isCloseConfirmOpen, setIsCloseConfirmOpen] = useState(false);
    const [isLocationPickerOpen, setIsLocationPickerOpen] = useState(false);
    // [Feature] 저장 확인 팝업 상태
    const [isSaveConfirmOpen, setIsSaveConfirmOpen] = useState(false);
    // [Feature] 삭제 모드 + 확인 팝업 상태
    const [isDeleteMode, setIsDeleteMode] = useState(false);
    const [isDeleteConfirmOpen, setIsDeleteConfirmOpen] = useState(false);
    const [deletingDiaryId, setDeletingDiaryId] = useState<number | null>(null);

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
        setIsEditMode(true);
        setIsModalOpen(true);
        // [Feature] 초기 상태 스냅샷 저장
        initialEditorRef.current = JSON.stringify({ ...emptyEditorState(), cover_image_path: coverImagePath ?? null });
    };

    const openDiaryModal = async (diaryId: number) => {
        setSelectedDiaryId(diaryId);
        setIsEditMode(false);
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
            const [dataUrl, gps] = await Promise.all([
                readFileAsDataUrl(file),
                readExifGps(file),
            ]);

            // EXIF GPS 있으면 Kakao 역지오코딩으로 장소 자동 첨부
            if (gps?.latitude && gps?.longitude) {
                const kakaoKey = process.env.NEXT_PUBLIC_KAKAO_REST_API_KEY ?? "";
                try {
                    const res = await fetch(
                        `https://dapi.kakao.com/v2/local/geo/coord2address.json?x=${gps.longitude}&y=${gps.latitude}`,
                        { headers: { Authorization: `KakaoAK ${kakaoKey}` } }
                    );
                    const data = await res.json();
                    const doc = data.documents?.[0];
                    const adress = doc?.road_address?.address_name || doc?.address?.address_name;
                    if (adress) {
                        const autoPlace: DiaryPlaceSearchResult = {
                            name: null,
                            adress,
                            latitude: gps.latitude,
                            longitude: gps.longitude,
                        };
                        if (target === "create" && !isModalOpen) {
                            openCreateModal(dataUrl);
                            setEditor((prev) => ({ ...prev, linked_places: [{ ...autoPlace, image_path: null, place_id: null, chat_place_id: null }] }));
                        } else {
                            setEditor((prev) => ({ ...prev, cover_image_path: dataUrl, linked_places: [{ ...autoPlace, image_path: null, place_id: null, chat_place_id: null }] }));
                            setIsEditMode(true);
                            setIsModalOpen(true);
                        }
                        return;
                    }
                } catch { /* 역지오코딩 실패 시 무시 */ }
            }

            // GPS 없거나 역지오코딩 실패: 기존 로직
            if (target === "create" && !isModalOpen) {
                openCreateModal(dataUrl);
            } else {
                setEditor((prev) => ({ ...prev, cover_image_path: dataUrl }));
                setIsEditMode(true);
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
            const isNew = editor.id === null;
            const payload = await buildPayload();
            const detail = isNew
                ? await createDiary(payload)
                : await updateDiary(editor.id!, payload);

            await loadDiaries(query);
            if (isNew) {
                setIsModalOpen(false);
                setEditor(emptyEditorState());
            } else {
                hydrateEditor(detail);
                setSelectedDiaryId(detail.id);
                setIsEditMode(false);
                setIsModalOpen(true);
            }
        } catch {
            setError("일기 저장에 실패했습니다.");
        } finally {
            setSaving(false);
        }
    };

    const handleRequestClose = () => {
        if (saving) return;
        if (!isEditMode) {
            setIsModalOpen(false);
            setError(null);
            return;
        }
        setIsCloseConfirmOpen(true);
    };

    const handleConfirmClose = () => {
        setIsCloseConfirmOpen(false);
        setIsModalOpen(false);
        setIsEditMode(false);
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


    // [Feature] Delete Memory - 쓰레기통 클릭 -> 삭제 모드 토글
    const handleToggleDeleteMode = () => {
        setIsDeleteMode((prev) => !prev);
    };

    // [Feature] 삭제 모드에서 카드 클릭 -> 확인 팝업
    const handleGallerySelect = (diaryId: number) => {
        if (isDeleteMode) {
            setDeletingDiaryId(diaryId);
            setIsDeleteConfirmOpen(true);
        } else {
            void openDiaryModal(diaryId);
        }
    };

    // [Feature] 삭제 확인 -> 실제 삭제 실행
    const handleConfirmDelete = async () => {
        if (deletingDiaryId === null) return;
        try {
            await deleteDiary(deletingDiaryId);
            if (selectedDiaryId === deletingDiaryId) {
                setSelectedDiaryId(null);
                setEditor(emptyEditorState());
            }
            await loadDiaries(query);
        } catch {
            setError("일기 삭제에 실패했습니다.");
        } finally {
            setDeletingDiaryId(null);
            setIsDeleteConfirmOpen(false);
            setIsDeleteMode(false);
        }
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
                <MomentsHeader
                    query={query}
                    onQueryChange={setQuery}
                    onCreate={() => openCreateModal()}
                    onDeleteSelect={handleToggleDeleteMode}
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
                            onSelect={handleGallerySelect}
                            isDeleteMode={isDeleteMode}
                        />
                    )}
                </div>
            </main>

            <DiaryEditorModal
                isOpen={isModalOpen}
                isEditMode={isEditMode}
                detailLoading={detailLoading}
                saving={saving}
                error={error}
                editor={editor}
                selectedDiarySummary={selectedDiarySummary}
                modalImageInputRef={modalImageInputRef}
                onClose={handleRequestClose}
                onEnterEditMode={() => setIsEditMode(true)}
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
            {/* [Feature] Delete Memory - 삭제 확인 팝업 */}
            <SimpleModal
                open={isDeleteConfirmOpen}
                title="Delete Memory"
                onClose={() => { setIsDeleteConfirmOpen(false); setDeletingDiaryId(null); }}
                maxWidth="sm"
            >
                <div className="space-y-4">
                    <p className="text-sm leading-6 text-gray-600">
                        정말로 추억을 지우시겠습니까?
                    </p>
                    <div className="flex justify-end gap-3">
                        <button
                            type="button"
                            onClick={() => { setIsDeleteConfirmOpen(false); setDeletingDiaryId(null); }}
                            className="rounded-full border border-gray-200 px-4 py-2 text-sm font-medium text-gray-600 transition hover:bg-gray-50"
                        >
                            아니요
                        </button>
                        <button
                            type="button"
                            onClick={() => void handleConfirmDelete()}
                            className="rounded-full bg-red-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-red-700"
                        >
                            네
                        </button>
                    </div>
                </div>
            </SimpleModal>
        </div>
    );
}
