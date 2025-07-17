/** @type {import('tailwindcss').Config} */
module.exports = {
    content: [
      './app/**/*.{js,ts,jsx,tsx}', // Сканирует файлы в директории app
      './components/**/*.{js,ts,jsx,tsx}', // Если у вас есть папка components
    ],
    theme: {
      extend: {},
    },
    plugins: [],
};
