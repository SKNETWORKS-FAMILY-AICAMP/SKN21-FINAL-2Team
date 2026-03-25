"use client";

import { AnimatePresence, motion } from "framer-motion";
import { useRouter } from "next/navigation";
import {
  Ticket,
  TrainFront,
  Hotel,
  UtensilsCrossed,
  CheckCircle2,
} from "lucide-react";

import { Sidebar } from "@/components/navigation/Sidebar";
import { JourneyDetailModal } from "./components/JourneyDetailModal";
import { ReservationDetailModal } from "./components/ReservationDetailModal";
import { RecommendedConversationCard } from "./components/RecommendedConversationCard";
import { TravelPreferenceSection } from "./components/TravelPreferenceSection";
import { UserSettingsModal } from "./components/UserSettingsModal";
import { DeleteReservationConfirmModal, PreferenceSavedPopup } from "./components/MyPageModals";

import { useTranslation } from "@/i18n/useTranslation";
import { resolveImageUrl } from "@/lib/imageUrl";
import { updateReservation } from "@/services/api";
import { useMyPage, mapReservationRecordToItem } from "./components/useMyPage";
import type { ReservationItem } from "./types";

function ReservationLogo({ category }: { category: ReservationItem["category"] }) {
  const common = { size: 14 };
  switch (category) {
    case "transportation":
      return <TrainFront {...common} />;
    case "hotel":
      return <Hotel {...common} />;
    case "restaurant":
      return <UtensilsCrossed {...common} />;
    case "activity":
      return <Ticket {...common} />;
    default:
      return <Ticket {...common} />;
  }
}

