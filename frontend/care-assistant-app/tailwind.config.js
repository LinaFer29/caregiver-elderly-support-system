/** @type {import('tailwindcss').Config} */
export default {
    content: [
      "./index.html",
      "./src/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
      extend: {
        colors: {
          primary: "#0C77A9",
          primaryLight: "#EBF6FD",
          background: "#F8F9FA",
  
          textPrimary: "#000000",
          textSecondary: "#6E7C92",
  
          hover: "#F5F5F5",
  
          whiteCustom: "#FFFFFF",

          borderCustom: "#D6DAE1"
        },
      },
    },
    plugins: [],
  };