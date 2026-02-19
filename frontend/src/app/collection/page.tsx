"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, Upload, Camera, MapPin, Grid } from "lucide-react";
import { Sidebar } from "@/components/Sidebar";

const MOCK_COLLECTION = [
    { id: 1, src: "https://images.unsplash.com/photo-1767168157604-dc1ccfbe3602?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxtb2Rlcm4lMjBtdXNldW0lMjBpbnRlcmlvciUyMGxpZ2h0JTIwY29uY3JldGV8ZW58MXx8fHwxNzcxNDc5NTg5fDA&ixlib=rb-4.1.0&q=80&w=1080", location: "Museum San, Wonju" },
    { id: 2, src: "https://images.unsplash.com/photo-1670823927806-5cc785754a4b?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHx0cmFkaXRpb25hbCUyMGhhbm9rJTIwdmlsbGFnZSUyMGtvcmVhJTIwYXV0dW1ufGVufDF8fHx8MTc3MTQ3OTU4OXww&ixlib=rb-4.1.0&q=80&w=1080", location: "Bukchon Hanok Village" },
    { id: 3, src: "https://images.unsplash.com/photo-1766244953579-e829796849cc?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxqZWp1JTIwaXNsYW5kJTIwY29hc3QlMjBjbGlmZiUyMG9jZWFufGVufDF8fHx8MTc3MTQ3OTU4OXww&ixlib=rb-4.1.0&q=80&w=1080", location: "Seopjikoji, Jeju" },
    { id: 4, src: "https://images.unsplash.com/photo-1687777504692-e825e3cb0e01?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxzZW91bCUyMG4lMjB0b3dlciUyMG5pZ2h0JTIwdmlld3xlbnwxfHx8fDE3NzE0Nzk1OTB8MA&ixlib=rb-4.1.0&q=80&w=1080", location: "Namsan Tower" },
    { id: 5, src: "https://images.unsplash.com/photo-1762440775708-7dbfe9e10842?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxidXNhbiUyMGdhbWNoZW9uJTIwY3VsdHVyZSUyMHZpbGxhZ2UlMjBjb2xvcmZ1bHxlbnwxfHx8fDE3NzE0Nzk1OTB8MA&ixlib=rb-4.1.0&q=80&w=1080", location: "Gamcheon Culture Village" },
    { id: 6, src: "https://images.unsplash.com/photo-1767294274414-5e1e6c3974e9?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxtaW5pbWFsaXN0JTIwYXJ0JTIwZ2FsbGVyeSUyMGV4aGliaXRpb258ZW58MXx8fHwxNzcxNDAzNDUxfDA&ixlib=rb-4.1.0&q=80&w=1080", location: "Leeum Museum" },
    { id: 7, src: "https://images.unsplash.com/photo-1734828813144-7ac7ad69120f?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxneWVvbmdib2tndW5nJTIwcGFsYWNlJTIwd2ludGVyJTIwc25vd3xlbnwxfHx8fDE3NzE0Nzk1OTB8MA&ixlib=rb-4.1.0&q=80&w=1080", location: "Gyeongbokgung Palace" },
    { id: 8, src: "https://images.unsplash.com/photo-1739918559783-ed40311fc814?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxzdHlsaXNoJTIwY29mZmVlJTIwc2hvcCUyMGludGVyaW9yJTIwd29vZHxlbnwxfHx8fDE3NzE0Nzk1OTB8MA&ixlib=rb-4.1.0&q=80&w=1080", location: "Seongsu Cafe Street" },
    { id: 9, src: "https://images.unsplash.com/photo-1770530436084-7be1789ecc5a?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxiYW1ib28lMjBmb3Jlc3QlMjBreW90byUyMHRyYW5xdWlsfGVufDF8fHx8MTc3MTQ3OTU5MXww&ixlib=rb-4.1.0&q=80&w=1080", location: "Damyang Bamboo Forest" },
    { id: 10, src: "https://images.unsplash.com/photo-1771218829768-16501433f7d1?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxsdXh1cnklMjBob3RlbCUyMHJvb2Z0b3AlMjBwb29sJTIwc3Vuc2V0fGVufDF8fHx8MTc3MTQ3OTU5MXww&ixlib=rb-4.1.0&q=80&w=1080", location: "Signiel Seoul" },
];

type CollectionItem = (typeof MOCK_COLLECTION)[0];

