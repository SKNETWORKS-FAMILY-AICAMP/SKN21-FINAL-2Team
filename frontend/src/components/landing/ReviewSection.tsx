"use client";

import { motion } from "framer-motion";
import { Star, Quote } from "lucide-react";

const reviews = [
    {
        id: 1, name: "Jimin Park", role: "Digital Nomad", location: "Busan, South Korea",
        image: "https://images.unsplash.com/photo-1624091844772-554661d10173?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxrb3JlYW4lMjB3b21hbiUyMHBvcnRyYWl0JTIwcHJvZmVzc2lvbmFsJTIwbWluaW1hbHxlbnwxfHx8fDE3NzE0ODI4ODd8MA&ixlib=rb-4.1.0&q=80&w=1080",
        rating: 5, text: "Triver completely changed how I explore my own country. It found hidden gems in Seongsu-dong that even locals don't know about.",
    },
    {
        id: 2, name: "Alex Kim", role: "Photography Enthusiast", location: "Seoul, South Korea",
        image: "https://images.unsplash.com/photo-1661854236305-b02cef4aa0af?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxrb3JlYW4lMjBtYW4lMjBwb3J0cmFpdCUyMHN0eWxpc2glMjBtaW5pbWFsfGVufDF8fHx8MTc3MTQ4Mjg4N3ww&ixlib=rb-4.1.0&q=80&w=1080",
        rating: 5, text: "As a photographer, I'm always chasing the perfect light and aesthetic. Triver's 'Collection' feature is a game-changer.",
    },
    {
        id: 3, name: "Sarah Jenkins", role: "Food Blogger", location: "New York, USA",
        image: "https://images.unsplash.com/photo-1628544220588-4d364916a3c1?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHx3b21hbiUyMHRyYXZlbGVyJTIwcG9ydHJhaXQlMjBtaW5pbWFsfGVufDF8fHx8MTc3MTQ4Mjg4N3ww&ixlib=rb-4.1.0&q=80&w=1080",
        rating: 5, text: "Planning a foodie trip to Seoul was overwhelming until I found Triver. It built a logical route connecting the best street food stalls.",
    },
];

export function ReviewSection() {
    return (
        <section id="reviews" className="py-24 bg-gray-50 overflow-hidden">
            <div className="max-w-7xl mx-auto px-6 lg:px-8">
                <div className="text-center mb-16">
                    <motion.div initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ duration: 0.6 }}>
                        <h2 className="text-4xl md:text-6xl font-black tracking-tight text-black mb-6 uppercase">Community Voices</h2>
                        <p className="text-gray-500 font-light max-w-xl mx-auto">Hear from the explorers who have redefined their travel experiences with Triver.</p>
                    </motion.div>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                    {reviews.map((review, index) => (
                        <motion.div
                            key={review.id}
                            initial={{ opacity: 0, y: 30 }}
                            whileInView={{ opacity: 1, y: 0 }}
                            viewport={{ once: true }}
                            transition={{ duration: 0.5, delay: index * 0.1 }}
                            className="bg-white p-8 rounded-[32px] shadow-sm hover:shadow-md transition-shadow duration-300 relative group border border-gray-100/50"
                        >
                            <div className="absolute top-8 right-8 text-gray-100 group-hover:text-black/5 transition-colors duration-300">
                                <Quote size={40} fill="currentColor" strokeWidth={0} />
                            </div>
                            <div className="flex gap-1 mb-6 text-black">
                                {[...Array(review.rating)].map((_, i) => (
                                    <Star key={i} size={14} fill="currentColor" strokeWidth={0} />
                                ))}
                            </div>
                            <p className="text-gray-600 text-sm leading-relaxed mb-8 font-light italic">"{review.text}"</p>
                            <div className="flex items-center gap-4 mt-auto">
                                <div className="w-12 h-12 rounded-full overflow-hidden ring-2 ring-gray-50">
                                    <img src={review.image} alt={review.name} className="w-full h-full object-cover grayscale group-hover:grayscale-0 transition-all duration-500" />
                                </div>
                                <div>
                                    <h4 className="font-bold text-sm text-black">{review.name}</h4>
                                    <div className="flex flex-col text-[10px] text-gray-400 font-medium uppercase tracking-wide">
                                        <span>{review.role}</span>
                                        <span className="text-gray-300">{review.location}</span>
                                    </div>
                                </div>
                            </div>
                        </motion.div>
                    ))}
                </div>
            </div>
        </section>
    );
}
