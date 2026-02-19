"use client";

import { useState, useEffect } from "react";
import { Settings, User, Heart, Shield } from "lucide-react";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
    DialogTrigger,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

interface SettingsModalProps {
    initialNickname: string;
    initialBio: string;
    initialPreferences: string[];
    onSave: (nickname: string, bio: string, preferences: string[]) => void;
}

export function SettingsModal({
    initialNickname,
    initialBio,
    initialPreferences,
    onSave,
}: SettingsModalProps) {
    const [nickname, setNickname] = useState(initialNickname);
    const [bio, setBio] = useState(initialBio);
    const [preferences, setPreferences] = useState<string[]>(initialPreferences);
    const [open, setOpen] = useState(false);

    useEffect(() => {
        if (open) {
            setNickname(initialNickname);
            setBio(initialBio);
            setPreferences(initialPreferences);
        }
    }, [open, initialNickname, initialBio, initialPreferences]);

    const togglePreference = (pref: string) => {
        if (preferences.includes(pref)) {
            setPreferences(preferences.filter((p) => p !== pref));
        } else {
            setPreferences([...preferences, pref]);
        }
    };

    const handleSave = () => {
        onSave(nickname, bio, preferences);
        setOpen(false);
    };

    return (
        <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>
                <button className="px-3 py-1.5 bg-white border border-gray-200 hover:border-gray-400 text-gray-600 rounded-lg text-[11px] font-bold transition-all flex items-center gap-2 uppercase tracking-wider">
                    <Settings size={12} /> Settings
                </button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-[425px] rounded-xl bg-white">
                <DialogHeader>
                    <DialogTitle className="text-xl font-serif italic">Edit Profile</DialogTitle>
                    <DialogDescription>
                        Update your personal information and travel preferences.
                    </DialogDescription>
                </DialogHeader>

                <div className="grid gap-6 py-4">
                    <div className="space-y-4">
                        <h4 className="text-xs font-bold uppercase tracking-widest text-gray-500 flex items-center gap-2">
                            <User size={14} /> Identity
                        </h4>
                        <div className="grid gap-2">
                            <Label htmlFor="nickname">Nickname</Label>
                            <Input
                                id="nickname"
                                value={nickname}
                                onChange={(e) => setNickname(e.target.value)}
                                className="col-span-3 rounded-xl"
                            />
                        </div>
                        <div className="grid gap-2">
                            <Label htmlFor="bio">Travel Title</Label>
                            <Input
                                id="bio"
                                value={bio}
                                onChange={(e) => setBio(e.target.value)}
                                className="col-span-3 rounded-xl"
                            />
                        </div>
                    </div>

                    <div className="h-[1px] bg-gray-100 w-full" />

                    <div className="space-y-4">
                        <h4 className="text-xs font-bold uppercase tracking-widest text-gray-500 flex items-center gap-2">
                            <Heart size={14} /> Travel Style
                        </h4>
                        <div className="flex flex-wrap gap-2">
                            {["Relaxation", "Adventure", "Culture", "Food", "Nature", "Luxury"].map((pref) => (
                                <button
                                    key={pref}
                                    onClick={() => togglePreference(pref)}
                                    className={`px-3 py-1 rounded-full text-xs font-medium border transition-all ${preferences.includes(pref)
                                            ? "bg-black text-white border-black"
                                            : "bg-white text-gray-600 border-gray-200 hover:border-gray-400"
                                        }`}
                                >
                                    {pref}
                                </button>
                            ))}
                        </div>
                    </div>

                    <div className="h-[1px] bg-gray-100 w-full" />

                    <div className="space-y-4">
                        <h4 className="text-xs font-bold uppercase tracking-widest text-gray-500 flex items-center gap-2">
                            <Shield size={14} /> Account
                        </h4>
                        <div className="text-xs text-gray-500 flex justify-between items-center p-3 bg-gray-50 rounded-lg border border-gray-100">
                            <span>Email</span>
                            <span className="font-mono">leo@example.com</span>
                        </div>
                    </div>
                </div>

                <DialogFooter>
                    <Button
                        onClick={handleSave}
                        type="submit"
                        className="w-full sm:w-auto rounded-full bg-black hover:bg-black/90 text-white"
                    >
                        Save changes
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
