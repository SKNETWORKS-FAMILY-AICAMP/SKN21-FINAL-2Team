"use client";

import { motion, AnimatePresence } from "framer-motion";
import { Star, MapPin, Search, CalendarPlus, X } from "lucide-react";
import { useState, useEffect } from "react";
import { cn } from "@/lib/utils";
import { useRouter } from "next/navigation";

const categories = [
    { id: "hot-places", label: "Hot Places" },
    { id: "historical", label: "Historical" },
    { id: "nature", label: "Nature" },
    { id: "activity", label: "Activity" },
];

const destinations: Record<string, Destination[]> = {
    "hot-places": [
        { contentid: 1, title: "Seongsu-dong Cafe Street", image: "https://images.unsplash.com/photo-1735491428084-853fb91c09e7?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxTZW91bCUyMGNhZmUlMjBhZXN0aGV0aWMlMjBtaW5pbWFsaXN0fGVufDF8fHx8MTc3MTQ4MTgyNnww&ixlib=rb-4.1.0&q=80&w=1080", rating: 4.8, addr: "Seongsu-dong, Seongdong-gu", distance: "2.5 km" },
        { contentid: 2, title: "Yeonnam-dong Park", image: "https://images.unsplash.com/photo-1692103675608-6e635afa077b?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxLb3JlYW4lMjBzdHJlZXQlMjBmb29kJTIwdHRlb2tib2traSUyMGFlc3RoZXRpY3xlbnwxfHx8fDE3NzE0ODE4MjZ8MA&ixlib=rb-4.1.0&q=80&w=1080", rating: 4.7, addr: "Yeonnam-dong, Mapo-gu", distance: "4.2 km" },
        { contentid: 3, title: "Starfield Library", image: "https://images.unsplash.com/photo-1659243013574-3b0ffb781fe4?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxTdGFyZmllbGQlMjBMaWJyYXJ5JTIwQ29leCUyME1hbGwlMjBTZW91bHxlbnwxfHx8fDE3NzE0ODE5MDh8MA&ixlib=rb-4.1.0&q=80&w=1080", rating: 4.9, addr: "Samseong-dong, Gangnam-gu", distance: "8.1 km" },
    ],
    historical: [
        { contentid: 4, title: "Gwanghwamun Gate", image: "https://images.unsplash.com/photo-1591203265333-2248cd9470c6?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxHd2FuZ2h3YW11biUyMGdhdGUlMjBTZW91bCUyMGhpc3RvcmljYWx8ZW58MXx8fHwxNzcxNDgxOTE5fDA&ixlib=rb-4.1.0&q=80&w=1080", rating: 4.9, addr: "Sajik-ro, Jongno-gu", distance: "1.2 km" },
        { contentid: 5, title: "Bukchon Hanok Village", image: "https://images.unsplash.com/photo-1707925679578-2a2d1a1b3fcd?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxIYW5vayUyMHZpbGxhZ2UlMjByb29mdG9wcyUyMHRyYWRpdGlvbmFsfGVufDF8fHx8MTc3MTQ4MTkxOXww&ixlib=rb-4.1.0&q=80&w=1080", rating: 4.6, addr: "Gahoe-dong, Jongno-gu", distance: "1.5 km" },
        { contentid: 6, title: "Changdeokgung Secret Garden", image: "https://images.unsplash.com/photo-1665688523044-32afbd7a9d28?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxDaGFuZ2Rlb2tndW5nJTIwUGFsYWNlJTIwU2VjcmV0JTIwR2FyZGVufGVufDF8fHx8MTc3MTQ4MTkwOHww&ixlib=rb-4.1.0&q=80&w=1080", rating: 4.8, addr: "Yulgok-ro, Jongno-gu", distance: "2.0 km" },
    ],
    nature: [
        { contentid: 7, title: "Hangang Park Picnic", image: "https://images.unsplash.com/photo-1720250050813-78406c8d1350?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxIYW5nYW5nJTIwcml2ZXIlMjBwaWNuaWMlMjBzdW5zZXR8ZW58MXx8fHwxNzcxNDgxOTE5fDA&ixlib=rb-4.1.0&q=80&w=1080", rating: 4.8, addr: "Yeouido-dong, Yeongdeungpo-gu", distance: "5.5 km" },
        { contentid: 8, title: "Namsan Seoul Tower", image: "https://images.unsplash.com/photo-1760788935785-2f50c6092980?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxOYW1zYW4lMjBTZW91bCUyMFRvd2VyJTIwc2NlbmljJTIwdmlld3xlbnwxfHx8fDE3NzE0ODE5MDh8MA&ixlib=rb-4.1.0&q=80&w=1080", rating: 4.7, addr: "Namsan-gongwon-gil, Yongsan-gu", distance: "3.0 km" },
        { contentid: 9, title: "Seoul Forest", image: "https://images.unsplash.com/photo-1707298409328-55d0c5fa9370?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxTZW91bCUyMEZvcmVzdCUyMFBhcmslMjBkZWVyJTIwdHJlZXN8ZW58MXx8fHwxNzcxNDgxOTE5fDA&ixlib=rb-4.1.0&q=80&w=1080", rating: 4.9, addr: "Seongsu-dong, Seongdong-gu", distance: "4.0 km" },
    ],
    activity: [
        { contentid: 10, title: "Lotte World Adventure", image: "https://images.unsplash.com/photo-1674606067725-b6ab1e340753?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxMb3R0ZSUyMFdvcmxkJTIwVG93ZXIlMjBTZW91bCUyMHRoZW1lJTIwcGFya3xlbnwxfHx8fDE3NzE0ODE5MDh8MA&ixlib=rb-4.1.0&q=80&w=1080", rating: 4.6, addr: "Jamsil-dong, Songpa-gu", distance: "9.5 km" },
        { contentid: 11, title: "COEX Aquarium", image: "https://images.unsplash.com/photo-1677607219759-5ee7279f2774?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxBcXVhcml1bSUyMHR1bm5lbCUyMGZpc2glMjBibHVlfGVufDF8fHx8MTc3MTQ4MTkxOXww&ixlib=rb-4.1.0&q=80&w=1080", rating: 4.5, addr: "Samseong-dong, Gangnam-gu", distance: "8.2 km" },
        { contentid: 12, title: "Hongdae Nightlife", image: "https://images.unsplash.com/photo-1676741556435-709eaa1f872f?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxOZW9uJTIwc2lnbiUyMG5pZ2h0JTIwc3RyZWV0JTIwU2VvdWwlMjBsaXZlbHl8ZW58MXx8fHwxNzcxNDgxOTE5fDA&ixlib=rb-4.1.0&q=80&w=1080", rating: 4.7, addr: "Hongdae, Mapo-gu", distance: "4.5 km" },
    ],
};


