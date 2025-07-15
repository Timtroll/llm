'use client';

import { useRouter } from 'next/navigation';

export const useAuthToken = () => {
  const router = useRouter();

  const saveToken = (token: string) => {
    localStorage.setItem('token', token);
  };

  const getToken = () => {
    return localStorage.getItem('token');
  };

  const clearToken = () => {
    localStorage.removeItem('token');
    router.push('/login');
  };

  return { saveToken, getToken, clearToken };
};