export default function CollectionPage() {
    const [selectedImage, setSelectedImage] = useState<CollectionItem | null>(null);
    const [uploadedImage, setUploadedImage] = useState<string | null>(null);

    const handleClose = () => setSelectedImage(null);

    const handleUploadMock = () => {
        setUploadedImage("https://images.unsplash.com/photo-1516035069371-29a1b244cc32?ixlib=rb-4.0.3&auto=format&fit=crop&w=1000&q=80");
    };

    return (
        <div className="flex w-full h-screen bg-gray-100 p-4 gap-4 overflow-hidden">
            <div className="flex-none h-full">
                <Sidebar />
            </div>
            <main className="flex-1 h-full min-w-0 bg-white rounded-lg flex flex-col overflow-hidden">
                <header className="flex-none p-6 pb-4 border-b border-gray-100 flex items-end justify-between">
                    <div>
                        <h1 className="text-2xl font-serif italic font-medium text-gray-900 mb-1 flex items-center gap-2">
                            Collection <Grid size={16} className="text-gray-400" />
                        </h1>
                        <p className="text-xs text-gray-500 font-medium tracking-wide uppercase">Inspirations & Moments</p>
                    </div>
                </header>

                <div className="flex-1 overflow-y-auto p-6">
                    <div className="columns-2 md:columns-3 lg:columns-4 gap-4 space-y-4">
                        {MOCK_COLLECTION.map((image) => (
                            <div
                                key={image.id}
                                className="relative group cursor-zoom-in overflow-hidden break-inside-avoid rounded-lg shadow-sm hover:shadow-lg transition-shadow mb-4"
                                onClick={() => { setSelectedImage(image); setUploadedImage(null); }}
                            >
                                <img src={image.src} alt={image.location} className="w-full h-auto object-cover transition-transform duration-700 group-hover:scale-105" />
                                <div className="absolute inset-0 bg-black/0 group-hover:bg-black/20 transition-colors duration-300" />
                                <div className="absolute bottom-0 left-0 w-full p-4 opacity-0 group-hover:opacity-100 transition-opacity duration-300 bg-gradient-to-t from-black/80 to-transparent">
                                    <p className="text-white text-[10px] font-bold uppercase tracking-widest flex items-center gap-1">
                                        <MapPin size={10} /> {image.location}
                                    </p>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>

                <AnimatePresence>
                    {selectedImage && (
                        <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            className="fixed inset-0 z-50 flex items-center justify-center bg-white/10 backdrop-blur-md p-4 md:p-8"
                            onClick={handleClose}
                        >
                            <motion.div
                                initial={{ scale: 0.95, opacity: 0 }}
                                animate={{ scale: 1, opacity: 1 }}
                                exit={{ scale: 0.95, opacity: 0 }}
                                onClick={(e) => e.stopPropagation()}
                                className="bg-black w-full max-w-5xl h-[85vh] rounded-xl overflow-hidden flex flex-col shadow-2xl border border-zinc-800"
                            >
                                <div className="flex items-center justify-between px-6 py-5 border-b border-zinc-900 bg-zinc-950">
                                    <div>
                                        <h2 className="text-lg font-serif italic text-white">Verification Mode</h2>
                                        <p className="text-zinc-500 text-xs uppercase tracking-widest">Compare & Verify</p>
                                    </div>
                                    <button onClick={handleClose} className="w-8 h-8 rounded-md border border-zinc-800 hover:bg-zinc-900 flex items-center justify-center text-zinc-400 hover:text-white transition-colors">
                                        <X size={14} />
                                    </button>
                                </div>
                                <div className="flex-1 flex flex-col md:flex-row gap-0.5 bg-zinc-900">
                                    <div className="flex-1 relative overflow-hidden bg-black group">
                                        <div className="absolute top-4 left-4 z-10 bg-black/80 backdrop-blur-sm text-white px-3 py-1.5 rounded-sm text-[9px] font-bold uppercase tracking-widest border border-white/10">Reference</div>
                                        <img src={selectedImage.src} alt="Reference" className="w-full h-full object-cover opacity-90" />
                                        <div className="absolute bottom-0 left-0 w-full p-6 bg-gradient-to-t from-black/90 to-transparent">
                                            <p className="text-white text-2xl font-serif italic">{selectedImage.location}</p>
                                        </div>
                                    </div>
                                    <div className="flex-1 relative overflow-hidden bg-zinc-950 flex items-center justify-center group">
                                        <div className="absolute top-4 left-4 z-10 bg-white/10 backdrop-blur-sm text-white px-3 py-1.5 rounded-sm text-[9px] font-bold uppercase tracking-widest border border-white/5">Your Shot</div>
                                        {uploadedImage ? (
                                            <div className="relative w-full h-full">
                                                <img src={uploadedImage} alt="User Upload" className="w-full h-full object-cover" />
                                                <button onClick={() => setUploadedImage(null)} className="absolute bottom-6 right-6 bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-md text-xs font-bold uppercase tracking-wide transition-colors shadow-lg">Remove</button>
                                            </div>
                                        ) : (
                                            <div className="text-center p-8">
                                                <div className="w-16 h-16 rounded-full border border-zinc-800 bg-zinc-900 flex items-center justify-center mx-auto mb-6">
                                                    <Camera size={24} className="text-zinc-500 group-hover:text-white transition-colors" />
                                                </div>
                                                <h3 className="text-white font-medium text-sm mb-2 uppercase tracking-wide">Upload Photo</h3>
                                                <p className="text-zinc-600 text-xs max-w-xs mx-auto mb-8 font-mono">Drag and drop your photo here to compare.</p>
                                                <button onClick={handleUploadMock} className="bg-white text-black px-6 py-3 rounded-md font-bold text-xs uppercase tracking-widest hover:bg-zinc-200 transition-colors flex items-center gap-2 mx-auto">
                                                    <Upload size={14} /> Select File
                                                </button>
                                            </div>
                                        )}
                                    </div>
                                </div>
                            </motion.div>
                        </motion.div>
                    )}
                </AnimatePresence>
            </main>
        </div>
    );
}
