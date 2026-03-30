"use client";

import { motion } from "framer-motion";
import { PLACE_PLACEHOLDER } from "@/lib/imageUrl";

export type PlaceCardItem = {
    contentid: string;
    title: string;
    address: string;
    image_url?: string | null;
};

type PlaceCardProps = {
    item: PlaceCardItem;
    onClick?: () => void;
};

/**
 * 장소 이미지 카드 컴포넌트.
 *
 * ExplorePage에서 restaurants / tourist / tours 세 섹션에 동일한 카드 JSX가
 * 반복(6회+)되어 추출함.
 */
export function PlaceCard({ item, onClick }: PlaceCardProps) {
    return (
        <motion.div
            whileHover={{ y: -3 }}
            className="group cursor-pointer"
            onClick={onClick}
        >
            <div className="aspect-[16/10] w-full rounded-2xl overflow-hidden bg-gray-100 mb-2">
                <img
                    src={item.image_url || PLACE_PLACEHOLDER}
                    alt={item.title}
                    onError={(e) => {
                        e.currentTarget.src = PLACE_PLACEHOLDER;
                    }}
                    className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                />
            </div>
            <h5 className="text-sm font-medium text-gray-900 leading-tight truncate">
                {item.title}
            </h5>
            <p className="text-[11px] text-gray-400 truncate">{item.address}</p>
        </motion.div>
    );
}
