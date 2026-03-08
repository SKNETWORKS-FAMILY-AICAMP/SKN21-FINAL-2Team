"use client";

import { X } from "lucide-react";
import { AnimatePresence, motion } from "framer-motion";
import { PlaceMapPanel, type ChatMapPlace, type ChatMapPlaceGroup } from "./PlaceMapPanel";

type PlaceMapSheetProps = {
  open: boolean;
  onClose: () => void;
  places: ChatMapPlace[];
  groups: ChatMapPlaceGroup[];
  selectedMapPlaceId: string | null;
  onSelectPlace: (mapId: string) => void;
  onMarkerClick: (mapId: string) => void;
};

export function PlaceMapSheet({
  open,
  onClose,
  places,
  groups,
  selectedMapPlaceId,
  onSelectPlace,
  onMarkerClick,
}: PlaceMapSheetProps) {
  return (
    <AnimatePresence>
      {open && (
        <motion.div
          className="fixed inset-0 z-[80] lg:hidden"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
        >
          <button
            type="button"
            className="absolute inset-0 bg-black/35"
            onClick={onClose}
            aria-label="Close map sheet"
          />

          <motion.div
            className="absolute bottom-0 left-0 right-0 h-[62vh] rounded-t-3xl bg-white shadow-2xl overflow-hidden"
            initial={{ y: "100%" }}
            animate={{ y: 0 }}
            exit={{ y: "100%" }}
            transition={{ type: "spring", stiffness: 380, damping: 34 }}
          >
            <div className="h-12 px-4 flex items-center justify-between border-b border-gray-100">
              <div className="text-sm font-semibold text-gray-900">Map</div>
              <button
                type="button"
                onClick={onClose}
                className="w-8 h-8 rounded-full border border-gray-200 bg-white text-gray-600 flex items-center justify-center"
                aria-label="Close"
              >
                <X size={14} />
              </button>
            </div>

            <PlaceMapPanel
              className="h-[calc(62vh-48px)]"
              places={places}
              groups={groups}
              selectedMapPlaceId={selectedMapPlaceId}
              onSelectPlace={onSelectPlace}
              onMarkerClick={onMarkerClick}
              showHeader={false}
            />
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
