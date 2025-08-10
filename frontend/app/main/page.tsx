'use client';
import { useState, useRef, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import dynamic from 'next/dynamic';
const Settings = dynamic(() => import('lucide-react').then((mod) => mod.Settings), { ssr: false });
const Send = dynamic(() => import('lucide-react').then((mod) => mod.Send), { ssr: false });
const X = dynamic(() => import('lucide-react').then((mod) => mod.X), { ssr: false });
const LogOut = dynamic(() => import('lucide-react').then((mod) => mod.LogOut), { ssr: false });
const History = dynamic(() => import('lucide-react').then((mod) => mod.History), { ssr: false });
type AuthData = {
  token: string;
  username: string;
};
type ChatHistory = {
  session_id: string;
  messages: { role: 'user' | 'assistant'; content: string }[];
};
export default function Home() {
  const [messages, setMessages] = useState<
    { role: 'user' | 'assistant'; content: string }[]
  >([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState(Math.floor(Date.now() / 1000));
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [auth, setAuth] = useState<AuthData | null>(null);
  const [chatHistory, setChatHistory] = useState<ChatHistory[]>([]);
  const chatRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const isUserScrolling = useRef(false);
  const router = useRouter();
  const [parameters, setParameters] = useState({
    n_tokens: 1024,
    temp: 0.7,
    top_p: 0.9,
    top_k: 40,
    repeat_penalty: 1.1,
    seed: 42,
    model: '',
  });
  const TitleParameters = {
    title_n_tokens: 'Максимальное количество токенов (единиц текста), которые модель может обработать за один раз. Один токен обычно равен одному слову или части слова. В контексте этой модели, 2048 токенов — это ограничение на количество входных и выходных токенов в одном запросе.',
    title_temp: 'Параметр, который влияет на степень случайности при генерации текста. Температура 1.0 означает более случайный и разнообразный выбор слов. Температура меньше 1.0 (например, 0.7) делает текст более детерминированным и предсказуемым, то есть модель будет чаще выбирать более вероятные продолжения текста. Температура выше 1.0 делает текст более креативным и разнообразным, но может приводить к менее логичному результату.',
    title_top_p: 'Параметр для сэмплинга с вероятностью (также известен как "nucleus sampling"). Модель выбирает из топовых вероятностей, суммарно составляющих p (в данном случае 0.9). Например, если top p = 0.9, то модель будет выбирать слова из множества с вероятностью 90% для текущего шага, что позволяет моделям генерировать более разнообразный текст, ограничивая выбор только наиболее вероятных слов.',
    title_top_k: 'Параметр, ограничивающий количество слов (токенов), из которых модель будет выбирать для следующего шага генерации. "top k" = 40 означает, что модель будет выбирать только из 40 наиболее вероятных токенов на каждом шаге. Меньшее значение уменьшает разнообразие, делая модель более детерминированной, а большее значение позволяет генерировать более креативные и разнообразные тексты.',
    title_repeat_penalty: 'Штраф за повторяющиеся фразы или слова. "1.1" означает, что модель будет склонна избегать повторов. Чем выше значение, тем сильнее штраф за повторение. Например, если модель повторяет одно и то же слово или фразу, этот параметр уменьшает вероятность такого повтора.',
    title_seed: 'Начальное значение для генерации случайных чисел. Если задать фиксированное значение для seed, то каждый раз при одинаковых условиях и с тем же seed модель будет генерировать одинаковые результаты. Это полезно, если требуется воспроизвести конкретный результат генерации в будущем. Если не указывать seed, то каждый запуск будет давать разные результаты.',
  };
  const [availableModels, setAvailableModels] = useState<string[]>([]);
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
  useEffect(() => {
    const fetchModels = async () => {
      if (!auth) return;
      try {
        const response = await fetch('https://llm.lmt.su/api/models', {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${auth.token}`,
          },
        });
        const data = await response.json();
        if (response.status === 401) {
          localStorage.removeItem('authToken');
          window.location.reload();
          return;
        }
        else if (response.ok) {
          const models = Object.keys(data);
          setAvailableModels(models);
          setParameters({
            n_tokens: data[models[0]]?.default_tokens || 128,
            temp: data[models[0]]?.default_temp || 0.7,
            top_p: 0.9,
            top_k: 40,
            repeat_penalty: 1.1,
            seed: 42,
            model: models[0] || '',
          });
        } else {
          console.error('Failed to fetch models:', data.error);
          setParameters({
            n_tokens: 128,
            temp: 0.7,
            top_p: 0.9,
            top_k: 40,
            repeat_penalty: 1.1,
            seed: 42,
            model: '',
          });
        }
      } catch (err) {
        console.error('Error fetching models:', err);
        setParameters({
          n_tokens: 128,
          temp: 0.7,
          top_p: 0.9,
          top_k: 40,
          repeat_penalty: 1.1,
          seed: 42,
          model: '',
        });
      }
    };
    fetchModels();
  }, [auth]);
  useEffect(() => {
    const fetchChatHistory = async () => {
      if (!auth) return;
    };
    fetchChatHistory();
  }, [auth]);
  const sendMessage = async (reset = false) => {
    if (!input.trim() || !auth || !parameters.model) router.push('/login');
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
      if (response.status === 401) {
        localStorage.removeItem('authToken');
        window.location.reload();
        return;
      }
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
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.ctrlKey) {
      e.preventDefault();
      handleSubmit(e);
    } else if (e.key === 'Enter' && e.ctrlKey) {
      setInput((prev) => prev + '\n');
    }
  };
  const handleNewChat = async () => {
    if (!auth) router.push('/login');
    try {
      const response = await fetch('https://llm.lmt.su/api/user/clear', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${auth.token}`,
        },
      });
      if (response.status === 401) {
        localStorage.removeItem('authToken');
        window.location.reload();
        return;
      }
      else if (response.ok) {
        setSessionId(Math.floor(Date.now() / 1000));
        setMessages([]);
        setSidebarOpen(false);
        setHistoryOpen(false);
      }
    } catch (err) {
      console.error('Error clearing history:', err);
    }
  };
  const handleSelectChat = (sessionId: string, messages: { role: 'user' | 'assistant'; content: string }[]) => {
    setSessionId(Number(sessionId));
    setMessages(messages);
    setHistoryOpen(false);
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
  if (!auth || !parameters.model) {
    return <div>Проверяем авторизацию…</div>;
  }
  return (
    <div className="min-h-screen flex bg-white text-black">
      <aside
        className={`fixed inset-y-0 left-0 z-50 w-64 bg-white text-black shadow-2xl transform transition-transform duration-300 ease-in-out ${
          historyOpen ? 'translate-x-0' : '-translate-x-full'
        } md:w-80`}
      >
        <div className="p-6 border-b border-gray-700 flex items-center justify-between">
          <h2 className="text-xl font-bold">История чатов</h2>
          <button
            onClick={() => setHistoryOpen(false)}
            className="text-gray-500 hover:text-gray-700 transition-colors"
          >
            <X size={24} />
          </button>
        </div>
        <div className="p-6 space-y-4 overflow-y-auto h-full">
          {chatHistory.length === 0 ? (
            <p className="text-gray-500">Нет сохраненных чатов</p>
          ) : (
            chatHistory.map((chat) => (
              <div
                key={chat.session_id}
                onClick={() => handleSelectChat(chat.session_id, chat.messages)}
                className="p-3 rounded-lg bg-gray-100 hover:bg-gray-200 cursor-pointer transition-colors"
              >
                <p className="text-sm font-medium">
                  Чат {chat.session_id}
                </p>
                <p className="text-xs text-gray-600 truncate">
                  {chat.messages[0]?.content.slice(0, 50) || 'Пустой чат'}
                </p>
              </div>
            ))
          )}
        </div>
      </aside>
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
                <div className="relative group">
                  <label className="block text-sm font-medium text-gray-600 capitalize">
                    {key.replace('_', ' ')}
                  </label>
                  <div className="absolute hidden group-hover:block bg-gray-800 text-white text-xs rounded py-1 px-2 mt-1 z-10 w-64">
                    {TitleParameters[`title_${key}`]}
                  </div>
                </div>
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
      {(sidebarOpen || historyOpen) && (
        <div
          className="fixed inset-0 bg-black bg-opacity-50 z-40 md:hidden"
          onClick={() => {
            setSidebarOpen(false);
            setHistoryOpen(false);
          }}
        />
      )}
      <div className="flex-1 flex flex-col min-h-0">
        <header className="px-6 py-4 border-b border-gray-300 bg-gray-100 flex justify-between items-center">
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <svg id="svg10" height="33" width="33" viewBox="0 0 600 600" version="1.1">
              <g transform="matrix(3.9572752,0,0,3.9469524,-484.68108,-434.93624)" id="g2900" style={{ fill: '#EAB308', fillOpacity: 1 }}>
                <path style={{ fill: '#EAB308', fillOpacity: 1, stroke: 'none', strokeWidth: 0.48919073, strokeMiterlimit: 4, strokeDasharray: 'none', strokeDashoffset: 0, strokeOpacity: 1 }}
                  d="m 137.43744,171.69421 18.86296,18.9937 17.78834,-17.66589 c 27.05847,29.021 55.43807,56.99501 82.28704,86.12782 4.03444,4.06233 10.59815,4.085 14.66056,0.0506 4.06232,-4.03445 4.08499,-10.59815 0.0506,-14.66056 -28.81871,-27.1901 -57.72545,-54.60143 -86.55328,-81.89095 l 23.96499,-23.80003 -33.34026,-4.61605 z"
                  id="rect4165-6" />
                <path style={{ fill: '#EAB308', fillOpacity: 1, stroke: 'none', strokeWidth: 0.50003481, strokeMiterlimit: 4, strokeDasharray: 'none', strokeDashoffset: 0, strokeOpacity: 1 }}
                  d="m 198.2887,110.1955 c 15.51743,8.7394 27.29872,21.28122 34.2484,34.3924 7.04394,13.28902 10.13959,27.16218 10.20325,38.25433 0.13054,22.74374 -18.43771,41.18184 -41.18183,41.18184 -12.13597,0 -23.04607,-5.24868 -30.58302,-13.60085 l -4.16863,3.51033 c -0.70999,-0.27231 -1.46387,-0.41221 -2.22429,-0.41276 -1.82948,1.9e-4 -3.56621,0.80531 -4.74859,2.20136 -2.97368,0.38896 -5.46251,2.44529 -6.40534,5.29224 -3.13486,6.28843 -8.63524,11.21997 -15.29104,13.4776 -0.0637,0.0216 -0.11992,0.05 -0.1758,0.0783 -3.07749,1.12758 -6.16259,3.1643 -8.78919,5.80245 -5.19155,5.23656 -7.72858,11.93658 -6.30024,16.63822 -0.14098,0.40857 -0.21361,0.83759 -0.21498,1.26979 1.5e-4,2.17082 1.75991,3.93058 3.93073,3.93073 0.54341,-0.002 1.08053,-0.11639 1.57745,-0.33632 4.69369,1.05881 11.06885,-1.54582 16.05444,-6.55917 2.82624,-2.85072 4.94356,-6.22349 5.98303,-9.53062 2.31696,-6.62278 7.29699,-12.01856 13.62281,-15.05312 0.15105,-0.0725 0.27303,-0.14714 0.38218,-0.22358 2.12082,-1.01408 3.67251,-2.92895 4.225,-5.2139 9.70222,11.44481 24.25255,18.75299 40.51876,19.13577 29.83352,0.70205 52.13299,-21.25802 53.16414,-52.83642 0.51894,-15.89259 -5.62993,-36.3847 -19.6412,-53.19089 -10.70835,-12.84441 -26.40987,-23.50795 -44.18699,-28.20777 z"
                  id="path4179-3"/>
              </g>
            </svg> LLM Chat
          </h1>
          <div className="flex gap-2">
            <button
              onClick={() => setHistoryOpen(!historyOpen)}
              className="bg-gray-600 hover:bg-gray-500 text-white p-2 rounded-lg transition-colors"
            >
              <History size={20} />
            </button>
            <button
              onClick={handleNewChat}
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
        <div className="flex-1 flex min-h-0">
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
        </div>
        <div className="border-t border-gray-300 bg-gray-100 p-4">
          <form onSubmit={handleSubmit} className="max-w-3xl mx-auto flex gap-3">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Введите ваш запрос..."
              className="flex-1 bg-white border border-gray-300 rounded-lg px-4 py-2 text-sm md:text-base outline-none focus:ring-2 focus:ring-gray-400 transition-all resize-y min-h-[40px] max-h-[140px]"
              rows={1}
            />
            <button
              type="submit"
              disabled={isLoading}
              className="bg-gray-600 hover:bg-gray-500 text-white px-4 py-2 rounded-lg disabled:opacity-50 transition-colors flex items-center gap-2 self-start"
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
