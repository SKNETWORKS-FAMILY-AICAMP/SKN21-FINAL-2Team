import React from "react";
import { useTranslation } from "react-i18next";
import {
  SURVEY_IMAGE_MAP,
  SNAPSHOT_OPTIONS,
  EXTRA_PREFER_OPTIONS,
  SURVEY_LABEL_KEY_MAP,
  EXTRA_PREFER_LABEL_KEY_MAP,
} from "../constants";

export interface UserInsight {
  planPrefer: string;
  vibePrefer: string;
  placesPrefer: string;
}

interface TravelPreferenceSectionProps {
  userInsight: UserInsight;
  draftInsight: UserInsight;
  setDraftInsight: React.Dispatch<React.SetStateAction<UserInsight>>;
  
  userPreferences: string[];
  draftExtraPreferences: string[];
  toggleDraftExtraPreference: (value: string) => void;
  
  isEditingPreferences: boolean;
  isSavingPreferences: boolean;
  handleTogglePreferenceEdit: () => void;
  handleCancelPreferenceEdit: () => void;
}

export function TravelPreferenceSection({
  userInsight,
  draftInsight,
  setDraftInsight,
  userPreferences,
  draftExtraPreferences,
  toggleDraftExtraPreference,
  isEditingPreferences,
  isSavingPreferences,
  handleTogglePreferenceEdit,
  handleCancelPreferenceEdit,
}: TravelPreferenceSectionProps) {
  const { t } = useTranslation();

  return (
    <div className="space-y-8">
      <div>
        <div className="flex items-center justify-between gap-3 mb-1">
          <h3 className="text-xl font-semibold text-gray-900 tracking-tight font-pretendard">{t("mypage.travelPreferences")}</h3>
          <div className="flex items-center gap-2">
            {isEditingPreferences && (
              <button
                type="button"
                onClick={handleCancelPreferenceEdit}
                className="h-10 px-4 rounded-full border border-gray-300 bg-white text-xs font-bold text-gray-700 hover:bg-gray-50 transition-all"
              >
                {t("common.cancel")}
              </button>
            )}
            <button
              type="button"
              onClick={handleTogglePreferenceEdit}
              disabled={isSavingPreferences}
              className={`h-10 px-4 rounded-full border text-xs font-bold transition-all disabled:opacity-60 ${isEditingPreferences
                ? "border-gray-900 bg-black text-white hover:opacity-90"
                : "border-gray-300 bg-white text-gray-700 hover:bg-gray-50"
                }`}
            >
              {isEditingPreferences ? (isSavingPreferences ? t("common.saving") : t("mypage.done")) : t("mypage.edit")}
            </button>
          </div>
        </div>
        <p className="text-sm text-gray-500">{t("mypage.travelPreferencesDesc")}</p>
      </div>

      <div>
        <h4 className="text-xs font-semibold text-gray-500 tracking-wider mb-4 font-pretendard">{t("mypage.travelerSnapshot")}</h4>
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
          {[
            { key: "plan" as const, label: t("mypage.surveyPlan"), value: isEditingPreferences ? draftInsight.planPrefer : userInsight.planPrefer },
            { key: "vibe" as const, label: t("mypage.surveyVibe"), value: isEditingPreferences ? draftInsight.vibePrefer : userInsight.vibePrefer },
            { key: "places" as const, label: t("mypage.surveyPlaces"), value: isEditingPreferences ? draftInsight.placesPrefer : userInsight.placesPrefer },
          ].map((item) => {
            const imageSrc = SURVEY_IMAGE_MAP[item.value] ?? "/image/noplan.png";
            return (
              <div key={item.key} className="space-y-2">
                <div className="relative aspect-[16/10] rounded-2xl overflow-hidden border border-gray-200 shadow-sm">
                  <img src={imageSrc} alt={item.value || item.label} className="w-full h-full object-cover" />
                  <div className="absolute inset-0 bg-gradient-to-t from-black/75 via-black/30 to-transparent" />
                  <div className="absolute inset-x-0 bottom-0 p-4">
                    <p className="text-[10px] text-white/80 font-semibold uppercase tracking-[0.12em]">{item.label}</p>
                    <p className="text-sm text-white font-semibold mt-1">{item.value ? (SURVEY_LABEL_KEY_MAP[item.value] ? t(SURVEY_LABEL_KEY_MAP[item.value]) : item.value) : "-"}</p>
                  </div>
                </div>
                {isEditingPreferences && (
                  <div className={`grid gap-1.5 ${SNAPSHOT_OPTIONS[item.key].length === 2 ? "grid-cols-2" : "grid-cols-2 sm:grid-cols-3"}`}>
                    {SNAPSHOT_OPTIONS[item.key].map((opt) => (
                      <button
                        key={`${item.key}-${opt}`}
                        type="button"
                        onClick={() => {
                          setDraftInsight((prev) => ({
                            ...prev,
                            ...(item.key === "plan" ? { planPrefer: opt } : {}),
                            ...(item.key === "vibe" ? { vibePrefer: opt } : {}),
                            ...(item.key === "places" ? { placesPrefer: opt } : {}),
                          }));
                        }}
                        className={`px-2 py-1.5 rounded-full text-[11px] font-medium border transition-colors whitespace-normal break-words text-center ${(item.key === "plan" && draftInsight.planPrefer === opt)
                          || (item.key === "vibe" && draftInsight.vibePrefer === opt)
                          || (item.key === "places" && draftInsight.placesPrefer === opt)
                          ? "bg-black text-white border-black"
                          : "bg-white text-gray-700 border-gray-200 hover:border-gray-400"
                          }`}
                      >
                        {SURVEY_LABEL_KEY_MAP[opt] ? t(SURVEY_LABEL_KEY_MAP[opt]) : opt}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      <div className="mt-6">
        <h4 className="text-xs font-semibold text-gray-500 tracking-wider mb-4 font-pretendard">{t("mypage.additionalPreference")}</h4>
        <div className="flex flex-wrap gap-2.5">
          {(isEditingPreferences
            ? EXTRA_PREFER_OPTIONS
            : (userPreferences.length ? userPreferences : [t("mypage.noPreference")])).map((pref) => (
              <button
                key={pref}
                type="button"
                onClick={() => isEditingPreferences && toggleDraftExtraPreference(pref)}
                disabled={!isEditingPreferences && pref === "No preference selected"}
                className={`px-4 py-2 rounded-full text-sm font-medium border shadow-sm transition-colors ${isEditingPreferences
                  ? draftExtraPreferences.includes(pref)
                    ? "bg-black text-white border-black"
                    : "bg-white text-gray-700 border-gray-200 hover:border-gray-400"
                  : "bg-gray-900 text-white border-gray-900"
                  }`}
              >
                {EXTRA_PREFER_LABEL_KEY_MAP[pref] ? t(EXTRA_PREFER_LABEL_KEY_MAP[pref]) : pref}
              </button>
            ))}
        </div>
        {isEditingPreferences && (
          <p className="mt-2 text-[11px] text-gray-500">{t("mypage.upTo3")}</p>
        )}
      </div>
    </div>
  );
}
