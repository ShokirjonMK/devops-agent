/// <reference types="vite/client" />

declare module "*?raw" {
  const content: string;
  export default content;
}

interface TelegramUser {
  id: number;
  first_name: string;
  last_name?: string;
  username?: string;
  photo_url?: string;
  auth_date: number;
  hash: string;
}

interface Window {
  TelegramLoginWidget: {
    dataOnauth: (user: TelegramUser) => void;
  };
}