export function MyPagePage() {
  const router = useRouter();
  const { t } = useTranslation();

  // 1. 상태 및 데이터 페칭 전면 캡슐화 훅
  const { state, actions } = useMyPage();
  const {
    userProfile,
    userInsight,
    draftInsight,
    todayRecommendation,
    trips,
    reservations,
    bookmarkedRoomCount,
    isEditingPreferences,
    isSavingPreferences,
    draftExtraPreferences,
    showPreferenceSavedPopup,
    settingsOpen,
    activeTrip,
    activeReservation,
    reservationToDelete,
  } = state;

  const {
    setUserProfile,
    setDraftInsight,
    setReservations,
    setShowPreferenceSavedPopup,
    setSettingsOpen,
    setActiveTrip,
    setActiveReservation,
    handleAddReservation,
    handleDeleteReservation,
    requestDeleteReservation,
    cancelDeleteReservation,
    confirmDeleteReservation,
    handleOpenSettings,
    toggleDraftExtraPreference,
    handleTogglePreferenceEdit,
    handleCancelPreferenceEdit,
  } = actions;

  return (
    <div className="flex w-full min-h-screen bg-gray-100 p-3 sm:p-4 gap-4 lg:h-screen lg:flex-row flex-col lg:overflow-hidden">
      <div className="flex-none lg:h-full max-w-full">
        <div className="h-full">
          <Sidebar />
        </div>
      </div>
      
      <main className="flex-1 min-w-0 bg-white rounded-lg lg:h-full lg:overflow-y-auto text-gray-900 flex flex-col">
        <div className="p-4 sm:p-6 flex flex-col flex-1 min-h-0">
          <header className="mb-6">
            <h1 className="page-title text-gray-900 mb-2">{t("mypage.title")}</h1>
            <p className="page-subtitle">{t("mypage.subtitle")}</p>
            <div className="mt-3 flex flex-wrap gap-2">
              <span className="px-2.5 py-1 rounded-full bg-gray-100 text-[11px] font-semibold text-gray-700">
                {t("mypage.rooms")} {trips.length}
              </span>
              <span className="px-2.5 py-1 rounded-full bg-gray-100 text-[11px] font-semibold text-gray-700">
                {t("mypage.savedRooms")} {bookmarkedRoomCount}
              </span>
              <span className="px-2.5 py-1 rounded-full bg-gray-100 text-[11px] font-semibold text-gray-700">
                {t("mypage.reservations")} {reservations.length}
              </span>
            </div>
          </header>

          <div className="grid grid-cols-1 xl:grid-cols-3 gap-6 pb-8 flex-1">
            <div className="xl:col-span-2 flex flex-col">
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="p-4 sm:p-6 sm:pb-4 rounded-3xl border border-gray-200 bg-white shadow-sm flex flex-col flex-1"
              >
                <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-3">
                  <div className="flex items-center gap-4 min-w-0">
                    <div className="w-14 h-14 sm:w-16 sm:h-16 xl:w-20 xl:h-20 rounded-full overflow-hidden border-4 border-gray-50 shadow-sm flex items-center justify-center bg-gray-200 text-gray-400 flex-none">
                      {userProfile.profile_picture ? (
                        <img
                          src={resolveImageUrl(userProfile.profile_picture)}
                          alt="Profile"
                          className="w-full h-full object-cover grayscale-[20%]"
                        />
                      ) : (
                        <span className="font-medium text-[10px]">No Image</span>
                      )}
                    </div>
                    <div className="min-w-0">
                      <h2 className="text-lg sm:text-xl font-bold text-gray-900 truncate">
                        {userProfile.nickname}
                      </h2>
                      <div className="flex items-center mt-0.5">
                        <span className="text-xs text-gray-500 truncate">{userProfile.bio}</span>
                      </div>
                    </div>
                  </div>

                  <button
                    type="button"
                    onClick={handleOpenSettings}
                    className="h-10 px-4 rounded-full border border-gray-300 bg-white text-xs font-bold text-gray-700 hover:bg-gray-50 transition-all"
                  >
                    {t("mypage.settings")}
                  </button>
                </div>

                <hr className="border-gray-100 my-3" />

                <TravelPreferenceSection
                  userInsight={userInsight}
                  draftInsight={draftInsight}
                  setDraftInsight={setDraftInsight}
                  userPreferences={userProfile.preferences}
                  draftExtraPreferences={draftExtraPreferences}
                  toggleDraftExtraPreference={toggleDraftExtraPreference}
                  isEditingPreferences={isEditingPreferences}
                  isSavingPreferences={isSavingPreferences}
                  handleTogglePreferenceEdit={handleTogglePreferenceEdit}
                  handleCancelPreferenceEdit={handleCancelPreferenceEdit}
                />
              </motion.div>
            </div>

            <div className="flex flex-col gap-6 h-full">
              <RecommendedConversationCard todayRecommendation={todayRecommendation} />

              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.35 }}
                className="p-6 sm:p-8 rounded-3xl border border-gray-200 bg-white flex flex-col flex-1 shadow-sm overflow-hidden min-h-0"
              >
                <div className="flex items-center justify-between gap-3 mb-6">
                  <h3 className="text-xl font-semibold text-gray-900 flex items-center gap-2">
                    {t("mypage.tplResDetails")}
                  </h3>
                  <button
                    type="button"
                    onClick={handleAddReservation}
                    className="text-xl font-medium text-gray-700 hover:opacity-70 leading-none"
                  >
                    +
                  </button>
                </div>

                <div className="space-y-3 flex-1 overflow-y-auto pr-1">
                  {reservations.length ? (
                    reservations.map((res) => (
                      <div
                        key={res.id}
                        className="group p-4 rounded-2xl border border-gray-100 hover:border-gray-300 hover:bg-gray-50 transition-all flex items-center justify-between gap-3"
                      >
                        <button
                          type="button"
                          onClick={() => setActiveReservation(res)}
                          className="flex-1 min-w-0 cursor-pointer text-left"
                        >
                          <div className="flex items-center gap-3">
                            <div className="w-10 h-10 rounded-xl bg-gray-100 flex items-center justify-center text-gray-500 group-hover:bg-white group-hover:text-black transition-colors border border-gray-200">
                              <ReservationLogo category={res.category} />
                            </div>
                            <div className="min-w-0">
                              <h4 className="text-sm font-bold leading-tight text-gray-900 truncate">{res.title}</h4>
                              <div className="flex items-center gap-1.5 mt-1 min-w-0">
                                <span className="text-[10px] text-gray-500 font-medium uppercase truncate">{res.subtitle}</span>
                                <span className="text-[10px] text-gray-300">•</span>
                                <span className="text-[10px] text-gray-400 font-medium truncate">{res.dateLabel}</span>
                              </div>
                            </div>
                          </div>
                        </button>
                        <div className="flex items-center gap-2 flex-none">
                          <CheckCircle2 size={14} className="text-black" />
                          <button
                            type="button"
                            onClick={() => requestDeleteReservation(res)}
                            className="text-[10px] font-semibold text-gray-700 uppercase tracking-[0.12em] hover:opacity-70"
                          >
                            {t("common.delete")}
                          </button>
                        </div>
                      </div>
                    ))
                  ) : (
                    <div className="h-full min-h-[120px] flex items-center justify-center text-gray-400 text-sm">
                      {t("mypage.emptyReservations")}
                    </div>
                  )}
                </div>
              </motion.div>
            </div>
          </div>
        </div>
      </main>

      {/* 모달 영역들 */}
      <JourneyDetailModal
        open={!!activeTrip}
        trip={activeTrip}
        onClose={() => setActiveTrip(null)}
      />

      <ReservationDetailModal
        open={!!activeReservation}
        reservation={activeReservation}
        photoUrl={activeReservation?.reservationImageUrl}
        onSavePhoto={async (url) => {
          if (!activeReservation) return;
          try {
            const updated = await updateReservation(activeReservation.reservationId, {
              image_path: url,
            });
            const mapped = mapReservationRecordToItem(updated);
            setReservations((prev) => prev.map((item) => (
              item.reservationId === mapped.reservationId ? mapped : item
            )));
          } catch (e) { console.error("Failed to update photo", e); }
        }}
        onSaveTitle={async (newTitle) => {
          if (!activeReservation) return;
          try {
            const updated = await updateReservation(activeReservation.reservationId, {
              name: newTitle,
            });
            const mapped = mapReservationRecordToItem(updated);
            setReservations((prev) => prev.map((item) => (
              item.reservationId === mapped.reservationId ? mapped : item
            )));
          } catch (error) { console.error("Failed to update title", error); }
        }}
        onSaveCategory={async (newCategory) => {
          if (!activeReservation) return;
          try {
            const updated = await updateReservation(activeReservation.reservationId, {
              category: newCategory,
            });
            const mapped = mapReservationRecordToItem(updated);
            setReservations((prev) => prev.map((item) => (
              item.reservationId === mapped.reservationId ? mapped : item
            )));
          } catch (error) { console.error("Failed to update category", error); }
        }}
        onSaveDetails={async (newDetails) => {
          if (!activeReservation) return;
          try {
            const updated = await updateReservation(activeReservation.reservationId, {
              details: newDetails,
            });
            const mapped = mapReservationRecordToItem(updated);
            setReservations((prev) => prev.map((item) => (
              item.reservationId === mapped.reservationId ? mapped : item
            )));
          } catch (error) { console.error("Failed to update details", error); }
        }}
        onClose={(wasSaved, isNewDraft) => {
          if (!wasSaved && isNewDraft && activeReservation) {
            void handleDeleteReservation(activeReservation.id);
          } else {
            setActiveReservation(null);
          }
        }}
      />

      {/* 분리된 서브 모달들 */}
      <DeleteReservationConfirmModal
        open={!!reservationToDelete}
        onCancel={cancelDeleteReservation}
        onConfirm={confirmDeleteReservation}
      />

      <PreferenceSavedPopup
        open={showPreferenceSavedPopup}
        onClose={() => setShowPreferenceSavedPopup(false)}
      />

      <UserSettingsModal
        open={settingsOpen}
        userProfile={userProfile}
        onClose={() => setSettingsOpen(false)}
        onProfileUpdated={(updatedFields) => {
          setUserProfile(prev => ({ ...prev, ...updatedFields }));
          window.dispatchEvent(new Event("triver:profile-updated"));
        }}
      />
    </div>
  );
}
