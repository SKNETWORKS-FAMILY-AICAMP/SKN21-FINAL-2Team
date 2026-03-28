import { useState, useEffect } from "react";
import type { ReservationItem } from "../types";
import { useTranslation } from "@/i18n/useTranslation";
import { ocrReservationImage } from "@/services/api";
import { resolveImageUrl } from "@/lib/imageUrl";
import { TEMPLATE_MAP } from "./ReservationFormSection";

export interface OcrMessage {
  type: "success" | "error";
  text: string;
}

interface UseReservationFormProps {
  open: boolean;
  reservation: ReservationItem | null;
  photoUrl?: string;
  onSavePhoto: (nextUrl: string | null) => Promise<void> | void;
  onSaveTitle?: (newTitle: string) => Promise<void> | void;
  onSaveCategory?: (newCategory: string) => Promise<void> | void;
  onSaveDetails?: (newDetails: Record<string, string>) => Promise<void> | void;
  onClose: (wasSaved: boolean, isNewDraft: boolean, shouldDeleteDraft?: boolean) => void;
}

/** Check if a title represents a new draft reservation (any language) */
export function isNewDraftTitle(title: string | undefined | null, t: (key: string) => string): boolean {
  if (!title) return true;
  return title === t("mypage.newReservation") || title === "Reservation" || title === "새 예약" || title === "New Reservation" || title === "新しい予約" || title === "新预订";
}

