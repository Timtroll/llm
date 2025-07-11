'use client';

import { useState } from 'react';
import Link from 'next/link';

export default function Home() {
  const [model, setModel] = useState('llama-7b');
  const [prompt, setPrompt] = useState('');
  const [response, setResponse] = useState('');
  const [sessionId, setSessionId] = useState('default');
  const [isLoading, setIsLoading] = useState(false);
  const [parameters, setParameters] = useState({
    n_tokens: 256,
    temp: 0.7,
    top_p: 0.9,
    top_k: 40,
    repeat_penalty: 1.1,
    seed: 42,
  });

  const models = ['llama-7b', 'model-q4'];

  const handleSubmit = async (e: React.FormEvent, reset: boolean = false) => {
    e.preventDefault();
    setIsLoading(true);

    try {
    //   const res = await fetch(process.env.NEXT_PUBLIC_API_URL + '/generate', {
    //     method: 'POST',
    //     headers: { 'Content-Type': 'application/json' },
    //     body: JSON.stringify({ text: prompt, model, session_id: sessionId, reset, ...parameters }),
    //   });
      const res = await fetch('http://spamh:5555/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: prompt, model, session_id: sessionId, reset, ...parameters }),
      });
      const data = await res.json();
      if (data.error) {
        setResponse(`Ошибка: ${data.error}`);
      } else {
        setResponse(data.response);
      }
    } catch (error) {
      setResponse('Ошибка при запросе');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-black text-white p-4">
      <nav className="flex gap-4 mb-4">
        <div>
          <label className="mr-2">Модель:</label>
          <select
            value={model}
            onChange={(e) => setModel(e.target.value)}
            className="bg-gray-800 text-white p-1 rounded"
          >
            {models.map((m) => (
              <option key={m} value={m}>{m}</option>
            ))}
          </select>
        </div>
        <Link href="#chat" className="bg-gray-800 px-4 py-1 rounded">
          Чат
        </Link>
      </nav>

      <div className="max-w-2xl mx-auto">
        <h1 className="text-2xl mb-4">LLM Чат</h1>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block mb-1">Параметры:</label>
            <div className="grid grid-cols-2 gap-2">
              <input
                type="number"
                placeholder="n_tokens"
                value={parameters.n_tokens}
                onChange={(e) => setParameters({ ...parameters, n_tokens: Number(e.target.value) })}
                className="bg-gray-800 p-1 rounded"
              />
              <input
                type="number"
                step="0.1"
                placeholder="temp"
                value={parameters.temp}
                onChange={(e) => setParameters({ ...parameters, temp: Number(e.target.value) })}
                className="bg-gray-800 p-1 rounded"
              />
              <input
                type="number"
                step="0.1"
                placeholder="top_p"
                value={parameters.top_p}
                onChange={(e) => setParameters({ ...parameters, top_p: Number(e.target.value) })}
                className="bg-gray-800 p-1 rounded"
              />
              <input
                type="number"
                placeholder="top_k"
                value={parameters.top_k}
                onChange={(e) => setParameters({ ...parameters, top_k: Number(e.target.value) })}
                className="bg-gray-800 p-1 rounded"
              />
              <input
                type="number"
                step="0.1"
                placeholder="repeat_penalty"
                value={parameters.repeat_penalty}
                onChange={(e) => setParameters({ ...parameters, repeat_penalty: Number(e.target.value) })}
                className="bg-gray-800 p-1 rounded"
              />
              <input
                type="number"
                placeholder="seed"
                value={parameters.seed}
                onChange={(e) => setParameters({ ...parameters, seed: Number(e.target.value) })}
                className="bg-gray-800 p-1 rounded"
              />
            </div>
          </div>
          <div>
            <label className="block mb-1">Session ID:</label>
            <input
              type="text"
              value={sessionId}
              onChange={(e) => setSessionId(e.target.value)}
              className="bg-gray-800 p-1 rounded w-full"
            />
          </div>
          <div>
            <label className="block mb-1">Промпт:</label>
            <textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              className="bg-gray-800 p-2 rounded w-full h-24"
              placeholder="Введите ваш запрос..."
            />
          </div>
          <div className="flex gap-2">
            <button
              type="submit"
              disabled={isLoading}
              className="bg-gray-700 px-4 py-2 rounded disabled:opacity-50"
            >
              {isLoading ? 'Загрузка...' : 'Отправить'}
            </button>
            <button
              type="button"
              onClick={(e) => handleSubmit(e as any, true)}
              className="bg-gray-700 px-4 py-2 rounded"
            >
              Сбросить историю
            </button>
          </div>
        </form>
        {response && (
          <div className="mt-4">
            <h2 className="text-xl">Ответ:</h2>
            <p className="bg-gray-800 p-2 rounded">{response}</p>
          </div>
        )}
      </div>
    </div>
  );
}