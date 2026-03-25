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
  "시간": "mypage.tplTime",
  "장소": "mypage.tplPlace",
  "식당이름": "mypage.tplRestaurantName",
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
  { value: "transportation", label: "교통" },
  { value: "hotel", label: "호텔" },
  { value: "activity", label: "공연/활동" },
  { value: "restaurant", label: "식당" },
  { value: "etc", label: "기타" },
] as const;

export const CATEGORY_MAP: Record<string, string> = {
  transportation: "교통",
  hotel: "호텔",
  restaurant: "식당",
  activity: "공연/활동",
  etc: "기타",
};

export const TEMPLATE_MAP: Record<string, string[]> = {
  transportation: ['날짜', '출발지', '출발시간', '도착지', '도착시간', '승차홈', '차량 번호', '좌석 번호'],
  hotel: ['숙소 이름', '체크인 날짜', '체크인 시간', '체크아웃 날짜', '체크아웃 시간', '방 호실'],
  activity: ['날짜', '이름', '시간', '장소', '좌석 번호'],
  restaurant: ['날짜', '식당이름', '예약시간', '예약자명', '예약 인원'],
  etc: ['예약내역', '시간', '예약자명']
};

export const PAIRED_FIELDS = [
  ["출발지", "도착지"],
  ["출발시간", "도착시간"],
  ["출발 시간", "도착 시간"],
  ["출발 날짜", "도착 날짜"],
  ["체크인 날짜", "체크아웃 날짜"],
  ["체크인 시간", "체크아웃 시간"],
  ["예약 날짜", "예약 시간"],
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
      {/* 예약 제목 편집 */}
      <div>
        <label className="block text-[10px] font-bold uppercase tracking-widest text-[#8b98a5] mb-1.5 pl-1">
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
              className="w-full h-12 rounded-2xl border-none bg-black/[0.03] px-4 text-sm font-semibold text-gray-800 transition-all duration-300 focus:outline-none focus:bg-black/[0.05] focus:ring-[1px] focus:ring-black/[0.08] shadow-[inset_0_2px_4px_rgba(0,0,0,0.02)]"
              placeholder={t("mypage.reservationTitlePlaceholder")}
            />
          ) : (
            <div
              onClick={() => setEditingTitle(true)}
              className="w-full min-h-[48px] px-4 py-3 flex items-center bg-black/[0.02] border border-transparent shadow-[inset_0_2px_4px_rgba(0,0,0,0.01)] rounded-2xl cursor-pointer hover:bg-black/[0.04] transition-colors"
            >
              <p className="text-sm font-semibold text-gray-900">
                {draftTitle || t("mypage.clickToInputTitle")}
              </p>
            </div>
          )
        ) : (
          <div className="w-full min-h-[48px] px-4 py-3 flex items-center border border-transparent rounded-2xl bg-black/[0.01]">
            <p className="text-sm font-extrabold text-gray-900">{draftTitle}</p>
          </div>
        )}
      </div>

      {/* 카테고리 선택 / 표시 */}
      <div>
        <label className="block text-[10px] font-bold uppercase tracking-widest text-[#8b98a5] mb-1.5 pl-1">
          {t("mypage.category")}
        </label>
        {isEditMode ? (
          <div className="flex flex-nowrap gap-2 overflow-x-auto pb-1">
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
                className={`whitespace-nowrap h-9 px-4 rounded-xl text-xs font-semibold transition-colors duration-300 ${draftCategory === opt.value
                    ? "bg-black text-white shadow-md border-transparent"
                    : "bg-white/80 text-gray-600 border border-white hover:bg-white shadow-sm"
                  }`}
              >
                {CATEGORY_I18N_MAP[opt.value] ? t(CATEGORY_I18N_MAP[opt.value]) : opt.label}
              </button>
            ))}
          </div>
        ) : (
          <div className="w-full h-11 px-4 flex items-center bg-black/[0.01] border border-transparent rounded-2xl">
            <p className="text-[13px] font-semibold text-gray-700">
              {CATEGORY_I18N_MAP[draftCategory] ? t(CATEGORY_I18N_MAP[draftCategory]) : CATEGORY_MAP[draftCategory]}
            </p>
          </div>
        )}
      </div>

      {/* 다이나믹 JSON 상세 정보 폼 (쌍 배열 렌더링 적용) */}
      {Object.keys(draftDetails).length > 0 && (
        <div className="mt-2">
          <div className="flex flex-col gap-y-6">
            {(() => {
              const keys = Object.keys(draftDetails);
              const rendered = new Set<string>();
              const groups: React.ReactNode[] = [];

              const renderInputGroup = (key: string, value: string) => (
                <div key={key} className="relative group w-full">
                  <label className="block text-[10px] font-bold text-[#8b98a5] uppercase tracking-widest px-1 mb-1.5">
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
                        className="w-full h-11 rounded-2xl border-none bg-black/[0.03] pl-4 pr-10 text-[13px] font-medium transition-colors duration-300 focus:outline-none focus:bg-black/[0.05] focus:ring-[1px] focus:ring-black/[0.08] shadow-[inset_0_2px_4px_rgba(0,0,0,0.02)]"
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
                    <div className="w-full px-1 min-h-[32px] flex items-center text-[13px] font-semibold text-gray-800">
                      {value || <span className="text-gray-300 font-normal">{t("mypage.noInput")}</span>}
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
                  className="w-full h-12 border border-dashed border-gray-300 rounded-2xl text-xs font-bold text-gray-500 hover:bg-gray-50 hover:border-gray-400 hover:text-black transition-all mt-2 flex items-center justify-center gap-1.5"
                >
                  <span className="text-lg leading-none mb-0.5">+</span> {t("mypage.addNewItem")}
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
