"use client";

import { ChangeEvent, useEffect, useMemo, useRef, useState } from "react";
import { Loader2 } from "lucide-react";

import { Sidebar } from "@/components/navigation/Sidebar";
import { SimpleModal } from "@/app/mypage/components/SimpleModal";
import {
    MomentDetail,
    MomentListItem,
    MomentPayload,
    MomentPlaceSearchResult,
    createMoment,
    fetchMoment,
    fetchMoments,
    deleteMoment,
    updateMoment,
    uploadImageDataUrl,
} from "@/services/api";
import { MomentsHeader } from "./components/MomentsHeader";
import { MomentEditorModal } from "./components/MomentEditorModal";
import { MomentGallery } from "./components/MomentGallery";
import { MomentLocationPickerModal } from "./components/MomentLocationPickerModal";
import { EmptyMomentState } from "./components/EmptyMomentState";
import { EditorState } from "./types";
import { emptyEditorState, readExifGps, readFileAsDataUrl } from "./utils";
import { useTranslation } from "@/i18n/useTranslation";

export function MomentsPage() {
    const { t } = useTranslation();
    const uploadInputRef = useRef<HTMLInputElement | null>(null);
    const modalImageInputRef = useRef<HTMLInputElement | null>(null);
    // [Feature] 모달 열 때 에디터 스냅샷 (수정 여부 판단용)
    const initialEditorRef = useRef<string>("");

    const [moments, setMoments] = useState<MomentListItem[]>([]);
    const [selectedMomentId, setSelectedMomentId] = useState<number | null>(null);
    const [editor, setEditor] = useState<EditorState>(emptyEditorState());
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
    // [Feature] 삭제 모드 + 다중 선택 + 확인 팝업 상태
    const [isDeleteMode, setIsDeleteMode] = useState(false);
    const [isDeleteConfirmOpen, setIsDeleteConfirmOpen] = useState(false);
    const [selectedToDelete, setSelectedToDelete] = useState<Set<number>>(new Set());

    const loadMoments = async (nextQuery = "") => {
        setLoading(true);
        setError(null);
        try {
            const items = await fetchMoments(nextQuery.trim() ? { query: nextQuery.trim() } : undefined);
            setMoments(Array.isArray(items) ? items : []);
        } catch {
            setError(t("moments.failedToLoadList"));
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
                const momentItems = await fetchMoments();
                if (cancelled) return;
                setMoments(Array.isArray(momentItems) ? momentItems : []);
            } catch {
                if (!cancelled) setError(t("moments.failedToLoadDiaries"));
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
            void loadMoments(query);
        }, 250);
        return () => window.clearTimeout(timer);
    }, [query]);

    const selectedMomentSummary = useMemo(
        () => moments.find((item) => item.id === selectedMomentId) ?? null,
        [moments, selectedMomentId]
    );

    const hydrateEditor = (detail: MomentDetail) => {
        setEditor({
            id: detail.id,
            title: detail.title,
            content: detail.content,
            entry_date: detail.entry_date,
            image_path: detail.image_path ?? null,
            adress: detail.adress ?? null,
            longitude: detail.longitude ?? null,
            latitude: detail.latitude ?? null,
        });
    };

    const openCreateModal = (imagePath?: string | null) => {
        setSelectedMomentId(null);
        setEditor({
            ...emptyEditorState(),
            image_path: imagePath ?? null,
        });
        setError(null);
        setIsEditMode(true);
        setIsModalOpen(true);
        // [Feature] 초기 상태 스냅샷 저장
        initialEditorRef.current = JSON.stringify({ ...emptyEditorState(), image_path: imagePath ?? null });
    };

    const openMomentModal = async (momentId: number) => {
        setSelectedMomentId(momentId);
        setIsEditMode(false);
        setIsModalOpen(true);
        setDetailLoading(true);
        setError(null);
        try {
            const detail = await fetchMoment(momentId);
            hydrateEditor(detail);
            // [Feature] 기존 moment 초기 상태 스냅샷 저장
            initialEditorRef.current = JSON.stringify({
                id: detail.id,
                title: detail.title,
                content: detail.content,
                entry_date: detail.entry_date,
                image_path: detail.image_path ?? null,
                adress: detail.adress ?? null,
                longitude: detail.longitude ?? null,
                latitude: detail.latitude ?? null,
            });
        } catch {
            setError(t("moments.failedToLoadDetail"));
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
                        if (target === "create" && !isModalOpen) {
                            openCreateModal(dataUrl);
                            setEditor((prev) => ({
                                ...prev,
                                adress,
                                latitude: gps.latitude,
                                longitude: gps.longitude,
                            }));
                        } else {
                            setEditor((prev) => ({
                                ...prev,
                                image_path: dataUrl,
                                adress,
                                latitude: gps.latitude,
                                longitude: gps.longitude,
                            }));
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
                setEditor((prev) => ({ ...prev, image_path: dataUrl }));
                setIsEditMode(true);
                setIsModalOpen(true);
            }
        } catch {
            setError(t("moments.failedToReadImage"));
        } finally {
            event.target.value = "";
        }
    };

    const buildPayload = async (): Promise<MomentPayload> => {
        const uploadedImage = editor.image_path
            ? await uploadImageDataUrl(editor.image_path, "diary")
            : null;

        return {
            title: editor.title.trim(),
            content: editor.content.trim(),
            entry_date: editor.entry_date,
            image_path: uploadedImage,
            adress: editor.adress,
            longitude: editor.longitude,
            latitude: editor.latitude,
        };
    };

    const handleSave = async () => {
        if (!editor.title.trim() || !editor.content.trim() || !editor.entry_date) {
            setError(t("moments.requiredFields"));
            return;
        }

        try {
            setSaving(true);
            setError(null);
            const isNew = editor.id === null;
            const payload = await buildPayload();
            const detail = isNew
                ? await createMoment(payload)
                : await updateMoment(editor.id!, payload);

            await loadMoments(query);
            if (isNew) {
                setIsModalOpen(false);
                setEditor(emptyEditorState());
            } else {
                hydrateEditor(detail);
                setSelectedMomentId(detail.id);
                setIsEditMode(false);
                setIsModalOpen(true);
            }
        } catch {
            setError(t("moments.failedToSave"));
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
        if (selectedMomentId === null) {
            setEditor(emptyEditorState());
        }
    };

    const handlePickLocation = (place: MomentPlaceSearchResult) => {
        setEditor((prev) => ({
            ...prev,
            adress: place.adress,
            latitude: place.latitude,
            longitude: place.longitude,
        }));
        setIsLocationPickerOpen(false);
    };


    // [Feature] Delete Memory - 쓰레기통 클릭 -> 삭제 모드 토글
    const handleToggleDeleteMode = () => {
        setIsDeleteMode((prev) => {
            if (prev) setSelectedToDelete(new Set()); // 취소 시 선택 초기화
            return !prev;
        });
    };

    // [Feature] 삭제 모드에서 카드 클릭 -> 다중 선택 토글
    const handleToggleDeleteSelect = (momentId: number) => {
        setSelectedToDelete((prev) => {
            const next = new Set(prev);
            if (next.has(momentId)) next.delete(momentId);
            else next.add(momentId);
            return next;
        });
    };

    // [Feature] 일반 모드 카드 클릭
    const handleGallerySelect = (momentId: number) => {
        void openMomentModal(momentId);
    };

    // [Feature] 삭제 버튼 클릭 -> 선택 항목 있으면 확인 팝업
    const handleRequestDelete = () => {
        if (selectedToDelete.size === 0) return;
        setIsDeleteConfirmOpen(true);
    };

    // [Feature] 삭제 확인 -> 선택된 항목 모두 삭제
    const handleConfirmDelete = async () => {
        try {
            await Promise.all(Array.from(selectedToDelete).map((id) => deleteMoment(id)));
            if (selectedMomentId !== null && selectedToDelete.has(selectedMomentId)) {
                setSelectedMomentId(null);
                setEditor(emptyEditorState());
            }
            await loadMoments(query);
        } catch {
            setError(t("moments.failedToDelete"));
        } finally {
            setSelectedToDelete(new Set());
            setIsDeleteConfirmOpen(false);
            setIsDeleteMode(false);
        }
    };

    // [Feature] 저장 확인 팝업에서 "확인" 클릭 → 모달 닫기
    const handleSaveConfirmClose = () => {
        setIsSaveConfirmOpen(false);
        setIsModalOpen(false);
        setError(null);
    };

    // LocationPicker에 전달할 initialPlace 계산
    const locationPickerInitialPlace: MomentPlaceSearchResult | null =
        editor.adress && editor.latitude != null && editor.longitude != null
            ? { name: null, adress: editor.adress, latitude: editor.latitude, longitude: editor.longitude }
            : null;

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
                    isDeleteMode={isDeleteMode}
                    deleteCount={selectedToDelete.size}
                    onConfirmDelete={handleRequestDelete}
                />


                <div className="flex-1 overflow-y-auto">
                    {loading ? (
                        <div className="flex h-full items-center justify-center text-gray-400">
                            <Loader2 className="h-6 w-6 animate-spin" />
                        </div>
                    ) : moments.length === 0 ? (
                        <EmptyMomentState onCreate={() => openCreateModal()} />
                    ) : (
                        <MomentGallery
                            diaries={moments}
                            selectedDiaryId={selectedMomentId}
                            onSelect={handleGallerySelect}
                            isDeleteMode={isDeleteMode}
                            selectedToDelete={selectedToDelete}
                            onToggleDeleteSelect={handleToggleDeleteSelect}
                        />
                    )}
                </div>
            </main>

            <MomentEditorModal
                isOpen={isModalOpen}
                isEditMode={isEditMode}
                detailLoading={detailLoading}
                saving={saving}
                error={error}
                editor={editor}
                selectedMomentSummary={selectedMomentSummary}
                modalImageInputRef={modalImageInputRef}
                onClose={handleRequestClose}
                onEnterEditMode={() => setIsEditMode(true)}
                onImageChange={(event) => void handleSelectImage(event, "replace")}
                onEditorChange={(updater) => setEditor(updater)}
                onOpenLocationPicker={() => setIsLocationPickerOpen(true)}
                onClearLocation={() => setEditor((prev) => ({ ...prev, adress: null, longitude: null, latitude: null }))}
                onSave={() => void handleSave()}
            />
            <MomentLocationPickerModal
                isOpen={isLocationPickerOpen}
                initialPlace={locationPickerInitialPlace}
                onClose={() => setIsLocationPickerOpen(false)}
                onConfirm={handlePickLocation}
            />
            <SimpleModal
                open={isCloseConfirmOpen}
                title={t("moments.unsavedTitle")}
                maxWidth="sm"
                onClose={() => setIsCloseConfirmOpen(false)}
            >
                <div className="space-y-4">
                    <p className="text-sm leading-6 text-gray-600">
                        {t("moments.unsavedWarning")}
                        <br />
                        {t("moments.savePrompt", { save: t("common.save") })}
                    </p>
                    <div className="flex justify-end gap-3">
                        <button
                            type="button"
                            onClick={() => setIsCloseConfirmOpen(false)}
                            className="rounded-full border border-gray-200 px-4 py-2 text-sm font-medium text-gray-600 transition hover:bg-gray-50"
                        >
                            {t("common.back")}
                        </button>
                        <button
                            type="button"
                            onClick={handleConfirmClose}
                            className="rounded-full bg-black px-4 py-2 text-sm font-semibold text-white transition hover:bg-gray-800"
                        >
                            {t("common.close")}
                        </button>
                    </div>
                </div>
            </SimpleModal>

            {/* [Feature] 저장 성공 확인 팝업 */}
            <SimpleModal
                open={isSaveConfirmOpen}
                title={t("moments.savedTitle")}
                onClose={handleSaveConfirmClose}
                maxWidth="sm"
            >
                <div className="space-y-4">
                    <p className="text-sm leading-6 text-gray-600">
                        {t("moments.momentSaved")}
                    </p>
                    <div className="flex justify-end">
                        <button
                            type="button"
                            onClick={handleSaveConfirmClose}
                            className="rounded-full bg-black px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-gray-800"
                        >
                            {t("common.confirm")}
                        </button>
                    </div>
                </div>
            </SimpleModal>
            {/* [Feature] Delete Memory - 삭제 확인 팝업 */}
            <SimpleModal
                open={isDeleteConfirmOpen}
                title={t("moments.deleteMemory")}
                onClose={() => { setIsDeleteConfirmOpen(false); }}
                maxWidth="sm"
            >
                <div className="space-y-4">
                    <p className="text-sm leading-6 text-gray-600">
                        {t("moments.deleteConfirmation")}
                    </p>
                    <div className="flex justify-end gap-3">
                        <button
                            type="button"
                            onClick={() => { setIsDeleteConfirmOpen(false); }}
                            className="rounded-full border border-gray-200 px-4 py-2 text-sm font-medium text-gray-600 transition hover:bg-gray-50"
                        >
                            {t("common.no")}
                        </button>
                        <button
                            type="button"
                            onClick={() => void handleConfirmDelete()}
                            className="rounded-full bg-red-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-red-700"
                        >
                            {t("common.yes")}
                        </button>
                    </div>
                </div>
            </SimpleModal>
        </div>
    );
}
