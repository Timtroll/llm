import { NextResponse } from 'next/server';
import { sign } from 'jsonwebtoken';

export const config = {
  runtime: 'nodejs', // Явно указываем Node.js Runtime
};

const JWT_SECRET = process.env.JWT_SECRET || 'c8f3e0e7f2c49aa647d944fa19b7a81e5fbd49e6c534a3a8c22ef13ccf7bd189';

// Mock пользователей для демонстрации
const mockUsers = [
  { username: 'admin', password: 'password123' },
  { username: 'user', password: 'user123' },
];

export async function POST(req: Request) {
  try {
    const { username, password } = await req.json();

    // Проверка пользователя
    const user = mockUsers.find(
      (u) => u.username === username && u.password === password
    );

    if (!user) {
      return NextResponse.json(
        { message: 'Неверное имя пользователя или пароль' },
        { status: 401 }
      );
    }

    // Генерация JWT токена
    const token = sign({ username }, JWT_SECRET, {
      expiresIn: '1h',
    });

    return NextResponse.json({ token });
  } catch (_err) {
    return NextResponse.json(
      { message: 'Ошибка сервера' },
      { status: 500 }
    );
  }
}