import React, { useState, useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";
import { Settings, UserX } from "lucide-react";
import { SimpleModal } from "./SimpleModal";
import { LanguageSwitcher } from "@/components/common/LanguageSwitcher";
import { COUNTRIES, type Country } from "@/config/countries";
import {
  updateCurrentUser,
  resetCurrentUserProfilePictureToGoogle,
  uploadImageDataUrl,
  deactivateCurrentUser,
  logoutApi,
} from "@/services/api";
import { clearAuth } from "@/services/errorHandler";

export interface UserProfileSubset {
  nickname: string;
  bio: string;
  countryCode: string;
  profile_picture: string;
  birthday: string;
  preferences?: string[];
}

interface UserSettingsModalProps {
  open: boolean;
  userProfile: UserProfileSubset;
  onClose: () => void;
  onProfileUpdated: (updatedProfile: Partial<UserProfileSubset>) => void;
}

export function UserSettingsModal({
  open,
  userProfile,
  onClose,
  onProfileUpdated,
}: UserSettingsModalProps) {
  const { t } = useTranslation();
  const countryOptions: Country[] = COUNTRIES;

  const [settingsModalView, setSettingsModalView] = useState<"settings" | "deactivate">("settings");
  const [settingsDraft, setSettingsDraft] = useState({
    nickname: "",
    countryCode: "",
    profilePicture: "",
    birthday: "",
  });
  const [settingsSaving, setSettingsSaving] = useState(false);
  const [settingsResettingPhoto, setSettingsResettingPhoto] = useState(false);
  const [showSettingsSavedPopup, setShowSettingsSavedPopup] = useState(false);

  const [deactivateGoogleConfirmed, setDeactivateGoogleConfirmed] = useState(false);
  const [deactivateAgreementConfirmed, setDeactivateAgreementConfirmed] = useState(false);
  const [deactivateSubmitAttempted, setDeactivateSubmitAttempted] = useState(false);
  const [deactivateSubmitting, setDeactivateSubmitting] = useState(false);
  const [deactivateError, setDeactivateError] = useState("");
  const [deactivateConfirmOpen, setDeactivateConfirmOpen] = useState(false);

  const settingsPhotoInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (open) {
      setSettingsModalView("settings");
      setSettingsDraft({
        nickname: userProfile.nickname || "",
        countryCode: userProfile.countryCode || "",
        profilePicture: userProfile.profile_picture || "",
        birthday: userProfile.birthday || "",
      });
      setDeactivateGoogleConfirmed(false);
      setDeactivateAgreementConfirmed(false);
      setDeactivateSubmitAttempted(false);
      setDeactivateSubmitting(false);
      setDeactivateError("");
      setDeactivateConfirmOpen(false);
      setShowSettingsSavedPopup(false);
    }
  }, [open, userProfile]);

  const handleOpenDeactivateAccount = () => {
    setSettingsModalView("deactivate");
    setDeactivateGoogleConfirmed(false);
    setDeactivateAgreementConfirmed(false);
    setDeactivateSubmitAttempted(false);
    setDeactivateSubmitting(false);
    setDeactivateError("");
    setDeactivateConfirmOpen(false);
  };

  const handleCancelDeactivateAccount = () => {
    setSettingsModalView("settings");
    setDeactivateGoogleConfirmed(false);
    setDeactivateAgreementConfirmed(false);
    setDeactivateSubmitAttempted(false);
    setDeactivateSubmitting(false);
    setDeactivateError("");
    setDeactivateConfirmOpen(false);
  };

  const handleRequestDeactivateAccount = () => {
    setDeactivateSubmitAttempted(true);
    setDeactivateError("");
    if (!deactivateGoogleConfirmed || !deactivateAgreementConfirmed) return;
    setDeactivateConfirmOpen(true);
  };

  const handleCancelDeactivateConfirm = () => {
    setDeactivateConfirmOpen(false);
  };

  const handleConfirmDeactivateAccount = async () => {
    setDeactivateSubmitting(true);
    setDeactivateError("");
    try {
      await deactivateCurrentUser();
      await logoutApi();
      clearAuth();
      onClose();
      window.location.href = "/";
    } catch (error) {
      console.error("Failed to deactivate account", error);
      setDeactivateError(t("mypage.deactivateFailed"));
      setDeactivateConfirmOpen(false);
    } finally {
      setDeactivateSubmitting(false);
    }
  };

  const handleSaveSettingsPopup = async () => {
    setSettingsSaving(true);
    try {
      const resolvedProfilePicture = settingsDraft.profilePicture?.startsWith("data:image/")
        ? await uploadImageDataUrl(settingsDraft.profilePicture, "profile")
        : settingsDraft.profilePicture;
        
      await updateCurrentUser({
        nickname: settingsDraft.nickname.trim() || null,
        country_code: settingsDraft.countryCode || null,
        profile_picture: resolvedProfilePicture || null,
        birthday: settingsDraft.birthday || null,
      });

      onProfileUpdated({
        nickname: settingsDraft.nickname.trim() || userProfile.nickname,
        countryCode: settingsDraft.countryCode,
        profile_picture: resolvedProfilePicture || "",
        birthday: settingsDraft.birthday,
      });

      setShowSettingsSavedPopup(true);
    } catch (error) {
      console.error("Failed to update user settings", error);
    } finally {
      setSettingsSaving(false);
    }
  };

  const handleResetProfilePhotoToGoogle = async () => {
    setSettingsResettingPhoto(true);
    try {
      const updated = await resetCurrentUserProfilePictureToGoogle();
      const nextPicture = updated.profile_picture || "";
      setSettingsDraft((prev) => ({ ...prev, profilePicture: nextPicture }));
      onProfileUpdated({ profile_picture: nextPicture });
    } catch (error) {
      console.error("Failed to reset profile photo", error);
    } finally {
      setSettingsResettingPhoto(false);
    }
  };

  const handlePhotoUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (ev) => {
        if (typeof ev.target?.result === "string") {
          setSettingsDraft((prev) => ({ ...prev, profilePicture: ev.target!.result as string }));
        }
      };
      reader.readAsDataURL(file);
    }
  };

  return (
    <>
      <SimpleModal
        open={open}
        title={settingsModalView === "settings" ? "SETTINGS" : "DEACTIVATE ACCOUNT"}
        icon={settingsModalView === "settings" ? <Settings size={14} className="text-gray-600" strokeWidth={2.5} /> : <UserX size={14} className="text-gray-600" strokeWidth={2.5} />}
        onClose={onClose}
      >
        <div className="hidden">
          <input type="file" ref={settingsPhotoInputRef} accept="image/*" onChange={handlePhotoUpload} />
        </div>
        
        {settingsModalView === "settings" ? (
          <div className="space-y-5 mt-2">
            <div className="p-5 rounded-3xl border border-white/60 bg-[#f5f7f9]/60 backdrop-blur-md shadow-[inset_0_2px_4px_rgba(255,255,255,0.7)] flex flex-col sm:flex-row items-center gap-5">
              <div className="flex border-none items-center gap-5">
                <div className="w-16 h-16 rounded-[1.25rem] overflow-hidden border border-white shadow-sm bg-white flex items-center justify-center text-gray-400">
                  {settingsDraft.profilePicture ? (
                    <img src={settingsDraft.profilePicture} alt="Profile" className="w-full h-full object-cover" />
                  ) : (
                    <span className="text-[10px] font-semibold">No Image</span>
                  )}
                </div>
                <div>
                  <p className="text-[10px] font-bold uppercase tracking-widest text-[#8b98a5] mb-2.5">{t("mypage.profilePhoto")}</p>
                  <button
                    type="button"
                    onClick={() => settingsPhotoInputRef.current?.click()}
                    className="h-9 px-5 rounded-xl border border-gray-200/50 bg-white/80 shadow-sm text-xs font-semibold text-gray-700 hover:bg-white transition-all hover:scale-[1.02]"
                  >
                    {t("mypage.changePhoto")}
                  </button>
                  <button
                    type="button"
                    onClick={handleResetProfilePhotoToGoogle}
                    disabled={settingsResettingPhoto}
                    className="h-9 ml-2 px-5 rounded-xl border border-gray-200/50 bg-white/80 shadow-sm text-xs font-semibold text-gray-700 hover:bg-white transition-all hover:scale-[1.02] disabled:opacity-60 disabled:hover:scale-100"
                  >
                    {settingsResettingPhoto ? t("mypage.restoringPhoto") : t("mypage.useGooglePhoto")}
                  </button>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
              <div>
                <label className="block text-[10px] font-bold uppercase tracking-widest text-[#8b98a5] mb-1.5 pl-1">{t("mypage.nickname")}</label>
                <input
                  value={settingsDraft.nickname}
                  onChange={(e) => setSettingsDraft((prev) => ({ ...prev, nickname: e.target.value }))}
                  className="w-full h-12 rounded-2xl border-none bg-black/[0.03] px-4 text-sm font-medium text-gray-800 transition-all duration-300 focus:outline-none focus:bg-black/[0.05] focus:ring-[1px] focus:ring-black/[0.08] shadow-[inset_0_2px_4px_rgba(0,0,0,0.02)]"
                  placeholder={t("mypage.nickname")}
                />
              </div>

              <div>
                <label className="block text-[10px] font-bold uppercase tracking-widest text-[#8b98a5] mb-1.5 pl-1">{t("mypage.country")}</label>
                <select
                  value={settingsDraft.countryCode}
                  onChange={(e) => setSettingsDraft((prev) => ({ ...prev, countryCode: e.target.value }))}
                  className="w-full h-12 rounded-2xl border-none bg-black/[0.03] pl-4 pr-12 text-sm font-medium text-gray-800 transition-all duration-300 focus:outline-none focus:bg-black/[0.05] focus:ring-[1px] focus:ring-black/[0.08] shadow-[inset_0_2px_4px_rgba(0,0,0,0.02)] cursor-pointer appearance-none bg-[url('data:image/svg+xml;charset=US-ASCII,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20width%3D%22292.4%22%20height%3D%22292.4%22%3E%3Cpath%20fill%3D%22%23374151%22%20d%3D%22M287%2069.4a17.6%2017.6%200%200%200-13-5.4H18.4c-5%200-9.3%201.8-12.9%205.4A17.6%2017.6%200%200%200%200%2082.2c0%205%201.8%209.3%205.4%2012.9l128%20127.9c3.6%203.6%207.8%205.4%2012.8%205.4s9.2-1.8%2012.8-5.4L287%2095c3.5-3.5%205.4-7.8%205.4-12.8%200-5-1.9-9.2-5.5-12.8z%22%2F%3E%3C%2Fsvg%3E')] bg-[length:12px_12px] bg-[position:right_1.25rem_center] bg-no-repeat"
                >
                  <option value="">{t("mypage.selectCountry")}</option>
                  {countryOptions.map((country) => (
                    <option key={country.code} value={country.code}>
                      {country.name} ({country.code})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-[10px] font-bold uppercase tracking-widest text-[#8b98a5] mb-1.5 pl-1">{t("profile.birthday")}</label>
                <input
                  type="date"
                  value={settingsDraft.birthday}
                  onChange={(e) => setSettingsDraft((prev) => ({ ...prev, birthday: e.target.value }))}
                  className="w-full h-12 rounded-2xl border-none bg-black/[0.03] px-4 text-sm font-medium text-gray-800 transition-all duration-300 focus:outline-none focus:bg-black/[0.05] focus:ring-[1px] focus:ring-black/[0.08] shadow-[inset_0_2px_4px_rgba(0,0,0,0.02)] cursor-pointer"
                />
              </div>

              <div>
                <label className="block text-[10px] font-bold uppercase tracking-widest text-[#8b98a5] mb-1.5 pl-1">{t("profile.language")}</label>
                <LanguageSwitcher
                  variant="select"
                  className="w-full h-12 !rounded-2xl !border-none !bg-black/[0.03] pl-4 !pr-12 !text-sm !font-medium !text-gray-800 transition-all duration-300 focus:outline-none focus:!bg-black/[0.05] focus:!ring-[1px] focus:!ring-black/[0.08] shadow-[inset_0_2px_4px_rgba(0,0,0,0.02)] cursor-pointer !appearance-none !bg-[url('data:image/svg+xml;charset=US-ASCII,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20width%3D%22292.4%22%20height%3D%22292.4%22%3E%3Cpath%20fill%3D%22%23374151%22%20d%3D%22M287%2069.4a17.6%2017.6%200%200%200-13-5.4H18.4c-5%200-9.3%201.8-12.9%205.4A17.6%2017.6%200%200%200%200%2082.2c0%205%201.8%209.3%205.4%2012.9l128%20127.9c3.6%203.6%207.8%205.4%2012.8%205.4s9.2-1.8%2012.8-5.4L287%2095c3.5-3.5%205.4-7.8%205.4-12.8%200-5-1.9-9.2-5.5-12.8z%22%2F%3E%3C%2Fsvg%3E')] !bg-[length:12px_12px] !bg-[position:right_1.25rem_center] !bg-no-repeat"
                />
              </div>
            </div>

            <div className="pt-6 flex flex-col sm:flex-row items-center justify-between gap-5">
              <button
                type="button"
                onClick={handleOpenDeactivateAccount}
                className="text-[10px] font-bold text-gray-400 hover:text-red-500 transition-colors uppercase tracking-widest flex items-center gap-1 order-2 sm:order-1"
              >
                {t("mypage.deactivateAccount")}
              </button>

              <div className="flex justify-end gap-3 w-full sm:w-auto order-1 sm:order-2">
                <button
                  type="button"
                  onClick={onClose}
                  className="h-12 w-full sm:w-auto px-7 rounded-2xl bg-black/5 text-sm font-bold text-gray-700 hover:bg-black/10 transition-all flex items-center justify-center"
                >
                  {t("common.cancel")}
                </button>
                <button
                  type="button"
                  onClick={handleSaveSettingsPopup}
                  disabled={settingsSaving}
                  className="h-12 w-full sm:w-auto min-w-[110px] rounded-2xl bg-gradient-to-r from-gray-900 to-black text-white text-sm font-bold shadow-[0_8px_16px_-4px_rgba(0,0,0,0.3)] hover:shadow-[0_12px_24px_-6px_rgba(0,0,0,0.4)] hover:-translate-y-0.5 disabled:opacity-60 disabled:hover:translate-y-0 transition-all duration-300 flex items-center justify-center gap-2"
                >
                  {settingsSaving ? t("common.saving") : t("common.save")}
                </button>
              </div>
            </div>
          </div>
        ) : (
          <div className="space-y-5">
            <div className="rounded-2xl border border-gray-200 bg-white p-4 space-y-3">
              <div>
                <p className="text-[11px] font-bold uppercase tracking-wider text-gray-500">{t("mypage.googleAccountConfirm")}</p>
                <p className="text-sm font-semibold text-gray-900 mt-1 break-all">
                  {userProfile.bio || t("mypage.unknownAccount")}
                </p>
              </div>
              <label className="flex items-start gap-2 text-sm text-gray-800">
                <input
                  type="checkbox"
                  className="mt-1"
                  checked={deactivateGoogleConfirmed}
                  onChange={(e) => setDeactivateGoogleConfirmed(e.target.checked)}
                />
                <span>{t("mypage.confirmGoogleAccount")}</span>
              </label>
              {deactivateSubmitAttempted && !deactivateGoogleConfirmed && (
                <div className="text-xs font-semibold text-red-600">{t("mypage.pleaseConfirmGoogle")}</div>
              )}
            </div>

            <div className="rounded-2xl border border-gray-200 bg-white p-4 space-y-3">
              <div>
                <p className="text-[11px] font-bold uppercase tracking-wider text-gray-500">{t("mypage.deactivateAgreement")}</p>
                <p className="text-xs text-gray-500 mt-1">{t("mypage.deactivateAgreementDesc")}</p>
              </div>
              <label className="flex items-start gap-2 text-sm text-gray-800">
                <input
                  type="checkbox"
                  className="mt-1"
                  checked={deactivateAgreementConfirmed}
                  onChange={(e) => setDeactivateAgreementConfirmed(e.target.checked)}
                />
                <span>{t("mypage.agreeToDeactivate")}</span>
              </label>
              {deactivateSubmitAttempted && !deactivateAgreementConfirmed && (
                <div className="text-xs font-semibold text-red-600">{t("mypage.pleaseAgreeDeactivate")}</div>
              )}
            </div>

            {!!deactivateError && <div className="text-xs font-semibold text-red-600">{deactivateError}</div>}

            <div className="pt-1 flex justify-end gap-2">
              <button
                type="button"
                onClick={handleCancelDeactivateAccount}
                className="h-10 px-4 rounded-full border border-gray-300 bg-white text-xs font-bold text-gray-700 hover:bg-gray-50 transition-all"
              >
                {t("common.cancel")}
              </button>
              <button
                type="button"
                onClick={handleRequestDeactivateAccount}
                disabled={deactivateSubmitting}
                className="h-10 px-4 rounded-full border border-gray-900 bg-black text-white text-xs font-bold hover:opacity-90 disabled:opacity-60 transition-all"
              >
                {t("mypage.deactivateButton")}
              </button>
            </div>
          </div>
        )}
      </SimpleModal>

      <SimpleModal
        open={deactivateConfirmOpen}
        title={t("mypage.deactivateConfirmTitle")}
        onClose={handleCancelDeactivateConfirm}
        zIndex={60}
        maxWidth="sm"
      >
        <div className="space-y-4">
          <p className="text-sm font-bold text-gray-900">{t("mypage.deactivateConfirmMessage")}</p>
          <div className="text-xs text-gray-500 leading-relaxed space-y-1">
            <p>• {t("mypage.deactivateWarning1")}</p>
            <p>• {t("mypage.deactivateWarning2")}</p>
            <p>• {t("mypage.deactivateWarning3")}</p>
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={handleCancelDeactivateConfirm}
              disabled={deactivateSubmitting}
              className="h-10 px-4 rounded-full border border-gray-300 bg-white text-xs font-bold text-gray-700 hover:bg-gray-50 transition-all disabled:opacity-60"
            >
              {t("common.no")}
            </button>
            <button
              type="button"
              onClick={handleConfirmDeactivateAccount}
              disabled={deactivateSubmitting}
              className="h-10 px-4 rounded-full border border-red-600 bg-red-600 text-white text-xs font-bold hover:bg-red-700 disabled:opacity-60 transition-all"
            >
              {deactivateSubmitting ? t("mypage.deactivating") : t("mypage.deactivateButton")}
            </button>
          </div>
        </div>
      </SimpleModal>

      <SimpleModal
        open={showSettingsSavedPopup}
        title={t("mypage.settingsSavedTitle")}
        onClose={() => {
          setShowSettingsSavedPopup(false);
          onClose(); // 저장 완료 팝업을 닫으면서 메뉴 모달 전체도 닫음
        }}
        zIndex={60}
        maxWidth="sm"
      >
        <div className="space-y-4">
          <p className="text-sm text-gray-700">{t("mypage.settingsSavedMessage")}</p>
          <div className="flex justify-end">
            <button
              type="button"
              onClick={() => {
                setShowSettingsSavedPopup(false);
                onClose();
              }}
              className="h-10 px-6 rounded-full border border-gray-900 bg-black text-white text-xs font-bold hover:opacity-90 transition-all"
            >
              {t("common.confirm")}
            </button>
          </div>
        </div>
      </SimpleModal>
    </>
  );
}
