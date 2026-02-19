"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import {
  Languages,
  Share2,
  Ticket,
  CheckCircle2,
  MessageSquare,
  Sparkles,
} from "lucide-react";
import {
  ResponsiveContainer,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  Radar,
  PolarRadiusAxis,
} from "recharts";
import { Sidebar } from "@/components/Sidebar";
import { SettingsModal } from "@/components/SettingsModal";

export default function MyPage() {
  const [userProfile, setUserProfile] = useState({
    nickname: "Leo_Travels",
    bio: "Explorer Lvl.3",
    preferences: ["Relaxation", "Food"],
  });

  const divingStyleData = [
    { subject: "Relaxation", fullMark: 150 },
    { subject: "Adventure", fullMark: 150 },
    { subject: "Culture", fullMark: 150 },
    { subject: "Food", fullMark: 150 },
    { subject: "Nature", fullMark: 150 },
    { subject: "Luxury", fullMark: 150 },
  ].map((item) => ({
    ...item,
    A: userProfile.preferences.includes(item.subject) ? 120 : 50,
  }));

  const handleSaveSettings = (nickname: string, bio: string, preferences: string[]) => {
    setUserProfile({ nickname, bio, preferences });
  };

  return (
    <div className="flex w-full h-screen bg-gray-100 p-4 gap-4 overflow-hidden">
      <div className="flex-none h-full">
        <Sidebar />
      </div>
      <main className="flex-1 h-full min-w-0 bg-white rounded-lg overflow-y-auto">
        <div className="p-6">
          <header className="mb-6 flex items-end justify-between border-b border-gray-100 pb-4">
            <div>
              <h1 className="text-2xl font-serif italic font-medium text-gray-900 mb-1">Travel Identity</h1>
              <p className="text-xs text-gray-500 font-medium tracking-wide uppercase">Profile & Preferences</p>
            </div>
            <SettingsModal
              initialNickname={userProfile.nickname}
              initialBio={userProfile.bio}
              initialPreferences={userProfile.preferences}
              onSave={handleSaveSettings}
            />
          </header>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 pb-8">
            <div className="space-y-4">
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="p-5 rounded-xl border border-gray-200 bg-white hover:border-gray-300 transition-colors"
              >
                <div className="flex items-center gap-4 mb-5">
                  <div className="w-14 h-14 rounded-lg overflow-hidden border border-gray-100 shadow-sm">
                    <img
                      src="https://images.unsplash.com/photo-1539571696357-5a69c17a67c6?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxtYW4lMjBwb3J0cmFpdHxlbnwxfHx8fDE3NzE0NTM5MTh8MA&ixlib=rb-4.1.0&q=80&w=1080"
                      alt="Profile"
                      className="w-full h-full object-cover grayscale-[20%]"
                    />
                  </div>
                  <div>
                    <h3 className="font-bold text-base text-gray-900">{userProfile.nickname}</h3>
                    <p className="text-[10px] text-gray-400 font-mono uppercase tracking-widest mt-0.5">{userProfile.bio}</p>
                    <div className="flex gap-2 mt-2">
                      <span className="px-1.5 py-0.5 bg-black text-white text-[9px] font-bold rounded-sm uppercase tracking-wider">Pro</span>
                      <span className="px-1.5 py-0.5 border border-gray-200 text-gray-500 text-[9px] font-bold rounded-sm uppercase tracking-wider">Verified</span>
                    </div>
                  </div>
                </div>
                <div className="space-y-2">
                  <div className="flex items-center justify-between p-2.5 bg-gray-50 rounded-lg border border-gray-100/50">
                    <div className="flex items-center gap-2">
                      <Languages size={14} className="text-gray-400" />
                      <div className="flex flex-col">
                        <span className="text-[10px] font-bold text-gray-900 uppercase">Language</span>
                        <span className="text-[9px] text-gray-500">English (US)</span>
                      </div>
                    </div>
                    <button className="text-[9px] font-bold text-black border-b border-black leading-none pb-0.5 hover:opacity-70">Change</button>
                  </div>
                </div>
              </motion.div>

              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 }}
                className="p-5 rounded-xl border border-gray-200 bg-white h-[280px] flex flex-col hover:border-gray-300 transition-colors"
              >
                <div className="mb-2 border-b border-gray-50 pb-2">
                  <h3 className="font-bold text-xs text-gray-900 uppercase tracking-widest">Diving Style</h3>
                </div>
                <div className="flex-1 -ml-4 -mt-2">
                  <ResponsiveContainer width="100%" height="100%">
                    <RadarChart cx="50%" cy="50%" outerRadius="65%" data={divingStyleData}>
                      <PolarGrid stroke="#e5e7eb" />
                      <PolarAngleAxis dataKey="subject" tick={{ fill: "#9ca3af", fontSize: 9, fontWeight: 600, fontFamily: "monospace" }} />
                      <PolarRadiusAxis angle={30} domain={[0, 150]} tick={false} axisLine={false} />
                      <Radar name="Leo" dataKey="A" stroke="#000000" strokeWidth={1.5} fill="#000000" fillOpacity={0.05} />
                    </RadarChart>
                  </ResponsiveContainer>
                </div>
              </motion.div>
            </div>

            <div className="space-y-4 lg:col-span-2">
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 }}
                className="p-6 rounded-xl bg-black text-white relative overflow-hidden group shadow-lg"
              >
                <div className="absolute top-0 right-0 w-64 h-64 bg-white/5 rounded-full blur-3xl -translate-y-1/2 translate-x-1/2 group-hover:bg-white/10 transition-colors duration-700"></div>
                <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
                  <div>
                    <div className="flex items-center gap-2 text-white/50 text-[9px] font-bold uppercase tracking-[0.2em] mb-3">
                      <Sparkles size={10} className="text-white" /> Active Context
                    </div>
                    <h2 className="text-xl font-serif italic font-light mb-2 tracking-wide">Seongsu-dong K-Beauty Tour</h2>
                    <p className="text-white/60 text-xs font-light max-w-md leading-relaxed">
                      Continuing from session #8821. Focusing on flagship stores and hidden cafes.
                    </p>
                  </div>
                  <button className="whitespace-nowrap flex items-center gap-2 bg-white text-black px-4 py-2.5 rounded-lg text-[10px] font-bold hover:bg-gray-200 transition-all uppercase tracking-wide">
                    <MessageSquare size={12} /> Resume Planning
                  </button>
                </div>
              </motion.div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.3 }}
                  className="p-5 rounded-xl border border-gray-200 bg-white hover:border-gray-300 transition-colors"
                >
                  <div className="flex items-center justify-between mb-5 border-b border-gray-50 pb-2">
                    <h3 className="font-bold text-xs text-gray-900 uppercase tracking-widest">Upcoming</h3>
                    <button className="text-gray-400 hover:text-black transition-colors"><Share2 size={14} /></button>
                  </div>
                  <div className="relative pl-3 space-y-5 border-l border-gray-200 ml-1.5">
                    {[
                      { time: "10:00 AM", title: "Tamburins Flagship", type: "Visit", status: "confirmed" },
                      { time: "12:30 PM", title: "Grandpa Factory Cafe", type: "Lunch", status: "pending" },
                      { time: "02:00 PM", title: "Amore Seongsu", type: "Experience", status: "confirmed" },
                    ].map((item, idx) => (
                      <div key={idx} className="relative pl-5">
                        <div className={`absolute -left-[19px] top-1 w-2 h-2 rounded-sm border border-white ring-1 ring-gray-100 ${item.status === "confirmed" ? "bg-black" : "bg-gray-300"}`}></div>
                        <div className="flex items-baseline gap-2">
                          <span className="text-[10px] text-gray-400 font-mono block">{item.time}</span>
                          <span className="text-[9px] text-gray-300 font-bold uppercase tracking-wider">{item.type}</span>
                        </div>
                        <h4 className="text-sm font-bold text-gray-900 mt-0.5">{item.title}</h4>
                      </div>
                    ))}
                  </div>
                </motion.div>

                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.4 }}
                  className="p-5 rounded-xl border border-gray-200 bg-white flex flex-col hover:border-gray-300 transition-colors"
                >
                  <div className="flex items-center justify-between mb-5 border-b border-gray-50 pb-2">
                    <h3 className="font-bold text-xs text-gray-900 uppercase tracking-widest">Vault</h3>
                    <span className="text-[9px] font-bold bg-black text-white px-1.5 py-0.5 rounded-sm">2 Active</span>
                  </div>
                  <div className="space-y-2.5 flex-1">
                    {[
                      { name: "AREX Express", provider: "Klook", status: "Ready", id: "#TK-8829" },
                      { name: "N Seoul Tower", provider: "MyRealTrip", status: "Used", id: "#TK-1102" },
                    ].map((ticket, idx) => (
                      <div key={idx} className="group p-2.5 rounded-lg border border-gray-100 hover:border-gray-300 hover:bg-gray-50 transition-all cursor-pointer flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 rounded-md bg-gray-100 flex items-center justify-center text-gray-500 group-hover:bg-white group-hover:text-black transition-colors border border-gray-200">
                            <Ticket size={12} />
                          </div>
                          <div>
                            <h4 className="text-[11px] font-bold text-gray-900 leading-tight">{ticket.name}</h4>
                            <div className="flex items-center gap-1.5 mt-0.5">
                              <span className="text-[9px] text-gray-400 font-medium uppercase">{ticket.provider}</span>
                              <span className="text-[9px] text-gray-300">•</span>
                              <span className="text-[9px] text-gray-400 font-mono">{ticket.id}</span>
                            </div>
                          </div>
                        </div>
                        {ticket.status === "Ready" ? (
                          <CheckCircle2 size={14} className="text-black" />
                        ) : (
                          <div className="w-3.5 h-3.5 rounded-full border border-gray-300"></div>
                        )}
                      </div>
                    ))}
                  </div>
                </motion.div>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
