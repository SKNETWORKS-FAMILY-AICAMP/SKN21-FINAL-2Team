import { Sparkles } from "lucide-react";
import { useTranslation } from "react-i18next";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";

export interface TodayRecommendation {
  title: string;
  description: string;
  prompt: string | null;
}

interface RecommendedConversationCardProps {
  todayRecommendation: TodayRecommendation | null;
}

export function RecommendedConversationCard({ todayRecommendation }: RecommendedConversationCardProps) {
  const { t } = useTranslation();
  const router = useRouter();

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.2 }}
      className="p-6 sm:p-8 rounded-3xl border border-zinc-800 bg-black shadow-xl flex flex-col justify-between"
    >
      <div>
        <div className="flex items-center gap-3 mb-6">
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-white/10 text-zinc-300">
            <Sparkles size={14} className="text-zinc-300" />
          </div>
          <h3 className="text-[11px] font-extrabold text-zinc-500 uppercase mt-0.5">
            {t("mypage.newConversation")}
          </h3>
        </div>

        {todayRecommendation ? (
          <div className="px-1">
            <h2 className="text-xl font-semibold text-white mb-2 leading-snug">
              {todayRecommendation.title}
            </h2>
            <p className="text-[13px] text-zinc-400 font-medium leading-relaxed">
              {todayRecommendation.description}
            </p>
          </div>
        ) : (
          <div className="px-1">
            <p className="text-[13px] text-zinc-400 font-medium leading-relaxed">
              {t("mypage.noRecommendation")}
            </p>
          </div>
        )}
      </div>

      <div className="mt-6">
        <button
          type="button"
          onClick={() => {
            if (todayRecommendation?.prompt) {
              router.push(`/chatbot?prompt=${encodeURIComponent(todayRecommendation.prompt)}`);
            } else {
              router.push("/chatbot");
            }
          }}
          className="w-full h-12 rounded-2xl bg-white text-black text-[13px] font-extrabold shadow-md hover:bg-gray-200 transition-colors flex items-center justify-center"
        >
          {todayRecommendation ? t("mypage.startPlanning") : t("mypage.startChat")}
        </button>
      </div>
    </motion.div>
  );
}
