"use client";

import { useContext } from "react";
import { LanguageContext } from "./LanguageContext";

export function useTranslation() {
  return useContext(LanguageContext);
}