// 데이터베이스에서 올 장소 정보의 '설계도(타입)'
export interface Destination {
    contentid: number;
    title: string;
    image: string;
    rating: number; //별점인데, 이 정보는 어디서? 
    addr: string;
    distance: string; //거리기준. 위치정보 다운로드 필요.
}

export function Destinations() {
    const router = useRouter();
    const [activeTab, setActiveTab] = useState("hot-places");
    const [displayItems, setDisplayItems] = useState<Destination[]>([]);
    const [selectedPlace, setSelectedPlace] = useState<Destination | null>(null);

    // // 주의: 실제 로그인 상태는 Context API나 전역 상태 관리(Zustand 등) 혹은 쿠키에서 가져와야 하지만, 
    // 임시로 localStorage를 확인하는 방식을 사용합니다. (구글 로그인 구현 방식에 맞게 나중에 수정 필요)
    const [isLoggedIn, setIsLoggedIn] = useState(false);

    useEffect(() => {
        // 컴포넌트 마운트 시 로그인(토큰) 여부를 확인합니다.
        const token = localStorage.getItem("token"); // 또는 구글 OAuth 관련 저장값
        setIsLoggedIn(!!token);
    }, []);

    // Plan Trip 버튼 클릭 핸들러
    const handlePlanTripClick = (place: Destination, e?: React.MouseEvent) => {
        if (e) e.stopPropagation(); // 모달 띄우기 이벤트 버블링 방지

        if (!isLoggedIn) {
            // 로그인이 안 되어 있다면 먼저 알람을 띄운 후 로그인 페이지로 보냅니다.
            alert("로그인이 필요한 서비스입니다! 로그인 페이지로 이동합니다.");
            router.push("/login"); // 실제 존재하는 로그인 페이지 경로로 수정하세요
        } else {
            // 로그인 되어 있다면, 장소 정보를 로컬 스토리지 북마크 배열에 추가합니다.
            const savedBookmarks = JSON.parse(localStorage.getItem("bookmarks") || "[]");

            // 이미 북마크 한 곳인지 확인 (중복 방지)
            const isAlreadySaved = savedBookmarks.some((b: Destination) => b.contentid === place.contentid);
            if (!isAlreadySaved) {
                savedBookmarks.push(place);
                localStorage.setItem("bookmarks", JSON.stringify(savedBookmarks));
            }

            alert(`${place.title}이(가) 북마크에 추가되었습니다!`);
            // 앱 내부의 bookmark 페이지로 부드럽게 화면 이동
            router.push("/bookmark");

            // 만약 모달이 열려있었다면 닫습니다
            setSelectedPlace(null);
        }
    };

    // 배열을 랜덤하게 섞어주는 함수 (Fisher-Yates Shuffle)
    const shuffleArray = (array: any[]) => {
        const newArr = [...array];
        for (let i = newArr.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [newArr[i], newArr[j]] = [newArr[j], newArr[i]];
        }
        return newArr;
    };

    // 탭이 바뀔 때마다 해당 카테고리의 데이터를 가져와 랜덤하게 섞어 상태에 저장합니다.
    useEffect(() => {
        const items = destinations[activeTab as keyof typeof destinations];
        if (items) {
            setDisplayItems(shuffleArray(items));
        }
    }, [activeTab]);

    {/* // 탭이 바뀔 때마다 백엔드(DB) 서버에 해당 카테고리의 데이터를 3개 요청합니다.
        //backend 데이터 연결 시 useEffect 대체할 부분.
    useEffect(() => {
        // 비동기(async) API 호출 함수 선언
        const fetchDestinations = async () => {
            try {
                // 백엔드 API 주소로 GET 요청을 보냄 (category: 탭 이름, limit: 3개 제한)
                // 현재 선택된 탭 이름(activeTab)을 주소 끝에 변수로 붙여줍니다.
                const response = await fetch(`/api/destinations?category=${activeTab}&limit=3`);
                
                if (!response.ok) {
                    throw new Error("데이터를 불러오는데 실패했습니다.");
                }
                
                // 백엔드에서 준 무작위 3개 데이터를 JSON 형태로 변환
                const data = await response.json(); 
                
                // 받아온 리스트를 화면에 보여줄 주머니(상태)에 쏙 담기!
                setDisplayItems(data);
            } catch (error) {
                console.error("API 호출 에러:", error);
                // // 주의: 여기에 에러 발생 시 처리할 로직 (예: "서버가 아파요 ㅠㅠ" 텍스트 띄우기) 추가 가능
            }
        };
        // 방금 만든 비동기 함수를 실행!
        fetchDestinations();
        
    }, [activeTab]); // activeTab(탭 이름)이 바뀔 때마다 위의 로직을 재실행*/}

    return (
        <section id="destinations" className="py-24 bg-gray-50/30">
            <div className="max-w-7xl mx-auto px-6 lg:px-8">
                <div className="flex flex-col md:flex-row md:items-end justify-between mb-16 gap-6">
                    <div>
                        <h2 className="text-4xl md:text-5xl font-black tracking-tight text-gray-900 mb-4 uppercase">Explore Seoul</h2>
                        <p className="text-gray-500 text-lg max-w-xl font-light">From historic palaces to neon-lit streets, find your perfect spot.</p>
                    </div>
                    <div className="flex flex-wrap gap-2 p-1.5 bg-gray-100/50 rounded-lg overflow-hidden backdrop-blur-sm border border-gray-200">
                        {categories.map((category) => (
                            <button
                                key={category.id}
                                onClick={() => setActiveTab(category.id)}
                                className={cn("px-5 py-2.5 rounded-md text-sm font-medium transition-all duration-300", activeTab === category.id ? "bg-black text-white shadow-sm" : "text-gray-500 hover:text-black hover:bg-gray-200/50")}
                            >
                                {category.label}
                            </button>
                        ))}
                    </div>
                </div>

                <div className="min-h-[500px]">
                    <AnimatePresence mode="wait">
                        <motion.div
                            key={activeTab}
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: -20 }}
                            transition={{ duration: 0.4 }}
                            className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8"
                        >
                            {displayItems.map((place) => (
                                <div key={place.contentid} className="group bg-white rounded-xl overflow-hidden border border-gray-100 shadow-sm hover:shadow-xl transition-all duration-300 flex flex-col">
                                    <div
                                        className="relative aspect-[4/3] overflow-hidden cursor-pointer"
                                        onClick={() => setSelectedPlace(place)} // 이미지 영역 클릭 시 해당 장소 데이터를 상태에 저장합니다.
                                    >
                                        <img src={place.image} alt={place.title} className="w-full h-full object-cover transform group-hover:scale-110 transition-transform duration-700 ease-in-out" />
                                        <div className="absolute top-4 right-4 bg-white/90 backdrop-blur-md px-3 py-1 rounded-full flex items-center gap-1 shadow-sm">
                                            <Star size={14} className="fill-black text-black" />
                                            <span className="text-xs font-bold text-gray-900">{place.rating}</span>
                                        </div>
                                    </div>
                                    <div className="p-6 flex flex-col flex-grow">
                                        <h3 className="text-xl font-bold text-gray-900 mb-2">{place.title}</h3>
                                        <div className="flex items-center gap-4 text-gray-500 text-sm mb-6 font-mono">
                                            <div className="flex items-center gap-1"><MapPin size={14} className="text-gray-400" /><span className="truncate max-w-[120px]">{place.addr}</span></div>
                                            <div className="w-1 h-1 bg-gray-300 rounded-full" />
                                            <span>{place.distance}</span>
                                        </div>
                                        <div className="mt-auto flex items-center justify-between gap-3 pt-4 border-t border-gray-50">
                                            <button className="flex items-center gap-1.5 text-xs font-medium text-gray-500 hover:text-black transition-colors px-2 py-1.5 rounded-md hover:bg-gray-100">
                                                <Search size={14} /><span>Reviews</span>
                                            </button>
                                            <button
                                                onClick={(e) => handlePlanTripClick(place, e)}
                                                className="flex items-center gap-2 bg-black text-white px-5 py-2.5 rounded-lg text-sm font-semibold hover:bg-gray-800 transition-colors shadow-lg z-10 relative"
                                            >
                                                <CalendarPlus size={16} />Plan Trip
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </motion.div>
                    </AnimatePresence>
                </div>
            </div>

            {/* ====== 모달 (Modal) 영역 ====== */}
            <AnimatePresence>
                {selectedPlace && (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        onClick={() => setSelectedPlace(null)} // 모달 바깥(배경)을 클릭하면 닫히게 합니다.
                        className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm"
                    >
                        {/* 모달 내부 컨텐츠 영역 */}
                        <motion.div
                            initial={{ scale: 0.95, opacity: 0, y: 20 }}
                            animate={{ scale: 1, opacity: 1, y: 0 }}
                            exit={{ scale: 0.95, opacity: 0, y: 20 }}
                            onClick={(e) => e.stopPropagation()} // 모달 내부를 클릭했을 때는 안 닫히도록 이벤트를 막습니다.
                            className="relative w-full max-w-2xl overflow-hidden bg-white shadow-2xl rounded-2xl"
                        >
                            {/* 닫기 버튼 */}
                            <button
                                onClick={() => setSelectedPlace(null)}
                                className="absolute z-10 p-2 bg-white rounded-full top-4 right-4 text-gray-500 hover:text-black hover:bg-gray-100 transition-colors shadow-md"
                            >
                                <X size={20} />
                            </button>

                            {/* 모달 상단 이미지 */}
                            <div className="relative w-full h-64 sm:h-80">
                                <img src={selectedPlace.image} alt={selectedPlace.title} className="object-cover w-full h-full" />
                            </div>

                            {/* 모달 하단 상세 정보 */}
                            <div className="p-8">
                                <div className="flex items-start justify-between mb-4">
                                    <div>
                                        <h3 className="text-3xl font-bold text-gray-900 mb-2">{selectedPlace.title}</h3>
                                        <div className="flex items-center gap-2 text-gray-500 font-mono">
                                            <MapPin size={16} />
                                            <span>{selectedPlace.addr} • {selectedPlace.distance}</span>
                                        </div>
                                    </div>
                                    <div className="flex flex-col items-end">
                                        <div className="flex items-center gap-1 font-bold text-lg bg-orange-100 text-orange-600 px-3 py-1 rounded-lg">
                                            <Star size={18} className="fill-current" />
                                            {selectedPlace.rating}
                                        </div>
                                    </div>
                                </div>

                                <p className="text-gray-600 leading-relaxed mb-8">
                                    {/* // 주의: 향후 DB에 'description'(상세 설명) 항목이 추가되면 이 부분에 넣으세요! */}
                                    여기에 DB에서 받아온 상세 설명 문구가 들어갈 자리입니다. 현재는 임시 텍스트를 보여주고 있습니다. 이 장소는 매력적인 분위기와 훌륭한 리뷰를 자랑하는 곳입니다. 방문하셔서 특별한 추억을 만들어보세요.
                                </p>

                                <div className="flex gap-4">
                                    <button
                                        onClick={() => handlePlanTripClick(selectedPlace)}
                                        className="flex-1 bg-black text-white px-6 py-3.5 rounded-xl font-semibold text-lg hover:bg-gray-800 transition-colors shadow-lg flex items-center justify-center gap-2"
                                    >
                                        <CalendarPlus size={20} /> Plan Trip
                                    </button>
                                </div>
                            </div>
                        </motion.div>
                    </motion.div>
                )}
            </AnimatePresence>
        </section>
    );
}
