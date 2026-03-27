import { Camera, Upload } from "lucide-react";
import { useTranslation } from "@/i18n/useTranslation";

type EmptyMomentStateProps = {
  onCreate: () => void;
};

export function EmptyMomentState({ onCreate }: EmptyMomentStateProps) {
  const { t } = useTranslation();
  return (
    <div className="flex h-full min-h-[60vh] flex-col items-center justify-center p-8 text-center">
      <div className="mb-6 flex h-24 w-24 items-center justify-center rounded-full border border-gray-100 bg-gray-50">
        <Camera size={32} className="text-gray-300" />
      </div>
      <h2 className="font-serif-korean py-[15px] text-2xl italic text-gray-900">
        {t("moments.startFirst")}
      </h2>
      <p className="mb-10 max-w-md text-sm text-gray-500">
        {t("moments.startFirstDesc")}
      </p>
      <button
        onClick={onCreate}
        className="flex items-center gap-2 rounded-full bg-black px-6 py-3 text-sm font-semibold text-white transition-colors hover:bg-gray-800"
      >
        <Upload size={14} /> {t("moments.create")}
      </button>
    </div>
  );
}