export function useReservationForm({
  open,
  reservation,
  photoUrl,
  onSavePhoto,
  onSaveTitle,
  onSaveCategory,
  onSaveDetails,
  onClose,
}: UseReservationFormProps) {
  const { t } = useTranslation();
  
  const [draftPhotoUrl, setDraftPhotoUrl] = useState<string | null | undefined>(undefined);
  const [draftDate, setDraftDate] = useState<string>("");
  const [draftCategory, setDraftCategory] = useState<string>(reservation?.category || "transportation");
  const [draftDetails, setDraftDetails] = useState<Record<string, string>>({});
  
  const [editingTitle, setEditingTitle] = useState(false);
  const [draftTitle, setDraftTitle] = useState(reservation?.title || "");
  const [previewOpen, setPreviewOpen] = useState(false);
  const [isOcrLoading, setIsOcrLoading] = useState(false);
  const [ocrMessage, setOcrMessage] = useState<OcrMessage | null>(null);
  const [showCloseWarning, setShowCloseWarning] = useState(false);
  const [showSuccessMessage, setShowSuccessMessage] = useState(false);
  const [isEditMode, setIsEditMode] = useState(false);
  const [promptOpen, setPromptOpen] = useState(false);
  const [promptValue, setPromptValue] = useState("");

  const initialPhotoUrl = (typeof photoUrl === "string" && photoUrl.trim().length
    ? photoUrl
    : (typeof reservation?.reservationImageUrl === "string" && reservation.reservationImageUrl.trim().length
      ? reservation.reservationImageUrl
      : null));
  const effectivePhotoUrl = draftPhotoUrl === undefined ? initialPhotoUrl : draftPhotoUrl;
  const previewPhotoUrl = effectivePhotoUrl ? resolveImageUrl(effectivePhotoUrl) : undefined;

  useEffect(() => {
    if (open) {
      const isNewDraft = !reservation?.reservationId || reservation.reservationId === -1;
      const pTitle = isNewDraft ? "" : (reservation?.title || "");
      setDraftTitle(pTitle);

      const pCategory = reservation?.category || "transportation";
      setDraftCategory(pCategory);
      setDraftPhotoUrl(undefined);
      setDraftDate("");
      setEditingTitle(false);
      setOcrMessage(null);
      setShowSuccessMessage(false);

      const existingDetails = reservation?.details;
      let pDetails: Record<string, string> = {};
      if (Array.isArray(existingDetails)) {
        existingDetails.forEach((d) => {
          pDetails[d.label] = d.value;
        });
      }

      const isDraftByTitle = isNewDraftTitle(reservation?.title, t);

    // 신규 작성 상���에서 아무것도 변경 안하고 닫을 때만 삭제 경고 무시
    if (Object.keys(pDetails).length === 0 && (!reservation?.title || isNewDraft || isDraftByTitle)) {
        const newKeys = TEMPLATE_MAP[pCategory] || TEMPLATE_MAP["etc"];
        newKeys.forEach(k => { pDetails[k] = ""; });
        setIsEditMode(true);
      } else {
        setIsEditMode(false);
      }
      setDraftDetails(pDetails);
    }
  }, [open, reservation, t]);

  const hasChanges = () => {
    if (!isEditMode) return false;

    const photoChanged = draftPhotoUrl !== undefined;
    const initialTitle = reservation?.title || "";
    const titleChanged = Boolean(reservation) && draftTitle !== initialTitle;
    const initialCategory = reservation?.category || "etc";
    const categoryChanged = draftCategory !== initialCategory;

    let originalDetails: Record<string, string> = {};
    if (Array.isArray(reservation?.details)) {
      reservation.details.forEach(d => {
        originalDetails[d.label] = d.value;
      });
    }

    if (Object.keys(originalDetails).length === 0 && isNewDraftTitle(reservation?.title, t)) {
      const newKeys = TEMPLATE_MAP[initialCategory] || TEMPLATE_MAP["etc"];
      newKeys.forEach(k => { originalDetails[k] = ""; });
    }

    let detailsChanged = false;
    const draftKeys = Object.keys(draftDetails);
    const originalKeys = Object.keys(originalDetails);

    if (draftKeys.length !== originalKeys.length) {
      detailsChanged = true;
    } else {
      for (const key of draftKeys) {
        if (draftDetails[key] !== originalDetails[key]) {
          detailsChanged = true;
          break;
        }
      }
    }
    return photoChanged || titleChanged || categoryChanged || detailsChanged;
  };

  const handleClose = () => {
    const isNewDraft = isNewDraftTitle(reservation?.title, t);
    if (!isEditMode) {
      onClose(false, isNewDraft);
      return;
    }
    if (hasChanges()) {
      setShowCloseWarning(true);
    } else {
      onClose(false, isNewDraft);
    }
  };

  const handleSave = async () => {
    await onSavePhoto(effectivePhotoUrl ?? null);

    if (onSaveTitle && draftTitle !== reservation?.title) {
      await onSaveTitle(draftTitle);
    }
    if (onSaveCategory && draftCategory !== (reservation?.category || "etc")) {
      await onSaveCategory(draftCategory);
    }
    if (onSaveDetails && Object.keys(draftDetails).length > 0) {
      await onSaveDetails(draftDetails);
    }

    setShowSuccessMessage(true);
    setTimeout(() => {
      setShowSuccessMessage(false);
      const isNewDraft = isNewDraftTitle(reservation?.title, t);
      onClose(true, isNewDraft);
    }, 1500);
  };

  const handleOcr = async () => {
    if (!effectivePhotoUrl) return;
    setIsOcrLoading(true);
    setOcrMessage(null);

    try {
      let result;
      if (effectivePhotoUrl.startsWith("data:image/")) {
        const res = await fetch(effectivePhotoUrl);
        const blob = await res.blob();
        const mimeType = blob.type || "image/jpeg";
        let extension = mimeType.split('/')[1] || "jpg";
        if (extension === "jpeg") extension = "jpg";
        const file = new File([blob], `ticket.${extension}`, { type: mimeType });
        result = await ocrReservationImage({ file, category: draftCategory });
      } else {
        const resolvedForOcr = resolveImageUrl(effectivePhotoUrl);
        const ocrImagePath = resolvedForOcr.startsWith("http")
          ? resolvedForOcr
          : effectivePhotoUrl;
        result = await ocrReservationImage({ imagePath: ocrImagePath, category: draftCategory });
      }

      if (result.date) {
        const CATEGORY_MAP_TRANSLATED: Record<string, string> = {
          transportation: t("mypage.catTransport"),
          hotel: t("mypage.catHotel"),
          restaurant: t("mypage.catRestaurant"),
          activity: t("mypage.catActivity"),
          etc: t("mypage.catEtc"),
        };

        const autoTitle = `${CATEGORY_MAP_TRANSLATED[draftCategory] || t("mypage.reservationSuffix")} ${result.date}`;
        if (!draftTitle || isNewDraftTitle(draftTitle, t)) {
          setDraftTitle(autoTitle);
        }

        if (result.details) {
          setDraftDetails(result.details);
        }
        setOcrMessage({
          type: "success",
          text: t("mypage.ocrSuccess"),
        });
      } else {
        setOcrMessage({
          type: "error",
          text: t("mypage.ocrFail"),
        });
      }
    } catch (e) {
      setOcrMessage({ type: "error", text: t("mypage.ocrError") });
      console.error(e);
    } finally {
      setIsOcrLoading(false);
    }
  };

  return {
    state: {
      draftPhotoUrl,
      draftDate,
      draftCategory,
      draftDetails,
      editingTitle,
      draftTitle,
      previewOpen,
      isOcrLoading,
      ocrMessage,
      showCloseWarning,
      showSuccessMessage,
      isEditMode,
      promptOpen,
      promptValue,
      photoUrl,
      effectivePhotoUrl,
      previewPhotoUrl,
      canSave: isEditMode && draftTitle.trim().length > 0 && !isNewDraftTitle(draftTitle, t),
    },
    actions: {
      setDraftPhotoUrl,
      setDraftDate,
      setDraftCategory,
      setDraftDetails,
      setEditingTitle,
      setDraftTitle,
      setPreviewOpen,
      setIsOcrLoading,
      setOcrMessage,
      setShowCloseWarning,
      setShowSuccessMessage,
      setIsEditMode,
      setPromptOpen,
      setPromptValue,
      handleClose,
      handleSave,
      handleOcr
    }
  };
}
