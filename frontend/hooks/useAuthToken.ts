"use client";

import { useState, useEffect } from "react";

export const useAuthToken = (): string | null => {
  const [token, setToken] = useState<string | null>(null);

  useEffect(() => {
    const savedToken = localStorage.getItem("authToken");
    if (savedToken) {
      setToken(savedToken);
    }
  }, []);

  return token;
};
