import React from "react";
import { X } from "lucide-react";
import { useTranslation } from "@/i18n/useTranslation";

export const CATEGORY_I18N_MAP: Record<string, string> = {
  transportation: "mypage.catTransport",
  hotel: "mypage.catHotel",
  activity: "mypage.catActivity",
  restaurant: "mypage.catRestaurant",
  etc: "mypage.catEtc",
};

export const FIELD_I18N_MAP: Record<string, string> = {
  "날짜": "mypage.tplDate",
  "출발지": "mypage.tplDepLoc",
  "도착지": "mypage.tplArrLoc",
  "출발시간": "mypage.tplDepTime",
  "도착시간": "mypage.tplArrTime",
  "출발 시간": "mypage.tplDepTimeSpace",
  "도착 시간": "mypage.tplArrTimeSpace",
  "출발 날짜": "mypage.tplDepDate",
  "도착 날짜": "mypage.tplArrDate",
  "승차홈": "mypage.tplSeatHome",
  "차량 번호": "mypage.tplCarNum",
  "좌석 번호": "mypage.tplSeatNum",
  "숙소 이름": "mypage.tplHotelName",
  "체크인 날짜": "mypage.tplCheckInDate",
  "체크인 시간": "mypage.tplCheckInTime",
  "체크아웃 날짜": "mypage.tplCheckOutDate",
  "체크아웃 시간": "mypage.tplCheckOutTime",
  "방 호실": "mypage.tplRoomNum",
  "이름": "mypage.tplName",
  "공연/활동명": "mypage.tplActivityName",
  "시간": "mypage.tplTime",
  "장소": "mypage.tplPlace",
  "식당이름": "mypage.tplRestaurantName",
  "매장명": "mypage.tplShopName",
  "예약시간": "mypage.tplResTime",
  "예약 시간": "mypage.tplResTimeSpace",
  "예약 날짜": "mypage.tplResDateSpace",
  "예약자명": "mypage.tplResName",
  "예약 인원": "mypage.tplResCount",
  "예약내역": "mypage.tplResDetails",
  "결제 수단": "mypage.tplPayMethod",
  "결제 금액": "mypage.tplPayAmount",
};

export const CATEGORY_OPTIONS = [
  { value: "transportation", i18nKey: "mypage.catTransport" },
  { value: "hotel", i18nKey: "mypage.catHotel" },
  { value: "activity", i18nKey: "mypage.catActivity" },
  { value: "restaurant", i18nKey: "mypage.catRestaurant" },
  { value: "etc", i18nKey: "mypage.catEtc" },
] as const;

export const TEMPLATE_MAP: Record<string, string[]> = {
  transportation: ['날짜', '출발지', '출발시간', '도착지', '도착시간', '승차홈', '차량 번호', '좌석 번호'],
  hotel: ['숙소 이름', '체크인 날짜', '체크인 시간', '체크아웃 날짜', '체크아웃 시간', '방 호실'],
  activity: ['공연/활동명', '날짜', '시간', '장소', '좌석 번호'],
  restaurant: ['매장명', '날짜', '예약시간', '예약자명', '예약 인원'],
  etc: ['예약내역', '시간', '예약자명']
};

export const PAIRED_FIELDS = [
  ["출발지", "도착지"],
  ["출발시간", "도착시간"],
  ["출발 시간", "도착 시간"],
  ["출발 날짜", "도착 날짜"],
  ["체크인 날짜", "체크아웃 날짜"],
  ["체크인 시간", "체크아웃 시간"],
  ["날짜", "시간"],
  ["날짜", "예약시간"],
  ["예약 날짜", "예약 시간"],
  ["예약자명", "예약 인원"],
  ["장소", "좌석 번호"],
  ["결제 금액", "결제 수단"]
];

interface ReservationFormSectionProps {
  isEditMode: boolean;
  draftTitle: string;
  setDraftTitle: (t: string) => void;
  editingTitle: boolean;
  setEditingTitle: (v: boolean) => void;
  draftCategory: string;
  setDraftCategory: (c: string) => void;
  draftDetails: Record<string, string>;
  setDraftDetails: React.Dispatch<React.SetStateAction<Record<string, string>>>;
  setPromptOpen: (v: boolean) => void;
  setPromptValue: (v: string) => void;
}

