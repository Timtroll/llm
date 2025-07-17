"use client";

import React from "react";
import { useRouter, usePathname } from "next/navigation";
import LoginPage from "./login/page";
import MainPage from "./main/page";

const routes = [
  {
    path: "/",
    component: LoginPage,
    exact: true,
  },
  {
    path: "/main",
    component: MainPage,
    exact: true,
    authRequired: true,
  },
];

// Простая реализация useAuthToken (замените на вашу, если она существует)
const useAuthToken = () => {
  const [auth, setAuth] = React.useState<{ token: string; username: string } | null>(null);

  React.useEffect(() => {
    const tokenString = localStorage.getItem("authToken");
    if (tokenString) {
      try {
        const parsed = JSON.parse(tokenString) as { token: string; username: string };
        setAuth(parsed);
      } catch {
        setAuth(null);
      }
    } else {
      setAuth(null);
    }
  }, []);

  return auth;
};

const Router = () => {
  const router = useRouter();
  const pathname = usePathname();
  const auth = useAuthToken();

  // Находим маршрут, соответствующий текущему пути
  const currentRoute = routes.find((route) => route.path === pathname && route.exact);

  // Если пользователь авторизован и находится на главной странице, перенаправляем на /main
  React.useEffect(() => {
    if (auth && pathname === "/") {
      router.push("/main");
    }
    // Если пользователь не авторизован и пытается открыть /main, перенаправляем на /
    if (!auth && pathname === "/main") {
      router.push("/");
    }
  }, [auth, pathname, router]);

  // Если маршрут не найден, отображаем страницу логина по умолчанию
  if (!currentRoute) {
    return <LoginPage />;
  }

  // Для защищённых маршрутов проверяем авторизацию
  if (currentRoute.authRequired && !auth) {
    return <LoginPage />;
  }

  // Отображаем компонент текущего маршрута
  const Component = currentRoute.component;
  return <Component />;
};

export default Router;