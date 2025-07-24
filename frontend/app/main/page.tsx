'use client';

import { useState, useRef, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import dynamic from 'next/dynamic';

const Settings = dynamic(() => import('lucide-react').then((mod) => mod.Settings), { ssr: false });
const Send = dynamic(() => import('lucide-react').then((mod) => mod.Send), { ssr: false });
const X = dynamic(() => import('lucide-react').then((mod) => mod.X), { ssr: false });
const LogOut = dynamic(() => import('lucide-react').then((mod) => mod.LogOut), { ssr: false });

type AuthData = {
  token: string;
  username: string;
};

export default function Home() {
  const [messages, setMessages] = useState<
    { role: 'user' | 'assistant'; content: string }[]
  >([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState('default');
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [auth, setAuth] = useState<AuthData | null>(null);
  const chatRef = useRef<HTMLDivElement>(null);
  const isUserScrolling = useRef(false);
  const router = useRouter();

  const [parameters, setParameters] = useState({
    n_tokens: 2048,
    temp: 0.7,
    top_p: 0.9,
    top_k: 40,
    repeat_penalty: 1.1,
    seed: 42,
    model: 'model-q4',
  });

  const availableModels = ['model-q4', 'gpt-4o', 'llama-7b'];

  const handleLogout = () => {
    localStorage.removeItem('authToken');
    router.push('/');
  };

  useEffect(() => {
    const storedToken = localStorage.getItem('authToken');
    if (!storedToken) {
      router.push('/login');
    } else {
      try {
        const parsed: AuthData = JSON.parse(storedToken);
        setAuth(parsed);
      } catch (e) {
        console.error('Invalid auth token in localStorage', e);
        router.push('/login');
      }
    }
  }, [router]);

  const sendMessage = async (reset = false) => {
    if (!input.trim() || !auth) return;
    const prompt = input.trim();

    setMessages((prev) => [...prev, { role: 'user', content: prompt }]);
    setInput('');
    setIsLoading(true);

    try {
      const response = await fetch('https://llm.lmt.su/api/generate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${auth.token}`,
        },
        body: JSON.stringify({
          text: prompt,
          session_id: sessionId,
          reset,
          ...parameters,
        }),
      });

      const data = await response.json();
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: data.response || `Ошибка: ${data.error}` },
      ]);
    } catch (err: any) {
      console.error(err);
      localStorage.removeItem('authToken');
      router.push('/login');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    sendMessage();
  };

  const handleNewSession = () => {
    setSessionId(Date.now().toString());
    setMessages([]);
    setSidebarOpen(false);
  };

  useEffect(() => {
    const chatContainer = chatRef.current;
    if (!chatContainer) return;

    const handleScroll = () => {
      const { scrollTop, scrollHeight, clientHeight } = chatContainer;
      isUserScrolling.current = scrollTop + clientHeight < scrollHeight - 10;
    };

    chatContainer.addEventListener('scroll', handleScroll);
    return () => chatContainer.removeEventListener('scroll', handleScroll);
  }, []);

  useEffect(() => {
    const chatContainer = chatRef.current;
    if (!chatContainer || isUserScrolling.current) return;

    chatContainer.scrollTo({
      top: chatContainer.scrollHeight,
      behavior: 'smooth',
    });
  }, [messages, isLoading]);

  if (!auth) {
    return <div>Проверяем авторизацию…</div>;
  }

  return (
    <div className="min-h-screen flex flex-col bg-white text-black">
      <aside
        className={`fixed inset-y-0 right-0 z-50 w-80 bg-white text-black shadow-2xl transform transition-transform duration-300 ease-in-out ${
          sidebarOpen ? 'translate-x-0' : 'translate-x-full'
        } md:w-96`}
      >
        <div className="p-6 border-b border-gray-700 flex items-center justify-between">
          <h2 className="text-xl font-bold">Настройки</h2>
          <button
            onClick={() => setSidebarOpen(false)}
            className="text-gray-500 hover:text-gray-700 transition-colors"
          >
            <X size={24} />
          </button>
        </div>
        <div className="p-6 space-y-6">
          <div className="space-y-2">
            <label className="block text-sm font-medium text-gray-600">Модель</label>
            <select
              value={parameters.model}
              onChange={(e) =>
                setParameters((prev) => ({
                  ...prev,
                  model: e.target.value,
                }))
              }
              className="w-full bg-gray-100 border border-gray-300 rounded-lg px-4 py-2 text-black focus:outline-none focus:ring-2 focus:ring-gray-400 transition-all"
            >
              {availableModels.map((model) => (
                <option key={model} value={model}>
                  {model}
                </option>
              ))}
            </select>
          </div>
          {Object.entries(parameters)
            .filter(([key]) => key !== 'model')
            .map(([key, value]) => (
              <div key={key} className="space-y-2">
                <label className="block text-sm font-medium text-gray-600 capitalize">
                  {key.replace('_', ' ')}
                </label>
                <input
                  type="number"
                  value={value}
                  step={key === 'temp' || key === 'top_p' || key === 'repeat_penalty' ? 0.1 : 1}
                  onChange={(e) =>
                    setParameters((prev) => ({
                      ...prev,
                      [key]: key === 'seed' || key === 'n_tokens' || key === 'top_k'
                        ? parseInt(e.target.value)
                        : parseFloat(e.target.value),
                    }))
                  }
                  className="w-full bg-gray-100 border border-gray-300 rounded-lg px-4 py-2 text-black focus:outline-none focus:ring-2 focus:ring-gray-400 transition-all"
                />
              </div>
            ))}
        </div>
      </aside>

      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black bg-opacity-50 z-40 md:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      <div className="flex-1 flex flex-col min-h-0">
        <header className="px-6 py-4 border-b border-gray-300 bg-gray-100 flex justify-between items-center">
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <span className="text-yellow-500">☭</span> LLM Chat
          </h1>
          <div className="flex gap-2">
            <button
              onClick={handleNewSession}
              className="bg-gray-600 hover:bg-gray-500 text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors"
            >
              Новая сессия
            </button>
            <button
              onClick={handleLogout}
              className="bg-gray-600 hover:bg-gray-500 text-white p-2 rounded-lg transition-colors"
            >
              <LogOut size={20} />
            </button>
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="bg-gray-600 hover:bg-gray-500 text-white p-2 rounded-lg transition-colors"
            >
              <Settings size={20} />
            </button>
          </div>
        </header>

        <main className="flex-1 overflow-y-auto p-6" ref={chatRef}>
          <div className="max-w-3xl mx-auto space-y-4">
            {messages.length === 0 && (
              <div className="text-center text-gray-500 py-10">
                <p className="text-lg">Начните чат, отправив сообщение!</p>
              </div>
            )}
            {messages.map((msg, idx) => (
              <div
                key={idx}
                className={`p-4 rounded-xl max-w-[80%] ${
                  msg.role === 'user' ? 'bg-gray-400 ml-auto' : 'bg-gray-200 mr-auto'
                } shadow`}
              >
                <p className="whitespace-pre-wrap text-sm md:text-base">{msg.content}</p>
              </div>
            ))}
            {isLoading && (
              <div className="p-4 rounded-xl bg-gray-200 max-w-[80%] mr-auto animate-pulse">
                <p className="text-gray-500">...</p>
              </div>
            )}
          </div>
        </main>

        <div className="border-t border-gray-300 bg-gray-100 p-4">
          <form onSubmit={handleSubmit} className="max-w-3xl mx-auto flex gap-3">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Введите ваш запрос..."
              className="flex-1 bg-white border border-gray-300 rounded-lg px-4 py-3 text-sm md:text-base outline-none focus:ring-2 focus:ring-gray-400 transition-all"
            />
            <button
              type="submit"
              disabled={isLoading}
              className="bg-gray-600 hover:bg-gray-500 text-white px-4 py-3 rounded-lg disabled:opacity-50 transition-colors flex items-center gap-2"
            >
              <Send size={18} />
              <span className="hidden md:inline">Отправить</span>
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}

// "use client";

// import { useEffect, useState } from "react";
// import { useRouter } from "next/navigation";

// type AuthData = {
//   token: string;
//   username: string;
// };

// const MainPage = () => {
//   const [auth, setAuth] = useState<AuthData | null>(null);
//   const router = useRouter();

//   useEffect(() => {
//     const storedToken = localStorage.getItem("authToken");
//     if (!storedToken) {
//       router.push("/login");
//     } else {
//       try {
//         const parsed: AuthData = JSON.parse(storedToken);
//         setAuth(parsed);
//       } catch (e) {
//         console.error("Invalid auth token in localStorage", e);
//         router.push("/login");
//       }
//     }
//   }, [router]);

//   if (!auth) {
//     return <div>Проверяем авторизацию…</div>;
//   }

//   return (
//     <div>
//       <h1>Главная страница</h1>
//       <p>Добро пожаловать, <strong>{auth.username}</strong>!</p>
//       <p>Токен: <code>{auth.token}</code></p>
//     </div>
//   );
// };

// export default MainPage;