export function ReservationFormSection({
  isEditMode,
  draftTitle,
  setDraftTitle,
  editingTitle,
  setEditingTitle,
  draftCategory,
  setDraftCategory,
  draftDetails,
  setDraftDetails,
  setPromptOpen,
  setPromptValue,
}: ReservationFormSectionProps) {
  const { t } = useTranslation();

  return (
    <div className="w-full md:w-7/12 space-y-5 flex flex-col">
      {/* 카테고리 선택 / 표시 */}
      <div className="flex flex-col">
        <label className="block text-[11px] font-bold text-gray-400 mb-1.5 pl-1">
          {t("mypage.category")}
        </label>
        {isEditMode ? (
          <div className="flex flex-wrap gap-2">
            {CATEGORY_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                type="button"
                onClick={() => {
                  setDraftCategory(opt.value);
                  const newKeys = TEMPLATE_MAP[opt.value] || TEMPLATE_MAP["etc"];
                  const nextDetails: Record<string, string> = {};
                  newKeys.forEach((k) => {
                    nextDetails[k] = draftDetails[k] || "";
                  });
                  setDraftDetails(nextDetails);
                }}
                className={`whitespace-nowrap h-9 px-4 rounded-xl text-[11px] font-semibold transition-all duration-300 ${draftCategory === opt.value
                    ? "bg-black text-white shadow-md border-transparent"
                    : "bg-white text-gray-500 border border-black/[0.05] hover:bg-gray-50 shadow-sm"
                  }`}
              >
                {t(opt.i18nKey)}
              </button>
            ))}
          </div>
        ) : (
          <div className="w-full h-10 px-1 flex items-center border border-transparent rounded-2xl">
            <p className="text-[14px] font-bold text-black uppercase">
              {CATEGORY_I18N_MAP[draftCategory] ? t(CATEGORY_I18N_MAP[draftCategory]) : draftCategory}
            </p>
          </div>
        )}
      </div>

      {/* 예약 제목 편집 */}
      <div className="flex flex-col">
        <label className="block text-[11px] font-bold text-gray-400 mb-1.5 pl-1">
          {t("mypage.reservationName")}
        </label>
        {isEditMode ? (
          editingTitle ? (
              <input
                type="text"
                value={draftTitle}
                onChange={(e) => setDraftTitle(e.target.value)}
                onBlur={() => setEditingTitle(false)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") setEditingTitle(false);
                }}
                autoFocus
                placeholder={t("mypage.clickToInputTitle")}
                className="w-full h-11 rounded-2xl border border-gray-100 bg-gray-50 px-4 text-[13px] font-semibold text-gray-900 transition-all focus:outline-none focus:border-gray-300 focus:bg-white shadow-sm"
                placeholder={t("mypage.reservationTitlePlaceholder")}
              />
          ) : (
            <div
              onClick={() => setEditingTitle(true)}
              className="w-full h-11 px-4 flex items-center bg-black/[0.02] border border-transparent shadow-[inset_0_2px_4px_rgba(0,0,0,0.01)] rounded-2xl cursor-pointer hover:bg-black/[0.04] transition-colors"
            >
              <p className="text-[13px] font-semibold text-gray-900 truncate">
                {draftTitle || t("mypage.clickToInputTitle")}
              </p>
            </div>
          )
        ) : (
          <div className="w-full h-11 px-4 flex items-center bg-gray-50 border border-gray-100 rounded-2xl shadow-sm">
            <p className="text-[14px] font-bold text-gray-900 truncate">{draftTitle}</p>
          </div>
        )}
      </div>

      {/* 다이나믹 JSON 상세 정보 폼 (2열 페어 레이아웃 복구) */}
      {Object.keys(draftDetails).length > 0 && (
        <div className="mt-2">
          <div className="flex flex-col gap-y-6">
            {(() => {
              const keys = Object.keys(draftDetails);
              const rendered = new Set<string>();
              const groups: React.ReactNode[] = [];

              const renderInputGroup = (key: string, value: string) => (
                <div key={key} className="relative group w-full">
                  <label className="block text-[11px] font-bold text-gray-400 px-1 mb-1.5">
                    {FIELD_I18N_MAP[key] ? t(FIELD_I18N_MAP[key]) : key}
                  </label>
                  {isEditMode ? (
                    <div className="relative isolate">
                      <input
                        type="text"
                        value={value || ""}
                        onChange={(e) =>
                          setDraftDetails((prev) => ({ ...prev, [key]: e.target.value }))
                        }
                        className="w-full h-11 rounded-2xl border border-gray-100 bg-gray-50 pl-4 pr-10 text-[13px] font-medium text-gray-900 transition-all focus:outline-none focus:border-gray-300 focus:bg-white shadow-sm"
                        placeholder={t("mypage.inputContent")}
                      />
                      <button
                        type="button"
                        onClick={() => {
                          const newDetails = { ...draftDetails };
                          delete newDetails[key];
                          setDraftDetails(newDetails);
                        }}
                        className="absolute right-1.5 top-1/2 -translate-y-1/2 flex h-8 w-8 items-center justify-center rounded-full text-gray-300 hover:bg-red-50 hover:text-red-500 transition-colors"
                        title={t("mypage.deleteItem")}
                      >
                        <X size={14} />
                      </button>
                    </div>
                  ) : (
                    <div className="w-full px-4 h-11 flex items-center bg-gray-50 border border-gray-100 rounded-2xl shadow-sm text-[13px] font-semibold text-gray-800">
                      {value || <span className="text-gray-400 font-normal">{t("mypage.noInput")}</span>}
                    </div>
                  )}
                </div>
              );

              keys.forEach((key) => {
                if (rendered.has(key)) return;

                const pairDef = PAIRED_FIELDS.find((p) => p[0] === key || p[1] === key);
                if (pairDef) {
                  const partnerKey = pairDef[0] === key ? pairDef[1] : pairDef[0];
                  if (keys.includes(partnerKey) && !rendered.has(partnerKey)) {
                    const leftKey = pairDef[0];
                    const rightKey = pairDef[1];
                    groups.push(
                      <div key={`${leftKey}-${rightKey}`} className="grid grid-cols-2 gap-x-4 w-full">
                        {renderInputGroup(leftKey, draftDetails[leftKey])}
                        {renderInputGroup(rightKey, draftDetails[rightKey])}
                      </div>
                    );
                    rendered.add(leftKey);
                    rendered.add(rightKey);
                    return;
                  }
                }

                groups.push(
                  <div key={key} className="w-full">
                    {renderInputGroup(key, draftDetails[key])}
                  </div>
                );
                rendered.add(key);
              });

              return groups;
            })()}

            {isEditMode && (
              <div className="pt-2 w-full">
                <button
                  type="button"
                  onClick={() => {
                    setPromptValue("");
                    setPromptOpen(true);
                  }}
                  className="w-full h-12 border border-dashed border-gray-300 rounded-2xl text-[11px] font-bold text-gray-400 hover:bg-gray-50 hover:border-gray-400 hover:text-black transition-all flex items-center justify-center gap-1.5"
                >
                  <span className="text-base leading-none mb-0.5">+</span> {t("mypage.addNewItem")}
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
